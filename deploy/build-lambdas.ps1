# Builds every Lambda deployment zip into .\dist-lambda\ for upload through the AWS Console.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File deploy\build-lambdas.ps1
#
# Dependencies are downloaded as Linux x86_64 / CPython 3.12 wheels, so the zips work on the
# Lambda "Python 3.12 / x86_64" runtime even though they're built on Windows (bcrypt is a
# compiled library — a Windows build of it would fail to import on Lambda).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "dist-lambda"
$work = Join-Path $out "_build"

# name = zip file, req = requirements file (or $null), packages = source folders to include
$targets = @(
    @{ name = "auth";       req = "auth\requirements.txt";       packages = @("auth") },
    @{ name = "scraper";    req = "deploy\scraper-lambda-requirements.txt"; packages = @("scraper") },
    @{ name = "consumer";   req = "processing\requirements.txt"; packages = @("processing", "db") },
    @{ name = "quotes-api"; req = "quotes_api\requirements.txt"; packages = @("quotes_api", "db") }
)

if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force $work | Out-Null

foreach ($t in $targets) {
    $dir = Join-Path $work $t.name
    New-Item -ItemType Directory -Force $dir | Out-Null
    Write-Host "==> $($t.name): installing dependencies"
    python -m pip install --quiet -r (Join-Path $root $t.req) --target $dir --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all: --upgrade
    if ($LASTEXITCODE -ne 0) { throw "pip install failed for $($t.name)" }

    foreach ($pkg in $t.packages) {
        Copy-Item -Recurse (Join-Path $root $pkg) $dir
    }
    Get-ChildItem -Path $dir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

    $zip = Join-Path $out "$($t.name).zip"
    Compress-Archive -Path (Join-Path $dir "*") -DestinationPath $zip -Force
    "{0,-12} {1,8:N1} MB" -f "$($t.name).zip", ((Get-Item $zip).Length / 1MB) | Write-Host
}

Remove-Item -Recurse -Force $work
Write-Host "`nDone. Upload the zips in $out via Lambda console -> Code -> Upload from -> .zip file"
