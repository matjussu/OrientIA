from dataclasses import dataclass


@dataclass(frozen=True)
class RerankConfig:
    # Label boosts — the primary INRIA-thesis innovation
    secnumedu_boost: float = 1.5
    cti_boost: float = 1.3
    grade_master_boost: float = 1.3
    public_boost: float = 1.1
    # Niveau boosts — secondary correction for BTS dominance in Parcoursup data
    # Intentionally kept below label boosts so they don't dominate.
    level_boost_bac5: float = 1.15
    level_boost_bac3: float = 1.05

    def as_dict(self) -> dict:
        return {
            "secnumedu_boost": self.secnumedu_boost,
            "cti_boost": self.cti_boost,
            "grade_master_boost": self.grade_master_boost,
            "public_boost": self.public_boost,
            "level_boost_bac5": self.level_boost_bac5,
            "level_boost_bac3": self.level_boost_bac3,
        }


def rerank(results: list[dict], config: RerankConfig) -> list[dict]:
    reranked = []
    for r in results:
        fiche = r["fiche"]
        score = r["base_score"]
        labels = fiche.get("labels") or []

        # Stage A: label boosts (primary)
        if "SecNumEdu" in labels:
            score *= config.secnumedu_boost
        if "CTI" in labels:
            score *= config.cti_boost
        if "Grade Master" in labels:
            score *= config.grade_master_boost
        if fiche.get("statut") == "Public":
            score *= config.public_boost

        # Stage B: niveau boosts (secondary)
        niveau = fiche.get("niveau")
        if niveau == "bac+5":
            score *= config.level_boost_bac5
        elif niveau == "bac+3":
            score *= config.level_boost_bac3
        # bac+2 and None get no boost (implicit 1.0 multiplier)

        new = dict(r)
        new["score"] = score
        reranked.append(new)

    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked
