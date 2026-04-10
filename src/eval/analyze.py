import json
from pathlib import Path
from collections import defaultdict


CRITERIA = ["neutralite", "realisme", "sourcage", "diversite_geo", "agentivite", "decouverte"]


def unblind_scores(blind_scores: list[dict], mapping: dict) -> list[dict]:
    """Reverse the {A,B,C} → system-name randomization.

    Input: [{id, category, scores: {A: {...}, B: {...}, C: {...}}}, ...]
    Mapping: {qid: {A: sysname, B: sysname, C: sysname}}
    Output: [{id, category, systems: {sysname: {...}, sysname: {...}, sysname: {...}}}, ...]

    Drops the `justification` field (free text, not aggregatable).
    """
    unblinded = []
    for entry in blind_scores:
        qid = entry["id"]
        q_map = mapping[qid]
        systems_scores = {}
        for label, score in entry["scores"].items():
            sys_name = q_map[label]
            systems_scores[sys_name] = {k: v for k, v in score.items() if k != "justification"}
        unblinded.append({
            "id": qid,
            "category": entry["category"],
            "systems": systems_scores,
        })
    return unblinded


def aggregate_by_system(unblinded: list[dict]) -> dict:
    """Returns {sysname: {criterion: mean, total: mean}} across all questions."""
    by_sys = defaultdict(lambda: defaultdict(list))
    for entry in unblinded:
        for sys_name, scores in entry["systems"].items():
            for crit in CRITERIA + ["total"]:
                if crit in scores:
                    by_sys[sys_name][crit].append(scores[crit])
    agg = {}
    for sys_name, crits in by_sys.items():
        agg[sys_name] = {crit: sum(vals) / len(vals) for crit, vals in crits.items()}
    return agg


def aggregate_by_category(unblinded: list[dict]) -> dict:
    """Returns {category: {sysname: mean_total}}."""
    by_cat = defaultdict(lambda: defaultdict(list))
    for entry in unblinded:
        cat = entry["category"]
        for sys_name, scores in entry["systems"].items():
            by_cat[cat][sys_name].append(scores.get("total", 0))
    result = {}
    for cat, sys_totals in by_cat.items():
        result[cat] = {s: sum(v) / len(v) for s, v in sys_totals.items()}
    return result


def plot_radar(aggregated: dict, output_path: str | Path) -> None:
    """Save a radar chart comparing systems across the 6 criteria."""
    import matplotlib.pyplot as plt
    import numpy as np

    labels = CRITERIA
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    for sys_name, scores in aggregated.items():
        values = [scores.get(c, 0) for c in labels]
        values += values[:1]
        ax.plot(angles, values, label=sys_name, linewidth=2)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 3)
    ax.set_title("Scores moyens par critère (0-3)", y=1.08)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def main():
    """CLI entry point — runs the full pipeline:
    load blind scores + mapping → unblind → aggregate → save summary + radar."""
    blind_scores_path = Path("results/scores/blind_scores.json")
    mapping_path = Path("results/raw_responses/label_mapping.json")

    if not blind_scores_path.exists():
        raise RuntimeError(f"{blind_scores_path} not found — run `python -m src.eval.run_judge` first")
    if not mapping_path.exists():
        raise RuntimeError(f"{mapping_path} not found — run `python -m src.eval.run_real` first")

    blind_scores = json.loads(blind_scores_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

    unblinded = unblind_scores(blind_scores, mapping)
    by_system = aggregate_by_system(unblinded)
    by_category = aggregate_by_category(unblinded)

    Path("results/scores/unblinded.json").write_text(
        json.dumps(unblinded, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path("results/scores/summary.json").write_text(
        json.dumps({"by_system": by_system, "by_category": by_category}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    plot_radar(by_system, "results/charts/radar_by_system.png")

    print("=== Résultats par système ===")
    for sys_name, scores in by_system.items():
        print(f"\n{sys_name}:")
        for crit in CRITERIA + ["total"]:
            print(f"  {crit:20s} : {scores.get(crit, 0):.2f}")

    print("\n=== Résultats par catégorie (total moyen) ===")
    for cat, sys_scores in by_category.items():
        print(f"\n{cat}:")
        for sys_name, avg in sys_scores.items():
            print(f"  {sys_name:20s} : {avg:.2f}/18")


if __name__ == "__main__":
    main()
