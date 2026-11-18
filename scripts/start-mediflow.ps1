# ============================================================
# MEDIFLOW — One-Click Launcher
#
# Ensures Docker Desktop, Ollama, the GitHub CD runner, and
# the MEDIFLOW production containers are running, waits for
# health checks, and opens http://localhost in your browser.
# ============================================================

param(
    [switch]$NoBrowser,
    [string]$Url = "http://localhost"
)

$ErrorActionPreference = "Continue"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

function Write-Info {
    param([string]$Msg)
    Write-Host "[MEDIFLOW] $Msg" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Msg)
    Write-Host "[OK]       $Msg" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Msg)
    Write-Host "[WARN]     $Msg" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Blue
Write-Host "  MEDIFLOW — Starting Personal Workspace  " -ForegroundColor Blue
Write-Host "==========================================" -ForegroundColor Blue
Write-Host ""

# 1. Check .env.prod
if (-not (Test-Path ".env.prod")) {
    Write-Host "[ERROR] Missing .env.prod in $RepoRoot. Copy .env.prod.example to .env.prod first." -ForegroundColor Red
    exit 1
}

# 2. Ensure Docker Desktop is running
Write-Info "Checking Docker engine..."
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktop) {
        Write-Info "Starting Docker Desktop (please wait)..."
        Start-Process -FilePath $dockerDesktop
        $ready = $false
        for ($i = 1; $i -le 45; $i++) {
            Start-Sleep -Seconds 2
            docker info *> $null
            if ($LASTEXITCODE -eq 0) {
                $ready = $true
                break
            }
            Write-Host "  Waiting for Docker engine ($i/45)..."
        }
        if (-not $ready) {
            Write-Host "[ERROR] Docker engine did not become ready in time. Please open Docker Desktop and retry." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "[ERROR] Docker is not running and Docker Desktop was not found at '$dockerDesktop'." -ForegroundColor Red
        exit 1
    }
}
Write-Ok "Docker engine is running"

# 3. Ensure Ollama is running on localhost:11434 (optional AI service)
Write-Info "Checking local Ollama AI service..."
$ollamaUp = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2
    if ($resp.StatusCode -eq 200) { $ollamaUp = $true }
} catch {}

if (-not $ollamaUp) {
    $ollamaApp = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama app.exe"
    $ollamaCli = Get-Command ollama -ErrorAction SilentlyContinue
    if (Test-Path $ollamaApp) {
        Write-Info "Starting Ollama..."
        Start-Process -FilePath $ollamaApp
        Start-Sleep -Seconds 3
        Write-Ok "Ollama started"
    } elseif ($ollamaCli) {
        Write-Info "Starting Ollama service..."
        Start-Process -FilePath $ollamaCli.Source -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Ok "Ollama started"
    } else {
        Write-Warn "Ollama not found — MEDIFLOW will still run, with AI assistant in offline fallback mode."
    }
} else {
    Write-Ok "Ollama AI service is running"
}

# 4. Ensure self-hosted GitHub Actions CD runner is running (if installed)
$runnerProc = Get-Process -Name "Runner.Listener" -ErrorAction SilentlyContinue
if (-not $runnerProc) {
    $task = Get-ScheduledTask -TaskName "MediFlow-GitHub-Runner" -ErrorAction SilentlyContinue
    if ($task) {
        Write-Info "Starting MediFlow GitHub Actions CD runner..."
        Start-ScheduledTask -TaskName "MediFlow-GitHub-Runner" -ErrorAction SilentlyContinue
        Write-Ok "CD runner started"
    }
} else {
    Write-Ok "CD runner is active"
}

# 5. Start MEDIFLOW production containers (fast — no rebuild unless images are missing)
Write-Info "Starting MEDIFLOW production containers..."
docker compose -f docker-compose.prod.yaml --env-file .env.prod up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start MEDIFLOW containers." -ForegroundColor Red
    exit 1
}

# 6. Wait for backend and frontend health endpoints
function Wait-ForEndpoint {
    param([string]$Endpoint, [int]$Retries = 30)
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Endpoint -UseBasicParsing -TimeoutSec 4
            if ($r.StatusCode -eq 200) {
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Info "Waiting for API and Web services to become healthy..."
$apiOk = Wait-ForEndpoint -Endpoint "$Url/api/v1/health"
$webOk = Wait-ForEndpoint -Endpoint "$Url/"

if ($apiOk -and $webOk) {
    Write-Ok "MEDIFLOW is live at $Url"
} else {
    Write-Warn "Containers started, but health check timed out. Opening $Url anyway — give it a few seconds and refresh."
}

if (-not $NoBrowser) {
    Write-Info "Opening $Url in your default browser..."
    Start-Process $Url
}

Write-Host ""
Write-Host "MEDIFLOW is ready: $Url" -ForegroundColor Green
Write-Host ""
