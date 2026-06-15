$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).ProviderPath
Set-Location -LiteralPath $Root

$RequiredPaths = @(
    "assets\kickabout-named-assets",
    "assets\kenney_sports-pack\PNG\Equipment\ball_soccer1.png",
    "research\animation-decoded\characters_animation_sequences.csv",
    "research\animation-decoded\skeleton_transforms.csv",
    "research\animation-decoded\frame_entries.csv"
)

foreach ($Path in $RequiredPaths) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required packaged asset: $Path"
    }
}

$DistDir = "dist"
$BuildDir = "build"
$Exe = Join-Path $DistDir "KickaboutBeta.exe"
$Zip = Join-Path $DistDir "KickaboutBeta-windows.zip"
$BuildCache = Join-Path $BuildDir "KickaboutBeta"

New-Item -ItemType Directory -Force -Path $DistDir, $BuildDir | Out-Null
Remove-Item -LiteralPath $BuildCache -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $Exe -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $Zip -Force -ErrorAction SilentlyContinue

$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--name", "KickaboutBeta",
    "--workpath", $BuildDir,
    "--distpath", $DistDir,
    "--specpath", ".",
    "--add-data", "assets;assets",
    "--add-data", "research\animation-decoded;research\animation-decoded",
    "main.py"
)

& python @PyInstallerArgs

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $Exe)) {
    throw "PyInstaller did not create expected executable: $Exe"
}

$ExeInfo = Get-Item -LiteralPath $Exe
if ($ExeInfo.Length -lt 1MB) {
    throw "Built executable is unexpectedly small ($($ExeInfo.Length) bytes): $Exe"
}

Compress-Archive -LiteralPath $Exe -DestinationPath $Zip -Force

if (-not (Test-Path -LiteralPath $Zip)) {
    throw "Failed to create release zip: $Zip"
}

$ZipInfo = Get-Item -LiteralPath $Zip
Write-Host "Built $Zip ($($ZipInfo.Length) bytes) from $Exe ($($ExeInfo.Length) bytes)"
