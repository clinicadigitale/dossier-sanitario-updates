from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
SERIES = BASE / 'R40ClinicalSeries.java'
CLOUD = BASE / 'R12CloudManager.java'
RCLONE = BASE / 'R12Rclone.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R44 failed: missing {label or signature}')
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
        raise SystemExit(f'R44 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# 1. Landscape: exact requested 30/70 split. Rotation rebuild from R43 is preserved.
s = MAIN.read_text(encoding='utf-8')
label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.TOP);
        row.setPadding(0, dp(5), 0, dp(5));
        row.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        boolean landscape = r36Landscape();
        TextView labelView = text(label, 13, MUTED, false);
        String visibleValue = r36HumanReminderDisplay(label, value);
        TextView valueView = text(visibleValue, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);

        if (landscape) {
            labelView.setSingleLine(true);
            labelView.setMaxLines(1);
            labelView.setHorizontallyScrolling(false);
            labelView.setEllipsize(null);
            row.addView(labelView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 0.30f));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 0.70f));
        } else {
            row.addView(labelView, new LinearLayout.LayoutParams(dp(92), ViewGroup.LayoutParams.WRAP_CONTENT));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        }
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, '30/70 labelValue')

# Fast selector: one pass only. Do not recompute every series just to populate the list.
selector = r'''    private void r31SelectClinicalValue(boolean graph) {
        java.util.ArrayList<JSONObject> choices = new java.util.ArrayList<>();

        JSONArray labs = R40ClinicalSeries.availableLabParameters(prefs);
        for (int i = 0; i < labs.length(); i++) {
            JSONObject p = labs.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "");
            if (id.isEmpty()) continue;
            String label = p.optString("name", id);
            String unit = p.optString("unit", "");
            if (!unit.isEmpty()) label += " (" + unit + ")";
            label += " · referti";
            try {
                JSONObject choice = new JSONObject();
                choice.put("label", label);
                choice.put("code", "l|" + id + "|value|" + label);
                choices.add(choice);
            } catch (Exception ignored) {}
        }

        r36AddClinicalChoice(choices, "Peso", "u|weight|value|Peso", R27ExactWindows.measurementsOf(prefs, "weight"));
        r36AddClinicalChoice(choices, "Saturazione ossigeno", "u|spo2|value|Saturazione ossigeno", R27ExactWindows.measurementsOf(prefs, "spo2"));
        r36AddClinicalChoice(choices, "Glicemia manuale", "u|glucose|value|Glicemia manuale", R27ExactWindows.measurementsOf(prefs, "glucose"));
        r36AddClinicalChoice(choices, "Frequenza cardiaca", "u|heart_rate|value|Frequenza cardiaca", R27ExactWindows.measurementsOf(prefs, "heart_rate"));
        JSONArray pressure = R27ExactWindows.measurementsOf(prefs, "blood_pressure");
        if (graph) {
            r36AddClinicalChoice(choices, "Pressione arteriosa", "p|blood_pressure|both|Pressione arteriosa", pressure);
            r36AddClinicalChoice(choices, "Frequenza da pressione", "u|blood_pressure|heartRate|Frequenza da pressione", pressure);
        } else {
            r36AddClinicalChoice(choices, "Pressione sistolica", "u|blood_pressure|systolic|Pressione sistolica", pressure);
            r36AddClinicalChoice(choices, "Pressione diastolica", "u|blood_pressure|diastolic|Pressione diastolica", pressure);
            r36AddClinicalChoice(choices, "Frequenza da pressione", "u|blood_pressure|heartRate|Frequenza da pressione", pressure);
        }

        if (choices.isEmpty()) {
            Toast.makeText(this, "Nessun parametro disponibile", Toast.LENGTH_SHORT).show();
            return;
        }
        choices.sort((a, b) -> a.optString("label", "").compareToIgnoreCase(b.optString("label", "")));
        String[] labels = new String[choices.size()];
        String[] codes = new String[choices.size()];
        for (int i = 0; i < choices.size(); i++) {
            labels[i] = choices.get(i).optString("label", "Parametro");
            codes[i] = choices.get(i).optString("code", "");
        }
        new AlertDialog.Builder(this)
                .setTitle(graph ? "Seleziona valore da visualizzare" : "Seleziona valore da confrontare")
                .setItems(labels, (d, which) -> {
                    prefs.edit().putString(graph ? "r31_graph_choice" : "r31_compare_choice", codes[which]).apply();
                    renderSection(graph ? "Grafici" : "Confronta");
                })
                .setNegativeButton("Annulla", null)
                .show();
    }'''
