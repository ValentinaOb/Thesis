param(
    [string]$FRAMEWORK,
    [int]$VCPU,
    [int]$CONCURRENCY,
    [string]$PDF_SETS,
    [int]$RUN
)

# Визначаємо locustfile
$locustFile = if ($FRAMEWORK -eq "node") {
    "/mnt/locust/locustfile_node.py"
} else {
    "/mnt/locust/locustfile_python.py"
}

$RESULT_DIR = "results"
New-Item -ItemType Directory -Force -Path $RESULT_DIR | Out-Null

Write-Host "TEST: $FRAMEWORK | CPU=$VCPU | C=$CONCURRENCY | PDF=$PDF_SETS | RUN=$RUN"

# STEP 1
docker compose down -v
docker compose up -d
#docker compose up -d --build

Start-Sleep 15

# STEP 2
try {
    Invoke-WebRequest http://localhost:3000/health -UseBasicParsing | Out-Null
} catch {
    Write-Host "Node not ready"
}

try {
    Invoke-WebRequest http://localhost:8000/health -UseBasicParsing | Out-Null
} catch {
    Write-Host "Python not ready"
}

# STEP 3 (warm-up)
$port = if ($FRAMEWORK -eq "node") {3000} else {8000}

docker run --rm `
  --user root `
  -e FRAMEWORK=$FRAMEWORK `
  -e VCPU=$VCPU `
  -e CONCURRENCY=$CONCURRENCY `
  -e RUN=$RUN `
  --network dipl1_default `
  -v "${PWD}/locust:/mnt/locust" `
  -v "${PWD}/pdf_corpus:/mnt/pdf_corpus" `
  locustio/locust `
  -f $locustFile `
  --host "http://$FRAMEWORK-app:$port" `
  --users 10 `
  --spawn-rate 5 `
  --run-time 30s `
  --headless `
  --only-summary | Out-Null

# STEP 4
$START_TS = [int][double]::Parse((Get-Date -UFormat %s))

# STEP 5
$spawn = [math]::Max([int]($CONCURRENCY / 10), 1)

$locustOutput = docker run --rm `
  --user root `
  -e FRAMEWORK=$FRAMEWORK `
  -e VCPU=$VCPU `
  -e CONCURRENCY=$CONCURRENCY `
  -e RUN=$RUN `
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
  --csv="/mnt/results/${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${RUN}" 2>&1

$locustOutput | Tee-Object -FilePath "$RESULT_DIR/locust_${FRAMEWORK}_${RUN}.log"
$locustOutput

# STEP 6
$END_TS = [int][double]::Parse((Get-Date -UFormat %s))

Invoke-WebRequest `
  "http://localhost:9090/api/v1/query_range?query=rate(container_cpu_usage_seconds_total[1m])&start=$START_TS&end=$END_TS&step=5" `
  -OutFile "$RESULT_DIR/prom_${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${RUN}.json"

$stats = docker stats --no-stream --format "{{.CPUPerc}},{{.MemUsage}}" "$FRAMEWORK"

$stats | Out-File "$RESULT_DIR/docker_${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${RUN}.txt"

$parts = $stats -split ","

# CPU

$samples = 10
$interval = 1

$cpuList = 1..$samples | ForEach-Object {
    $val = docker stats $FRAMEWORK --no-stream --format "{{.CPUPerc}}"
    Start-Sleep -Seconds $interval
    ($val -replace '%','' -replace ',', '.') -as [double]
}

$cpuAvg = ($cpuList | Measure-Object -Average).Average

$cpuAvg | Out-File "$RESULT_DIR/cpu_${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${RUN}.txt"

# RAM
$memRaw = docker stats $FRAMEWORK --no-stream --format "{{.MemUsage}}"

# Приклад:
# 45.23MiB / 1.9GiB

if ($memRaw -match "^([\d\.,]+)(KiB|MiB|GiB)") {

    $value = ($matches[1] -replace ',', '.') -as [double]
    $unit = $matches[2]

    switch ($unit) {
        "KiB" { $value = $value / 1024 }
        "MiB" { $value = $value }
        "GiB" { $value = $value * 1024 }
    }

    $value | Out-File "$RESULT_DIR/ram_${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${RUN}.txt"
}
else {
    "0" | Out-File "$RESULT_DIR/ram_${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${PDF_SETS}_${RUN}.txt"
}

# STEP 7
Start-Sleep 60

# STEP 8
# Parse Locust CSV

$csv = "$RESULT_DIR/${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${PDF_SETS}_${RUN}_stats.csv"

if (!(Test-Path $csv)) {
    Write-Host "CSV missing!"
    exit 1
}

