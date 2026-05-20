# Build the CDIF profile model browser end-to-end.
#
#   0. (optional) Run the OGC bblocks postprocessor on metadataBuildingBlocks/_sources/
#      via Docker. Regenerates resolvedSchema.json files, generateddocs/, and
#      the bblocks register. Only runs if any _sources/ file is newer than
#      build/register.json, unless -ForceBblocks is set. Skip with -SkipBblocks
#      (useful when iterating only on ucmism2m configs).
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
#           Step 0 additionally needs Docker Desktop running.
[CmdletBinding()]
param(
    [string]$JavaExe = "C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe",
    [string]$PlantUmlJar = "$PSScriptRoot\..\..\metadataBuildingBlocks\tools\plantuml.jar",
    [switch]$NoOpen,
    [switch]$SkipBblocks,
    [switch]$ForceBblocks
)

$ErrorActionPreference = "Stop"
$python = "C:\Users\smrTu\miniconda3\python.exe"
$repoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$tool = Join-Path $repoRoot "metadataBuildingBlocks\tools\uml_to_schema.py"
# DDI-CDI 1.1beta canonical UML (sourced from the UCMIS-M2T reference repo).
$xmi  = "C:\GithubC\ucmis.m2t\model\ddi-cdi_1-1beta_canonical-unique-names.xmi"
$configDir = Join-Path $repoRoot "ucmism2m\configuration"
$genDir = Join-Path $repoRoot "ucmism2m\generated"
# Outputs go OUTSIDE metadataBuildingBlocks/build/ so the OGC bblocks
# postprocess workflow (which manages build/) can't accidentally wipe them.
# The cdif-uml-model/ tree at repo root is the published model browser; its
# _plantuml/ subdir holds the intermediate .pu/.svg sources for diagram embed.
$pumlOut = Join-Path $repoRoot "metadataBuildingBlocks\cdif-uml-model\_plantuml"
$htmlOut = Join-Path $repoRoot "metadataBuildingBlocks\cdif-uml-model"

$profiles = @(
    @{ slug = "cdifCodelist";        config = "ddi-cdi2cdifCodelist_mapping.json";        umlName = "CDIFCodelist" },
    @{ slug = "cdifCore";            config = "ddi-cdi2cdifCore_mapping.json";            umlName = "CDIFCore" },
    @{ slug = "cdifDiscovery";       config = "ddi-cdi2cdifDiscovery_mapping.json";       umlName = "CDIFDiscovery" },
    @{ slug = "cdifDataDescription"; config = "ddi-cdi2cdifDataDescription_mapping.json"; umlName = "CDIFDataDescription" },
    @{ slug = "cdifDataStructure";   config = "ddi-cdi2cdifDataStructure_mapping.json";   umlName = "CDIFDataStructure" }
)

$mbbDir = Join-Path $repoRoot "metadataBuildingBlocks"
$mbbSources = Join-Path $mbbDir "_sources"
# bblocks-postprocess writes to build-local/ by default (gitignored, regenerable);
# the committed build/ is populated by the CI publish workflow. We track the
# local register for staleness so iterating on _sources/ triggers a rebuild.
$mbbRegister = Join-Path $mbbDir "build-local\register.json"

function Test-BblocksStale {
    if (-not (Test-Path $mbbRegister)) { return $true }
    $regTime = (Get-Item $mbbRegister).LastWriteTime
    # Any source file newer than the register => stale
    $newer = Get-ChildItem -Path $mbbSources -Recurse -File `
        -Include *.yaml,*.yml,*.json,*.md,*.shacl -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt $regTime } |
        Select-Object -First 1
    return $null -ne $newer
}

if (-not $SkipBblocks) {
    $needs = $ForceBblocks -or (Test-BblocksStale)
    if ($needs) {
        Write-Host "==> Step 0: run OGC bblocks postprocessor (Docker) on metadataBuildingBlocks/_sources/"
        # Mirror build.sh; Docker handles the volume mount via the host path.
        $hostPath = $mbbDir -replace '\\','/'
        & docker run --pull=always --rm --workdir /workspace `
            -v "${hostPath}:/workspace" `
            ghcr.io/opengeospatial/bblocks-postprocess `
            --clean true --base-url "http://localhost:9090/register/"
        if ($LASTEXITCODE -ne 0) { throw "bblocks postprocessor failed (exit $LASTEXITCODE). Re-run with -SkipBblocks to bypass, or check Docker Desktop is running." }
    } else {
        Write-Host "==> Step 0: bblocks register up to date; skipping (force with -ForceBblocks)"
    }
} else {
    Write-Host "==> Step 0: bblocks build skipped (-SkipBblocks)"
}

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
