#!/usr/bin/env bash
set -euo pipefail
APK=/tmp/r28-smoke.apk

adb install -r "$APK"
adb shell am start -W -n it.dossiersanitario.clinicadigitale.beta/.R6MainActivity >/tmp/clean-start.txt
sleep 2
adb shell pidof it.dossiersanitario.clinicadigitale.beta >/tmp/clean-pid.txt
test -s /tmp/clean-pid.txt
adb shell am force-stop it.dossiersanitario.clinicadigitale.beta

printf '%s' 'PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0ndXRmLTgnIHN0YW5kYWxvbmU9J3llcycgPz4KPG1hcD4KICA8c3RyaW5nIG5hbWU9InIxMl9hY2NvdW50X2pzb24iPnsmcXVvdDt1c2VybmFtZSZxdW90OzomcXVvdDt0ZXN0JnF1b3Q7LCZxdW90O2FjdGl2ZSZxdW90Ozp0cnVlfTwvc3RyaW5nPgogIDxzdHJpbmcgbmFtZT0icjEyX2Nsb3VkX2NvbmZpZ19qc29uIj57JnF1b3Q7YXJjaGl2ZUlkJnF1b3Q7OiZxdW90O3Rlc3QtYXJjaGl2ZSZxdW90OywmcXVvdDthc3NvY2lhdGlvblN0YXR1cyZxdW90OzomcXVvdDthY3RpdmUmcXVvdDt9PC9zdHJpbmc+CjwvbWFwPgo=' | base64 -d >/tmp/r28prefs.xml
adb shell run-as it.dossiersanitario.clinicadigitale.beta mkdir -p shared_prefs
adb exec-out run-as it.dossiersanitario.clinicadigitale.beta sh -c 'cat > shared_prefs/clinica_android_beta.xml' </tmp/r28prefs.xml

adb logcat -c
adb shell am start -W -n it.dossiersanitario.clinicadigitale.beta/.R6MainActivity | tee /tmp/configured-start.txt
sleep 3
adb shell pidof it.dossiersanitario.clinicadigitale.beta | tee /tmp/configured-pid.txt
test -s /tmp/configured-pid.txt
adb shell uiautomator dump /sdcard/r28-window.xml >/dev/null
adb pull /sdcard/r28-window.xml /tmp/r28-window.xml >/dev/null
grep -q 'Accesso al Dossier' /tmp/r28-window.xml
grep -q 'Nome utente' /tmp/r28-window.xml
grep -q 'Password' /tmp/r28-window.xml
if adb logcat -d -v brief | grep -E 'FATAL EXCEPTION|Process: it.dossiersanitario.clinicadigitale.beta'; then
  exit 1
fi

echo 'R28_CONFIGURED_STARTUP_SMOKE=PASS'
