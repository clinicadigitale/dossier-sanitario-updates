from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R24 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    # Una volta verificate le credenziali, conserva l'account locale per il gate
    # di accesso. La chiave Dossier resta nel checkpoint e non viene richiesta di nuovo.
    old_prepare = '''                persistExistingImportCheckpoint(activity, prefs, payload, cfg, choice, snap, account);\n                Toast.makeText(activity, "Account verificato. Avvio importazione del Dossier.", Toast.LENGTH_SHORT).show();\n'''
    new_prepare = '''                persistExistingImportCheckpoint(activity, prefs, payload, cfg, choice, snap, account);\n                prefs.edit().putString(ACCOUNT_KEY, account.toString()).apply();\n                Toast.makeText(activity, "Account verificato. Avvio importazione del Dossier.", Toast.LENGTH_SHORT).show();\n'''
    s = replace_once(s, old_prepare, new_prepare, 'persist verified account before first import')

    # Recupera l'account dal checkpoint R20/R23 dopo un'importazione interrotta,
    # così il riavvio passa sempre dalle credenziali e non riapre il Dossier liberamente.
    resume_marker = '    private static void persistExistingImportCheckpoint(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account) throws Exception {\n'
    recover_method = r'''    public static JSONObject recoverPendingAccountForLogin(Context context, SharedPreferences prefs) {
        try {
            String existing = prefs.getString(ACCOUNT_KEY, "");
            if (existing != null && !existing.trim().isEmpty()) return new JSONObject(existing);
            String protectedState = prefs.getString(PENDING_EXISTING_IMPORT_KEY, "");
            if (!pendingExistingImportAvailable(protectedState)) return null;
            JSONObject state = new JSONObject(R20CheckpointCrypto.unprotect(context, protectedState));
            JSONObject account = state.optJSONObject("account");
            if (account == null || !account.optBoolean("active", true)) return null;
            prefs.edit().putString(ACCOUNT_KEY, account.toString()).apply();
            return new JSONObject(account.toString());
        } catch (Exception e) {
            return null;
        }
    }

'''
    s = replace_once(s, resume_marker, recover_method + resume_marker, 'pending account recovery for login')

    # Il pacchetto Windows V8 e' volutamente generico: linkedProfileId e' vuoto.
    # Per un account gia' esistente si usa prima il profilo collegato all'account;
    # per l'amministratore il profilo personale viene risolto dal contenuto verificato.
    old_cfg = '''        String linked = account.optString("linkedProfileId", "");\n        if (linked.isEmpty() && payload.optJSONObject("membershipTemplate") != null) linked = payload.optJSONObject("membershipTemplate").optString("linkedProfileId", "");\n        cfg.put("linkedProfileId", linked);\n        cfg.put("accessLevel", "administrator".equals(account.optString("role")) ? "administrator" : account.optString("accessLevel", "viewer"));\n        cfg.put("profileName", payload.optString("profileName", account.optString("displayName", "")));\n'''
    new_cfg = '''        String linked = account.optString("linkedProfileId", "");\n        if (linked.isEmpty() && payload.optJSONObject("membershipTemplate") != null) linked = payload.optJSONObject("membershipTemplate").optString("linkedProfileId", "");\n        boolean administrator = "administrator".equals(account.optString("role", ""));\n        cfg.put("linkedProfileId", linked);\n        cfg.put("accessLevel", administrator ? "administrator" : account.optString("accessLevel", "viewer"));\n        cfg.put("accountDisplayName", account.optString("displayName", ""));\n        cfg.put("profileName", linked.isEmpty() ? account.optString("displayName", "") : payload.optString("profileName", account.optString("displayName", "")));\n'''
    s = replace_once(s, old_cfg, new_cfg, 'existing account profile authorization draft')

    old_import_start = '''    private static void importSnapshotWithProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {\n        String linked = cfg.optString("linkedProfileId", "");\n        if (linked.isEmpty()) throw new Exception("Profilo autorizzato non indicato.");\n        String linkedFolder = null;\n'''
    new_import_start = '''    private static void importSnapshotWithProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {\n        R24ProfileResolver.Result resolvedProfile = R24ProfileResolver.resolve(\n                verifiedZip,\n                cfg.optString("linkedProfileId", ""),\n                "administrator".equals(cfg.optString("accessLevel", "")),\n                cfg.optString("accountDisplayName", cfg.optString("profileName", "")));\n        String linked = resolvedProfile.id;\n        if (linked.isEmpty()) throw new Exception("Profilo autorizzato non indicato.");\n        cfg.put("linkedProfileId", linked);\n        if (!resolvedProfile.name.isEmpty()) cfg.put("profileName", resolvedProfile.name);\n        String linkedFolder = null;\n'''
    s = replace_once(s, old_import_start, new_import_start, 'resolve administrator profile before import')

    CLOUD.write_text(s, encoding='utf-8')


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    old_gate = '''        JSONObject account = localAccount();\n        if (account == null) {\n            showPairingOnlyScreen();\n            return;\n        }\n        showLoginScreen(state, account);\n'''
    new_gate = '''        JSONObject account = localAccount();\n        if (account == null) account = R12CloudManager.recoverPendingAccountForLogin(this, prefs);\n        if (account == null) {\n            showPairingOnlyScreen();\n            return;\n        }\n        showLoginScreen(state, account);\n'''
    s = replace_once(s, old_gate, new_gate, 'startup login recovery from pending checkpoint')

    s = s.replace('Android R23 TEST', 'Android R24 TEST')
    s = s.replace('Aiuto R23', 'Aiuto R24')
    s = s.replace('R23: struttura presente', 'R24: struttura presente')
    s = s.replace('R23 mantiene lo stesso pacchetto Android', 'R24 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R22', 'Installala sopra la R23')
    MAIN.write_text(s, encoding='utf-8')


def patch_version():
    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 23', 'versionCode 24', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r23-test'", "versionName '1.0.0-android-r24-test'", 'versionName')
    GRADLE.write_text(g, encoding='utf-8')


patch_cloud()
patch_main()
patch_version()
print('R24 administrator profile resolution and gated resume patch applied')
