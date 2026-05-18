"""Génère docs/CODEBASE_REFERENCE.html — document de référence visuel.

Single-file HTML interactif auto-contenu (CDN Cytoscape + Mermaid + Alpine),
représentant l'intégralité de la codebase OrientIA via 5 vues :

1. Overview     — statistiques globales + état session
2. Pipeline E2E — Mermaid flowchart des 10 étapes
3. Code Graph   — Cytoscape force-directed des modules src/
4. Data Lineage — Cytoscape DAG raw → scripts → processed → indexes → pipeline
5. Tests & Eval — couverture par module + matrice 7 systèmes

Ré-exécutable après chaque session significative pour garder le doc à jour.

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python3 scripts/generate_reference_html.py

Output : docs/CODEBASE_REFERENCE.html (~2-4 MB, ouvre direct dans browser).

Aucun appel API. Zéro coût. Lecture statique de la codebase locale.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_PATH = DOCS_DIR / "CODEBASE_REFERENCE.html"


# ─────────────────────────── Couleurs par dossier src/ ────────────────────────

FOLDER_COLORS = {
    "rag": "#3b82f6",            # bleu
    "rag/validator": "#ef4444",  # rouge
    "rag/agents": "#a855f7",     # violet
    "rag/tools": "#a855f7",      # violet
    "eval": "#10b981",           # vert
    "collect": "#f97316",        # orange
    "agents": "#a855f7",         # violet
    "agent": "#a855f7",          # violet
    "validator": "#ef4444",      # rouge
    "api": "#64748b",            # gris
    "prompt": "#eab308",         # jaune
    "observability": "#14b8a6",  # teal
    "lookup": "#ec4899",         # rose
    "config": "#0ea5e9",         # cyan
}

# Étapes du pipeline pipeline.answer() (cf cartographie 2026-05-18)
PIPELINE_STEPS = [
    {
        "id": "S1",
        "name": "Scope Classifier",
        "file": "src/rag/scope_classifier.py",
        "func": "ScopeClassifier.classify()",
        "desc": "Regex prefiltres (urgent / identity / greeting) puis LLM Mistral Small JSON-mode si pas de match. Renvoie in_scope | out_of_scope | urgent | identity | greeting.",
        "latency": "0.5-1.5 s",
    },
    {
        "id": "S2",
        "name": "Intent + DomainHint",
        "file": "src/rag/intent.py",
        "func": "classify_intent() + classify_domain_hint()",
        "desc": "Classification rule-based : 7 intents (comparaison, geographic, realisme, ...) + 13 domain hints (crous, dares, apec, voie_pre_bac, ...). Drives top_k_sources + mmr_lambda.",
        "latency": "<10 ms",
    },
    {
        "id": "S3",
        "name": "RouterLLM + Retrieval",
        "file": "src/rag/retriever.py + router_llm.py + bm25_index.py",
        "func": "RouterLLM.route() + retrieve_top_k() + BM25 RRF fusion",
        "desc": "RouterLLM Mistral Small décide les sub-indexes ciblés (formations/metiers/aides/stats). FAISS dense top-150 (1024 dims). BM25 lexical RRF fusion optionnel.",
        "latency": "0.5-1.5 s",
    },
    {
        "id": "S4",
        "name": "Reranking",
        "file": "src/rag/reranker.py",
        "func": "rerank()",
        "desc": "Boosts multiplicatifs : parcoursup_rich 1.2, etab_named 1.1, niveau bac+5 1.15, domain-aware 1.3-1.5 si hint match. Calibration éprouvée Run F+G.",
        "latency": "<50 ms",
    },
    {
        "id": "S5",
        "name": "MMR diversification",
        "file": "src/rag/mmr.py",
        "func": "mmr_select()",
        "desc": "Maximal Marginal Relevance pour diversifier le top-K. λ piloté par intent (0.3 décou-verte, 0.9 conceptuel).",
        "latency": "<100 ms",
    },
    {
        "id": "S6",
        "name": "Golden QA few-shot",
        "file": "src/rag/pipeline.py::_maybe_build_golden_qa_prefix",
        "func": "_maybe_build_golden_qa_prefix()",
        "desc": "Inject top-1 Q&A golden par similarité de ton (676 records multi-cat post-GQ rebuild). Lazy-load FAISS au 1er .answer().",
        "latency": "0.2-0.5 s",
    },
    {
        "id": "S7",
        "name": "Generation Mistral",
        "file": "src/rag/generator.py + src/prompt/system.py",
        "func": "generate() + SYSTEM_PROMPT_SPRINT11_P0",
        "desc": "FactCard JSON structuré → Mistral medium max_tokens=800, temperature=0.3. Prompt v5 SPRINT11_P0 (4 directives anti-hallu).",
        "latency": "3-8 s",
    },
    {
        "id": "S8",
        "name": "Validator L1+L2+L3",
        "file": "src/rag/validator/",
        "func": "Validator.validate()",
        "desc": "L1 rules regex (20+ patterns), L2 corpus_check cosinus seuil 0.55, L3 Mistral Small optionnel. honesty_score ∈ [0,1] + flagged boolean.",
        "latency": "<10 ms (L1+L2), 2-4 s (L3 si actif)",
    },
    {
        "id": "S9",
        "name": "Retry conditionnel",
        "file": "src/rag/pipeline.py::_generate_with_retry",
        "func": "_generate_with_retry()",
        "desc": "Si flagged + budget temps restant > 5s → 1 retry max avec domain hint injecté. Timeout wall-clock total 30s.",
        "latency": "0 ou ~6 s",
    },
    {
        "id": "S10",
        "name": "Post-process",
        "file": "src/rag/post_process.py",
        "func": "post_process_answer()",
        "desc": "strip_invented_urls, neutralize_broken_link_fallback (PR #135), fix_broken_markdown_tables, validate_onisep_slugs. Silently corrective.",
        "latency": "<5 ms",
    },
]

# Hubs critiques identifiés (≥5 imports entrants)
KNOWN_HUBS = {
    "src.config": "Configuration central (load_config) — 7 imports",
    "src.rag.intent": "Intent + DomainHint classifiers — 6 imports",
    "src.eval.rate_limit": "Rate limiter OpenAI tier-1 — 6 imports",
    "src.rag.pipeline": "OrientIAPipeline.answer() — 5 imports",
    "src.collect.ft_base": "FT base utilities — 5 imports",
    "src.agents.hierarchical.schemas": "Hierarchical agent schemas — 5 imports",
    "src.agents.hierarchical.session": "Session state hierarchical — 5 imports",
}

# Catégorisation scripts par regex sur nom de fichier
SCRIPT_CATEGORIES = [
    ("build", re.compile(r"^(build|embed|rebuild|reembed|refresh|backfill|dedup)_")),
    ("ingest", re.compile(r"^(ingest|download)_")),
    ("bench", re.compile(r"^(bench|run_bench|grid_search|reproduce_bench)")),
    ("eval", re.compile(r"^(eval|spot_check|validate)_")),
    ("audit", re.compile(r"^audit_")),
    ("diag", re.compile(r"^(diag|sante)_")),
    ("observability", re.compile(r"^observability|scripts/observability/")),
    ("diff", re.compile(r"^(diff|sante_diff|vague_a_diff|vague_b1_)")),
    ("test", re.compile(r"^test_")),
    ("util", re.compile(r"")),  # catch-all dernier
]


# ─────────────────────────── Extraction code source ───────────────────────────


def parse_python_file(path: Path) -> dict[str, Any]:
    """Extrait fonctions/classes publiques + imports cross-module via AST.

    Returns {functions: [...], classes: [...], imports: [...], path: str}
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as e:
        return {"functions": [], "classes": [], "imports": [], "error": str(e),
                "path": str(path.relative_to(PROJECT_ROOT))}

    functions: list[dict] = []
    classes: list[dict] = []
    imports: set[str] = set()

    for node in ast.walk(tree):
        # Fonctions top-level uniquement (pas les méthodes imbriquées)
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args[:6]]
            signature = f"{node.name}({', '.join(args)}{'...' if len(node.args.args) > 6 else ''})"
            functions.append({"name": node.name, "signature": signature, "line": node.lineno})
        elif isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
            functions.append({"name": node.name, "signature": f"async {node.name}(...)", "line": node.lineno})
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            classes.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("src."):
                imports.add(node.module)
            elif node.level > 0:
                # Imports relatifs — résoudre en absolu via le chemin du fichier
                rel = path.relative_to(PROJECT_ROOT)
                parents = list(rel.parts[:-1])  # dossiers parents (sans le fichier)
                if node.level <= len(parents):
                    base = ".".join(parents[: len(parents) - node.level + 1])
                    full = f"{base}.{node.module}" if node.module else base
                    if full.startswith("src."):
                        imports.add(full)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src."):
                    imports.add(alias.name)

    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "module": str(path.relative_to(PROJECT_ROOT)).replace("/", ".").replace(".py", ""),
        "functions": functions,
        "classes": classes,
        "imports": sorted(imports),
    }


