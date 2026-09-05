from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'
EXACT = BASE / 'R27ExactWindows.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R29 patch failed: missing {label}')

# ---------------------------------------------------------------------------
# Exact Windows importer: progress is tied to actual imported units.
# ---------------------------------------------------------------------------
e = EXACT.read_text(encoding='utf-8')
require(e, 'final class R27ExactWindows {\n', 'R27ExactWindows class')
e = e.replace(
    'final class R27ExactWindows {\n',
    '''final class R27ExactWindows {\n    interface ProgressCallback {\n        void onProgress(int done, int total, String stage);\n    }\n\n''',
    1
)

old_sig = '''    static void importSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {\n        if (context == null || prefs == null || verifiedZip == null || !verifiedZip.isFile()) throw new Exception("Snapshot Windows non disponibile");'''
new_sig = '''    static void importSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {\n        importSnapshot(context, prefs, cfg, verifiedZip, null);\n    }\n\n    static void importSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, File verifiedZip, ProgressCallback progress) throws Exception {\n        notifyProgress(progress, 0, 1, "Lettura struttura del Dossier Windows");\n        if (context == null || prefs == null || verifiedZip == null || !verifiedZip.isFile()) throw new Exception("Snapshot Windows non disponibile");'''
require(e, old_sig, 'importSnapshot signature')
e = e.replace(old_sig, new_sig, 1)

marker = '''            if (importedProfiles.length() == 0) throw new Exception("Nessun profilo autorizzato trovato nel backup Windows");\n\n            String active = chooseActiveProfile(settingsRows, windowsUserId, linked, importedProfiles);'''
progress_setup = '''            if (importedProfiles.length() == 0) throw new Exception("Nessun profilo autorizzato trovato nel backup Windows");\n\n            int totalWork = 1;\n            for (int p = 0; p < importedProfiles.length(); p++) {\n                JSONObject profileForWork = importedProfiles.optJSONObject(p);\n                if (profileForWork == null) continue;\n                String folderForWork = folderByProfile.get(profileForWork.optString("id", ""));\n                if (folderForWork == null) continue;\n                totalWork += 9; // doctors, therapies, exemptions, diagnoses, measurements, weight, versions, agenda, suggestions\n                totalWork += readArray(zip, entries.get(folderForWork + "indice_documenti.json")).length();\n                String cardPrefixForWork = folderForWork + "tessera_sanitaria/";\n                for (String entryName : entries.keySet()) if (entryName.startsWith(cardPrefixForWork)) totalWork++;\n            }\n            int workDone = 1;\n            notifyProgress(progress, workDone, totalWork, "Profili, utenti e preferenze Windows");\n\n            String active = chooseActiveProfile(settingsRows, windowsUserId, linked, importedProfiles);'''
require(e, marker, 'progress setup marker')
e = e.replace(marker, progress_setup, 1)

old_arrays = '''                putArray(editor, profileId, "doctors", readArray(zip, entries.get(folder + "medici.json")));\n                putArray(editor, profileId, "therapies", readArray(zip, entries.get(folder + "terapie.json")));\n                putArray(editor, profileId, "exemptions", readArray(zip, entries.get(folder + "esenzioni.json")));\n                putArray(editor, profileId, "diagnoses", readArray(zip, entries.get(folder + "diagnosi.json")));\n                putArray(editor, profileId, "measurements", readArray(zip, entries.get(folder + "misurazioni.json")));\n                putArray(editor, profileId, "weightJourneys", readArray(zip, entries.get(folder + "percorsi_peso.json")));\n                putArray(editor, profileId, "documentVersions", readArray(zip, entries.get(folder + "versioni_documenti.json")));\n                putArray(editor, profileId, "calendarEvents", readArray(zip, entries.get(folder + "agenda.json")));\n                putArray(editor, profileId, "calendarSuggestions", readArray(zip, entries.get(folder + "richiami_calendario.json")));'''
new_arrays = '''                putArray(editor, profileId, "doctors", readArray(zip, entries.get(folder + "medici.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Medici e specialisti");\n                putArray(editor, profileId, "therapies", readArray(zip, entries.get(folder + "terapie.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Terapie");\n                putArray(editor, profileId, "exemptions", readArray(zip, entries.get(folder + "esenzioni.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Esenzioni");\n                putArray(editor, profileId, "diagnoses", readArray(zip, entries.get(folder + "diagnosi.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Diagnosi");\n                putArray(editor, profileId, "measurements", readArray(zip, entries.get(folder + "misurazioni.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Monitoraggio e misurazioni");\n                putArray(editor, profileId, "weightJourneys", readArray(zip, entries.get(folder + "percorsi_peso.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Percorso peso e grafici");\n                putArray(editor, profileId, "documentVersions", readArray(zip, entries.get(folder + "versioni_documenti.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Storico documenti");\n                putArray(editor, profileId, "calendarEvents", readArray(zip, entries.get(folder + "agenda.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Agenda ed eventi");\n                putArray(editor, profileId, "calendarSuggestions", readArray(zip, entries.get(folder + "richiami_calendario.json")));\n                notifyProgress(progress, ++workDone, totalWork, "Richiami e scadenze");'''
require(e, old_arrays, 'profile arrays')
e = e.replace(old_arrays, new_arrays, 1)

