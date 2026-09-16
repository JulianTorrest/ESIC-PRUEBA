import json
import sqlite3
import uuid
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "dummy_data.json"

CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"
SQLITE_DB = DATA_DIR / "vector_sqlite.db"


class EmbeddingModel:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)


embedder = EmbeddingModel()


def load_dummy_data() -> List[Dict[str, Any]]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for category, items in data.items():
        if category == "total_registros":
            continue
        for item in items:
            text = " ".join([f"{k}: {v}" for k, v in item.items() if not isinstance(v, dict)])
            docs.append({
                "id": item.get("id", str(uuid.uuid4())),
                "category": category,
                "content": text,
                "metadata": item,
            })
    return docs


def _doc_to_text(doc: Dict) -> str:
    return doc["content"]


def _flatten_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Aplana metadatos para ChromaDB (solo str, int, float, bool)."""
    flat = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            flat[key] = value
        elif isinstance(value, list):
            flat[key] = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (str, int, float, bool)):
                    flat[f"{key}_{sub_key}"] = sub_value
                else:
                    flat[f"{key}_{sub_key}"] = json.dumps(sub_value, ensure_ascii=False)
        else:
            flat[key] = str(value)
    return flat


class SQLiteVectorStore:
    def __init__(self):
        self.db_path = SQLITE_DB
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                category TEXT,
                content TEXT,
                embedding BLOB,
                metadata TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def index(self, docs: List[Dict]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents")
        contents = [_doc_to_text(d) for d in docs]
        embeddings = embedder.encode(contents)
        for doc, emb in zip(docs, embeddings):
            cursor.execute(
                "INSERT OR REPLACE INTO documents (id, category, content, embedding, metadata) VALUES (?, ?, ?, ?, ?)",
                (doc["id"], doc["category"], doc["content"], emb.tobytes(), json.dumps(doc["metadata"], ensure_ascii=False)),
            )
        conn.commit()
        conn.close()

    def is_indexed(self) -> bool:
        if not self.db_path.exists():
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def search(self, query: str, k: int = 4) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query_emb = embedder.encode([query])
        cursor.execute("SELECT id, category, content, embedding, metadata FROM documents")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        embeddings = np.array([np.frombuffer(row[3], dtype=np.float32) for row in rows])
        similarities = self._cosine_similarity(query_emb[0], embeddings)
        top_k = np.argsort(similarities)[-k:][::-1]

        results = []
        for idx in top_k:
            row = rows[idx]
            results.append({
                "id": row[0],
                "category": row[1],
                "content": row[2],
                "metadata": json.loads(row[4]),
                "score": float(similarities[idx]),
            })
        return results

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_norm = a / (np.linalg.norm(a) + 1e-10)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
        return np.dot(b_norm, a_norm)


class ChromaVectorStore:
    def __init__(self):
        import chromadb
        self.client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        self.collection = self.client.get_or_create_collection(name="esic_knowledge")

    def index(self, docs: List[Dict]):
        self.collection.delete(where={"source": "dummy_data"})
        ids = [doc["id"] for doc in docs]
        contents = [_doc_to_text(d) for d in docs]
        embeddings = embedder.encode(contents).tolist()
        metadatas = []
        for d in docs:
            flat = _flatten_metadata(d["metadata"])
            metadatas.append({"category": d["category"], **flat})
        self.collection.add(ids=ids, documents=contents, embeddings=embeddings, metadatas=metadatas)

    def is_indexed(self) -> bool:
        try:
            return self.collection.count() > 0
        except Exception:
            return False

    def search(self, query: str, k: int = 4) -> List[Dict]:
        query_emb = embedder.encode([query]).tolist()
        results = self.collection.query(query_embeddings=query_emb, n_results=k)
        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["ids"][0][i],
                "category": results["metadatas"][0][i].get("category", "general"),
                "content": results["documents"][0][i],
                "metadata": {k: v for k, v in results["metadatas"][0][i].items() if k != "category"},
                "score": float(results["distances"][0][i]) if results["distances"] else 0.0,
            })
        return items


class FAISSVectorStore:
    def __init__(self):
        self.index_dir = FAISS_INDEX_DIR
        self.index_file = self.index_dir / "faiss.index"
        self.mapping_file = self.index_dir / "mapping.json"
        self._docs: List[Dict] = []
        self._index = None

    def _init_index(self, dim: int):
        import faiss
        self._index = faiss.IndexFlatIP(dim)

    def index(self, docs: List[Dict]):
        self._docs = docs
        contents = [_doc_to_text(d) for d in docs]
        embeddings = embedder.encode(contents)
        embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)
        self._init_index(embeddings.shape[1])
        self._index.add(embeddings.astype("float32"))
        self.index_dir.mkdir(parents=True, exist_ok=True)
        import faiss
        faiss.write_index(self._index, str(self.index_file))
        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump([{"id": d["id"], "category": d["category"], "metadata": d["metadata"]} for d in docs], f, ensure_ascii=False)

    def is_indexed(self) -> bool:
        return self.index_file.exists() and self.mapping_file.exists()

    def search(self, query: str, k: int = 4) -> List[Dict]:
        import faiss
        if self._index is None and self.index_file.exists():
            self._index = faiss.read_index(str(self.index_file))
            with open(self.mapping_file, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            self._docs = [
                {
                    "id": m["id"],
                    "category": m["category"],
                    "content": self._content_from_metadata(m["metadata"]),
                    "metadata": m["metadata"],
                }
                for m in mapping
            ]
        if self._index is None:
            return []

        query_emb = embedder.encode([query])
        query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-10)
        scores, indices = self._index.search(query_emb.astype("float32"), k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._docs):
                continue
            doc = self._docs[idx]
            doc["content"] = self._content_from_metadata(doc["metadata"])
            doc["score"] = float(score)
            results.append(doc)
        return results

    @staticmethod
    def _content_from_metadata(metadata: Dict) -> str:
        return " ".join([f"{k}: {v}" for k, v in metadata.items() if not isinstance(v, (dict, list))])


STORES = {
    "Chroma": ChromaVectorStore,
    "FAISS": FAISSVectorStore,
    "SQLite": SQLiteVectorStore,
}


def get_vector_store(name: str, force_reindex: bool = False):
    if name not in STORES:
        raise ValueError(f"Vector store {name} no soportado. Opciones: {list(STORES.keys())}")
    store = STORES[name]()
    if not force_reindex and store.is_indexed():
        return store
    docs = load_dummy_data()
    store.index(docs)
    return store
