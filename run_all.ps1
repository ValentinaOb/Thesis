# Clear final_results before start
'''$resultFile = "final_results.csv"

if (Test-Path $resultFile) {
    Clear-Content $resultFile
}
else {
    New-Item -Path $resultFile -ItemType File | Out-Null
}'''


$FRAMEWORKS = @("node","python")
#$PDF_SETS = @("small","medium","large")
$PDF_SETS = @("small")
$RUNS = 1..5
#$CONCURRENCY_LIST = @(1,10,25,50,100,150,250,300,350,400,450,500)
$CONCURRENCY_LIST = @(400,450,500)
$RESULT_DIR = "results"

Write-Host "Saving to: $resultFile"
Write-Host "Result object:"
$resultLine | Format-List *
if (!(Test-Path $RESULT_DIR)) {
    New-Item -ItemType Directory -Path $RESULT_DIR | Out-Null
}

try {
    Stop-Transcript | Out-Null
}
catch {}

try {
    Start-Transcript -Path "$RESULT_DIR/results_log.txt" -Append
}
catch {
    Write-Host "Transcript could not be started"
}


foreach ($PDF in $PDF_SETS) {

    foreach ($C in $CONCURRENCY_LIST) {

        foreach ($F in $FRAMEWORKS) {

            if ($F -eq "node") {

                $env:LOCUSTFILE = "locustfile_node.py"
                $env:TARGET_HOST = "http://node:3000"

            }
            else {

                $env:LOCUSTFILE = "locustfile_python.py"
                $env:TARGET_HOST = "http://python:8000"
            }

            # NEW VARIABLE
            $env:PDF_SET = $PDF


            foreach ($R in $RUNS) {

                Write-Host ""
                Write-Host "======================================="
                Write-Host "FRAMEWORK   : $F"
                Write-Host "PDF_SET     : $PDF"
                Write-Host "CONCURRENCY : $C"
                Write-Host "RUN         : $R"
                Write-Host "======================================="
                Write-Host ""

                .\run_test.ps1  `
                    -FRAMEWORK $F `
                    -VCPU 4 `
                    -CONCURRENCY $C `
                    -RUN $R `
                    -PDF_SETS $PDF
            }
        }
    }
}


Write-Host "Analysis and plot generation completed."

try {
    Stop-Transcript
}
catch {}

# Запуску Аналізу, якщо помилки - записуються в analysis
# Перевірка
'''Write-Host "Checking Python..."
python --version

Write-Host "Running analysis..."

# Run main analysis
$analysisOutput = python analyze.py 2>&1 | Out-String
# $analysisOutput = python analyze.py 2>&1
$analysisOutput | Tee-Object -FilePath "analysis.log"

Write-Host $analysisOutput

# Run plot generation
Write-Host "Generating plots..."

#$analysisOutput = python analyze_plots.py 2>&1 | Out-String
#$plotsOutput | Tee-Object -FilePath "plots.log"
$plotsOutput = python analyze_plots.py 2>&1 | Out-String
$plotsOutput | Tee-Object -FilePath "plots.log"

Write-Host $plotsOutput'''
