#!/usr/bin/env python3
"""Audit: compare each CDIF Core UML config class to its building-block
RESOLVED property set (resolvedProperties.json, $refs already inlined).
Accounts for config attributes AND associations AND inheritance. Read-only."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "metadataBuildingBlocks"
CFG = Path(__file__).resolve().parents[1] / "configuration" / "ddi-cdi2cdifCore_mapping.json"

# Core UML class -> BB folder (under annotated/bbr/metadata). None = synthesized.
CLASS_BB = {
    "Dataset": "profiles/cdifProfile/cdifCore",
    "AbstractDistribution": None,
    "DataDownload": "schemaorgProperties/dataDownload",
    "WebAPI": "schemaorgProperties/webAPI",
    "Agent": None,
    "Person": "schemaorgProperties/person",
    "ContactPoint": None,
    "Organization": "schemaorgProperties/organization",
    "Contributor": "schemaorgProperties/agentInRole",
    "DefinedTerm": "schemaorgProperties/definedTerm",
    "Identifier": "schemaorgProperties/identifier",
    "AdditionalProperty": "schemaorgProperties/additionalProperty",
    "Reference": "cdifDataType/cdifReference",
    "MonetaryGrant": "schemaorgProperties/monetaryGrant",
    "ProvActivity": "provProperties/generatedBy",
    "DerivedFrom": "provProperties/derivedFrom",
    "CatalogRecord": "cdifDataType/cdifCatalogRecord",
}
SKIP = {"@id", "@type", "@context"}

def bare(n): return n.split(":")[-1]

def bb_props(folder):
    for base in ("build-local/annotated/bbr/metadata", "build/annotated/bbr/metadata"):
        fp = ROOT / base / folder / "resolvedProperties.json"
        if fp.exists():
            d = json.loads(fp.read_text(encoding="utf-8"))
            props = d.get("properties", []) or []
            names = []
            for entry in props:
                path = entry.get("path") or []
                if len(path) == 1 and path[0] not in SKIP:   # top-level only
                    names.append(bare(path[0]))
            # de-dup preserving order
            seen = set(); out = []
            for n in names:
                if n not in seen:
                    seen.add(n); out.append(n)
            return out, base.split("/")[0]
    return None, None

def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    classes = {c["targetClass"]: c for c in cfg["mapping"]["class"]}
    assocs = cfg["mapping"].get("association", []) or []

    def assoc_roles(name):
        roles = []
        for a in assocs:
            subj, obj = a.get("subjectClass"), a.get("objectClass")
            tan = a.get("targetAssociationName", "")
            if subj == name and tan.startswith(subj + "_") and tan.endswith("_" + obj):
                roles.append(tan[len(subj)+1 : -(len(obj)+1)])
        return roles

    def own_attrs(name):
        return [a["name"] for a in (classes.get(name, {}).get("attribute") or [])]
    def inherited(name):
        out = []
        for p in classes.get(name, {}).get("generalization", []) or []:
            out += own_attrs(p) + assoc_roles(p) + inherited(p)
        return out

    print("=" * 84)
    print("CORE UML class vs BB resolvedProperties.json  (attrs + associations + inheritance)")
    print("=" * 84)
    any_div = False
    for cname in classes:
        folder = CLASS_BB.get(cname, "??")
        own = own_attrs(cname); ar = assoc_roles(cname); inh = inherited(cname)
        have = set(own) | set(ar) | set(inh)
        if folder is None:
            print(f"\n## {cname}  (synthesized / no standalone BB)\n   attrs: {', '.join(own)}  assoc: {', '.join(ar) or '-'}")
            continue
        bb, src = bb_props(folder)
        if bb is None:
            print(f"\n## {cname}  *** resolvedProperties not found: {folder} ***")
            continue
        bbset = set(bb)
        missing = [p for p in bb if p not in have]
        extra = [p for p in (own + ar) if p not in bbset]
        flag = "" if not (missing or extra) else "  <-- DIVERGES"
        if missing or extra: any_div = True
        print(f"\n## {cname}  [{folder}]  ({src}){flag}")
        print(f"   BB    : {', '.join(bb)}")
        print(f"   UML   : attrs[{', '.join(own)}] assoc[{', '.join(ar) or '-'}] inh[{', '.join(inh) or '-'}]")
        if missing: print(f"   MISSING: {', '.join(missing)}")
        if extra:   print(f"   EXTRA  : {', '.join(extra)}")
    print(f"\n{'='*84}\nDivergences found: {any_div}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
