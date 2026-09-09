from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
RCLONE = BASE / 'R12Rclone.java'
MANIFEST = Path('android-r3/app/src/main/AndroidManifest.xml')
GRADLE = Path('android-r3/app/build.gradle')
GEOMETRY = BASE / 'R43LayoutGeometry.java'


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R43 failed: missing {label or signature}')
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
        raise SystemExit(f'R43 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# ---------------------------------------------------------------------------
# 1. LANDSCAPE: deterministic geometry + explicit rebuild on rotation.
# Portrait remains 92dp. Landscape uses a real pixel width from the current
# display instead of weights that can be resolved inside a stale/narrow row.
# ---------------------------------------------------------------------------
GEOMETRY.write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

final class R43LayoutGeometry {
    private R43LayoutGeometry() {}

    static int portraitLabelWidthPx(float density) {
        return Math.round(92f * density);
    }

    static int landscapeLabelWidthPx(int screenWidthPx, float density) {
        int min = Math.round(300f * density);
        int max = Math.round(420f * density);
        int proportional = Math.round(screenWidthPx * 0.48f);
        return Math.max(min, Math.min(max, proportional));
    }
}
''', encoding='utf-8')

s = MAIN.read_text(encoding='utf-8')
if 'import android.content.res.Configuration;' not in s:
    anchor = 'import android.content.SharedPreferences;\n'
    if anchor not in s:
        raise SystemExit('R43 failed: SharedPreferences import missing')
    s = s.replace(anchor, anchor + 'import android.content.res.Configuration;\n', 1)

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

        float density = getResources().getDisplayMetrics().density;
        if (landscape) {
            int width = R43LayoutGeometry.landscapeLabelWidthPx(getResources().getDisplayMetrics().widthPixels, density);
            labelView.setSingleLine(true);
            labelView.setMaxLines(1);
            labelView.setHorizontallyScrolling(false);
            labelView.setEllipsize(null);
            row.addView(labelView, new LinearLayout.LayoutParams(width, ViewGroup.LayoutParams.WRAP_CONTENT));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        } else {
            int width = R43LayoutGeometry.portraitLabelWidthPx(density);
            row.addView(labelView, new LinearLayout.LayoutParams(width, ViewGroup.LayoutParams.WRAP_CONTENT));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        }
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'deterministic labelValue')

rotation = r'''    @Override public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        if (content != null) {
            int side = newConfig.orientation == Configuration.ORIENTATION_LANDSCAPE ? dp(12) : dp(16);
            content.setPadding(side, dp(4), side, dp(28));
        }
        renderSection(currentSection);
    }'''
insert_at = s.find('    @Override public void onBackPressed() {')
if insert_at < 0:
    raise SystemExit('R43 failed: onBackPressed marker missing')
if 'onConfigurationChanged(Configuration newConfig)' not in s:
    s = s[:insert_at] + rotation + '\n\n' + s[insert_at:]
s = s.replace('Android R42 TEST COMPLETO', 'Android R43 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')

m = MANIFEST.read_text(encoding='utf-8')
old = '<activity\n            android:name=".R6MainActivity"\n            android:exported="true">'
new = '<activity\n            android:name=".R6MainActivity"\n            android:configChanges="orientation|screenSize|keyboardHidden"\n            android:exported="true">'
if old in m:
    m = m.replace(old, new, 1)
elif 'android:name=".R6MainActivity"' in m and 'android:configChanges=' not in m:
    m = m.replace('android:name=".R6MainActivity"', 'android:name=".R6MainActivity"\n            android:configChanges="orientation|screenSize|keyboardHidden"', 1)
MANIFEST.write_text(m, encoding='utf-8')


# ---------------------------------------------------------------------------
# 2. GRAPH PARITY WITH WINDOWS.
# Keep the exact Windows-backed clinical series and reference ranges, but use
# the Windows presentation model: observations are distributed evenly in their
# chronological order, every clinical date is shown, labels are inclined, and
# the Y-unit has its own reserved margin separate from tick values.
# ---------------------------------------------------------------------------
chart = CHART.read_text(encoding='utf-8')
chart = chart.replace('setMinimumHeight(dp(300));', 'setMinimumHeight(dp(360));')

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
            if (Math.abs(referenceHigh - referenceLow) > 0.000001) {
                drawReferenceLine(canvas, referenceHigh, min, max, left, right, top, bottom);
            }
        }

        Path p = new Path();
        for (int i = 0; i < values.size(); i++) {
            float x = pointXForIndex(i, values.size(), left, right);
            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);
            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);
            canvas.drawCircle(x, y, dp(4.0f), point);
        }
        if (values.size() > 1) canvas.drawPath(p, line);

        drawYearAxis(canvas, 0L, 0L, left, right, bottom);

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
            if (referenceDate != null && !referenceDate.isEmpty()) {
                canvas.drawText("Riferimento dal referto del " + shortClinicalDate(referenceDate), left, legendY - dp(22), label);
            }
        }
    }'''
