import json
from pathlib import Path


def load_secnumedu(path: str | Path) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    fiches = []
    for entry in raw:
        fiches.append({
            "source": "secnumedu",
            "domaine": "cyber",
            "nom": entry["nom"],
            "etablissement": entry["etablissement"],
            "ville": entry.get("ville", ""),
            "rncp": entry.get("rncp"),
            "labels": ["SecNumEdu"],
        })
    return fiches
