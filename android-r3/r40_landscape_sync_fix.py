from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R40 failed: missing {label or signature}')
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
        raise SystemExit(f'R40 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

s = MAIN.read_text(encoding='utf-8')
landscape = r'''    private boolean r36Landscape() {
        android.util.DisplayMetrics dm = getResources().getDisplayMetrics();
        return dm.widthPixels > dm.heightPixels
                || getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
    }'''
s = replace_block(s, '    private boolean r36Landscape() {', landscape, 'r36Landscape')

label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));

        TextView labelView = text(label, 13, MUTED, false);
        boolean landscape = r36Landscape();
        int labelWidth = dp(92);
        if (landscape) {
            android.util.DisplayMetrics dm = getResources().getDisplayMetrics();
            int available = Math.max(1, dm.widthPixels - dp(48));
            labelWidth = Math.max(dp(220), Math.min(dp(430), Math.round(available * 0.38f)));
            labelView.setSingleLine(true);
            labelView.setMaxLines(1);
            labelView.setHorizontallyScrolling(false);
            labelView.setEllipsize(null);
        }
        row.addView(labelView, new LinearLayout.LayoutParams(labelWidth, ViewGroup.LayoutParams.WRAP_CONTENT));

        String visibleValue = r36HumanReminderDisplay(label, value);
        TextView valueView = text(visibleValue, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);
        row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        if (landscape) {
            row.post(() -> {
                int rowWidth = row.getWidth();
                if (rowWidth <= 0) return;
                int target = Math.max(dp(220), Math.min(dp(430), Math.round(rowWidth * 0.38f)));
                ViewGroup.LayoutParams lp = labelView.getLayoutParams();
                if (lp != null && lp.width != target) {
                    lp.width = target;
                    labelView.setLayoutParams(lp);
                    labelView.requestLayout();
                }
            });
        }
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'labelValue')
MAIN.write_text(s, encoding='utf-8')

c = CLOUD.read_text(encoding='utf-8')
sync40 = r'''    public static void syncInteractiveR40(Activity activity, SharedPreferences prefs) {
        LinearLayout box = new LinearLayout(activity);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(activity, 22), dp(activity, 14), dp(activity, 22), dp(activity, 10));
        TextView phase = new TextView(activity);
        phase.setText("Controllo configurazione e archivio...");
        phase.setTextSize(15);
        phase.setTextColor(Color.rgb(28, 47, 43));
        box.addView(phase, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        android.widget.ProgressBar bar = new android.widget.ProgressBar(activity, null, android.R.attr.progressBarStyleHorizontal);
        bar.setIndeterminate(false);
        bar.setMax(100);
        bar.setProgress(5);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(activity, 18));
        bp.setMargins(0, dp(activity, 14), 0, dp(activity, 4));
        box.addView(bar, bp);
        TextView percent = new TextView(activity);
        percent.setText("5%");
        percent.setTextSize(13);
        percent.setTextColor(Color.DKGRAY);
        box.addView(percent);
        AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("Sincronizzazione Dossier")
                .setView(box)
                .setCancelable(false)
                .create();
        dialog.show();

        java.util.function.BiConsumer<Integer,String> update = (value, message) -> activity.runOnUiThread(() -> {
            bar.setProgress(value);
            percent.setText(value + "%");
            phase.setText(message);
        });

        EXECUTOR.execute(() -> {
            try {
                update.accept(10, "Controllo configurazione e archivio...");
                JSONObject cfg = loadConfig(prefs);
                if (cfg.optString("archiveId", "").isEmpty()) throw new Exception("Dossier cloud non configurato");
                update.accept(20, "Ricerca della copia Windows più recente...");
                boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
                int snapshotUpdated = snapshotSafe ? r36RefreshLatestCommittedSnapshot(activity, prefs, cfg) : 0;
                update.accept(65, "Ricezione delle modifiche dal Dossier...");
                int received = pullRemoteChanges(activity, prefs, cfg, false);
                update.accept(80, "Invio delle modifiche locali...");
                int sent = uploadPendingChanges(activity, prefs, cfg);
                update.accept(94, "Verifica finale della sincronizzazione...");
                checkCompletionConsumed(activity, prefs, cfg);
                cfg.put("lastSyncAt", Instant.now().toString());
                saveConfig(prefs, cfg);
                final String result = sent + " inviate · " + received + " ricevute" + (snapshotUpdated > 0 ? " · archivio Windows aggiornato" : "");
                activity.runOnUiThread(() -> {
                    bar.setProgress(100);
                    percent.setText("100%");
                    phase.setText("Sincronizzazione completata");
                    dialog.dismiss();
                    Toast.makeText(activity, "Sincronizzazione completata · " + result, Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                activity.runOnUiThread(() -> {
                    dialog.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Sincronizzazione non completata").setMessage(e.getMessage()).setPositiveButton("Chiudi", null).show();
                });
            }
        });
    }'''
marker = '    public static void syncInteractiveR39(Activity activity, SharedPreferences prefs) {'
if marker not in c:
    raise SystemExit('R40 failed: R39 sync missing')
c = c.replace(marker, sync40 + '\n\n' + marker, 1)
r39 = r'''    public static void syncInteractiveR39(Activity activity, SharedPreferences prefs) {
        syncInteractiveR40(activity, prefs);
    }'''
c = replace_block(c, marker, r39, 'syncInteractiveR39')
private_sync = r'''    private static void syncInteractive(Activity activity, SharedPreferences prefs) {
        syncInteractiveR40(activity, prefs);
    }'''
c = replace_block(c, '    private static void syncInteractive(Activity activity, SharedPreferences prefs) {', private_sync, 'cloud panel syncInteractive')
CLOUD.write_text(c, encoding='utf-8')

print('R40 landscape and sync fix applied')
