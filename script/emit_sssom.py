#!/usr/bin/env python3
"""Emit a SSSOM TSV mapping file consolidating the `sssom` blocks from every
ucmism2m configuration file.

Output conforms to the SSSOM specification:
  https://mapping-commons.github.io/sssom/dev/spec-model/

Format: TSV body preceded by a YAML metadata header (each header line begins
with `# `). Required fields per row: subject_id, predicate_id, object_id,
mapping_justification.

Subject IRIs use the DDI-CDI RDF namespace
(http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/<ClassName>).
Object IRIs are derived from the per-config targetModel.uri or, when the
sssom block's object_label embeds a "(prefix:Name)" hint, from the matching
prefix in CURIE_MAP.

Class mappings come from `mapping.class[*].sssom` blocks.
Attribute mappings are emitted when an attribute carries an explicit
`sssom` block (optional v1.1 extension).

Usage:
    python emit_sssom.py [--out PATH] [--config-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

CURIE_MAP = {
    "skos":      "http://www.w3.org/2004/02/skos/core#",
    "schema":    "http://schema.org/",
    "dcterms":   "http://purl.org/dc/terms/",
    "dcat":      "http://www.w3.org/ns/dcat#",
    "prov":      "http://www.w3.org/ns/prov#",
    "dqv":       "http://www.w3.org/ns/dqv#",
    "spdx":      "http://spdx.org/rdf/terms#",
    "geosparql": "http://www.opengis.net/ont/geosparql#",
    "time":      "http://www.w3.org/2006/time#",
    "csvw":      "http://www.w3.org/ns/csvw#",
    "cdi":       "http://ddialliance.org/Specification/DDI-CDI/1.0/RDF/",
    "cdif":      "https://cdif.org/0.1/",
    "owl":       "http://www.w3.org/2002/07/owl#",
}

DDI_CDI_NS = CURIE_MAP["cdi"]

# Match "(prefix:Name)" inside an object_label
_OBJ_HINT = re.compile(r"\(([A-Za-z][\w\-]*):([A-Za-z][\w\-]*)\)")


def _curie_to_iri(curie: str) -> str:
    if ":" not in curie:
        return curie
    prefix, local = curie.split(":", 1)
    base = CURIE_MAP.get(prefix)
    return f"{base}{local}" if base else curie


_SUBJECT_LABEL_NAME = re.compile(r"DDI-CDI\s+([A-Za-z][\w]*)")


def _ddi_subject_iri(class_name: str, attr_name: str = "") -> str:
    """Build a DDI-CDI subject IRI. Attributes are addressed as
    ClassName/attrName (a convention; DDI-CDI doesn't ship attribute IRIs)."""
    if attr_name:
        return f"{DDI_CDI_NS}{class_name}/{attr_name}"
    return f"{DDI_CDI_NS}{class_name}"


def _ddi_subject_iri_from_label(subject_label: str) -> str:
    """Fallback when sourceClass isn't a UML Class (e.g. a DataType). Pull
    the bare name out of subject_label like 'DDI-CDI AgentInRole (DataType)'."""
    if not subject_label:
        return ""
    m = _SUBJECT_LABEL_NAME.search(subject_label)
    if m:
        return f"{DDI_CDI_NS}{m.group(1)}"
    return ""


def _object_iri(target_class: str, object_label: str,
                target_model_uri: str, profile_acronym: str,
                attr_name: str = "") -> str:
    """Decide the object IRI for a profile class/attribute.

    Order of preference:
      1. CURIE hint inside object_label, e.g. "(schema:Dataset)".
      2. Profile-specific URI for the class.
    """
    m = _OBJ_HINT.search(object_label or "")
    if m:
        base_iri = _curie_to_iri(f"{m.group(1)}:{m.group(2)}")
        return f"{base_iri}/{attr_name}" if attr_name else base_iri
    base = target_model_uri.rstrip("/")
    if attr_name:
        return f"{base}/{target_class}/{attr_name}"
    return f"{base}/{target_class}"


def _coerce_confidence(value) -> str:
    if value is None or value == "":
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    # SSSOM expects a number in [0,1]
    return f"{f:.3f}".rstrip("0").rstrip(".")


def _row_for_class(cls_spec: dict, profile_acronym: str,
                   target_model_uri: str) -> dict | None:
    sssom = cls_spec.get("sssom") or {}
    if not sssom:
        return None
    source = cls_spec.get("sourceClass") or ""
    target = cls_spec.get("targetClass") or ""
    subject_id = (_ddi_subject_iri(source) if source
                  else _ddi_subject_iri_from_label(sssom.get("subject_label", "")))
    object_id = _object_iri(target, sssom.get("object_label", ""),
                            target_model_uri, profile_acronym)
    predicate_curie = sssom.get("predicate_id") or "skos:closeMatch"
    return {
        "subject_id":            subject_id,
        "subject_label":         sssom.get("subject_label") or source,
        "predicate_id":          predicate_curie,
        "object_id":             object_id,
        "object_label":          sssom.get("object_label") or f"{profile_acronym} {target}",
        "mapping_justification": "semapv:ManualMappingCuration",
        "confidence":            _coerce_confidence(sssom.get("confidence")),
        "comment":               (sssom.get("comment") or sssom.get("predicate_label") or "").replace("\t", " ").replace("\n", " "),
        "mapping_provider":      f"ucmism2m config {profile_acronym}",
        "subject_category":      "owl:Class",
        "object_category":       "owl:Class",
    }


def _row_for_attribute(attr_spec: dict, cls_spec: dict,
                       profile_acronym: str, target_model_uri: str) -> dict | None:
    sssom = attr_spec.get("sssom") or {}
    if not sssom:
        return None
    source_cls = cls_spec.get("sourceClass") or ""
    target_cls = cls_spec.get("targetClass") or ""
    source_attr = attr_spec.get("fromSourceAttributeName") or attr_spec.get("name") or ""
    target_attr = attr_spec.get("name") or ""
    subject_id = (_ddi_subject_iri(source_cls, source_attr)
                  if source_cls and source_attr else "")
    object_id = _object_iri(target_cls, sssom.get("object_label", ""),
                            target_model_uri, profile_acronym,
                            attr_name=target_attr)
    predicate_curie = sssom.get("predicate_id") or "skos:closeMatch"
    return {
        "subject_id":            subject_id,
        "subject_label":         sssom.get("subject_label") or f"{source_cls}.{source_attr}",
        "predicate_id":          predicate_curie,
        "object_id":             object_id,
        "object_label":          sssom.get("object_label") or f"{target_cls}.{target_attr}",
        "mapping_justification": "semapv:ManualMappingCuration",
        "confidence":            _coerce_confidence(sssom.get("confidence")),
        "comment":               (sssom.get("comment") or sssom.get("predicate_label") or "").replace("\t", " ").replace("\n", " "),
        "mapping_provider":      f"ucmism2m config {profile_acronym}",
        "subject_category":      "owl:DatatypeProperty",
        "object_category":       "owl:DatatypeProperty",
    }


def collect_rows(config_paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for cp in config_paths:
        with open(cp, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        target = cfg.get("transformation", {}).get("targetModel", {})
        acronym = target.get("acronym", cp.stem)
        target_uri = target.get("uri") or f"https://cdif.org/{acronym}/"
        for cls_spec in cfg.get("mapping", {}).get("class", []):
            r = _row_for_class(cls_spec, acronym, target_uri)
            if r:
                rows.append(r)
            for attr in cls_spec.get("attribute", []) or []:
                r = _row_for_attribute(attr, cls_spec, acronym, target_uri)
                if r:
                    rows.append(r)
    return rows


# SSSOM column order — first 4 are required, rest are common metadata.
COLUMNS = [
    "subject_id", "subject_label",
    "predicate_id",
    "object_id", "object_label",
    "mapping_justification",
    "confidence",
    "subject_category", "object_category",
    "mapping_provider",
    "comment",
]


def write_sssom_tsv(rows: list[dict], out_path: Path,
                    mapping_set_id: str, mapping_set_title: str,
                    version: str) -> None:
    today = date.today().isoformat()
    header_lines = [
        "# mapping_set_id: " + mapping_set_id,
        "# mapping_set_title: " + mapping_set_title,
        f"# mapping_set_version: {version}",
        f"# mapping_set_description: Class and attribute crosswalks from DDI-CDI 1.1beta to the five CDIF profiles (Codelist, Core, Discovery, DataDescription, DataStructure). Generated from ucmism2m mapping configurations.",
        "# license: https://creativecommons.org/licenses/by/4.0/",
        f"# mapping_date: {today}",
        "# mapping_tool: ucmism2m/script/emit_sssom.py",
        "# mapping_provider: CDIF metadataBuildingBlocks",
        "# curie_map:",
    ]
    for prefix, ns in CURIE_MAP.items():
        header_lines.append(f"#   {prefix}: {ns}")
    header_lines.append("#   semapv: https://w3id.org/semapv/vocab/")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(header_lines) + "\n")
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t",
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    default_cfg_dir = Path(__file__).resolve().parents[1] / "configuration"
    default_out = Path(__file__).resolve().parents[1] / "generated" / "cdif-ddi-cdi-mappings.sssom.tsv"
    ap.add_argument("--config-dir", type=Path, default=default_cfg_dir,
                    help=f"Directory of ddi-cdi2cdif*_mapping.json files (default: {default_cfg_dir})")
    ap.add_argument("--out", type=Path, default=default_out,
                    help=f"Output TSV path (default: {default_out})")
    ap.add_argument("--mapping-set-id",
                    default="https://w3id.org/cdif/mappings/ddi-cdi-to-cdif")
    ap.add_argument("--mapping-set-title",
                    default="DDI-CDI to CDIF profile classes and properties")
    ap.add_argument("--version", default="0.1")
    args = ap.parse_args(argv)

    configs = sorted(args.config_dir.glob("ddi-cdi2cdif*_mapping.json"))
    if not configs:
        print(f"ERROR: no configs found in {args.config_dir}", file=sys.stderr)
        return 2
    print(f"Reading {len(configs)} configs from {args.config_dir}",
          file=sys.stderr)

    rows = collect_rows(configs)
    print(f"Collected {len(rows)} mapping rows", file=sys.stderr)
    write_sssom_tsv(rows, args.out,
                    mapping_set_id=args.mapping_set_id,
                    mapping_set_title=args.mapping_set_title,
                    version=args.version)
    print(f"Wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
