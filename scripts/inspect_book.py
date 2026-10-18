from pathlib import Path
import xml.etree.ElementTree as ET

# Projektin juuri päätellään tämän skriptin sijainnista.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

BOOK_ROOT = (
    PROJECT_ROOT
    / "data/books/raw/osbooks-college-algebra-bundle-main"
)
COLLECTION = BOOK_ROOT / "collections/college-algebra-2e.collection.xml"
OUTPUT = PROJECT_ROOT / "data/books/processed/college-algebra-2e-toc.md"

NS = {
    "col": "http://cnx.rice.edu/collxml",
    "md": "http://cnx.rice.edu/mdml",
    "cnx": "http://cnx.rice.edu/cnxml",
    "m": "http://www.w3.org/1998/Math/MathML",
}


def main():
    collection = ET.parse(COLLECTION).getroot()
    book_title = collection.findtext("col:metadata/md:title", namespaces=NS)
    lines = [f"# {book_title}", ""]
    module_count = 0
    missing_count = 0

    def walk(content):
        nonlocal module_count, missing_count

        for item in content:
            if item.tag == f"{{{NS['col']}}}subcollection":
                title = item.findtext("md:title", namespaces=NS)
                lines.extend([f"## {title}", ""])
                nested = item.find("col:content", NS)
                if nested is not None:
                    walk(nested)

            elif item.tag == f"{{{NS['col']}}}module":
                module_id = item.attrib["document"]
                source = BOOK_ROOT / "modules" / module_id / "index.cnxml"

                if not source.is_file():
                    missing_count += 1
                    lines.append(f"- MISSING: {module_id}")
                    continue

                module = ET.parse(source).getroot()
                title = module.findtext("cnx:title", namespaces=NS)
                math_count = len(module.findall(".//m:math", NS))

                lines.append(
                    f"- {title} | {module_id} | MathML: {math_count}"
                )
                module_count += 1

    content = collection.find("col:content", NS)
    if content is None:
        raise ValueError("Kirjan sisältörakennetta ei löytynyt.")

    walk(content)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Modules read: {module_count}")
    print(f"Missing modules: {missing_count}")
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()