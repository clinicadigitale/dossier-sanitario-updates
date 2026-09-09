from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
SERIES = BASE / 'R40ClinicalSeries.java'
GRADLE = Path('android-r3/app/build.gradle')

SERIES.write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class R40ClinicalSeries {
    private static final Pattern NUMBER = Pattern.compile("[-+]?\\d+(?:[\\.,]\\d+)?");
    private R40ClinicalSeries() {}

    static JSONArray availableLabParameters(SharedPreferences prefs) {
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
        for (JSONObject p : parameters.values()) {
            if (labSeries(prefs, p.optString("id", "")).length() > 0) out.put(p);
        }
        return out;
    }

    static JSONArray labSeries(SharedPreferences prefs, String parameterId) {
        List<JSONObject> rows = new ArrayList<>();
        JSONArray docs = R27ExactWindows.documents(prefs);
        for (int i = 0; i < docs.length(); i++) {
            JSONObject doc = docs.optJSONObject(i);
            if (doc == null) continue;
            JSONArray labs = doc.optJSONArray("labValues");
            if (labs == null) continue;
            for (int j = 0; j < labs.length(); j++) {
                JSONObject lab = labs.optJSONObject(j);
                if (lab == null || explicitInvalid(lab)) continue;
                if (!parameterId.equals(lab.optString("parameterId", ""))) continue;
                double value = canonicalValue(lab);
                if (!Double.isFinite(value)) continue;
                try {
                    JSONObject row = new JSONObject(lab.toString());
                    row.put("value", value);
                    String unit = canonicalUnit(lab);
                    if (!unit.isEmpty()) row.put("unit", unit);
                    row.put("date", doc.optString("clinicalDate", doc.optString("issueDate", doc.optString("createdAt", ""))));
                    rows.add(row);
                } catch (Exception ignored) {}
            }
        }
        rows.sort(Comparator.comparing(o -> sortDate(o.optString("date", ""))));
        rows = removeObviousParserExplosions(rows);
        JSONArray out = new JSONArray();
        for (JSONObject row : rows) out.put(row);
        return out;
    }

    static double canonicalValue(JSONObject lab) {
        if (lab == null) return Double.NaN;
        String[] preferred = {"normalizedValue", "canonicalValue", "numericValue", "graphValue", "value", "valore", "result", "risultato"};
        for (String key : preferred) {
            double v = parse(lab.opt(key));
            if (Double.isFinite(v)) return v;
        }
        return Double.NaN;
    }

    private static String canonicalUnit(JSONObject lab) {
        String[] keys = {"normalizedUnit", "canonicalUnit", "unit"};
        for (String key : keys) {
            String s = lab.optString(key, "").trim();
            if (!s.isEmpty()) return s;
        }
        return "";
    }

    static boolean explicitInvalid(JSONObject lab) {
        String[] bools = {"validForGraph", "graphValid", "isValid", "valid", "recognized"};
        for (String key : bools) if (lab.has(key) && !lab.optBoolean(key, true)) return true;
        String status = (lab.optString("status", "") + " " + lab.optString("validationStatus", "") + " " + lab.optString("parseStatus", "")).toLowerCase(Locale.ROOT);
        return status.contains("invalid") || status.contains("non valido") || status.contains("unrecognized") || status.contains("non riconosci") || status.contains("errore") || status.contains("error");
    }

    static List<JSONObject> removeObviousParserExplosions(List<JSONObject> source) {
        if (source == null) return new ArrayList<>();
        if (source.size() < 5) return source;
        List<Double> abs = new ArrayList<>();
        for (JSONObject row : source) {
            double v = Math.abs(row.optDouble("value", Double.NaN));
            if (Double.isFinite(v) && v > 0) abs.add(v);
        }
        if (abs.size() < 4) return source;
        Collections.sort(abs);
        double median = abs.get(abs.size() / 2);
        if (!(median > 0)) return source;
        List<JSONObject> out = new ArrayList<>();
        for (JSONObject row : source) {
            double v = Math.abs(row.optDouble("value", Double.NaN));
            if (!keepAgainstMedian(v, median)) continue;
            out.add(row);
        }
        return out.size() >= 2 ? out : source;
    }

    static boolean keepAgainstMedian(double value, double median) {
        if (!Double.isFinite(value) || !Double.isFinite(median) || median <= 0.0) return false;
        double v = Math.abs(value);
        return v > 0.0 && v >= median / 50.0 && v <= median * 50.0;
    }

    private static double parse(Object raw) {
        if (raw == null || raw == JSONObject.NULL) return Double.NaN;
        if (raw instanceof Number) return ((Number) raw).doubleValue();
        Matcher m = NUMBER.matcher(String.valueOf(raw).trim());
        if (!m.find()) return Double.NaN;
        try { return Double.parseDouble(m.group().replace(',', '.')); }
        catch (Exception ignored) { return Double.NaN; }
    }

    private static String sortDate(String raw) {
        if (raw == null) return "";
        String s = raw.trim();
        if (s.length() >= 10 && s.charAt(4) == '-' && s.charAt(7) == '-') return s.substring(0, 10);
        if (s.length() >= 10 && s.charAt(2) == '/' && s.charAt(5) == '/') return s.substring(6,10)+"-"+s.substring(3,5)+"-"+s.substring(0,2);
        return s;
    }
}
''', encoding='utf-8')

s = MAIN.read_text(encoding='utf-8')
s = s.replace('R27ExactWindows.availableLabParameters(prefs)', 'R40ClinicalSeries.availableLabParameters(prefs)')
s = s.replace('R27ExactWindows.labSeries(prefs, p[1])', 'R40ClinicalSeries.labSeries(prefs, p[1])')
s = s.replace('R27ExactWindows.labSeries(prefs, x.optString("id", ""))', 'R40ClinicalSeries.labSeries(prefs, x.optString("id", ""))')
s = s.replace('Android R39 TEST COMPLETO', 'Android R40 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
if 'versionCode 39' not in g:
    raise SystemExit('R40 failed: versionCode 39 missing')
g = g.replace('versionCode 39', 'versionCode 40', 1)
g = g.replace("versionName '1.0.0-android-r39-landscape-exactlabs-sync-progress-test'", "versionName '1.0.0-android-r40-global-parity-final-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R40 all-graphs Windows parity fix applied')