if ((Get-Item $csv).Length -eq 0) {
    Write-Host "CSV empty!"
    exit 1
}

Write-Host "Test completed"

$csvData = Import-Csv $csv

# Беремо aggregated row
$agg = $csvData | Where-Object {
    $_.Name -eq "Aggregated" -or
    $_.Name -eq "POST /upload"
} | Select-Object -First 1

if (!$agg) {
    Write-Host "Aggregated row not found!"
    Write-Host "CSV CONTENT:"
    $csvData | Format-Table
    exit 1
}


# METRICS

$rps = [double]($agg."Requests/s")
$p50 = [double]($agg."50%")
$p95 = [double]($agg."95%")
$p99 = [double]($agg."99%")

$failures = [double]($agg."Failure Count")
$total = [double]($agg."Request Count")

$errorRate = if ($total -gt 0) {
    ($failures / $total) * 100
} else {
    0
}

# TTA from Locust custom metric

$ttaAvg = 0

$archiveMetric = $csvData |
    Where-Object {
        $_.Type -eq "ARCHIVE"
    }

if ($archiveMetric) {

    $ttaAvg = [double](
        $archiveMetric."Average Response Time"
    )
}


# CPU / RAM

$cpuFile = "$RESULT_DIR/cpu_${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${PDF_SETS}_${RUN}.txt"
$ramFile = "$RESULT_DIR/ram_${FRAMEWORK}_${VCPU}_${CONCURRENCY}_${PDF_SETS}_${RUN}.txt"

if (Test-Path $cpuFile) {

    $cpuRaw = (Get-Content $cpuFile | Select-Object -First 1).Trim()

    try {
        $cpuUsage = [double]$cpuRaw
    }
    catch {
        $cpuUsage = 0
    }

} else {
    Write-Host "CPU file missing: $cpuFile"
    $cpuUsage = 0
}

if (Test-Path $ramFile) {

    $ramRaw = (Get-Content $ramFile | Select-Object -First 1).Trim()

    try {
        $ramUsage = [double]$ramRaw
    }
    catch {
        $ramUsage = 0
    }

} else {
    Write-Host "RAM file missing: $ramFile"
    $ramUsage = 0
}


# CREATE RESULT OBJECT

$resultLine = [PSCustomObject]@{
    Framework   = $FRAMEWORK
    VCPU        = $VCPU
    Concurrency = $CONCURRENCY
    PDF_SET   = $PDF_SETS
    Run         = $RUN
    
    RPS         = [math]::Round($rps, 4)

    P50_ms      = [math]::Round($p50, 4)
    P95_ms      = [math]::Round($p95, 4)
    P99_ms      = [math]::Round($p99, 4)

    ErrorRate   = [math]::Round($errorRate, 4)

    TTA_ms      = [math]::Round($ttaAvg, 4)

    CPU_Usage   = [math]::Round($cpuUsage, 4)
    RAM_MB      = [math]::Round($ramUsage, 4)
}


# SAVE TO final_results.csv

$resultFile = "$RESULT_DIR/final_results.csv"

# правильний порядок колонок
$columns = @(
    "Framework",
    "VCPU",
    "Concurrency",
    "Run",
    "PDF_SET",
    "RPS",
    "P50_ms",
    "P95_ms",
    "P99_ms",
    "ErrorRate",
    "TTA_ms",
    "CPU_Usage",
    "RAM_MB"
)

$row = $resultLine |
    Select-Object $columns |
    ConvertTo-Csv -NoTypeInformation

if (!(Test-Path $resultFile)) {

    $row | Set-Content $resultFile -Encoding UTF8

} else {

    $row | Select-Object -Skip 1 | Add-Content $resultFile
}

Write-Host "Saved results to $resultFile"


# DEBUG OUTPUT

Write-Host ""
Write-Host "================ RESULT ================"
Write-Host "Framework   : $FRAMEWORK"
Write-Host "VCPU        : $VCPU"
Write-Host "Concurrency : $CONCURRENCY"
Write-Host "PDF_SET         : $PDF_SETS"
Write-Host "Run         : $RUN"

Write-Host "RPS         : $rps"

Write-Host "P50         : $p50 ms"
Write-Host "P95         : $p95 ms"
Write-Host "P99         : $p99 ms"

Write-Host "Error Rate  : $errorRate %"

Write-Host "TTA         : $ttaAvg ms"

Write-Host "CPU Usage   : $cpuUsage %"
Write-Host "RAM Usage   : $ramUsage MB"

Write-Host "========================================"
Write-Host ""


#Stop-Transcript
