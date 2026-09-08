from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R37 patch failed: missing {label}')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R37 patch failed: missing {label or signature}')
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
        raise SystemExit(f'R37 patch failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


s = MAIN.read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# 1. PORTRAIT IS FROZEN.
# Restore exactly the R34/R35 portrait row geometry (92 dp label column), while
# making the landscape label column much wider and single-line. No portrait
# spacing, width or wrapping change is allowed here.
# ---------------------------------------------------------------------------
label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));

        boolean landscape = r36Landscape();
        int labelWidth;
        TextView labelView = text(label, 13, MUTED, false);
        if (landscape) {
            int screenWidth = getResources().getDisplayMetrics().widthPixels;
            labelWidth = Math.max(dp(280), Math.min(dp(320), Math.round(screenWidth * 0.46f)));
            labelView.setSingleLine(true);
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
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'frozen portrait labelValue')

# Keep the portrait content padding exactly at the old 16 dp. Landscape gets a
# little more usable width instead of the R36-added 24 dp side padding.
old_side = '        int r36ContentSide = r36Landscape() ? dp(24) : dp(16);'
require(s, old_side, 'R36 content side padding')
s = s.replace(old_side, '        int r36ContentSide = r36Landscape() ? dp(12) : dp(16);', 1)

# ---------------------------------------------------------------------------
# 2. GRAPHS.
# Laboratory graphs are sourced from Windows document labValues. In particular,
# a saved legacy glucose graph is migrated to report-derived glycaemia instead
# of continuing to show manual/home measurements.
# ---------------------------------------------------------------------------
selector = r'''    private void r31SelectClinicalValue(boolean graph) {
        java.util.ArrayList<JSONObject> choices = new java.util.ArrayList<>();

        JSONArray labs = R37ClinicalSeries.availableLabParameters(prefs);
        for (int i = 0; i < labs.length(); i++) {
            JSONObject p = labs.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "");
            if (id.isEmpty()) continue;
            String label = p.optString("name", id);
            String unit = p.optString("unit", "");
            if (!unit.isEmpty()) label += " (" + unit + ")";
            label += " · referti";
            r36AddClinicalChoice(choices, label, "l|" + id + "|value|" + label, R37ClinicalSeries.labSeries(prefs, id));
        }

        r36AddClinicalChoice(choices, "Peso", "u|weight|value|Peso", R27ExactWindows.measurementsOf(prefs, "weight"));
        r36AddClinicalChoice(choices, "Saturazione ossigeno", "u|spo2|value|Saturazione ossigeno", R27ExactWindows.measurementsOf(prefs, "spo2"));
        if (!graph) r36AddClinicalChoice(choices, "Glicemia manuale", "u|glucose|value|Glicemia manuale", R27ExactWindows.measurementsOf(prefs, "glucose"));
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
s = replace_block(s, '    private void r31SelectClinicalValue(boolean graph) {', selector, 'R37 clinical selector')

series_method = r'''    private JSONArray r31SeriesForChoice(String choice) {
        String[] p = choice == null ? new String[0] : choice.split("\\|", 4);
        if (p.length < 4) return new JSONArray();
        if ("l".equals(p[0])) return R37ClinicalSeries.labSeries(prefs, p[1]);
        if (("m".equals(p[0]) || "u".equals(p[0])) && "glucose".equalsIgnoreCase(p[1])) {
            JSONArray reports = R37ClinicalSeries.glycemiaFromReports(prefs);
            if (reports.length() > 0) return reports;
            return "u".equals(p[0]) ? R27ExactWindows.measurementsOf(prefs, p[1]) : new JSONArray();
        }
        if ("u".equals(p[0])) return R27ExactWindows.measurementsOf(prefs, p[1]);
        if ("m".equals(p[0])) return R27ExactWindows.measurementsOf(prefs, p[1]);
        return new JSONArray();
    }'''
s = replace_block(s, '    private JSONArray r31SeriesForChoice(String choice) {', series_method, 'R37 report series')

choice_label = r'''    private String r31ChoiceLabel(String choice) {
        String[] p = choice == null ? new String[0] : choice.split("\\|", 4);
        if (p.length < 4) return "Parametro";
        if (("m".equals(p[0]) || "u".equals(p[0])) && "glucose".equalsIgnoreCase(p[1])
                && R37ClinicalSeries.glycemiaFromReports(prefs).length() > 0) {
            return "Glicemia · referti";
        }
        return p[3];
    }'''
s = replace_block(s, '    private String r31ChoiceLabel(String choice) {', choice_label, 'R37 graph label')

# ---------------------------------------------------------------------------
# 3. AGENDA.
# Reminder timings are useful only in the edit screen. The ordinary Agenda card
# must not repeat them. Document-original behavior from R36 remains untouched.
# ---------------------------------------------------------------------------
agenda_reminders = '''            JSONArray reminders = row.optJSONArray("reminders");\n            if (reminders != null && reminders.length() > 0) c.addView(labelValue("Avvisi", r31JoinArray(reminders)));\n'''
require(s, agenda_reminders, 'Agenda reminder display')
s = s.replace(agenda_reminders, '', 1)

# ---------------------------------------------------------------------------
# 4. Version marker only. All other R35/R36 working sectors remain frozen.
# ---------------------------------------------------------------------------
g = GRADLE.read_text(encoding='utf-8')
require(g, 'versionCode 36', 'versionCode 36')
require(g, "versionName '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test'", 'R36 versionName')
g = g.replace('versionCode 36', 'versionCode 37', 1)
g = g.replace("versionName '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test'",
              "versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

# Visible release marker.
require(s, 'Android R36 TEST COMPLETO', 'R36 release marker')
s = s.replace('Android R36 TEST COMPLETO', 'Android R37 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')

print('R37 frozen portrait, wider landscape, report graphs and Agenda cleanup patch applied')
