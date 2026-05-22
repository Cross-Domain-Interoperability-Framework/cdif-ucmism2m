#!/usr/bin/env python3
"""Audit CDIF profile JSON-Schema coverage against the ucmism2m UML config.

For each profile this compares the composed JSON Schema (resolvedSchema.json,
produced by the OGC bblocks postprocessor) against the composed ucmism2m UML
mapping config, and reports the schema properties / $defs / @type classes that
have no corresponding class, attribute, or association role in the UML.

This is a *drift detector*, not a generator input. The UML config stays the
curated source of truth for the profile UML (it carries the union-type
reductions and DDI-CDI provenance the JSON Schema cannot express). The audit
just makes "the schema added a building block the UML hasn't mirrored yet"
visible instead of silent.

Usage:
    python audit_schema_vs_uml.py            # all profiles
    python audit_schema_vs_uml.py cdifDataDescription   # one profile
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[1]                       # .../CDIF
MBB = REPO / "metadataBuildingBlocks"
TOOLS = MBB / "tools"
CONFIG_DIR = REPO / "ucmism2m" / "configuration"
GENERATED_DIR = REPO / "ucmism2m" / "generated"
SOURCES = MBB / "_sources"

sys.path.insert(0, str(TOOLS))
from uml_to_schema import _load_with_composition  # noqa: E402

# profile slug -> (ucmism2m config, resolvedSchema.json)
PROFILES = {
    "cdifCodelist": (
        CONFIG_DIR / "ddi-cdi2cdifCodelist_mapping.json",
        SOURCES / "profiles/cdifProfiles/CDIFCodelistProfile/resolvedSchema.json",
    ),
    "cdifCore": (
        CONFIG_DIR / "ddi-cdi2cdifCore_mapping.json",
        SOURCES / "cdifProperties/cdifCore/resolvedSchema.json",
    ),
    "cdifDiscovery": (
        CONFIG_DIR / "ddi-cdi2cdifDiscovery_mapping.json",
        SOURCES / "profiles/cdifProfiles/CDIFDiscoveryProfile/resolvedSchema.json",
    ),
    "cdifDataDescription": (
        CONFIG_DIR / "ddi-cdi2cdifDataDescription_mapping.json",
        SOURCES / "profiles/cdifProfiles/CDIFDataDescriptionProfile/resolvedSchema.json",
    ),
    "cdifDataStructure": (
        CONFIG_DIR / "ddi-cdi2cdifDataStructure_mapping.json",
        SOURCES / "profiles/cdifProfiles/CDIFDataStructureProfile/resolvedSchema.json",
    ),
}

JSONLD_KEYWORDS = {
    "@context", "@id", "@type", "@value", "@language", "@graph",
    "@base", "@vocab", "@container", "@list", "@set", "@reverse", "@none",
}

# JSON-LD prefixes whose properties are first-class metadata fields. Properties
# under other prefixes (rdf, owl, ...) are usually structural and noisy.
INTERESTING_PREFIXES = {"schema", "cdi", "cdif", "dcterms", "skos", "dqv", "prov", "time", "geosparql"}

# class/type const looks like  prefix:PascalCase
TYPE_CONST_RE = re.compile(r"^[A-Za-z][\w.]*:[A-Z][A-Za-z0-9]+$")

# generic property local-names that are covered everywhere / not worth flagging
GENERIC_PROPS = {
    "id", "type", "value", "context", "name", "description", "identifier",
    "url", "title", "label", "comment", "seealso", "sameas",
}

# Names the UML deliberately does NOT model as separate classes because the
# union-type policy collapses them to a single canonical type / supertype.
UNION_POLICY = {
    # schema.org Action polymorphism (schema:potentialAction) - not modelled
    "action", "assessaction", "consumeaction", "controlaction", "createaction",
    "deleteaction", "findaction", "interactaction", "moveaction", "playaction",
    "searchaction", "transferaction", "updateaction", "entrypoint",
    "propertyvaluespecification",
    # schema:PropertyValue split into Identifier / VariableMeasured / AdditionalProperty
    "propertyvalue",
    # Agent / Organization polymorphism -> Agent supertype
    "consortium", "corporation", "educationalorganization",
    "governmentorganization", "ngo", "researchorganization", "fundingagency",
    "fundingscheme", "project",
    # CreativeWork / Distribution / Reference collapses
    "creativework", "mediaobject", "imageobject", "digitaldocument",
    "softwareapplication", "softwaresourcecode", "product", "collection",
    "datacatalog", "contactpoint", "role", "linkrole", "definedtermset",
    "relationship",
    # union / JSON-LD serialization artifacts
    "languagetaggedvalue", "conceptref", "id-reference",
    # $def wrapper names emitted by the resolver (not real classes)
    "cdifinstancevariable", "cdifinstancevariable_definedterm", "cdifcodelistconcept",
    # WebAPI / schema.org Action service-description machinery (cdifOpenApi) -
    # deliberately NOT modelled in the UML (decision: keep the WebAPI class
    # itself but not the potentialAction/EntryPoint/PropertyValueSpecification tree)
    "propertyvaluespecification", "entrypoint", "potentialaction", "result",
    "target", "object", "urltemplate", "httpmethod", "contenttype",
    "query-input", "valuename", "valuepattern", "valuerequired",
    # schema:LinkRole hyperlink machinery (collapsed)
    "linkrelationship",
}

# Known naming differences between schema local-name and the UML class name,
# so they aren't reported as false-positive gaps.
ALIASES = {
    "activity": "provactivity",       # prov:Activity ~ ProvActivity
    "place": "spatialextent",         # schema:Place wrapper ~ SpatialExtent
    "properinterval": "temporalextent",  # time:ProperInterval ~ TemporalExtent
    "key": "primarykey",              # cdif:Key ~ DDI-CDI PrimaryKey (kept name)
    "componentposition": "primarykeycomponent",  # cdi:ComponentPosition ~ PrimaryKeyComponent
}


def strip_prefix(name: str) -> str:
    n = name.lstrip("@")
    if ":" in n:
        n = n.split(":", 1)[1]
    return n


def norm(name: str) -> str:
    return strip_prefix(name).lower()


def canon(name: str) -> str:
    """Normalized name with known schema<->UML aliases applied."""
    n = norm(name)
    return ALIASES.get(n, n)


def datatype_policy() -> set[str]:
    """Source DataTypes the policy substitutes or excludes, unioned across all
    profile configs (the project-wide policy lives in Core and cascades, but a
    profile may add its own, e.g. DataStructure's TypedString). These are
    intentionally flattened, not modelled as their own classes."""
    names: set[str] = set()
    for cfg_path in CONFIG_DIR.glob("ddi-cdi2cdif*_mapping.json"):
        tr = json.loads(cfg_path.read_text(encoding="utf-8")).get("transformation", {})
        names |= set(tr.get("datatypeSubstitutions", {}).keys())
        names |= set(tr.get("excludeDatatypes", []))
    return {canon(n) for n in names}


DATATYPE_POLICY = datatype_policy()


def extract_schema(node, props: set[str], classes: set[str]) -> None:
    """Collect property keys, $defs names, and @type const class names."""
    if isinstance(node, dict):
        p = node.get("properties")
        if isinstance(p, dict):
            for k in p:
                if k in JSONLD_KEYWORDS:
                    continue
                prefix = k.split(":", 1)[0] if ":" in k else ""
                if (not prefix) or prefix in INTERESTING_PREFIXES:
                    props.add(k)
        for dk in ("$defs", "definitions"):
            d = node.get(dk)
            if isinstance(d, dict):
                classes.update(d.keys())
        v = node.get("const")
        if isinstance(v, str) and TYPE_CONST_RE.match(v):
            classes.add(v)
        en = node.get("enum")
        if isinstance(en, list):
            for x in en:
                if isinstance(x, str) and TYPE_CONST_RE.match(x):
                    classes.add(x)
        for k, val in node.items():
            if k == "@context":
                continue
            extract_schema(val, props, classes)
    elif isinstance(node, list):
        for it in node:
            extract_schema(it, props, classes)


def covered_from_config(cfg: dict) -> set[str]:
    """Normalized names the UML config covers: class names, attribute names,
    and association role names (and assoc subject/object class names)."""
    out: set[str] = set()
    mapping = cfg.get("mapping", {})
    for c in mapping.get("class", []) or []:
        tc = c.get("targetClass")
        if tc:
            out.add(canon(tc))
        for a in c.get("attribute", []) or []:
            if a.get("name"):
                out.add(canon(a["name"]))
    for a in mapping.get("association", []) or []:
        nm = a.get("targetAssociationName") or a.get("sourceAssociationName") or ""
        parts = nm.split("_")
        if len(parts) >= 3:
            role = "_".join(parts[1:-1])
            obj = parts[-1]
            out.add(canon(role))                    # role
            out.add(canon(obj))                     # object class
            out.add(canon(parts[0]))                # subject class
            # role_Target convention: BB splits polymorphic associations into
            # target-suffixed property names (cdif:has_Statistics, formats_X).
            out.add(canon(f"{role}_{obj}"))
        if a.get("objectClass"):
            out.add(canon(a["objectClass"]))
        if a.get("subjectClass"):
            out.add(canon(a["subjectClass"]))
    return out


def covered_from_xmi(xmi_path: Path) -> set[str]:
    """Names actually present in the generated UML XMI: every <name> (classes,
    datatypes, attributes, packages, associations). Captures attributes that
    bare 'map' classes copy from the source (which the config does not list).
    Association names (Owner_role_Target) also contribute role / role_Target."""
    out: set[str] = set()
    if not xmi_path.exists():
        return out
    root = ET.parse(xmi_path).getroot()
    for nm in root.iter("name"):
        text = (nm.text or "").strip()
        if not text:
            continue
        out.add(canon(text))
        parts = text.split("_")
        if len(parts) >= 3:
            role = "_".join(parts[1:-1])
            obj = parts[-1]
            out.add(canon(role))
            out.add(canon(obj))
            out.add(canon(parts[0]))
            out.add(canon(f"{role}_{obj}"))
    return out


def classify(orig: str, covered: set[str]) -> str:
    """Bucket a schema name: 'covered', 'vocabulary' (SKOS/Concept, defined in
    Codelist), 'datatype' (policy-substituted/excluded source DataType or xsd),
    'union' (union-type-policy collapse), or 'gap' (likely real)."""
    n = canon(orig)
    if n in covered:
        return "covered"
    prefix = orig.split(":", 1)[0] if ":" in orig else ""
    if prefix == "skos" or n in {"concept", "conceptscheme", "skosconcept", "conceptref"}:
        return "vocabulary"
    # dcterms:* alternates are intentionally not modelled - CDIF prefers the
    # schema: equivalents (dcterms:conformsTo is the exception and is modelled).
    if prefix == "dcterms":
        return "datatype"
    if prefix == "xsd" or n in DATATYPE_POLICY:
        return "datatype"
    # $def wrappers the resolver emits for each BB's local id-reference / cdif:Reference
    # serialization-shorthand defs (e.g. CdifRepresentedVariable_id-reference,
    # CdifRepresentedVariable_Reference). The union-type policy collapses these to the
    # canonical @id-ref / cdif:Reference type; they are never standalone UML classes.
    if n.endswith("_id-reference") or n.endswith("_reference"):
        return "union"
    if n in UNION_POLICY:
        return "union"
    return "gap"


def audit_one(slug: str) -> dict:
    config_path, resolved_path = PROFILES[slug]
    cfg, _inherited = _load_with_composition(config_path)
    tm = cfg["transformation"]["targetModel"]
    xmi_name = f"{tm['acronym'].lower()}_{tm['majorVersion']}-{tm['minorVersion']}_canonical-unique-names.xmi"
    covered = covered_from_config(cfg) | covered_from_xmi(GENERATED_DIR / xmi_name)

    schema = json.loads(resolved_path.read_text(encoding="utf-8"))
    props: set[str] = set()
    classes: set[str] = set()
    extract_schema(schema, props, classes)

    def bucketize(names: set[str], drop_generic: bool = False) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = {"gap": [], "vocabulary": [], "datatype": [], "union": []}
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
        "covered": len(covered),
        "classes": bucketize(classes),
        "props": bucketize(props, drop_generic=True),
    }


def main(argv: list[str]) -> int:
    verbose = "-v" in argv
    slugs = [a for a in argv[1:] if not a.startswith("-")] or list(PROFILES)
    for slug in slugs:
        if slug not in PROFILES:
            print(f"unknown profile: {slug} (known: {', '.join(PROFILES)})")
            continue
        r = audit_one(slug)
        cg, pg = r["classes"], r["props"]
        print(f"\n==================== {slug} ====================")
        print(f"  REAL GAPS - classes/types in schema with no UML class ({len(cg['gap'])}):")
        for c in cg["gap"]:
            print(f"      - {c}")
        print(f"\n  REAL GAPS - properties in schema with no UML attribute/association ({len(pg['gap'])}):")
        for p in pg["gap"]:
            print(f"      - {p}")
        print(f"\n  (intentionally absent - union policy: "
              f"{len(cg['union']) + len(pg['union'])}, "
              f"datatype/xsd policy: {len(cg['datatype']) + len(pg['datatype'])}, "
              f"SKOS vocabulary defined in Codelist: {len(cg['vocabulary']) + len(pg['vocabulary'])})")
        if verbose:
            for label, key in (("union", "union"), ("datatype", "datatype"), ("vocabulary", "vocabulary")):
                items = sorted(cg[key] + pg[key], key=str.lower)
                if items:
                    print(f"      [{label}] {', '.join(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
