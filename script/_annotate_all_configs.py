"""Batch annotator: write `sourceUri` fields into every mapping config for
each class / attribute / association based on the lookup tables in
`_uri_lookup.py`.

Also bumps each config's `$schema` reference from v1.1 to v1.2 (v1.2 declares
the new `sourceUri` and `cdifBookUri` fields).

Skips:
  - `ddi-cdi2ddsc_mapping.json` (not a CDIF profile)
  - `ddi-cdi2cdifCodelist_mapping.json` (already annotated manually)
  - Any element whose resolved URI is empty (leaves the field off, per policy
    for CDIF-native terms with no upstream source).

Reports per-config counts of {classes, attrs, assocs} that received a URI
and the total number left un-annotated (empty URI resolution).
"""
import argparse
import json
import re
import sys
from pathlib import Path

CFG_DIR = Path(r"C:\GithubC\CDIF\ucmism2m\configuration")
sys.path.insert(0, str(Path(__file__).parent))
from _uri_lookup import resolve_uri, resolve_class_uri

SKIP = {"ddi-cdi2ddsc_mapping.json", "ddi-cdi2cdifCodelist_mapping.json"}
SCHEMA_OLD = "ucmis_mapping_configuration.schema.v1.1.json"
SCHEMA_NEW = "ucmis_mapping_configuration.schema.v1.2.json"

# Set by CLI --force: when True, existing sourceUri values are overwritten by
# the resolved value from the lookup tables. Default False (setdefault behavior)
# so hand-edited values are preserved.
FORCE = False


def _set_uri(container, key, value):
    if FORCE or key not in container:
        container[key] = value


def _role_variants(target_assoc_name: str) -> list:
    """Return role candidates to try in order (most specific first).

    For `Subject_role_Target`, tries:
      1. `role_Target` — the full trailing form (matches target-qualified URIs
         like `cdi:has_Statistics` or `cdif:has_CategoryStatistics`).
      2. `role`        — the short form (matches generic `cdi:has`).

    Returns [] if the name doesn't have at least Subject_role_Target shape."""
    if not target_assoc_name:
        return []
    parts = target_assoc_name.split("_")
    if len(parts) < 3:
        return []
    remaining = parts[1:]                # drop the subject
    variants = ["_".join(remaining)]     # full form: role[_..]_Target
    if len(remaining) > 1:
        variants.append("_".join(remaining[:-1]))  # drop the trailing target class
    return variants


def annotate_config(cfg_path: Path) -> dict:
    """Annotate one config; return counts."""
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    profile = cfg_path.stem.replace("ddi-cdi2", "").replace("_mapping", "")

    counts = {
        "classes_annotated": 0, "classes_skipped": 0,
        "attrs_annotated": 0, "attrs_skipped": 0,
        "assocs_annotated": 0, "assocs_skipped": 0,
    }

    for cls in cfg.get("mapping", {}).get("class") or []:
        tc = cls.get("targetClass")
        if not tc:
            continue
        uri = resolve_class_uri(tc)
        if uri:
            _set_uri(cls, "sourceUri", uri)
            counts["classes_annotated"] += 1
        else:
            counts["classes_skipped"] += 1
        for attr in cls.get("attribute") or []:
            aname = attr.get("name")
            if not aname:
                continue
            uri = resolve_uri(profile, tc, aname)
            if uri:
                _set_uri(attr, "sourceUri", uri)
                counts["attrs_annotated"] += 1
            else:
                counts["attrs_skipped"] += 1

    for assoc in cfg.get("mapping", {}).get("association") or []:
        tan = assoc.get("targetAssociationName") or ""
        subject_class = assoc.get("subjectClass") or (tan.split("_", 1)[0] if tan else "")
        uri = ""
        for role in _role_variants(tan):
            uri = resolve_uri(profile, subject_class, role)
            if uri:
                break
        if uri:
            _set_uri(assoc, "sourceUri", uri)
            counts["assocs_annotated"] += 1
        else:
            counts["assocs_skipped"] += 1

    # Bump $schema reference (in-place)
    if cfg.get("$schema") == SCHEMA_OLD:
        cfg["$schema"] = SCHEMA_NEW
        counts["schema_bumped"] = True
    else:
        counts["schema_bumped"] = False

    cfg_path.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return counts


def main():
    global FORCE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing sourceUri values with the lookup result")
    ns = ap.parse_args()
    FORCE = ns.force
    if FORCE:
        print("(--force: existing sourceUri values will be overwritten)")
    print(f"{'CONFIG':50s}  {'CLS OK/SK':>10s}  {'ATTR OK/SK':>12s}  {'ASSC OK/SK':>12s}  {'SCHEMA':>6s}")
    print("=" * 100)
    for cfg_path in sorted(CFG_DIR.glob("ddi-cdi2*.json")):
        if cfg_path.name in SKIP:
            print(f"  SKIP  {cfg_path.name}")
            continue
        c = annotate_config(cfg_path)
        print(
            f"{cfg_path.name:50s}  "
            f"{c['classes_annotated']:>4d}/{c['classes_skipped']:>4d}  "
            f"{c['attrs_annotated']:>5d}/{c['attrs_skipped']:>5d}  "
            f"{c['assocs_annotated']:>5d}/{c['assocs_skipped']:>5d}  "
            f"{'v1.2' if c['schema_bumped'] else '-':>6s}"
        )


if __name__ == "__main__":
    main()
