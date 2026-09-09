from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
RCLONE = BASE / 'R12Rclone.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R42 failed: missing {label or signature}')
    brace = text.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f'R42 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# ---------------------------------------------------------------------------
# 1. LANDSCAPE: every standard label/value row must actually occupy the card
#    width. R41 used weights but left the row itself WRAP_CONTENT, so on the real
#    Xiaomi the weights were calculated inside a narrow row. Portrait is frozen.
# ---------------------------------------------------------------------------
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
            row.addView(labelView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 0.48f));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 0.52f));
        } else {
            row.addView(labelView, new LinearLayout.LayoutParams(dp(92), ViewGroup.LayoutParams.WRAP_CONTENT));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        }
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'labelValue full-width landscape')
s = s.replace('Android R41 TEST COMPLETO', 'Android R42 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')


# ---------------------------------------------------------------------------
# 2. GRAPHS: keep the Windows-backed series/reference lines from R41, but make
#    the clinical year axis adaptive to the actual plot width. Never draw more
#    year labels than fit. Always preserve first/last year. This prevents the
#    real-device overlap seen on the Xiaomi while keeping the Windows behaviour
#    of a chronological year axis.
# ---------------------------------------------------------------------------
chart = CHART.read_text(encoding='utf-8')
year_axis = r'''    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {
        java.util.Calendar c1 = java.util.Calendar.getInstance(Locale.ITALY);
        java.util.Calendar c2 = java.util.Calendar.getInstance(Locale.ITALY);
        c1.setTimeInMillis(tMin);
        c2.setTimeInMillis(tMax);
        int y1 = c1.get(java.util.Calendar.YEAR);
        int y2 = c2.get(java.util.Calendar.YEAR);
        if (y2 < y1) { int t = y1; y1 = y2; y2 = t; }
        int span = Math.max(1, y2 - y1);
        float plotWidth = Math.max(1f, right - left);
        float fourDigitWidth = Math.max(dp(24), label.measureText("0000"));
        float minimumSpacing = fourDigitWidth + dp(16);
        int maximumLabels = Math.max(2, (int) Math.floor(plotWidth / minimumSpacing) + 1);
        int rawStep = Math.max(1, (int) Math.ceil(span / (double) Math.max(1, maximumLabels - 1)));
        int step;
        if (rawStep <= 1) step = 1;
        else if (rawStep <= 2) step = 2;
        else if (rawStep <= 5) step = 5;
        else if (rawStep <= 10) step = 10;
        else if (rawStep <= 20) step = 20;
        else if (rawStep <= 25) step = 25;
        else step = ((rawStep + 49) / 50) * 50;

        java.util.ArrayList<Integer> years = new java.util.ArrayList<>();
        years.add(y1);
        int firstAligned = ((y1 + step - 1) / step) * step;
        for (int year = firstAligned; year < y2; year += step) {
            if (year > y1 && year < y2) years.add(year);
        }
        if (y2 != y1) years.add(y2);

        // If endpoint insertion still makes two labels too close, remove inner
        // labels from the right until every visible label has enough room.
        while (years.size() > 2) {
            boolean overlap = false;
            float previousX = -Float.MAX_VALUE;
            for (int year : years) {
                float x = yearX(year, tMin, tMax, left, right);
                if (previousX > -Float.MAX_VALUE && x - previousX < minimumSpacing) {
                    overlap = true;
                    break;
                }
                previousX = x;
            }
            if (!overlap) break;
            years.remove(years.size() - 2);
        }

        for (int year : years) {
            float x = yearX(year, tMin, tMax, left, right);
            String text = String.valueOf(year);
            float tw = label.measureText(text);
            float drawX = Math.max(left, Math.min(right - tw, x - tw / 2f));
            canvas.drawText(text, drawX, bottom + dp(18), label);
        }
    }

    private float yearX(int year, long tMin, long tMax, float left, float right) {
        java.util.Calendar cy = java.util.Calendar.getInstance(Locale.ITALY);
        cy.clear();
        cy.set(java.util.Calendar.YEAR, year);
        cy.set(java.util.Calendar.MONTH, 0);
        cy.set(java.util.Calendar.DAY_OF_MONTH, 1);
        long t = cy.getTimeInMillis();
        if (tMax <= tMin) return left;
        return left + (right - left) * (t - tMin) / (float) (tMax - tMin);
    }'''
chart = replace_block(chart, '    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {', year_axis, 'adaptive year axis')
CHART.write_text(chart, encoding='utf-8')


# ---------------------------------------------------------------------------
# 3. CLOUD TRANSPORT: MEGA/rclone can transiently return an incomplete JSON API
#    response while opening a remote object. Rclone already retries internally,
#    but a single failed command previously aborted the whole Dossier sync and
#    exposed the raw technical log. Add a bounded outer retry for remote copies.
# ---------------------------------------------------------------------------
r = RCLONE.read_text(encoding='utf-8')
copy_remote = r'''    public static void copyFromRemote(Context context, String remote, File local) throws Exception {
        File parent = local.getParentFile();
        if (parent != null && !parent.exists()) parent.mkdirs();
        Exception last = null;
        for (int attempt = 1; attempt <= 3; attempt++) {
            if (local.exists()) local.delete();
            try {
                run(context, list("copyto", remote, local.getAbsolutePath(), "--retries", "4", "--low-level-retries", "10", "--retries-sleep", "2s"));
                if (!local.isFile() || local.length() <= 0) throw new Exception("Download cloud non completato.");
                return;
            } catch (Exception ex) {
                last = ex;
                if (local.exists()) local.delete();
                if (attempt < 3) {
                    try { Thread.sleep(attempt * 2000L); }
                    catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new Exception("Sincronizzazione interrotta.");
                    }
                }
            }
        }
        String message = last == null ? "" : String.valueOf(last.getMessage());
        String lower = message.toLowerCase(Locale.ROOT);
        if (lower.contains("unexpected end of json input") || lower.contains("failed to open source object")) {
            throw new Exception("Il cloud ha interrotto temporaneamente il download. Riprova la sincronizzazione tra poco.");
        }
        throw new Exception(message == null || message.trim().isEmpty() ? "Download cloud non riuscito." : message);
    }'''
