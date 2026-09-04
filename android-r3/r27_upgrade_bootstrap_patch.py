from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'

c = CLOUD.read_text(encoding='utf-8')
marker = '    public static boolean configured(SharedPreferences prefs) {\n'
if marker not in c:
    raise SystemExit('R27 bootstrap patch failed: configured marker missing')
method = r'''    public static boolean bootstrapR27ExactIfNeeded(Activity activity, SharedPreferences prefs) {
        if (activity == null || prefs == null) return false;
        if (R27ExactWindows.profiles(prefs).length() > 0) return true;
        File verified = null;
        try {
            JSONObject cfg = loadConfig(prefs);
            if (cfg.optString("archiveId", "").isEmpty()) return false;
            File snapshot = currentSnapshot(activity, cfg);
            if (snapshot == null || !snapshot.isFile()) return false;
            byte[] recovery = recoveryKey(activity, cfg);
            verified = File.createTempFile("r27_upgrade_", ".zip", activity.getCacheDir());
            R22StreamingDsl5.decryptVerified(snapshot, verified, recovery, null);
            R27ExactWindows.importSnapshot(activity, prefs, cfg, verified);
            return R27ExactWindows.profiles(prefs).length() > 0;
        } catch (Exception ignored) {
            return false;
        } finally {
            if (verified != null && verified.exists()) verified.delete();
        }
    }

'''
c = c.replace(marker, method + marker, 1)
CLOUD.write_text(c, encoding='utf-8')

s = MAIN.read_text(encoding='utf-8')
old = '        cleanCameraTemp();\n        loadR26ImportedUiSettings();\n'
new = '        cleanCameraTemp();\n        R12CloudManager.bootstrapR27ExactIfNeeded(this, prefs);\n        loadR26ImportedUiSettings();\n'
if old not in s:
    raise SystemExit('R27 bootstrap patch failed: startup marker missing')
s = s.replace(old, new, 1)
MAIN.write_text(s, encoding='utf-8')
print('R27 upgrade bootstrap applied')