s = replace_block(s, '    private void r31SelectClinicalValue(boolean graph) {', selector, 'fast selector')
s = s.replace('Android R43 TEST COMPLETO', 'Android R44 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')

# One-pass laboratory parameter discovery. R43/R40 rescanned all documents once per parameter.
series = SERIES.read_text(encoding='utf-8')
available = r'''    static JSONArray availableLabParameters(SharedPreferences prefs) {
        LinkedHashMap<String, JSONObject> parameters = new LinkedHashMap<>();
        JSONArray docs = R27ExactWindows.documents(prefs);
        for (int i = 0; i < docs.length(); i++) {
            JSONObject doc = docs.optJSONObject(i);
            JSONArray labs = doc == null ? null : doc.optJSONArray("labValues");
            if (labs == null) continue;
            for (int j = 0; j < labs.length(); j++) {
                JSONObject lab = labs.optJSONObject(j);
                if (lab == null || explicitInvalid(lab)) continue;
                String id = lab.optString("parameterId", "").trim();
                if (id.isEmpty() || parameters.containsKey(id)) continue;
                if (!Double.isFinite(canonicalValue(lab))) continue;
                try {
                    JSONObject p = new JSONObject();
                    p.put("id", id);
                    p.put("name", lab.optString("parameterName", id));
                    p.put("unit", canonicalUnit(lab));
                    parameters.put(id, p);
                } catch (Exception ignored) {}
            }
        }
        JSONArray out = new JSONArray();
        for (JSONObject p : parameters.values()) out.put(p);
        return out;
    }'''
series = replace_block(series, '    static JSONArray availableLabParameters(SharedPreferences prefs) {', available, 'one-pass lab parameter index')
SERIES.write_text(series, encoding='utf-8')

# 2. Graph parity: preserve R43 inclined labels, restore the Windows time-proportional X geometry.
chart = CHART.read_text(encoding='utf-8')
on_draw = r'''    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        boolean hasReference = Double.isFinite(referenceLow) && Double.isFinite(referenceHigh);
        float left = dp(82), right = getWidth() - dp(18), top = dp(38);
        float bottom = getHeight() - dp(hasReference ? 132 : 108);
        if (right <= left || bottom <= top) return;
        if (values.isEmpty()) {
            canvas.drawText(emptyText, left, top + dp(28), label);
            return;
        }

        double[] bounds = scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh);
        double min = bounds[0], max = bounds[1];

        Paint.Align oldAlign = label.getTextAlign();
        label.setTextAlign(Paint.Align.RIGHT);
        for (int i = 0; i <= 4; i++) {
            float y = top + (bottom - top) * i / 4f;
            canvas.drawLine(left, y, right, y, grid);
            double tick = max - (max - min) * i / 4.0;
            canvas.drawText(shortNumber(tick), left - dp(10), y + dp(4), label);
        }
        label.setTextAlign(oldAlign);

        if (hasReference) {
            drawReferenceLine(canvas, referenceLow, min, max, left, right, top, bottom);
            if (Math.abs(referenceHigh - referenceLow) > 0.000001) drawReferenceLine(canvas, referenceHigh, min, max, left, right, top, bottom);
        }

        long[] times = dateTimes(dates);
        long tMin = Long.MAX_VALUE, tMax = Long.MIN_VALUE;
        for (long t : times) if (t > 0) { tMin = Math.min(tMin, t); tMax = Math.max(tMax, t); }
        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;

        Path p = new Path();
        for (int i = 0; i < values.size(); i++) {
            float x;
            if (values.size() == 1) x = (left + right) / 2f;
            else if (dated && i < times.length && times[i] > 0) x = pointXForTime(times[i], tMin, tMax, left, right);
            else x = pointXForIndex(i, values.size(), left, right);
            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);
            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);
            canvas.drawCircle(x, y, dp(4.0f), point);
        }
        if (values.size() > 1) canvas.drawPath(p, line);

        drawYearAxis(canvas, tMin, tMax, left, right, bottom);

        String unit = referenceUnit;
        if (unit == null || unit.isEmpty()) unit = seriesUnit;
        if (unit != null && !unit.isEmpty()) {
            canvas.save();
            canvas.rotate(-90f, dp(16), (top + bottom) / 2f);
            label.setTextAlign(Paint.Align.CENTER);
            canvas.drawText(unit, dp(16), (top + bottom) / 2f, label);
            label.setTextAlign(Paint.Align.LEFT);
            canvas.restore();
        }

        String footer = values.size() + " rilevazioni · min " + shortNumber(dataMin) + " · max " + shortNumber(dataMax);
        canvas.drawText(footer, left, dp(20), label);

        String axisTitle = "Data clinica";
        float aw = label.measureText(axisTitle);
        canvas.drawText(axisTitle, Math.max(left, (getWidth() - aw) / 2f), bottom + dp(88), label);

        if (hasReference) {
            float legendY = getHeight() - dp(20);
            canvas.drawLine(left, legendY - dp(4), left + dp(28), legendY - dp(4), reference);
            String interval = "Intervallo " + shortNumber(referenceLow) + " - " + shortNumber(referenceHigh) + (unit == null || unit.isEmpty() ? "" : " " + unit);
            canvas.drawText(interval, left + dp(38), legendY, label);
            if (referenceDate != null && !referenceDate.isEmpty()) canvas.drawText("Riferimento dal referto del " + shortClinicalDate(referenceDate), left, legendY - dp(22), label);
        }
    }'''
