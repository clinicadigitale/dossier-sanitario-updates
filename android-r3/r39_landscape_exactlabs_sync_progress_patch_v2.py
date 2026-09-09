from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R39 v2 failed: missing {label or signature}')
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
        raise SystemExit(f'R39 v2 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


s = MAIN.read_text(encoding='utf-8')

# LANDSCAPE ONLY: portrait stays frozen. Every standard first-column label is one line.
label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));

        boolean landscape = r36Landscape();
        TextView labelView = text(label, 13, MUTED, false);
        int labelWidth;
        if (landscape) {
            int screenWidth = getResources().getDisplayMetrics().widthPixels;
            labelWidth = Math.max(dp(360), Math.min(dp(460), Math.round(screenWidth * 0.52f)));
            labelView.setSingleLine(true);
            labelView.setHorizontallyScrolling(false);
        } else {
            labelWidth = dp(92);
        }
        row.addView(labelView, new LinearLayout.LayoutParams(labelWidth, ViewGroup.LayoutParams.WRAP_CONTENT));

        String visibleValue = r36HumanReminderDisplay(label, value);
        TextView valueView = text(visibleValue, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);
        row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'labelValue')

# EXACT WINDOWS LAB DATA: no second parser, no recursive rescans, no invented values.
selector = r'''    private void r31SelectClinicalValue(boolean graph) {
        java.util.ArrayList<JSONObject> choices = new java.util.ArrayList<>();

        JSONArray labs = R27ExactWindows.availableLabParameters(prefs);
        for (int i = 0; i < labs.length(); i++) {
            JSONObject p = labs.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "");
            if (id.isEmpty()) continue;
            String label = p.optString("name", id);
            String unit = p.optString("unit", "");
            if (!unit.isEmpty()) label += " (" + unit + ")";
            label += " · referti";
            r36AddClinicalChoice(choices, label, "l|" + id + "|value|" + label, R27ExactWindows.labSeries(prefs, id));
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
s = replace_block(s, '    private void r31SelectClinicalValue(boolean graph) {', selector, 'clinical selector')

series = r'''    private JSONArray r31SeriesForChoice(String choice) {
        String[] p = choice == null ? new String[0] : choice.split("\\|", 4);
        if (p.length < 4) return new JSONArray();
        if ("l".equals(p[0])) return R27ExactWindows.labSeries(prefs, p[1]);
        if ("u".equals(p[0])) return R27ExactWindows.measurementsOf(prefs, p[1]);
        if ("m".equals(p[0])) {
            if ("glucose".equalsIgnoreCase(p[1])) {
                JSONArray params = R27ExactWindows.availableLabParameters(prefs);
                for (int i = 0; i < params.length(); i++) {
                    JSONObject x = params.optJSONObject(i);
                    if (x == null) continue;
                    String name = x.optString("name", "").toLowerCase(Locale.ROOT);
                    if (name.contains("glicem") || name.contains("glucos")) {
                        JSONArray exact = R27ExactWindows.labSeries(prefs, x.optString("id", ""));
                        if (exact.length() > 0) return exact;
                    }
                }
            }
            return R27ExactWindows.measurementsOf(prefs, p[1]);
        }
        return new JSONArray();
    }'''
if '    private JSONArray r31SeriesForChoice(String choice) {' in s:
    s = replace_block(s, '    private JSONArray r31SeriesForChoice(String choice) {', series, 'series choice')
elif '    private JSONArray r31SeriesForChoice(String choice){' in s:
    s = replace_block(s, '    private JSONArray r31SeriesForChoice(String choice){', series, 'series choice')
else:
    raise SystemExit('R39 v2 failed: series choice not found')

s = s.replace('Android R38 TEST COMPLETO', 'Android R39 TEST COMPLETO', 1)
# All existing UI sync buttons now use the staged R39 path.
s = s.replace('R12CloudManager.syncInteractiveR31(this, prefs)', 'R12CloudManager.syncInteractiveR39(this, prefs)')
MAIN.write_text(s, encoding='utf-8')

# SYNC PROGRESS: replace the existing R31 interactive wrapper, keeping sync engine intact.
c = CLOUD.read_text(encoding='utf-8')
sync_methods = r'''    public static void syncInteractiveR39(Activity activity, SharedPreferences prefs) {
        ProgressDialog dialog = new ProgressDialog(activity);
        dialog.setTitle("Sincronizzazione Dossier");
        dialog.setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);
        dialog.setIndeterminate(false);
        dialog.setMax(100);
        dialog.setProgress(0);
        dialog.setMessage("Controllo archivio cloud...");
        dialog.setCancelable(false);
        dialog.show();
        EXECUTOR.execute(() -> {
            try {
                activity.runOnUiThread(() -> { dialog.setProgress(10); dialog.setMessage("Controllo configurazione e archivio..."); });
                JSONObject cfg = loadConfig(prefs);
                if (cfg.optString("archiveId", "").isEmpty()) throw new Exception("Dossier cloud non configurato");
                activity.runOnUiThread(() -> { dialog.setProgress(20); dialog.setMessage("Ricerca della copia Windows più recente..."); });
                boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
                int snapshotUpdated = snapshotSafe ? r36RefreshLatestCommittedSnapshot(activity, prefs, cfg) : 0;
                activity.runOnUiThread(() -> { dialog.setProgress(60); dialog.setMessage("Ricezione delle modifiche dal Dossier..."); });
                int received = pullRemoteChanges(activity, prefs, cfg, false);
                activity.runOnUiThread(() -> { dialog.setProgress(78); dialog.setMessage("Invio delle modifiche locali..."); });
                int sent = uploadPendingChanges(activity, prefs, cfg);
                activity.runOnUiThread(() -> { dialog.setProgress(92); dialog.setMessage("Verifica finale della sincronizzazione..."); });
                checkCompletionConsumed(activity, prefs, cfg);
                cfg.put("lastSyncAt", Instant.now().toString());
                saveConfig(prefs, cfg);
                final String result = sent + " inviate · " + received + " ricevute" + (snapshotUpdated > 0 ? " · archivio Windows aggiornato" : "");
                activity.runOnUiThread(() -> {
                    dialog.setProgress(100);
                    dialog.setMessage("Sincronizzazione completata");
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
    }

    public static void syncInteractiveR31(Activity activity, SharedPreferences prefs) {
        syncInteractiveR39(activity, prefs);
    }'''
c = replace_block(c, '    public static void syncInteractiveR31(Activity activity, SharedPreferences prefs) {', sync_methods, 'syncInteractiveR31')
CLOUD.write_text(c, encoding='utf-8')

# VERSION
g = GRADLE.read_text(encoding='utf-8')
if 'versionCode 38' not in g:
    raise SystemExit('R39 v2 failed: versionCode 38 missing')
g = g.replace('versionCode 38', 'versionCode 39', 1)
g = g.replace("versionName '1.0.0-android-r38-graph-scale-landscape-width-test'", "versionName '1.0.0-android-r39-landscape-exactlabs-sync-progress-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R39 v2 exact Windows labValues, landscape and sync progress patch applied')
