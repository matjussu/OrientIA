#!/usr/bin/env python3
"""generate_golden_qa_v1.py — Sprint 9-data Ordre 2/2 (2026-04-28).

Génère un dataset de Q&A "réponses parfaites de conseiller" via pipeline
agentique 4 phases (research WebSearch → draft → self-critique → refine)
en orchestrant des sub-agents Claude Opus 4.7 via subprocess `claude --print`.

Coût marginal 0$ (utilise quota Claude Max plan de Matteo, pas l'API
Anthropic facturée — décision D5 ADR `2026-04-28-orientia-pivot-pipeline-agentique-claude`).

## Architecture

```
[YAML config 51 prompts × 5-6 seeds]
        ↓
ThreadPoolExecutor (--parallel N)
        ↓
Pour chaque (prompt_id, iteration_idx) :
    Phase 1 : research WebSearch (sub-agent, allowedTools=WebSearch)
        ↓
    Phase 2 : draft Q&A persona conseiller (sub-agent)
        ↓
    Phase 3 : self-critique 4 axes (sub-agent)
        ↓
    Phase 4 : refinement (sub-agent)
        ↓
    Decision policy : keep≥85 / flag 70-85 / drop<70
        ↓
ThreadSafeJsonlAppender → data/golden_qa/golden_qa_v1.jsonl
```

## Rate limiting défensif

- `--parallel N` : 3 par défaut (Max 20x : 5, Max 5x : 2, Pro : 1)
- `--rate-limit-delay D` : délai entre calls (défaut 0.5s)
- `--max-retries R` : retries sur 429 (défaut 3)
- Stop condition : >10 consecutive 429 → abort (Sprint 9-data fallback 500 cas)
- Backoff exponentiel sur 429 : 2^attempt + delay

## Checkpointing

JSONL append-only — si CTRL+C / crash, le prochain run skip les
(prompt_id, iteration) déjà présents dans le fichier output.

## Usage

```bash
# Dry-run 1 prompt × 5 itérations
python scripts/generate_golden_qa_v1.py \\
    --config config/diverse_prompts_50.yaml \\
    --output data/golden_qa/dryrun_test.jsonl \\
    --parallel 2 --filter-prompt-id A1 --max-iterations 5

# Lancement nuit (1020 cas)
python scripts/generate_golden_qa_v1.py \\
    --config config/diverse_prompts_50.yaml \\
    --output data/golden_qa/golden_qa_v1.jsonl \\
    --parallel 3 --target 1020 --model claude-opus-4-7
```
"""
from __future__ import annotations

import argparse
import json
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ────────────────────────────── Constants ─────────────────────────────

DEFAULT_PARALLEL = 3
DEFAULT_RATE_LIMIT_DELAY = 0.5
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_S = 300
RATE_LIMIT_BACKOFF_BASE = 2.0
MAX_CONSECUTIVE_429 = 10  # stop condition

SCORE_KEEP_THRESHOLD = 85
SCORE_FLAG_THRESHOLD = 70

# Détection 429 / rate limit / quota Claude Max plan dans stderr/stdout subprocess
# (la CLI `claude --print` peut exit en signalant des limites de plusieurs façons :
#  HTTP 429 standard, message "out of extra usage" Claude Max, "limit reached", etc.)
_RATE_LIMIT_PATTERNS = [
    re.compile(r"\brate[-_ ]?limit", re.IGNORECASE),
    re.compile(r"\b429\b"),
    re.compile(r"\bquota exceeded", re.IGNORECASE),
    re.compile(r"\btoo many requests", re.IGNORECASE),
    # Claude Max plan limits (signature observée 2026-04-28 dryrun v2 :
    # "You're out of extra usage · resets 5:40pm (Europe/Paris)")
    re.compile(r"\bout of (?:extra )?usage", re.IGNORECASE),
    re.compile(r"\busage limit", re.IGNORECASE),
    re.compile(r"\b(?:5-?hour|monthly) limit", re.IGNORECASE),
    re.compile(r"\bresets? (?:at )?\d", re.IGNORECASE),  # "resets 5:40pm" / "resets at 17h"
]

# Cap pour ne pas exploser la taille du JSONL
_RESEARCH_TEXT_CAP = 5000
_RAW_FALLBACK_CAP = 2000

# Global shutdown signal (CTRL+C clean)
_shutdown_event = threading.Event()


