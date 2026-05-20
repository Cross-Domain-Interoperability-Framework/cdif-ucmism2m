# AGENTS.md — working on the CDIF profile UML generation

Operational guide for adding or extending a CDIF profile UML. Read this with
[`README.md`](README.md) (what/why) and [`workflowDescription.md`](workflowDescription.md)
(the full pipeline + union-type policy).

## The one-paragraph model

A per-profile **ucmism2m JSON config** + the **DDI-CDI source XMI** drive
`uml_to_schema.py --emit-uml`, which emits a canonical **Eclipse UML2 XMI 2.5.1**
for the profile. Generation is **config-driven, not schema-driven** — the emitter
never reads the profile's JSON Schema. The config is the curated source of truth
(it carries union-type reductions, abstract supertypes, DDI-CDI provenance). The
JSON Schema (`resolvedSchema.json`) is used only by the **audit** to detect drift.

## Two repos

| Repo | Holds | This session's commits |
|---|---|---|
| `cdif-ucmism2m` (this repo) | configs, schema, scripts, generated XMIs, docs | configs/audit/XMIs |
| `metadataBuildingBlocks` (sibling) | the generator `tools/uml_to_schema.py` + the building blocks | generator fixes |

A full run depends on **both** repos being current. If you change emit behavior,
it's in `metadataBuildingBlocks/tools/uml_to_schema.py`.

## Key paths

