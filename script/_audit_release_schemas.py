"""Audit the v1.1 generated XMIs against the release-repo *StructuredSchema.json
files (NOT the mBB resolvedSchema.json files). Reuses the buckets / policy from
audit_schema_vs_uml.py — only the schema source path is swapped.

The release schemas live in sibling repos C:/GithubC/CDIF/profile-<name>/.
ConceptScheme has no ucmism2m config + no XMI yet, so it's reported as
"no UML at all"."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[1]  # .../CDIF
CONFIG_DIR = REPO / "ucmism2m" / "configuration"
GENERATED_DIR = REPO / "ucmism2m" / "generated"

# Re-use audit_schema_vs_uml internals
sys.path.insert(0, str(SCRIPT_DIR))
from audit_schema_vs_uml import (  # noqa: E402
    UNION_POLICY, ALIASES, DATATYPE_POLICY, GENERIC_PROPS,
    extract_schema, covered_from_config, covered_from_xmi, canon, classify,
)

sys.path.insert(0, str(REPO / "metadataBuildingBlocks" / "tools"))
from uml_to_schema import _load_with_composition  # noqa: E402

# 6 release profiles: (label, config or None, release schema path, expected XMI slug or None)
PROFILES = [
    ("Core",
     CONFIG_DIR / "ddi-cdi2cdifCore_mapping.json",
     REPO / "profile-core" / "cdifCoreStructuredSchema.json"),
    ("Discovery",
     CONFIG_DIR / "ddi-cdi2cdifDiscovery_mapping.json",
     REPO / "profile-discovery" / "cdifDiscoveryStructuredSchema.json"),
    ("DataDescription",
     CONFIG_DIR / "ddi-cdi2cdifDataDescription_mapping.json",
     REPO / "profile-datadescription" / "cdifDataDescriptionStructuredSchema.json"),
    ("DataStructure",
     CONFIG_DIR / "ddi-cdi2cdifDataStructure_mapping.json",
     REPO / "profile-datastructure" / "cdifDataStructureStructuredSchema.json"),
    ("Codelist",
     CONFIG_DIR / "ddi-cdi2cdifCodelist_mapping.json",
     REPO / "profile-codelist" / "CDIFCodelistProfileStructuredSchema.json"),
    ("ConceptScheme",
     CONFIG_DIR / "ddi-cdi2cdifConceptScheme_mapping.json",
     REPO / "profile-conceptscheme" / "cdifConceptSchemeStructuredSchema.json"),
]


def audit_release(label, cfg_path, schema_path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    props, classes = set(), set()
    extract_schema(schema, props, classes)

    if cfg_path is None:
        return {
            "label": label,
            "no_uml": True,
            "n_props": len(props), "n_classes": len(classes),
            "props": sorted(props, key=str.lower),
            "classes": sorted(classes, key=str.lower),
        }

    cfg, _ = _load_with_composition(cfg_path)
    tm = cfg["transformation"]["targetModel"]
    xmi_name = f"{tm['acronym'].lower()}_{tm['majorVersion']}-{tm['minorVersion']}_canonical-unique-names.xmi"
    covered = covered_from_config(cfg) | covered_from_xmi(GENERATED_DIR / xmi_name)

    def bucketize(names, drop_generic=False):
        buckets = {"gap": [], "vocabulary": [], "datatype": [], "union": []}
        for name in names:
            if drop_generic and canon(name) in GENERIC_PROPS:
                continue
            b = classify(name, covered)
            if b == "covered":
                continue
            buckets[b].append(name)
        for v in buckets.values():
            v.sort(key=str.lower)
        return buckets

    return {
        "label": label,
        "xmi": xmi_name,
        "covered": len(covered),
        "classes": bucketize(classes),
        "props": bucketize(props, drop_generic=True),
    }


def main():
    print(f"Auditing v1.1 XMIs in {GENERATED_DIR} against release schemas in C:/GithubC/CDIF/profile-*/\n")
    for label, cfg_path, schema_path in PROFILES:
        print(f"==================== {label} ====================")
        if not schema_path.exists():
            print(f"  ! release schema not found: {schema_path}")
            continue
        r = audit_release(label, cfg_path, schema_path)
        if r.get("no_uml"):
            print(f"  ! NO UML AT ALL for {label}.")
            print(f"    No ucmism2m config; no XMI in generated/.")
            print(f"    Release schema has {r['n_classes']} $defs/types and {r['n_props']} properties.")
            print(f"    A complete XMI requires a new ucmism2m config + regen.")
            continue
        cg, pg = r["classes"], r["props"]
        print(f"  XMI: {r['xmi']}")
        print(f"  REAL GAPS - classes/types in release schema with no UML class ({len(cg['gap'])}):")
        for c in cg["gap"]:
            print(f"      - {c}")
        print(f"  REAL GAPS - properties in release schema with no UML attribute/association ({len(pg['gap'])}):")
        for p in pg["gap"]:
            print(f"      - {p}")
        print(f"  (intentionally absent - union policy: {len(cg['union']) + len(pg['union'])}, "
              f"datatype/xsd policy: {len(cg['datatype']) + len(pg['datatype'])}, "
              f"SKOS vocabulary: {len(cg['vocabulary']) + len(pg['vocabulary'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