old_doc_tail = '''                    localDocs.put(copy);\n                }\n                putArray(editor, profileId, "documents", localDocs);'''
new_doc_tail = '''                    localDocs.put(copy);\n                    String progressName = source.optString("title", source.optString("originalName", "Documento"));\n                    notifyProgress(progress, ++workDone, totalWork, "Documento: " + progressName);\n                }\n                putArray(editor, profileId, "documents", localDocs);'''
require(e, old_doc_tail, 'document progress marker')
e = e.replace(old_doc_tail, new_doc_tail, 1)

old_card_tail = '''                    else if (frontPath.isEmpty()) frontPath = target.getAbsolutePath();\n                    else if (backPath.isEmpty()) backPath = target.getAbsolutePath();\n                }\n                editor.putString(key(profileId, "healthFront"), frontPath);'''
new_card_tail = '''                    else if (frontPath.isEmpty()) frontPath = target.getAbsolutePath();\n                    else if (backPath.isEmpty()) backPath = target.getAbsolutePath();\n                    notifyProgress(progress, ++workDone, totalWork, back ? "Tessera Sanitaria · retro" : "Tessera Sanitaria · fronte");\n                }\n                editor.putString(key(profileId, "healthFront"), frontPath);'''
require(e, old_card_tail, 'health card progress marker')
e = e.replace(old_card_tail, new_card_tail, 1)

old_apply = '''            editor.apply();\n        }\n    }\n\n    static JSONArray profiles'''
new_apply = '''            editor.apply();\n            notifyProgress(progress, totalWork, totalWork, "Dati Windows importati");\n        }\n    }\n\n    private static void notifyProgress(ProgressCallback callback, int done, int total, String stage) {\n        if (callback == null) return;\n        int safeTotal = Math.max(1, total);\n        int safeDone = Math.max(0, Math.min(done, safeTotal));\n        callback.onProgress(safeDone, safeTotal, stage == null ? "" : stage);\n    }\n\n    static JSONArray profiles'''
require(e, old_apply, 'import completion marker')
e = e.replace(old_apply, new_apply, 1)
EXACT.write_text(e, encoding='utf-8')

