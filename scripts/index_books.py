import hashlib
import json
from pathlib import Path
import os

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_FILE = PROJECT_ROOT / "data" / "rag" / "chunks.jsonl"
DATABASE_DIR = (
    Path(os.environ["LOCALAPPDATA"])
    / "dev-ai-project"
    / "chroma"
)

MODEL_NAME = "intfloat/multilingual-e5-small"
COLLECTION_NAME = "openstax_math_e5_v2"
BATCH_SIZE = 32


def embed_documents(model, texts):
    """Muodosta jokaiselle tekstipalalle yksi hakuvektori."""
    windows = []
    owners = []

    for index, text in enumerate(texts):
        # Pitkä teksti käsitellään useassa osassa, jotta sen loppu
        # ei jää mallin pituusrajan vuoksi kokonaan huomioimatta.
        encoded = model.tokenizer(
            text,
            add_special_tokens=False,
            truncation=False,
            return_offsets_mapping=True,
        )
        offsets = encoded["offset_mapping"]

        if not offsets:
            raise ValueError("Tyhjää tekstipalaa ei voi indeksoida.")

        for start in range(0, len(offsets), 400):
            end = min(start + 400, len(offsets))

            first_character = offsets[start][0]
            last_character = offsets[end - 1][1]

            window = text[first_character:last_character]
            windows.append("passage: " + window)
            owners.append(index)

    vectors = model.encode(
        windows,
        batch_size=16,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )

    # Pitkien palojen osavektoreista muodostetaan keskiarvo.
    # Alkuperäinen teksti ja kaavat tallennetaan muuttamattomina.
    combined = np.zeros(
        (len(texts), vectors.shape[1]),
        dtype=np.float32,
    )

    for owner, vector in zip(owners, vectors):
        combined[owner] += vector

    lengths = np.linalg.norm(combined, axis=1, keepdims=True)
    combined /= np.maximum(lengths, 1e-12)

    return combined.tolist()


def make_metadata(chunk):
    metadata = {
        "book_id": chunk["book_id"],
        "module_id": chunk["module_id"],
        "module_title": chunk["module_title"],
        "section_title": chunk["section_title"],
        "source_url": chunk["source_url"],
        "tag_method": chunk["tag_method"],
        "concept_ids": json.dumps(chunk["concept_ids"]),
    }

    # Erilliset kentät mahdollistavat haun rajaamisen taidolla.
    for concept_id in chunk["concept_ids"]:
        metadata[f"skill_{concept_id}"] = True

    return metadata


def main():
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            "chunks.jsonl puuttuu. Aja ensin chunk_books.py."
        )

    raw = CHUNKS_FILE.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()

    chunks = [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]

    if not chunks:
        raise ValueError("Tekstipalojen tiedosto on tyhjä.")

    ids = [chunk["id"] for chunk in chunks]

    if len(ids) != len(set(ids)):
        raise ValueError("Tekstipalojen tunnisteissa on duplikaatteja.")

    print(f"Tekstipaloja: {len(chunks)}")
    print(f"Ladataan hakumalli: {MODEL_NAME}")
    print("Ensimmäinen ajo lataa mallin internetistä.")

    model = SentenceTransformer(MODEL_NAME, device="cpu")

    client = chromadb.PersistentClient(path=str(DATABASE_DIR))

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": MODEL_NAME,
            "chunks_sha256": fingerprint,
        },
    )

    metadata = collection.metadata or {}

    if (
        metadata.get("embedding_model") != MODEL_NAME
        or metadata.get("chunks_sha256") != fingerprint
    ):
        raise ValueError(
            "Tietokanta on luotu eri aineistolla tai hakumallilla. "
            "Indeksi pitää rakentaa uudelleen ennen jatkamista."
        )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]

        embeddings = embed_documents(model, texts)

        # Sama aineisto voidaan ajaa uudelleen ilman duplikaatteja.
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[make_metadata(chunk) for chunk in batch],
        )

        completed = start + len(batch)
        print(f"Tallennettu {completed}/{len(chunks)}")

    count = collection.count()

    if count != len(chunks):
        raise ValueError(
            f"Tallennettujen määrä ei täsmää: {count}/{len(chunks)}"
        )

    print()
    print("Indeksointi valmis.")
    print(f"Chromassa tekstipaloja: {count}")
    print(f"Tietokanta: {DATABASE_DIR}")


if __name__ == "__main__":
    main()