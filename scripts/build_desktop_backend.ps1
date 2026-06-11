$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$binaryDir = Join-Path $root "frontend\src-tauri\binaries"
$outputDir = Join-Path $root "dist"
$backendName = "supplierintel-backend"

New-Item -ItemType Directory -Force -Path $binaryDir | Out-Null

Push-Location $root
try {
    python -m PyInstaller --version | Out-Null

    $pyInstallerArgs = @(
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--exclude-module", "app.tests",
        "--exclude-module", "pytest",
        "--exclude-module", "IPython",
        "--exclude-module", "notebook",
        "--exclude-module", "jupyterlab",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "pyarrow",
        "--exclude-module", "dask",
        "--exclude-module", "distributed"
    )

    if (Test-Path ".env") {
        $pyInstallerArgs += @("--add-data", ".env;.")
    }

    $pyInstallerArgs += @("--name", $backendName, "app\desktop_server.py")

    python -m PyInstaller @pyInstallerArgs

    $targetTriple = "x86_64-pc-windows-msvc"
    if (Get-Command rustc -ErrorAction SilentlyContinue) {
        $targetTriple = (rustc -Vv | Select-String "host:" | ForEach-Object { $_.Line.Split(" ")[1] }).Trim()
    }

    $sourceExe = Join-Path $outputDir "$backendName.exe"
    $targetExe = Join-Path $binaryDir "$backendName-$targetTriple.exe"
    Copy-Item -Force -Path $sourceExe -Destination $targetExe

    Write-Host "Desktop backend sidecar created at $targetExe"
}
finally {
    Pop-Location
}