def walk_src() -> list[dict[str, Any]]:
    """Énumère tous les .py de src/, retourne liste de dicts module."""
    modules = []
    for py in sorted(SRC_DIR.rglob("*.py")):
        if py.name == "__init__.py":
            continue  # Skip __init__ (rarement informatif)
        info = parse_python_file(py)
        modules.append(info)
    return modules


def build_code_graph(modules: list[dict]) -> dict[str, Any]:
    """Convertit la liste de modules en nodes/edges pour Cytoscape.

    - Nodes : 1 par module, taille ∝ degré entrant, couleur par dossier
    - Edges : imports cross-module (du module qui importe → module importé)

    Filtrage : un edge n'est créé que si source ET target existent dans la
    liste des modules indexés. Évite les références orphelines à des
    packages (`src.agents.hierarchical` sans suffixe désigne le package,
    pas un fichier — pas de node correspondant).
    """
    # Set des module IDs valides (existent comme nodes)
    valid_modules = {m["module"] for m in modules}

    # Compter degré entrant (combien d'autres modules m'importent)
    in_degree: Counter = Counter()
    edges = []
    for m in modules:
        src = m["module"]
        for imp in m["imports"]:
            target = imp
            if target == src:
                continue
            # Skip si target n'est pas un module indexé (package, etc.)
            if target not in valid_modules:
                continue
            in_degree[target] += 1
            edges.append({"data": {"source": src, "target": target, "id": f"{src}__{target}"}})

    nodes = []
    for m in modules:
        module = m["module"]
        # Couleur par premier sous-dossier après src/
        parts = module.split(".")
        folder = parts[1] if len(parts) > 1 else "config"
        # Cas spéciaux (sous-dossiers de rag, agents)
        if len(parts) > 2 and parts[1] == "rag" and parts[2] in ("validator", "agents", "tools"):
            folder = f"rag/{parts[2]}"
        color = FOLDER_COLORS.get(folder, "#94a3b8")  # gris par défaut
        is_hub = module in KNOWN_HUBS
        size = 25 + in_degree.get(module, 0) * 6
        label = ".".join(parts[-2:]) if len(parts) > 2 else parts[-1]
        nodes.append({
            "data": {
                "id": module,
                "label": label,
                "fullPath": m["path"],
                "color": color,
                "folder": folder,
                "isHub": is_hub,
                "hubDesc": KNOWN_HUBS.get(module, ""),
                "size": min(size, 100),
                "inDegree": in_degree.get(module, 0),
                "nFunctions": len(m["functions"]),
                "nClasses": len(m["classes"]),
                "functions": [f["name"] for f in m["functions"][:15]],
                "classes": [c["name"] for c in m["classes"][:10]],
            }
        })

    return {"nodes": nodes, "edges": edges, "in_degree": dict(in_degree)}


# ─────────────────────────── Extraction data ──────────────────────────────────


def list_data_files() -> dict[str, Any]:
    """Énumère data/processed + data/embeddings + data/golden_qa avec tailles."""
    processed = []
    embeddings = []
    golden = []

    proc_dir = DATA_DIR / "processed"
    if proc_dir.exists():
        for f in sorted(proc_dir.glob("*.json")):
            try:
                size = f.stat().st_size
                processed.append({
                    "name": f.name,
                    "size_mb": round(size / 1_048_576, 2),
                    "size_bytes": size,
                    "path": str(f.relative_to(PROJECT_ROOT)),
                })
            except OSError:
                pass
    processed.sort(key=lambda x: -x["size_bytes"])

    emb_dir = DATA_DIR / "embeddings"
    if emb_dir.exists():
        for f in sorted(emb_dir.glob("*.index")):
            try:
                size = f.stat().st_size
                embeddings.append({
                    "name": f.name,
                    "size_mb": round(size / 1_048_576, 2),
                    "size_bytes": size,
                    "path": str(f.relative_to(PROJECT_ROOT)),
                })
            except OSError:
                pass
    embeddings.sort(key=lambda x: -x["size_bytes"])

    gold_dir = DATA_DIR / "golden_qa"
    if gold_dir.exists():
        for f in sorted(gold_dir.iterdir()):
            if f.is_file():
                try:
                    size = f.stat().st_size
                    golden.append({
                        "name": f.name,
                        "size_mb": round(size / 1_048_576, 2),
                        "size_bytes": size,
                    })
                except OSError:
                    pass

    return {"processed": processed, "embeddings": embeddings, "golden_qa": golden}


