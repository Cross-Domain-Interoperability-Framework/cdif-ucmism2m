#!/usr/bin/env python3
"""Survey CDIF profile resolvedSchema.json files for properties whose value
can be one of several types (anyOf / oneOf / array-typed type).

Reports each (path, type-set) it finds, then a histogram of the distinct
type-set shapes. Helps decide a UML representation policy for union-style
properties when the source schema admits multiple shapes (e.g. string OR
schema:DefinedTerm OR @id-reference).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "metadataBuildingBlocks" / "_sources" / "profiles" / "cdifCompositeProfile"

# Tag a sub-schema with a short type label, suitable for grouping.
def describe(schema: dict, defs: dict, depth: int = 0) -> str:
    if not isinstance(schema, dict):
        return "?"
    if depth > 6:
        return "..."
    # Direct $ref
    if "$ref" in schema:
        ref = schema["$ref"]
        # Resolve local "#/$defs/X" only; foreign refs returned by name.
        if ref.startswith("#/$defs/"):
            name = ref.split("/")[-1]
            resolved = defs.get(name)
            if resolved is not None:
                inner = describe(resolved, defs, depth + 1)
                return f"#{name}({inner})" if inner not in (name, "?", "object") else f"#{name}"
            return f"#{name}"
        # External ref — keep the file basename
        m = re.search(r"/([A-Za-z0-9_-]+)/schema\.yaml", ref)
        if m:
            return f"@{m.group(1)}"
        return f"@{ref.rsplit('/', 1)[-1]}"
    # If schema has @type contains const, surface that
    if "properties" in schema:
        at = schema["properties"].get("@type")
        if isinstance(at, dict) and isinstance(at.get("contains"), dict):
            const = at["contains"].get("const")
            if const:
                return f"object<{const}>"
        # @id-only ref pattern
        keys = set(schema["properties"].keys())
        if keys == {"@id"} or (keys <= {"@id", "@type"} and schema.get("required") == ["@id"]):
            return "@id-ref"
    t = schema.get("type")
    if isinstance(t, list):
        return "|".join(t)
    if t:
        if t == "object":
            return "object"
        if t == "array":
            inner = describe(schema.get("items", {}), defs, depth + 1)
            return f"array<{inner}>"
        return t
    if "enum" in schema:
        return f"enum({len(schema['enum'])})"
    if "const" in schema:
        return f"const"
    return "?"


def walk(node, path: list[str], defs: dict, sink: list[tuple[str, tuple[str, ...]]]):
    if isinstance(node, dict):
        # Check for union shapes at this node
        for key in ("anyOf", "oneOf"):
            arr = node.get(key)
            if isinstance(arr, list) and len(arr) > 1:
                types = tuple(sorted({describe(item, defs) for item in arr}))
                # Skip pure schema-org polymorphism artifacts where one option
                # is just an @id-ref alongside an inline object — that's the
                # JSON-LD reference-or-inline pattern, not a union of distinct
                # *value types*. But still record it if interesting.
                sink.append((".".join(path) or "<root>", types))
        # Recurse into common containers
        for k in ("properties", "patternProperties", "$defs", "definitions"):
            sub = node.get(k)
            if isinstance(sub, dict):
                for pk, pv in sub.items():
                    walk(pv, path + [k, pk], defs, sink)
        for k in ("items", "additionalItems", "additionalProperties",
                  "if", "then", "else", "not"):
            sub = node.get(k)
            if isinstance(sub, dict):
                walk(sub, path + [k], defs, sink)
        for k in ("allOf",):
            arr = node.get(k)
            if isinstance(arr, list):
                for i, item in enumerate(arr):
                    walk(item, path + [f"{k}[{i}]"], defs, sink)
        # anyOf/oneOf were recorded above; still recurse into them so nested
        # union props inside an inline option are found.
        for k in ("anyOf", "oneOf"):
            arr = node.get(k)
            if isinstance(arr, list):
                for i, item in enumerate(arr):
                    walk(item, path + [f"{k}[{i}]"], defs, sink)


def survey(profile_path: Path) -> tuple[list, Counter]:
    schema_path = profile_path / "resolvedSchema.json"
    if not schema_path.exists():
        return [], Counter()
    with open(schema_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    defs = doc.get("$defs", {}) or doc.get("definitions", {}) or {}
    sink = []
    walk(doc, [], defs, sink)
    hist = Counter(types for _path, types in sink)
    return sink, hist


def main() -> int:
    if not ROOT.exists():
        print(f"ERROR: profile dir not found: {ROOT}", file=sys.stderr)
        return 2
    total = Counter()
    by_profile = {}
    for prof in sorted(ROOT.iterdir()):
        if not prof.is_dir():
            continue
        sink, hist = survey(prof)
        if not sink:
            continue
        by_profile[prof.name] = (sink, hist)
        total += hist

    print("=" * 78)
    print("UNION-TYPE PROPERTY SHAPES across CDIF profile resolvedSchema.json files")
    print("=" * 78)
    print()
    for prof_name, (sink, hist) in by_profile.items():
        print(f"\n## {prof_name}  ({len(sink)} union-shape occurrences)")
        print("-" * 78)
        for types, n in hist.most_common():
            print(f"  {n:3d}  {' | '.join(types)}")

    print()
    print("=" * 78)
    print(f"COMBINED HISTOGRAM ({sum(total.values())} occurrences across {len(by_profile)} profiles)")
    print("=" * 78)
    for types, n in total.most_common():
        print(f"  {n:3d}  {' | '.join(types)}")

    # Sample paths for each distinct shape, taken from the first profile that has it.
    print()
    print("=" * 78)
    print("SAMPLE PROPERTY PATHS for each distinct shape (one example per shape)")
    print("=" * 78)
    seen = set()
    for prof_name, (sink, _hist) in by_profile.items():
        for path, types in sink:
            if types in seen:
                continue
            seen.add(types)
            print(f"\n  shape: {' | '.join(types)}")
            print(f"    {prof_name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
