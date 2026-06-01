$FRAMEWORKS = @("node", "python")
#$PDF_SETS = @("small","medium","large")
$PDF_SETS = @("small")

#
if ($FRAMEWORK -eq "node") {
    $env:LOCUSTFILE = "locustfile_node.py"
    $env:TARGET_HOST = "http://node:3000"
}
else {
    $env:LOCUSTFILE = "locustfile_python.py"
    $env:TARGET_HOST = "http://python:8000"
}

docker compose up locust
#

foreach ($PDF in $PDF_SETS){
    foreach ($F in $FRAMEWORKS) {

        .\run_test_endurance.ps1 `
            -FRAMEWORK $F `
            -PDF_SETS $PDF `
            -VCPU 4 `
            -CONCURRENCY 100 `
            -DURATION_MIN 60
            
    }
}