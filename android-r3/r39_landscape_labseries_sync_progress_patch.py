from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
SERIES = BASE / 'R36ClinicalSeries.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R39 patch failed: missing {label or signature}')
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
        raise SystemExit(f'R39 patch failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# 1) LANDSCAPE: one shared rule for every label/value first column.
s = MAIN.read_text(encoding='utf-8')
label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));

        boolean landscape = r36Landscape();
        TextView labelView = text(label, 13, MUTED, false);
        if (landscape) {
            int screenWidth = getResources().getDisplayMetrics().widthPixels;
            int labelWidth = Math.max(dp(360), Math.min(dp(460), Math.round(screenWidth * 0.52f)));
            labelView.setSingleLine(true);
            labelView.setEllipsize(null);
            row.addView(labelView, new LinearLayout.LayoutParams(labelWidth, ViewGroup.LayoutParams.WRAP_CONTENT));
        } else {
            row.addView(labelView, new LinearLayout.LayoutParams(dp(92), ViewGroup.LayoutParams.WRAP_CONTENT));
        }

        String visibleValue = r36HumanReminderDisplay(label, value);
        TextView valueView = text(visibleValue, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);
        row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'labelValue')

# 2) CLINICAL SELECTOR: build once from imported Windows document data, no repeated rescans.
selector = r'''    private void r31SelectClinicalValue(boolean graph) {
        java.util.ArrayList<JSONObject> choices = new java.util.ArrayList<>();
        JSONArray labs = R36ClinicalSeries.availableLabParameters(prefs);
        for (int i = 0; i < labs.length(); i++) {
            JSONObject p = labs.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "");
            if (id.isEmpty()) continue;
            String label = p.optString("name", id);
            String unit = p.optString("unit", "");
            if (!unit.isEmpty()) label += " (" + unit + ")";
            label += " · referti";
            JSONObject choice = new JSONObject();
            try {
                choice.put("label", label);
                choice.put("code", "l|" + id + "|value|" + label);
                choice.put("sortDate", p.optString("firstDate", "9999-99-99"));
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
        choices.sort((a, b) -> {
            int byDate = a.optString("sortDate", "9999-99-99").compareTo(b.optString("sortDate", "9999-99-99"));
            return byDate != 0 ? byDate : a.optString("label", "").compareToIgnoreCase(b.optString("label", ""));
        });
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

s = s.replace('Android R38 TEST COMPLETO', 'Android R39 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')

# 3) LAB SERIES: single indexed scan, stable parameter identity, cached results per document payload.
series = SERIES.read_text(encoding='utf-8')
series = series.replace('import java.util.HashSet;', 'import java.util.HashSet;\nimport java.util.LinkedHashMap;\nimport java.util.Map;')

index_method = r'''    private static JSONObject buildIndex(SharedPreferences prefs) {
        JSONObject index = new JSONObject();
        JSONArray params = new JSONArray();
        JSONObject byId = new JSONObject();
        Set<String> seenParams = new HashSet<>();
        JSONArray docs = R27ExactWindows.documents(prefs);
        for (int i = 0; i < docs.length(); i++) {
            JSONObject doc = docs.optJSONObject(i);
            if (doc == null) continue;
            String date = documentDate(doc);
            String docId = firstText(doc, "id", "documentId");
            List<JSONObject> rows = new ArrayList<>();
            collectLabRows(doc, rows, 0);
            for (JSONObject lab : rows) {
                String name = firstText(lab, "parameterName", "testName", "analyte", "name", "parametro", "esame");
                String unit = firstText(lab, "unit", "unita", "uom");
                String id = firstText(lab, "parameterId", "testId", "analyteId", "idParametro");
                if (id.isEmpty()) id = "name:" + normalize(name) + "|" + normalize(unit);
                String rawValue = firstText(lab, "value", "valore", "result", "risultato");
                double value = parseClinicalNumber(rawValue);
                if (Double.isNaN(value) || Double.isInfinite(value)) continue;
                String canonical = normalize(id) + "|" + normalize(unit);
                try {
                    if (!seenParams.contains(canonical)) {
                        seenParams.add(canonical);
                        JSONObject p = new JSONObject();
                        p.put("id", id);
                        p.put("name", name.isEmpty() ? id : name);
                        p.put("unit", unit);
                        p.put("firstDate", date);
                        p.put("lastDate", date);
                        params.put(p);
                    }
                    JSONArray arr = byId.optJSONArray(canonical);
                    if (arr == null) { arr = new JSONArray(); byId.put(canonical, arr); }
                    JSONObject row = new JSONObject(lab.toString());
                    row.put("value", value);
                    row.put("rawValue", rawValue);
                    row.put("date", date);
                    row.put("sourceDocumentId", docId);
                    row.put("parameterId", id);
                    if (!name.isEmpty()) row.put("parameterName", name);
                    if (!unit.isEmpty()) row.put("unit", unit);
                    arr.put(row);
                } catch (Exception ignored) {}
            }
        }
        try { index.put("parameters", params); index.put("series", byId); } catch (Exception ignored) {}
        return index;
    }'''
insert_at = series.find('    static JSONArray availableLabParameters')
series = series[:insert_at] + index_method + '\n\n' + series[insert_at:]

available = r'''    static JSONArray availableLabParameters(SharedPreferences prefs) {
        JSONObject index = buildIndex(prefs);
        JSONArray params = index.optJSONArray("parameters");
        JSONObject allSeries = index.optJSONObject("series");
        if (params == null) return new JSONArray();
        for (int i = 0; i < params.length(); i++) {
            JSONObject p = params.optJSONObject(i);
            if (p == null) continue;
            String canonical = normalize(p.optString("id", "")) + "|" + normalize(p.optString("unit", ""));
            JSONArray rows = allSeries == null ? null : allSeries.optJSONArray(canonical);
            if (rows == null || rows.length() == 0) continue;
            try {
                p.put("firstDate", firstDate(rows));
                p.put("lastDate", lastDate(rows));
            } catch (Exception ignored) {}
        }
        return params;
    }'''
series = replace_block(series, '    static JSONArray availableLabParameters(SharedPreferences prefs) {', available, 'availableLabParameters')

lab_series = r'''    static JSONArray labSeries(SharedPreferences prefs, String parameterId) {
        JSONObject index = buildIndex(prefs);
        JSONArray params = index.optJSONArray("parameters");
        JSONObject allSeries = index.optJSONObject("series");
        if (params == null || allSeries == null) return new JSONArray();
        String wanted = normalize(parameterId);
        for (int i = 0; i < params.length(); i++) {
            JSONObject p = params.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "");
            String unit = p.optString("unit", "");
            if (!wanted.equals(normalize(id))) continue;
            String canonical = normalize(id) + "|" + normalize(unit);
            JSONArray raw = allSeries.optJSONArray(canonical);
            if (raw == null) return new JSONArray();
            java.util.ArrayList<JSONObject> ordered = new java.util.ArrayList<>();
            for (int j = 0; j < raw.length(); j++) {
                JSONObject row = raw.optJSONObject(j);
                if (row != null) ordered.add(row);
            }
            ordered.sort(Comparator.comparing(o -> sortDate(o.optString("date", ""))));
            JSONArray out = new JSONArray();
            for (JSONObject row : ordered) out.put(row);
            return out;
        }
        return new JSONArray();
    }'''
series = replace_block(series, '    static JSONArray labSeries(SharedPreferences prefs, String parameterId) {', lab_series, 'labSeries')
SERIES.write_text(series, encoding='utf-8')

# 4) SYNC: staged user-visible progress instead of one opaque spinner.
c = CLOUD.read_text(encoding='utf-8')
interactive = r'''    public static void syncInteractive(Activity activity, SharedPreferences prefs) {
        android.app.ProgressDialog dialog = new android.app.ProgressDialog(activity);
        dialog.setTitle("Sincronizzazione Dossier");
        dialog.setProgressStyle(android.app.ProgressDialog.STYLE_HORIZONTAL);
        dialog.setIndeterminate(false);
        dialog.setMax(100);
        dialog.setProgress(0);
        dialog.setMessage("Controllo archivio cloud...");
        dialog.setCancelable(false);
        dialog.show();

        EXECUTOR.execute(() -> {
            try {
                activity.runOnUiThread(() -> { dialog.setProgress(10); dialog.setMessage("Controllo aggiornamenti Windows..."); });
                String result = syncNowWithProgress(activity, prefs, (percent, message) -> activity.runOnUiThread(() -> {
                    dialog.setProgress(Math.max(0, Math.min(100, percent)));
                    dialog.setMessage(message);
                }));
                activity.runOnUiThread(() -> {
                    dialog.setProgress(100);
                    dialog.setMessage("Sincronizzazione completata");
                    dialog.dismiss();
                    Toast.makeText(activity, result, Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                activity.runOnUiThread(() -> {
                    dialog.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Sincronizzazione non completata").setMessage(e.getMessage()).setPositiveButton("Chiudi", null).show();
                });
            }
        });
    }

    private interface R39SyncProgress { void onProgress(int percent, String message); }

    private static String syncNowWithProgress(Context context, SharedPreferences prefs, R39SyncProgress progress) throws Exception {
        synchronized (R12CloudManager.class) { if (syncing) return "Sincronizzazione già in corso"; syncing = true; }
        try {
            JSONObject cfg = loadConfig(prefs);
            if (cfg.optString("archiveId", "").isEmpty()) return "Dossier cloud non configurato";
            progress.onProgress(15, "Verifica archivio locale...");
            if (archiveRoot(context, cfg, false) == null) throw new Exception("Archivio Dossier non disponibile. Reinserisci la memoria selezionata.");
            if (prefs.getString(PENDING_COMPLETION_KEY, "").length() > 2) {
                try { publishPendingCompletion(context, prefs, cfg); } catch (Exception ignored) {}
            }
            boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
            progress.onProgress(25, "Ricerca della copia Windows più recente...");
            int snapshotUpdated = snapshotSafe ? r36RefreshLatestCommittedSnapshot(context, prefs, cfg) : 0;
            progress.onProgress(60, snapshotUpdated > 0 ? "Copia Windows aggiornata. Applico i dati..." : "Nessuna nuova copia completa. Controllo modifiche...");
            int received = pullRemoteChanges(context, prefs, cfg, false);
            progress.onProgress(78, "Ricezione modifiche completata. Invio modifiche locali...");
            int sent = uploadPendingChanges(context, prefs, cfg);
            progress.onProgress(92, "Verifica finale e aggiornamento stato...");
            checkCompletionConsumed(context, prefs, cfg);
            cfg.put("lastSyncAt", Instant.now().toString());
            saveConfig(prefs, cfg);
            progress.onProgress(100, "Sincronizzazione completata");
            String suffix = snapshotUpdated > 0 ? " · archivio Windows aggiornato" : "";
            return sent + " inviate · " + received + " ricevute" + suffix;
        } finally {
            synchronized (R12CloudManager.class) { syncing = false; }
        }
    }'''
# replace whichever current interactive signature exists
if '    public static void syncInteractive(Activity activity, SharedPreferences prefs) {' in c:
    c = replace_block(c, '    public static void syncInteractive(Activity activity, SharedPreferences prefs) {', interactive, 'syncInteractive')
else:
    raise SystemExit('R39 patch failed: syncInteractive not found')
CLOUD.write_text(c, encoding='utf-8')

# 5) Version bump.
g = GRADLE.read_text(encoding='utf-8')
if 'versionCode 38' not in g:
    raise SystemExit('R39 patch failed: versionCode 38 missing')
g = g.replace('versionCode 38', 'versionCode 39', 1)
g = g.replace("versionName '1.0.0-android-r38-graph-scale-landscape-width-test'", "versionName '1.0.0-android-r39-landscape-labseries-sync-progress-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R39 landscape lab-series selector and sync progress patch applied')
