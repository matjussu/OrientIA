"""Construction du prompt à passer à un sous-agent Claude Code (Haiku)
pour traiter un chunk de fiches (ADR-060 addendum 2026-05-08).

Le sous-agent reçoit un seul prompt-string qui contient :
1. Identité / rôle
2. Règles R1-R5 (ton, format, préservation faits)
3. 1 example concret (input/output)
4. Instructions I/O strictes : lire le fichier chunk, produire le fichier
   results, format JSON exact attendu.
"""

from __future__ import annotations

from pathlib import Path

from src.rewrite.prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT


# Format de sortie strict — c'est le contrat avec le finalize_rewrite_v6.py.
# Toute déviation et la fiche est skippée.
OUTPUT_FORMAT_SPEC = """[
  {"fiche_id": "<id de la fiche source>", "rewritten_text": "<paragraphe naturel français 80-250 mots>"},
  ...
]"""


def build_agent_prompt(
    chunk_path: Path,
    results_path: Path,
    *,
    chunk_id: str | None = None,
) -> str:
    """Construit le prompt complet à passer à ``Agent(model="haiku", ...)``.

    Args:
        chunk_path: chemin absolu du fichier ``chunk_NNNN.json`` à lire.
        results_path: chemin absolu du fichier ``chunk_NNNN_results.json``
            à écrire.
        chunk_id: identifiant lisible du chunk pour traçabilité dans le
            prompt (par défaut dérivé du nom de fichier).

    Returns:
        prompt-string prêt à être passé en ``prompt`` du tool Agent.
    """
    chunk_id = chunk_id or chunk_path.stem
    fs1 = FEW_SHOT_EXAMPLES[0]

    return f"""Tu es un sous-agent dispatché pour réécrire en français naturel les fiches d'un corpus officiel d'orientation post-bac (Phase 3 V2 du projet OrientIA). Ton seul travail : lire un fichier de fiches, produire un paragraphe naturel pour chacune, écrire le résultat dans un autre fichier. Pas de question, pas d'analyse stratégique, pas d'exploration du repo.

# Mission

Lire **toutes** les fiches contenues dans :
  {chunk_path}

Pour chacune, produire un paragraphe rewritten respectant strictement les règles ci-dessous. Écrire le résultat (toutes les fiches du chunk, dans une seule liste JSON) dans :
  {results_path}

Identifiant lisible du chunk : `{chunk_id}`.

# Pourquoi

Les `text` actuels des fiches sont rédigés en format structuré avec séparateurs `|` (ex : "CROUS Lyon | 12000 logements | 36 restos U"). Ces textes sont mal alignés sémantiquement avec les questions naturelles d'un lycéen, donc le retrieval RAG les rate. Tu produis la version « paragraphe naturel » qui sera ensuite ré-embeddée dans FAISS pour améliorer le retrieval.

# Règles de réécriture (R1-R5)

{SYSTEM_PROMPT}

# Exemple

## Input fiche
```json
{fs1["input"]}
```

## Output (paragraphe rewritten attendu)
{fs1["output"]}

# Format de sortie EXIGÉ

Le fichier {results_path} doit contenir une **liste JSON** stricte au format :

```json
{OUTPUT_FORMAT_SPEC}
```

Règles I/O strictes :
- Une entrée par fiche du chunk d'entrée. Si tu n'arrives pas à rewriter une fiche en respectant les règles, mets `"rewritten_text": null` plutôt que d'omettre l'entrée ou de produire du contenu vide. **Aucune fiche ne doit être manquante** dans la liste output.
- Pas de markdown autour du JSON, pas de commentaires, juste la liste.
- Le `fiche_id` doit être **exactement** le champ `id` de la fiche source (copié verbatim).
- Le `rewritten_text` doit faire entre 80 et 250 mots (cap dur 300), être un paragraphe unique, sans `|`, sans `**`, sans `##`, sans bullets, sans guillemets autour.
- Les chiffres ≥ 100 et les codes officiels (code_rome, code_fap, cs_code, intitule, libelle_metier, etc.) **doivent être préservés** dans le rewritten.

# Étapes à suivre

1. Read({chunk_path}) — récupère la liste des fiches.
2. Pour chaque fiche dans l'ordre, applique les règles R1-R5 et produis son paragraphe.
3. Construis la liste JSON complète au format exigé.
4. Write({results_path}, contenu_JSON).
5. Réponds en une ligne avec : « Done. {{n_fiches}} fiches traitées, {{n_null}} en null. »

Pas d'exploration de répertoires, pas de Grep, pas de questions de clarification : la tâche est entièrement spécifiée par ce prompt et le contenu du fichier chunk."""


def build_agent_prompt_for_chunk(
    chunks_dir: Path, chunk_id: str
) -> tuple[str, Path, Path]:
    """Helper pour construire le prompt + résoudre les paths à partir
    d'un ``chunks_dir`` + ``chunk_id``.

    Returns:
        (prompt, chunk_path, results_path)
    """
    chunks_dir = Path(chunks_dir)
    chunk_path = chunks_dir / f"{chunk_id}.json"
    results_path = chunks_dir / f"{chunk_id}_results.json"
    prompt = build_agent_prompt(chunk_path, results_path, chunk_id=chunk_id)
    return prompt, chunk_path, results_path
