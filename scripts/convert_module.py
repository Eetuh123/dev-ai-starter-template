from pathlib import Path
from html import escape
import copy
import shutil
import subprocess
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BOOK_ROOT = (
    PROJECT_ROOT
    / "data"
    / "books"
    / "raw"
    / "osbooks-college-algebra-bundle-main"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "books"
    / "processed"
    / "college-algebra-2e"
)

# Muunnetaan aluksi yksi kappale.
MODULE_ID = "m51239"

CNXML = "http://cnx.rice.edu/cnxml"
MATHML = "http://www.w3.org/1998/Math/MathML"


def local_name(element):
    """Palauttaa XML-tagin nimen ilman nimiavaruutta."""
    return element.tag.split("}")[-1]


def render(element, level=1):
    """Muuntaa CNXML-elementin HTML-muotoon."""
    tag = local_name(element)

    # Jätetään opiskelutapakysely pois matematiikan materiaalista.
    classes = element.get("class", "").split()
    if "coreq-skills" in classes:
        return ""

    # Säilytetään kaava MathML-muodossa Pandocia varten.
    if element.tag == f"{{{MATHML}}}math":
        math = copy.deepcopy(element)
        math.tail = None

        for node in math.iter():
            node.tag = local_name(node)

        return ET.tostring(math, encoding="unicode")

    def children(child_level=level):
        result = escape(element.text or "")

        for child in element:
            result += render(child, child_level)
            result += escape(child.tail or "")

        return result

    if tag == "section":
        return children(level + 1)

    if tag == "title":
        heading = min(max(level, 2), 6)
        return f"<h{heading}>{children()}</h{heading}>"

    if tag == "list":
        list_tag = (
            "ol"
            if element.get("list-type") == "enumerated"
            else "ul"
        )
        return f"<{list_tag}>{children()}</{list_tag}>"

    if tag == "emphasis":
        emphasis = (
            "em"
            if element.get("effect") == "italics"
            else "strong"
        )
        return f"<{emphasis}>{children()}</{emphasis}>"

    if tag == "equation":
        equation = copy.deepcopy(element)

        for math in equation.iter(f"{{{MATHML}}}math"):
            math.set("display", "block")

        return (
            escape(equation.text or "")
            + "".join(
                render(child, level) + escape(child.tail or "")
                for child in equation
            )
        )

    # Kuvat korvataan niiden tekstikuvauksilla.
    if tag == "media":
        description = element.get("alt") or "Image in original source"
        return f"<p>[Image: {escape(description)}]</p>"

    if tag in {"image", "colspec"}:
        return ""

    if tag == "newline":
        return "<br>"

    if tag == "link":
        text = children()
        target = element.get("url")

        if target:
            return (
                f'<a href="{escape(target, quote=True)}">'
                f"{text or escape(target)}</a>"
            )

        reference = (
            element.get("target-id")
            or element.get("document")
            or ""
        )

        return text or escape(f"[Reference: {reference}]")

    if tag in {
        "example",
        "exercise",
        "problem",
        "solution",
        "note",
        "definition",
    }:
        label = escape(tag.capitalize())
        identifier = escape(element.get("id", ""))

        return (
            f"<p><strong>{label}</strong> {identifier}</p>"
            f"{children()}"
        )

    html_tags = {
        "para": "p",
        "item": "li",
        "table": "table",
        "thead": "thead",
        "tbody": "tbody",
        "row": "tr",
        "entry": "td",
        "caption": "p",
        "label": "strong",
        "term": "strong",
        "sup": "sup",
        "sub": "sub",
        "span": "span",
    }

    if tag in html_tags:
        html_tag = html_tags[tag]
        return f"<{html_tag}>{children()}</{html_tag}>"

    # Muiden elementtien sisältämä teksti säilytetään.
    return children()


def main():
    pandoc = shutil.which("pandoc")

    if not pandoc:
        raise RuntimeError(
            "Pandoc ei löytynyt. Aja skripti aktivoidussa "
            "dev-ai-project-ympäristössä."
        )

    source = BOOK_ROOT / "modules" / MODULE_ID / "index.cnxml"

    if not source.exists():
        raise FileNotFoundError(
            f"Lähdetiedostoa ei löytynyt: {source}"
        )

    root = ET.parse(source).getroot()

    title = root.findtext(f"{{{CNXML}}}title") or MODULE_ID
    content = root.find(f"{{{CNXML}}}content")

    if content is None:
        raise ValueError("Moduulista ei löytynyt content-elementtiä.")

    source_url = (
        "https://github.com/openstax/"
        "osbooks-college-algebra-bundle/"
        f"blob/main/modules/{MODULE_ID}/index.cnxml"
    )

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        "</head><body>"
        f"<h1>{escape(title)}</h1>"
        "<p>Source: OpenStax, College Algebra 2e</p>"
        f"<p>Module: {MODULE_ID}</p>"
        f'<p><a href="{source_url}">Original source</a></p>'
        "<p>License: CC BY-NC-SA 4.0. "
        "Format converted from CNXML; study-skills section omitted. "
        "Images represented by text descriptions.</p>"
        f"{render(content)}"
        "</body></html>"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html_path = OUTPUT_DIR / f"{MODULE_ID}.html"
    markdown_path = OUTPUT_DIR / f"{MODULE_ID}.md"

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
        print("Pandocin ilmoitukset:")
        print(result.stderr)

    result.check_returncode()

    print(f"Kappale: {title}")
    print(f"HTML: {html_path}")
    print(f"Markdown: {markdown_path}")
    print("Muunnos valmis.")


if __name__ == "__main__":
    main()