# ────────────────────────────── Datatypes ─────────────────────────────


@dataclass
class GenerateConfig:
    yaml_config_path: Path
    output_jsonl: Path
    parallel: int = DEFAULT_PARALLEL
    target: int | None = None
    filter_prompt_id: str | None = None
    max_iterations: int | None = None
    model: str | None = None
    rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout_s: int = DEFAULT_TIMEOUT_S
    dry_run_no_subprocess: bool = False  # debug : no subprocess, fake responses


@dataclass
class RetryStats:
    """Statistiques retries thread-safe pour stop conditions."""

    consecutive_429: int = 0
    total_429: int = 0
    total_success: int = 0
    total_other_errors: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self) -> None:
        with self._lock:
            self.consecutive_429 = 0
            self.total_success += 1

    def record_429(self) -> int:
        with self._lock:
            self.consecutive_429 += 1
            self.total_429 += 1
            return self.consecutive_429

    def record_other_error(self) -> None:
        with self._lock:
            self.total_other_errors += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "success": self.total_success,
                "429": self.total_429,
                "other_errors": self.total_other_errors,
                "consecutive_429": self.consecutive_429,
            }


# ────────────────────────────── Subprocess wrapper ──────────────────────


def call_claude_subprocess(
    prompt: str,
    allowed_tools: list[str] | None = None,
    model: str | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> tuple[str, str, int]:
    """Invoque `claude --print` subprocess. Retourne (stdout, stderr, returncode)."""
    cmd = ["claude", "--print"]
    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])
    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {timeout_s}s", -1
    except FileNotFoundError:
        return "", "claude CLI not found in PATH (install Claude Code first)", -2


def is_rate_limit_error(stderr: str, stdout: str) -> bool:
    """Détecte 429 / rate limit dans stderr ou stdout."""
    for text in (stderr or "", stdout or ""):
        for pattern in _RATE_LIMIT_PATTERNS:
            if pattern.search(text):
                return True
    return False


def call_claude_with_retry(
    prompt: str,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
    allowed_tools: list[str] | None = None,
) -> str:
    """Subprocess avec backoff exponentiel sur 429. Raise RuntimeError sur fail définitif."""
    if cfg.dry_run_no_subprocess:
        return _fake_response_for_debug(prompt)

    for attempt in range(cfg.max_retries + 1):
        if _shutdown_event.is_set():
            raise RuntimeError("shutdown signal received")

        stdout, stderr, rc = call_claude_subprocess(
            prompt,
            allowed_tools=allowed_tools,
            model=cfg.model,
            timeout_s=cfg.timeout_s,
        )

        if rc == 0 and stdout:
            retry_stats.record_success()
            time.sleep(cfg.rate_limit_delay)
            return stdout

        if is_rate_limit_error(stderr, stdout):
            consecutive = retry_stats.record_429()
            if consecutive > MAX_CONSECUTIVE_429:
                raise RuntimeError(
                    f"Stop condition: {consecutive} consecutive 429 — abort "
                    "(reduce --parallel or wait Claude Max quota reset)"
                )
            backoff = (RATE_LIMIT_BACKOFF_BASE ** attempt) + cfg.rate_limit_delay
            time.sleep(backoff)
            continue

        # Autre erreur (timeout, CLI not found, malformed prompt)
        retry_stats.record_other_error()
        if attempt < cfg.max_retries:
            time.sleep(cfg.rate_limit_delay * (attempt + 1))
            continue
        raise RuntimeError(
            f"claude --print failed after {cfg.max_retries} retries "
            f"(rc={rc}): {(stderr or stdout)[:500]}"
        )

    raise RuntimeError("call_claude_with_retry: unreachable (loop exhausted)")


def _fake_response_for_debug(prompt: str) -> str:
    """Réponse fake pour mode debug `--dry-run-no-subprocess` (CI / tests).

    Détection par schema attendu dans le prompt (markers "Output JSON STRICT")
    plutôt que par mots-clés du contenu, pour éviter les faux-positifs (ex
    Phase 2 prompt mentionnant 'Phase 1' dans une instruction).
    """
    has_score = '"score_total"' in prompt and '"scores_par_axe"' in prompt
    has_answer_refined = '"answer_refined"' in prompt
    has_qa_pair = (
        '"question"' in prompt and '"answer"' in prompt and not has_answer_refined
    )

    if has_score:
        return '{"score_total": 90, "scores_par_axe": {"factuelle": 22, "posture": 23, "coherence": 23, "hallucination": 22}, "corrections_suggérées": "RAS — fake debug", "decision_recommandée": "keep"}'
    if has_answer_refined:
        return '{"question": "Q fake", "answer_refined": "A fake refined"}'
    if has_qa_pair:
        return '{"question": "Q fake", "answer": "A fake draft"}'
    # Phase 1 research : output plain text, pas de schema JSON attendu
    return "- URL: https://example.gouv.fr\n- Date: 2026-01-15\n- Extrait clé: Source factice."


