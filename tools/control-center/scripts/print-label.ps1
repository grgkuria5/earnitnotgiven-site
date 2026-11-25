# Prints a 4x6 label. PDF uses the Windows printer. ZPL is sent raw for Zebra, Rollo, or Brother QL in raw mode.
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$PrinterName = "",
  [ValidateSet("PDF", "ZPL")][string]$Format = "PDF"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Path)) { throw "Label file not found." }
if ($Format -eq "ZPL") {
  if (-not $PrinterName) { throw "Set a label printer name for ZPL." }
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  $code = @'
using System;
using System.Runtime.InteropServices;
public class RawPrinter {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
  public class DOCINFO { public string pDocName; public string pOutputFile; public string pDataType; }
  [DllImport("winspool.Drv", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern bool OpenPrinter(string p, out IntPtr h, IntPtr d);
  [DllImport("winspool.Drv", SetLastError=true)]
  public static extern bool ClosePrinter(IntPtr h);
  [DllImport("winspool.Drv", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern bool StartDocPrinter(IntPtr h, int level, DOCINFO di);
  [DllImport("winspool.Drv", SetLastError=true)]
  public static extern bool EndDocPrinter(IntPtr h);
  [DllImport("winspool.Drv", SetLastError=true)]
  public static extern bool StartPagePrinter(IntPtr h);
  [DllImport("winspool.Drv", SetLastError=true)]
  public static extern bool EndPagePrinter(IntPtr h);
  [DllImport("winspool.Drv", SetLastError=true)]
  public static extern bool WritePrinter(IntPtr h, byte[] b, int c, out int w);
}
'@
  Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue
  $handle = [IntPtr]::Zero
  if (-not [RawPrinter]::OpenPrinter($PrinterName, [ref]$handle, [IntPtr]::Zero)) { throw "Could not open $PrinterName" }
  $info = New-Object RawPrinter+DOCINFO
  $info.pDocName = "EarnIt label"
  $info.pDataType = "RAW"
  [RawPrinter]::StartDocPrinter($handle, 1, $info) | Out-Null
  [RawPrinter]::StartPagePrinter($handle) | Out-Null
  $written = 0
  [RawPrinter]::WritePrinter($handle, $bytes, $bytes.Length, [ref]$written) | Out-Null
  [RawPrinter]::EndPagePrinter($handle) | Out-Null
  [RawPrinter]::EndDocPrinter($handle) | Out-Null
  [RawPrinter]::ClosePrinter($handle) | Out-Null
} else {
  if ($PrinterName) {
    Start-Process -FilePath $Path -Verb PrintTo -ArgumentList $PrinterName
  } else {
    Start-Process -FilePath $Path -Verb Print
  }
}
