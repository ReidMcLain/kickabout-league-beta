$ErrorActionPreference = "Stop"

$Root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
Set-Location $Root
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("kickabout-beta-build-" + [System.Guid]::NewGuid().ToString("N"))
$TempBuild = Join-Path $TempRoot "build"
$TempDist = Join-Path $TempRoot "dist"
$TempSpec = Join-Path $TempRoot "spec"
New-Item -ItemType Directory -Force -Path $TempBuild, $TempDist, $TempSpec | Out-Null

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

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name "KickaboutBeta" `
    --workpath $TempBuild `
    --distpath $TempDist `
    --specpath $TempSpec `
    --add-data "$Root\assets;assets" `
    --add-data "$Root\research\animation-decoded;research\animation-decoded" `
    main.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$Zip = Join-Path $Root "dist\KickaboutBeta-windows.zip"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Zip) | Out-Null
if (Test-Path -LiteralPath $Zip) {
    try {
        Remove-Item -LiteralPath $Zip -Force
    }
    catch {
        $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $Zip = Join-Path $Root "dist\KickaboutBeta-windows-$Stamp.zip"
    }
}

Compress-Archive -Path (Join-Path $TempDist "KickaboutBeta.exe") -DestinationPath $Zip
Write-Host "Built $Zip"