chart = replace_block(chart, '    @Override protected void onDraw(Canvas canvas) {', on_draw, 'Windows time-proportional onDraw')
axis = r'''    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {
        if (dates.isEmpty()) return;
        long[] times = dateTimes(dates);
        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;
        Paint.Align previous = label.getTextAlign();
        label.setTextAlign(Paint.Align.RIGHT);
        for (int i = 0; i < dates.size(); i++) {
            String text = shortClinicalDate(dates.get(i));
            if (text.isEmpty()) continue;
            float x;
            if (dated && i < times.length && times[i] > 0) x = pointXForTime(times[i], tMin, tMax, left, right);
            else x = pointXForIndex(i, dates.size(), left, right);
            canvas.save();
            canvas.rotate(dateLabelRotationDegrees(), x, bottom + dp(18));
            canvas.drawText(text, x, bottom + dp(18), label);
            canvas.restore();
        }
        label.setTextAlign(previous);
    }

    static float pointXForTime(long time, long minTime, long maxTime, float left, float right) {
        if (maxTime <= minTime) return (left + right) / 2f;
        long safe = Math.max(minTime, Math.min(maxTime, time));
        return left + (right - left) * (safe - minTime) / (float) (maxTime - minTime);
    }

    static float pointXForIndex(int index, int count, float left, float right) {
        if (count <= 1) return (left + right) / 2f;
        int safe = Math.max(0, Math.min(count - 1, index));
        return left + (right - left) * safe / (count - 1f);
    }

    static float dateLabelRotationDegrees() { return -45f; }

    private String shortClinicalDate(String raw) {
        if (raw == null || raw.trim().isEmpty()) return "";
        String value = raw.trim();
        long[] parsed = dateTimes(java.util.Collections.singletonList(value));
        if (parsed.length > 0 && parsed[0] > 0) return new SimpleDateFormat("dd/MM/yyyy", Locale.ITALY).format(new Date(parsed[0]));
        if (value.length() >= 10) return value.substring(0, 10);
        return value;
    }'''
chart = replace_block(chart, '    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {', axis, 'time-proportional inclined dates')
CHART.write_text(chart, encoding='utf-8')

# 3. Sync: real milestone progress and bounded snapshot discovery, with a plain-text listing fallback.
r = RCLONE.read_text(encoding='utf-8')
if 'public static String lsfBounded' not in r:
    marker = '    public static JSONArray lsJsonBounded(Context context, String remote, boolean recursive, long timeoutSeconds) throws Exception {'
    pos = r.find(marker)
    if pos < 0: raise SystemExit('R44 failed: lsJsonBounded marker missing')
    lsf = r'''    public static String lsfBounded(Context context, String remote, long timeoutSeconds) throws Exception {
        return runBounded(context, list("lsf", remote, "--files-only", "--format", "ps", "--separator", "\\t", "--retries", "2", "--low-level-retries", "4", "--retries-sleep", "1s"), timeoutSeconds);
    }

'''
    r = r[:pos] + lsf + r[pos:]
