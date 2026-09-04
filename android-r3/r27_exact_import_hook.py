from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'

s = CLOUD.read_text(encoding='utf-8')
old = '''        capture.commit(prefs);\n        setImportProgress(activity, progress, 96, "Dati, preferenze e impostazioni Windows importati.");'''
new = '''        capture.commit(prefs);\n        R27ExactWindows.importSnapshot(activity, prefs, cfg, verifiedZip);\n        setImportProgress(activity, progress, 96, "Dossier Windows completo importato: profili, documenti, tessera, grafici e preferenze.");'''
if old not in s:
    raise SystemExit('R27 import hook failed')
s = s.replace(old, new, 1)
CLOUD.write_text(s, encoding='utf-8')
print('R27 exact import hook applied')