# ────────────────────────────── 4-phase pipeline ────────────────────────


def phase1_research(prompt_config: dict, cfg: GenerateConfig, retry_stats: RetryStats) -> str:
    sources_str = "\n  - ".join(prompt_config["sources_priority"])
    prompt = f"""Pour ce persona : {prompt_config['persona']}
Et ce contexte : {prompt_config['context']}

Cherche les dernières infos officielles 2025-2026 via WebSearch.

Sources à prioriser (utilise WebSearch sur ces domaines en priorité) :
  - {sources_str}

Output : 3-5 sources factuelles datées, chaque source au format :
- URL : ...
- Date : ... (préfère 2025-2026)
- Extrait clé : ... (1-2 phrases factuelles)

Réponds UNIQUEMENT avec ces sources, pas de préambule, pas de markdown autour."""
    return call_claude_with_retry(
        prompt, cfg, retry_stats, allowed_tools=["WebSearch", "WebFetch"]
    )


def phase2_draft(
    prompt_config: dict,
    research_result: str,
    question_seed: str,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
) -> str:
    prompt = f"""Tu es un expert orientation conseiller bienveillant. Avec ces sources factuelles :

{research_result}

Et ce contexte profil :
- Persona : {prompt_config['persona']}
- Context : {prompt_config['context']}
- Constraints : {prompt_config['constraints']}
- Tone : {prompt_config['tone']}

Génère 1 Q&A type entretien d'orientation.

QUESTION (à varier autour de la seed mais en restant proche de l'esprit du seed) :
"{question_seed}"

RÉPONSE PARFAITE de conseiller bienveillant :
- Active listening + reformulation en ouverture (1-2 phrases "Si je te/vous comprends bien...")
- Reconnaissance émotion si pertinent (1 phrase max, optionnel)
- 3 pistes pondérées non-prescriptives avec critères objectifs (durée, coût, sélectivité, débouché)
- INTERDIT : reco prescriptive ("tu devrais"). Toujours 3 options pondérées
- Question finale d'exploration qui rend le choix à l'utilisateur·ice
- Tone strictement {prompt_config['tone']}

INTERDICTION STRICTE de chiffres précis (tarif, salaire, %, durée, taux d'insertion, sélectivité, places concours, années, mensualité, montant aide, score moyen) non EXPLICITEMENT présents dans les sources de la Phase 1 WebSearch.

Si une donnée chiffrée n'est pas dans les sources Phase 1 retrievées, remplace-la par une notion QUALITATIVE :
- "frais de scolarité ~10 500€/an" → "frais élevés (école privée de commerce)"
- "taux d'insertion 90%" → "très bonne insertion documentée"
- "salaire moyen 2 000€ brut/mois" → "salaire de débutant standard"
- "sélectivité ~28%" → "sélectivité modérée"
- "9 mois de césure" → "césure de quelques mois à 1 an"

NE JAMAIS écrire un nombre (avec %, €, ans, mois, mensuel, points, places, etc.) sans vérifier qu'il est dans le research Phase 1. En cas de doute, **registre qualitatif obligatoire**.

Cette règle est plus stricte que l'ancien estimation marker : on retire complètement les chiffres non sourcés au lieu de les flagger "(estimation)". Raison : Mistral en inférence finale peut perdre le marker `(estimation)` et propager des faux chiffres en confiance — éviter le risque à la racine.

LISIBILITÉ MOBILE OBLIGATOIRE :
- Lecteur cible : 17-25 ans sur smartphone, souvent angoissé (Parcoursup, réorientation)
- Format obligatoire :
  - 1-2 phrases reformulation/active listening en ouverture
  - 3 pistes en BULLET POINTS COURTS (max 2-3 phrases par piste, pas de paragraphe long)
  - 1 phrase question finale d'exploration
- Limite totale : **250-350 mots maximum**
- Sauts de ligne entre pistes pour respiration
- Densité = ennemi du lecteur stressé. Bloc texte massif INTERDIT.

Output JSON STRICT :
{{
  "question": "...",
  "answer": "..."
}}

Réponds UNIQUEMENT avec ce JSON, pas de préambule, pas de markdown autour."""
    return call_claude_with_retry(prompt, cfg, retry_stats)