RCLONE.write_text(r, encoding='utf-8')

c = CLOUD.read_text(encoding='utf-8')
progress_iface = r'''    private interface R44Progress {
        void update(int value, String message);
    }

    private static SnapshotInfo latestSnapshotR44(Context context, JSONObject cfg) throws Exception {
        String snapshotsRoot = cloudRoot(cfg) + "/snapshots";
        JSONArray items = null;
        Exception jsonError = null;
        try {
            items = R12Rclone.lsJsonBounded(context, snapshotsRoot, false, 30L);
        } catch (Exception ex) {
            jsonError = ex;
        }
        if (items != null) {
            Set<String> names = new HashSet<>();
            for (int i = 0; i < items.length(); i++) {
                JSONObject x = items.optJSONObject(i);
                if (x != null) names.add(x.optString("Path", x.optString("Name", "")));
            }
            List<SnapshotInfo> list = new ArrayList<>();
            for (int i = 0; i < items.length(); i++) {
                JSONObject x = items.optJSONObject(i);
                if (x == null) continue;
                String n = x.optString("Path", x.optString("Name", ""));
                if (!n.endsWith(".dsl5")) continue;
                String leaf = n.substring(n.lastIndexOf('/') + 1);
                boolean committed = !leaf.startsWith("snapshot23_") || names.contains(leaf + ".commit") || names.contains(n + ".commit");
                if (committed) list.add(new SnapshotInfo(leaf, x.optLong("Size", 0)));
            }
            list.sort((a,b) -> b.name.compareTo(a.name));
            if (!list.isEmpty()) return list.get(0);
        }

        try {
            String plain = R12Rclone.lsfBounded(context, snapshotsRoot, 30L);
            Set<String> names = new HashSet<>();
            Map<String, Long> sizes = new HashMap<>();
            for (String line : plain.split("\\r?\\n")) {
                if (line.trim().isEmpty()) continue;
                String[] parts = line.split("\\t", 2);
                String name = parts[0].trim();
                if (name.isEmpty()) continue;
                names.add(name);
                if (parts.length > 1) try { sizes.put(name, Long.parseLong(parts[1].trim())); } catch (Exception ignored) {}
            }
            List<SnapshotInfo> list = new ArrayList<>();
            for (String name : names) {
                if (!name.endsWith(".dsl5")) continue;
                String leaf = name.substring(name.lastIndexOf('/') + 1);
                boolean committed = !leaf.startsWith("snapshot23_") || names.contains(leaf + ".commit") || names.contains(name + ".commit");
                if (committed) list.add(new SnapshotInfo(leaf, sizes.containsKey(name) ? sizes.get(name) : 0L));
            }
            list.sort((a,b) -> b.name.compareTo(a.name));
            if (!list.isEmpty()) return list.get(0);
        } catch (Exception plainError) {
            String a = jsonError == null ? "" : String.valueOf(jsonError.getMessage());
            String b = String.valueOf(plainError.getMessage());
            throw new Exception("Impossibile leggere la cartella snapshots del Dossier Windows su MEGA. " + (a.isEmpty() ? b : a));
        }
        throw new Exception("Nessuna copia Windows committed trovata nella cartella snapshots del Dossier autorizzato.");
    }

    private static int r44RefreshLatestCommittedSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, R44Progress progress) throws Exception {
        if (progress != null) progress.update(12, "Verifica dell'archivio MEGA autorizzato...");
        verifyArchiveManifestR43(context, cfg);
        if (progress != null) progress.update(20, "Ricerca della copia Windows più recente...");
        SnapshotInfo latest = latestSnapshotR44(context, cfg);
        String reconciled = cfg.optString("r36ReconciledSnapshotName", "");
        if (!reconciled.isEmpty() && latest.name.equals(reconciled)) {
            if (progress != null) progress.update(55, "La copia Windows locale è già aggiornata.");
            return 0;
        }

        File root = archiveRoot(context, cfg, false);
        if (root == null) throw new Exception("Archivio Dossier non disponibile.");
        long required = requiredBytes(Math.max(0L, latest.size));
        if (latest.size > 0 && freeBytes(root) < required) throw new Exception("Spazio insufficiente per aggiornare il Dossier: servono " + formatBytes(required) + ".");

        File encryptedPart = new File(root, "r44_snapshot_refresh.dsl5.part");
        File plainZip = new File(context.getCacheDir(), "r44_snapshot_refresh.zip");
        if (encryptedPart.exists()) encryptedPart.delete();
        if (plainZip.exists()) plainZip.delete();
        try {
            if (progress != null) progress.update(28, "Download della copia Windows più recente...");
            R12Rclone.copyFromRemote(context, cloudRoot(cfg) + "/snapshots/" + latest.name, encryptedPart);
            if (latest.size > 0 && encryptedPart.length() != latest.size) throw new Exception("La copia cloud più recente non ha la dimensione attesa.");
            if (progress != null) progress.update(42, "Copia Windows scaricata. Decifratura in corso...");

            byte[] recovery = recoveryKey(context, cfg);
            try (InputStream decrypted = R12Crypto.openDsl5File(encryptedPart, recovery); FileOutputStream out = new FileOutputStream(plainZip)) {
                byte[] buffer = new byte[256 * 1024];
                int n;
                while ((n = decrypted.read(buffer)) >= 0) if (n > 0) out.write(buffer, 0, n);
                out.flush();
            }
            if (!plainZip.isFile() || plainZip.length() == 0) throw new Exception("Snapshot Windows decifrato non disponibile.");
            if (progress != null) progress.update(50, "Importazione dei dati Windows nel Dossier Android...");
            R30BoundedWindows.importSnapshot(context, prefs, cfg, plainZip, null);
            File finalFile = new File(root, "current_snapshot.dsl5");
            replaceVerified(encryptedPart, finalFile);
            cfg.put("lastSnapshotName", latest.name);
            cfg.put("r36ReconciledSnapshotName", latest.name);
            cfg.put("r36SnapshotReconciledAt", Instant.now().toString());
            saveConfig(prefs, cfg);
            if (progress != null) progress.update(60, "Dati Windows aggiornati.");
            return 1;
        } finally {
            if (plainZip.exists()) plainZip.delete();
            if (encryptedPart.exists()) encryptedPart.delete();
        }
    }

'''
insert = c.find('    private static void verifyArchiveManifestR43(')
if insert < 0: raise SystemExit('R44 failed: R43 manifest helper missing')
c = c[:insert] + progress_iface + c[insert:]

