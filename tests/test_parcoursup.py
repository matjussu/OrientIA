import pandas as pd
from src.collect.parcoursup import load_parcoursup, filter_domain, DOMAIN_KEYWORDS


def test_domain_keywords_defined():
    assert "cyber" in DOMAIN_KEYWORDS
    assert "data_ia" in DOMAIN_KEYWORDS
    assert any("cybersécurité" in kw.lower() or "cyber" in kw.lower()
               for kw in DOMAIN_KEYWORDS["cyber"])
    assert any("data" in kw.lower() or "intelligence artificielle" in kw.lower()
               for kw in DOMAIN_KEYWORDS["data_ia"])


def test_filter_domain_keeps_cyber_entries():
    df = pd.DataFrame({
        "formation": [
            "Master Cybersécurité",
            "Licence Histoire",
            "BUT Informatique parcours cyber",
            "BTS Comptabilité",
        ]
    })
    filtered = filter_domain(df, "cyber", name_column="formation")
    assert len(filtered) == 2
    assert "Histoire" not in filtered["formation"].values
