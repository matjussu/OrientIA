"""LLM-Judge Faithfulness — Sprint 11 P0 Item 3.

Module de jugement sémantique des hallucinations factuelles dans les réponses
RAG OrientIA. Remplace la métrique pollution regex naïve (chantier E) qui était
aveugle aux affirmations factuelles datées (concours IFSI supprimé 2019, DEAMP
fusionné DEAES 2016, série L supprimée réforme bac 2021).

Modèle juge : claude-haiku-4-5 via subprocess (CI/dev offline uniquement,
JAMAIS en runtime prod — souveraineté FR exige Mistral pour traitement
données utilisateur réel).

Validation empirique sur ground truth :
- 3 hallu Matteo (Q5 IFSI / Q8 DEAMP / Q10 Terminale L) → détectées (score < 0.5)
- Edge cases (vide / fiches vides / format inattendu / JSON malformed)
  → fallback graceful

Usage programmatique :
```python
from scripts.judge_faithfulness import judge_faithfulness

verdict = judge_faithfulness(question, answer, fiches)
print(f"score={verdict.score} flagged={verdict.flagged_entities}")
```

Spec ordre : 2026-04-29-2055-claudette-orientia-sprint11-P0-item3-llm-judge-faithfulness
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------- Constants ----------

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_TIMEOUT_S = 120
DEFAULT_MAX_FICHES = 5
DEFAULT_FICHE_MAX_CHARS = 800

# Prompt v1 minimal — purement sémantique, mobilise la connaissance externe du
# juge (knowledge cutoff janv 2026 couvre largement les faits français publics).
# Itération post-recadrage Jarvis 2026-04-29 20:27 : v2 (qui injectait une
# whitelist de faits officiels = ground truth déguisée) abandonné car biaisait
# le test de faithfulness. Cf docs/sprint11-P0-item3-llm-judge-faithfulness-2026-04-29.md §2.
JUDGE_PROMPT_TEMPLATE = """Tu es un évaluateur de qualité factuelle pour un système RAG d'orientation académique en France.

OBJECTIF : repérer les AFFIRMATIONS FACTUELLES (pas les conseils) non sourcées dans les fiches OU contradictoires avec les faits réels du système éducatif français.

QUESTION : {question}

RÉPONSE À ÉVALUER :
{answer}

FICHES SOURCES ({n_fiches} premières) :
{fiches_text}

CRITÈRES D'ÉVALUATION :

