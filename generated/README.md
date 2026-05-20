# Generated profile UML models

This folder holds Eclipse UML2 XMI 2.5.1 files produced by running the UCMIS M2M transformation against the configurations in `../configuration/`. Each file is a standalone UML model for one CDIF profile, suitable for importing into Enterprise Architect, Papyrus, or any other tool that reads canonical XMI 2.5.1.

## Current contents

Filenames follow the canonical pattern `<lower-acronym>_<major>-<minor>_canonical-unique-names.xmi`.

| File | Source configuration | Approx. size | Classes |
|---|---|---:|---:|
| `cdifcodelist_1-0_canonical-unique-names.xmi` | `ddi-cdi2cdifCodelist_mapping.json` | 84 KB | ConceptScheme, Concept (plus Identifier/Reference DataTypes and the XSD DataTypes) |
| `cdifcore_1-0_canonical-unique-names.xmi` | `ddi-cdi2cdifCore_mapping.json` | 160 KB | Dataset, Person, Organization, DataDownload, WebAPI, Contributor, MonetaryGrant, ProvActivity, CatalogRecord, DefinedTerm, DerivedFrom (Identifier and Reference are emitted as DataTypes) |
| `cdifdiscovery_1-0_canonical-unique-names.xmi` | `ddi-cdi2cdifDiscovery_mapping.json` | 224 KB | Dataset, VariableMeasured, SpatialExtent, TemporalExtent, QualityMeasure (+ composed Core) |
| `cdifdatadescription_1-0_canonical-unique-names.xmi` | `ddi-cdi2cdifDataDescription_mapping.json` | 316 KB | InstanceVariable, VariableMeasured, DataDownload, PrimaryKey, PrimaryKeyComponent, Statistic, SubstantiveValueDomain, SentinelValueDomain, EnumerationDomain, PhysicalMapping (+ composed Discovery/Core) |
| `cdifdatastructure_1-0_canonical-unique-names.xmi` | `ddi-cdi2cdifDataStructure_mapping.json` | 464 KB | full DDI-CDI structural tree: DataStructure + variants, the Component subclasses, RepresentedVariable, ReferenceVariable, DescriptorVariable, InstanceVariable, the ValueDomain subclasses, PrimaryKey, PrimaryKeyComponent, ComponentPosition (+ composed DataDescription/Discovery/Core) |

All five validate as well-formed canonical Eclipse UML2 (XMI 2.5.1) and round-trip cleanly through the tool's own parser. Each model carries a model-level `ModelIdentification` DataType (constant, read-only prefix/version/title/language/uri); primitive-typed attributes reference Eclipse's standard `PrimitiveTypes.xmi` by href; and value types `Identifier` and `Reference` are emitted as `uml:DataType`. The DataDescription file currently silences three cross-profile associations (`Dataset_variableMeasured_VariableMeasured`, `Dataset_hasPrimaryKey_PrimaryKey`, `Dataset_statistics_Statistic`) because `Dataset` lives in Core, not DataDescription; the generator emits warnings naming each skipped association.

## Format

Eclipse UML2 + OMG XMI 2.5.1:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xmi:XMI xmlns:StandardProfile="http://www.eclipse.org/uml2/5.0.0/UML/Profile/Standard"
         xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML"
         xmlns:xmi="http://www.omg.org/spec/XMI/20131001">
  <uml:Model xmi:id="..." xmi:uuid="...">
    <name>CDIFCodelist</name>
    <URI>https://w3id.org/cdif/codelist/1.0/xmi/</URI>
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

This is the same on-the-wire format as the existing `cdif-umlmodel/ddsc/model/cdif-ddsc_canonical-unique-names-eclipse.xmi` and `cdif-umlmodel/codelist/model/cdif-codelist_canonical-unique-names.xmi` reference files. The `.xmi` extension is conventional; `.uml` is also accepted by Eclipse tooling and is functionally equivalent.

## Regenerating

These files are not committed for human editing — they are output. Re-create them by running the Python generator described in `../README.md §4`:

```powershell
$base = "<repository-root>"
foreach ($c in 'cdifCodelist','cdifCore','cdifDiscovery','cdifDataDescription','cdifDataStructure') {
    $out = "$($c.ToLower())_1-0_canonical-unique-names.xmi"
    python "$base\metadataBuildingBlocks\tools\uml_to_schema.py" `
        --xmi    "$base\..\ucmis.m2t\model\ddi-cdi_1-1beta_canonical-unique-names.xmi" `
        --config "$base\ucmism2m\configuration\ddi-cdi2${c}_mapping.json" `
        --emit-uml "$base\ucmism2m\generated\$out"
}
```

POSIX equivalent:

```bash
base="<repository-root>"
for c in cdifCodelist cdifCore cdifDiscovery cdifDataDescription cdifDataStructure; do
    out="$(echo "$c" | tr '[:upper:]' '[:lower:]')_1-0_canonical-unique-names.xmi"
    python "$base/metadataBuildingBlocks/tools/uml_to_schema.py" \
        --xmi    "$base/../ucmis.m2t/model/ddi-cdi_1-1beta_canonical-unique-names.xmi" \
        --config "$base/ucmism2m/configuration/ddi-cdi2${c}_mapping.json" \
        --emit-uml "$base/ucmism2m/generated/$out"
done
```

Both the generator and the configuration files are deterministic: re-running on the same inputs produces byte-identical output. Diffing two generated files highlights exactly which configuration change caused which model change.

## Importing into Enterprise Architect

Enterprise Architect v16.1 reads canonical XMI 2.5.1 well:

1. **Project Browser** → right-click target package → **Import/Export** → **Import Model from XMI**.
2. Browse to the `.xmi` file. Accept the default options. EA will create classes, attributes, datatypes, and associations in the chosen package.

Note: the Python generator also has an `--emit-ea-xmi PATH` flag that writes Enterprise Architect's native XMI 1.1 format. As of this writing the EA 1.1 output imports the class and attribute structure correctly but EA v16.1 does not consistently resolve DataType references on attribute types. **Prefer the canonical XMI 2.5.1 output (the files in this folder).**

## Importing into Papyrus / Eclipse UML2

Open the `.xmi` file in any Eclipse with the UML2 plug-in. The file is canonical UML2 5.0; no transformation step is needed. Save-as `.uml` if your downstream tooling expects that extension.

## Stale files

If you find leftover files or sub-folders here from earlier generator runs (for example, a `cdifCodelistProfile/` folder containing schema-emit scaffolding, or `${c}-from-config.uml` files created by a misquoted shell loop), they are safe to delete; only the five `.xmi` files listed above are intended outputs of the current configuration set.
