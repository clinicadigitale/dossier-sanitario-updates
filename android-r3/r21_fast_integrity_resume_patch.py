from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R21 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    old_range = r'''    private static void setImportRangeProgress(Activity activity, ProgressDialog progress, int start, int end, long done, long total, String label) {
        long safeTotal = Math.max(1L, total);
        long safeDone = Math.max(0L, Math.min(done, safeTotal));
        int value = importRangePercent(start, end, safeDone, safeTotal);
        setImportProgress(activity, progress, value, label + "\n" + formatBytes(safeDone) + " / " + formatBytes(safeTotal));
    }
'''
    new_range = r'''    static String formatProgressBytesOneDecimal(long bytes) {
        if (bytes < MB) return formatBytes(bytes);
        String number = String.format(Locale.ROOT, "%.1f", bytes / (double) MB).replace('.', ',');
        return number + " MB";
    }

    private static void setImportRangeProgress(Activity activity, ProgressDialog progress, int start, int end, long done, long total, String label) {
        long safeTotal = Math.max(1L, total);
        long safeDone = Math.max(0L, Math.min(done, safeTotal));
        int value = importRangePercent(start, end, safeDone, safeTotal);
        setImportProgress(activity, progress, value, label + "\n" + formatProgressBytesOneDecimal(safeDone) + " / " + formatBytes(safeTotal));
    }
'''
    s = replace_once(s, old_range, new_range, 'one decimal progress display')

    start = s.find('    static void verifySnapshotIntegrityCore(File snapshot, byte[] recovery, ImportProgressCallback callback) throws Exception {')
    end = s.find('    private static void populateExistingConnectionConfig(', start)
    if start < 0 or end < 0:
        raise SystemExit('R21 patch failed: integrity method block not found')

    new_integrity = r'''    static void verifySnapshotIntegrityCore(File snapshot, byte[] recovery, ImportProgressCallback callback) throws Exception {
        File parent = snapshot == null ? null : snapshot.getParentFile();
        File verified = File.createTempFile("r21_verify_", ".zip", parent);
        try {
            R21FastDsl5.decryptVerified(snapshot, verified, recovery,
                    (done, total) -> { if (callback != null) callback.onProgress(done, total); });
        } finally {
            if (verified.exists()) verified.delete();
        }
    }

    private static File prepareVerifiedSnapshotProgress(Activity activity, ProgressDialog progress, File snapshot, byte[] recovery) throws Exception {
        File verified = File.createTempFile("r21_verified_", ".zip", activity.getCacheDir());
        boolean success = false;
        try {
            R21FastDsl5.decryptVerified(snapshot, verified, recovery,
                    (done, all) -> setImportRangeProgress(activity, progress,
                            INTEGRITY_PROGRESS_START, INTEGRITY_PROGRESS_END,
                            done, all,
                            "Verifica integrità del Dossier...\nIn questa fase possono essere necessari diversi minuti."));
            setImportProgress(activity, progress, INTEGRITY_PROGRESS_END, "Integrità verificata.");
            success = true;
            return verified;
        } finally {
            if (!success && verified.exists()) verified.delete();
        }
    }

'''
    s = s[:start] + new_integrity + s[end:]

    old_signature = '    private static void importSnapshotWithProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject cfg, File snapshot, byte[] recovery) throws Exception {'
    new_signature = '    private static void importSnapshotWithProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {'
    s = replace_once(s, old_signature, new_signature, 'import verified zip signature')

    old_import_open = r'''        try (InputStream decrypted = openDsl5ProgressStream(snapshot, recovery,
                     (done, all) -> setImportRangeProgress(activity, progress,
                             DATA_PROGRESS_START, DATA_PROGRESS_END,
                             done, all, "Importazione dati del Dossier..."));
             ZipInputStream zip = new ZipInputStream(decrypted)) {
'''
    new_import_open = r'''        try (InputStream verifiedInput = new CountingInputStream(new FileInputStream(verifiedZip), Math.max(1L, verifiedZip.length()),
                     (done, all) -> setImportRangeProgress(activity, progress,
                             DATA_PROGRESS_START, DATA_PROGRESS_END,
                             done, all, "Importazione dati del Dossier..."));
             ZipInputStream zip = new ZipInputStream(verifiedInput)) {
'''
    s = replace_once(s, old_import_open, new_import_open, 'single decrypt import stream')

    old_worker = '''        EXECUTOR.execute(() -> {\n            File partial = null;\n            try {\n'''
    new_worker = '''        EXECUTOR.execute(() -> {\n            File partial = null;\n            File verifiedZip = null;\n            try {\n'''
    s = replace_once(s, old_worker, new_worker, 'verified zip worker state')

    old_flow = r'''                setImportProgress(activity, progress, INTEGRITY_PROGRESS_START, "Verifica integrità del Dossier...");
                byte[] recovery = R12Crypto.unb64Url(cloud.getString("recoveryKey"));
                verifySnapshotIntegrityProgress(activity, progress, partialRef, recovery);

                populateExistingConnectionConfig(activity, prefs, payload, cfg, choice, account);

                setImportProgress(activity, progress, DATA_PROGRESS_START, "Importazione dati del Dossier...");
                importSnapshotWithProgress(activity, progress, prefs, cfg, partialRef, recovery);

                finalizeExistingConnectionProgress(activity, progress, prefs, payload, cfg, choice, readySnap, account, partialRef);
'''
    new_flow = r'''                setImportProgress(activity, progress, INTEGRITY_PROGRESS_START, "Verifica integrità del Dossier...\nIn questa fase possono essere necessari diversi minuti.");
                byte[] recovery = R12Crypto.unb64Url(cloud.getString("recoveryKey"));
                verifiedZip = prepareVerifiedSnapshotProgress(activity, progress, partialRef, recovery);

                populateExistingConnectionConfig(activity, prefs, payload, cfg, choice, account);

                setImportProgress(activity, progress, DATA_PROGRESS_START, "Importazione dati del Dossier...");
                importSnapshotWithProgress(activity, progress, prefs, cfg, verifiedZip);

                finalizeExistingConnectionProgress(activity, progress, prefs, payload, cfg, choice, readySnap, account, partialRef);
'''
    s = replace_once(s, old_flow, new_flow, 'single pass integrity import flow')

    finally_marker = '''            } finally {\n                if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();\n'''
    finally_new = '''            } finally {\n                if (verifiedZip != null && verifiedZip.exists()) verifiedZip.delete();\n                if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();\n'''
    s = replace_once(s, finally_marker, finally_new, 'verified temp cleanup')

    CLOUD.write_text(s, encoding='utf-8')


def patch_version():
    m = MAIN.read_text(encoding='utf-8')
    m = m.replace('Android R20 TEST', 'Android R21 TEST')
    m = m.replace('Aiuto R20', 'Aiuto R21')
    m = m.replace('R20: struttura presente', 'R21: struttura presente')
    m = m.replace('R20 mantiene lo stesso pacchetto Android', 'R21 mantiene lo stesso pacchetto Android')
    m = m.replace('Installala sopra la R19', 'Installala sopra la R20')
    MAIN.write_text(m, encoding='utf-8')

    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 20', 'versionCode 21', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r20-test'", "versionName '1.0.0-android-r21-test'", 'versionName')
    GRADLE.write_text(g, encoding='utf-8')


patch_cloud()
patch_version()
print('R21 fast single-pass integrity/resume patch applied')
