# Disabled by default. Refreshes the public eBay catalog. It does not end listings.
param([switch]$Register)

$ErrorActionPreference = "Stop"
if (-not $Register) {
  Write-Host "The eBay refresh is not scheduled."
  Write-Host "To create a DISABLED daily task:  powershell -File schedule-ebay.ps1 -Register"
  exit 0
}

$script = Join-Path (Split-Path $PSScriptRoot -Parent) "ebay-import\\import_ebay.py"
$action = New-ScheduledTaskAction -Execute "py.exe" -Argument "-3 `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 7:30am
Register-ScheduledTask -TaskName "EarnItNotGiven eBay refresh" -Action $action -Trigger $trigger -Description "Copy active workhard1140 listings. Does not edit eBay." | Out-Null
Disable-ScheduledTask -TaskName "EarnItNotGiven eBay refresh" | Out-Null
Write-Host "Task created and left DISABLED."