sync44 = r'''    public static void syncInteractiveR44(Activity activity, SharedPreferences prefs) {
        ProgressDialog dialog = new ProgressDialog(activity);
        dialog.setTitle("Sincronizzazione Dossier");
        dialog.setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);
        dialog.setIndeterminate(false);
        dialog.setMax(100);
        dialog.setProgress(3);
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
                if (snapshotSafe) snapshotUpdated = r44RefreshLatestCommittedSnapshot(activity, prefs, cfg, ui);
                else ui.update(60, "Copia Windows non sostituita: ci sono modifiche Android da inviare.");

                ui.update(68, "Ricezione delle modifiche dal Dossier...");
                int received = pullRemoteChanges(activity, prefs, cfg, false);
                ui.update(82, "Invio delle modifiche locali...");
                int sent = uploadPendingChanges(activity, prefs, cfg);
                ui.update(94, "Verifica finale della sincronizzazione...");
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
# append method before the current R43 entry if not already present
marker = '    public static void syncInteractiveR43(Activity activity, SharedPreferences prefs) {'
pos = c.find(marker)
if pos < 0: raise SystemExit('R44 failed: R43 sync entry missing')
c = c[:pos] + sync44 + '\n\n' + c[pos:]
# route every interactive predecessor/current wrapper to R44
c = c.replace('syncInteractiveR43(activity, prefs)', 'syncInteractiveR44(activity, prefs)')
CLOUD.write_text(c, encoding='utf-8')

# Build identity.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s+43', 'versionCode 44', g, count=1)
g = re.sub(r'versionName\s+["\'][^"\']+["\']', 'versionName "1.0.0-android-r44-realdevice-parity-sync-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

print('R44 real-device 30/70, Windows time-geometry, fast selector and milestone sync applied')
