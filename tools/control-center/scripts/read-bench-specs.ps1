# Optional. Run on the Windows PC you are listing. Prints JSON. Does not upload it.
$ErrorActionPreference = "Stop"
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ram = [math]::Round(((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB), 1)
$disks = Get-CimInstance Win32_DiskDrive | ForEach-Object { "$($_.Model) $([math]::Round($_.Size/1GB,0)) GB" }
$gpu = (Get-CimInstance Win32_VideoController | Select-Object -First 1).Name
$bios = Get-CimInstance Win32_BIOS
[pscustomobject]@{
  sample = $false
  identifier = [string]$bios.SerialNumber
  maker = [string]$cs.Manufacturer
  system = [string]$cs.Model
  cpu = [string]$cpu.Name
  ram_gb = $ram
  disk = ($disks -join "; ")
  gpu = [string]$gpu
  bios_serial = [string]$bios.SerialNumber
  note = "Read on this PC with WMI/CIM. Not sent anywhere."
} | ConvertTo-Json
