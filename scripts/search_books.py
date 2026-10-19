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


def normalize(text):
    return " ".join(text.casefold().strip().split())


def find_concept(query, concepts):
    """Tunnista taito sen tunnisteesta tai tarkasta nimestä."""
    normalized = normalize(query)

    for concept in concepts:
        names = [
            concept["id"],
            concept["name"],
            concept.get("name_fi", ""),
            concept.get("name_en", ""),
        ]

        if normalized in {
            normalize(name) for name in names if name
        }:
            return concept

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Hae OpenStax-materiaalista lähdetekstejä."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="ketjusääntö",
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

    concepts_file = PROJECT_ROOT / "data" / "concepts.json"
    concepts = json.loads(
        concepts_file.read_text(encoding="utf-8")
    )
    concepts_by_id = {
        concept["id"]: concept for concept in concepts
    }

    if args.concept:
        if args.concept not in concepts_by_id:
            raise ValueError(
                f"Tuntematon taitotunniste: {args.concept}"
            )

        concept = concepts_by_id[args.concept]
    else:
        concept = find_concept(args.query, concepts)

    if concept:
        concept_id = concept["id"]
        english_name = concept.get("name_en") or concept["name"]

        if find_concept(args.query, [concept]):
            search_text = english_name
        else:
            search_text = f"{english_name}. {args.query}"
    else:
        concept_id = None
        search_text = args.query

    if not DATABASE_DIR.exists():
        raise FileNotFoundError(
            "Chroma-tietokanta puuttuu. Aja ensin index_books.py."
        )

    client = chromadb.PersistentClient(path=str(DATABASE_DIR))

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
    )

    count = collection.count()

    if count == 0:
        raise ValueError("Tietokanta on tyhjä.")

    metadata = collection.metadata or {}

    if metadata.get("embedding_model") != MODEL_NAME:
        raise ValueError("Tietokannan hakumalli ei täsmää.")

    print(f"Alkuperäinen haku: {args.query}")
    print(f"Hakumallille annettava teksti: {search_text}")
    print(f"Taitorajaus: {concept_id or 'ei rajausta'}")
    print("Ladataan hakumalli...")

    model = SentenceTransformer(MODEL_NAME, device="cpu")

    query_vector = model.encode(
        ["query: " + search_text],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).tolist()

    # Haetaan ylimääräisiä ehdokkaita, koska osa voidaan
    # jättää pois esimerkiksi irrallisina harjoitusvihjeinä.
    options = {
        "query_embeddings": query_vector,
        "n_results": min(max(args.top * 10, 30), count),
        "include": ["documents", "metadatas", "distances"],
    }

    if concept_id:
        options["where"] = {
            f"skill_{concept_id}": True
        }

    result = collection.query(**options)
    hits = []

    for index, chunk_id in enumerate(result["ids"][0]):
        source = result["metadatas"][0][index]
        text = result["documents"][0][index]
        distance = result["distances"][0][index]

        # Irrallinen vihje ei auta ilman alkuperäistä tehtävää.
        section_title = source.get("section_title", "")
        if normalize(section_title).startswith("hint"):
            continue

        hits.append({
            "id": chunk_id,
            "distance": distance,
            "metadata": source,
            "text": text,
        })

        print()
        print(f"Tulos {len(hits)}")
        print(
            f"{source['book_id']} | "
            f"{source['module_id']} | "
            f"{source['module_title']}"
        )
        print(f"Osio: {section_title}")
        print(f"Etäisyys: {distance:.4f}")
        print(f"Lähde: {source['source_url']}")
        print()
        print(text[:1200])

        if len(text) > 1200:
            print("... [koko teksti tulostiedostossa]")

        if len(hits) >= args.top:
            break

    output = PROJECT_ROOT / "data" / "rag" / "last_search.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(
            {
                "query": args.query,
                "search_text": search_text,
                "concept": concept_id,
                "retrieval_method": (
                    "concept_filtered_vector_search"
                    if concept_id
                    else "vector_search"
                ),
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

    if not hits:
        print("Sopivia tekstipaloja ei löytynyt.")
    elif len(hits) < args.top:
        print("Suodatuksen jälkeen tuloksia jäi pyydettyä vähemmän.")


if __name__ == "__main__":
    main()