# Přepínač Diktátu: když běží, vypne ho; když neběží, zapne ho (bez konzole).
$root = $PSScriptRoot
$procs = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'run\.pyw|-m diktat(\s|$)' }

if ($procs) {
    $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "Diktat VYPNUT" -ForegroundColor Yellow
} else {
    # python.exe se skrytým oknem (pythonw.exe blokuje Smart App Control)
    Start-Process -FilePath (Join-Path $root ".venv\Scripts\python.exe") `
        -ArgumentList "`"$(Join-Path $root 'run.pyw')`"" -WorkingDirectory $root -WindowStyle Hidden
    Write-Host "Diktat ZAPNUT - za par sekund zezelena ikona v liste" -ForegroundColor Green
}
Start-Sleep -Seconds 2
