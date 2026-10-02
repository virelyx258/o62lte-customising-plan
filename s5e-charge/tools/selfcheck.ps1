# S5eChg rebuild + self-check pipeline. Key output is appended to docs/selfcheck_run.txt
# Usage:  & ".\\.work\\selfcheck.ps1"     (run from the project root)
# NOTE: keep this file pure ASCII -- the Chinese text comes from the python tools.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$proj = Split-Path -Parent $PSScriptRoot
Set-Location $proj
$py = 'C:\Users\hi\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$log = 'docs\selfcheck_run.txt'
$bar = '=' * 78

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"S5eChg rebuild + self-check run: $stamp" | Out-File -Encoding utf8 $log
"Python : $py" | Out-File -Append -Encoding utf8 $log
"Project: $proj" | Out-File -Append -Encoding utf8 $log

function Step([string[]]$argv) {
    $line = '>>> python ' + ($argv -join ' ')
    $bar | Out-File -Append -Encoding utf8 $log
    $line | Out-File -Append -Encoding utf8 $log
    $bar | Out-File -Append -Encoding utf8 $log
    Write-Host ''
    Write-Host $line
    & $py @argv 2>&1 | Tee-Object -FilePath $log -Append
    $rc = $LASTEXITCODE
    "EXIT=$rc" | Out-File -Append -Encoding utf8 $log
    Write-Host "EXIT=$rc"
    if ($rc -ne 0) {
        Write-Host '!! step failed, aborting' -ForegroundColor Red
        exit $rc
    }
}

Step @('tools\make_charge_payload.py', 'all')
Step @('tools\make_dd_payload.py', 'replace')
Step @('tools\gen_ui_lua.py', 'replace')
Step @('tools\verify_anim.py', 'replace')
Step @('tools\make_dd_payload.py', 'restore')
Step @('tools\gen_ui_lua.py', 'restore')
Step @('tools\verify_anim.py', 'restore')
Step @('tools\verify_all.py')

'' | Out-File -Append -Encoding utf8 $log
'ALL STEPS OK' | Out-File -Append -Encoding utf8 $log
Write-Host ''
Write-Host "ALL STEPS OK -- log: $log"
