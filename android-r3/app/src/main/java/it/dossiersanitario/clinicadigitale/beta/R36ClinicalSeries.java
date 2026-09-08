package it.dossiersanitario.clinicadigitale.beta;

import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * R36 clinical-series reader.
 *
 * Graphs backed by laboratory results must use the values extracted from the
 * original reports stored in the Windows-compatible document index. This class
 * walks the document payload conservatively, accepts only structures that look
 * like actual laboratory-result rows, keeps the report date as the time axis,
 * and sorts every series chronologically before it reaches the chart.
 */
final class R36ClinicalSeries {
    private static final Pattern NUMBER = Pattern.compile("[-+]?\\d+(?:[\\.,]\\d+)?");

    private R36ClinicalSeries() {}

    static JSONArray availableLabParameters(SharedPreferences prefs) {
        JSONArray out = new JSONArray();
        Set<String> seen = new HashSet<>();
        JSONArray docs = R27ExactWindows.documents(prefs);
        for (int i = 0; i < docs.length(); i++) {
            JSONObject doc = docs.optJSONObject(i);
            if (doc == null) continue;
            List<JSONObject> rows = new ArrayList<>();
            collectLabRows(doc, rows, 0);
            for (JSONObject lab : rows) {
                String name = firstText(lab, "parameterName", "testName", "analyte", "name", "parametro", "esame");
                String id = firstText(lab, "parameterId", "testId", "analyteId", "idParametro");
                String unit = firstText(lab, "unit", "unita", "uom");
                String value = firstText(lab, "value", "valore", "result", "risultato");
                if (name.isEmpty() && id.isEmpty()) continue;
                if (Double.isNaN(parseClinicalNumber(value))) continue;
                if (id.isEmpty()) id = "name:" + normalize(name) + "|" + normalize(unit);
                String dedupe = normalize(id) + "|" + normalize(unit);
                if (!seen.add(dedupe)) continue;
                try {
                    JSONObject p = new JSONObject();
                    p.put("id", id);
                    p.put("name", name.isEmpty() ? id : name);
                    p.put("unit", unit);
                    p.put("firstDate", documentDate(doc));
                    p.put("lastDate", documentDate(doc));
                    out.put(p);
                } catch (Exception ignored) {}
            }
        }

        // Complete first/last dates for each parameter from its exact report series.
        for (int i = 0; i < out.length(); i++) {
            JSONObject p = out.optJSONObject(i);
            if (p == null) continue;
            JSONArray series = labSeries(prefs, p.optString("id", ""));
            if (series.length() == 0) continue;
            try {
                p.put("firstDate", firstDate(series));
                p.put("lastDate", lastDate(series));
            } catch (Exception ignored) {}
        }
        return out;
    }

