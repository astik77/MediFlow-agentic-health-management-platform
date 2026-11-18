# ============================================================
# MEDIFLOW — Smart Local / Self-Hosted Production Deployment
#
# Rebuilds and restarts only the Docker services affected by
# recent git changes (or all services with -ForceAll), then
# verifies frontend and backend health endpoints.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/deploy.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/deploy.ps1 -ForceAll
#   powershell -ExecutionPolicy Bypass -File scripts/deploy.ps1 -FromRef <old-sha> -ToRef <new-sha>
# ============================================================

param(
    [switch]$ForceAll,
    [string]$FromRef = "HEAD~1",
    [string]$ToRef = "HEAD",
    [string]$EnvFile = ".env.prod",
    [string]$ComposeFile = "docker-compose.prod.yaml",
    [string]$HealthBaseUrl = "http://localhost"
)

# Use Continue so docker compose / git informational stderr output does not
# trigger terminating NativeCommandError in Windows PowerShell 5.1; we check
# $LASTEXITCODE explicitly after every native command.
$ErrorActionPreference = "Continue"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

# Move to repo root
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not (Test-Path $EnvFile)) {
    throw "Missing '$EnvFile' in $RepoRoot. Copy .env.prod.example to .env.prod and configure secrets first."
}

if (-not (Test-Path $ComposeFile)) {
    throw "Missing '$ComposeFile' in $RepoRoot."
}

$rebuildWeb = $false
$rebuildApi = $false
$rebuildStack = $false

if ($ForceAll) {
    Write-Step "ForceAll enabled — rebuilding full production stack"
    $rebuildStack = $true
} else {
    Write-Step "Detecting changed files ($FromRef..$ToRef)"
    $changedFiles = @()
    try {
        $diffOutput = git diff --name-only $FromRef $ToRef 2>&1
        if ($LASTEXITCODE -eq 0 -and $diffOutput) {
            $changedFiles = @($diffOutput | Where-Object { $_ -and $_.Trim() -ne "" })
        }
    } catch {
        Write-Warning "Could not compute git diff; falling back to rebuilding api and web."
        $rebuildWeb = $true
        $rebuildApi = $true
    }

    if ($changedFiles.Count -eq 0 -and -not $rebuildWeb -and -not $rebuildApi) {
        Write-Host "No file changes detected between $FromRef and $ToRef. Skipping rebuild." -ForegroundColor Yellow
        exit 0
    }

    foreach ($file in $changedFiles) {
        Write-Host "  changed: $file"
        if ($file -like "apps/web/*") {
            $rebuildWeb = $true
        }
        if ($file -like "apps/api/*") {
            $rebuildApi = $true
        }
        if ($file -eq "docker-compose.prod.yaml" -or $file -like "infra/docker/caddy/*" -or $file -like "infra/docker/postgres/*") {
            $rebuildStack = $true
        }
    }
}

if (-not $rebuildStack -and -not $rebuildWeb -and -not $rebuildApi) {
    Write-Host "`nOnly non-runtime files (docs/CI/scripts) changed — no container rebuild required." -ForegroundColor Green
    exit 0
}

if ($rebuildStack) {
    Write-Step "Rebuilding and updating full production stack"
    docker compose -f $ComposeFile --env-file $EnvFile up -d --build
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed (exit $LASTEXITCODE)" }
} else {
    if ($rebuildApi) {
        Write-Step "Rebuilding and restarting 'api' container"
        docker compose -f $ComposeFile --env-file $EnvFile up -d --build --no-deps api
        if ($LASTEXITCODE -ne 0) { throw "Failed to rebuild api container (exit $LASTEXITCODE)" }
    }
    if ($rebuildWeb) {
        Write-Step "Rebuilding and restarting 'web' container"
        docker compose -f $ComposeFile --env-file $EnvFile up -d --build --no-deps web
        if ($LASTEXITCODE -ne 0) { throw "Failed to rebuild web container (exit $LASTEXITCODE)" }
    }
}

# Verify health endpoints with retry loop
function Wait-ForHttp200 {
    param(
        [string]$Url,
        [int]$MaxAttempts = 20,
        [int]$DelaySeconds = 3
    )
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) {
                Write-Host "  [OK] $Url -> HTTP $($resp.StatusCode)" -ForegroundColor Green
                return
            }
        } catch {
            # Retry until container becomes ready
        }
        Write-Host "  Waiting for $Url (attempt $i/$MaxAttempts)..."
        Start-Sleep -Seconds $DelaySeconds
    }
    throw "Health check failed for $Url after $MaxAttempts attempts."
}

Write-Step "Verifying deployment health"
Wait-ForHttp200 -Url "$HealthBaseUrl/api/v1/health"
Wait-ForHttp200 -Url "$HealthBaseUrl/"

Write-Step "Production containers status"
docker compose -f $ComposeFile --env-file $EnvFile ps

Write-Host "`nMEDIFLOW production deployment updated successfully." -ForegroundColor Green
