# Build the CDIF profile model browser end-to-end.
#
#   1. Run uml_to_schema.py for each of the 5 profiles to produce:
#        ucmism2m/generated/<profile>.xmi        (canonical UML XMI 2.5)
#        metadataBuildingBlocks/build/plantuml/<profile>/*.pu
#        metadataBuildingBlocks/build/plantuml/<profile>/*.svg  (via plantuml.jar)
#   2. Pre-scan all configs to build a cross-profile class registry.
#   3. Re-run HTML emit for each profile with the registry so cross-profile
#      references become clickable links.
#   4. Open the root index in the default browser.
#
# Requires: miniconda Python on PATH (or update $python), Java 11+,
#           plantuml.jar (default: ../../metadataBuildingBlocks/tools/plantuml.jar).
[CmdletBinding()]
param(
    [string]$JavaExe = "C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe",
    [string]$PlantUmlJar = "$PSScriptRoot\..\..\metadataBuildingBlocks\tools\plantuml.jar",
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$python = "C:\Users\smrTu\miniconda3\python.exe"
$repoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$tool = Join-Path $repoRoot "metadataBuildingBlocks\tools\uml_to_schema.py"
# DDI-CDI 1.1beta canonical UML (sourced from the UCMIS-M2T reference repo).
$xmi  = "C:\Users\smrTu\OneDrive\Documents\GithubC\ucmis.m2t\model\ddi-cdi_1-1beta_canonical-unique-names.xmi"
$configDir = Join-Path $repoRoot "ucmism2m\configuration"
$genDir = Join-Path $repoRoot "ucmism2m\generated"
$pumlOut = Join-Path $repoRoot "metadataBuildingBlocks\build\plantuml"
$htmlOut = Join-Path $repoRoot "metadataBuildingBlocks\build\field-level-documentation"

$profiles = @(
    @{ slug = "cdifCodelist";        config = "ddi-cdi2cdifCodelist_mapping.json";        umlName = "CDIFCodelist" },
    @{ slug = "cdifCore";            config = "ddi-cdi2cdifCore_mapping.json";            umlName = "CDIFCore" },
    @{ slug = "cdifDiscovery";       config = "ddi-cdi2cdifDiscovery_mapping.json";       umlName = "CDIFDiscovery" },
    @{ slug = "cdifDataDescription"; config = "ddi-cdi2cdifDataDescription_mapping.json"; umlName = "CDIFDataDescription" },
    @{ slug = "cdifDataStructure";   config = "ddi-cdi2cdifDataStructure_mapping.json";   umlName = "CDIFDataStructure" }
)

Write-Host "==> Step 1: emit XMI + PlantUML + SVG for each profile"
foreach ($p in $profiles) {
    $cfg = Join-Path $configDir $p.config
    $xmiOut = Join-Path $genDir "$($p.slug).xmi"
    $puDir = Join-Path $pumlOut $p.slug
    Write-Host "    $($p.slug) ..."
    & $python $tool --xmi $xmi --config $cfg `
        --emit-uml $xmiOut `
        --emit-puml $puDir `
        --plantuml-jar $PlantUmlJar `
        --java-exe $JavaExe
    if ($LASTEXITCODE -ne 0) { throw "Failed: $($p.slug)" }
}

Write-Host "==> Step 2: build cross-profile class registry"
$registry = @{}
foreach ($p in $profiles) {
    $cfg = Join-Path $configDir $p.config
    $json = Get-Content $cfg -Raw | ConvertFrom-Json
    foreach ($m in $json.mapping.class) {
        $name = $m.targetClass
        if ($name) { $registry[$name] = $p.umlName }
    }
}
# DataTypes shared across profiles: scan generated .pu DataType files (each
# profile pulls in only the datatypes it actually references).
foreach ($p in $profiles) {
    $dtDir = Join-Path $pumlOut "$($p.slug)\DataTypes"
    if (Test-Path $dtDir) {
        Get-ChildItem $dtDir -Filter *.pu | ForEach-Object {
            $name = $_.BaseName
            if (-not $registry.ContainsKey($name)) { $registry[$name] = $p.umlName }
        }
    }
}
$registryPath = Join-Path $htmlOut "_registry.json"
New-Item -ItemType Directory -Force -Path $htmlOut | Out-Null
$registry | ConvertTo-Json -Depth 3 | Set-Content -Path $registryPath -Encoding utf8
Write-Host "    Wrote registry with $($registry.Count) entries: $registryPath"

Write-Host "==> Step 3: emit HTML browser for each profile (with cross-profile links)"
foreach ($p in $profiles) {
    $cfg = Join-Path $configDir $p.config
    $puDir = Join-Path $pumlOut $p.slug
    Write-Host "    $($p.slug) ..."
    & $python $tool --xmi $xmi --config $cfg `
        --emit-html $htmlOut `
        --puml-dir $puDir `
        --cross-profile-registry $registryPath
    if ($LASTEXITCODE -ne 0) { throw "Failed HTML: $($p.slug)" }
}

$indexPath = Join-Path $htmlOut "index.html"
Write-Host ""
Write-Host "DONE. Open: $indexPath"
if (-not $NoOpen) {
    Start-Process $indexPath
}
