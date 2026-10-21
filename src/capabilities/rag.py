import json
import os
from functools import lru_cache
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import config
from src.schemas.study import Concept, RagChunk


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_NAME = "intfloat/multilingual-e5-small"
COLLECTION_NAME = "openstax_math_e5_v2"

# Sama Windowsin oletussijainti kuin index_books.py:ssä.
DEFAULT_DATABASE_DIR = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache")))
    / "dev-ai-project"
    / "chroma"
)

# Tarvittaessa sijainnin voi määrittää ympäristömuuttujalla.
DATABASE_DIR = Path(
    os.environ.get("RAG_DB_PATH", str(DEFAULT_DATABASE_DIR))
).expanduser()

if not DATABASE_DIR.is_absolute():
    DATABASE_DIR = PROJECT_ROOT / DATABASE_DIR


BOOK_NAMES = {
    "college-algebra-2e": "College Algebra 2e",
    "precalculus-2e": "Precalculus 2e",
    "calculus-volume-1": "Calculus Volume 1",
}


def _read_concept_data():
    """Lue myös kartan lisäkentät, kuten englanninkieliset nimet."""
    path = Path(config.concept_map_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Taitokartan pitää olla JSON-lista.")

    return data


def load_concept_map() -> list[Concept]:
    """Nykyisen AI-palvelun käyttämä taitokartan lukufunktio."""
    return [Concept(**item) for item in _read_concept_data()]


@lru_cache(maxsize=1)
def _get_model():
    """Lataa hakumalli vain kerran sovelluksen ajon aikana."""
    return SentenceTransformer(MODEL_NAME, device="cpu")


@lru_cache(maxsize=1)
def _get_collection():
    """Avaa valmiiksi rakennettu tietokanta."""
    if not (DATABASE_DIR / "chroma.sqlite3").is_file():
        raise FileNotFoundError(
            f"Chroma-tietokantaa ei löytynyt: {DATABASE_DIR}. "
            "Aja ensin scripts/index_books.py."
        )

    client = chromadb.PersistentClient(path=str(DATABASE_DIR))

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
    )

    metadata = collection.metadata or {}

    if metadata.get("embedding_model") != MODEL_NAME:
        raise ValueError(
            "Chroma-tietokanta on rakennettu eri hakumallilla."
        )

    return collection


def retrieve(
    concept_id: str,
    top_k: int = 3,
    query: str | None = None,
) -> list[RagChunk]:
    """
    Hae lähdetekstejä yhdelle taidolle.

    concept_id: concepts.json-tiedoston taitotunniste.
    top_k: palautettavien tekstipalojen enimmäismäärä.
    query: valinnainen tarkentava kysymys taidon sisällä.

    Tyhjä hakutulos palautetaan tyhjänä listana.
    Virheellinen tunniste tai puuttuva tietokanta nostaa virheen.
    """
    if top_k < 1:
        raise ValueError("top_k-arvon pitää olla vähintään 1.")

    concepts = {
        item["id"]: item
        for item in _read_concept_data()
    }

    if concept_id not in concepts:
        raise ValueError(f"Tuntematon taitotunniste: {concept_id}")

    concept = concepts[concept_id]
    english_name = concept.get("name_en") or concept["name"]

    search_text = english_name
    if query and query.strip():
        search_text = f"{english_name}. {query.strip()}"

    collection = _get_collection()
    count = collection.count()

    if count == 0:
        return []

    model = _get_model()
    query_vector = model.encode(
        ["query: " + search_text],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).tolist()

    result = collection.query(
        query_embeddings=query_vector,
        n_results=min(max(top_k * 10, 30), count),
        where={f"skill_{concept_id}": True},
        include=["documents", "metadatas", "distances"],
    )

    chunks = []

    for index, chunk_id in enumerate(result["ids"][0]):
        metadata = result["metadatas"][0][index]
        text = result["documents"][0][index]
        distance = float(result["distances"][0][index])

        section_title = metadata.get("section_title", "")

        # Irrallinen harjoitusvihje tarvitsee alkuperäisen tehtävän.
        if section_title.strip().casefold().startswith("hint"):
            continue

        if not text or not text.strip():
            continue

        book_id = metadata["book_id"]
        module_title = metadata["module_title"]

        section = module_title
        if section_title and section_title != module_title:
            section = f"{module_title} — {section_title}"

        chunks.append(
            RagChunk(
                id=chunk_id,
                concept_id=concept_id,
                text=text,
                book=BOOK_NAMES.get(book_id, book_id),
                section=section,
                # Kosinisamankaltaisuus, ei oikeellisuuden
                # todennäköisyys. Suurempi tarkoittaa lähempää.
                score=max(-1.0, min(1.0, 1.0 - distance)),
                source_url=metadata.get("source_url", ""),
            )
        )

        if len(chunks) >= top_k:
            break

    return chunks