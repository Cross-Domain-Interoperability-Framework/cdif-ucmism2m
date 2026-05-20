# Copy the five CDIF profile XMIs produced by UCMIS-M2M into the
# UCMIS-M2T model/ folder, renaming them to the convention UCMIS-M2T's
# launch configurations expect (lowercase, "_canonical-unique-names-eclipse.xmi"
# suffix). After this runs, open ucmis.m2t in Eclipse and use the
# "Step 1 - CDIF <profile>.launch" configurations.
#
# Usage:
#   .\stage-xmis-to-m2t.ps1
#   .\stage-xmis-to-m2t.ps1 -M2tRoot "C:\path\to\ucmis.m2t"
#
# The default M2tRoot is C:\GithubC\ucmis.m2t
# (matching the user's local clone).

[CmdletBinding()]
param(
    [string]$M2tRoot = "C:\GithubC\ucmis.m2t",
    [string]$GeneratedDir
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Ucmism2mRoot = Split-Path -Parent $ScriptDir
if (-not $GeneratedDir) { $GeneratedDir = Join-Path $Ucmism2mRoot "generated" }
$ModelDir = Join-Path $M2tRoot "model"

if (-not (Test-Path $ModelDir)) {
    Write-Host "ERROR: UCMIS-M2T model folder not found: $ModelDir" -ForegroundColor Red
    exit 1
}

# Mapping: ucmism2m output filename -> UCMIS-M2T model filename (the convention
# the existing launch configs use: lowercase, no camel case, with the canonical
# suffix). Add new profiles here as more are authored.
$Mapping = @{
    "cdifCodelist.xmi"        = "cdifcodelist_canonical-unique-names-eclipse.xmi"
    "cdifCore.xmi"            = "cdifcore_canonical-unique-names-eclipse.xmi"
    "cdifDiscovery.xmi"       = "cdifdiscovery_canonical-unique-names-eclipse.xmi"
    "cdifDataDescription.xmi" = "cdifdatadescription_canonical-unique-names-eclipse.xmi"
    "cdifDataStructure.xmi"   = "cdifdatastructure_canonical-unique-names-eclipse.xmi"
}

Write-Host "Source:  $GeneratedDir"
Write-Host "Target:  $ModelDir"
Write-Host ""

foreach ($pair in $Mapping.GetEnumerator()) {
    $src = Join-Path $GeneratedDir $pair.Key
    $dst = Join-Path $ModelDir    $pair.Value
    if (-not (Test-Path $src)) {
        Write-Host "SKIP $($pair.Key) (not found in $GeneratedDir)" -ForegroundColor Yellow
        continue
    }
    Copy-Item -Path $src -Destination $dst -Force
    Write-Host "Staged $($pair.Key) -> $($pair.Value)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Next:" -ForegroundColor Cyan
Write-Host "  1. Open the ucmis.m2t project in Eclipse (with Acceleo 4.2 installed)."
Write-Host "  2. In the Project Explorer, open the launch/ folder."
Write-Host "  3. Right-click 'Step 1 - CDIF Codelist.launch' -> Run As -> the .launch."
Write-Host "  4. Repeat for each 'Step 1 - CDIF <profile>.launch' configuration."
Write-Host "  5. Then run 'Step 2 - Pre Sphinx ...', 'Step 3 - ... Sphinx Cmd', 'Step 4 - post Sphinx'."
Write-Host "  6. Find generated output under <m2t-root>/generated/."
