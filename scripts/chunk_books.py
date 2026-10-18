import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONCEPTS_FILE = PROJECT_ROOT / "data" / "concepts.json"
BOOKS_DIR = PROJECT_ROOT / "data" / "books" / "processed"
OUTPUT_FILE = PROJECT_ROOT / "data" / "rag" / "chunks.jsonl"

# Tavoitekoko merkkeinä. Yksittäistä pitkää kappaletta tai kaavaa
# ei katkaista väkisin.
TARGET_SIZE = 2500


def paragraphs(text):
    """Erottele kappaleet säilyttäen moniriviset $$-kaavat."""
    buffer = []
    inside_math = False

    for line in text.splitlines():
        if not line.strip() and not inside_math:
            if buffer:
                yield "\n".join(buffer).strip()
                buffer = []
            continue

        buffer.append(line)

        if line.count("$$") % 2:
            inside_math = not inside_math

    if buffer:
        yield "\n".join(buffer).strip()


def split_sections(text):
    """Jaa moduuli Markdown-otsikoiden kohdalta."""
    heading = ""
    buffer = []
    inside_math = False

    for line in text.splitlines():
        if not inside_math and re.match(r"^#{1,6}\s+", line):
            if buffer:
                yield heading, "\n".join(buffer)
            heading = re.sub(r"^#{1,6}\s+", "", line).strip()
            buffer = []
        else:
            buffer.append(line)

        if line.count("$$") % 2:
            inside_math = not inside_math

    if buffer:
        yield heading, "\n".join(buffer)


def make_chunks(text):
    """Yhdistä kokonaisia kappaleita tavoitekoon mukaan."""
    buffer = []
    size = 0

    for paragraph in paragraphs(text):
        if buffer and size + len(paragraph) + 2 > TARGET_SIZE:
            yield "\n\n".join(buffer)
            buffer = []
            size = 0

        buffer.append(paragraph)
        size += len(paragraph) + 2

    if buffer:
        yield "\n\n".join(buffer)


def main():
    concepts = json.loads(CONCEPTS_FILE.read_text(encoding="utf-8"))

    # Yksi lähdemoduuli voi liittyä useaan taitoon.
    modules = {}

    for concept in concepts:
        for source in concept.get("sources", []):
            key = (source["book_id"], source["module_id"])

            if key not in modules:
                modules[key] = {
                    "source": source,
                    "concept_ids": [],
                }

            if concept["id"] not in modules[key]["concept_ids"]:
                modules[key]["concept_ids"].append(concept["id"])

    if not modules:
        raise ValueError("Taitokartasta ei löytynyt lähdemoduuleja.")

    chunks = []
    missing = []

    for (book_id, module_id), entry in sorted(modules.items()):
        source = entry["source"]
        path = BOOKS_DIR / book_id / f"{module_id}.md"

        if not path.exists():
            missing.append(str(path))
            continue

        text = path.read_text(encoding="utf-8")

        # Ohitetaan muunnosskriptin lisäämät lähdetietorivit.
        # Samat tiedot tulevat jokaisen palan metadataan.
        text = re.sub(
            r"^(?:Source:|Module:|License:|\[Original source\]).*$",
            "",
            text,
            flags=re.MULTILINE,
        )

        number = 0

        for heading, section in split_sections(text):
            for body in make_chunks(section):
                if not body.strip():
                    continue

                number += 1

                chunks.append({
                    "id": f"{book_id}:{module_id}:{number:04d}",
                    "text": (
                        f"# {source['module_title']}\n\n"
                        f"## {heading}\n\n{body}"
                        if heading != source["module_title"]
                        else f"# {heading}\n\n{body}"
                    ),
                    "book_id": book_id,
                    "module_id": module_id,
                    "module_title": source["module_title"],
                    "section_title": heading,
                    "concept_ids": entry["concept_ids"],
                    "tag_method": "module_mapping",
                    "source_url": source["source_url"],
                })

    # Puuttuvia lähteitä ei ohiteta huomaamatta.
    if missing:
        raise FileNotFoundError(
            "Seuraavat lähdetiedostot puuttuvat:\n"
            + "\n".join(missing)
        )

    if not chunks:
        raise ValueError("Tekstipaloja ei syntynyt.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    chain_chunks = [
        chunk
        for chunk in chunks
        if "chain_rule" in chunk["concept_ids"]
    ]

    print(f"Taitoja: {len(concepts)}")
    print(f"Lähdemoduuleja: {len(modules)}")
    print(f"Tekstipaloja: {len(chunks)}")
    print(f"Ketjusääntöön liittyviä paloja: {len(chain_chunks)}")
    print(f"Tallennettu: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()