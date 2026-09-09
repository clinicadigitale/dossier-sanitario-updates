from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
text = MAIN.read_text(encoding='utf-8')
if 'Android R39 TEST COMPLETO' not in text:
    raise SystemExit('R39 compatibility check failed: release marker missing')
print('R39 compatibility marker verified')
