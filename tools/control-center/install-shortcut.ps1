# Creates a desktop shortcut for Spec Checker. Run on the AIDesktop.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $here "spec-checker.bat"
$icon = Join-Path $here "spec-checker.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$link = Join-Path $desktop "EarnIt Spec Checker.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $bat
$shortcut.WorkingDirectory = $here
$shortcut.IconLocation = $icon
$shortcut.Description = "EarnItNotGiven Spec Checker"
$shortcut.Save()
Write-Host "Shortcut created: $link"
