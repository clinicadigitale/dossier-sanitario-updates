@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Richiesta dei permessi di amministratore...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
cd /d "%~dp0"
echo ============================================================
echo   Installazione di: Dossier Sanitario - PROVA (Store)
echo   (versione di prova, NON sostituisce la tua versione attuale)
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Certificate -FilePath '.\DossierSanitario.cer' -CertStoreLocation Cert:\LocalMachine\Root | Out-Null; Import-Certificate -FilePath '.\DossierSanitario.cer' -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null; Add-AppxPackage -Path '.\DossierSanitario.msix' -ForceUpdateFromAnyVersion"
if %errorlevel% neq 0 (
  echo.
  echo ERRORE durante l'installazione. Riprova o avvisami.
  pause
  exit /b
)
echo.
rem Rimuove una eventuale vecchia icona generica della prova precedente
if exist "%USERPROFILE%\Desktop\Dossier Sanitario PROVA.lnk" del /f /q "%USERPROFILE%\Desktop\Dossier Sanitario PROVA.lnk"
echo.
choice /C SN /N /M "Vuoi creare l'icona sul desktop? [S=si  N=no]: "
if errorlevel 2 goto FINE
if not exist "%LOCALAPPDATA%\DossierProva" mkdir "%LOCALAPPDATA%\DossierProva"
copy /y ".\DossierProva.ico" "%LOCALAPPDATA%\DossierProva\DossierProva.ico" >nul
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $lnk=[Environment]::GetFolderPath('Desktop')+'\Dossier Sanitario PROVA.lnk'; $s=$ws.CreateShortcut($lnk); $s.TargetPath='explorer.exe'; $s.Arguments='shell:AppsFolder\ClinicaDigitale.DossierSanitario_jg1xxf87v0t26!DossierSanitario'; $s.IconLocation=$env:LOCALAPPDATA+'\DossierProva\DossierProva.ico'; $s.Save()"
echo Icona creata sul desktop.
:FINE
echo.
echo FATTO. Apri "Dossier Sanitario - PROVA (Store)" dal menu Start
echo oppure dall'icona sul desktop (se creata).
echo.
pause