chart = replace_block(chart, '    @Override protected void onDraw(Canvas canvas) {', on_draw, 'Windows-parity onDraw')

axis = r'''    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {
        if (dates.isEmpty()) return;
        Paint.Align previous = label.getTextAlign();
        label.setTextAlign(Paint.Align.RIGHT);
        for (int i = 0; i < dates.size(); i++) {
            String text = shortClinicalDate(dates.get(i));
            if (text.isEmpty()) continue;
            float x = pointXForIndex(i, dates.size(), left, right);
            canvas.save();
            canvas.rotate(dateLabelRotationDegrees(), x, bottom + dp(18));
            canvas.drawText(text, x, bottom + dp(18), label);
            canvas.restore();
        }
        label.setTextAlign(previous);
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
        if (parsed.length > 0 && parsed[0] > 0) {
            return new SimpleDateFormat("dd/MM/yyyy", Locale.ITALY).format(new Date(parsed[0]));
        }
        if (value.length() >= 10) return value.substring(0, 10);
        return value;
    }'''
chart = replace_block(chart, '    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {', axis, 'all inclined clinical dates')
# Remove R42 helper if still present; it is no longer used.
chart = re.sub(r'\n    private float yearX\(int year, long tMin, long tMax, float left, float right\) \{.*?\n    \}', '', chart, flags=re.S)
CHART.write_text(chart, encoding='utf-8')


# ---------------------------------------------------------------------------
# 3. SYNC: bound the remote lookup itself, validate the exact family archive,
# then require a committed Windows snapshot before continuing. No silent phase-1
# warning/fallback to stale local data.
# ---------------------------------------------------------------------------
r = RCLONE.read_text(encoding='utf-8')
marker = '    public static JSONArray lsJson(Context context, String remote, boolean recursive) throws Exception {'
if marker not in r:
    raise SystemExit('R43 failed: lsJson marker missing')
extra = r'''    public static String runBounded(Context context, List<String> args, long timeoutSeconds) throws Exception {
        File exe = new File(context.getApplicationInfo().nativeLibraryDir, "librclone.so");
        if (!exe.isFile()) throw new Exception("Connettore cloud Android non disponibile in questa build.");
        List<String> command = new ArrayList<>();
        command.add(exe.getAbsolutePath());
        command.addAll(args);
        boolean hasConfig = false;
        for (String arg : args) if ("--config".equals(arg)) hasConfig = true;
        if (!hasConfig && !args.isEmpty() && !"obscure".equals(args.get(0))) {
            command.add("--config");
            command.add(configFile(context).getAbsolutePath());
        }
        command.add("--log-level");
        command.add("ERROR");
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        builder.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath());
        builder.environment().put("HOME", context.getFilesDir().getAbsolutePath());
        Process process = builder.start();
        StringBuilder output = new StringBuilder();
        Thread reader = new Thread(() -> {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) output.append(line).append('\n');
            } catch (Exception ignored) {}
        }, "r43-rclone-reader");
        reader.start();
        boolean finished = process.waitFor(Math.max(10L, timeoutSeconds), TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            try { reader.join(2000L); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
            throw new Exception("La lettura del cloud ha superato il tempo massimo.");
        }
        try { reader.join(2000L); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
        if (process.exitValue() != 0) {
            String message = output.toString().trim();
            if (message.length() > 700) message = message.substring(message.length() - 700);
            throw new Exception(message.isEmpty() ? "Operazione cloud non riuscita." : message);
        }
        return output.toString();
    }

    public static JSONArray lsJsonBounded(Context context, String remote, boolean recursive, long timeoutSeconds) throws Exception {
        List<String> args = list("lsjson", remote, "--files-only", "--retries", "4", "--low-level-retries", "10", "--retries-sleep", "2s");
        if (recursive) args.add("--recursive");
        String raw = runBounded(context, args, timeoutSeconds).trim();
        return raw.isEmpty() ? new JSONArray() : new JSONArray(raw);
    }

    public static String catBounded(Context context, String remote, long timeoutSeconds) throws Exception {
        return runBounded(context, list("cat", remote, "--retries", "4", "--low-level-retries", "10", "--retries-sleep", "2s"), timeoutSeconds);
    }

'''
r = r.replace(marker, extra + marker, 1)
RCLONE.write_text(r, encoding='utf-8')

