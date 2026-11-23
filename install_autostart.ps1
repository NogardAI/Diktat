# Vytvoří zástupce Diktátu ve složce Po spuštění (shell:startup).
# Odebrání: smaž "Diktat.lnk" ve složce, kterou skript vypíše.
$root = $PSScriptRoot
$startup = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $startup "Diktat.lnk"
$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = Join-Path $root "Diktat.bat"
$s.WorkingDirectory = $root
$s.WindowStyle = 7  # minimalizované okno přepínače
$s.Description = "Diktát - push-to-talk diktování"
$s.Save()
Write-Output "Autostart vytvořen: $lnk"
