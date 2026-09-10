from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CHART = BASE / 'R26ChartView.java'
SERIES = BASE / 'R40ClinicalSeries.java'
CLOUD = BASE / 'R12CloudManager.java'
CRYPTO = BASE / 'R12Crypto.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R45 failed: missing {label or signature}')
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
        raise SystemExit(f'R45 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# ---------------------------------------------------------------------------
# 1. Graphs: keep time-proportional point positions but make the X axis a true
#    chronological YEAR axis, not a list of report dates. Add point inspection.
# ---------------------------------------------------------------------------
chart = CHART.read_text(encoding='utf-8')
if 'private final List<JSONObject> pointRecords' not in chart:
    marker = '    private final List<String> dates = new ArrayList<>();'
    if marker not in chart:
        raise SystemExit('R45 failed: chart dates list missing')
    chart = chart.replace(marker, marker + '\n    private final List<JSONObject> pointRecords = new ArrayList<>();', 1)

old_ingest = '''                    values.add(v);\n                    dates.add(o == null ? "" : o.optString("date", o.optString("clinicalDate", o.optString("createdAt", ""))));'''
new_ingest = '''                    values.add(v);\n                    dates.add(o == null ? "" : o.optString("date", o.optString("clinicalDate", o.optString("createdAt", ""))));\n                    pointRecords.add(o == null ? new JSONObject() : o);'''
if old_ingest not in chart:
    raise SystemExit('R45 failed: chart ingest block missing')
chart = chart.replace(old_ingest, new_ingest, 1)

axis = r'''    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {
        if (tMin == Long.MAX_VALUE || tMax <= 0L || tMax < tMin) return;
        int[] years = yearTicks(tMin, tMax);
        if (years.length == 0) return;
        Paint.Align previous = label.getTextAlign();
        label.setTextAlign(Paint.Align.RIGHT);
        for (int year : years) {
            long tickTime = yearStartMillis(year);
            if (year == years[0] && tickTime < tMin) tickTime = tMin;
            if (tickTime > tMax) tickTime = tMax;
            float x = pointXForTime(tickTime, tMin, tMax, left, right);
            canvas.drawLine(x, bottom, x, bottom + dp(5), grid);
            canvas.save();
            canvas.rotate(dateLabelRotationDegrees(), x, bottom + dp(20));
            canvas.drawText(String.valueOf(year), x, bottom + dp(20), label);
            canvas.restore();
        }
        label.setTextAlign(previous);
    }

    static int[] yearTicks(long minTime, long maxTime) {
        if (minTime <= 0L || maxTime <= 0L || maxTime < minTime) return new int[0];
        java.util.Calendar a = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"), Locale.ITALY);
        java.util.Calendar b = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"), Locale.ITALY);
        a.setTimeInMillis(minTime);
        b.setTimeInMillis(maxTime);
        int first = a.get(java.util.Calendar.YEAR);
        int last = b.get(java.util.Calendar.YEAR);
        int[] out = new int[Math.max(0, last - first + 1)];
        for (int i = 0; i < out.length; i++) out[i] = first + i;
        return out;
    }

    static long yearStartMillis(int year) {
        java.util.Calendar c = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"), Locale.ITALY);
        c.clear();
        c.set(java.util.Calendar.YEAR, year);
        c.set(java.util.Calendar.MONTH, java.util.Calendar.JANUARY);
        c.set(java.util.Calendar.DAY_OF_MONTH, 1);
        return c.getTimeInMillis();
    }'''
chart = replace_block(chart, '    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {', axis, 'year axis')

# Point tap: nearest visible point shows exact clinical date and report reference.
touch = r'''
    @Override public boolean onTouchEvent(android.view.MotionEvent event) {
        if (event == null) return false;
        if (event.getAction() != android.view.MotionEvent.ACTION_UP) return true;
        if (values.isEmpty()) return true;
        float left = dp(82), right = getWidth() - dp(18), top = dp(38);
        boolean hasReference = Double.isFinite(referenceLow) && Double.isFinite(referenceHigh);
        float bottom = getHeight() - dp(hasReference ? 132 : 108);
        if (right <= left || bottom <= top) return true;

        double[] bounds = scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh);
        double min = bounds[0], max = bounds[1];
        long[] times = dateTimes(dates);
        long tMin = Long.MAX_VALUE, tMax = Long.MIN_VALUE;
        for (long t : times) if (t > 0) { tMin = Math.min(tMin, t); tMax = Math.max(tMax, t); }
        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;

        int nearest = -1;
        float best = Float.MAX_VALUE;
        for (int i = 0; i < values.size(); i++) {
            float x = values.size() == 1 ? (left + right) / 2f :
                    (dated && i < times.length && times[i] > 0 ? pointXForTime(times[i], tMin, tMax, left, right) : pointXForIndex(i, values.size(), left, right));
            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);
            float dx = event.getX() - x, dy = event.getY() - y;
            float distance = (float) Math.sqrt(dx * dx + dy * dy);
            if (distance < best) { best = distance; nearest = i; }
        }
        if (nearest >= 0 && best <= dp(28)) {
            String date = nearest < dates.size() ? shortClinicalDate(dates.get(nearest)) : "";
            JSONObject row = nearest < pointRecords.size() ? pointRecords.get(nearest) : null;
            String ref = "";
            if (row != null) {
                ref = row.optString("sourceDocumentLabel", row.optString("originalName", row.optString("fileName", row.optString("sourceDocumentId", ""))));
            }
            if (ref == null || ref.trim().isEmpty()) ref = "Rilevazione";
            String message = (date == null || date.isEmpty() ? "Data non disponibile" : date) + " · " + ref;
            android.widget.Toast.makeText(getContext(), message, android.widget.Toast.LENGTH_LONG).show();
            return true;
        }
        return true;
    }
'''
marker = '\n    private String shortNumber(double v) {'
if marker not in chart:
    raise SystemExit('R45 failed: chart helper insertion marker missing')
chart = chart.replace(marker, touch + marker, 1)
CHART.write_text(chart, encoding='utf-8')

# Preserve the report identity in each laboratory graph point.
series = SERIES.read_text(encoding='utf-8')
old = '''                    row.put("date", doc.optString("clinicalDate", doc.optString("issueDate", doc.optString("createdAt", ""))));\n                    rows.add(row);'''
new = '''                    row.put("date", doc.optString("clinicalDate", doc.optString("issueDate", doc.optString("createdAt", ""))));\n                    String sourceId = doc.optString("id", doc.optString("documentId", ""));\n                    if (!sourceId.isEmpty()) row.put("sourceDocumentId", sourceId);\n                    String sourceLabel = doc.optString("title", doc.optString("name", doc.optString("originalName", doc.optString("fileName", "Referto di laboratorio"))));\n                    if (!sourceLabel.isEmpty()) row.put("sourceDocumentLabel", sourceLabel);\n                    rows.add(row);'''
if old not in series:
    raise SystemExit('R45 failed: lab report source insertion point missing')
series = series.replace(old, new, 1)
SERIES.write_text(series, encoding='utf-8')


# ---------------------------------------------------------------------------
# 2. Backup/sync progress: count real encrypted bytes during AES-GCM reading,
#    poll the real downloaded file size, and map bounded importer callbacks.
# ---------------------------------------------------------------------------
progress_math = BASE / 'R45ProgressMath.java'
progress_math.write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

final class R45ProgressMath {
    private R45ProgressMath() {}

    static int percent(long done, long total, int start, int end) {
        if (end <= start) return start;
        if (total <= 0L) return start;
        long safe = Math.max(0L, Math.min(done, total));
        double ratio = safe / (double) total;
        return Math.max(start, Math.min(end, start + (int) Math.floor((end - start) * ratio)));
    }

    static int importPercent(int done, int total) {
        return percent(done, total, 60, 86);
    }
}
''', encoding='utf-8')

crypto = CRYPTO.read_text(encoding='utf-8')
old_method = '''    public static InputStream openDsl5File(File file, byte[] keyRaw) throws Exception {\n        return openDsl5Stream(new FileInputStream(file), keyRaw);\n    }'''
new_method = r'''    public interface Dsl5ReadProgress {
        void onBytes(long read, long total);
    }

    private static final class ProgressInputStream extends java.io.FilterInputStream {
        private final long total;
        private final Dsl5ReadProgress progress;
        private long read;

        ProgressInputStream(InputStream source, long total, Dsl5ReadProgress progress) {
            super(source);
            this.total = Math.max(0L, total);
            this.progress = progress;
        }

        private void report(int n) {
            if (n <= 0) return;
            read += n;
            if (progress != null) progress.onBytes(read, total);
        }

        @Override public int read() throws java.io.IOException {
            int value = super.read();
            if (value >= 0) report(1);
            return value;
        }

        @Override public int read(byte[] b, int off, int len) throws java.io.IOException {
            int n = super.read(b, off, len);
            report(n);
            return n;
        }
    }

    public static InputStream openDsl5File(File file, byte[] keyRaw) throws Exception {
        return openDsl5File(file, keyRaw, null);
    }

    public static InputStream openDsl5File(File file, byte[] keyRaw, Dsl5ReadProgress progress) throws Exception {
        FileInputStream raw = new FileInputStream(file);
        try {
            return openDsl5Stream(new ProgressInputStream(raw, file.length(), progress), keyRaw);
        } catch (Exception failure) {
            try { raw.close(); } catch (Exception ignored) {}
            throw failure;
        }
    }'''
if old_method not in crypto:
    raise SystemExit('R45 failed: openDsl5File original method missing')
crypto = crypto.replace(old_method, new_method, 1)
CRYPTO.write_text(crypto, encoding='utf-8')

cloud = CLOUD.read_text(encoding='utf-8')

refresh45 = r'''    private static int r45RefreshLatestCommittedSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, R44Progress progress) throws Exception {
        if (progress != null) progress.update(8, "Verifica dell'archivio MEGA autorizzato...");
        verifyArchiveManifestR43(context, cfg);
        if (progress != null) progress.update(14, "Ricerca della copia Windows più recente...");
        SnapshotInfo latest = latestSnapshotR44(context, cfg);
        String reconciled = cfg.optString("r36ReconciledSnapshotName", "");
        if (!reconciled.isEmpty() && latest.name.equals(reconciled)) {
            if (progress != null) progress.update(88, "La copia Windows locale è già aggiornata.");
            return 0;
        }

        File root = archiveRoot(context, cfg, false);
        if (root == null) throw new Exception("Archivio Dossier non disponibile.");
        long required = requiredBytes(Math.max(0L, latest.size));
        if (latest.size > 0 && freeBytes(root) < required) throw new Exception("Spazio insufficiente per aggiornare il Dossier: servono " + formatBytes(required) + ".");

        File encryptedPart = new File(root, "r45_snapshot_refresh.dsl5.part");
        File plainZip = new File(context.getCacheDir(), "r45_snapshot_refresh.zip");
        if (encryptedPart.exists()) encryptedPart.delete();
        if (plainZip.exists()) plainZip.delete();
        try {
            if (progress != null) progress.update(20, "Download della copia Windows più recente...");
            java.util.concurrent.atomic.AtomicReference<Throwable> downloadError = new java.util.concurrent.atomic.AtomicReference<>();
            Thread download = new Thread(() -> {
                try {
                    R12Rclone.copyFromRemote(context, cloudRoot(cfg) + "/snapshots/" + latest.name, encryptedPart);
                } catch (Throwable failure) {
                    downloadError.set(failure);
                }
            }, "clinica-r45-snapshot-download");
            download.setDaemon(true);
            download.start();
            int lastDownload = 20;
            while (download.isAlive()) {
                if (latest.size > 0L && progress != null) {
                    int now = R45ProgressMath.percent(encryptedPart.length(), latest.size, 20, 40);
                    if (now > lastDownload) {
                        lastDownload = now;
                        progress.update(now, "Download copia Windows " + now + "%...");
                    }
                }
                try { download.join(250L); }
                catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); throw new Exception("Sincronizzazione interrotta."); }
            }
            Throwable downloadFailure = downloadError.get();
            if (downloadFailure != null) throw new Exception(String.valueOf(downloadFailure.getMessage()), downloadFailure);
            if (latest.size > 0 && encryptedPart.length() != latest.size) throw new Exception("La copia cloud più recente non ha la dimensione attesa.");
            if (progress != null) progress.update(41, "Copia Windows scaricata. Preparazione decifratura...");

            byte[] recovery = recoveryKey(context, cfg);
            final int[] lastDecrypt = new int[]{41};
            try (InputStream decrypted = R12Crypto.openDsl5File(encryptedPart, recovery, (read, total) -> {
                        if (progress == null) return;
                        int now = R45ProgressMath.percent(read, total, 42, 59);
                        if (now > lastDecrypt[0]) {
                            lastDecrypt[0] = now;
                            progress.update(now, "Decifratura copia Windows " + now + "%...");
                        }
                    });
                 FileOutputStream out = new FileOutputStream(plainZip)) {
                byte[] buffer = new byte[256 * 1024];
                int n;
                while ((n = decrypted.read(buffer)) >= 0) if (n > 0) out.write(buffer, 0, n);
                out.flush();
            }
            if (!plainZip.isFile() || plainZip.length() == 0) throw new Exception("Snapshot Windows decifrato non disponibile.");
            if (progress != null) progress.update(60, "Decifratura completata. Importazione dati Windows...");

            R27ExactWindows.ProgressCallback importProgress = (done, total, stage) -> {
                if (progress == null) return;
                int now = R45ProgressMath.importPercent(done, total);
                String detail = stage == null || stage.trim().isEmpty() ? "Importazione dati Windows" : stage;
                progress.update(now, detail + " · " + now + "%");
            };
            R30BoundedWindows.importSnapshot(context, prefs, cfg, plainZip, importProgress);
            if (progress != null) progress.update(87, "Importazione Windows completata.");

            File finalFile = new File(root, "current_snapshot.dsl5");
            replaceVerified(encryptedPart, finalFile);
            cfg.put("lastSnapshotName", latest.name);
            cfg.put("r36ReconciledSnapshotName", latest.name);
            cfg.put("r36SnapshotReconciledAt", Instant.now().toString());
            saveConfig(prefs, cfg);
            if (progress != null) progress.update(88, "Dati Windows aggiornati.");
            return 1;
        } finally {
            if (plainZip.exists()) plainZip.delete();
            if (encryptedPart.exists()) encryptedPart.delete();
        }
    }'''

insert = cloud.find('    private static int r44RefreshLatestCommittedSnapshot(')
if insert < 0:
    raise SystemExit('R45 failed: R44 refresh method missing')
cloud = cloud[:insert] + refresh45 + '\n\n' + cloud[insert:]

sync45 = r'''    public static void syncInteractiveR45(Activity activity, SharedPreferences prefs) {
        ProgressDialog dialog = new ProgressDialog(activity);
        dialog.setTitle("Sincronizzazione Dossier");
        dialog.setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);
        dialog.setIndeterminate(false);
        dialog.setMax(100);
        dialog.setProgress(2);
        dialog.setMessage("Controllo configurazione...");
        dialog.setCancelable(false);
        dialog.show();
        EXECUTOR.execute(() -> {
            try {
                JSONObject cfg = loadConfig(prefs);
                if (cfg.optString("archiveId", "").isEmpty()) throw new Exception("Dossier cloud non configurato");
                R44Progress ui = (value, message) -> activity.runOnUiThread(() -> {
                    dialog.setIndeterminate(false);
                    dialog.setProgress(Math.max(0, Math.min(100, value)));
                    dialog.setMessage(message);
                });
                boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
                int snapshotUpdated = 0;
                if (snapshotSafe) snapshotUpdated = r45RefreshLatestCommittedSnapshot(activity, prefs, cfg, ui);
                else ui.update(88, "Copia Windows non sostituita: ci sono modifiche Android da inviare.");

                ui.update(90, "Ricezione delle modifiche dal Dossier...");
                int received = pullRemoteChanges(activity, prefs, cfg, false);
                ui.update(94, "Invio delle modifiche locali...");
                int sent = uploadPendingChanges(activity, prefs, cfg);
                ui.update(98, "Verifica finale della sincronizzazione...");
                checkCompletionConsumed(activity, prefs, cfg);
                cfg.put("lastSyncAt", Instant.now().toString());
                saveConfig(prefs, cfg);
                ui.update(100, "Sincronizzazione completata.");
                final String result = sent + " inviate · " + received + " ricevute" + (snapshotUpdated > 0 ? " · archivio Windows aggiornato" : "");
                activity.runOnUiThread(() -> {
                    dialog.dismiss();
                    Toast.makeText(activity, "Sincronizzazione completata · " + result, Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                activity.runOnUiThread(() -> {
                    dialog.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Sincronizzazione non completata").setMessage(r42SyncMessage(e)).setPositiveButton("Chiudi", null).show();
                });
            }
        });
    }'''

marker = '    public static void syncInteractiveR44(Activity activity, SharedPreferences prefs) {'
pos = cloud.find(marker)
if pos < 0:
    raise SystemExit('R45 failed: R44 sync entry missing')
cloud = cloud[:pos] + sync45 + '\n\n' + cloud[pos:]
cloud = cloud.replace('syncInteractiveR44(activity, prefs)', 'syncInteractiveR45(activity, prefs)')
CLOUD.write_text(cloud, encoding='utf-8')

# Build identity.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s+44', 'versionCode 45', g, count=1)
g = re.sub(r'versionName\s+["\'][^"\']+["\']', 'versionName "1.0.0-android-r45-year-axis-progressive-backup-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

print('R45 year-axis, point-reference and progressive backup fix applied')
