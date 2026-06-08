# Generated profile UML models

This folder holds Eclipse UML2 XMI 2.5.1 files produced by running the Python generator (`metadataBuildingBlocks/tools/uml_to_schema.py --emit-uml`) against the configurations in `../configuration/`. Each file is a standalone UML model for one CDIF profile (or composite), suitable for importing into Enterprise Architect, Papyrus, or any other tool that reads canonical XMI 2.5.1.

## Current contents (v1.1, 2026-06)

All XMI files in this folder are at CDIF profile **version 1.1** — the conformance URIs migrated from `/1.0/` to `/1.1/` in mBB commit `958360635` on 2026-06-02 and the configs/XMIs were bumped to match.

Filenames follow the canonical pattern `<lower-acronym>_<major>-<minor>_canonical-unique-names.xmi`.

### Per-profile XMIs (8)

| File | Source configuration | Approx. size | Classes |
|---|---|---:|---|
| `cdifcodelist_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifCodelist_mapping.json` | 60 KB | ConceptScheme, Concept, CatalogRecord stub; Identifier + Reference DataTypes |
| `cdifconceptscheme_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifConceptScheme_mapping.json` | 49 KB | ConceptScheme, Concept, CatalogRecord stub (looser SKOS shape than Codelist: skos:altLabel / note / schema:version added; no schema:identifier PropertyValue / dateModified / license) |
| `cdifcore_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifCore_mapping.json` | 191 KB | Dataset, Agent / Person / Organization, AbstractDistribution / DataDownload / WebAPI, Action / EntryPoint / ActionResult / PropertyValueSpecification (WebAPI potentialAction subtree), Contributor, MonetaryGrant, ProvActivity, CatalogRecord, DefinedTerm, AdditionalProperty, CdifConceptOrTerm union shorthand |
| `cdifdiscovery_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifDiscovery_mapping.json` | 106 KB | VariableMeasured (fattened), SpatialExtent, AbstractGeometry / GeoCoordinates / GeoShape / Geometry (GeoSPARQL), TemporalExtent / Instant / TimePosition (OWL-Time), QualityMeasure + QualityMeasurement (DQV), DefinedTerm (fattened) |
| `cdifdatadescription_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifDataDescription_mapping.json` | 285 KB | InstanceVariable (fattened), ValueAndConceptDescription, EnumerationDomain, ComponentPosition; Statistics extension (Statistics / CategoryStatistics / StatisticsCollection / Category); TabularTextDataSet / StructuredDataSet (PhysicalDataSet variants); PhysicalMapping / TextMapping / LocatorMapping; DataFingerprint |
| `cdifdatastructure_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifDataStructure_mapping.json` | 528 KB | DataDownload, DataStructure + abstract DataStructureComponent + variant/component generalizations, RepresentedVariable, DescriptorVariable, value-domain classes (Substantive / Sentinel / Descriptor + EnumerationDomain + ValueAndConceptDescription), UnitType, DefinedTerm, CdifConceptOrTerm; PrimaryKey / ForeignKey + generic `has` associations |
| `cdifmanifest_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifManifest_mapping.json` | 99 KB | ArchivePart, abstract Mapping family (PhysicalMapping / TextMapping / LocatorMapping), dataset variants (AbstractDataSet + TabularTextDataSet / StructuredDataSet), DefinedTerm |
| `cdifprovenance_1-1_canonical-unique-names.xmi` | `ddi-cdi2cdifProvenance_mapping.json` | 242 KB | ProvActivity, Instrument (fattened with manufacturer / model / owner), AgentInRole, action-chaining via schema:object back-references |

### Composite XMIs (3)

Composite profiles aggregate per-profile modules via the `composes` chain in their config. They share class IDs with their constituent modules so that an importer sees one merged graph.

| File | Source configuration | Approx. size | Composes |
|---|---|---:|---|
| `corediscovery_1-1_canonical-unique-names.xmi` | `ddi-cdi2CoreDiscovery_mapping.json` | 289 KB | Core ← Discovery |
| `discoverydatadescription_1-1_canonical-unique-names.xmi` | `ddi-cdi2DiscoveryDataDescription_mapping.json` | 574 KB | Core ← Discovery ← DataDescription |
| `discoverydatadescriptionstructure_1-1_canonical-unique-names.xmi` | `ddi-cdi2DiscoveryDataDescriptionStructure_mapping.json` | 846 KB | Core ← Discovery ← DataDescription ← DataStructure |

### Audit status

All 8 per-profile XMIs audit clean (0 / 0 real gaps) against both the mBB `_sources/profiles/cdifProfile/<name>/resolvedSchema.json` and the published release schemas in the sibling `profile-<name>/` repositories (`reviewRevision202606` branch). The audit is run by `../script/audit_schema_vs_uml.py`; see `../AGENTS.md` for the add-a-profile workflow.

**Audit caveat (2026-05):** the audit checks whether each schema *name* is covered somewhere; it does NOT verify that an association is anchored on the right source/target class. Eyeball the model-browser SVGs for the new shapes (especially the Jun-2026 `schema:subjectOf` re-anchoring) to confirm anchoring is correct.

### Other files in this folder

| File | Purpose |
|---|---|
| `modelTesting.feap` | Enterprise Architect project file used to interactively review/test the generated XMIs. Not produced by the generator. |
| `cdif-ddi-cdi-mappings.sssom.tsv` | SSSOM mapping table (DDI-CDI ↔ CDIF) emitted by `../script/emit_sssom.py`. Useful for tracing provenance of each CDIF class back to a DDI-CDI source class. |
| `CDIFCore.jpg`, `ConceptOrTermSketch.jpg`, `DataDownloadSketch.jpg`, `DatasetVariableSketch.jpg` | Hand-drawn / annotated reference sketches kept alongside the generated outputs for context. |

