$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$DefaultPython = Join-Path $RootDir ".venv/Scripts/python.exe"
$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } elseif (Test-Path $DefaultPython) { $DefaultPython } else { "python" }
$TargetTriple = if ($args.Count -gt 0 -and $args[0]) { $args[0] } else { "x86_64-pc-windows-msvc" }

function Remove-GitUsrBinFromPath {
  $entries = $env:Path -split ";"
  $cleaned = $entries | Where-Object { $_ -and ($_ -notmatch "(?i)\\Git\\usr\\bin\\?") }
  $env:Path = ($cleaned -join ";")
}

function Import-VsDevEnvironment {
  $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
  if (-not (Test-Path $vswhere)) {
    return $false
  }

  $installPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  if (-not $installPath) {
    return $false
  }

  $vcvars = Join-Path $installPath "VC\Auxiliary\Build\vcvars64.bat"
  if (-not (Test-Path $vcvars)) {
    return $false
  }

  $envDump = cmd.exe /s /c "`"$vcvars`" >nul && set"
  foreach ($line in $envDump) {
    if ($line -notmatch "=") {
      continue
    }

    $idx = $line.IndexOf("=")
    if ($idx -le 0) {
      continue
    }

    $name = $line.Substring(0, $idx)
    $value = $line.Substring($idx + 1)
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
  }

  return $true
}

function Assert-TauriWindowsToolchain {
  Remove-GitUsrBinFromPath
  $null = Import-VsDevEnvironment

  $linkCmd = Get-Command link.exe -ErrorAction SilentlyContinue
  if ($null -eq $linkCmd) {
    throw "Khong tim thay Microsoft linker (link.exe). Cai Visual Studio Build Tools voi Desktop development with C++ roi chay lai."
  }

  $clCmd = Get-Command cl.exe -ErrorAction SilentlyContinue
  if ($null -eq $clCmd) {
    throw "Khong tim thay cl.exe (MSVC compiler). Mo terminal PowerShell moi va chay lai script."
  }

  if ($linkCmd.Source -match "(?i)\\Git\\usr\\bin\\link\.exe$") {
    throw "Dang dung nham link.exe cua Git. Hay mo PowerShell (khong dung Git Bash) roi chay lai script."
  }
}

function Resolve-BundleRoot {
  $targetBundle = Join-Path $RootDir "src-tauri/target/$TargetTriple/release/bundle"
  if (Test-Path $targetBundle) {
    return $targetBundle
  }

  return (Join-Path $RootDir "src-tauri/target/release/bundle")
}

Set-Location $RootDir
Assert-TauriWindowsToolchain

Write-Host "[1/5] Install frontend dependencies"
npm install

Write-Host "[2/5] Install sidecar Python dependencies"
& $PythonBin -m pip install -r sidecar/requirements.txt
& $PythonBin -m pip install pyinstaller

Write-Host "[3/5] Build sidecar executable"
Set-Location (Join-Path $RootDir "sidecar")
& $PythonBin -m PyInstaller --noconfirm --clean main.py --onefile --name dictover-sidecar --distpath ../src-tauri/binaries/

Set-Location $RootDir
$pyinstallerSpec = Join-Path $RootDir "sidecar/dictover-sidecar.spec"
if (Test-Path $pyinstallerSpec) {
  Remove-Item $pyinstallerSpec -Force
}

$pyinstallerBuildDir = Join-Path $RootDir "sidecar/build"
if (Test-Path $pyinstallerBuildDir) {
  Remove-Item $pyinstallerBuildDir -Recurse -Force
}

$pyinstallerDistDir = Join-Path $RootDir "sidecar/dist"
if (Test-Path $pyinstallerDistDir) {
  Remove-Item $pyinstallerDistDir -Recurse -Force
}

$sidecarExe = Join-Path $RootDir "src-tauri/binaries/dictover-sidecar.exe"
if (-not (Test-Path $sidecarExe)) {
  throw "Khong tao duoc sidecar executable: $sidecarExe"
}

Write-Host "[4/5] Build Windows installer"
npm run tauri build -- --target $TargetTriple

Write-Host "[5/5] Collect installer artifacts"
$bundleRoot = Resolve-BundleRoot
if (-not (Test-Path $bundleRoot)) {
  throw "Khong tim thay thu muc bundle: $bundleRoot"
}

$installers = Get-ChildItem -Path $bundleRoot -Recurse -File | Where-Object { $_.Extension -in @(".exe", ".msi") }
if (-not $installers) {
  throw "Khong tim thay file installer (.exe/.msi) trong $bundleRoot"
}

Write-Host ""
Write-Host "Installer build thanh cong. File tao ra:"
$installers | Sort-Object FullName | ForEach-Object {
  Write-Host " - $($_.FullName)"
}