c = CLOUD.read_text(encoding='utf-8')
latest = r'''    private static SnapshotInfo latestSnapshot(Context context,JSONObject cfg)throws Exception{
        String snapshotsRoot = cloudRoot(cfg) + "/snapshots";
        Exception last = null;
        for (int attempt = 1; attempt <= 3; attempt++) {
            try {
                JSONArray items = R12Rclone.lsJsonBounded(context, snapshotsRoot, false, 60L);
                Set<String> names = new HashSet<>();
                for (int i = 0; i < items.length(); i++) {
                    JSONObject x = items.optJSONObject(i);
                    if (x == null) continue;
                    String n = x.optString("Path", x.optString("Name", ""));
                    if (!n.isEmpty()) {
                        names.add(n);
                        names.add(n.substring(n.lastIndexOf('/') + 1));
                    }
                }
                List<SnapshotInfo> list = new ArrayList<>();
                for (int i = 0; i < items.length(); i++) {
                    JSONObject x = items.optJSONObject(i);
                    if (x == null) continue;
                    String n = x.optString("Path", x.optString("Name", ""));
                    if (!n.endsWith(".dsl5")) continue;
                    String leaf = n.substring(n.lastIndexOf('/') + 1);
                    boolean committed = !leaf.startsWith("snapshot23_") || names.contains(leaf + ".commit") || names.contains(n + ".commit");
                    if (!committed) continue;
                    list.add(new SnapshotInfo(leaf, x.optLong("Size", 0)));
                }
                list.sort((a,b)->b.name.compareTo(a.name));
                if (list.isEmpty()) throw new Exception("Nessuna copia Windows committed trovata nella cartella snapshots del Dossier autorizzato.");
                return list.get(0);
            } catch (Exception ex) {
                last = ex;
                if (attempt < 3) {
                    try { Thread.sleep(attempt * 2000L); }
                    catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new Exception("Sincronizzazione interrotta.");
                    }
                }
            }
        }
        String detail = last == null ? "" : String.valueOf(last.getMessage());
        throw new Exception("Impossibile leggere la cartella snapshots del Dossier Windows su MEGA." + (detail == null || detail.trim().isEmpty() ? "" : " " + detail));
    }'''
c = replace_block(c, '    private static SnapshotInfo latestSnapshot(Context context,JSONObject cfg)throws Exception{', latest, 'bounded latestSnapshot')

verify = r'''    private static void verifyArchiveManifestR43(Context context, JSONObject cfg) throws Exception {
        String remote = cloudRoot(cfg) + "/archive.json";
        String raw = R12Rclone.catBounded(context, remote, 45L).trim();
        JSONObject manifest = new JSONObject(raw);
        if (!"DSL5-CLOUD".equals(manifest.optString("format"))) {
            throw new Exception("Il percorso cloud non contiene un Dossier Clinica Digitale valido.");
        }
        if (!cfg.optString("archiveId", "").equals(manifest.optString("archiveId", ""))) {
            throw new Exception("Il percorso cloud appartiene a un Dossier diverso da quello autorizzato.");
        }
        if (!manifest.optString("displayName", "").isEmpty()) cfg.put("displayName", manifest.optString("displayName"));
    }

'''
insert = c.find('    private static SnapshotInfo latestSnapshot(')
if insert < 0:
    raise SystemExit('R43 failed: latestSnapshot insertion point missing')
c = c[:insert] + verify + c[insert:]

