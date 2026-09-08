package it.dossiersanitario.clinicadigitale.beta;

import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** R37 report-backed clinical series. Direct Windows labValues are authoritative for laboratory graphs. */
final class R37ClinicalSeries {
    private static final Pattern NUMBER = Pattern.compile("[-+]?\\d+(?:[\\.,]\\d+)?");

    private R37ClinicalSeries() {}

    static JSONArray availableLabParameters(SharedPreferences prefs) {
        JSONArray direct = R27ExactWindows.availableLabParameters(prefs);
        if (direct != null && direct.length() > 0) return withDates(prefs, direct);
        return withDates(prefs, R36ClinicalSeries.availableLabParameters(prefs));
    }

    static JSONArray labSeries(SharedPreferences prefs, String parameterId) {
        JSONArray direct = R27ExactWindows.labSeries(prefs, parameterId);
        JSONArray source = direct != null && direct.length() > 0 ? direct : R36ClinicalSeries.labSeries(prefs, parameterId);
        List<JSONObject> rows = new ArrayList<>();
        if (source != null) {
            for (int i = 0; i < source.length(); i++) {
                JSONObject original = source.optJSONObject(i);
                if (original == null) continue;
                double value = firstNumber(original, "value", "valore", "result", "risultato");
                if (Double.isNaN(value) || Double.isInfinite(value)) continue;
                try {
                    JSONObject row = new JSONObject(original.toString());
                    row.put("value", value);
                    if (row.optString("date", "").trim().isEmpty()) {
                        String d = firstText(row, "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt");
                        if (!d.isEmpty()) row.put("date", d);
                    }
                    rows.add(row);
                } catch (Exception ignored) {}
            }
        }
        rows.sort(Comparator.comparing(o -> sortDate(firstText(o, "date", "clinicalDate", "issueDate", "createdAt", "updatedAt"))));
        JSONArray out = new JSONArray();
        for (JSONObject row : rows) out.put(row);
        return out;
    }

    static JSONArray glycemiaFromReports(SharedPreferences prefs) {
        JSONArray params = availableLabParameters(prefs);
        List<JSONObject> merged = new ArrayList<>();
        for (int i = 0; i < params.length(); i++) {
            JSONObject p = params.optJSONObject(i);
            if (p == null || !isGlycemiaParameter(p)) continue;
            JSONArray series = labSeries(prefs, p.optString("id", ""));
            for (int j = 0; j < series.length(); j++) {
                JSONObject row = series.optJSONObject(j);
                if (row != null) merged.add(row);
            }
        }
        merged.sort(Comparator.comparing(o -> sortDate(firstText(o, "date", "clinicalDate", "issueDate", "createdAt", "updatedAt"))));
        JSONArray out = new JSONArray();
        for (JSONObject row : merged) out.put(row);
        return out;
    }

    static String glycemiaParameterId(SharedPreferences prefs) {
        JSONArray params = availableLabParameters(prefs);
        for (int i = 0; i < params.length(); i++) {
            JSONObject p = params.optJSONObject(i);
            if (p != null && isGlycemiaParameter(p)) return p.optString("id", "");
        }
        return "";
    }

    static boolean isGlycemiaParameter(JSONObject p) {
        if (p == null) return false;
        String n = normalize(p.optString("name", "") + " " + p.optString("id", ""));
        return n.contains("glicem") || n.contains("glucos") || n.contains("glucose") || n.contains("glyc");
    }

    static String firstDate(JSONArray rows) {
        String best = "";
        String key = "";
        if (rows == null) return best;
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String raw = firstText(row, "date", "clinicalDate", "issueDate", "createdAt", "updatedAt");
            String k = sortDate(raw);
            if (k.isEmpty()) continue;
            if (key.isEmpty() || k.compareTo(key) < 0) { key = k; best = raw; }
        }
        return best;
    }

    private static JSONArray withDates(SharedPreferences prefs, JSONArray source) {
        JSONArray out = new JSONArray();
        if (source == null) return out;
        for (int i = 0; i < source.length(); i++) {
            JSONObject p = source.optJSONObject(i);
            if (p == null) continue;
            try {
                JSONObject copy = new JSONObject(p.toString());
                JSONArray series = labSeries(prefs, copy.optString("id", ""));
                copy.put("firstDate", firstDate(series));
                out.put(copy);
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static double firstNumber(JSONObject o, String... keys) {
        for (String key : keys) {
            Object v = o.opt(key);
            if (v instanceof Number) return ((Number) v).doubleValue();
            if (v == null || v == JSONObject.NULL) continue;
            Matcher m = NUMBER.matcher(String.valueOf(v).trim());
            if (!m.find()) continue;
            try { return Double.parseDouble(m.group().replace(',', '.')); }
            catch (Exception ignored) {}
        }
        return Double.NaN;
    }

    private static String firstText(JSONObject o, String... keys) {
        if (o == null) return "";
        for (String key : keys) {
            Object value = o.opt(key);
            if (value == null || value == JSONObject.NULL) continue;
            String s = String.valueOf(value).trim();
            if (!s.isEmpty() && !"null".equalsIgnoreCase(s)) return s;
        }
        return "";
    }

    private static String sortDate(String raw) {
        if (raw == null) return "";
        String s = raw.trim();
        if (s.length() >= 10 && s.charAt(4) == '-' && s.charAt(7) == '-') return s.substring(0, 10);
        if (s.length() >= 10 && s.charAt(2) == '/' && s.charAt(5) == '/') {
            String d = s.substring(0, 2), m = s.substring(3, 5), y = s.substring(6, 10);
            if (d.matches("\\d{2}") && m.matches("\\d{2}") && y.matches("\\d{4}")) return y + "-" + m + "-" + d;
        }
        return s;
    }

    private static String normalize(String value) {
        if (value == null) return "";
        return value.toLowerCase(Locale.ROOT)
                .replace('à','a').replace('á','a').replace('è','e').replace('é','e')
                .replace('ì','i').replace('í','i').replace('ò','o').replace('ó','o')
                .replace('ù','u').replace('ú','u')
                .replaceAll("[^a-z0-9]+", " ").trim();
    }
}