def phase3_critique(
    draft_raw: str,
    prompt_config: dict,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
) -> str:
    prompt = f"""Tu es un évaluateur qualité Q&A orientation. Évalue cette Q&A :

{draft_raw}

Profil cible attendu :
- Persona : {prompt_config['persona']}
- Tone attendu : {prompt_config['tone']}

Évalue sur 4 axes (chacun /25, total /100) :

1. Pertinence factuelle (formation existe vraiment, infos justes, pas de chiffre inventé hors sources) /25
2. Posture conseiller (questions ouvertes, non-jugement, reformulation présente, 3 options pondérées non-prescriptives) /25
3. Cohérence avec persona/contexte (vocabulaire/registre adapté au tone, contraintes respectées) /25
4. Absence d'hallucination flagrante (pas de slug ONISEP/Parcoursup inventé, pas d'URL bidon, pas d'école inexistante, pas de chiffre précis non sourcé) /25

Pénalités lourdes (-10 sur l'axe correspondant) :
- "Tu devrais faire X" (prescriptif au lieu de pondéré)
- Reco au tour 1 sans questionnement préalable (rare mais signal)
- Slug ONISEP/Parcoursup factice
- Tone mismatch (ex: vouvoiement attendu, tutoiement produit)

Output JSON STRICT :
{{
  "score_total": <int 0-100>,
  "scores_par_axe": {{
    "factuelle": <int 0-25>,
    "posture": <int 0-25>,
    "coherence": <int 0-25>,
    "hallucination": <int 0-25>
  }},
  "corrections_suggérées": "<text 1-3 phrases courtes>",
  "decision_recommandée": "<keep|flag|drop>"
}}

Réponds UNIQUEMENT avec ce JSON."""
    return call_claude_with_retry(prompt, cfg, retry_stats)


def phase4_refine(
    draft_raw: str,
    critique_raw: str,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
) -> str:
    prompt = f"""Tu es un expert orientation. Voici une Q&A initialement produite :

DRAFT :
{draft_raw}

Voici les corrections suggérées par l'évaluateur :

CRITIQUE :
{critique_raw}

Réécris la réponse en intégrant TOUTES les corrections suggérées. Préserve la question originale (ne pas la modifier). Préserve le ton et la structure conseiller (reformulation + 3 options pondérées + question finale).

Output JSON STRICT :
{{
  "question": "...",
  "answer_refined": "..."
}}

Réponds UNIQUEMENT avec ce JSON."""
    return call_claude_with_retry(prompt, cfg, retry_stats)


# ────────────────────────────── JSONL appender ─────────────────────────


class ThreadSafeJsonlAppender:
    """Append JSON lines à un fichier en mode thread-safe.

    Pattern reproduit de `src/agent/parallel.py:parallel_apply` Sprint 4-5.
    Chaque write est atomique (lock + open(append) + write + close).
    """

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def existing_keys(self) -> set[tuple]:
        """Retourne l'ensemble des (prompt_id, iteration) déjà présents.

        Utilisé pour le checkpointing : skip les jobs déjà faits au resume.
        Tolère les lignes JSON invalides (skip silencieusement, log).
        """
        keys: set[tuple] = set()
        if not self.path.exists() or self.path.stat().st_size == 0:
            return keys
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    keys.add((rec.get("prompt_id"), rec.get("iteration")))
                except json.JSONDecodeError:
                    continue
        return keys


# ────────────────────────────── Decision policy + parsing ───────────────


def decision_from_score(score: int) -> str:
    if score >= SCORE_KEEP_THRESHOLD:
        return "keep"
    if score >= SCORE_FLAG_THRESHOLD:
        return "flag"
    return "drop"