# ---------------------------------------------------------------------------
# Cloud bootstrap: callbacks + Throwable guard + non-sensitive failure state.
# ---------------------------------------------------------------------------
c = CLOUD.read_text(encoding='utf-8')
configured_marker = '    public static boolean configured(SharedPreferences prefs) {\n'
require(c, configured_marker, 'configured marker')
cloud_methods = r'''    private static final String R29_IMPORT_ERROR_KEY = "r29_import_error";

    public static boolean bootstrapR29ExactIfNeeded(
            Activity activity,
            SharedPreferences prefs,
            R22StreamingDsl5.ProgressCallback decryptProgress,
            R27ExactWindows.ProgressCallback importProgress) {
        if (activity == null || prefs == null) return false;
        if (R27ExactWindows.profiles(prefs).length() > 0) return true;
        File verified = null;
        try {
            prefs.edit().remove(R29_IMPORT_ERROR_KEY).apply();
            JSONObject cfg = loadConfig(prefs);
            if (cfg.optString("archiveId", "").isEmpty()) return false;
            File snapshot = currentSnapshot(activity, cfg);
            if (snapshot == null || !snapshot.isFile()) return false;
            byte[] recovery = recoveryKey(activity, cfg);
            verified = File.createTempFile("r29_upgrade_", ".zip", activity.getCacheDir());
            R22StreamingDsl5.decryptVerified(snapshot, verified, recovery, decryptProgress);
            R27ExactWindows.importSnapshot(activity, prefs, cfg, verified, importProgress);
            return R27ExactWindows.profiles(prefs).length() > 0;
        } catch (Throwable failure) {
            String kind = failure instanceof OutOfMemoryError
                    ? "Memoria insufficiente durante la ricostruzione del Dossier"
                    : "Importazione dei dati sincronizzati non completata";
            try { prefs.edit().putString(R29_IMPORT_ERROR_KEY, kind).apply(); } catch (Throwable ignored) {}
            return false;
        } finally {
            if (verified != null && verified.exists()) verified.delete();
        }
    }

    public static String r29LastImportError(SharedPreferences prefs) {
        if (prefs == null) return "Importazione non completata";
        return prefs.getString(R29_IMPORT_ERROR_KEY, "Importazione non completata");
    }

'''
c = c.replace(configured_marker, cloud_methods + configured_marker, 1)
CLOUD.write_text(c, encoding='utf-8')

# ---------------------------------------------------------------------------
# Main UI: real determinate progress and crash-safe post-import opening.
# ---------------------------------------------------------------------------
s = MAIN.read_text(encoding='utf-8')
require(s, 'import android.widget.LinearLayout;\n', 'LinearLayout import')
s = s.replace('import android.widget.LinearLayout;\n', 'import android.widget.LinearLayout;\nimport android.widget.ProgressBar;\n', 1)

field_marker = '    private long lastPanoramicaBackMs = 0L;\n'
require(s, field_marker, 'field marker')
s = s.replace(field_marker, field_marker + '''    private ProgressBar r29ProgressBar;\n    private TextView r29ProgressPercent;\n    private TextView r29ProgressStage;\n''', 1)

start = s.find('    private void openAuthenticatedDossierR28(Bundle state) {')
end = s.find('    private void showMainUi(Bundle state) {', start)
if start < 0 or end <= start:
    raise SystemExit('R29 patch failed: R28 authenticated block missing')

