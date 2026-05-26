#!/usr/bin/env python3
"""One-shot path remap to align ucmism2m text references with the
metadataBuildingBlocks profile reorg (2026-05).

See the docstring inline below for the mappings (kept out of the rewrite
patterns so this script doesn't transform its own description).

Only rewrites text content (descriptive _comment / definition fields and
documentation). Does NOT touch UML transformations.
"""
from pathlib import Path
import re

REPO = Path(__file__).resolve().parent.parent

MOVED_TO_PROFILE = {
    "cdifCore", "cdifCodelist", "cdifDataDescription",
    "cdifDataStructure", "cdifArchive", "cdifProvenance",
}
COMPOSITE_RENAMES = {
    "CDIFDiscoveryProfile": "BasicDiscovery",
    "CDIFDataDescriptionProfile": "BasicDataDescription",
    "CDIFDataStructureProfile": "DataDescriptionWithStructure",
    "CDIFxasProfile": "XASdata",
    "CDIFcompleteProfile": "cdifComplete",
    "CDIFCodelistProfile": "_ARCHIVED_",
}

TARGET_GLOBS = [
    "configuration/*.json",
    "documentation/*.md",
    "documentation/*.html",
    "README.md",
    "AGENTS.md",
    "workflowDescription.md",
    # script/*.py intentionally excluded after first run so we don't
    # rewrite our own docstrings.
]


def remap(text: str) -> str:
    def sub_props(m):
        bb = m.group(1)
        if bb in MOVED_TO_PROFILE:
            return f"profiles/cdifProfile/{bb}"
        return f"cdifDataType/{bb}"

    text = re.sub(
        r"cdifProperties/([A-Za-z][A-Za-z0-9_]*)",
        sub_props, text,
    )

    def sub_composite(m):
        old = m.group(1)
        new = COMPOSITE_RENAMES.get(old)
        if new == "_ARCHIVED_":
            return f"profiles/archive/{old}"
        if new:
            return f"profiles/cdifCompositeProfile/{new}"
        return m.group(0)

    text = re.sub(
        r"profiles/cdifProfiles/([A-Za-z][A-Za-z0-9_]*)",
        sub_composite, text,
    )

    # Bare directory token without trailing path segment.
    text = re.sub(r"(?<![A-Za-z/])cdif" r"Properties(?![A-Za-z0-9/])",
                  "cdifDataType", text)

    return text


def main():
    changed = []
    for pat in TARGET_GLOBS:
        for p in REPO.glob(pat):
            if not p.is_file():
                continue
            try:
                orig = p.read_text(encoding="utf-8")
            except Exception:
                continue
            new = remap(orig)
            if new != orig:
                p.write_text(new, encoding="utf-8")
                changed.append(p.relative_to(REPO).as_posix())
    print(f"Rewrote {len(changed)} files:")
    for c in changed:
        print(f"  {c}")


if __name__ == "__main__":
    main()
