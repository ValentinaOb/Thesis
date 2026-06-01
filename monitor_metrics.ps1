param(
    [string]$FRAMEWORK,
    [string]$RESULT_DIR
)

# CREATE RESULTS DIR

New-Item `
    -ItemType Directory `
    -Force `
    -Path $RESULT_DIR | Out-Null

# CSV FILE

$csvFile = Join-Path `
    $RESULT_DIR `
    "endurance_metrics_${FRAMEWORK}.csv"

Write-Host "Writing metrics to: $csvFile"

"timestamp,cpu_percent,ram_mb" |
    Out-File `
    $csvFile `
    -Encoding utf8

# CONTAINER

$container = $FRAMEWORK

Write-Host "Monitoring container: $container"

# LOOP

while ($true) {

    try {

        $timestamp = Get-Date `
            -Format "yyyy-MM-dd HH:mm:ss"

        $stats = docker stats `
            --no-stream `
            --format "{{.CPUPerc}},{{.MemUsage}}" `
            $container

        if (!$stats) {

            Write-Host "No docker stats available"

            Start-Sleep 30
            continue
        }

        # Example:
        # 12.45%,120.3MiB / 2GiB

        $parts = $stats -split ","

        # CPU

        $cpuRaw = $parts[0]

        $cpu = $cpuRaw.Replace("%", "")
        $cpu = $cpu.Replace(",", ".")
        $cpu = $cpu.Trim()

        # RAM

        $memRaw = $parts[1]

        $ram = 0

        if ($memRaw -match "^([\d\.]+)(MiB|GiB)") {

            $value = [double]$matches[1]
            $unit = $matches[2]

            if ($unit -eq "GiB") {

                $value = $value * 1024
            }

            $ram = [math]::Round($value, 2)
        }

        # SAVE CSV

        "$timestamp,$cpu,$ram" |
            Out-File `
            $csvFile `
            -Append `
            -Encoding utf8

        Write-Host "$timestamp CPU=$cpu RAM=$ram"

    }
    catch {

        Write-Host "Monitor error:"
        Write-Host $_
    }

    Start-Sleep 30
}