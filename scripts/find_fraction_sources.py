from pathlib import Path
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = (
    PROJECT_ROOT
    / "data/books/raw"
    / "osbooks-college-algebra-bundle-main"
    / "modules"
)

TITLE_TAG = "{http://cnx.rice.edu/cnxml}title"


def main():
    matches = 0

    for path in sorted(MODULES_DIR.glob("*/index.cnxml")):
        root = ET.parse(path).getroot()
        title = root.findtext(TITLE_TAG) or ""

        if any(word in title.casefold() for word in (
            "fraction",
            "rational expression",
            "rational number",
        )):
            print(f"{path.parent.name}: {title}")
            matches += 1

    print(f"\nLöytyneitä moduuleja: {matches}")


if __name__ == "__main__":
    main()