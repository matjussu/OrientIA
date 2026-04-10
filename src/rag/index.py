from pathlib import Path
import faiss
import numpy as np


def build_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
    if embeddings.dtype != np.float32:
        embeddings = embeddings.astype("float32")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def save_index(index: faiss.IndexFlatL2, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))


def load_index(path: str | Path) -> faiss.IndexFlatL2:
    return faiss.read_index(str(path))