## Format

Eclipse UML2 + OMG XMI 2.5.1:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xmi:XMI xmlns:StandardProfile="http://www.eclipse.org/uml2/5.0.0/UML/Profile/Standard"
         xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML"
         xmlns:xmi="http://www.omg.org/spec/XMI/20131001">
  <uml:Model xmi:id="..." xmi:uuid="...">
    <name>CDIFCodelist</name>
    <URI>https://w3id.org/cdif/codelist/1.1/xmi/</URI>
    <packagedElement xmi:type="uml:Package">
      <packagedElement xmi:type="uml:DataType">...</packagedElement>
      ...
      <packagedElement xmi:type="uml:Package">  <!-- Classes sub-package -->
        <packagedElement xmi:type="uml:Class">...</packagedElement>
        ...
      </packagedElement>
      <packagedElement xmi:type="uml:Association">...</packagedElement>
    </packagedElement>
  </uml:Model>
</xmi:XMI>
```

Each model carries a model-level `ModelIdentification` DataType (constant, read-only prefix/version/title/language/uri); primitive-typed attributes reference Eclipse's standard `PrimitiveTypes.xmi` by href; and value types `Identifier` and `Reference` are emitted as `uml:DataType`. The `.xmi` extension is conventional; `.uml` is also accepted by Eclipse tooling and is functionally equivalent.

## Regenerating

These files are output — not committed for human editing. The full pipeline (XMI + PlantUML + SVG + HTML model browser) is driven by `../script/build-docs.ps1`:

```powershell
# Full pipeline: XMI -> PlantUML -> SVG -> HTML model browser at
# ../../metadataBuildingBlocks/cdif-uml-model/. Skip Step 0 (the OGC bblocks
# postprocessor) unless _sources/ has been edited.
& ..\script\build-docs.ps1 -SkipBblocks
```

For just the XMI files (no diagrams or HTML), call the Python generator directly:

```powershell
$base = "<repository-root>"
$profiles = 'cdifCodelist','cdifConceptScheme','cdifCore','cdifDiscovery','cdifDataDescription','cdifDataStructure','cdifManifest','cdifProvenance'
foreach ($c in $profiles) {
    $out = "$($c.ToLower())_1-1_canonical-unique-names.xmi"
    python "$base\metadataBuildingBlocks\tools\uml_to_schema.py" `
        --xmi    "$base\..\ucmis.m2t\model\ddi-cdi_1-1beta_canonical-unique-names.xmi" `
        --config "$base\ucmism2m\configuration\ddi-cdi2${c}_mapping.json" `
        --emit-uml "$base\ucmism2m\generated\$out"
}
# Composites: CoreDiscovery, DiscoveryDataDescription, DiscoveryDataDescriptionStructure
```

POSIX equivalent:

```bash
base="<repository-root>"
for c in cdifCodelist cdifConceptScheme cdifCore cdifDiscovery cdifDataDescription cdifDataStructure cdifManifest cdifProvenance; do
    out="$(echo "$c" | tr '[:upper:]' '[:lower:]')_1-1_canonical-unique-names.xmi"
    python "$base/metadataBuildingBlocks/tools/uml_to_schema.py" \
        --xmi    "$base/../ucmis.m2t/model/ddi-cdi_1-1beta_canonical-unique-names.xmi" \
        --config "$base/ucmism2m/configuration/ddi-cdi2${c}_mapping.json" \
        --emit-uml "$base/ucmism2m/generated/$out"
done
```

The version-stamped filename (`1-1` here) comes from `targetModel.majorVersion`/`minorVersion` in each config — bumping the version in the configs and re-running produces a new set of files alongside the older ones. The previous `_1-0_` snapshots (including the alternative-Wackerow `AW-cdifcodelist_1-0_…` build) have been moved to `archive/` as historical reference; the active outputs are the `_1-1_` files at the top level of this folder.

Both the generator and the configuration files are deterministic: re-running on the same inputs produces byte-identical output. Diffing two generated files highlights exactly which configuration change caused which model change.

## Importing into Enterprise Architect

Enterprise Architect v16.1 reads canonical XMI 2.5.1 well:

1. **Project Browser** → right-click target package → **Import/Export** → **Import Model from XMI**.
2. Browse to the `.xmi` file. Accept the default options. EA will create classes, attributes, datatypes, and associations in the chosen package.

Note: the Python generator also has an `--emit-ea-xmi PATH` flag that writes Enterprise Architect's native XMI 1.1 format. As of this writing the EA 1.1 output imports the class and attribute structure correctly but EA v16.1 does not consistently resolve DataType references on attribute types. **Prefer the canonical XMI 2.5.1 output (the files in this folder).**

## Importing into Papyrus / Eclipse UML2

Open the `.xmi` file in any Eclipse with the UML2 plug-in. The file is canonical UML2 5.0; no transformation step is needed. Save-as `.uml` if your downstream tooling expects that extension.

## Stale files

If you find leftover files or sub-folders here from earlier generator runs (for example a `cdifCodelistProfile/` folder containing schema-emit scaffolding, or `${c}-from-config.uml` files created by a misquoted shell loop), they are safe to delete; only the 11 `.xmi` files listed above plus the historical snapshots under `archive/` are intended outputs.
