# Disabled by default. This file does not register a task unless you pass -Register.
# The task, once registered, is created DISABLED. Enable it in Task Scheduler yourself.
param([switch]$Register)

$ErrorActionPreference = "Stop"
if (-not $Register) {
  Write-Host "Daily drafts are not scheduled."
  Write-Host "To create a DISABLED task that runs at 8:00:  powershell -File schedule-daily.ps1 -Register"
  exit 0
}

$script = Join-Path $PSScriptRoot "server.py"
$action = New-ScheduledTaskAction -Execute "py.exe" -Argument "-3 `"$script`" --daily"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00am
Register-ScheduledTask -TaskName "EarnItNotGiven drafts" -Action $action -Trigger $trigger -Description "Local draft generator. Does not publish." | Out-Null
Disable-ScheduledTask -TaskName "EarnItNotGiven drafts" | Out-Null
Write-Host "Task created and left DISABLED. Turn it on in Task Scheduler only when you want it."