- **Source XMI (DDI-CDI 1.1beta):** `../ucmis.m2t/model/ddi-cdi_1-1beta_canonical-unique-names.xmi` (sibling clone, *outside* this repo; a 1.0 copy is in `model/` for reference).
- **Generator:** `../metadataBuildingBlocks/tools/uml_to_schema.py`
- **Configs:** `configuration/ddi-cdi2cdif<Profile>_mapping.json`
- **Config schema (v1.1):** `configuration/ucmis_mapping_configuration.schema.v1.1.json`
- **Audit:** `script/audit_schema_vs_uml.py`
- **Orchestrator (XMI + PlantUML + HTML, all profiles):** `script/build-docs.ps1`
- **Output:** `generated/<lower-acronym>_<major>-<minor>_canonical-unique-names.xmi`
- **Profile JSON Schemas (for the audit):** `../metadataBuildingBlocks/_sources/profiles/cdifProfiles/CDIF<Name>Profile/resolvedSchema.json` (Core's is under `_sources/cdifProperties/cdifCore/`).

## The loop: extend or add a profile

1. **Find the gap.** Run the audit for the profile (see below). The `REAL GAPS`
   bucket is your worklist; the other buckets are intentionally absent.
2. **Read the building block(s)** the profile composes
   (`_sources/cdifProperties/<bb>/schema.yaml`) to learn the classes/properties.
3. **Verify source names** against the 1.1beta XMI before mapping
   (`grep "<name>X</name>" <source.xmi>`) — the `.ddi-cdi-source-index.json` is
   1.0 and can be stale (e.g. `CategoryStatistic` vs 1.1beta `CategoryStatistics`).
4. **Edit the config:** add classes (`map` for DDI-CDI-aligned, `new` for
   CDIF-specific) and associations. Bare `map` (no `attribute` list) copies all
   non-association source attributes — efficient, and the datatype policy handles
   their types.
5. **Validate** against the schema:
   ```python
   import json, jsonschema
   s=json.load(open('configuration/ucmis_mapping_configuration.schema.v1.1.json'))
   c=json.load(open('configuration/ddi-cdi2cdif<Profile>_mapping.json'))
   jsonschema.validate(c,s)
   ```
6. **Regenerate** the profile (and any that `compose` it):
   ```bash
   python ../metadataBuildingBlocks/tools/uml_to_schema.py \
     --xmi ../../ucmis.m2t/model/ddi-cdi_1-1beta_canonical-unique-names.xmi \
     --config configuration/ddi-cdi2cdif<Profile>_mapping.json \
     --emit-uml generated/<lower-acronym>_<major>-<minor>_canonical-unique-names.xmi
   ```
   Confirm the XMI is well-formed (`xml.dom.minidom.parse`).
7. **Re-audit** until `REAL GAPS` is zero or a documented residue.
8. **Update** `generated/README.md` (file size + class list).
9. **Commit** the config + regenerated XMI(s) + README together.

To add a *new* profile: author the config (copy an existing one), set
`targetModel` (acronym, version, uri, `composes`), add it to the `$profiles`
array in `script/build-docs.ps1`, then run the loop.

## The audit

```powershell
python script/audit_schema_vs_uml.py                 # all profiles
python script/audit_schema_vs_uml.py cdifDiscovery -v # one profile, show intentional buckets
```

It compares each profile's `resolvedSchema.json` against the **generated XMI** and
buckets findings: **REAL GAPS** (fix these) vs **union policy** / **datatype
policy** / **SKOS vocabulary** (intentional). When a "gap" is actually covered
under a different name, add an entry to `ALIASES` (e.g. `place→spatialextent`);
when something is deliberately not modelled, add it to `UNION_POLICY` or rely on
the per-config `datatypeSubstitutions`/`excludeDatatypes` (the audit unions those
across all configs). The audit understands the `Owner_role_Target` association
naming convention, so an association named `X_has_Y` covers the BB property
`has_Y`.

## Conventions and gotchas

- **Union-type policy:** reduce JSON `anyOf`/`oneOf` to one canonical UML type.
  Polymorphic class unions get an **abstract supertype** (`isAbstract:true` +
  `generalization` on the children): `Agent`, `AbstractDistribution`,
  `AbstractGeometry`, and `AbstractVariable` (parent of `VariableMeasured` +
  `InstanceVariable`). See README.
- **Value types → DataType:** mark identity-less value types with
  `"isDataType": true` (`Identifier`, `Reference`, the `Statistic` value object).
  It cascades through `composes`.
- **Datatype policy:** `datatypeSubstitutions` (rewrite a source DataType to a
  primitive or local stub) and `excludeDatatypes` (drop). Project-wide policy
  lives in the **Core** config and cascades; a profile may add its own (e.g.
  DataStructure's `TypedString → String`).
- **Composition (`composes`)** dedups associations by `targetAssociationName`
  (local wins). To **override** a base profile's association while retargeting it,
  keep the base's `targetAssociationName` and change `objectClass` — the emitted
  name follows `objectClass`. (This is how DataDescription points
  `Dataset_variableMeasured_*` at `AbstractVariable` while still overriding
  Discovery's `…_VariableMeasured`.)
- **Filenames/version** come from `targetModel.acronym` + `majorVersion`/`minorVersion`.
  All profiles are currently `1`/`0` (matching the `/1.0/` URIs). `build-docs.ps1`
  derives the canonical filename.
- **Generator behaviors (not config):** primitives by Eclipse `PrimitiveTypes.xmi`
  href; a model-level `ModelIdentification` DataType from `targetModel` fields.

## Decisions in force (don't silently reverse)

- **WebAPI/OpenAPI action machinery NOT modelled** (`potentialAction`/`EntryPoint`/
  `PropertyValueSpecification`) — kept as intentional union-policy absence.
- **Keys keep DDI-CDI `PrimaryKey`/`PrimaryKeyComponent` naming**, not `cdif:Key`/`ComponentPosition`.
- **`dcterms:*` alternates not modelled** — CDIF prefers `schema:` equivalents (`dcterms:conformsTo` is the exception, modelled on `CatalogRecord`).
- **OWL-Time and geosparql geometry ARE modelled as classes** in Discovery
  (`Instant`/`TimePosition`/`Geometry`) — an intentional exception to the
  `ProperInterval`↔string union-policy shorthand, because the BB defines real
  structured content there.

## Verify before committing

- Config validates against the v1.1 schema.
- Generated XMI is well-formed; new classes/associations present.
- `py_compile` the generator if you touched it.
- Audit `REAL GAPS` is zero or a residue you can explain.
