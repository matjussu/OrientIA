"""LLM-Judge Empathie — Sprint 11 P1.1 Phase 2.

Mesure l'empathie / le ton conseiller bienveillant des réponses Mistral via
subprocess `claude --print --model claude-haiku-4-5`. Note 1-5 :
- 1 = robotique distante
- 3 = neutre informatif
- 5 = conseiller bienveillant
+ pénalité -2 si pavé indigeste sans aération.

Pas de gold standard (pas d'audit Matteo calibrant 1-5 sur sample). Single-run
par défaut avec calibration empirique sur sample bench. Si signal très bruité
(variance >1.5 entre températures équivalentes) → flag dans verdict.

Usage programmatique :
```python
from scripts.judge_empathie import judge_empathie
verdict = judge_empathie(question, answer)
print(f"score={verdict.score} (penalty={verdict.penalty_applied})")
```

Spec ordre Phase 2 : 2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_TIMEOUT_S = 120

JUDGE_EMPATHIE_PROMPT_TEMPLATE = """Tu es un évaluateur d'empathie et de ton conversationnel pour un système de conseil en orientation académique français.

OBJECTIF : noter sur une échelle 1-5 le caractère empathique / bienveillant / accessible de la réponse pour un lycéen / étudiant / jeune adulte qui se renseigne sur son orientation.

QUESTION UTILISATEUR :
{question}

RÉPONSE À ÉVALUER :
{answer}

ÉCHELLE DE NOTATION :
- **1** : robotique distante. Liste de faits sans humanité, ton administratif, aucune reconnaissance de la situation de la personne.
- **2** : peu engageant. Quelques formulations conventionnelles ("voici les options") mais surtout informatif sec.
- **3** : neutre informatif. Réponse correcte qui informe sans froideur excessive, mais pas de chaleur particulière. Standard administratif courtois.
- **4** : conseiller attentif. Reconnaissance de la situation utilisateur, formulations adaptées au profil, encouragements ponctuels.
- **5** : conseiller bienveillant exemplaire. Empathie marquée, ton chaleureux et personnalisé, anticipe les inquiétudes, propose des alternatives, encourage activement, respect du choix utilisateur.

PÉNALITÉ FORMAT (à appliquer en plus de la note) :
- Si la réponse est un PAVÉ INDIGESTE sans aération (>500 mots d'un bloc, pas de structure visuelle claire avec sections, listes, espacements) → applique pénalité -2 sur la note (jusqu'à minimum 1).
- Aération suffisante : présence de TL;DR, plans structurés (A/B/C), sections nommées, listes à puces, espaces entre paragraphes.

