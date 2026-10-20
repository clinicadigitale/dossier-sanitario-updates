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
powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Certificate -FilePath '.\DossierSanitario.cer' -CertStoreLocation Cert:\LocalMachine\Root | Out-Null; Import-Certificate -FilePath '.\DossierSanitario.cer' -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null; Add-AppxPackage -Path '.\DossierSanitario.msix'"
if %errorlevel% neq 0 (
  echo.
  echo ERRORE durante l'installazione. Riprova o avvisami.
  pause
  exit /b
)
echo.
echo FATTO. Apri "Dossier Sanitario - PROVA (Store)" dal menu Start.
echo Al primo avvio ti chiedera' se creare l'icona sul desktop.
echo.
pause
