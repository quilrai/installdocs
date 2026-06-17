<#
============================================================================
 quilr-connectivity-check.ps1
 Tests outbound TCP/443 reachability to the Quilr backplane hosts that the
 Quilr Endpoint Agent needs, for a given tenant environment.

 Usage:
   # Defaults to the US environment:
   irm https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/Windows/quilr-connectivity-check.ps1 | iex

   # Pick an environment (iex can't take args, so create a scriptblock):
   & ([scriptblock]::Create((irm https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/Windows/quilr-connectivity-check.ps1))) -Env usa

   # Or, run a downloaded copy:
   powershell -ExecutionPolicy Bypass -File .\quilr-connectivity-check.ps1 -Env japan

   -Env = us (default) | usa | japan | india

 Result code: 0 = every host reachable, 1 = one or more BLOCKED, 2 = bad usage.
 When run interactively (irm | iex / scriptblock) the script RETURNS and sets
 $LASTEXITCODE instead of calling exit, so it does NOT close your console.
 When run as a file (-File) it sets the process exit code normally.
 A BLOCKED host must be unblocked AND added to the SSL-bypass / no-decrypt
 list on any TLS-intercepting proxy before installing the agent.
 Run elevated for the most reliable results.
============================================================================
#>
[CmdletBinding()]
param(
    [string]$Env = 'us'
)

$ErrorActionPreference = 'SilentlyContinue'
$port     = 443
$shared   = @('discover.quilrai.dev','log.quilrai.dev','quilr-extensions.quilr.ai')
$hosts    = $null
$exitCode = 0

switch ($Env.ToLower()) {
    { $_ -in @('us','default') } {
        $label = 'quilr-saas (US default)'
        $hosts = $shared + @('app.quilr.ai','dlpone.quilr.ai'); break
    }
    { $_ -in @('usa','usa-prod','usaprod') } {
        $label = 'quilr-saas-usa-prod'
        $hosts = $shared + @('quilr-extensions.quilrai.com','app.quilrai.com','dlpone.quilrai.com'); break
    }
    { $_ -in @('japan','jp') } {
        $label = 'quilr-saas-japan'
        $hosts = $shared + @('app-jp.quilr.ai','dlpone-jp-1.quilr.ai'); break
    }
    { $_ -in @('india','ind','ind-prod') } {
        $label = 'quilr-saas-ind-prod (India)'
        $hosts = $shared + @('quilr-extensions.quilrai.com','platform.quilrai.com','dlp-platform.quilrai.com'); break
    }
    default {
        Write-Host "Unknown environment: '$Env'  (use: us | usa | japan | india)"
        $exitCode = 2
    }
}

if ($hosts) {
    Write-Host ""
    Write-Host "Quilr connectivity check  -  $label"
    Write-Host ("-" * 60)

    $fail = $false
    foreach ($h in $hosts) {
        $ok = Test-NetConnection -ComputerName $h -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
        $status = if ($ok) { 'OK' } else { 'BLOCKED' }
        "{0,-34}  TCP/{1}  {2}" -f $h, $port, $status
        if (-not $ok) { $fail = $true }
    }

    Write-Host ("-" * 60)
    if ($fail) {
        Write-Host "RESULT: one or more hosts BLOCKED - unblock and SSL-bypass them before installing."
        $exitCode = 1
    } else {
        Write-Host "RESULT: all hosts reachable on TCP/$port."
        $exitCode = 0
    }
}

# Report the result code WITHOUT closing an interactive console.
# Only call exit when launched as its own process (powershell -File ...),
# detected via $PSCommandPath; otherwise return and surface $LASTEXITCODE.
if ($PSCommandPath) {
    exit $exitCode
} else {
    $global:LASTEXITCODE = $exitCode
    return
}
