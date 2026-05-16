#!/usr/bin/env python3
"""One-off retrofit per the union-type-policy (workflowDescription.md):

For every attribute in every ucmism2m mapping config, retype dataType to the
canonical UML class per the policy, based on the attribute name and any
existing dataType signal. The rules below match how the BB JSON Schemas
present each property's anyOf shape.

Run via:
    python script/retype_to_union_canonical.py [--check]

--check prints what would change without writing.

Side effect: also renames any target class named "LabeledLink" to "Reference"
(and fixes inbound dataType references), to align with the cdifReference BB
naming established in commit acbe384c2.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[1] / "configuration"

# ---------------------------------------------------------------------------
# Retype rules: attribute name -> canonical UML dataType.
#
# These match the BB resolvedSchema anyOf shapes (see the survey output in
# survey_union_types.py) and the union-type-policy reduction table.
#
# Rules apply only when the current dataType is the "primitive shorthand" form
# (XsdAnyUri or String) — never overrides a richer existing type like Concept.
# ---------------------------------------------------------------------------

# Attribute names whose BB shape is `Identifier | @id-ref | string`
# (schema:PropertyValue or shorter forms).
IDENTIFIER_ATTRS = {
    "identifier",
    "sameAs",
    "additionalProperty",
    "propertyID",          # propertyID is itself sometimes structured
}

# Attribute names whose BB shape is `DefinedTerm | string` (controlled term
# with a labeled vocabulary).
DEFINED_TERM_ATTRS = {
    "additionalType",
    "keywords",
    "unitCode",
    "category",
    "serviceType",
    "manufacturer",
    "model",
    "measurementTechnique",
    "roleName",            # role from a controlled list
    "encodingFormat",      # MIME types or DefinedTerm
}

# Attribute names whose BB shape is `cdif:Reference | @id-ref | string` — a
# labeled URL plus optional structured form.
REFERENCE_ATTRS = {
    "license",
    "conditionsOfAccess",
    "publishingPrinciples",
    "documentation",
    "termsOfService",
    "relatedLink",
    "subjectOf",
    "termsOfUse",
}

# Primitives we know we should NEVER convert (these are plain URI / date /
# language tag / numeric, not structured types).
PRIMITIVE_KEEP_ATTRS = {
    "url",                  # plain URI in JSON
    "contentUrl",           # direct fetch URL
    "@id",                  # the JSON-LD id
}


def retype_attribute(attr: dict, *, owner_class: str, profile: str) -> bool:
    """Mutate attr in place; return True if dataType changed."""
    name = attr.get("name")
    if not name:
        return False
    if name in PRIMITIVE_KEEP_ATTRS:
        return False
    current = attr.get("dataType")
    if not current:
        return False
    # Only widen from a primitive shorthand to a richer structured type.
    if current not in {"String", "XsdAnyUri"}:
        return False

    new_type = None
    if name in IDENTIFIER_ATTRS:
        new_type = "Identifier"
    elif name in DEFINED_TERM_ATTRS:
        new_type = "DefinedTerm"
    elif name in REFERENCE_ATTRS:
        new_type = "Reference"

    if not new_type or new_type == current:
        return False

    # Skip retyping if the owner class IS the canonical type (avoid self-ref).
    if owner_class in {"Identifier", "DefinedTerm", "Reference"} and owner_class == new_type:
        return False

    attr["dataType"] = new_type
    return True


def rename_labeled_link_class(cfg: dict) -> int:
    """Rename a target class 'LabeledLink' -> 'Reference' and flesh out the
    attribute list to match the cdifReference BB shape. Returns count of
    inbound dataType references updated."""
    refs_updated = 0
    classes = cfg.get("mapping", {}).get("class", [])
    has_reference = any(c.get("targetClass") == "Reference" for c in classes)
    for cls in classes:
        if cls.get("targetClass") == "LabeledLink" and not has_reference:
            cls["targetClass"] = "Reference"
            cls["_comment"] = (
                "Reference (the cdif:Reference type — local UML class matching "
                "the cdifProperties/cdifReference building block). Renamed from "
                "the previous 'LabeledLink' stub. Used wherever the JSON schema "
                "admits 'cdif:Reference | @id-ref | string' shape (license, "
                "conditionsOfAccess, publishingPrinciples, documentation, "
                "termsOfService, relatedLink, subjectOf)."
            )
            cls["definition"] = (
                "A typed reference to an external entity (cdif:Reference). "
                "Provides a labeled link surface (name, description, url) plus "
                "the DDI-CDI dt-Reference semantics (uri, optional cdif:semantic "
                "describing the role). See the cdifProperties/cdifReference "
                "building block for the full definition; this is the per-profile "
                "UML class that JSON-shape unions reduce to."
            )
            # Replace attributes with the cdifReference shape (subset OK for
            # the UML model browser; the BB schema carries the full thing).
            cls["attribute"] = [
                {"name": "identifier",  "dataType": "XsdAnyUri",
                 "definition": "@id - URI of the referenced resource.",
                 "multiplicity": {"lower": "1", "upper": "1"}},
                {"name": "name",        "dataType": "String",
                 "definition": "schema:name - human-readable label for the URI.",
                 "multiplicity": {"lower": "0", "upper": "1"}},
                {"name": "description", "dataType": "String",
                 "definition": "schema:description - short summary of the referenced resource.",
                 "multiplicity": {"lower": "0", "upper": "1"}},
                {"name": "url",         "dataType": "XsdAnyUri",
                 "definition": "schema:url - resolvable URL (when distinct from the @id).",
                 "multiplicity": {"lower": "0", "upper": "1"}},
            ]

    # Update inbound dataType references from "LabeledLink" -> "Reference"
    for cls in classes:
        for attr in cls.get("attribute", []) or []:
            if attr.get("dataType") == "LabeledLink":
                attr["dataType"] = "Reference"
                refs_updated += 1
    # Update association object class references too
    for assoc in cfg.get("mapping", {}).get("association", []) or []:
        if assoc.get("objectClass") == "LabeledLink":
            assoc["objectClass"] = "Reference"
            refs_updated += 1
        tname = assoc.get("targetAssociationName") or ""
        if tname.endswith("_LabeledLink"):
            assoc["targetAssociationName"] = tname[: -len("_LabeledLink")] + "_Reference"
            refs_updated += 1
    return refs_updated


def add_stub_class(cfg: dict, target_name: str, package: str = "Support") -> bool:
    """If the named target class is referenced as a dataType but not defined
    in this config, add a minimal stub. Returns True if added."""
    classes = cfg.get("mapping", {}).get("class", [])
    existing = {c.get("targetClass") for c in classes}
    if target_name in existing:
        return False
    # Is anything in this config typed as target_name?
    used = False
    for c in classes:
        for a in c.get("attribute", []) or []:
            if a.get("dataType") == target_name:
                used = True
                break
        if used:
            break
    if not used:
        return False

    # Build a stub matching the canonical Core definitions
    stubs = {
        "Identifier": {
            "_comment": "Identifier (schema:PropertyValue) stub. Local target class so attributes typed as 'Identifier' resolve inside this profile; the canonical definition lives in the CDIFCore profile.",
            "mappingType": "new", "targetPackage": package, "targetClass": "Identifier",
            "definition": "schema:PropertyValue / schema:Identifier (stub). A structured identifier with a propertyID (scheme), value, and optional url. Full definition in CDIFCore::Identifier.",
            "attribute": [
                {"name": "propertyId", "dataType": "String",    "definition": "schema:propertyID - the identifier scheme (e.g. DOI, Handle, ROR).", "multiplicity": {"lower": "0", "upper": "1"}},
                {"name": "value",      "dataType": "String",    "definition": "schema:value - the identifier value.",                                 "multiplicity": {"lower": "1", "upper": "1"}},
                {"name": "url",        "dataType": "XsdAnyUri", "definition": "schema:url - resolvable form of the identifier.",                       "multiplicity": {"lower": "0", "upper": "1"}},
            ],
        },
        "DefinedTerm": {
            "_comment": "DefinedTerm (schema:DefinedTerm) stub. Local target class so attributes typed as 'DefinedTerm' resolve inside this profile; the canonical definition lives in the CDIFCore profile.",
            "mappingType": "new", "targetPackage": package, "targetClass": "DefinedTerm",
            "definition": "schema:DefinedTerm (stub). A controlled-vocabulary term with name, code, and scheme URI. Full definition in CDIFCore::DefinedTerm.",
            "attribute": [
                {"name": "identifier",       "dataType": "XsdAnyUri", "definition": "@id / schema:identifier - URI for the term.",                              "multiplicity": {"lower": "0", "upper": "1"}},
                {"name": "name",             "dataType": "String",    "definition": "schema:name - the term's preferred label.",                                "multiplicity": {"lower": "1", "upper": "1"}},
                {"name": "termCode",         "dataType": "String",    "definition": "schema:termCode - code value within the term set.",                       "multiplicity": {"lower": "0", "upper": "1"}},
                {"name": "inDefinedTermSet", "dataType": "XsdAnyUri", "definition": "schema:inDefinedTermSet - URI of the controlled vocabulary.",             "multiplicity": {"lower": "0", "upper": "1"}},
            ],
        },
        "Reference": {
            "_comment": "Reference (cdif:Reference) stub. Local target class so attributes typed as 'Reference' resolve inside this profile; the canonical definition lives in the CDIFCore profile and the cdifProperties/cdifReference building block.",
            "mappingType": "new", "targetPackage": package, "targetClass": "Reference",
            "definition": "cdif:Reference (stub). A typed reference to an external entity. Full definition in CDIFCore::Reference and cdifProperties/cdifReference.",
            "attribute": [
                {"name": "identifier",  "dataType": "XsdAnyUri", "definition": "@id - URI of the referenced resource.",                       "multiplicity": {"lower": "1", "upper": "1"}},
                {"name": "name",        "dataType": "String",    "definition": "schema:name - human-readable label for the URI.",             "multiplicity": {"lower": "0", "upper": "1"}},
                {"name": "description", "dataType": "String",    "definition": "schema:description - short summary of the referenced resource.", "multiplicity": {"lower": "0", "upper": "1"}},
                {"name": "url",         "dataType": "XsdAnyUri", "definition": "schema:url - resolvable URL (when distinct from the @id).",   "multiplicity": {"lower": "0", "upper": "1"}},
            ],
        },
    }
    stub = stubs.get(target_name)
    if stub:
        classes.append(stub)
        # Also ensure the Support package exists in the package[] list
        pkgs = cfg.get("package") or []
        if not any(p.get("name") == package for p in pkgs):
            cfg["package"] = pkgs + [{
                "name": package,
                "parent": cfg["transformation"]["targetModel"]["mainPackage"],
                "definition": "Supporting structured types: Identifier, DefinedTerm, Reference (stubs; full definitions in CDIFCore).",
            }]
        return True
    return False


def process(cfg_path: Path, check: bool) -> dict:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    profile = cfg.get("transformation", {}).get("targetModel", {}).get("acronym", cfg_path.stem)

    # Step 1: rename LabeledLink class (if present) and inbound refs
    inbound = rename_labeled_link_class(cfg)

    # Step 2: retype attributes
    changes = []
    classes = cfg.get("mapping", {}).get("class", [])
    for cls in classes:
        owner = cls.get("targetClass", "?")
        for attr in cls.get("attribute", []) or []:
            before = attr.get("dataType")
            if retype_attribute(attr, owner_class=owner, profile=profile):
                changes.append((owner, attr["name"], before, attr["dataType"]))

    # Step 3: add stub classes if any retype now needs an undefined target
    added_stubs = []
    for name in ("Identifier", "DefinedTerm", "Reference"):
        if add_stub_class(cfg, name):
            added_stubs.append(name)

    if not check and (changes or inbound or added_stubs):
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return {
        "profile": profile,
        "labeled_link_inbound_refs": inbound,
        "retypes": changes,
        "added_stubs": added_stubs,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="Show changes without writing")
    args = ap.parse_args(argv)

    configs = sorted(CONFIG_DIR.glob("ddi-cdi2cdif*_mapping.json"))
    total_retypes = 0
    for cp in configs:
        result = process(cp, args.check)
        print(f"\n== {result['profile']} ({cp.name}) ==")
        if result["labeled_link_inbound_refs"]:
            print(f"  LabeledLink -> Reference (class+{result['labeled_link_inbound_refs']} inbound refs)")
        if result["added_stubs"]:
            print(f"  + stubs: {', '.join(result['added_stubs'])}")
        if result["retypes"]:
            for owner, name, before, after in result["retypes"]:
                print(f"  {owner}.{name}: {before} -> {after}")
            total_retypes += len(result["retypes"])
        if not (result["labeled_link_inbound_refs"] or result["retypes"] or result["added_stubs"]):
            print("  (no changes)")

    print(f"\nTotal retypes: {total_retypes}")
    if args.check:
        print("(--check mode — files not modified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
