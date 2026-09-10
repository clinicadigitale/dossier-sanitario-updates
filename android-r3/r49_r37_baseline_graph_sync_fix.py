from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit('R49 missing ' + label)


def replace_block(text, signature, replacement, label):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('R49 missing ' + label)
    brace = text.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit('R49 unclosed ' + label)
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# ---------------------------------------------------------------------------
# GRAPH: R37 renderer/data path is frozen. Change ONLY its vertical height.
# No series parsing, values, axes, labels, dates, selectors or profile logic.
# ---------------------------------------------------------------------------
chart = CHART.read_text(encoding='utf-8')
require(chart, 'setMinimumHeight(dp(220));', 'R37 chart height')
chart = chart.replace('setMinimumHeight(dp(220));', 'setMinimumHeight(dp(320));', 1)
CHART.write_text(chart, encoding='utf-8')

# ---------------------------------------------------------------------------
# SYNC: keep R37 data/import path, but use bounded authenticated streaming
# decrypt, a real byte-progress snapshot download, Throwable containment, and
# robust final commit that falls back to verified copy if rename fails.
# ---------------------------------------------------------------------------
(BASE / 'R49SnapshotDownload.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class R49SnapshotDownload {
    interface Progress { void onPercent(int percent); }
    private static final Pattern PERCENT = Pattern.compile("(?:^|\\s)(\\d{1,3})%(?:,|\\s|$)");
    private R49SnapshotDownload() {}

    static void download(Context context, String remote, File local, Progress progress) throws Exception {
        File parent = local.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Impossibile preparare la cartella locale.");
        if (local.exists() && !local.delete()) throw new Exception("Impossibile preparare la copia temporanea.");
        File exe = new File(context.getApplicationInfo().nativeLibraryDir, "librclone.so");
        if (!exe.isFile()) throw new Exception("Connettore cloud Android non disponibile.");

        List<String> cmd = new ArrayList<>();
        cmd.add(exe.getAbsolutePath());
        cmd.add("copyto"); cmd.add(remote); cmd.add(local.getAbsolutePath());
        cmd.add("--config"); cmd.add(R12Rclone.configFile(context).getAbsolutePath());
        cmd.add("--transfers"); cmd.add("1");
        cmd.add("--checkers"); cmd.add("1");
        cmd.add("--buffer-size"); cmd.add("1M");
        cmd.add("--multi-thread-streams"); cmd.add("1");
        cmd.add("--retries"); cmd.add("3");
        cmd.add("--low-level-retries"); cmd.add("5");
        cmd.add("--contimeout"); cmd.add("15s");
        cmd.add("--timeout"); cmd.add("90s");
        cmd.add("--stats"); cmd.add("1s");
        cmd.add("--stats-one-line");
        cmd.add("--log-level"); cmd.add("NOTICE");

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        pb.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath());
        pb.environment().put("HOME", context.getFilesDir().getAbsolutePath());
        Process process = pb.start();
        ArrayDeque<String> tail = new ArrayDeque<>();
        int last = -1;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (tail.size() >= 24) tail.removeFirst();
                tail.addLast(line);
                Matcher m = PERCENT.matcher(line);
                int seen = -1;
                while (m.find()) seen = Integer.parseInt(m.group(1));
                if (seen >= 0) {
                    seen = Math.max(0, Math.min(100, seen));
                    if (seen > last) {
                        last = seen;
                        if (progress != null) progress.onPercent(seen);
                    }
                }
            }
        }
        if (!process.waitFor(2, TimeUnit.MINUTES)) {
            process.destroyForcibly();
            throw new Exception("Download della copia Windows fermo oltre il tempo massimo.");
        }
        if (process.exitValue() != 0) {
            StringBuilder b = new StringBuilder();
            for (String line : tail) b.append(line).append('\n');
            String msg = b.toString().trim();
            if (msg.length() > 800) msg = msg.substring(msg.length() - 800);
            throw new Exception(msg.isEmpty() ? "Download della copia Windows non riuscito." : msg);
        }
        if (!local.isFile() || local.length() <= 0L) throw new Exception("Download della copia Windows non completato.");
        if (progress != null) progress.onPercent(100);
    }
}
''', encoding='utf-8')

cloud = CLOUD.read_text(encoding='utf-8')

# Add determinate sync progress callback and specialized interactive runner.
marker = '    private static volatile boolean syncing = false;\n'
require(cloud, marker, 'syncing marker')
cloud = cloud.replace(marker, marker + '    private interface R49Progress { void update(int percent, String message); }\n', 1)

sync_now = r'''    public static String syncNow(Context context, SharedPreferences prefs, boolean background) throws Exception {
        return r49SyncNow(context, prefs, background, null);
    }

    private static String r49SyncNow(Context context, SharedPreferences prefs, boolean background, R49Progress progress) throws Exception {
        synchronized (R12CloudManager.class) { if (syncing) return "Sincronizzazione già in corso"; syncing = true; }
        try {
            if (progress != null) progress.update(2, "Controllo configurazione Dossier...");
            JSONObject cfg = loadConfig(prefs);
            if (cfg.optString("archiveId", "").isEmpty()) return "Dossier cloud non configurato";
            if (archiveRoot(context, cfg, false) == null) throw new Exception("Archivio Dossier non disponibile. Reinserisci la memoria selezionata.");

            if (prefs.getString(PENDING_COMPLETION_KEY, "").length() > 2) {
                if (progress != null) progress.update(5, "Verifica associazione familiare...");
                try { publishPendingCompletion(context, prefs, cfg); } catch (Exception ignored) {}
            }

            boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
            int snapshotUpdated = snapshotSafe ? r49RefreshLatestCommittedSnapshot(context, prefs, cfg, progress) : 0;

            if (progress != null) progress.update(82, "Ricezione modifiche cloud...");
            int received = pullRemoteChanges(context, prefs, cfg, false);
            if (progress != null) progress.update(90, "Invio modifiche locali...");
            int sent = uploadPendingChanges(context, prefs, cfg);
            if (progress != null) progress.update(96, "Verifica finale sincronizzazione...");
            checkCompletionConsumed(context, prefs, cfg);
            cfg.put("lastSyncAt", Instant.now().toString());
            saveConfig(prefs, cfg);
            if (progress != null) progress.update(100, "Sincronizzazione completata");
            String suffix = snapshotUpdated > 0 ? " · archivio Windows aggiornato" : "";
            return sent + " inviate · " + received + " ricevute" + suffix;
        } finally {
            synchronized (R12CloudManager.class) { syncing = false; }
        }
    }'''
cloud = replace_block(cloud, '    public static String syncNow(Context context, SharedPreferences prefs, boolean background) throws Exception {', sync_now, 'syncNow')

refresh = r'''    private static int r49RefreshLatestCommittedSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, R49Progress progress) throws Exception {
        if (progress != null) progress.update(7, "Ricerca della copia Windows più recente...");
        SnapshotInfo latest = latestSnapshot(context, cfg);
        if (latest == null || latest.name == null || latest.name.trim().isEmpty()) return 0;

        String reconciled = cfg.optString("r36ReconciledSnapshotName", "");
        if (!reconciled.isEmpty() && latest.name.equals(reconciled)) {
            if (progress != null) progress.update(80, "Copia Windows già aggiornata");
            return 0;
        }

        File root = archiveRoot(context, cfg, false);
        if (root == null) throw new Exception("Archivio Dossier non disponibile.");
        long required = requiredBytes(Math.max(0L, latest.size));
        if (latest.size > 0 && freeBytes(root) < required) throw new Exception("Spazio insufficiente per aggiornare il Dossier: servono " + formatBytes(required) + ".");

        File encryptedPart = new File(root, "r49_snapshot_refresh.dsl5.part");
        File plainZip = new File(context.getCacheDir(), "r49_snapshot_refresh.zip");
        if (encryptedPart.exists()) encryptedPart.delete();
        if (plainZip.exists()) plainZip.delete();
        try {
            if (progress != null) progress.update(10, "Download della copia Windows...");
            R49SnapshotDownload.download(context, cloudRoot(cfg) + "/snapshots/" + latest.name, encryptedPart, p -> {
                if (progress != null) progress.update(10 + (int)Math.floor(35.0 * p / 100.0), "Download copia Windows " + p + "%");
            });
            if (latest.size > 0 && encryptedPart.length() != latest.size) throw new Exception("La copia cloud più recente non ha la dimensione attesa.");

            byte[] recovery = recoveryKey(context, cfg);
            if (progress != null) progress.update(46, "Decifratura e verifica copia Windows...");
            R22StreamingDsl5.decryptVerified(encryptedPart, plainZip, recovery, (done,total) -> {
                if (progress != null && total > 0L) {
                    int p = (int)Math.min(100L, Math.max(0L, (done * 100L) / total));
                    progress.update(46 + (int)Math.floor(22.0 * p / 100.0), "Decifratura e verifica " + p + "%");
                }
            });
            if (!plainZip.isFile() || plainZip.length() == 0L) throw new Exception("Snapshot Windows decifrato non disponibile.");

            if (progress != null) progress.update(69, "Importazione dati Windows...");
            R30BoundedWindows.importSnapshot(context, prefs, cfg, plainZip, null);
            if (progress != null) progress.update(77, "Consolidamento copia locale...");
            r49CommitSnapshot(encryptedPart, new File(root, "current_snapshot.dsl5"));

            cfg.put("lastSnapshotName", latest.name);
            cfg.put("r36ReconciledSnapshotName", latest.name);
            cfg.put("r36SnapshotReconciledAt", Instant.now().toString());
            saveConfig(prefs, cfg);
            if (progress != null) progress.update(80, "Copia Windows aggiornata");
            return 1;
        } finally {
            if (plainZip.exists()) plainZip.delete();
            if (encryptedPart.exists()) encryptedPart.delete();
        }
    }

    private static void r49CommitSnapshot(File partial, File target) throws Exception {
        if (partial == null || !partial.isFile() || partial.length() <= 0L) throw new Exception("Copia temporanea non disponibile.");
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Cartella Dossier non disponibile.");
        File staged = new File(parent, target.getName() + ".new");
        File old = new File(parent, target.getName() + ".old");
        if (staged.exists()) staged.delete();
        if (old.exists()) old.delete();

        r49CopyFileVerified(partial, staged);
        boolean hadTarget = target.exists();
        if (hadTarget && !target.renameTo(old)) {
            staged.delete();
            throw new Exception("Impossibile proteggere la copia precedente.");
        }
        boolean committed = staged.renameTo(target);
        if (!committed) {
            try {
                r49CopyFileVerified(staged, target);
                committed = target.isFile() && target.length() == staged.length();
            } catch (Exception copyFailure) {
                committed = false;
            }
        }
        if (!committed) {
            if (target.exists()) target.delete();
            if (hadTarget && old.exists()) old.renameTo(target);
            staged.delete();
            throw new Exception("Impossibile rendere definitiva la nuova copia.");
        }
        staged.delete();
        if (old.exists()) old.delete();
        partial.delete();
    }

    private static void r49CopyFileVerified(File source, File destination) throws Exception {
        try (FileInputStream in = new FileInputStream(source); FileOutputStream out = new FileOutputStream(destination, false)) {
            byte[] buffer = new byte[256 * 1024];
            long copied = 0L;
            int n;
            while ((n = in.read(buffer)) >= 0) {
                if (n == 0) continue;
                out.write(buffer, 0, n);
                copied += n;
            }
            out.flush();
            out.getFD().sync();
            if (copied != source.length() || destination.length() != source.length()) throw new Exception("Verifica della copia locale non riuscita.");
        }
    }'''
# Replace the R36 snapshot helper entirely.
cloud = replace_block(cloud, '    private static int r36RefreshLatestCommittedSnapshot(Context context, SharedPreferences prefs, JSONObject cfg) throws Exception {', refresh, 'R36 snapshot refresh')

interactive = r'''    private static void syncInteractive(Activity activity, SharedPreferences prefs) {
        ProgressDialog dialog = new ProgressDialog(activity);
        dialog.setTitle("Sincronizzazione Dossier");
        dialog.setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);
        dialog.setIndeterminate(false);
        dialog.setMax(100);
        dialog.setProgress(1);
        dialog.setMessage("Avvio sincronizzazione...");
        dialog.setCancelable(false);
        dialog.show();
        EXECUTOR.execute(() -> {
            try {
                String result = r49SyncNow(activity, prefs, false, (percent, message) -> activity.runOnUiThread(() -> {
                    if (!dialog.isShowing()) return;
                    dialog.setProgress(Math.max(dialog.getProgress(), Math.max(0, Math.min(100, percent))));
                    dialog.setMessage(message);
                }));
                activity.runOnUiThread(() -> {
                    if (dialog.isShowing()) dialog.dismiss();
                    Toast.makeText(activity, "Sincronizzazione completata · " + result, Toast.LENGTH_LONG).show();
                });
            } catch (Throwable failure) {
                final String msg = failure.getMessage() == null || failure.getMessage().trim().isEmpty() ? failure.getClass().getSimpleName() : failure.getMessage();
                activity.runOnUiThread(() -> {
                    if (dialog.isShowing()) dialog.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Sincronizzazione non completata").setMessage(msg).setPositiveButton("Chiudi", null).show();
                });
            }
        });
    }'''
cloud = replace_block(cloud, '    private static void syncInteractive(Activity activity, SharedPreferences prefs) {', interactive, 'interactive sync')
CLOUD.write_text(cloud, encoding='utf-8')

# Version only, necessary to install over R48.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 49', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', 'versionName "1.0.0-android-r49-r37-baseline-graph-sync-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

# Regression tests. These intentionally verify that R37 graph data logic stays untouched.
TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R49R37BaselineGraphSyncTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R49R37BaselineGraphSyncTest {
    private String read(String p) throws Exception { return new String(Files.readAllBytes(Paths.get(p)), StandardCharsets.UTF_8); }

    @Test public void graphIsExactlyR37LogicExceptHeight() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(c.contains("setMinimumHeight(dp(320))"));
        assertTrue(c.contains("R26SnapshotBridge.numericValue(o, preferredKeys)"));
        assertTrue(c.contains("left + (right - left) * i / (values.size() - 1f)"));
        assertFalse(c.contains("windowsYearTicks"));
        assertFalse(c.contains("R40ClinicalSeries"));
    }

    @Test public void r37ClinicalSeriesPathIsPreserved() throws Exception {
        String m = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(m.contains("R37ClinicalSeries.availableLabParameters"));
        assertTrue(m.contains("R37ClinicalSeries.labSeries"));
        assertTrue(m.contains("R37ClinicalSeries.glycemiaFromReports"));
    }

    @Test public void syncUsesBoundedDecryptAndRobustCommit() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(c.contains("R22StreamingDsl5.decryptVerified"));
        assertTrue(c.contains("r49CommitSnapshot"));
        assertTrue(c.contains("r49CopyFileVerified"));
        assertFalse(c.contains("R12Crypto.openDsl5File(encryptedPart, recovery)"));
    }

    @Test public void syncContainsCrashAndShowsRealProgress() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String d = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R49SnapshotDownload.java");
        assertTrue(c.contains("catch (Throwable failure)"));
        assertTrue(c.contains("ProgressDialog.STYLE_HORIZONTAL"));
        assertTrue(c.contains("Decifratura e verifica"));
        assertTrue(d.contains("--stats"));
        assertTrue(d.contains("--buffer-size"));
        assertTrue(d.contains("1M"));
    }
}
''', encoding='utf-8')

print('R49 R37-baseline graph-height and sync stability patch applied')
