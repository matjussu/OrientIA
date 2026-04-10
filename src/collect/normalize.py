import re
import unicodedata


_STOPWORDS = {"de", "du", "des", "la", "le", "les", "d", "l"}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _clean(text: str) -> str:
    text = _strip_accents(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_name(text: str) -> str:
    cleaned = _clean(text)
    tokens = [t for t in cleaned.split() if t not in _STOPWORDS]
    return " ".join(tokens)


def normalize_city(text: str) -> str:
    return _clean(text)
