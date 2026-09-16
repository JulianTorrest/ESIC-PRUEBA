import json
import time
from pathlib import Path

from data_generator import main as generate_data
from vector_store import DATA_FILE, get_vector_store


def precargar():
    print("Generando datos dummies...")
    generate_data()

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"No se encontró {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Datos cargados: {data.get('total_registros', 0)} registros")

    for store_name in ["Chroma", "FAISS", "SQLite"]:
        print(f"Precargando base vectorial {store_name}...")
        start = time.time()
        store = get_vector_store(store_name, force_reindex=True)
        elapsed = time.time() - start
        print(f"{store_name} lista en {elapsed:.2f}s")

    print("Precarga completada. Puedes iniciar Streamlit ahora:")
    print("streamlit run streamlit_app.py")


if __name__ == "__main__":
    precargar()
