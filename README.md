# UCMIS M2M Transformation — Project Documentation

**Version:** 1.0
**Last Updated:** 2026-05-15
**Compatibility:** Eclipse 2025-12 · QVTo 3.11.1 · Java 21 (Eclipse path) — or any Python 3.10+ (alternative path)

---

## At a glance — two ways to run the transformation

There are now **two interchangeable implementations** of the transformation described below. Both take the same inputs (DDI-CDI canonical Eclipse UML2 XMI + a JSON configuration that conforms to `configuration/ucmis_mapping_configuration.schema.json`) and produce the same kind of output (Eclipse UML2 XMI 2.5.1 for a profile model). Choose whichever fits your environment:

| Path | Status | Toolchain | Use when |
|---|---|---|---|
| **Eclipse / QVTo application** | In development — described in sections 1–3 below | Java 21 + Eclipse Tycho + QVTo 3.11.1 (build) | You want the long-term canonical tool, run from a packaged Eclipse RCP binary |
| **Python generator** | Working today — see [section 4](#4-alternative-python-generator-using-uml_to_schemapy) | Python 3.10+ with `pyyaml` and `jsonschema` | You want to generate profile UML right now, on any platform, without an Eclipse build |

Both paths read the same configuration files (`configuration/ddi-cdi2*.json`) and the same source model — the current DDI-CDI **1.1beta** canonical UML at `../ucmis.m2t/model/ddi-cdi_1-1beta_canonical-unique-names.xmi` (in the sibling UCMIS-M2T clone). A DDI-CDI 1.0 model remains at `model/ddi-cdi_canonical-unique-names-eclipse.xmi` for reference. The five CDIF profile UML files in `generated/` were produced by the Python path from the 1.1beta source; the Eclipse application will produce equivalent output once built.

---

## About this fork

This repository is a CDIF fork of Joachim Wackerow's UCMIS-M2M project (https://bitbucket.org/wackerow/ucmis.m2t/, retained as the `upstream` git remote in local clones). The CDIF fork extends the v1.0 mapping-configuration schema with a small set of backwards-compatible enhancements to handle modelling situations that arose when applying the original tool to the CDIF profiles. The full rationale and reference tables live in [`workflowDescription.md`](workflowDescription.md); the summary:

### v1.1 schema additions

| Field | Where | Purpose |
|---|---|---|
| `$schema` at top level | every config | enables editor validation |
| `fromSourceAttributeName` | map attributes | rename a source attribute (`cdi:name` → `skos:prefLabel`) |
| Optional `sourceAssociationName` | associations | brand-new associations don't need a DDI-CDI source |
| Optional `sourceClass` on `new` mappings | class mappings | record provenance Dependency without forcing source attrs |
| `sssom` as object **or** array | sssom blocks | accept both forms |
| `confidence` as number **or** string | sssom blocks | match the SSSOM 0..1 numeric form |
| `isAbstract` | class mappings | emit `uml:Class isAbstract="true"` (used for `Agent`, `AbstractDistribution`, `AbstractGeometry`) |
| `isDataType` | class mappings | emit the mapping as `<packagedElement xmi:type="uml:DataType">` instead of `uml:Class` (used for value types `Identifier`, `Reference`); cascades through `composes` |
| `generalization` | class mappings | emit `<generalization><general …/></generalization>`; inherited attrs flow through the closure walker |
| `composes` | `targetModel` | recursive profile composition mirroring JSON Schema `allOf` (Discovery → Core; DataDescription → Discovery → Core; DataStructure → DataDescription → Discovery → Core) |
| `datatypeSubstitutions` | `transformation` | rewrite synthetic target class properties whose type points at a named source DataType (`InternationalString` → `String`, `ControlledVocabularyEntry` → `Concept`, `NonDdiIdentifier` → `Identifier`, …); applied in two places (synthetic targets + transitive closure walker); cascades through `composes` |
| `excludeDatatypes` | `transformation` | drop properties typed by named source DataTypes (`BibliographicName`, `RationaleDefinition`, `Selector`, …) |

### Canonical Eclipse-XMI conventions (generator behavior)

Beyond the config fields above, the emitter applies three Eclipse-XMI conventions (from Joachim Wackerow's review of the generated XMI):

- **Primitive types by href** — primitive-typed attributes reference Eclipse's standard `PrimitiveTypes.xmi` (`<type xmi:type="uml:PrimitiveType" href="…/PrimitiveTypes.xmi#String"/>`) rather than a profile-local primitive stub.
- **`ModelIdentification` DataType** — each model carries a model-level `ModelIdentification` `uml:DataType` (read-only `prefix`/`majorVersion`/`minorVersion`/`title`/`language`/`uri`), driven by the config `targetModel` fields.
- **Canonical filenames** — outputs are named `<lower-acronym>_<major>-<minor>_canonical-unique-names.xmi` (e.g. `cdifcodelist_1-0_canonical-unique-names.xmi`), derived from the config acronym + version.

### Keeping the UML in step with the building-block schemas

UML generation is **config-driven, not schema-driven** — the emitter reads the DDI-CDI source XMI + the per-profile ucmism2m config, never the profile's JSON Schema. So when a building block is added to a profile's `schema.yaml`, the UML config must be updated to match. To catch that drift, run the coverage audit:

```powershell
python script/audit_schema_vs_uml.py            # all profiles
python script/audit_schema_vs_uml.py cdifDataDescription   # one profile
```

It diffs each profile's composed `resolvedSchema.json` against the **generated XMI** and buckets findings into **real gaps** vs intentionally-absent (union-type policy, datatype policy, SKOS vocabulary defined in Codelist). When extending a profile, drive the real-gaps list down to its intentional residue. See [`AGENTS.md`](AGENTS.md) for the full add-a-profile loop.

### The union-type problem — and the CDIF solution

JSON Schema admits union types (`anyOf` / `oneOf`); UML 2 does not have first-class union types. A survey across the five CDIF profile resolvedSchemas (see [`script/survey_union_types.py`](script/survey_union_types.py)) found **900+ union-shape occurrences** that needed reconciling. Rather than adopting the ShapeChange/GeoSciML `<<union>>` stereotype workaround (which CDIF stakeholders rejected), we chose to reduce every JSON union to a **single canonical UML attribute type**, with the simpler JSON forms (string, `@id`-only ref) treated as **serialization shorthand for the canonical type**.

The rules:

- **Coded-term unions** (`X | string`, where X is `Concept` / `SkosConcept` / `DefinedTerm`) → UML attribute typed `X`. The plain string is a shorthand for `X.prefLabel` or `X.@id`.
- **Identifier unions** (`Identifier | @id-ref | string`) → UML attribute typed `Identifier` (`schema:PropertyValue`). The plain string is a shorthand for the bare identifier value.
- **Reference unions** (`cdif:Reference | @id-ref | string`) → UML attribute typed `cdif:Reference`. The plain string is a shorthand URL.
- **Multilingual-string unions** (`LanguageTaggedValue | string | array<…>`) → UML attribute typed `String`. JSON-LD `@language` tags carry the multilingualism. A future "language-localized" profile family will treat every string as a `{@value, @language}` object.
- **Polymorphic class unions** → UML attribute typed by an abstract supertype:
  - `Person | Organization` → `Agent`
  - `DataDownload | WebAPI` → `AbstractDistribution`
  - `GeoCoordinates | GeoShape` → `AbstractGeometry`
  - `AttributeComponent | DimensionComponent | …` → `cdi:DataStructureComponent`
- **`Concept` is special** — a Concept value MUST be a controlled-vocabulary entry (object or `@id`-ref). Plain strings are **not** permitted because vocabulary identity cannot be recovered from an unscoped string label.
- **`schema:PropertyValue` is polymorphic across three roles** ([CDIF Discovery Implementation Guide](https://github.com/Cross-Domain-Interoperability-Framework/discovery/blob/main/CDIFDiscoveryImplementationGuide.md#polymorphism-of-propertyvalue)). Three distinct target classes exist so the union-rule reduction applies per-role:
  - `Identifier` (for `schema:identifier`, `schema:sameAs`) — string shorthand permitted
  - `VariableMeasured` (for `schema:variableMeasured`) — no string shorthand
  - `AdditionalProperty` (for `schema:additionalProperty`) — no string shorthand (both `propertyID` and `value` are required)

The `datatypeSubstitutions` and `excludeDatatypes` fields automate the source-DataType side of the policy. Putting them in `configuration/ddi-cdi2cdifCore_mapping.json` (cascades via `composes`) sets a project-wide policy that every CDIF profile inherits.

### Round-trip with Wackerow's v1.0 tool

The v1.0 base-schema parts of the configs (sourceModel / targetModel skeleton, basic `map`/`new`/`merge` mappings, attributes, associations, sssom blocks in object form) are unchanged and would still be processed correctly by Wackerow's QVTo/Acceleo tool. The v1.1 extensions (`composes`, `isAbstract`, `generalization`, `datatypeSubstitutions`, `excludeDatatypes`, plus numeric `confidence` and top-level `$schema`) are not understood by the v1.0 tool. If you ran the configs through Wackerow's tool, you would get the basic profile UML structure but lose the abstract supertypes, profile composition, polymorphic-association collapse, and DataType-policy flattening. To round-trip, either strip the v1.1 fields with a small script or contribute the v1.1 semantics upstream.

---

## 1. Summary for a Non-Technical Audience

### What does this tool do?

The UCMIS M2M Transformation tool converts a UML model (a formal diagram describing the structure of data and concepts) from one representation into another. Specifically, it reads the **DDI-CDI** model — a widely used international standard for describing survey and research data concepts — and produces a **profile model** (such as DDSC or CDIF) that contains a carefully chosen subset of the DDI-CDI concepts, adapted to the requirements of that profile.

This conversion would traditionally require a data architect to manually replicate dozens of class definitions, attributes, and relationships across two large model files. The tool automates this fully: a single configuration file describes which concepts to include and how they should be mapped, and the tool does the rest.

### Why is this useful?

Different communities working with research data (statisticians, social scientists, archivists) use different but related conceptual models. The DDI-CDI model is the common reference point. Profile models derived from it must stay consistent with DDI-CDI while being lighter and more focused. Maintaining this consistency by hand is error-prone and time-consuming. This tool makes it repeatable, transparent, and auditable.

### What does the output look like?

The output is a standard UML model file (`.uml` format) that can be opened in any UML modelling tool that supports Eclipse UML2, such as Papyrus or Eclipse itself. The output contains:

- All selected classes, with their attributes and definitions.
- All selected associations between classes.
- A metadata block recording the model's name, version, language, and URI.
- Provenance records — machine-readable links back to the DDI-CDI concepts each profile concept was derived from, in both human-readable and RDF Turtle formats.

### What does a user need to do?

The only file a user normally needs to edit is the **JSON configuration file** (described in detail in section 5.7). This file lists which classes, attributes, and associations from DDI-CDI should appear in the profile model, and allows overriding names, definitions, and multiplicities as needed. The tool is then run from the command line. No programming is required to operate the tool once it is built.

---

## 2. Requirements

### 2.1 Runtime Requirements

The built product is a self-contained, headless Eclipse application. It includes all necessary Eclipse and EMF runtime libraries. The only external requirement to run the built binary is:

| Requirement | Version | Notes |
|---|---|---|
| Java (JRE or JDK) | 21 or later | OpenJDK or Oracle JDK both supported |

No Eclipse installation is needed at runtime. The tool is distributed as a directory containing a launcher executable and a `plugins/` directory.

### 2.2 Build Requirements

To build the tool from source, the following are required:

| Requirement | Version | Notes |
|---|---|---|
| Java Development Kit (JDK) | 21 | Must be JDK (not just JRE) |
| Apache Maven | 3.9 or later | Standard Maven installation |
| Internet access | — | Required to download Eclipse p2 dependencies during first build |

The build system uses **Eclipse Tycho** (a Maven plugin for building Eclipse applications). Tycho downloads all Eclipse dependencies automatically from the configured p2 repositories. No manual Eclipse installation is required to build.

### 2.3 Eclipse IDE Requirements (Development Only)

For working on the source code in Eclipse:

| Requirement | Version |
|---|---|
| Eclipse IDE for RCP and RAP Developers | 2025-12 |
| Eclipse QVTo SDK (installed via Help → Install New Software) | 3.11.1 |
| Eclipse UML2 (installed via Help → Install New Software) | 5.x (part of Eclipse Modeling Tools) |

The target platform file `ucmism2m.target/ucmism2m.target.target` must be activated in Eclipse before any development work (Window → Preferences → Plug-in Development → Target Platform → activate `UCMIS M2M Target Platform`).

---

## 3. Usage: Building and Running the Tool

### 3.1 Building

From the project root directory (the directory containing the top-level `pom.xml`), run:

```bash
# Build for the current platform only (Linux x86_64 by default — fastest)
mvn clean verify

# Build for all platforms (Linux, Windows, macOS x86_64 and ARM)
mvn clean verify -P all-platforms

# Build for Windows only
mvn clean verify -P windows-only

# Build for macOS only
mvn clean verify -P macos-only
```

The build output is placed in:

```
ucmism2m.product/target/products/ucmism2m/
```

Platform-specific ZIP archives are also created in that directory:

| Archive | Platform |
|---|---|
| `ucmism2m-linux.gtk.x86_64.zip` | Linux 64-bit |
| `ucmism2m-win32.win32.x86_64.zip` | Windows 64-bit |
| `ucmism2m-macosx.cocoa.x86_64.zip` | macOS Intel |
| `ucmism2m-macosx.cocoa.aarch64.zip` | macOS Apple Silicon |

### 3.2 Location of Binaries

After building and extracting the ZIP for your platform, the product directory has the following layout:

```
ucmism2m/                       ← root of the extracted archive
├── ucmism2m                    ← launcher executable (Linux/macOS)
├── ucmism2m.exe                ← launcher executable (Windows)
├── plugins/                    ← all OSGi bundles
│   ├── ucmism2m.app_1.0.0...jar
│   ├── ucmism2m.blackbox_1.0.0...jar
│   ├── ucmism2m.transformation_1.0.0...jar
│   └── ... (Eclipse runtime bundles)
└── configuration/
    └── config.ini
```

The main executable is `ucmism2m` (Linux/macOS) or `ucmism2m.exe` (Windows) in the root of the extracted directory.

### 3.3 Running the Tool

```bash
./ucmism2m \
  -input  /path/to/source-model.uml \
  -output /path/to/output-model.uml \
  -config /path/to/mapping-config.json
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `-input <path>` | Yes | Path to the source UML model file (`.uml` format, Eclipse UML2) |
| `-output <path>` | Yes | Path where the output UML model will be written (`.uml` format) |
| `-config <path>` | Yes | Path to the JSON mapping configuration file |

**Example (DDI-CDI to DDSC):**

```bash
./ucmism2m \
  -input  /data/models/DDI-CDI.uml \
  -output /data/models/DDSC.uml \
  -config /data/configs/ddi-cdi_to_ddsc.json
```

### 3.4 Interpreting Output

The tool prints progress to standard output:

```
UCMIS M2M Transformation Application
Eclipse 2025-12 | QVTo 3.11.1 | Java 21
=====================================
Input model: /data/models/DDI-CDI.uml
Output model: /data/models/DDSC.uml
Configuration: /data/configs/ddi-cdi_to_ddsc.json

Loading input model...
Input model loaded: 1 root elements
Loading transformation...
Transformation loaded successfully

Executing transformation...
Transformation completed successfully!

Saving output model...
Output model saved: /data/models/DDSC.uml
```

If the transformation fails, an error and stack trace are printed to standard error and the process exits with code 1.

---

## 4. Alternative: Python generator using `uml_to_schema.py`

Sibling repository `metadataBuildingBlocks/tools/uml_to_schema.py` contains a Python implementation that already does the same kind of UML transformation work for a different downstream purpose (DDI-CDI UML → CDIF building-block JSON Schemas). It has been augmented to ALSO emit Eclipse UML2 XMI for a profile, driven by the same ucmism2m JSON configuration files in `configuration/`. The five CDIF profile UML files in `generated/` were produced by this path.

### 4.1 Why a Python path exists

- Bypasses the Eclipse + Tycho + QVTo + Java 21 build chain. Useful for quick iteration on profile design and for environments where setting up the Eclipse toolchain is impractical.
- Reuses the parser, generalisation flattening, multiplicity handling, and type-closure logic already proven by the JSON Schema generation pathway.
- Output is canonical Eclipse UML2 XMI 2.5.1 — byte-compatible with the source DDI-CDI canonical XMI shape, openable in Papyrus, Magic Draw, and (via XMI 2.5.1 import) Enterprise Architect.

### 4.2 Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10 or later | Tested on 3.12 |
| `pyyaml` | any recent | Required by the existing schema-emit code path |
| `jsonschema` | any recent | Used to validate configs against the schema |

Install dependencies:

```bash
pip install pyyaml jsonschema
```

### 4.3 Running

From any working directory:

```bash
python <repo>/metadataBuildingBlocks/tools/uml_to_schema.py \
  --xmi    <repo>/../ucmis.m2t/model/ddi-cdi_1-1beta_canonical-unique-names.xmi \
  --config <repo>/ucmism2m/configuration/ddi-cdi2cdifCodelist_mapping.json \
  --emit-uml <repo>/ucmism2m/generated/cdifcodelist_1-0_canonical-unique-names.xmi
```

Arguments:

| Argument | Required | Description |
|---|---|---|
| `--xmi PATH` | Yes | Canonical Eclipse UML2 XMI 2.5.1 source (DDI-CDI). The current source is the DDI-CDI 1.1beta model `../ucmis.m2t/model/ddi-cdi_1-1beta_canonical-unique-names.xmi` (sibling UCMIS-M2T clone); a 1.0 model remains at `ucmism2m/model/ddi-cdi_canonical-unique-names-eclipse.xmi` for reference. |
| `--config PATH` | Yes (for profile UML emit) | A ucmism2m JSON configuration file from `configuration/`. |
| `--emit-uml PATH` | Yes (for profile UML emit) | Output path. Any extension works; `.xmi` is conventional, `.uml` is also fine. |

The `--config` flag short-circuits the JSON-Schema-emit pathway; you do not need to supply `--class`, `--bb-name`, or `--out-dir` when generating a profile UML.

The Python generator also has an Enterprise Architect XMI 1.1 emitter (`--emit-ea-xmi PATH`) for direct import into EA. As of this writing the EA-flavoured output imports the class and attribute structure correctly but EA v16.1 does not consistently resolve DataType references on attribute types. Use the canonical XMI 2.5.1 output (`--emit-uml`) for now, even when importing into EA — EA reads canonical XMI well.

### 4.4 Output and interpretation

The Python generator writes a single Eclipse UML2 XMI file containing:

- `uml:Model` with the profile's name and URI
- One `uml:Package` carrying the profile's classes, plus transitively-referenced DataTypes and Enumerations from the source DDI-CDI model
- For each target class: a `uml:Class` packagedElement with `ownedAttribute` properties (multiplicity, doc, type ref or primitive)
- For each association edge: a top-level `uml:Association` packagedElement with `memberEnd` / `ownedEnd` references

The closure walker pulls in only the types the selected classes actually use. Run-time warnings on `stderr` flag associations whose source or target class lives in a different profile (e.g., `Dataset_variableMeasured_VariableMeasured` in the DataDescription config when `Dataset` is part of Core, not DataDescription — these associations are skipped and noted).

### 4.5 What the Python path does NOT yet do

- **Provenance Dependency** (`Client_dependsOn_Supplier`) elements described in the original ucmism2m `concept/requirements.txt` — only the underlying mapping is emitted; the SSSOM block in the config is read but not yet surfaced as a UML ownedComment or RDF Turtle block on the target class.
- **Cross-profile composition** — each profile UML is a standalone file. Associations whose subject or object class lives in a different profile (e.g., references from DataDescription to Core's `Dataset`) are dropped with a warning, not emitted as foreign-class references.
- **EA XMI 1.1 datatype resolution** — see note in section 4.3.

These are tracked as Phase 3 work; the Eclipse / QVTo path is expected to address them in its long-term implementation.