    static JSONArray labSeries(SharedPreferences prefs, String parameterId) {
        List<JSONObject> found = new ArrayList<>();
        Set<String> seen = new HashSet<>();
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
                String id = firstText(lab, "parameterId", "testId", "analyteId", "idParametro");
                String unit = firstText(lab, "unit", "unita", "uom");
                if (id.isEmpty()) id = "name:" + normalize(name) + "|" + normalize(unit);
                if (!sameParameter(parameterId, id, name, unit)) continue;
                String rawValue = firstText(lab, "value", "valore", "result", "risultato");
                double value = parseClinicalNumber(rawValue);
                if (Double.isNaN(value) || Double.isInfinite(value)) continue;
                String key = docId + "|" + sortDate(date) + "|" + normalize(id) + "|" + value + "|" + normalize(unit);
                if (!seen.add(key)) continue;
                try {
                    JSONObject row = new JSONObject(lab.toString());
                    row.put("value", value);
                    row.put("rawValue", rawValue);
                    row.put("date", date);
                    row.put("sourceDocumentId", docId);
                    if (!name.isEmpty()) row.put("parameterName", name);
                    if (!unit.isEmpty()) row.put("unit", unit);
                    found.add(row);
                } catch (Exception ignored) {}
            }
        }
        found.sort(Comparator.comparing(o -> sortDate(o.optString("date", ""))));
        JSONArray out = new JSONArray();
        for (JSONObject row : found) out.put(row);
        return out;
    }

    static String findParameterByName(SharedPreferences prefs, String token) {
        String wanted = normalize(token);
        JSONArray params = availableLabParameters(prefs);
        for (int i = 0; i < params.length(); i++) {
            JSONObject p = params.optJSONObject(i);
            if (p == null) continue;
            String n = normalize(p.optString("name", ""));
            if (!wanted.isEmpty() && n.contains(wanted)) return p.optString("id", "");
        }
        return "";
    }

    static String firstDate(JSONArray rows) {
        String best = "";
        String bestKey = "";
        if (rows == null) return best;
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String d = firstText(row, "date", "clinicalDate", "issueDate", "createdAt", "updatedAt");
            String k = sortDate(d);
            if (k.isEmpty()) continue;
            if (bestKey.isEmpty() || k.compareTo(bestKey) < 0) { best = d; bestKey = k; }
        }
        return best;
    }

    static String lastDate(JSONArray rows) {
        String best = "";
        String bestKey = "";
        if (rows == null) return best;
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String d = firstText(row, "date", "clinicalDate", "issueDate", "createdAt", "updatedAt");
            String k = sortDate(d);
            if (k.isEmpty()) continue;
            if (bestKey.isEmpty() || k.compareTo(bestKey) > 0) { best = d; bestKey = k; }
        }
        return best;
    }

    static String chronologicalKey(JSONArray rows) {
        String first = firstDate(rows);
        String key = sortDate(first);
        return key.isEmpty() ? "9999-99-99" : key;
    }

    private static boolean sameParameter(String wanted, String id, String name, String unit) {
        if (wanted == null) return false;
        if (wanted.equals(id)) return true;
        String normalizedWanted = normalize(wanted);
        if (normalizedWanted.equals(normalize(id))) return true;
        String synthetic = normalize("name:" + normalize(name) + "|" + normalize(unit));
        return normalizedWanted.equals(synthetic);
    }

    private static void collectLabRows(Object value, List<JSONObject> out, int depth) {
        if (value == null || value == JSONObject.NULL || depth > 8) return;
        if (value instanceof JSONArray) {
            JSONArray array = (JSONArray) value;
            for (int i = 0; i < array.length(); i++) collectLabRows(array.opt(i), out, depth + 1);
            return;
        }
        if (!(value instanceof JSONObject)) return;
        JSONObject object = (JSONObject) value;
        if (looksLikeLabRow(object)) out.add(object);
        Iterator<String> keys = object.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            Object child = object.opt(key);
            if (child instanceof JSONObject || child instanceof JSONArray) collectLabRows(child, out, depth + 1);
        }
    }

    private static boolean looksLikeLabRow(JSONObject o) {
        if (o == null) return false;
        boolean hasValue = hasAny(o, "value", "valore", "result", "risultato");
        boolean hasIdentity = hasAny(o, "parameterId", "parameterName", "testId", "testName", "analyte", "analyteId", "parametro", "esame", "idParametro");
        if (!hasValue || !hasIdentity) return false;
        String value = firstText(o, "value", "valore", "result", "risultato");
        return !Double.isNaN(parseClinicalNumber(value));
    }

    private static boolean hasAny(JSONObject o, String... keys) {
        for (String key : keys) if (o.has(key) && o.opt(key) != null && o.opt(key) != JSONObject.NULL) return true;
        return false;
    }

    private static String documentDate(JSONObject doc) {
        return firstText(doc, "clinicalDate", "issueDate", "date", "documentDate", "createdAt", "updatedAt");
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

    private static double parseClinicalNumber(String raw) {
        if (raw == null) return Double.NaN;
        Matcher matcher = NUMBER.matcher(raw.trim());
        if (!matcher.find()) return Double.NaN;
        try { return Double.parseDouble(matcher.group().replace(',', '.')); }
        catch (Exception ignored) { return Double.NaN; }
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
