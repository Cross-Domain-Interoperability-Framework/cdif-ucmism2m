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
- **Property exclusion:** `transformation.excludeProperties` (v1.1) is a list of
  `"ClassName.propertyName"` removed from the target class before the closure /
  diagram / XMI emit. Use to drop a source-`map` property that is not part of the
  CDIF building block. (`emit_uml_from_config` prunes the target class; also fed to
  `ctx.exclude_property_specs`.)
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
- **Model browser:** generated by `build-docs.ps1` into
  `metadataBuildingBlocks/cdif-uml-model/`. See the **Model browser** section below.

## Model browser (`build-docs.ps1`)

Renders the per-profile HTML/SVG class browser into
`metadataBuildingBlocks/cdif-uml-model/` in five steps:

1. Build a **class → origin-profile registry** from the configs (`_registry.json`).
2. Emit XMI + PlantUML + SVG per profile. Overview boxes are **colored by
   originating profile**, and a **simplified `index.local.*`** overview is also
   emitted (Core/Discovery-inherited classes dropped) when meaningful.
3. Augment the registry with datatypes (needs the generated `.pu`).
4. Emit the HTML browser (cross-profile links resolved from the registry).
5. **Normalize the emitted tree to LF.** The emitter writes CRLF on Windows but
   `metadataBuildingBlocks/.gitattributes` is `* text=auto eol=lf`, so without this
   every regenerated file shows as modified. `_registry.json` is written with
   **sorted keys** for byte-stability.

The registry is built *before* the PlantUML emit (step 1) so coloring and the
simplified diagram can consume it.