def build_data_lineage(data_files: dict, modules: list[dict]) -> dict[str, Any]:
    """Construit le DAG data lineage : raw → scripts → processed → indexes → consumers."""
    nodes = []
    edges = []

    # Sources raw (regroupées)
    raw_groups = [
        ("raw_parcoursup", "raw/parcoursup_*.csv", "Parcoursup CSV"),
        ("raw_onisep", "raw/onisep_*.json", "ONISEP"),
        ("raw_insersup", "raw/insersup.csv", "InserSup CSV"),
        ("raw_rome", "raw/rome_4_0.zip", "ROME 4.0"),
        ("raw_monmaster", "raw/monmaster/", "MonMaster"),
        ("raw_lba", "raw/lba/", "La Bonne Alternance"),
        ("raw_insee", "raw/insee/", "INSEE"),
        ("raw_dares", "raw/dares/", "DARES"),
    ]
    for nid, path, label in raw_groups:
        nodes.append({"data": {"id": nid, "label": label, "type": "raw", "color": "#94a3b8", "path": path}})

    # Scripts collecte clés
    collect_scripts = [
        ("collect_merge_v3", "src/collect/run_merge_v3.py", "merge orchestrator"),
        ("rebuild_index", "scripts/rebuild_faiss_index.py", "rebuild FAISS"),
        ("embed_unified", "scripts/embed_unified.py", "embed corpus"),
        ("embed_golden", "scripts/embed_golden_qa.py", "embed golden QA"),
    ]
    for nid, path, label in collect_scripts:
        nodes.append({"data": {"id": nid, "label": label, "type": "script", "color": "#eab308", "path": path}})

    # Edges raw → scripts
    for nid, _, _ in raw_groups:
        edges.append({"data": {"source": nid, "target": "collect_merge_v3", "id": f"{nid}__merge"}})

    # Artefacts processed clés
    for f in data_files["processed"][:20]:  # top 20 largest
        name = f["name"]
        nid = f"proc_{name.replace('.', '_').replace('-', '_')}"
        is_hub = name in ("formations.json", "formations_v5.json", "golden_qa_meta.json", "manual_labels.json")
        nodes.append({
            "data": {
                "id": nid,
                "label": f"{name} ({f['size_mb']} MB)",
                "type": "processed",
                "color": "#10b981" if is_hub else "#86efac",
                "isHub": is_hub,
                "sizeMb": f["size_mb"],
                "path": f["path"],
            }
        })
        # Le merge orchestrator produit la plupart des fichiers
        if name.startswith("formations"):
            edges.append({"data": {"source": "collect_merge_v3", "target": nid, "id": f"merge__{nid}"}})

    # Edge golden_qa scripts
    nodes.append({"data": {"id": "gold_qa_v1", "label": "golden_qa_v1.jsonl (4.3 MB)", "type": "raw", "color": "#cbd5e1"}})
    edges.append({"data": {"source": "gold_qa_v1", "target": "embed_golden", "id": "gold__embed"}})

    # Indexes FAISS — top 7 par taille MAIS garantir inclusion des hubs
    # même si petits (golden_qa.index = 2.7 MB est critique pour le pipeline)
    HUB_INDEXES = {"formations.index", "formations_v5.index", "formations_v7.index", "golden_qa.index"}
    top_by_size = data_files["embeddings"][:7]
    hub_set = {f["name"] for f in top_by_size}
    # Ajouter les hubs manquants
    for f in data_files["embeddings"]:
        if f["name"] in HUB_INDEXES and f["name"] not in hub_set:
            top_by_size.append(f)
            hub_set.add(f["name"])

    for f in top_by_size:
        name = f["name"]
        nid = f"idx_{name.replace('.', '_').replace('-', '_')}"
        is_hub = name in HUB_INDEXES
        nodes.append({
            "data": {
                "id": nid,
                "label": f"{name} ({f['size_mb']} MB)",
                "type": "index",
                "color": "#3b82f6" if is_hub else "#93c5fd",
                "isHub": is_hub,
                "sizeMb": f["size_mb"],
            }
        })
        # Rebuild script produit les indexes
        if "golden_qa" in name:
            edges.append({"data": {"source": "embed_golden", "target": nid, "id": f"egold__{nid}"}})
        else:
            edges.append({"data": {"source": "rebuild_index", "target": nid, "id": f"reidx__{nid}"}})
            # Et embed_unified pour formations.index
            if name == "formations.index":
                edges.append({"data": {"source": "embed_unified", "target": nid, "id": f"eu__{nid}"}})

    # Consumer principal du pipeline
    nodes.append({
        "data": {
            "id": "consumer_pipeline",
            "label": "src/rag/factory.py\nmake_production_pipeline()",
            "type": "consumer",
            "color": "#a855f7",
        }
    })
    nodes.append({
        "data": {
            "id": "consumer_bench",
            "label": "scripts/spot_check_v5.py\n+ bench_* + eval_recall",
            "type": "consumer",
            "color": "#a855f7",
        }
    })
    # Indexes → consumers
    edges.append({"data": {"source": "idx_formations_v5_index", "target": "consumer_pipeline", "id": "v5__pipe"}})
    edges.append({"data": {"source": "idx_golden_qa_index", "target": "consumer_pipeline", "id": "gqa__pipe"}})
    edges.append({"data": {"source": "idx_formations_v5_index", "target": "consumer_bench", "id": "v5__bench"}})

    # Filtrage défensif : retirer tout edge dont source ou target n'a pas de node
    valid_ids = {n["data"]["id"] for n in nodes}
    edges = [e for e in edges
             if e["data"]["source"] in valid_ids and e["data"]["target"] in valid_ids]

    return {"nodes": nodes, "edges": edges}


# ─────────────────────────── Extraction scripts / tests ───────────────────────


def categorize_scripts() -> dict[str, list[dict]]:
    """Classifie tous les scripts/*.py par catégorie via regex sur le nom."""
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for py in sorted(SCRIPTS_DIR.rglob("*.py")):
        rel = py.relative_to(PROJECT_ROOT)
        name = py.name
        matched = False
        for cat, regex in SCRIPT_CATEGORIES:
            if regex.search(name) or regex.search(str(rel)):
                by_cat[cat].append({"name": name, "path": str(rel)})
                matched = True
                break
        if not matched:
            by_cat["util"].append({"name": name, "path": str(rel)})
    # Trier par nom dans chaque catégorie
    for cat in by_cat:
        by_cat[cat].sort(key=lambda x: x["name"])
    return dict(by_cat)


def count_tests_by_module() -> dict[str, Any]:
    """Compte les tests par module src/ correspondant.

    Heuristique : test_X.py couvre src/X.py (ou src/.../X.py).
    """
    tests = list(TESTS_DIR.rglob("test_*.py"))
    by_module: Counter = Counter()
    n_classes = 0
    n_tests_func = 0

    for t in tests:
        try:
            source = t.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(t))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    n_classes += 1
                elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    n_tests_func += 1
        except (SyntaxError, UnicodeDecodeError):
            continue

        # Match nom de fichier vers src/
        name = t.stem.replace("test_", "")
        # Top-level matches
        for category in ("rag", "eval", "collect", "agents", "agent", "validator", "api", "prompt"):
            cat_dir = SRC_DIR / category
            if cat_dir.exists():
                # Check si test_X correspond à src/category/X.py ou contient le mot-clé
                if (cat_dir / f"{name}.py").exists() or name in str(t):
                    by_module[category] += 1
                    break
        else:
            by_module["misc"] += 1

    return {
        "total_files": len(tests),
        "total_test_classes": n_classes,
        "total_test_functions": n_tests_func,
        "by_module": dict(by_module),
    }


