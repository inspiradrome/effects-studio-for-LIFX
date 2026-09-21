param(
    [ValidateSet("Public", "SisterRussian")]
    [string]$Edition = "Public"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Create .venv and install requirements-dev.txt before building."
}

& (Join-Path $PSScriptRoot "make_icon.ps1") | Out-Host
$version = & $python -c "from effects_studio import __version__; print(__version__)"
& $python -m PyInstaller --noconfirm --clean (Join-Path $projectRoot "LIFXEffectsStudio.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$distributionName = "EffectsStudioForLIFX"
$distributionDirectory = Join-Path $projectRoot "dist\$distributionName"
$executable = Join-Path $distributionDirectory "$distributionName.exe"
$smokeTest = Start-Process `
    -FilePath $executable `
    -ArgumentList "--smoke-test" `
    -PassThru `
    -Wait `
    -WindowStyle Hidden
if ($smokeTest.ExitCode -ne 0) {
    throw "The packaged executable failed its smoke test with exit code $($smokeTest.ExitCode)."
}

# Antivirus scanners can briefly retain handles after first launch.
$deadline = [DateTime]::UtcNow.AddSeconds(15)
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $probe = [System.IO.File]::Open(
            (Join-Path $distributionDirectory "_internal\base_library.zip"),
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::None
        )
        $probe.Dispose()
        break
    } catch {
        Start-Sleep -Milliseconds 250
    }
}
if ([DateTime]::UtcNow -ge $deadline) {
    throw "The packaged application did not release its files after the smoke test."
}

if ($Edition -eq "SisterRussian") {
    Copy-Item `
        -LiteralPath (Join-Path $projectRoot "editions\sister-russian\edition.js") `
        -Destination (Join-Path $distributionDirectory "_internal\effects_studio\static\edition.js") `
        -Force
    Copy-Item `
        -LiteralPath (Join-Path $projectRoot "editions\sister-russian\QUICK_START_RU.md") `
        -Destination (Join-Path $distributionDirectory "Quick Start RU.md") `
        -Force
}

Copy-Item `
    -LiteralPath (Join-Path $projectRoot "USER_GUIDE.md") `
    -Destination (Join-Path $distributionDirectory "Quick Start Guide.md") `
    -Force

$releaseDirectory = Join-Path $projectRoot "release"
New-Item -ItemType Directory -Force -Path $releaseDirectory | Out-Null
$editionSuffix = if ($Edition -eq "SisterRussian") { "-sister-ru" } else { "" }
$archive = Join-Path $releaseDirectory "$distributionName-$version$editionSuffix-windows-x64.zip"
if (Test-Path -LiteralPath $archive) {
    Remove-Item -LiteralPath $archive
}
Compress-Archive -Path (Join-Path $distributionDirectory "*") -DestinationPath $archive

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
$checksum = Join-Path $releaseDirectory "$distributionName-$version$editionSuffix-windows-x64.sha256"
Set-Content -LiteralPath $checksum -Encoding ascii -Value "$hash  $(Split-Path -Leaf $archive)"
Write-Output "Release: $archive"
Write-Output "SHA-256: $hash"
