from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
s = MAIN.read_text(encoding='utf-8')
marker = '    private void renderBackup() {'
if marker not in s:
    raise SystemExit('R27 sections patch failed: backup marker missing')

methods = r'''    private void renderCronologia() {
        JSONArray rows = R27ExactWindows.timeline(prefs);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Cronologia clinica"));
        intro.addView(labelValue("Eventi ricostruiti dal Dossier", String.valueOf(rows.length())));
        intro.addView(text("Comprende documenti, diagnosi, terapie, Agenda e rilevazioni con data presenti nel backup Windows.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));
        if (rows.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessun evento clinico datato presente.", 13, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }
        int max = Math.min(rows.length(), 150);
        for (int i = 0; i < max; i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            LinearLayout c = card();
            c.addView(text(row.optString("kind", "Evento"), 12, GREEN_DARK, true));
            c.addView(text(row.optString("title", "Evento"), 15, TEXT, true));
            if (!row.optString("date", "").isEmpty()) c.addView(labelValue("Data", row.optString("date", "")));
            content.addView(c, matchWrapBottom(8));
        }
    }

    private void renderEsenzioni() { r27RenderRecords("Esenzioni", R27ExactWindows.exemptions(prefs), "Esenzione"); }
    private void renderDiagnosi() { r27RenderRecords("Diagnosi", R27ExactWindows.diagnoses(prefs), "Diagnosi"); }
    private void renderTerapie() { r27RenderRecords("Terapie", R27ExactWindows.therapies(prefs), "Terapia"); }
    private void renderMedici() { r27RenderRecords("Medici e specialisti", R27ExactWindows.doctors(prefs), "Medico / specialista"); }
    private void renderAgenda() { r27RenderRecords("Agenda", R27ExactWindows.calendarEvents(prefs), "Evento"); }

    private void r27RenderRecords(String titleText, JSONArray rows, String fallback) {
        LinearLayout intro = card();
        intro.addView(sectionHeader(titleText));
        intro.addView(labelValue("Elementi", String.valueOf(rows.length())));
        content.addView(intro, matchWrapBottom(14));
        if (rows.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessun elemento presente nel backup Windows per questo profilo.", 13, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }
        int max = Math.min(rows.length(), 180);
        for (int i = 0; i < max; i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            LinearLayout c = card();
            c.addView(text(R27ExactWindows.label(row, fallback), 16, TEXT, true));
            String detail = R27ExactWindows.detail(row);
            if (!detail.isEmpty()) c.addView(text(detail, 13, GREEN_DARK, true));
            java.util.Iterator<String> keys = row.keys();
            int details = 0;
            while (keys.hasNext() && details < 10) {
                String key = keys.next();
                if (key.startsWith("_") || "id".equalsIgnoreCase(key) || "profileId".equalsIgnoreCase(key)) continue;
                Object value = row.opt(key);
                if (value == null || value == JSONObject.NULL || value instanceof JSONObject || value instanceof JSONArray) continue;
                String textValue = String.valueOf(value).trim();
                if (textValue.isEmpty()) continue;
                c.addView(labelValue(key, textValue));
                details++;
            }
            content.addView(c, matchWrapBottom(9));
        }
    }

    private void renderConfronta() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Confronta"));
        intro.addView(text("Confronto tra le ultime due rilevazioni Windows dello stesso parametro.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));
        r27Comparison("Peso", R27ExactWindows.measurementsOf(prefs, "weight"), "value");
        r27Comparison("Saturazione", R27ExactWindows.measurementsOf(prefs, "spo2"), "value");
        r27Comparison("Glicemia", R27ExactWindows.measurementsOf(prefs, "glucose"), "value");
        r27Comparison("Frequenza cardiaca", R27ExactWindows.measurementsOf(prefs, "heart_rate"), "value");
        r27Comparison("Pressione sistolica", R27ExactWindows.measurementsOf(prefs, "blood_pressure"), "systolic");
        r27Comparison("Pressione diastolica", R27ExactWindows.measurementsOf(prefs, "blood_pressure"), "diastolic");
    }

    private void r27Comparison(String name, JSONArray rows, String key) {
        if (rows.length() < 2) return;
        JSONObject previous = rows.optJSONObject(rows.length() - 2);
        JSONObject latest = rows.optJSONObject(rows.length() - 1);
        double a = R27ExactWindows.number(previous, key);
        double b = R27ExactWindows.number(latest, key);
        if (Double.isNaN(a) || Double.isNaN(b)) return;
        LinearLayout c = card();
        c.addView(sectionHeader(name));
        c.addView(labelValue("Precedente", formatR26Number(a)));
        c.addView(labelValue("Ultima", formatR26Number(b)));
        c.addView(labelValue("Differenza", (b - a >= 0 ? "+" : "") + formatR26Number(b - a)));
        content.addView(c, matchWrapBottom(10));
    }

    private void renderGrafici() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Grafici"));
        intro.addView(text("Grafici costruiti sui dati esatti di misurazioni.json e sui valori di laboratorio contenuti nell'indice documenti Windows.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));

        r27Chart("Percorso peso", R27ExactWindows.measurementsOf(prefs, "weight"), "value");
        r27Chart("Saturazione ossigeno", R27ExactWindows.measurementsOf(prefs, "spo2"), "value");
        r27Chart("Glicemia domestica", R27ExactWindows.measurementsOf(prefs, "glucose"), "value");
        JSONArray pressure = R27ExactWindows.measurementsOf(prefs, "blood_pressure");
        r27Chart("Pressione sistolica", pressure, "systolic");
        r27Chart("Pressione diastolica", pressure, "diastolic");
        r27Chart("Frequenza cardiaca", pressure, "heartRate");
        r27Chart("Frequenza cardiaca", R27ExactWindows.measurementsOf(prefs, "heart_rate"), "value");

        JSONArray params = R27ExactWindows.availableLabParameters(prefs);
        JSONObject profilePrefs = R27ExactWindows.profilePreferences(prefs);
        JSONArray selected = profilePrefs.optJSONArray("selectedGraphs");
        int labShown = 0;
        for (int i = 0; i < params.length() && labShown < 12; i++) {
            JSONObject p = params.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "");
            if (selected != null && selected.length() > 0 && !r27ArrayContains(selected, id)) continue;
            JSONArray series = R27ExactWindows.labSeries(prefs, id);
            if (series.length() < 2) continue;
            String unit = p.optString("unit", "");
            r27Chart(p.optString("name", id) + (unit.isEmpty() ? "" : " (" + unit + ")"), series, "value");
            labShown++;
        }
    }

    private boolean r27ArrayContains(JSONArray array, String value) {
        if (array == null) return false;
        for (int i = 0; i < array.length(); i++) if (value.equals(array.optString(i, ""))) return true;
        return false;
    }

    private void r27Chart(String titleText, JSONArray rows, String key) {
        if (rows == null || rows.length() == 0) return;
        R26ChartView chart = new R26ChartView(this, rows, GREEN, key);
        if (!chart.hasData()) return;
        LinearLayout c = card();
        c.addView(sectionHeader(titleText));
        c.addView(chart, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(230)));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderMonitoraggio() {
        JSONArray measurements = R27ExactWindows.measurements(prefs);
        JSONArray journeys = R27ExactWindows.weightJourneys(prefs);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Monitoraggio"));
        intro.addView(labelValue("Rilevazioni", String.valueOf(measurements.length())));
        intro.addView(labelValue("Percorsi peso", String.valueOf(journeys.length())));
        content.addView(intro, matchWrapBottom(14));
        r27RenderRecords("Peso", R27ExactWindows.measurementsOf(prefs, "weight"), "Peso");
        r27RenderRecords("Pressione arteriosa", R27ExactWindows.measurementsOf(prefs, "blood_pressure"), "Pressione");
        r27RenderRecords("Saturazione", R27ExactWindows.measurementsOf(prefs, "spo2"), "Saturazione");
        r27RenderRecords("Glicemia", R27ExactWindows.measurementsOf(prefs, "glucose"), "Glicemia");
        r27RenderRecords("Frequenza cardiaca", R27ExactWindows.measurementsOf(prefs, "heart_rate"), "Frequenza cardiaca");
        if (journeys.length() > 0) r27RenderRecords("Percorso peso", journeys, "Percorso peso");
    }

'''
s = s.replace(marker, methods + marker, 1)
MAIN.write_text(s, encoding='utf-8')
print('R27 clinical sections patch applied')
