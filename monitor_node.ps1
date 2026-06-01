while ($true) {

    $time = Get-Date -Format "HH:mm:ss"

    $proc = Get-Process node -ErrorAction SilentlyContinue

    if ($proc) {

        $cpu = $proc.CPU
        $ram = [math]::Round($proc.WorkingSet64 / 1MB, 2)

        "$time,$cpu,$ram" | Out-File `
            metrics.csv `
            -Append
    }

    Start-Sleep 30
}