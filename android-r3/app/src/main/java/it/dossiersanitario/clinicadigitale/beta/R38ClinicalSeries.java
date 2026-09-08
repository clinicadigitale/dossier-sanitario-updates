package it.dossiersanitario.clinicadigitale.beta;

import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * R38 clinical-series reconciliation.
 * Uses both the exact Windows document index and the more tolerant R36 report reader,
 * then normalizes the selected numeric field before a graph is drawn.
 */
final class R38ClinicalSeries {
    private static final Pattern NUMBER = Pattern.compile("[-+]?\\d+(?:[\\.,]\\d+)?");

    private R38ClinicalSeries() {}

    static JSONArray availableLabParameters(SharedPreferences prefs) {
        JSONArray out = new JSONArray();
        Set<String> seen = new HashSet<>();
        addParameters(out, seen, R36ClinicalSeries.availableLabParameters(prefs));
        addParameters(out, seen, R27ExactWindows.availableLabParameters(prefs));
        for (int i = 0; i < out.length(); i++) {
            JSONObject p = out.optJSONObject(i);
            if (p == null) continue;
            try {
                JSONArray series = labSeries(prefs, p.optString("id", ""));
                p.put("firstDate", firstDate(series));
                p.put("lastDate", lastDate(series));
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static void addParameters(JSONArray out, Set<String> seen, JSONArray source) {
        if (source == null) return;
        for (int i = 0; i < source.length(); i++) {
            JSONObject p = source.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "").trim();
            if (id.isEmpty()) continue;
            String key = normalize(id);
            if (!seen.add(key)) continue;
            try { out.put(new JSONObject(p.toString())); }
            catch (Exception ignored) {}
        }
    }

    static JSONArray labSeries(SharedPreferences prefs, String parameterId) {
        JSONArray exact = R27ExactWindows.labSeries(prefs, parameterId);
        JSONArray tolerant = R36ClinicalSeries.labSeries(prefs, parameterId);
        return mergeSeries(exact, tolerant);
    }

    static JSONArray glycemiaFromReports(SharedPreferences prefs) {
        JSONArray params = availableLabParameters(prefs);
        JSONArray merged = new JSONArray();
        for (int i = 0; i < params.length(); i++) {
            JSONObject p = params.optJSONObject(i);
            if (p == null || !isGlycemiaParameter(p)) continue;
            merged = mergeSeries(merged, labSeries(prefs, p.optString("id", "")));
        }
        return merged;
    }

    static boolean isGlycemiaParameter(JSONObject p) {
        if (p == null) return false;
        String n = normalize(p.optString("name", "") + " " + p.optString("id", ""));
        return n.contains("glicem") || n.contains("glucos") || n.contains("glucose") || n.contains("glyc");
    }

    /** Normalizes exactly the requested field; it never falls back to another numeric property. */
    static JSONArray normalizeGraphSeries(JSONArray source, String key) {
        List<JSONObject> rows = new ArrayList<>();
        if (source == null || key == null || key.trim().isEmpty()) return new JSONArray();
        for (int i = 0; i < source.length(); i++) {
            JSONObject original = source.optJSONObject(i);
            if (original == null) continue;
            double value = parseNumber(original.opt(key));
            if (!Double.isFinite(value)) continue;
            try {
                JSONObject row = new JSONObject(original.toString());
                row.put("value", value);
                String date = firstText(row, "date", "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt");
                if (!date.isEmpty()) row.put("date", date);
                rows.add(row);
            } catch (Exception ignored) {}
        }
        rows.sort(Comparator.comparing(o -> sortDate(firstText(o, "date", "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt"))));
        JSONArray out = new JSONArray();
        for (JSONObject row : rows) out.put(row);
        return out;
    }

    /** Merges report readers while preserving every distinct dated numeric value once. */
    static JSONArray mergeSeries(JSONArray... sources) {
        List<JSONObject> rows = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        if (sources != null) {
            for (JSONArray source : sources) {
                if (source == null) continue;
                for (int i = 0; i < source.length(); i++) {
                    JSONObject original = source.optJSONObject(i);
                    if (original == null) continue;
                    double value = firstNumber(original, "value", "rawValue", "displayResult", "result", "risultato", "valore");
                    if (!Double.isFinite(value)) continue;
                    String date = firstText(original, "date", "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt");
                    String parameter = firstText(original, "parameterId", "parameterName", "testName", "name");
                    String unit = firstText(original, "unit", "uom", "unita");
                    String key = sortDate(date) + "|" + normalize(parameter) + "|" + normalize(unit) + "|" + canonicalNumber(value);
                    if (!seen.add(key)) continue;
                    try {
                        JSONObject row = new JSONObject(original.toString());
                        row.put("value", value);
                        if (!date.isEmpty()) row.put("date", date);
                        rows.add(row);
                    } catch (Exception ignored) {}
                }
            }
        }
        rows.sort(Comparator.comparing(o -> sortDate(firstText(o, "date", "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt"))));
        JSONArray out = new JSONArray();
        for (JSONObject row : rows) out.put(row);
        return out;
    }

    static String firstDate(JSONArray rows) {
        String best = "", bestKey = "";
        if (rows == null) return best;
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String raw = firstText(row, "date", "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt");
            String key = sortDate(raw);
            if (key.isEmpty()) continue;
            if (bestKey.isEmpty() || key.compareTo(bestKey) < 0) { best = raw; bestKey = key; }
        }
        return best;
    }

    static String lastDate(JSONArray rows) {
        String best = "", bestKey = "";
        if (rows == null) return best;
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String raw = firstText(row, "date", "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt");
            String key = sortDate(raw);
            if (key.isEmpty()) continue;
            if (bestKey.isEmpty() || key.compareTo(bestKey) > 0) { best = raw; bestKey = key; }
        }
        return best;
    }

    private static double firstNumber(JSONObject o, String... keys) {
        if (o == null) return Double.NaN;
        for (String key : keys) {
            double value = parseNumber(o.opt(key));
            if (Double.isFinite(value)) return value;
        }
        return Double.NaN;
    }

    private static double parseNumber(Object raw) {
        if (raw == null || raw == JSONObject.NULL) return Double.NaN;
        if (raw instanceof Number) return ((Number) raw).doubleValue();
        Matcher m = NUMBER.matcher(String.valueOf(raw).trim());
        if (!m.find()) return Double.NaN;
        try { return Double.parseDouble(m.group().replace(',', '.')); }
        catch (Exception ignored) { return Double.NaN; }
    }

    private static String canonicalNumber(double value) {
        return String.format(Locale.ROOT, "%.8f", value);
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