FORMAT DE RÉPONSE (STRICT, rien d'autre) :
NOTE_BRUTE: <entier 1-5>
PENALTY: <0 ou -2>
SCORE_FINAL: <NOTE_BRUTE + PENALTY, minimum 1>
JUSTIFICATION: <1-2 phrases courtes en français>
"""


@dataclass
class EmpathieVerdict:
    """Verdict d'évaluation empathie pour une (question, answer).

    Attributes:
        score: float 1-5 (score final post-pénalité).
        note_brute: int 1-5 (note avant pénalité format).
        penalty_applied: int (0 ou -2).
        justification: str (1-2 phrases).
        parse_errors: list[str].
        latency_ms: int.
        error: Optional[str].
        model: str.
        prompt_chars: int.
    """
    score: float
    note_brute: int
    penalty_applied: int
    justification: str
    parse_errors: list[str] = field(default_factory=list)
    latency_ms: int = 0
    error: Optional[str] = None
    model: str = DEFAULT_MODEL
    prompt_chars: int = 0

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "note_brute": self.note_brute,
            "penalty_applied": self.penalty_applied,
            "justification": self.justification,
            "parse_errors": self.parse_errors,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "model": self.model,
            "prompt_chars": self.prompt_chars,
        }


def _call_judge(prompt: str, model: str, timeout_s: int) -> dict:
    t0 = time.time()
    try:
        result = subprocess.run(
            ["claude", "--print", "--model", model],
            input=prompt, capture_output=True, text=True, timeout=timeout_s,
        )
        latency_ms = round((time.time() - t0) * 1000)
        if result.returncode != 0:
            return {"ok": False, "raw": "", "latency_ms": latency_ms,
                    "error": f"returncode={result.returncode} stderr={result.stderr[:300]}"}
        return {"ok": True, "raw": result.stdout.strip(), "latency_ms": latency_ms, "error": None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "raw": "", "latency_ms": timeout_s * 1000, "error": "timeout"}
    except FileNotFoundError:
        return {"ok": False, "raw": "", "latency_ms": 0, "error": "claude CLI not found in PATH"}
    except Exception as e:
        return {"ok": False, "raw": "", "latency_ms": round((time.time() - t0) * 1000),
                "error": f"{type(e).__name__}: {e}"}


_NOTE_RE = re.compile(r"NOTE_BRUTE\s*:\s*(\d+)", re.IGNORECASE)
_PENALTY_RE = re.compile(r"PENALTY\s*:\s*(-?\d+)", re.IGNORECASE)
_SCORE_RE = re.compile(r"SCORE_FINAL\s*:\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_JUSTIF_RE = re.compile(r"JUSTIFICATION\s*:\s*(.+?)(?:\n\n|\Z)", re.IGNORECASE | re.DOTALL)


def _parse_judge_output(raw: str) -> dict:
    parse_errors = []
    note_brute = None
    penalty = 0
    score = None

    m_note = _NOTE_RE.search(raw)
    if m_note:
        try:
            note_brute = int(m_note.group(1))
            note_brute = max(1, min(5, note_brute))
        except ValueError:
            parse_errors.append(f"NOTE_BRUTE not int: {m_note.group(1)}")
    else:
        parse_errors.append("NOTE_BRUTE pattern not matched")

    m_pen = _PENALTY_RE.search(raw)
    if m_pen:
        try:
            penalty = int(m_pen.group(1))
        except ValueError:
            parse_errors.append(f"PENALTY not int: {m_pen.group(1)}")
    else:
        parse_errors.append("PENALTY pattern not matched")

    m_score = _SCORE_RE.search(raw)
    if m_score:
        try:
            score = float(m_score.group(1).replace(",", "."))
            score = max(1.0, min(5.0, score))
        except ValueError:
            parse_errors.append(f"SCORE_FINAL not float: {m_score.group(1)}")
    else:
        # Fallback : compute from note_brute + penalty
        if note_brute is not None:
            score = max(1.0, float(note_brute) + float(penalty))

    justification = ""
    m_just = _JUSTIF_RE.search(raw)
    if m_just:
        justification = m_just.group(1).strip()
    else:
        parse_errors.append("JUSTIFICATION pattern not matched")

    return {
        "note_brute": note_brute or 3,  # fallback neutral
        "penalty": penalty,
        "score": score if score is not None else 3.0,  # fallback neutral
        "justification": justification,
        "parse_errors": parse_errors,
    }


def judge_empathie(
    question: str,
    answer: str,
    *,
    model: str = DEFAULT_MODEL,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> EmpathieVerdict:
    """Évalue l'empathie d'une réponse de conseiller orientation.

    Returns EmpathieVerdict avec score 1-5 (post-pénalité format).
    En cas d'erreur subprocess : score=3.0 (neutre), error=msg.
    En cas de parse error : score=3.0 fallback, parse_errors=[...].
    """
    if not answer or not answer.strip():
        return EmpathieVerdict(
            score=1.0, note_brute=1, penalty_applied=0,
            justification="(réponse vide, robotique par défaut)",
            model=model,
        )

    prompt = JUDGE_EMPATHIE_PROMPT_TEMPLATE.format(
        question=question.strip(), answer=answer.strip()
    )

    call = _call_judge(prompt, model=model, timeout_s=timeout_s)

    if not call["ok"]:
        return EmpathieVerdict(
            score=3.0, note_brute=3, penalty_applied=0, justification="",
            parse_errors=[], latency_ms=call["latency_ms"],
            error=call["error"], model=model, prompt_chars=len(prompt),
        )

    parsed = _parse_judge_output(call["raw"])
    return EmpathieVerdict(
        score=float(parsed["score"]),
        note_brute=int(parsed["note_brute"]),
        penalty_applied=int(parsed["penalty"]),
        justification=parsed["justification"],
        parse_errors=parsed["parse_errors"],
        latency_ms=call["latency_ms"],
        model=model, prompt_chars=len(prompt),
    )


def main() -> int:
    """Demo CLI : lance le judge sur un cas hardcodé."""
    question = "Je suis perdu après mon bac, que faire ?"
    answer = (
        "Je comprends ton inquiétude — c'est un moment important. "
        "Voici 3 pistes concrètes adaptées à ton profil. **TL;DR** : "
        "(1) Faire un bilan de tes intérêts via le CIO, (2) Explorer "
        "les BTS/BUT alternance pour démarrer rapidement, (3) Considérer "
        "une licence universitaire si tu hésites encore. Plan A : ..."
    )
    verdict = judge_empathie(question, answer)
    print(json.dumps(verdict.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