r = replace_block(r, '    public static void copyFromRemote(Context context, String remote, File local) throws Exception {', copy_remote, 'resilient cloud copy')
RCLONE.write_text(r, encoding='utf-8')


# ---------------------------------------------------------------------------
# 4. SYNC UI AND FLOW: phase 1 is the first real long operation, not an invisible
#    setup phase. No fake percentage. A transient full-snapshot refresh failure
#    no longer prevents the proven incremental pull/upload path from running.
#    If the snapshot remains unavailable after retries, report that explicitly.
# ---------------------------------------------------------------------------
c = CLOUD.read_text(encoding='utf-8')
sync42 = r'''    public static void syncInteractiveR42(Activity activity, SharedPreferences prefs) {
        LinearLayout box = new LinearLayout(activity);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(activity, 22), dp(activity, 14), dp(activity, 22), dp(activity, 10));

        TextView phase = new TextView(activity);
        phase.setText("Fase 1 di 4");
        phase.setTextSize(16);
        phase.setTextColor(Color.rgb(55, 68, 65));
        box.addView(phase);

        TextView detail = new TextView(activity);
        detail.setText("Ricerca della copia Windows più recente...");
        detail.setTextSize(15);
        detail.setTextColor(Color.rgb(45, 58, 55));
        detail.setPadding(0, dp(activity, 8), 0, dp(activity, 12));
        box.addView(detail);

        android.widget.ProgressBar progress = new android.widget.ProgressBar(activity, null, android.R.attr.progressBarStyleHorizontal);
        progress.setIndeterminate(true);
        box.addView(progress, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(activity, 18)));

        AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("Sincronizzazione Dossier")
                .setView(box)
                .setCancelable(false)
                .create();
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

                update.accept("Fase 1 di 4", "Ricerca della copia Windows più recente...");
                boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
                int snapshotUpdated = 0;
                String snapshotWarning = "";
                if (snapshotSafe) {
                    try {
                        snapshotUpdated = r36RefreshLatestCommittedSnapshot(activity, prefs, cfg);
                    } catch (Exception snapshotError) {
                        snapshotWarning = r42SyncMessage(snapshotError);
                    }
                }

                update.accept("Fase 2 di 4", "Ricezione delle modifiche dal Dossier...");
                int received = pullRemoteChanges(activity, prefs, cfg, false);

                update.accept("Fase 3 di 4", "Invio delle modifiche locali...");
                int sent = uploadPendingChanges(activity, prefs, cfg);

                update.accept("Fase 4 di 4", "Verifica finale della sincronizzazione...");
                checkCompletionConsumed(activity, prefs, cfg);
                cfg.put("lastSyncAt", Instant.now().toString());
                saveConfig(prefs, cfg);

                String result = sent + " inviate · " + received + " ricevute";
                if (snapshotUpdated > 0) result += " · archivio Windows aggiornato";
                if (!snapshotWarning.isEmpty()) result += "\n\nAttenzione: " + snapshotWarning;
                final String message = result;
                activity.runOnUiThread(() -> {
                    if (dialog.isShowing()) dialog.dismiss();
                    new AlertDialog.Builder(activity)
                            .setTitle("Sincronizzazione completata")
                            .setMessage(message)
                            .setPositiveButton("CHIUDI", null)
                            .show();
                });
            } catch (Exception ex) {
                final String message = r42SyncMessage(ex);
                activity.runOnUiThread(() -> {
                    if (dialog.isShowing()) dialog.dismiss();
                    new AlertDialog.Builder(activity)
                            .setTitle("Sincronizzazione non completata")
                            .setMessage(message)
                            .setPositiveButton("CHIUDI", null)
                            .show();
                });
            }
        });
    }

    private static String r42SyncMessage(Exception ex) {
        String message = ex == null ? "" : String.valueOf(ex.getMessage()).trim();
        String lower = message.toLowerCase(Locale.ROOT);
        if (lower.contains("unexpected end of json input") || lower.contains("failed to open source object")) {
            return "Il servizio cloud ha interrotto temporaneamente il trasferimento. Riprova la sincronizzazione tra poco.";
        }
        if (message.length() > 500) message = message.substring(message.length() - 500);
        return message.isEmpty() ? "Operazione cloud non riuscita." : message;
    }'''
# Insert R42 immediately before R41 so all historical wrappers can route forward.
marker = '    public static void syncInteractiveR41(Activity activity, SharedPreferences prefs) {'
if marker not in c:
    raise SystemExit('R42 failed: R41 sync marker missing')
c = c.replace(marker, sync42 + '\n\n' + marker, 1)
# Route every predecessor wrapper/call that currently targets R41 to R42.
c = c.replace('syncInteractiveR41(activity, prefs);', 'syncInteractiveR42(activity, prefs);')
CLOUD.write_text(c, encoding='utf-8')


# 5. Version identity.
g = GRADLE.read_text(encoding='utf-8')
g = g.replace('versionCode 41', 'versionCode 42', 1)
g = g.replace('versionName "1.0.0-android-r41-realdevice-final-fixes-test"', 'versionName "1.0.0-android-r42-realdevice-landscape-graph-sync-final-test"', 1)
GRADLE.write_text(g, encoding='utf-8')

print('R42 real-device landscape, graph-axis and sync fixes applied')