methods = r'''    private void openAuthenticatedDossierR28(Bundle state) {
        sessionAuthenticated = true;

        if (R27ExactWindows.profiles(prefs).length() > 0 || !R12CloudManager.configured(prefs)) {
            safeOpenMainUiR29(state);
            return;
        }

        showR29WindowsMigrationScreen();
        dataExecutor.execute(() -> {
            boolean imported;
            try {
                imported = R12CloudManager.bootstrapR29ExactIfNeeded(
                        this,
                        prefs,
                        (done, total) -> updateR29Progress(scaleR29(done, total, 0, 55), "Verifica e decifratura del Dossier sincronizzato"),
                        (done, total, stage) -> updateR29Progress(scaleR29(done, total, 55, 44), stage));
            } catch (Throwable failure) {
                imported = false;
            }
            final boolean completed = imported;
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed() || !sessionAuthenticated) return;
                if (!completed) {
                    showR29WindowsMigrationFailure(state, R12CloudManager.r29LastImportError(prefs));
                    return;
                }
                updateR29Progress(100, "Importazione completata");
                safeOpenMainUiR29(state);
            });
        });
    }

    private int scaleR29(long done, long total, int start, int span) {
        if (total <= 0L) return start;
        long bounded = Math.max(0L, Math.min(done, total));
        return start + (int) ((bounded * span) / total);
    }

    private void updateR29Progress(int percent, String stage) {
        final int value = Math.max(0, Math.min(100, percent));
        runOnUiThread(() -> {
            if (r29ProgressBar != null) r29ProgressBar.setProgress(value);
            if (r29ProgressPercent != null) r29ProgressPercent.setText(value + "%");
            if (r29ProgressStage != null && stage != null && !stage.trim().isEmpty()) r29ProgressStage.setText(stage);
        });
    }

    private void showR29WindowsMigrationScreen() {
        LinearLayout page = securePage(
                "Sincronizzazione del Dossier",
                "Sto ricostruendo sul telefono i dati e le impostazioni già presenti nel Dossier Windows.");
        LinearLayout card = card();
        card.addView(text("Importazione completa in corso", 15, TEXT, true));

        r29ProgressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        r29ProgressBar.setIndeterminate(false);
        r29ProgressBar.setMax(100);
        r29ProgressBar.setProgress(0);
        card.addView(r29ProgressBar, matchWrapTop(14));

        r29ProgressPercent = text("0%", 14, TEXT, true);
        card.addView(r29ProgressPercent, matchWrapTop(8));
        r29ProgressStage = text("Preparazione dei dati sincronizzati", 13, MUTED, false);
        card.addView(r29ProgressStage, matchWrapTop(4));
        card.addView(text("La percentuale segue i byte realmente verificati e gli elementi realmente importati.", 12, MUTED, false), matchWrapTop(8));
        page.addView(card, matchWrapBottom(14));
        setContentView(wrapSecurePage(page));
    }

    private void showR29WindowsMigrationFailure(Bundle state, String reason) {
        r29ProgressBar = null;
        r29ProgressPercent = null;
        r29ProgressStage = null;
        LinearLayout page = securePage(
                "Sincronizzazione non completata",
                "L'app resta aperta e il Dossier non viene mostrato con dati parziali.");
        LinearLayout card = card();
        String safeReason = reason == null || reason.trim().isEmpty() ? "Importazione non completata" : reason;
        card.addView(text(safeReason, 14, TEXT, true));
        Button retry = button("Riprova sincronizzazione");
        retry.setOnClickListener(v -> openAuthenticatedDossierR28(state));
        card.addView(retry, matchWrapTop(12));
        Button lock = button("Blocca e torna al login");
        lock.setOnClickListener(v -> showStartupGate(null));
        card.addView(lock, matchWrapTop(8));
        page.addView(card, matchWrapBottom(14));
        setContentView(wrapSecurePage(page));
    }

    private void safeOpenMainUiR29(Bundle state) {
        try {
            loadR26ImportedUiSettings();
            getWindow().setStatusBarColor(GREEN_DARK);
            showMainUi(state);
            r29ProgressBar = null;
            r29ProgressPercent = null;
            r29ProgressStage = null;
        } catch (Throwable failure) {
            showR29UiFailure(state);
        }
    }

    private void showR29UiFailure(Bundle state) {
        r29ProgressBar = null;
        r29ProgressPercent = null;
        r29ProgressStage = null;
        LinearLayout page = securePage(
                "Dati sincronizzati, apertura non completata",
                "La sincronizzazione è stata conservata. L'app resta aperta invece di chiudersi.");
        LinearLayout card = card();
        card.addView(text("Si è verificato un errore durante la costruzione dell'interfaccia del Dossier.", 14, TEXT, true));
        Button retry = button("Riprova apertura Dossier");
        retry.setOnClickListener(v -> safeOpenMainUiR29(state));
        card.addView(retry, matchWrapTop(12));
        Button lock = button("Blocca e torna al login");
        lock.setOnClickListener(v -> showStartupGate(null));
        card.addView(lock, matchWrapTop(8));
        page.addView(card, matchWrapBottom(14));
        setContentView(wrapSecurePage(page));
    }

'''
s = s[:start] + methods + s[end:]

s = s.replace('Android R28 TEST COMPLETO', 'Android R29 TEST COMPLETO')
s = s.replace('Aiuto R28', 'Aiuto R29')
s = s.replace('R28: sezione completa collegata al backup Windows', 'R29: sezione completa collegata al backup Windows')
s = s.replace('R28 mantiene lo stesso pacchetto Android', 'R29 mantiene lo stesso pacchetto Android')
s = s.replace('Installala sopra la R27', 'Installala sopra la R28')
MAIN.write_text(s, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
require(g, 'versionCode 28', 'versionCode 28')
require(g, "versionName '1.0.0-android-r28-startup-async-test'", 'R28 versionName')
g = g.replace('versionCode 28', 'versionCode 29', 1)
g = g.replace("versionName '1.0.0-android-r28-startup-async-test'", "versionName '1.0.0-android-r29-progress-crashguard-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R29 real progress and crash guard patch applied')