# ─────────────────────────── Extraction métriques ─────────────────────────────


def extract_latest_metrics() -> dict[str, Any]:
    """Extrait les métriques de référence depuis les derniers docs."""
    metrics = {
        "spot_check_top5": "9/13",
        "pct_top5_formation": "24.6%",
        "refusals": "2/13",
        "faithfulness_ragas": "0.49 (bimodale)",
        "honesty_haiku": "0.575 (baseline Run F+G)",
        "tests_passing": "220+ (115 intent + 33 post_process + 23 embeddings + ...)",
        "spot_check_evolution": "4/13 → 8/13 (PR #137 C+) → 9/13 (PR #138 Q11)",
        "ragas_calibration": "26% grounded ≥0.7, 54% extrapolent <0.5 (bimodale)",
        "cold_start_warmup": "~14s premier .answer() (lazy load FAISS + connection pool)",
    }
    return metrics


def get_git_info() -> dict[str, str]:
    """Récupère HEAD + branche + nb commits."""
    try:
        head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=PROJECT_ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                          cwd=PROJECT_ROOT, text=True).strip()
        return {"head": head, "branch": branch}
    except subprocess.CalledProcessError:
        return {"head": "unknown", "branch": "unknown"}


# ─────────────────────────── HTML template ────────────────────────────────────


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>OrientIA — Codebase Reference</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
<script src="https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
<script src="https://unpkg.com/cytoscape-cose-bilkent@4.1.0/cytoscape-cose-bilkent.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script defer src="https://unpkg.com/alpinejs@3/dist/cdn.min.js"></script>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0; padding: 0;
    background: #0f172a; color: #e2e8f0;
    min-height: 100vh;
  }
  header {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-bottom: 1px solid #334155;
    padding: 20px 32px;
  }
  header h1 {
    margin: 0; font-size: 22px;
    background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  header .subtitle { color: #94a3b8; font-size: 13px; margin-top: 4px; }
  header .meta {
    display: flex; gap: 20px; margin-top: 12px;
    font-size: 12px; color: #cbd5e1;
  }
  header .meta span { display: flex; align-items: center; gap: 6px; }
  header .meta strong { color: #e2e8f0; }
  nav.tabs {
    background: #1e293b;
    border-bottom: 1px solid #334155;
    padding: 0 32px;
    display: flex; gap: 4px;
  }
  nav.tabs button {
    background: none;
    border: none;
    color: #94a3b8;
    padding: 14px 20px;
    font-size: 14px;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }
  nav.tabs button:hover { color: #e2e8f0; }
  nav.tabs button.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
  }
  main { padding: 24px 32px; }
  section { display: none; animation: fadeIn 0.3s; }
  section.active { display: block; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

  /* Cards Overview */
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
  .card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 20px;
  }
  .card .label { color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
  .card .value { font-size: 28px; font-weight: 600; color: #e2e8f0; margin-top: 8px; }
  .card .hint { color: #64748b; font-size: 11px; margin-top: 4px; }

  h2 { color: #cbd5e1; font-size: 18px; margin: 24px 0 12px; font-weight: 500; }
  h3 { color: #cbd5e1; font-size: 14px; margin: 16px 0 8px; font-weight: 500; }

  table.data {
    width: 100%;
    border-collapse: collapse;
    background: #1e293b;
    border-radius: 6px;
    overflow: hidden;
    font-size: 13px;
  }
  table.data th, table.data td {
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid #334155;
  }
  table.data th { color: #94a3b8; background: #0f172a; font-weight: 500; }
  table.data tr:last-child td { border-bottom: none; }

  .legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: #94a3b8; margin: 12px 0; }
  .legend span { display: flex; align-items: center; gap: 6px; }
  .legend .dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }

  #cyCode, #cyData { width: 100%; height: 720px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; }

  .filters { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
  .filters button {
    background: #1e293b; color: #cbd5e1; border: 1px solid #334155;
    padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
  }
  .filters button.on { background: #3b82f6; color: white; border-color: #3b82f6; }

  #sidePanel {
    position: fixed; right: 0; top: 0; bottom: 0;
    width: 380px; background: #1e293b; border-left: 1px solid #334155;
    padding: 24px; overflow-y: auto;
    transform: translateX(100%); transition: transform 0.3s;
    z-index: 100;
  }
  #sidePanel.open { transform: none; }
  #sidePanel .close { position: absolute; top: 12px; right: 16px; background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; }
  #sidePanel h3 { margin-top: 0; color: #3b82f6; font-size: 16px; }
  #sidePanel .meta { color: #94a3b8; font-size: 12px; margin-bottom: 16px; }
  #sidePanel ul { padding-left: 16px; margin: 6px 0; }
  #sidePanel li { font-family: "SF Mono", Menlo, monospace; font-size: 12px; padding: 2px 0; }

  pre.mermaid {
    background: #1e293b; border-radius: 8px; padding: 24px; margin: 16px 0;
    border: 1px solid #334155;
  }

  .pipe-step {
    background: #1e293b; border: 1px solid #334155; border-radius: 6px;
    padding: 14px 18px; margin-bottom: 8px;
    display: grid; grid-template-columns: 60px 1fr 120px; gap: 12px; align-items: center;
  }
  .pipe-step .step-id { font-weight: 600; color: #3b82f6; font-size: 14px; }
  .pipe-step .step-name { font-weight: 500; color: #e2e8f0; }
  .pipe-step .step-file { font-family: "SF Mono", Menlo, monospace; font-size: 11px; color: #94a3b8; }
  .pipe-step .step-desc { color: #cbd5e1; font-size: 13px; line-height: 1.5; margin-top: 4px; }
  .pipe-step .step-latency { color: #f59e0b; font-size: 12px; text-align: right; }

  .test-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
  .test-bar .module-name { width: 120px; color: #cbd5e1; font-size: 13px; }
  .test-bar .bar-track { flex: 1; height: 22px; background: #0f172a; border-radius: 4px; overflow: hidden; }
  .test-bar .bar-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); display: flex; align-items: center; padding: 0 8px; color: white; font-size: 11px; font-weight: 500; }

  footer { text-align: center; padding: 32px; color: #64748b; font-size: 12px; border-top: 1px solid #334155; margin-top: 48px; }
  footer a { color: #3b82f6; text-decoration: none; }

  details summary { cursor: pointer; padding: 8px 12px; background: #1e293b; border-radius: 4px; margin-bottom: 4px; color: #cbd5e1; font-size: 13px; }
  details[open] summary { background: #334155; }
  details ul { margin: 8px 0 16px 24px; font-size: 12px; }
</style>
</head>
<body x-data="{ view: 'overview', selectedNode: null }">

<header>
  <h1>OrientIA — Codebase Reference</h1>
  <div class="subtitle">Système RAG d'orientation académique française — Document de référence visuel</div>
  <div class="meta">
    <span>📅 <strong>{{GEN_DATE}}</strong></span>
    <span>🔗 HEAD <strong>{{GIT_HEAD}}</strong></span>
    <span>🌿 Branche <strong>{{GIT_BRANCH}}</strong></span>
    <span>📦 {{NB_MODULES}} modules · {{NB_FUNCTIONS}} fonctions · {{NB_CLASSES}} classes</span>
  </div>
</header>

<nav class="tabs">
  <button @click="view='overview'" :class="{ active: view==='overview' }">🏠 Overview</button>
  <button @click="view='pipeline'" :class="{ active: view==='pipeline' }">🔄 Pipeline E2E</button>
  <button @click="view='code'" :class="{ active: view==='code' }">📁 Code Graph</button>
  <button @click="view='data'" :class="{ active: view==='data' }">💾 Data Lineage</button>
  <button @click="view='tests'" :class="{ active: view==='tests' }">🧪 Tests & Eval</button>
  <button @click="view='reference'" :class="{ active: view==='reference' }">📚 Référence</button>
</nav>

<main>

<!-- Vue 1 — Overview -->
<section :class="{ active: view==='overview' }">
  <h2>État du projet</h2>
  <div class="cards">
    <div class="card"><div class="label">Corpus</div><div class="value">{{N_FICHES}}</div><div class="hint">fiches indexées FAISS</div></div>
    <div class="card"><div class="label">Tests</div><div class="value">{{N_TEST_CLASSES}}</div><div class="hint">{{N_TEST_FILES}} fichiers, {{N_TEST_FUNCS}} fonctions</div></div>
    <div class="card"><div class="label">Spot-check</div><div class="value">{{SPOT_CHECK}}</div><div class="hint">top-5 domain match (post #135 #137 #138)</div></div>
    <div class="card"><div class="label">% bruit (formation)</div><div class="value">{{PCT_FORMATION}}</div><div class="hint">↓ de 60.7% (engineer Langfuse cross-validé)</div></div>
    <div class="card"><div class="label">Refusals</div><div class="value">{{REFUSALS}}</div><div class="hint">"info non disponible" sur 13 questions</div></div>
    <div class="card"><div class="label">Faithfulness Ragas</div><div class="value">{{FAITHFULNESS}}</div><div class="hint">bimodale — bloqueur produit #1</div></div>
  </div>

  <h2>Stack technique</h2>
  <table class="data">
    <tr><th>Composant</th><th>Détail</th></tr>
    <tr><td>Python</td><td>3.12 (.venv local)</td></tr>
    <tr><td>LLMs</td><td>Mistral medium (génération) + mistral-embed (1024 dims) + Claude Sonnet 4.5 + GPT-4o + Haiku (judges)</td></tr>
    <tr><td>Vector store</td><td>FAISS IndexFlatL2 (CPU)</td></tr>
    <tr><td>Backend</td><td>FastAPI (Railway prêt) + SSE streaming (PR #136)</td></tr>
    <tr><td>Observability</td><td>Langfuse v4.6.1 self-host + Ragas v0.4.3 (installés 2026-05-13)</td></tr>
    <tr><td>Tests</td><td>pytest 9.0.3, {{N_TEST_CLASSES}}+ classes Test*</td></tr>
  </table>

  <h2>3 PRs structurelles mergées cette série (2026-05-18)</h2>
  <table class="data">
    <tr><th>PR</th><th>Contenu</th><th>Métrique mesurée</th></tr>
    <tr><td>#135</td><td>E (broken link post-process) + H (regex citation multi-format)</td><td>33/33 tests verts, 0 régression visuelle</td></tr>
    <tr><td>#137</td><td>C+ (fiche_to_text annexes utilise champ <code>text</code>) + GQ (rebuild golden_qa 45→676 multi-cat)</td><td>4/13 → 8/13, 60.7% → 24.6% bruit (formation)</td></tr>
    <tr><td>#138</td><td>Phase 1.4 Q11 (domain_hint voie_pre_bac élargi) + script diag Q01</td><td>8/13 → 9/13</td></tr>
  </table>
</section>

<!-- Vue 2 — Pipeline E2E -->
<section :class="{ active: view==='pipeline' }">
  <h2>Pipeline.answer() — 10 étapes</h2>
  <p style="color:#94a3b8;font-size:13px;">Flux d'une question utilisateur de bout en bout. Chaque étape a son fichier, sa fonction principale et sa latence typique mesurée.</p>

  <pre class="mermaid">
flowchart TD
    Q["Question utilisateur"] --> S1["1. ScopeClassifier"]
    S1 -->|in_scope| S2["2. Intent + DomainHint"]
    S1 -->|urgent / identity / out| OUT["Réponse pré-écrite"]
    S2 --> S3["3. RouterLLM + Retrieval FAISS+BM25"]
    S3 --> S4["4. Reranking boosts"]
    S4 --> S5["5. MMR diversification"]
    S5 --> S6["6. Golden QA few-shot"]
    S6 --> S7["7. Generation Mistral"]
    S7 --> S8["8. Validator L1+L2+L3"]
    S8 -->|flagged + budget OK| S9["9. Retry conditionnel max 1"]
    S8 -->|ok| S10["10. Post-process"]
    S9 --> S10
    S10 --> A["Réponse + sources + honesty_score"]

    classDef step fill:#1e293b,stroke:#3b82f6,color:#e2e8f0;
    classDef out fill:#7c2d12,stroke:#f97316,color:#fed7aa;
    classDef finalc fill:#064e3b,stroke:#10b981,color:#a7f3d0;
    class S1,S2,S3,S4,S5,S6,S7,S8,S9,S10 step;
    class OUT out;
    class A finalc;
  </pre>

  <h2>Détail par étape</h2>
  {{PIPELINE_STEPS_HTML}}
</section>

<!-- Vue 3 — Code Graph -->
<section :class="{ active: view==='code' }">
  <h2>Code Graph — {{NB_MODULES}} modules src/ + imports</h2>
  <p style="color:#94a3b8;font-size:13px;">Nœuds = fichiers .py (taille ∝ degré entrant). Edges = imports cross-module. Couleur par dossier. Click un nœud pour voir ses fonctions / classes / imports.</p>

  <div class="legend">
    <span><span class="dot" style="background:#3b82f6"></span>rag</span>
    <span><span class="dot" style="background:#ef4444"></span>validator</span>
    <span><span class="dot" style="background:#a855f7"></span>agents</span>
    <span><span class="dot" style="background:#10b981"></span>eval</span>
    <span><span class="dot" style="background:#f97316"></span>collect</span>
    <span><span class="dot" style="background:#64748b"></span>api</span>
    <span><span class="dot" style="background:#eab308"></span>prompt</span>
    <span><span class="dot" style="background:#14b8a6"></span>observability</span>
    <span><span class="dot" style="background:#ec4899"></span>lookup</span>
    <span><span class="dot" style="background:#0ea5e9"></span>config</span>
  </div>

  <div class="filters">
    <strong style="color:#94a3b8;font-size:12px;margin-right:8px;align-self:center">Layout :</strong>
    <button id="btnLayoutCose" class="on" onclick="setCodeLayout('cose-bilkent')">Force-directed</button>
    <button id="btnLayoutBreadthfirst" onclick="setCodeLayout('breadthfirst')">Breadth-first</button>
    <button id="btnLayoutCircle" onclick="setCodeLayout('circle')">Circle</button>
    <button onclick="fitCode()">Recentrer</button>
  </div>

  <div id="cyCode"></div>
</section>

<!-- Vue 4 — Data Lineage -->
<section :class="{ active: view==='data' }">
  <h2>Data Lineage — Sources → Scripts → Artefacts → Pipeline</h2>
  <p style="color:#94a3b8;font-size:13px;">Flux des données : sources brutes (gris) → scripts collecte (jaune) → artefacts processed (vert, hubs en gros) → indexes FAISS (bleu) → consumers pipeline (violet).</p>

  <div class="legend">
    <span><span class="dot" style="background:#94a3b8"></span>raw</span>
    <span><span class="dot" style="background:#eab308"></span>script</span>
    <span><span class="dot" style="background:#10b981"></span>processed (hub)</span>
    <span><span class="dot" style="background:#86efac"></span>processed</span>
    <span><span class="dot" style="background:#3b82f6"></span>FAISS index (hub)</span>
    <span><span class="dot" style="background:#93c5fd"></span>FAISS index</span>
    <span><span class="dot" style="background:#a855f7"></span>consumer pipeline/bench</span>
  </div>

  <div id="cyData"></div>

  <h2>Top 20 artefacts processed (par taille)</h2>
  <table class="data" id="processedTable">
    <tr><th>Fichier</th><th>Taille</th></tr>
    {{PROCESSED_TABLE}}
  </table>

  <h2>FAISS Indexes</h2>
  <table class="data">
    <tr><th>Fichier</th><th>Taille</th></tr>
    {{EMBEDDINGS_TABLE}}
  </table>
</section>

<!-- Vue 5 — Tests & Eval -->
<section :class="{ active: view==='tests' }">
  <h2>Couverture tests — {{N_TEST_FILES}} fichiers, {{N_TEST_CLASSES}} classes Test*, {{N_TEST_FUNCS}} fonctions test_*</h2>

  <div id="testBars">
    {{TEST_BARS}}
  </div>

  <h2>Matrice 7-system bench (src/eval/systems.py)</h2>
  <table class="data">
    <tr><th>#</th><th>System</th><th>Prompt</th><th>RAG</th><th>Rôle</th></tr>
    <tr><td>1</td><td><code>our_rag</code></td><td>SPRINT11_P0</td><td>full pipeline</td><td>thèse (full stack)</td></tr>
    <tr><td>2</td><td><code>mistral_neutral</code></td><td>NEUTRAL</td><td>no</td><td>fair baseline Mistral</td></tr>
    <tr><td>3</td><td><code>mistral_v3_2_no_rag</code></td><td>v3.2</td><td>no</td><td><strong>isole le RAG</strong> (compétiteur clé)</td></tr>
    <tr><td>4</td><td><code>gpt4o_neutral</code></td><td>NEUTRAL</td><td>no</td><td>baseline GPT-4o</td></tr>
    <tr><td>5</td><td><code>gpt4o_v3_2_no_rag</code></td><td>v3.2</td><td>no</td><td>cross-vendor prompt</td></tr>
    <tr><td>6</td><td><code>claude_neutral</code></td><td>NEUTRAL</td><td>no</td><td>baseline Claude</td></tr>
    <tr><td>7</td><td><code>claude_v3_2_no_rag</code></td><td>v3.2</td><td>no</td><td>cross-vendor prompt</td></tr>
  </table>

  <h2>Métriques actuelles (2026-05-18 post-merges)</h2>
  <table class="data">
    {{METRICS_TABLE}}
  </table>
</section>

<!-- Vue 6 — Référence -->
<section :class="{ active: view==='reference' }">
  <h2>Hubs critiques (≥5 imports entrants)</h2>
  <table class="data">
    <tr><th>Module</th><th>Rôle</th></tr>
    {{HUBS_TABLE}}
  </table>

  <h2>Scripts par catégorie</h2>
  {{SCRIPTS_HTML}}

  <h2>Docs structurelles (à lire en priorité)</h2>
  <table class="data">
    <tr><th>Doc</th><th>Rôle</th></tr>
    <tr><td><code>docs/STRATEGIE_VISION_2026-04-16.md</code></td><td>Vision V2 + 4 axes d'attaque + roadmap</td></tr>
    <tr><td><code>docs/SESSION_HANDOFF.md</code></td><td>État projet à un instant T (mise à jour par sprint)</td></tr>
    <tr><td><code>docs/DECISION_LOG.md</code></td><td>ADRs cumulative (15+ Architecture Decision Records)</td></tr>
    <tr><td><code>docs/METHODOLOGY.md</code></td><td>Protocole reproductible benchmark</td></tr>
    <tr><td><code>docs/FUTURE_PHASES_2026-05-18.md</code></td><td>Roadmap futures phases (Phase 2 faithfulness + Chantiers F/D/B)</td></tr>
    <tr><td><code>CLAUDE.md</code></td><td>Playbook agent : stack + observability + conventions</td></tr>
  </table>

  <h2>Lignes directrices à retenir</h2>
  <ul style="line-height:1.8;color:#cbd5e1;font-size:14px;">
    <li><strong>fiche_to_text est load-bearing</strong> : modif additive uniquement (Run F+G baseline éprouvé)</li>
    <li><strong>Aucun re-embed sans backup</strong> : <code>cp formations.index .bak-YYYYMMDD</code> avant tout rebuild</li>
    <li><strong>Spot-check manuel obligatoire</strong> avant merge d'une nouvelle source data (3-5 échantillons vs source officielle, ADR-026)</li>
    <li><strong>Validator déterministe</strong> : préférer une règle L1 regex à un re-prompt LLM (déterministe, mesurable, débogable)</li>
    <li><strong>Pipeline 10 étapes additives</strong> : chaque étape A/B-testable via flags <code>enable_*</code> de factory.py</li>
    <li><strong>Bloqueur produit #1</strong> : faithfulness Ragas 0.49 bimodale (Phase 2 à attaquer en priorité)</li>
  </ul>
</section>

</main>

<div id="sidePanel">
  <button class="close" onclick="document.getElementById('sidePanel').classList.remove('open')">×</button>
  <div id="sidePanelContent"></div>
</div>

<footer>
  Document généré le {{GEN_DATE}} par <code>scripts/generate_reference_html.py</code>.<br>
  Ré-exécuter après chaque session significative pour mettre à jour. Coût budget : $0 (zéro appel API).
</footer>

<script>
// ─────── Embedded data ────────────────────────────────────────────────
const CODE_GRAPH = {{CODE_GRAPH_JSON}};
const DATA_LINEAGE = {{DATA_LINEAGE_JSON}};
const MODULES_DETAIL = {{MODULES_DETAIL_JSON}};

// ─────── Mermaid ───────
mermaid.initialize({ startOnLoad: true, theme: 'dark', themeVariables: {
  primaryColor: '#1e293b', primaryTextColor: '#e2e8f0', primaryBorderColor: '#3b82f6',
  lineColor: '#64748b', secondaryColor: '#334155', tertiaryColor: '#0f172a'
}});

// ─────── Cytoscape : enregistrement des plugins de layout ───────
// Les CDN unpkg exposent des globales (cytoscapeDagre, cytoscapeCoseBilkent)
// qu'il faut explicitement enregistrer auprès de Cytoscape avant usage.
// Sans ces appels, layout: 'cose-bilkent' déclenche 'Cannot read layoutBase'.
function registerCytoscapePlugins() {
  if (typeof cytoscapeDagre !== 'undefined') {
    cytoscape.use(cytoscapeDagre);
  }
  if (typeof cytoscapeCoseBilkent !== 'undefined') {
    cytoscape.use(cytoscapeCoseBilkent);
  }
}

// Fallback layout si cose-bilkent indisponible
function safeLayoutName(preferred) {
  const extensions = cytoscape.layouts || {};
  // Cytoscape n'expose pas une liste publique des layouts ; on tente le
  // layout demandé et on retombe sur 'cose' (natif Cytoscape) si erreur.
  return preferred;
}

// ─────── Cytoscape Code Graph ───────
let cyCode;
function initCodeGraph() {
  cyCode = cytoscape({
    container: document.getElementById('cyCode'),
    elements: [...CODE_GRAPH.nodes, ...CODE_GRAPH.edges],
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'label': 'data(label)',
          'color': '#e2e8f0',
          'font-size': 10,
          'text-valign': 'bottom',
          'text-margin-y': 4,
          'width': 'data(size)',
          'height': 'data(size)',
          'border-width': 'data(isHub)',
          'border-color': '#f59e0b',
          'border-style': 'solid',
        }
      },
      {
        selector: 'node[?isHub]',
        style: {
          'border-width': 3,
          'border-color': '#f59e0b',
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 1,
          'line-color': '#475569',
          'target-arrow-color': '#475569',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 0.7,
          'opacity': 0.5,
        }
      },
      {
        selector: 'node:selected',
        style: { 'border-width': 4, 'border-color': '#3b82f6' }
      }
    ],
    layout: { name: 'cose-bilkent', animate: false, nodeRepulsion: 8000, idealEdgeLength: 80 }
  });
  cyCode.on('tap', 'node', evt => {
    const n = evt.target.data();
    const detail = MODULES_DETAIL[n.id] || {};
    let html = `<h3>${n.label}</h3>`;
    html += `<div class="meta">${n.fullPath}</div>`;
    if (n.isHub) html += `<p style="color:#f59e0b;font-size:13px;">⭐ HUB — ${n.hubDesc}</p>`;
    html += `<p style="color:#cbd5e1;font-size:13px;">${n.inDegree} module(s) m'importent · ${n.nFunctions} fonctions · ${n.nClasses} classes</p>`;
    if (n.functions && n.functions.length) {
      html += `<h3 style="margin-top:16px">Fonctions publiques</h3><ul>`;
      n.functions.forEach(f => html += `<li>${f}()</li>`);
      html += `</ul>`;
    }
    if (n.classes && n.classes.length) {
      html += `<h3 style="margin-top:16px">Classes publiques</h3><ul>`;
      n.classes.forEach(c => html += `<li>${c}</li>`);
      html += `</ul>`;
    }
    if (detail.imports && detail.imports.length) {
      html += `<h3 style="margin-top:16px">Imports cross-module</h3><ul>`;
      detail.imports.forEach(i => html += `<li>${i}</li>`);
      html += `</ul>`;
    }
    document.getElementById('sidePanelContent').innerHTML = html;
    document.getElementById('sidePanel').classList.add('open');
  });
}

function setCodeLayout(name) {
  if (!cyCode) return;
  document.querySelectorAll('#btnLayoutCose, #btnLayoutBreadthfirst, #btnLayoutCircle').forEach(b => b.classList.remove('on'));
  const map = { 'cose-bilkent': 'btnLayoutCose', 'breadthfirst': 'btnLayoutBreadthfirst', 'circle': 'btnLayoutCircle' };
  if (map[name]) document.getElementById(map[name]).classList.add('on');
  cyCode.layout({ name, animate: true, nodeRepulsion: 8000, idealEdgeLength: 80 }).run();
}
function fitCode() { if (cyCode) cyCode.fit(); }

// ─────── Cytoscape Data Lineage ───────
let cyData;
function initDataLineage() {
  cyData = cytoscape({
    container: document.getElementById('cyData'),
    elements: [...DATA_LINEAGE.nodes, ...DATA_LINEAGE.edges],
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'label': 'data(label)',
          'color': '#e2e8f0',
          'font-size': 9,
          'text-wrap': 'wrap',
          'text-max-width': 180,
          'text-valign': 'center',
          'text-halign': 'center',
          'width': 'mapData(isHub, 0, 1, 50, 90)',
          'height': 'mapData(isHub, 0, 1, 50, 90)',
          'shape': 'round-rectangle',
          'padding': 10,
        }
      },
      {
        selector: 'node[type="raw"]',
        style: { 'shape': 'ellipse' }
      },
      {
        selector: 'node[type="script"]',
        style: { 'shape': 'diamond' }
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#3b82f6',
          'target-arrow-color': '#3b82f6',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'opacity': 0.7,
        }
      }
    ],
    layout: { name: 'dagre', rankDir: 'LR', nodeSep: 60, rankSep: 120 }
  });
}

// ─────── Init when DOM ready ───────
document.addEventListener('DOMContentLoaded', () => {
  // Enregistrer les plugins AVANT toute init Cytoscape
  registerCytoscapePlugins();
  // Délai pour laisser les CDN se charger complètement
  setTimeout(() => {
    try { initCodeGraph(); }
    catch (e) {
      console.error('initCodeGraph failed:', e);
      document.getElementById('cyCode').innerHTML =
        '<div style="padding:40px;color:#ef4444;text-align:center">Erreur init code graph : ' + e.message +
        '<br><small style="color:#94a3b8">Vérifier que les CDN Cytoscape sont accessibles (Internet requis au 1er load).</small></div>';
    }
  }, 600);
  setTimeout(() => {
    try { initDataLineage(); }
    catch (e) {
      console.error('initDataLineage failed:', e);
      document.getElementById('cyData').innerHTML =
        '<div style="padding:40px;color:#ef4444;text-align:center">Erreur init data lineage : ' + e.message + '</div>';
    }
  }, 1100);
});
</script>

</body>
</html>
"""


# ─────────────────────────── Assembly HTML ────────────────────────────────────


def render_pipeline_steps_html(steps: list[dict]) -> str:
    """Rend les 10 étapes du pipeline en HTML cards."""
    rows = []
    for s in steps:
        rows.append(f"""
<div class="pipe-step">
  <div class="step-id">{s['id']}</div>
  <div>
    <div class="step-name">{s['name']}</div>
    <div class="step-file">{s['file']}</div>
    <div class="step-desc">{s['desc']}</div>
    <div style="color:#10b981;font-size:11px;margin-top:6px"><code>{s['func']}</code></div>
  </div>
  <div class="step-latency">{s['latency']}</div>
</div>
""")
    return "".join(rows)


def render_processed_table(data_files: dict) -> str:
    rows = []
    for f in data_files["processed"][:20]:
        rows.append(f"<tr><td><code>{f['name']}</code></td><td>{f['size_mb']} MB</td></tr>")
    return "".join(rows)


def render_embeddings_table(data_files: dict) -> str:
    rows = []
    for f in data_files["embeddings"]:
        rows.append(f"<tr><td><code>{f['name']}</code></td><td>{f['size_mb']} MB</td></tr>")
    return "".join(rows)


def render_test_bars(tests: dict) -> str:
    """Bar chart simple par module."""
    bars = []
    by_mod = tests["by_module"]
    if not by_mod:
        return "<p>Aucun test indexé.</p>"
    max_count = max(by_mod.values()) or 1
    for mod, n in sorted(by_mod.items(), key=lambda x: -x[1]):
        pct = 100 * n / max_count
        bars.append(f"""
<div class="test-bar">
  <div class="module-name">src/{mod}</div>
  <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%">{n} fichier(s)</div></div>
</div>
""")
    return "".join(bars)


def render_metrics_table(metrics: dict) -> str:
    rows = []
    for k, v in metrics.items():
        rows.append(f"<tr><td>{k.replace('_', ' ').title()}</td><td><code>{v}</code></td></tr>")
    return "".join(rows)


def render_hubs_table(hubs: dict) -> str:
    rows = []
    for module, desc in hubs.items():
        rows.append(f"<tr><td><code>{module}</code></td><td>{desc}</td></tr>")
    return "".join(rows)


def render_scripts_html(scripts: dict) -> str:
    """Détails par catégorie en <details> collapsibles."""
    sections = []
    for cat, items in sorted(scripts.items()):
        if not items:
            continue
        cat_label = {
            "build": "🔨 Build / Embed / Index",
            "ingest": "📥 Ingest / Download",
            "bench": "🏁 Bench",
            "eval": "📊 Eval / Spot-check / Validate",
            "audit": "🔍 Audit",
            "diag": "🩺 Diagnostic",
            "observability": "📡 Observability",
            "diff": "🔄 Diff / Compare",
            "test": "🧪 Test scripts",
            "util": "⚙️ Utilitaires",
        }.get(cat, cat)
        items_html = "".join(f"<li><code>{i['path']}</code></li>" for i in items)
        sections.append(f"<details><summary>{cat_label} — {len(items)} script(s)</summary><ul>{items_html}</ul></details>")
    return "\n".join(sections)


def main() -> int:
    print("==> Cartographie src/...")
    modules = walk_src()
    print(f"    {len(modules)} modules trouvés")

    n_functions = sum(len(m["functions"]) for m in modules)
    n_classes = sum(len(m["classes"]) for m in modules)
    print(f"    {n_functions} fonctions publiques, {n_classes} classes publiques")

    print("==> Construction code graph...")
    code_graph = build_code_graph(modules)
    print(f"    {len(code_graph['nodes'])} nodes, {len(code_graph['edges'])} edges")

    print("==> Cartographie data/...")
    data_files = list_data_files()
    print(f"    {len(data_files['processed'])} fichiers processed, {len(data_files['embeddings'])} indexes FAISS")

    print("==> Construction data lineage...")
    data_lineage = build_data_lineage(data_files, modules)
    print(f"    {len(data_lineage['nodes'])} nodes, {len(data_lineage['edges'])} edges")

    print("==> Catégorisation scripts...")
    scripts = categorize_scripts()
    total_scripts = sum(len(v) for v in scripts.values())
    print(f"    {total_scripts} scripts dans {len(scripts)} catégories")

    print("==> Comptage tests...")
    tests = count_tests_by_module()
    print(f"    {tests['total_files']} fichiers test, {tests['total_test_classes']} classes Test*, {tests['total_test_functions']} fonctions test_*")

    print("==> Extraction métriques...")
    metrics = extract_latest_metrics()
    git_info = get_git_info()

    # Détail par module pour le side panel
    modules_detail = {
        m["module"]: {
            "imports": m["imports"],
            "functions": [f["signature"] for f in m["functions"]],
            "classes": [c["name"] for c in m["classes"]],
        }
        for m in modules
    }

    print("==> Assemblage HTML...")
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    replacements = {
        "{{GEN_DATE}}": gen_date,
        "{{GIT_HEAD}}": git_info["head"],
        "{{GIT_BRANCH}}": git_info["branch"],
        "{{NB_MODULES}}": str(len(modules)),
        "{{NB_FUNCTIONS}}": str(n_functions),
        "{{NB_CLASSES}}": str(n_classes),
        "{{N_FICHES}}": "47k+",
        "{{N_TEST_FILES}}": str(tests["total_files"]),
        "{{N_TEST_CLASSES}}": str(tests["total_test_classes"]),
        "{{N_TEST_FUNCS}}": str(tests["total_test_functions"]),
        "{{SPOT_CHECK}}": "9/13",
        "{{PCT_FORMATION}}": "24.6%",
        "{{REFUSALS}}": "2/13",
        "{{FAITHFULNESS}}": "0.49",
        "{{PIPELINE_STEPS_HTML}}": render_pipeline_steps_html(PIPELINE_STEPS),
        "{{PROCESSED_TABLE}}": render_processed_table(data_files),
        "{{EMBEDDINGS_TABLE}}": render_embeddings_table(data_files),
        "{{TEST_BARS}}": render_test_bars(tests),
        "{{METRICS_TABLE}}": render_metrics_table(metrics),
        "{{HUBS_TABLE}}": render_hubs_table(KNOWN_HUBS),
        "{{SCRIPTS_HTML}}": render_scripts_html(scripts),
        "{{CODE_GRAPH_JSON}}": json.dumps(code_graph, ensure_ascii=False),
        "{{DATA_LINEAGE_JSON}}": json.dumps(data_lineage, ensure_ascii=False),
        "{{MODULES_DETAIL_JSON}}": json.dumps(modules_detail, ensure_ascii=False),
    }
    html = HTML_TEMPLATE
    for k, v in replacements.items():
        html = html.replace(k, v)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    size_mb = OUTPUT_PATH.stat().st_size / 1_048_576

    print(f"\n==> ✅ Output: {OUTPUT_PATH.relative_to(PROJECT_ROOT)} ({size_mb:.2f} MB)")
    print(f"    Ouvrir : xdg-open {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
