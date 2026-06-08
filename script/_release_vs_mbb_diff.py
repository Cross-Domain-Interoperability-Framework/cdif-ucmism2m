"""Compare release *StructuredSchema.json vs mBB resolvedSchema.json by extracting
the structural surface (property keys, $defs keys, @type const class names)."""
import json, re, sys
from pathlib import Path

JSONLD = {"@context", "@id", "@type", "@vocab"}
TYPE_CONST_RE = re.compile(r"^[a-z]+:[A-Z][A-Za-z0-9]*$")
INTERESTING = {"schema", "skos", "dcterms", "dcat", "cdif", "cdi", "dqv", "prov",
               "geo", "geosparql", "time", "owl", "rdf", "rdfs", "xsd"}

def extract(node, props, classes):
    if isinstance(node, dict):
        p = node.get("properties")
        if isinstance(p, dict):
            for k in p:
                if k in JSONLD: continue
                prefix = k.split(":",1)[0] if ":" in k else ""
                if not prefix or prefix in INTERESTING:
                    props.add(k)
        for dk in ("$defs","definitions"):
            d = node.get(dk)
            if isinstance(d, dict): classes.update(d.keys())
        v = node.get("const")
        if isinstance(v, str) and TYPE_CONST_RE.match(v): classes.add(v)
        en = node.get("enum")
        if isinstance(en, list):
            for x in en:
                if isinstance(x, str) and TYPE_CONST_RE.match(x): classes.add(x)
        for k, val in node.items():
            if k != "@context":
                extract(val, props, classes)
    elif isinstance(node, list):
        for x in node: extract(x, props, classes)

ROOT = Path(r"C:\GithubC\CDIF")
PAIRS = [
    ("Core",            ROOT/"profile-core/cdifCoreStructuredSchema.json",
                        ROOT/"metadataBuildingBlocks/_sources/profiles/cdifProfile/cdifCore/resolvedSchema.json"),
    ("Discovery",       ROOT/"profile-discovery/cdifDiscoveryStructuredSchema.json",
                        ROOT/"metadataBuildingBlocks/_sources/profiles/cdifProfile/cdifDiscovery/resolvedSchema.json"),
    ("DataDescription", ROOT/"profile-datadescription/cdifDataDescriptionStructuredSchema.json",
                        ROOT/"metadataBuildingBlocks/_sources/profiles/cdifProfile/cdifDataDescription/resolvedSchema.json"),
    ("DataStructure",   ROOT/"profile-datastructure/cdifDataStructureStructuredSchema.json",
                        ROOT/"metadataBuildingBlocks/_sources/profiles/cdifProfile/cdifDataStructure/resolvedSchema.json"),
    ("Codelist",        ROOT/"profile-codelist/CDIFCodelistProfileStructuredSchema.json",
                        ROOT/"metadataBuildingBlocks/_sources/profiles/cdifProfile/cdifCodelist/resolvedSchema.json"),
    ("ConceptScheme",   ROOT/"profile-conceptscheme/cdifConceptSchemeStructuredSchema.json",
                        ROOT/"metadataBuildingBlocks/_sources/profiles/cdifProfile/cdifConceptScheme/resolvedSchema.json"),
]

for label, rel_path, mbb_path in PAIRS:
    rel = json.loads(rel_path.read_text(encoding="utf-8"))
    mbb = json.loads(mbb_path.read_text(encoding="utf-8"))
    rp, rc = set(), set(); mp, mc = set(), set()
    extract(rel, rp, rc); extract(mbb, mp, mc)
    only_rel_p = rp - mp; only_mbb_p = mp - rp
    only_rel_c = rc - mc; only_mbb_c = mc - rc
    status = "IDENTICAL surface" if not (only_rel_p|only_mbb_p|only_rel_c|only_mbb_c) else "DIFFERS"
    print(f"=== {label} === {status}")
    if only_rel_p: print(f"  properties only in release: {sorted(only_rel_p)}")
    if only_mbb_p: print(f"  properties only in mBB:     {sorted(only_mbb_p)}")
    if only_rel_c: print(f"  classes only in release:    {sorted(only_rel_c)}")
    if only_mbb_c: print(f"  classes only in mBB:        {sorted(only_mbb_c)}")
