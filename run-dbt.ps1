# Loads .env into the current process's environment, then runs dbt with
# whatever arguments you pass through.
#
# Why this exists: dbt does NOT read .env files (unlike ingest.py, which
# uses python-dotenv). Its profiles.yml reads env_var()s straight from the
# real shell environment instead, so without something like this you'd have
# to set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD by hand every session.
# This keeps .env as the single source of truth for connection details,
# the same way ingest.py already treats it.
#
# Usage, from anywhere in the repo:
#   ..\run-dbt.ps1 build
#   ..\run-dbt.ps1 test
#   ..\run-dbt.ps1 deps
#
# Not needed on the deployed homelab or inside this repo's own bundled
# docker-compose stack -- both set DB_* directly on the container.

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$envFile = Join-Path $repoRoot ".env"
$projectDir = Join-Path $repoRoot "dbt_project\uk_crime_pipeline"
$profilesDir = Join-Path $repoRoot "dbt_profiles"

if (-not (Test-Path $envFile)) {
    Write-Error "No .env found at $envFile -- copy .env.example to .env and fill in real values."
}

# Read .env line by line, skipping blanks and # comments, and set each
# KEY=VALUE pair as an environment variable for this process only.
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }

    $separator = $line.IndexOf("=")
    if ($separator -lt 1) { return }

    $key = $line.Substring(0, $separator).Trim()
    $value = $line.Substring($separator + 1).Trim()

    # Strip surrounding quotes if present -- .env files commonly have them,
    # but the actual value shouldn't include them.
    if ($value.Length -ge 2) {
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
    }

    Set-Item -Path "Env:$key" -Value $value
}

Write-Host "Loaded .env -- connecting to $env:DB_NAME on $env:DB_HOST`:$env:DB_PORT as $env:DB_USER" -ForegroundColor Cyan

dbt @args --project-dir $projectDir --profiles-dir $profilesDir
exit $LASTEXITCODE
