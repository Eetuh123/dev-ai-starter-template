import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from html import escape

from convert_module import BOOK_ROOT, OUTPUT_DIR, CNXML, render


COLLECTION = (
    BOOK_ROOT
    / "collections"
    / "college-algebra-2e.collection.xml"
)

COLLXML = "http://cnx.rice.edu/collxml"


def convert_one(module_id, pandoc):
    source = BOOK_ROOT / "modules" / module_id / "index.cnxml"

    root = ET.parse(source).getroot()
    title = root.findtext(f"{{{CNXML}}}title") or module_id
    content = root.find(f"{{{CNXML}}}content")

    if content is None:
        raise ValueError("Content-elementti puuttuu.")

    source_url = (
        "https://github.com/openstax/"
        "osbooks-college-algebra-bundle/"
        f"blob/main/modules/{module_id}/index.cnxml"
    )

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        "</head><body>"
        f"<h1>{escape(title)}</h1>"
        "<p>Source: OpenStax, College Algebra 2e</p>"
        f"<p>Module: {module_id}</p>"
        f'<p><a href="{source_url}">Original source</a></p>'
        "<p>License: CC BY-NC-SA 4.0. "
        "Format converted from CNXML; study-skills sections omitted "
        "where present. Images represented by text descriptions.</p>"
        f"{render(content)}"
        "</body></html>"
    )

    html_path = OUTPUT_DIR / f"{module_id}.html"
    markdown_path = OUTPUT_DIR / f"{module_id}.md"

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
        "book": "College Algebra 2e",
        "file": markdown_path.name,
        "source_url": source_url,
    }


def main():
    pandoc = shutil.which("pandoc")

    if not pandoc:
        raise RuntimeError(
            "Pandoc ei löytynyt. Aktivoi dev-ai-project-ympäristö."
        )

    collection = ET.parse(COLLECTION).getroot()

    # Luetaan vain tähän kirjaan kuuluvat moduulit.
    # Poistetaan mahdolliset duplikaatit säilyttäen järjestys.
    module_ids = list(dict.fromkeys(
        element.attrib["document"]
        for element in collection.iter(f"{{{COLLXML}}}module")
    ))

    if not module_ids:
        raise ValueError("Kirjan moduuleja ei löytynyt.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    failures = []

    for number, module_id in enumerate(module_ids, start=1):
        try:
            entry = convert_one(module_id, pandoc)
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

    # Lähdetiedot myöhempää pilkkomista ja hakua varten.
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    failure_path = OUTPUT_DIR / "conversion_errors.json"
    failure_path.write_text(
        json.dumps(failures, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Onnistuneet: {len(manifest)}")
    print(f"Epäonnistuneet: {len(failures)}")
    print(f"Tallennuskansio: {OUTPUT_DIR}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()