import argparse
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from html import escape

from convert_module import PROJECT_ROOT, CNXML, render


COLLXML = "http://cnx.rice.edu/collxml"

BOOKS = {
    "algebra": {
        "repository": "osbooks-college-algebra-bundle",
        "collection": "college-algebra-2e",
        "title": "College Algebra 2e",
    },
    "precalculus": {
        "repository": "osbooks-college-algebra-bundle",
        "collection": "precalculus-2e",
        "title": "Precalculus 2e",
    },
    "calculus": {
        "repository": "osbooks-calculus-bundle",
        "collection": "calculus-volume-1",
        "title": "Calculus Volume 1",
    },
}


def convert_one(module_id, book, book_root, output_dir, pandoc):
    source = book_root / "modules" / module_id / "index.cnxml"

    root = ET.parse(source).getroot()
    title = root.findtext(f"{{{CNXML}}}title") or module_id
    content = root.find(f"{{{CNXML}}}content")

    if content is None:
        raise ValueError("Content-elementti puuttuu.")

    source_url = (
        f"https://github.com/openstax/{book['repository']}"
        f"/blob/main/modules/{module_id}/index.cnxml"
    )

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        "</head><body>"
        f"<h1>{escape(title)}</h1>"
        f"<p>Source: OpenStax, {escape(book['title'])}</p>"
        f"<p>Module: {module_id}</p>"
        f'<p><a href="{source_url}">Original source</a></p>'
        "<p>License: CC BY-NC-SA 4.0. "
        "Format converted from CNXML; study-skills sections omitted "
        "where present. Images represented by text descriptions.</p>"
        f"{render(content)}"
        "</body></html>"
    )

    html_path = output_dir / f"{module_id}.html"
    markdown_path = output_dir / f"{module_id}.md"

    html_path.write_text(html, encoding="utf-8")

    result = subprocess.run(
        [
            pandoc,
            str(html_path),
            "--from=html",
            "--to=markdown+tex_math_dollars",
            "--wrap=none",
            "--output",
            str(markdown_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.stderr:
        print(f"  Pandoc: {result.stderr.strip()}")

    result.check_returncode()

    return {
        "module_id": module_id,
        "title": title,
        "book": book["title"],
        "file": markdown_path.name,
        "source_url": source_url,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Muunna OpenStax-kirja Markdown + LaTeX -muotoon."
    )
    parser.add_argument(
        "--book",
        choices=BOOKS.keys(),
        default="algebra",
        help="Muunnettava kirja. Oletus: algebra.",
    )
    args = parser.parse_args()

    book = BOOKS[args.book]

    book_root = (
        PROJECT_ROOT
        / "data"
        / "books"
        / "raw"
        / f"{book['repository']}-main"
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "books"
        / "processed"
        / book["collection"]
    )

    collection_path = (
        book_root
        / "collections"
        / f"{book['collection']}.collection.xml"
    )

    pandoc = shutil.which("pandoc")

    if not pandoc:
        raise RuntimeError(
            "Pandoc ei löytynyt. Aktivoi dev-ai-project-ympäristö."
        )

    if not collection_path.exists():
        raise FileNotFoundError(
            f"Kokoelmatiedostoa ei löytynyt: {collection_path}"
        )

    collection = ET.parse(collection_path).getroot()

    module_ids = list(dict.fromkeys(
        element.attrib["document"]
        for element in collection.iter(f"{{{COLLXML}}}module")
    ))

    if not module_ids:
        raise ValueError("Kirjan moduuleja ei löytynyt.")

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    failures = []

    print(f"Kirja: {book['title']}")

    for number, module_id in enumerate(module_ids, start=1):
        try:
            entry = convert_one(
                module_id, book, book_root, output_dir, pandoc
            )
            manifest.append(entry)

            print(
                f"[{number}/{len(module_ids)}] OK "
                f"{module_id}: {entry['title']}"
            )

        except Exception as error:
            failures.append({
                "module_id": module_id,
                "error": str(error),
            })

            print(
                f"[{number}/{len(module_ids)}] VIRHE "
                f"{module_id}: {error}"
            )

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (output_dir / "conversion_errors.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Kirja: {book['title']}")
    print(f"Onnistuneet: {len(manifest)}")
    print(f"Epäonnistuneet: {len(failures)}")
    print(f"Tallennuskansio: {output_dir}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()