1. **Affirmations factuelles à vérifier** :
   - Procédures d'admission ("concours", "sur dossier", "Parcoursup")
   - Existence de diplômes/écoles nommés
   - Faits historiques datés (suppression de filière, fusion de diplôme, réforme du bac)
   - Chiffres précis (taux d'admission, nombre de places, salaires, années)

2. **Sont OK même si pas dans fiches** :
   - Conseils méthodologiques ("prépare ton dossier", "soigne ton projet motivé")
   - Énoncés marqués "(connaissance générale)" explicitement
   - Liens et URLs (l'URL elle-même)
   - Recommandations sur la démarche

3. **Mobilise ta propre connaissance** du système éducatif français pour évaluer la véracité des affirmations factuelles. Si une affirmation est démentie par ce que tu sais des réformes, fusions de diplômes, procédures d'admission, etc. → flagger même si l'absence dans fiches semble OK.

FORMAT DE RÉPONSE (STRICT, rien d'autre) :
VERDICT: FIDELE | INFIDELE
ELEMENTS_NON_FOUND: ["citation textuelle 1", "citation textuelle 2"]
JUSTIFICATION: <1-2 phrases>
"""


# ---------- Public dataclass ----------

@dataclass
class FaithfulnessVerdict:
    """Verdict d'un eval faithfulness sur une (question, answer, fiches).

    Attributes:
        score: float dans [0, 1]. 1.0 = totalement fidèle, 0.0 = très infidèle,
               0.5 = neutre (parse error / unknown / timeout — caller doit
               décider quoi en faire).
        flagged_entities: liste des affirmations ciblées par le juge.
        justification: phrase courte expliquant le verdict.
        raw_verdict: "FIDELE" | "INFIDELE" | "UNKNOWN".
        parse_errors: liste de strings si format inattendu (vide si parse OK).
        latency_ms: temps wall-clock du subprocess.
        error: Optional[str] — message si subprocess a échoué.
        model: nom du modèle utilisé.
        prompt_chars: taille du prompt envoyé (debug/cost).
    """
    score: float
    flagged_entities: list[str]
    justification: str
    raw_verdict: str
    parse_errors: list[str] = field(default_factory=list)
    latency_ms: int = 0
    error: Optional[str] = None
    model: str = DEFAULT_MODEL
    prompt_chars: int = 0

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "flagged_entities": self.flagged_entities,
            "justification": self.justification,
            "raw_verdict": self.raw_verdict,
            "parse_errors": self.parse_errors,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "model": self.model,
            "prompt_chars": self.prompt_chars,
        }


# ---------- Helpers ----------

def fiche_to_text(fi: dict, max_chars: int = DEFAULT_FICHE_MAX_CHARS) -> str:
    """Compresse une fiche en bloc texte court pour le juge.

    Couvre les schémas Parcoursup/ONISEP/RNCP/etc. utilisés dans
    formations_unified.json. Garde uniquement les champs porteurs de signal
    factuel (nom, etab, ville, niveau, durée, type diplôme, detail).
    """
    parts = []
    nom = fi.get("nom") or fi.get("title") or fi.get("nom_metier") or "?"
    parts.append(f"NOM : {nom}")
    for k in ("etablissement", "ville", "departement", "region",
              "type_diplome", "duree", "niveau", "statut"):
        v = fi.get(k)
        if v:
            parts.append(f"{k.upper()} : {v}")
    detail = fi.get("detail") or fi.get("description") or ""
    if detail:
        parts.append(f"DETAIL : {str(detail)[:400]}")
    return " | ".join(parts)[:max_chars]


def build_fiches_text(fiches: list[dict], max_fiches: int = DEFAULT_MAX_FICHES) -> str:
    """Concatène les N premières fiches uniques en un bloc texte structuré."""
    if not fiches:
        return "(aucune fiche retournée par le RAG)"
    seen, out = set(), []
    for fi in fiches:
        fid = fi.get("id") or fi.get("identifiant") or fi.get("nom") or str(id(fi))
        if fid in seen:
            continue
        seen.add(fid)
        out.append(fi)
        if len(out) >= max_fiches:
            break
    return "\n---\n".join(f"[fiche {i+1}]\n{fiche_to_text(fi)}" for i, fi in enumerate(out))


# ---------- Subprocess ----------

def _call_judge(prompt: str, model: str, timeout_s: int) -> dict:
    """Invoque le juge via `claude --print --model <model>`.

    Returns:
        dict with keys: ok (bool), raw (str), latency_ms (int), error (Optional[str]).
    """
    t0 = time.time()
    try:
        result = subprocess.run(
            ["claude", "--print", "--model", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        latency_ms = round((time.time() - t0) * 1000)
        if result.returncode != 0:
            return {"ok": False, "raw": "", "latency_ms": latency_ms,
                    "error": f"returncode={result.returncode} stderr={result.stderr[:300]}"}
        return {"ok": True, "raw": result.stdout.strip(), "latency_ms": latency_ms, "error": None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "raw": "", "latency_ms": timeout_s * 1000, "error": "timeout"}
    except FileNotFoundError:
        return {"ok": False, "raw": "", "latency_ms": 0,
                "error": "claude CLI not found in PATH"}
    except Exception as e:  # pragma: no cover - defensive catch-all
        return {"ok": False, "raw": "", "latency_ms": round((time.time() - t0) * 1000),
                "error": f"{type(e).__name__}: {e}"}


# ---------- Parser ----------

_VERDICT_RE = re.compile(r"VERDICT\s*:\s*(FIDELE|INFIDELE|OUI|NON)", re.IGNORECASE)
_ELEMENTS_RE = re.compile(r"ELEMENTS_NON_FOUND\s*:\s*(\[.*?\])", re.IGNORECASE | re.DOTALL)
_JUSTIF_RE = re.compile(r"JUSTIFICATION\s*:\s*(.+?)(?:\n\n|\Z)", re.IGNORECASE | re.DOTALL)


def _parse_judge_output(raw: str) -> dict:
    """Parser robuste du format strict du juge.

    Tolère :
    - VERDICT en lowercase / OUI ou NON (alias FIDELE/INFIDELE).
    - ELEMENTS_NON_FOUND avec quotes mal échappées (fallback regex string extraction).
    - JUSTIFICATION manquante.

    Returns dict {verdict, elements, justification, parse_errors}.
    """
    parse_errors = []

    m_v = _VERDICT_RE.search(raw)
    if not m_v:
        return {"verdict": "UNKNOWN", "elements": [], "justification": "",
                "parse_errors": ["VERDICT pattern not matched in output"]}
    tok = m_v.group(1).upper()
    if tok in ("OUI", "FIDELE"):
        verdict = "FIDELE"
    elif tok in ("NON", "INFIDELE"):
        verdict = "INFIDELE"
    else:
        verdict = "UNKNOWN"
        parse_errors.append(f"Unknown verdict token: {tok}")

    elements: list[str] = []
    m_e = _ELEMENTS_RE.search(raw)
    if m_e:
        try:
            decoded = json.loads(m_e.group(1))
            if isinstance(decoded, list):
                elements = [str(x) for x in decoded]
            else:
                parse_errors.append("ELEMENTS_NON_FOUND not a list, ignored")
        except json.JSONDecodeError as e:
            parse_errors.append(f"ELEMENTS JSON decode failed: {e}")
            # Fallback : extract quoted strings (best effort)
            elements = re.findall(r'"([^"]+)"', m_e.group(1))
    else:
        parse_errors.append("ELEMENTS_NON_FOUND section not found")

    justification = ""
    m_j = _JUSTIF_RE.search(raw)
    if m_j:
        justification = m_j.group(1).strip()
    else:
        parse_errors.append("JUSTIFICATION section not found")

    return {
        "verdict": verdict,
        "elements": elements,
        "justification": justification,
        "parse_errors": parse_errors,
    }


def _score_from_parsed(parsed: dict) -> float:
    """Convertit (verdict, elements) en score float [0, 1].

    Calibration empirique pour respecter :
    - Ground truth (1+ element flagged + INFIDELE) → score < 0.5 ✅
    - Cas clean strict (FIDELE + 0 element) → score = 1.0 ≥ 0.8 ✅
    - Parse error / UNKNOWN → 0.5 (neutre, signal au caller qu'il y a un doute)

    Tableau :
        FIDELE     + 0 elements   → 1.00
        FIDELE     + 1+ elements  → 0.70  (juge fidèle mais a noté des points)
        INFIDELE   + 0 elements   → 0.40  (juge infidèle sans citation = douteux)
        INFIDELE   + 1 element    → 0.35
        INFIDELE   + 2 elements   → 0.20
        INFIDELE   + 3+ elements  → 0.00
        UNKNOWN    + N quelconque → 0.50
    """
    v = parsed.get("verdict")
    n = len(parsed.get("elements") or [])
    if v == "FIDELE":
        return 1.0 if n == 0 else 0.7
    if v == "INFIDELE":
        if n == 0:
            return 0.4
        return max(0.0, 0.5 - 0.15 * n)
    return 0.5


# ---------- Public API ----------

def judge_faithfulness(
    question: str,
    answer: str,
    fiches: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    max_fiches: int = DEFAULT_MAX_FICHES,
) -> FaithfulnessVerdict:
    """Évalue la fidélité d'une réponse RAG aux fiches sources.

    Args:
        question: question utilisateur.
        answer: réponse générée par le LLM.
        fiches: liste de dicts (formations_unified.json schema).
        model: modèle juge (défaut claude-haiku-4-5).
        timeout_s: timeout subprocess.
        max_fiches: nombre max de fiches à inclure dans le contexte juge.

    Returns:
        FaithfulnessVerdict avec score, flagged_entities, justification.
        En cas d'erreur subprocess : score=0.5, error=msg.
        En cas de parse error : score=0.5, parse_errors=[...].
    """
    # Edge case : answer vide → fidèle par défaut (rien à juger)
    if not answer or not answer.strip():
        return FaithfulnessVerdict(
            score=1.0, flagged_entities=[], justification="(réponse vide, rien à juger)",
            raw_verdict="FIDELE", model=model,
        )

    fiches_text = build_fiches_text(fiches, max_fiches=max_fiches)
    n_fiches = min(len(fiches or []), max_fiches)
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question.strip(),
        answer=answer.strip(),
        fiches_text=fiches_text,
        n_fiches=n_fiches,
    )

    call = _call_judge(prompt, model=model, timeout_s=timeout_s)

    if not call["ok"]:
        return FaithfulnessVerdict(
            score=0.5, flagged_entities=[], justification="",
            raw_verdict="UNKNOWN",
            parse_errors=[],
            latency_ms=call["latency_ms"],
            error=call["error"], model=model, prompt_chars=len(prompt),
        )

    parsed = _parse_judge_output(call["raw"])
    return FaithfulnessVerdict(
        score=_score_from_parsed(parsed),
        flagged_entities=parsed["elements"],
        justification=parsed["justification"],
        raw_verdict=parsed["verdict"],
        parse_errors=parsed["parse_errors"],
        latency_ms=call["latency_ms"],
        model=model, prompt_chars=len(prompt),
    )


# ---------- CLI standalone ----------

def main() -> int:
    """Demo CLI : lance le juge sur un cas hardcodé Q5 IFSI ground truth.

    Usage : `python3 scripts/judge_faithfulness.py`
    """
    question = "J'ai raté ma PASS, est-ce que je peux quand même faire kiné ou infirmière ?"
    answer = (
        "Pour devenir infirmière, l'IFSI est accessible **sur concours post-bac** "
        "(3 ans d'études). Tu peux aussi tenter une L.AS pour retenter kiné en 2e année."
    )
    fiches = [
        {"id": "parcoursup-X", "nom": "PASS Lille", "etablissement": "Université de Lille",
         "type_diplome": "Licence", "duree": "1 an"},
    ]
    print(f"==> Demo judge_faithfulness sur Q5 IFSI hallu")
    verdict = judge_faithfulness(question, answer, fiches)
    print(json.dumps(verdict.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
