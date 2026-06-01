param(
    [string]$FRAMEWORK,
    [int]$VCPU = 4,
    [int]$CONCURRENCY = 100,
    [int]$DURATION_MIN = 60,
    [string]$PDF_SETS
)

$RESULT_DIR = "results"
New-Item -ItemType Directory -Force -Path $RESULT_DIR | Out-Null

Write-Host ""
Write-Host "====================================="
Write-Host "ENDURANCE TEST"
Write-Host "Framework   : $FRAMEWORK"
Write-Host "PDF_SETS    : $PDF_SETS"
Write-Host "Concurrency : $CONCURRENCY"
Write-Host "Duration    : $DURATION_MIN min"
Write-Host "====================================="
Write-Host ""

# LOCUST FILE

$locustFile = if ($FRAMEWORK -eq "node") {
    "/mnt/locust/locustfile_node.py"
} else {
    "/mnt/locust/locustfile_python.py"
}

# CONTAINER NAME

$containerName = "$FRAMEWORK"

# RESTART

docker compose down -v
docker compose up -d

Start-Sleep 20

# HEALTHCHECK

try {
    Invoke-WebRequest http://localhost:3000/health -UseBasicParsing | Out-Null
} catch {}

try {
    Invoke-WebRequest http://localhost:8000/health -UseBasicParsing | Out-Null
} catch {}

# PORT

$port = if ($FRAMEWORK -eq "node") {3000} else {8000}


# START METRIC MONITOR

$monitorScript = Join-Path $PSScriptRoot "monitor_metrics.ps1"

Write-Host "Monitor script: $monitorScript"

$monitorProcess = Start-Process powershell `
    -ArgumentList `
    "-ExecutionPolicy Bypass -File `"$monitorScript`" -FRAMEWORK $FRAMEWORK -RESULT_DIR $RESULT_DIR" `
    -PassThru `
    -WindowStyle Hidden

Write-Host "Metric monitor started..."

# START TS

$START_TS = [int][double]::Parse((Get-Date -UFormat %s))

# LOCUST

$spawn = [math]::Max([int]($CONCURRENCY / 10), 1)

Write-Host "Starting Locust..."

$locustOutput = docker run --rm `
  --user root `
  -e FRAMEWORK=$FRAMEWORK `
  -e VCPU=$VCPU `
  -e CONCURRENCY=$CONCURRENCY `
  -e RUN=1 `
  --network dipl1_default `
  -v "${PWD}/locust:/mnt/locust" `
  -v "${PWD}/pdf_corpus:/mnt/pdf_corpus" `
  -v "${PWD}/results:/mnt/results" `
  locustio/locust `
  -f $locustFile `
  --host "http://$FRAMEWORK-app:$port" `
  --users $CONCURRENCY `
  --spawn-rate $spawn `
  --run-time 5m `
  --headless `
  --csv="/mnt/results/endurance_${FRAMEWORK}"

# STOP MONITOR

Write-Host "Stopping monitor..."

if ($monitorProcess) {

    Stop-Process `
        -Id $monitorProcess.Id `
        -Force `
        -ErrorAction SilentlyContinue

    Write-Host "Monitor stopped"
}

# ANALYSIS

Write-Host "Running analysis..."

python analyze_endurance.py $FRAMEWORK

Write-Host ""
Write-Host "ENDURANCE TEST COMPLETED"
Write-Host ""