sync43 = r'''    public static void syncInteractiveR43(Activity activity, SharedPreferences prefs) {
        LinearLayout box = new LinearLayout(activity);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(activity, 22), dp(activity, 14), dp(activity, 22), dp(activity, 10));
        TextView phase = new TextView(activity);
        phase.setText("Fase 1 di 4");
        phase.setTextSize(16);
        phase.setTextColor(Color.rgb(55, 68, 65));
        box.addView(phase);
        TextView detail = new TextView(activity);
        detail.setText("Verifica dell'archivio Windows autorizzato...");
        detail.setTextSize(15);
        detail.setTextColor(Color.rgb(45, 58, 55));
        detail.setPadding(0, dp(activity, 8), 0, dp(activity, 12));
        box.addView(detail);
        android.widget.ProgressBar progress = new android.widget.ProgressBar(activity, null, android.R.attr.progressBarStyleHorizontal);
        progress.setIndeterminate(true);
        box.addView(progress, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(activity, 18)));
        AlertDialog dialog = new AlertDialog.Builder(activity).setTitle("Sincronizzazione Dossier").setView(box).setCancelable(false).create();
        dialog.show();

        java.util.function.BiConsumer<String,String> update = (p, d) -> activity.runOnUiThread(() -> {
            if (activity.isFinishing()) return;
            phase.setText(p);
            detail.setText(d);
        });

        EXECUTOR.execute(() -> {
            try {
                JSONObject cfg = loadConfig(prefs);
                if (cfg.optString("archiveId", "").isEmpty()) throw new Exception("Dossier cloud non configurato");
                if (archiveRoot(activity, cfg, false) == null) throw new Exception("Archivio Dossier non disponibile. Reinserisci la memoria selezionata.");

                update.accept("Fase 1 di 4", "Verifica dell'archivio Windows autorizzato...");
                verifyArchiveManifestR43(activity, cfg);
                update.accept("Fase 1 di 4", "Ricerca della copia Windows più recente...");
                if (readArray(prefs, QUEUE_KEY).length() != 0) {
                    throw new Exception("Sono presenti modifiche Android non ancora inviate. Sincronizzale prima di sostituire la copia Windows locale.");
                }
                int snapshotUpdated = r36RefreshLatestCommittedSnapshot(activity, prefs, cfg);

                update.accept("Fase 2 di 4", "Ricezione delle modifiche dal Dossier...");
                int received = pullRemoteChanges(activity, prefs, cfg, false);
                update.accept("Fase 3 di 4", "Invio delle modifiche locali...");
                int sent = uploadPendingChanges(activity, prefs, cfg);
                update.accept("Fase 4 di 4", "Verifica finale della sincronizzazione...");
                checkCompletionConsumed(activity, prefs, cfg);
                cfg.put("lastSyncAt", Instant.now().toString());
                saveConfig(prefs, cfg);

                String result = sent + " inviate · " + received + " ricevute" + (snapshotUpdated > 0 ? " · archivio Windows aggiornato" : " · copia Windows già aggiornata");
                final String message = result;
                activity.runOnUiThread(() -> {
                    if (dialog.isShowing()) dialog.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Sincronizzazione completata").setMessage(message).setPositiveButton("CHIUDI", null).show();
                });
            } catch (Exception ex) {
                final String message = r43SyncMessage(ex);
                activity.runOnUiThread(() -> {
                    if (dialog.isShowing()) dialog.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Sincronizzazione non completata").setMessage(message).setPositiveButton("CHIUDI", null).show();
                });
            }
        });
    }

    private static String r43SyncMessage(Exception ex) {
        String message = ex == null ? "" : String.valueOf(ex.getMessage()).trim();
        String lower = message.toLowerCase(Locale.ROOT);
        if (lower.contains("unexpected end of json input") || lower.contains("failed to open source object")) {
            return "MEGA non ha restituito correttamente la copia Windows. La sincronizzazione è stata interrotta senza usare dati vecchi.";
        }
        if (lower.contains("tempo massimo")) return "MEGA non ha risposto entro il tempo massimo durante la ricerca della copia Windows.";
        if (message.length() > 500) message = message.substring(message.length() - 500);
        return message.isEmpty() ? "Operazione cloud non riuscita." : message;
    }'''
marker = '    public static void syncInteractiveR42(Activity activity, SharedPreferences prefs) {'
if marker not in c:
    raise SystemExit('R43 failed: R42 sync marker missing')
c = c.replace(marker, sync43 + '\n\n' + marker, 1)
c = c.replace('syncInteractiveR42(activity, prefs);', 'syncInteractiveR43(activity, prefs);')
CLOUD.write_text(c, encoding='utf-8')


# 4. Version identity.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s+42\b', 'versionCode 43', g, count=1)
g = re.sub(r'versionName\s+[\'\"]1\.0\.0-android-r42-realdevice-landscape-graph-sync-final-test[\'\"]', 'versionName "1.0.0-android-r43-windows-parity-landscape-sync-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

print('R43 Windows-parity graph, deterministic landscape and bounded Windows snapshot sync applied')
