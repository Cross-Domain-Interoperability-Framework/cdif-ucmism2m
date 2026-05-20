# Feeding the five generated CDIF profile XMIs through UCMIS-M2T

This guide reflects the **actual** workflow after inspecting the local clone at
`C:\GithubC\ucmis.m2t\`. (An earlier draft of
this file guessed at a Tycho RCP-product structure — that was wrong; the real
project is an Eclipse Acceleo project run via `.launch` configurations.)

## What UCMIS-M2T expects

UCMIS-M2T has a single Java entry point `ucmis.m2t.main.M2tMaster` that takes
four positional arguments:

```
<inputXMI>  <outputDir>  <generic.properties>  <profile.properties>
```

- `inputXMI` — a canonical Eclipse UML2 XMI (XMI 2.5.1) for the profile.
- `outputDir` — where to put generated artefacts. Existing launches point at
  the `generated/` folder of the `ucmis.m2t` project.
- `generic.properties` — global settings (which artefacts to emit, diagram
  colours, tooltips, UML-to-RDF type mapping). Same for every profile.
- `<profile>.properties` — per-profile settings: `RDF_NS`, `RDF_PREFIX`,
  Sphinx theme, copyright. **The filename must equal the model's
  `ModelIdentification.acronym` attribute** (e.g. `CDIFCodelist.properties`
  for a model whose acronym is `CDIFCodelist`).

The Acceleo template emits a number of artefacts in one go (controlled by the
boolean toggles in `generic.properties`): RST source for Sphinx, XSD, JSON-LD,
JSON Schema, ontology Turtle, SHACL shapes, ShEx shapes, plus assorted reports.

The full publication pipeline is **four steps**, all defined as `.launch`
configurations under `ucmis.m2t/launch/`:

| Step | Purpose |
|---|---|
| Step 1 — `<profile>` | Run UCMIS-M2T (Acceleo) on the profile's XMI; produces RST + XSD + JSON-LD + ontology + SHACL etc. |
| Step 2 — Pre Sphinx UCMIS Mapping Documentation | Intermediate RST polishing. |
| Step 3 — `<profile>` Sphinx Cmd | Run Sphinx (HTML) on the polished RST. |
| Step 4 — post Sphinx | Final tidy-up. |

## What we did to add CDIF Core / Discovery / DataDescription / DataStructure

The clone shipped with Step 1 launch configs for **CDIF Codelist** and
**CDIF DDSC** only. We added the four missing profiles by mirroring those:

**Files added under `ucmis.m2t/`:**

```
src/ucmis/m2t/property/CDIFCore.properties
src/ucmis/m2t/property/CDIFDiscovery.properties
src/ucmis/m2t/property/CDIFDataDescription.properties
src/ucmis/m2t/property/CDIFDataStructure.properties
launch/Step 1 - CDIF Core.launch
launch/Step 1 - CDIF Discovery.launch
launch/Step 1 - CDIF DataDescription.launch
launch/Step 1 - CDIF DataStructure.launch
```

Each property file sets `RDF_NS`/`RDF_PREFIX` to the profile's own CDIF URI by
default; edit if you prefer to use the underlying vocabulary's namespace
(e.g. `http://schema.org/` for Core / Discovery / DataDescription). The
`CDIFCodelist.properties` example uses `http://www.w3.org/2004/02/skos/core#`
on the same principle.

Each `.launch` config points at a profile-specific XMI in `ucmis.m2t/model/`
using the existing naming convention
(`<acronym-lowercased>_canonical-unique-names-eclipse.xmi`).

## Staging the XMIs

`ucmism2m/script/stage-xmis-to-m2t.ps1` copies the five generated XMI files
from `ucmism2m/generated/` into `ucmis.m2t/model/`, renaming them to the
convention the launch configs expect:

```
cdifCodelist.xmi         -> cdifcodelist_canonical-unique-names-eclipse.xmi
cdifCore.xmi             -> cdifcore_canonical-unique-names-eclipse.xmi
cdifDiscovery.xmi        -> cdifdiscovery_canonical-unique-names-eclipse.xmi
cdifDataDescription.xmi  -> cdifdatadescription_canonical-unique-names-eclipse.xmi
cdifDataStructure.xmi    -> cdifdatastructure_canonical-unique-names-eclipse.xmi
```

Run it any time you regenerate the XMIs:

```powershell
.\ucmism2m\script\stage-xmis-to-m2t.ps1
```

The script defaults to `C:\GithubC\ucmis.m2t`;
pass `-M2tRoot <path>` if your clone lives elsewhere.

Note: the existing `cdifcodelist_canonical-unique-names-eclipse.xmi` in
`ucmis.m2t/model/` was overwritten by the staging run. Wackerow's earlier
version remains as `cdifcodelist_canonical-unique-names-eclipse2.xmi`, so the
diff is recoverable.

## Running the pipeline

Once the XMIs are staged and the project is open in Eclipse with Acceleo 4.2
installed (per `ucmism2m/documentation/installation_acceleo.md`):

1. **Project Explorer → ucmis.m2t → launch/**
2. For each profile you want to publish, right-click
   **`Step 1 - CDIF <profile>.launch` → Run As → "Step 1 - CDIF <profile>"**.
3. Repeat for **Step 2 — Pre Sphinx UCMIS Mapping Documentation**.
4. Repeat for **Step 3 — `<profile>` Sphinx Cmd**.
5. Repeat for **Step 4 — post Sphinx**.
6. Outputs land under `ucmis.m2t/generated/`.

If you only want the XSD / JSON-LD / Turtle structured outputs and don't need
the HTML site, **Step 1 alone is sufficient**. Steps 2–4 are the Sphinx HTML
pipeline.

## Quick smoke test before doing all four

Try the simplest profile first to confirm the toolchain is healthy on your
machine:

1. Right-click `Step 1 - CDIF Codelist.launch` → Run As.
2. After it finishes, check `ucmis.m2t/generated/` for new files
   (Sphinx RST under a `CDIFCodelist/` sub-folder, plus XSD/JSON-LD/Turtle).

If that works, run the other four. If it fails, the Eclipse Error Log will
tell you why (most common cause: Acceleo 4.2 not installed correctly — see
the install doc).

## Headless (CLI) execution — if you really need it

UCMIS-M2T does not ship a built RCP launcher. There are two paths to running
it outside Eclipse:

1. `ucmis.m2t/standalone/build.xml` — an Ant script that invokes
   `ucmis.m2t.main.M2tMaster` against a hard-coded classpath. Edit the
   `MODEL`, `OUTPUT_DIR`, and classpath `fileset dir=` to match your local
   Eclipse `.p2/pool/plugins` directory, then `ant generate`.
2. Eclipse headless: launch Eclipse with `-noSplash -application
   org.eclipse.ant.core.antRunner` pointing at a custom Ant target. Mature,
   but fiddly to set up; the Eclipse-UI path is faster for one-off runs.

For now I recommend the Eclipse-UI workflow above. If you'd like an Ant
target that uses your local paths I can write one once you have the Eclipse
install working.
