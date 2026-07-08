"""Report which class / attribute / association names in each config did NOT
receive a `sourceUri` after the batch annotation pass. Read-only — does not
modify any config."""
import json
import sys
from pathlib import Path

CFG_DIR = Path(r"C:\GithubC\CDIF\ucmism2m\configuration")
sys.path.insert(0, str(Path(__file__).parent))
from _uri_lookup import resolve_uri, resolve_class_uri

SKIP = {"ddi-cdi2ddsc_mapping.json"}


def _role_variants(target_assoc_name: str) -> list:
    if not target_assoc_name:
        return []
    parts = target_assoc_name.split("_")
    if len(parts) < 3:
        return []
    remaining = parts[1:]
    variants = ["_".join(remaining)]
    if len(remaining) > 1:
        variants.append("_".join(remaining[:-1]))
    return variants


def report_config(cfg_path: Path):
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    profile = cfg_path.stem.replace("ddi-cdi2", "").replace("_mapping", "")
    unresolved_classes = []
    unresolved_attrs = []  # list of (class, attr)
    unresolved_assocs = []  # list of (subjectClass, targetAssocName)

    for cls in cfg.get("mapping", {}).get("class") or []:
        tc = cls.get("targetClass")
        if not tc:
            continue
        if not resolve_class_uri(tc):
            unresolved_classes.append(tc)
        for attr in cls.get("attribute") or []:
            aname = attr.get("name")
            if not aname:
                continue
            if not resolve_uri(profile, tc, aname):
                unresolved_attrs.append((tc, aname))

    for assoc in cfg.get("mapping", {}).get("association") or []:
        tan = assoc.get("targetAssociationName") or ""
        subject_class = assoc.get("subjectClass") or (tan.split("_", 1)[0] if tan else "")
        variants = _role_variants(tan)
        hit = ""
        for role in variants:
            u = resolve_uri(profile, subject_class, role)
            if u:
                hit = u
                break
        if not hit:
            display_role = variants[0] if variants else ""
            unresolved_assocs.append((subject_class, tan or "(no name)", display_role))

    if not (unresolved_classes or unresolved_attrs or unresolved_assocs):
        return
    print(f"\n=== {cfg_path.name} ===")
    if unresolved_classes:
        print(f"  Classes ({len(unresolved_classes)}):")
        for c in unresolved_classes:
            print(f"    - {c}")
    if unresolved_attrs:
        print(f"  Attributes ({len(unresolved_attrs)}):")
        # group by class
        by_cls = {}
        for c, a in unresolved_attrs:
            by_cls.setdefault(c, []).append(a)
        for c, attrs in by_cls.items():
            print(f"    {c}: {', '.join(attrs)}")
    if unresolved_assocs:
        print(f"  Associations ({len(unresolved_assocs)}):")
        for subj, tan, role in unresolved_assocs:
            print(f"    - {subj} :: {tan}  (role='{role}')")


def main():
    for cfg_path in sorted(CFG_DIR.glob("ddi-cdi2*.json")):
        if cfg_path.name in SKIP:
            continue
        report_config(cfg_path)


if __name__ == "__main__":
    main()
