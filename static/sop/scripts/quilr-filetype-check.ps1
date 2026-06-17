<#
============================================================================
 quilr-filetype-check.ps1
 Checks that the file types / MIME types the Quilr Endpoint Agent needs
 (.exe .msi .msp .zip .json .toml .xml) are not blocked, stripped, or
 MIME-rewritten by a web filter / SWG / download-control policy.

 How it works: downloads a tiny probe file per extension from the Quilr CDN
 and verifies (a) it returns HTTP 200, (b) its content marker is intact
 (a proxy block page would not contain it), and (c) reports the Content-Type.

 Usage:
   irm https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/Windows/quilr-filetype-check.ps1 | iex
   & ([scriptblock]::Create((irm https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/Windows/quilr-filetype-check.ps1)))
   powershell -ExecutionPolicy Bypass -File .\quilr-filetype-check.ps1 -BaseUrl <url>

 Result code: 0 = all types OK, 1 = one or more BLOCKED/ALTERED.
 Runs interactively without closing your console (returns + $LASTEXITCODE).

 Note: this detects extension/MIME-based filtering. A gateway that blocks on
 deep content inspection of real binaries may behave differently for an
 actual PE/MSI than for a probe file.
============================================================================
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = 'https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/mime-test'
)

$ErrorActionPreference = 'SilentlyContinue'
$marker = 'QUILR-MIME-PROBE-OK'
$exts   = @('exe','msi','msp','zip','json','toml','xml')

Write-Host ""
Write-Host "Quilr file-type / MIME allow check"
Write-Host "Base: $BaseUrl"
Write-Host ("-" * 64)

$fail = $false
foreach ($e in $exts) {
    $u = "$BaseUrl/probe.$e"
    $status = 'BLOCKED'
    $ct = '-'
    try {
        $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 15
        $ct = "$($r.Headers['Content-Type'])"
        if (-not $ct) { $ct = '(none)' }
        $content = if ($r.Content -is [byte[]]) { [Text.Encoding]::ASCII.GetString($r.Content) } else { [string]$r.Content }
        if ($r.StatusCode -eq 200 -and $content -like "*$marker*") { $status = 'OK' }
        elseif ($r.StatusCode -eq 200) { $status = 'ALTERED' }
    } catch {
        if ($_.Exception.Response) { $ct = "HTTP $([int]$_.Exception.Response.StatusCode)" }
        $status = 'BLOCKED'
    }
    "{0,-6}  {1,-8}  {2}" -f ".$e", $status, $ct
    if ($status -ne 'OK') { $fail = $true }
}

Write-Host ("-" * 64)
if ($fail) {
    Write-Host "RESULT: one or more file types BLOCKED or ALTERED - allow them on your SWG / download policy."
    $code = 1
} else {
    Write-Host "RESULT: all file types downloadable with intact content."
    $code = 0
}

if ($PSCommandPath) { exit $code } else { $global:LASTEXITCODE = $code; return }
