# Copies new photos from a connected iPhone (This PC\Apple iPhone) or from a watched folder.
# Does not delete anything on the phone. George points iCloud/AirDrop exports at -Watch if USB is empty.
param(
  [string]$Tag = "SAMPLE7X",
  [string]$Root = "C:\Users\Hacking\EarnItNotGiven\Products",
  [string]$Watch = ""
)
$ErrorActionPreference = "Stop"
$dest = Join-Path $Root (Join-Path $Tag "photos")
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$copied = @()
if ($Watch -and (Test-Path $Watch)) {
  Get-ChildItem $Watch -File | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $dest $_.Name)
    $copied += $_.Name
  }
}
$shell = New-Object -ComObject Shell.Application
$pc = $shell.NameSpace(0x11)
$phone = $null
foreach ($item in @($pc.Items())) {
  if ($item.Name -match "iPhone") { $phone = $item; break }
}
if ($phone) {
  function Walk($folder) {
    foreach ($item in @($folder.Items())) {
      if ($item.IsFolder) { Walk $item.GetFolder }
      elseif ($item.Name -match "\.(jpe?g|png|heic|heif)$") {
        $target = Join-Path $dest $item.Name
        if (-not (Test-Path $target)) {
          $folder.CopyHere($item, 0x14)
          $copied += $item.Name
        }
      }
    }
  }
  Walk $phone.GetFolder()
}
[pscustomobject]@{ tag = $Tag; folder = $dest; files = $copied; sample = $false } | ConvertTo-Json -Compress
