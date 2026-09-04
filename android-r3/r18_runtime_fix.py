from pathlib import Path

CLOUD = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java')

s = CLOUD.read_text(encoding='utf-8')

old_clock = '            long now = android.os.SystemClock.elapsedRealtime();\n'
new_clock = '            long now = System.nanoTime() / 1000000L;\n'
if old_clock not in s:
    raise SystemExit('R18 runtime fix failed: SystemClock marker missing')
s = s.replace(old_clock, new_clock, 1)

old_helper = '''    static boolean pendingExistingImportAvailable(JSONObject cfg, String protectedState) {\n        return cfg != null\n                && "import_pending".equals(cfg.optString("associationStatus", ""))\n                && protectedState != null\n                && protectedState.trim().length() > 20;\n    }\n'''
new_helper = '''    static boolean pendingExistingImportAvailable(String associationStatus, String protectedState) {\n        return "import_pending".equals(String.valueOf(associationStatus))\n                && protectedState != null\n                && protectedState.trim().length() > 20;\n    }\n'''
if old_helper not in s:
    raise SystemExit('R18 runtime fix failed: pending helper marker missing')
s = s.replace(old_helper, new_helper, 1)

old_render = '            if (pendingExistingImportAvailable(cfg, prefs.getString(PENDING_EXISTING_IMPORT_KEY, ""))) {\n'
new_render = '            if (pendingExistingImportAvailable(cfg.optString("associationStatus", ""), prefs.getString(PENDING_EXISTING_IMPORT_KEY, ""))) {\n'
if old_render not in s:
    raise SystemExit('R18 runtime fix failed: render pending call missing')
s = s.replace(old_render, new_render, 1)

old_resume = '            if (!pendingExistingImportAvailable(cfg, protectedState)) throw new Exception("Nessuna importazione da riprendere.");\n'
new_resume = '            if (!pendingExistingImportAvailable(cfg.optString("associationStatus", ""), protectedState)) throw new Exception("Nessuna importazione da riprendere.");\n'
if old_resume not in s:
    raise SystemExit('R18 runtime fix failed: resume pending call missing')
s = s.replace(old_resume, new_resume, 1)

CLOUD.write_text(s, encoding='utf-8')
print('R18 runtime helper fix applied')
