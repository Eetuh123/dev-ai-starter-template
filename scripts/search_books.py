import argparse
import json

import chromadb
from sentence_transformers import SentenceTransformer

from index_books import (
    PROJECT_ROOT,
    DATABASE_DIR,
    MODEL_NAME,
    COLLECTION_NAME,
)


def main():
    parser = argparse.ArgumentParser(
        description="Hae OpenStax-materiaalista lähdetekstejä."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="ketjusääntö",
        help="Hakusana tai kysymys.",
    )
    parser.add_argument(
        "--concept",
        help="Valinnainen taitotunniste, esimerkiksi chain_rule.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Palautettavien tekstipalojen määrä.",
    )
    args = parser.parse_args()

    if not args.query.strip():
        parser.error("Hakuteksti ei saa olla tyhjä.")

    if args.top < 1:
        parser.error("--top-arvon pitää olla vähintään 1.")

    if not DATABASE_DIR.exists():
        raise FileNotFoundError(
            "Chroma-tietokanta puuttuu. Aja ensin index_books.py."
        )

    client = chromadb.PersistentClient(path=str(DATABASE_DIR))

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
    )

    if collection.count() == 0:
        raise ValueError("Tietokanta on tyhjä.")

    metadata = collection.metadata or {}

    if metadata.get("embedding_model") != MODEL_NAME:
        raise ValueError("Tietokannan hakumalli ei vastaa skriptin mallia.")

    if args.concept:
        concepts_file = PROJECT_ROOT / "data" / "concepts.json"
        concepts = json.loads(
            concepts_file.read_text(encoding="utf-8")
        )
        known_ids = {concept["id"] for concept in concepts}

        if args.concept not in known_ids:
            raise ValueError(
                f"Tuntematon taitotunniste: {args.concept}"
            )

    print(f"Haku: {args.query}")
    print(f"Taitorajaus: {args.concept or 'ei rajausta'}")
    print("Ladataan hakumalli...")

    model = SentenceTransformer(MODEL_NAME, device="cpu")

    query_vector = model.encode(
        ["query: " + args.query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).tolist()

    options = {
        "query_embeddings": query_vector,
        "n_results": min(args.top, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }

    if args.concept:
        options["where"] = {
            f"skill_{args.concept}": True
        }

    result = collection.query(**options)

    hits = []

    for index, chunk_id in enumerate(result["ids"][0]):
        source = result["metadatas"][0][index]
        text = result["documents"][0][index]
        distance = result["distances"][0][index]

        hits.append({
            "id": chunk_id,
            "distance": distance,
            "metadata": source,
            "text": text,
        })

        print()
        print(f"Tulos {index + 1}")
        print(
            f"{source['book_id']} | "
            f"{source['module_id']} | "
            f"{source['module_title']}"
        )
        print(f"Osio: {source['section_title']}")
        print(f"Etäisyys: {distance:.4f} (pienempi on lähempänä)")
        print(f"Lähde: {source['source_url']}")
        print()
        print(text[:1200])

        if len(text) > 1200:
            print("... [koko teksti tulostiedostossa]")

    output = PROJECT_ROOT / "data" / "rag" / "last_search.json"

    output.write_text(
        json.dumps(
            {
                "query": args.query,
                "concept": args.concept,
                "results": hits,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Tuloksia: {len(hits)}")
    print(f"Kokonaiset hakutulokset: {output}")


if __name__ == "__main__":
    main()