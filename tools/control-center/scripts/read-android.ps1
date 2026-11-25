# Optional. Requires adb (Android platform-tools) and USB debugging on the phone.
$ErrorActionPreference = "Stop"
if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
  throw "adb is not installed. This step is optional."
}
$raw = adb shell getprop
$raw