Browser features:
- **Per-profile box colors + legend** (Core blue, Discovery green, DataDescription
  yellow, DataStructure peach, Codelist purple). Colors come from `_PROFILE_COLORS`
  in the generator; origin = registry value (deepest profile that declares the
  class, so a class re-declared in a child config shows the child's color).
- **"Hide inherited (Core/Discovery)" toggle** swaps the full overview for
  `index.local.svg`; the choice is **persisted per page** (sessionStorage) so
  drilling into a class and pressing the diagram **Back** button returns to the
  same view. The toggle + legend sit in a **sticky bar**.
- Class-typed attributes render as linked **association boxes**; the union classes
  (`DefinedTerm`/`Identifier`/`Reference`/`AdditionalProperty`) carry a
  **"JSON serialization" note** (a plain string / `@id` ref may substitute).
- **Own-members-only (May 2026):** a class's context diagram/table and the overview
  show only members *specific to that class* — outgoing associations and class/datatype
  attribute-refs **inherited from an ancestor are not duplicated** (they show on the
  parent, reachable via the generalization arrow). Helpers `_ancestor_ids`,
  `_inherited_assoc_keys` (by `(role, target)`), `_inherited_prop_names`. The
  `(role,target)`/name match (not prop-id) is required because a bare `map` copies the
  source's *inherited* attributes onto each subclass as if own; per-variant overrides
  that reuse a role with a different target are preserved. Incoming associations +
  generalization arrows always shown.
- Interactive diagrams (zoom/pan/copy) are clipped to their box via
  `position:relative` + `contain:paint` on `.diagram-viewport`, so panning never
  paints the graph over surrounding text or the sticky controls.
- SVG re-render is **content-hash gated** via a gitignored `_render_cache.json`
  per profile (records only successful renders; a fresh clone renders once).

## Decisions in force (don't silently reverse)

- **Configs are aligned to their building blocks.** Each Core UML class's attribute
  set matches its BB (`_sources/.../<bb>/schema.yaml` / `resolvedProperties.json`) —
  drop schema.org/DDI properties the restricted CDIF profile doesn't include, add the
  ones it does. (Sept/May 2026 pass realigned all 17 Core classes, e.g. Person,
  Organization, DataDownload, CatalogRecord; added the `ContactPoint` class.) When in
  doubt, compare config attrs+associations (incl. inherited) against the BB.
- **ProvActivity in Core = only `prov:used`.** Core's `prov:wasGeneratedBy` uses the
  `provProperties/generatedBy` BB (just `prov:used`). The richer `provProperties/
  provActivity` and the schema.org-extended `cdifProvActivity` belong to the
  cdifComplete / cdifXAS profiles — do NOT add name/description/startedAtTime/etc. to
  ProvActivity in Core/Discovery/DataDescription/DataStructure.
- **WebAPI action machinery IS modelled in Core** (May 2026; reverses the earlier
  "not modelled" decision). `WebAPI.potentialAction` is an association to a real
  **`Action`** class (was an `XsdAnyUri` stub), and `Action` ramifies into
  **`EntryPoint`** (`schema:target`), **`ActionResult`** (`schema:result`; the
  `actionResult` BB), and **`PropertyValueSpecification`** (`schema:query-input`).
  All four live in Core's `Distribution` package, so they propagate to Discovery/
  DataDescription/DataStructure. The Action subtypes (SearchAction, FindAction, …)
  stay union-collapsed to the `Action` base, and `schema:object` (open-ended
  `schema:Thing`) is still not modelled. Mirrors the `action`/`actionResult`/`webAPI`
  BBs. Audit: `query-input` ~ `Action_queryInput_PropertyValueSpecification` (ALIAS,
  since association names can't contain `-`).
- **Keys keep DDI-CDI `PrimaryKey`/`PrimaryKeyComponent` naming**, not `cdif:Key`/`ComponentPosition`.
- **DataStructure hierarchy via generalization, not duplication.** `DataStructureComponent`
  is abstract with the component types (`Identifier`/`Measure`/`Attribute`/`Dimension`/
  `VariableValue`) generalizing it; `Wide`/`Long`/`DimensionalDataStructure` generalize the
  generic (concrete) `DataStructure`. So `cdi:isStructuredBy`, the generic
  `has DataStructureComponent`/`PrimaryKey`/`ForeignKey`, AND
  `cdif:isDefinedBy_RepresentedVariable` (declared once on the abstract) apply to every variant/
  component via inheritance, with per-variant `has_*` associations kept for the specific
  component requirements. **`VariableDescriptorComponent` is the exception:** it is defined by a
  `DescriptorVariable` (not a RepresentedVariable), so it is modelled **standalone** (does NOT
  generalize `DataStructureComponent`) with its own `isDefinedBy_DescriptorVariable` and a
  `refersTo` → `VariableValueComponent` (target type also enforced by SHACL). Real DDI-CDI
  generalizations declared in the config (`generalization`/`isAbstract`), not diagram fictions.
- **ReferenceVariable collapses to RepresentedVariable; conceptual domains dropped.** CDIF has
  no ReferenceVariable — a `VariableValueComponent` is defined by a plain `RepresentedVariable`.
  CDIF also drops the whole conceptual-domain side: no `Substantive/SentinelConceptualDomain`,
  no `takesConceptsFrom`, no `ConceptSystem`. A `ValueDomain` carries `takesValuesFrom`
  (→ EnumerationDomain) and **`isDescribedBy` → `ValueAndConceptDescription`** (defined in the
  DataDescription config, in cdifValueDomain on the JSON side). `RepresentedVariable` carries
  `uses` → `Concept` (`cdif:uses_Concept`) and `measures` → `UnitType`. `DescriptorVariable` is
  curated to its BB (id + name + `hasValuesFrom` → DescriptorValueDomain), not a bare source map.
- **`cdi:isStructuredBy` is anchored on `DataDownload`** (the distribution, co-typed
  `cdi:PhysicalDataSet` in instances) — not on `AbstractDistribution`. A WebAPI carries it on
  its Action result instead: `ActionResult → DataStructure : isStructuredBy` (now that the
  Action subtree is modelled). **`cdif:uses` is `InstanceVariable → RepresentedVariable`** in the
  DataStructure profile (the IV instantiates the RV that supplies its represented-variable-level
  properties); the RV in turn `uses → Concept`.
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