def parse_json_safe(text: str) -> dict | None:
    """Parse JSON robuste — tolère ```json blocks, préambules courts, JSON imbriqué."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown json fence
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback : regex extraction du premier { ... } objet
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


# ────────────────────────────── Main 4-phase orchestration ─────────────


def generate_qa(
    prompt_config: dict,
    iteration_idx: int,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
) -> dict:
    """Orchestre les 4 phases pour 1 (prompt_id, iteration_idx). Retourne le record JSONL."""
    t0 = time.time()
    seeds = prompt_config["questions_seed"]
    question_seed = seeds[iteration_idx % len(seeds)]

    record: dict[str, Any] = {
        "prompt_id": prompt_config["id"],
        "iteration": iteration_idx,
        "question_seed": question_seed,
        "category": prompt_config["category"],
        "axe_couvert": prompt_config["axe_couvert"],
        "model": cfg.model,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    try:
        # Phase 1 — Research WebSearch
        research = phase1_research(prompt_config, cfg, retry_stats)

        # Phase 2 — Draft
        draft_raw = phase2_draft(prompt_config, research, question_seed, cfg, retry_stats)
        draft = parse_json_safe(draft_raw)

        # Phase 3 — Self-critique
        critique_raw = phase3_critique(draft_raw, prompt_config, cfg, retry_stats)
        critique = parse_json_safe(critique_raw)
        score = int(critique.get("score_total", 0)) if critique else 0

        # Phase 4 — Refinement
        refined_raw = phase4_refine(draft_raw, critique_raw, cfg, retry_stats)
        refined = parse_json_safe(refined_raw)

        record.update({
            "research_sources_text": research[:_RESEARCH_TEXT_CAP],
            "draft": draft or {"raw": draft_raw[:_RAW_FALLBACK_CAP]},
            "critique": critique or {"raw": critique_raw[:_RAW_FALLBACK_CAP]},
            "final_qa": refined or {"raw": refined_raw[:_RAW_FALLBACK_CAP]},
            "score_total": score,
            "decision": decision_from_score(score),
            "elapsed_s": round(time.time() - t0, 1),
            "error": None,
        })
    except Exception as e:
        record.update({
            "error": f"{type(e).__name__}: {e}",
            "decision": "drop",
            "score_total": 0,
            "elapsed_s": round(time.time() - t0, 1),
        })
    return record


# ────────────────────────────── CLI / main ──────────────────────────────


def parse_cli() -> GenerateConfig:
    p = argparse.ArgumentParser(
        description="Pipeline agentique 4 phases — génération 1000 Q&A conseiller"
    )
    p.add_argument("--config", type=Path, required=True, help="YAML config 51 prompts")
    p.add_argument("--output", type=Path, required=True, help="Output JSONL append-only")
    p.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL,
                   help=f"Sub-agents simultanés (défaut {DEFAULT_PARALLEL}). "
                        "Max 20x: 5, Max 5x: 2, Pro: 1")
    p.add_argument("--target", type=int, default=None,
                   help="Cap nb total Q&A à générer (défaut : tous prompts × max_iterations)")
    p.add_argument("--filter-prompt-id", type=str, default=None,
                   help="Filtre sur 1 seul prompt (pour dry-run, ex: A1)")
    p.add_argument("--max-iterations", type=int, default=None,
                   help="Override iterations_per_prompt YAML metadata")
    p.add_argument("--model", type=str, default=None,
                   help="Modèle Claude (claude-opus-4-7 / opus-4.7 / drop pour default)")
    p.add_argument("--rate-limit-delay", type=float, default=DEFAULT_RATE_LIMIT_DELAY,
                   help=f"Délai entre calls subprocess (s, défaut {DEFAULT_RATE_LIMIT_DELAY})")
    p.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
                   help=f"Retries sur 429 (défaut {DEFAULT_MAX_RETRIES})")
    p.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S,
                   help=f"Timeout subprocess (s, défaut {DEFAULT_TIMEOUT_S})")
    p.add_argument("--dry-run-no-subprocess", action="store_true",
                   help="Debug : remplace subprocess par fake responses (no API)")
    args = p.parse_args()

    return GenerateConfig(
        yaml_config_path=args.config,
        output_jsonl=args.output,
        parallel=args.parallel,
        target=args.target,
        filter_prompt_id=args.filter_prompt_id,
        max_iterations=args.max_iterations,
        model=args.model,
        rate_limit_delay=args.rate_limit_delay,
        max_retries=args.max_retries,
        timeout_s=args.timeout_s,
        dry_run_no_subprocess=args.dry_run_no_subprocess,
    )


def _signal_handler(signum, _frame):
    print(f"\n⚠️  Signal {signum} reçu — arrêt propre en cours (en attente fin des tâches en vol)...",
          flush=True)
    _shutdown_event.set()


def build_jobs(yaml_data: dict, cfg: GenerateConfig) -> list[tuple[dict, int]]:
    """Construit la liste des jobs (prompt_config, iteration_idx)."""
    prompts = yaml_data["prompts"]
    if cfg.filter_prompt_id:
        prompts = [p for p in prompts if p["id"] == cfg.filter_prompt_id]
        if not prompts:
            raise ValueError(f"Aucun prompt trouvé pour --filter-prompt-id {cfg.filter_prompt_id}")
    iter_per_prompt = (
        cfg.max_iterations
        or yaml_data.get("metadata", {}).get("iterations_per_prompt", 20)
    )
    jobs = [(p, i) for p in prompts for i in range(iter_per_prompt)]
    if cfg.target:
        jobs = jobs[: cfg.target]
    return jobs


def main() -> int:
    cfg = parse_cli()
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"==> generate_golden_qa_v1.py")
    print(f"    config: {cfg.yaml_config_path}")
    print(f"    output: {cfg.output_jsonl}")
    print(f"    parallel: {cfg.parallel}, model: {cfg.model or '(default)'}, "
          f"rate_limit_delay: {cfg.rate_limit_delay}s, max_retries: {cfg.max_retries}")
    if cfg.dry_run_no_subprocess:
        print("    ⚠️  --dry-run-no-subprocess : NO real subprocess, fake responses")

    yaml_data = yaml.safe_load(cfg.yaml_config_path.read_text(encoding="utf-8"))
    jobs = build_jobs(yaml_data, cfg)

    appender = ThreadSafeJsonlAppender(cfg.output_jsonl)
    existing = appender.existing_keys()
    jobs_to_run = [(p, i) for p, i in jobs if (p["id"], i) not in existing]

    print(f"    jobs total: {len(jobs)}, déjà fait: {len(existing)}, à exécuter: {len(jobs_to_run)}")

    if not jobs_to_run:
        print("==> Rien à faire (tous les jobs déjà présents dans le JSONL).")
        return 0

    retry_stats = RetryStats()
    counts: dict[str, int] = {"keep": 0, "flag": 0, "drop": 0}
    errors_count = 0
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=cfg.parallel) as pool:
        futures = {
            pool.submit(generate_qa, pc, ii, cfg, retry_stats): (pc["id"], ii)
            for pc, ii in jobs_to_run
        }

        for i, fut in enumerate(as_completed(futures), 1):
            if _shutdown_event.is_set():
                pool.shutdown(wait=False, cancel_futures=True)
                print("\n==> Shutdown propagé, arrêt des futures restantes.")
                break
            try:
                rec = fut.result()
            except Exception as e:
                errors_count += 1
                print(f"[{i}/{len(jobs_to_run)}] ERROR future: {type(e).__name__}: {e}",
                      flush=True)
                continue

            appender.append(rec)
            decision = rec.get("decision", "drop")
            counts[decision] = counts.get(decision, 0) + 1
            if rec.get("error"):
                errors_count += 1

            if i % 10 == 0 or i == len(jobs_to_run) or i <= 5:
                elapsed = time.time() - t_start
                rate = i / elapsed if elapsed > 0 else 0.0
                stats = retry_stats.snapshot()
                print(f"[{i}/{len(jobs_to_run)}] {rec['prompt_id']}#{rec['iteration']} → "
                      f"{decision} (score={rec.get('score_total', 0)}) | "
                      f"counts={counts} errors={errors_count} | "
                      f"rate={rate:.2f}/s | retry={stats}",
                      flush=True)

    total_elapsed = time.time() - t_start
    print(f"\n==> DONE. Elapsed: {total_elapsed/60:.1f} min")
    print(f"    Final counts: {counts}, errors: {errors_count}")
    print(f"    Retry stats: {retry_stats.snapshot()}")

    # Exit non-zéro si trop d'erreurs (pour signal Jarvis surveillance nuit)
    error_rate = errors_count / max(len(jobs_to_run), 1)
    if error_rate > 0.30:
        print(f"⚠️  Error rate {error_rate:.1%} > 30% — investigation requise.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
