from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R19 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    old_helper = '''    static boolean pendingExistingImportAvailable(String associationStatus, String protectedState) {\n        return "import_pending".equals(String.valueOf(associationStatus))\n                && protectedState != null\n                && protectedState.trim().length() > 20;\n    }\n'''
    new_helper = '''    static boolean pendingExistingImportAvailable(String protectedState) {\n        return protectedState != null && protectedState.trim().length() > 20;\n    }\n'''
    s = replace_once(s, old_helper, new_helper, 'pending helper')

    title_marker = '        card.addView(title(activity, "Dossier e sincronizzazione cloud"));\n'
    top_pending = title_marker + '''        String pendingImportState = prefs.getString(PENDING_EXISTING_IMPORT_KEY, "");\n        if (pendingExistingImportAvailable(pendingImportState)) {\n            card.addView(warning(activity, "Importazione del Dossier incompleta. Il dispositivo è già autenticato: non devi reinserire chiave Dossier, account o TOTP."));\n            Button resumeImport = button(activity, "Riprendi importazione del Dossier");\n            resumeImport.setOnClickListener(v -> resumeExistingImport(activity, prefs));\n            card.addView(resumeImport, top(12));\n            card.addView(note(activity, "La procedura riparte dallo stato autenticato salvato e riutilizza l'archivio locale completo se già presente."));\n            content.addView(card, bottom(14));\n            return;\n        }\n'''
    s = replace_once(s, title_marker, top_pending, 'top-level pending resume panel')

    old_inner = '''            if (pendingExistingImportAvailable(cfg.optString("associationStatus", ""), prefs.getString(PENDING_EXISTING_IMPORT_KEY, ""))) {\n                card.addView(warning(activity, "Importazione del Dossier incompleta. Il dispositivo è già autenticato: non devi reinserire chiave Dossier, account o TOTP."));\n                Button resumeImport = button(activity, "Riprendi importazione del Dossier");\n                resumeImport.setOnClickListener(v -> resumeExistingImport(activity, prefs));\n                card.addView(resumeImport, top(12));\n                card.addView(note(activity, "La procedura riparte dall'ultimo archivio locale completo disponibile e conserva l'associazione già verificata."));\n                content.addView(card, bottom(14));\n                return;\n            }\n'''
    s = replace_once(s, old_inner, '', 'old configured-only resume panel')

    start = s.find('    private static void persistExistingImportCheckpoint(')
    end = s.find('    private static void showFamilyConnect(', start)
    if start < 0 or end < 0:
        raise SystemExit('R19 patch failed: checkpoint/resume block not found')
    new_checkpoint_block = r'''    private static void persistExistingImportCheckpoint(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account) throws Exception {
        JSONObject state = new JSONObject();
        state.put("payload", new JSONObject(payload.toString()));
        state.put("cfgDraft", new JSONObject(cfg.toString()));
        state.put("account", new JSONObject(account.toString()));
        state.put("storagePath", choice.root.getAbsolutePath());
        state.put("storageLabel", choice.label);
        state.put("snapshotName", snap == null ? "" : snap.name);
        state.put("snapshotSize", snap == null ? 0L : snap.size);
        state.put("savedAt", Instant.now().toString());
        String protectedState = R12Crypto.protectSecret(context, state.toString());
        prefs.edit().putString(PENDING_EXISTING_IMPORT_KEY, protectedState).apply();
    }

    private static void safeStartExistingImportProgress(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account) {
        try {
            startExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);
        } catch (Throwable e) {
            String message = String.valueOf(e.getMessage());
            new AlertDialog.Builder(activity)
                    .setTitle("Importazione non avviata")
                    .setMessage((message == null || message.trim().isEmpty() ? "Avvio dell'importazione non riuscito." : message) + "\n\nL'autenticazione resta salvata. Puoi usare Riprendi importazione del Dossier senza reinserire i dati.")
                    .setPositiveButton("Chiudi", null)
                    .show();
        }
    }

    private static void resumeExistingImport(Activity activity, SharedPreferences prefs) {
        try {
            String protectedState = prefs.getString(PENDING_EXISTING_IMPORT_KEY, "");
            if (!pendingExistingImportAvailable(protectedState)) throw new Exception("Nessuna importazione da riprendere.");
            JSONObject state = new JSONObject(R12Crypto.unprotectSecret(activity, protectedState));
            JSONObject payload = state.getJSONObject("payload");
            JSONObject account = state.getJSONObject("account");
            JSONObject cfg = state.optJSONObject("cfgDraft");
            if (cfg == null) cfg = loadConfig(prefs); // compatibilità con checkpoint R18 già presenti sul dispositivo
            File root = new File(state.getString("storagePath"));
            String label = state.optString("storageLabel", "Memoria del Dossier");
            StorageChoice choice = new StorageChoice(root, label, freeBytes(root));
            String snapshotName = state.optString("snapshotName", "");
            long snapshotSize = state.optLong("snapshotSize", 0L);
            SnapshotInfo snap = snapshotName.isEmpty() ? null : new SnapshotInfo(snapshotName, snapshotSize);
            safeStartExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);
        } catch (Exception e) {
            String message = String.valueOf(e.getMessage());
            new AlertDialog.Builder(activity)
                    .setTitle("Ripresa importazione non disponibile")
                    .setMessage(message == null || message.trim().isEmpty() ? "Lo stato di ripresa non è leggibile." : message)
                    .setPositiveButton("Chiudi", null)
                    .show();
        }
    }

'''
    s = s[:start] + new_checkpoint_block + s[end:]

    old_start_call = '                        startExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);\n'
    new_start_call = '                        safeStartExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);\n'
    s = replace_once(s, old_start_call, new_start_call, 'safe start after TOTP')

    old_show = '''        activity.getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        android.os.PowerManager power = (android.os.PowerManager) activity.getSystemService(Context.POWER_SERVICE);\n        final android.os.PowerManager.WakeLock wakeLock = power == null ? null : power.newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK, "ClinicaDigitale:ImportDossier");\n        if (wakeLock != null) wakeLock.acquire(java.util.concurrent.TimeUnit.MINUTES.toMillis(30));\n        progress.show();\n\n        EXECUTOR.execute(() -> {\n'''
    new_show = '''        activity.getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        android.os.PowerManager.WakeLock wakeLockCandidate = null;\n        try {\n            android.os.PowerManager power = (android.os.PowerManager) activity.getSystemService(Context.POWER_SERVICE);\n            if (power != null) {\n                wakeLockCandidate = power.newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK, "ClinicaDigitale:ImportDossier");\n                wakeLockCandidate.acquire(java.util.concurrent.TimeUnit.MINUTES.toMillis(30));\n            }\n        } catch (Throwable ignored) {\n            wakeLockCandidate = null;\n        }\n        final android.os.PowerManager.WakeLock wakeLock = wakeLockCandidate;\n        progress.show();\n\n        EXECUTOR.execute(() -> {\n'''
    s = replace_once(s, old_show, new_show, 'nonfatal wake lock')

    early_clear = '''        cfg.put("associationStatus", "active");\n        saveConfig(prefs, cfg);\n        prefs.edit().remove(PENDING_EXISTING_IMPORT_KEY).apply();\n\n        setImportProgress(activity, progress, 98, "Preparazione sincronizzazione automatica...");\n'''
    delayed_clear = '''        cfg.put("associationStatus", "active");\n        saveConfig(prefs, cfg);\n\n        setImportProgress(activity, progress, 98, "Preparazione sincronizzazione automatica...");\n'''
    s = replace_once(s, early_clear, delayed_clear, 'do not clear checkpoint before final completion')

    finish_marker = '        setImportProgress(activity, progress, 100, "Completamento...");\n'
    finish_new = finish_marker + '        prefs.edit().remove(PENDING_EXISTING_IMPORT_KEY).apply();\n'
    s = replace_once(s, finish_marker, finish_new, 'clear checkpoint only after full success')

    CLOUD.write_text(s, encoding='utf-8')


def patch_version():
    s = MAIN.read_text(encoding='utf-8')
    s = s.replace('Android R18 TEST', 'Android R19 TEST')
    s = s.replace('Aiuto R18', 'Aiuto R19')
    s = s.replace('R18: struttura presente', 'R19: struttura presente')
    s = s.replace('R18 mantiene lo stesso pacchetto Android', 'R19 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R17', 'Installala sopra la R18')
    MAIN.write_text(s, encoding='utf-8')

    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 18', 'versionCode 19', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r18-test'", "versionName '1.0.0-android-r19-test'", 'versionName')
    GRADLE.write_text(g, encoding='utf-8')


patch_cloud()
patch_version()
print('R19 transactional authenticated resume patch applied')
