from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
EXACT = BASE / 'R27ExactWindows.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R30 patch failed: missing {label}')

# All exact Windows reconstruction paths must use the bounded-memory importer.
c = CLOUD.read_text(encoding='utf-8')
replacements = [
    (
        'R27ExactWindows.importSnapshot(activity, prefs, cfg, verifiedZip);',
        'R30BoundedWindows.importSnapshot(activity, prefs, cfg, verifiedZip, null);',
        'fresh exact import hook'
    ),
    (
        'R27ExactWindows.importSnapshot(activity, prefs, cfg, verified);',
        'R30BoundedWindows.importSnapshot(activity, prefs, cfg, verified, null);',
        'legacy upgrade bootstrap'
    ),
    (
        'R27ExactWindows.importSnapshot(activity, prefs, cfg, verified, importProgress);',
        'R30BoundedWindows.importSnapshot(activity, prefs, cfg, verified, importProgress);',
        'R29 post-login bootstrap'
    ),
]
for old, new, label in replacements:
    require(c, old, label)
    c = c.replace(old, new, 1)
CLOUD.write_text(c, encoding='utf-8')

# Keep the existing R27 UI/API contract, but allow large arrays to live on disk.
e = EXACT.read_text(encoding='utf-8')
old_pref = '''    private static JSONArray readArrayPref(SharedPreferences prefs, String key) {\n        try { return new JSONArray(prefs.getString(key, "[]")); } catch (Exception e) { return new JSONArray(); }\n    }'''
new_pref = '''    private static JSONArray readArrayPref(SharedPreferences prefs, String key) {\n        try {\n            String raw = prefs.getString(key, "[]");\n            if (raw != null && raw.startsWith("@file:")) {\n                return R30BoundedWindows.readArrayFile(new File(raw.substring("@file:".length())));\n            }\n            return new JSONArray(raw == null ? "[]" : raw);\n        } catch (Throwable failure) {\n            return new JSONArray();\n        }\n    }'''
require(e, old_pref, 'disk-backed readArrayPref')
e = e.replace(old_pref, new_pref, 1)

old_open = '''            String path = doc.optString("localPath", "");\n            File source = new File(path);\n            if (!source.isFile()) throw new Exception("File originale non disponibile");'''
new_open = '''            String path = doc.optString("localPath", "");\n            File source = path == null || path.trim().isEmpty()\n                    ? R30BoundedWindows.resolveDocumentFile(activity, doc)\n                    : new File(path);\n            if (!source.isFile()) throw new Exception("File originale non disponibile");'''
require(e, old_open, 'document resolver')
e = e.replace(old_open, new_open, 1)
EXACT.write_text(e, encoding='utf-8')

# Visible R30 test identity. Existing R29 progress/crash-guard methods remain frozen.
s = MAIN.read_text(encoding='utf-8')
s = s.replace('Android R29 TEST COMPLETO', 'Android R30 TEST COMPLETO')
s = s.replace('Aiuto R29', 'Aiuto R30')
s = s.replace('R29: sezione completa collegata al backup Windows', 'R30: sezione completa collegata al backup Windows')
s = s.replace('R29 mantiene lo stesso pacchetto Android', 'R30 mantiene lo stesso pacchetto Android')
s = s.replace('Installala sopra la R28', 'Installala sopra la R29')
MAIN.write_text(s, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
require(g, 'versionCode 29', 'versionCode 29')
require(g, "versionName '1.0.0-android-r29-progress-crashguard-test'", 'R29 versionName')
g = g.replace('versionCode 29', 'versionCode 30', 1)
g = g.replace("versionName '1.0.0-android-r29-progress-crashguard-test'", "versionName '1.0.0-android-r30-bounded-import-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R30 bounded-memory Windows import patch applied')
