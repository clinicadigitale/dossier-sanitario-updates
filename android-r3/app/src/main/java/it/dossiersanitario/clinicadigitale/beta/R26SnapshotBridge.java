package it.dossiersanitario.clinicadigitale.beta;

import android.content.SharedPreferences;
import android.graphics.Color;

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import java.util.Locale;

/**
 * R26 bridge between the complete Windows snapshot and Android UI.
 * It deliberately preserves every JSON payload by snapshot path so Android can
 * consume present and future Windows sections without dropping unknown fields.
 */
final class R26SnapshotBridge {
    static final String PREF_JSON_BY_PATH = "r26_windows_snapshot_json_by_path";
    static final String PREF_ENTRY_INDEX = "r26_windows_snapshot_entry_index";

    private R26SnapshotBridge() {}

    static final class Capture {
        private final JSONObject jsonByPath = new JSONObject();
        private final JSONArray entries = new JSONArray();

        void captureJson(String path, byte[] bytes) {
            if (path == null || bytes == null) return;
            captureEntry(path);
            try {
                String text = new String(bytes, StandardCharsets.UTF_8);
                Object parsed = new JSONTokener(text).nextValue();
                jsonByPath.put(path, parsed);
            } catch (Exception ignored) {
            }
        }

        void captureEntry(String path) {
            if (path == null || path.trim().isEmpty()) return;
            entries.put(path);
        }

        void commit(SharedPreferences prefs) {
            if (prefs == null) return;
            prefs.edit()
                    .putString(PREF_JSON_BY_PATH, jsonByPath.toString())
                    .putString(PREF_ENTRY_INDEX, entries.toString())
                    .apply();
        }
    }

    static JSONObject jsonByPath(SharedPreferences prefs) {
        try {
            return new JSONObject(prefs.getString(PREF_JSON_BY_PATH, "{}"));
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    static JSONArray entryIndex(SharedPreferences prefs) {
        try {
            return new JSONArray(prefs.getString(PREF_ENTRY_INDEX, "[]"));
        } catch (Exception e) {
            return new JSONArray();
        }
    }

    static JSONArray diagnoses(SharedPreferences prefs) {
        return recordsFor(prefs, "diagnos");
    }

    static JSONArray therapies(SharedPreferences prefs) {
        JSONArray a = recordsFor(prefs, "terap");
        if (a.length() == 0) a = recordsFor(prefs, "farmac");
        return a;
    }

    static JSONArray clinicalEvents(SharedPreferences prefs) {
        JSONArray a = recordsFor(prefs, "cronolog", "clinical", "eventi_clinic", "eventi-clinic");
        if (a.length() == 0) {
            try { a = new JSONArray(prefs.getString("android_clinical_events_json", "[]")); }
            catch (Exception ignored) { a = new JSONArray(); }
        }
        return a;
    }

    static JSONArray weightRecords(SharedPreferences prefs) {
        return recordsFor(prefs, "peso", "weight", "pesat");
    }

    static JSONArray glucoseRecords(SharedPreferences prefs) {
        return recordsFor(prefs, "glicem", "glucose");
    }

    static JSONArray pressureRecords(SharedPreferences prefs) {
        return recordsFor(prefs, "pression", "pressure", "blood_pressure");
    }

    static JSONArray saturationRecords(SharedPreferences prefs) {
        return recordsFor(prefs, "saturaz", "spo2", "oxygen");
    }

    static JSONArray genericMonitoringRecords(SharedPreferences prefs) {
        return recordsFor(prefs, "monitor", "misur", "measurement", "parametr");
    }

    static JSONArray users(SharedPreferences prefs) {
        return recordsForAnyPath(prefs, new String[]{"utenti", "users", "sicurezza", "security"}, false);
    }

    static JSONObject windowsSettings(SharedPreferences prefs) {
        JSONObject out = new JSONObject();
        JSONObject all = jsonByPath(prefs);
        Iterator<String> keys = all.keys();
        while (keys.hasNext()) {
            String path = keys.next();
            String lower = normalize(path);
            if (!(lower.contains("prefer") || lower.contains("impost") || lower.contains("setting") || lower.contains("configur"))) continue;
            mergeSettings(out, all.opt(path));
        }
        return out;
    }

    static int themeColor(SharedPreferences prefs, int fallback) {
        JSONObject settings = windowsSettings(prefs);
        Integer found = findColor(settings, true);
        if (found == null) found = findColor(settings, false);
        return found == null ? fallback : found;
    }

    static int userColorFor(SharedPreferences prefs, String profileName, int fallback) {
        JSONArray users = users(prefs);
        String wanted = normalize(profileName);
        for (int i = 0; i < users.length(); i++) {
            JSONObject u = users.optJSONObject(i);
            if (u == null) continue;
            String name = firstText(u, "displayName", "name", "nome", "profileName", "profilo");
            if (!wanted.isEmpty() && !normalize(name).contains(wanted) && !wanted.contains(normalize(name))) continue;
            Integer c = findColor(u, false);
            if (c != null) return c;
        }
        return fallback;
    }

    static int timeoutMinutes(SharedPreferences prefs, int fallback) {
        JSONObject settings = windowsSettings(prefs);
        Integer found = findTimeout(settings);
        if (found == null || found < 1 || found > 240) return fallback;
        return found;
    }

    static JSONArray userColorRows(SharedPreferences prefs) {
        JSONArray out = new JSONArray();
        JSONArray users = users(prefs);
        for (int i = 0; i < users.length(); i++) {
            JSONObject u = users.optJSONObject(i);
            if (u == null) continue;
            Integer color = findColor(u, false);
            if (color == null) continue;
            JSONObject row = new JSONObject();
            try {
                row.put("name", firstText(u, "displayName", "name", "nome", "profileName", "profilo", "username"));
                row.put("color", color);
                row.put("selected", selectedFlag(u));
                out.put(row);
            } catch (Exception ignored) {
            }
        }
        return out;
    }

    static String selectedUsersSummary(SharedPreferences prefs) {
        JSONObject settings = windowsSettings(prefs);
        String direct = findSelectedUsers(settings);
        if (!direct.isEmpty()) return direct;
        JSONArray colors = userColorRows(prefs);
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < colors.length(); i++) {
            JSONObject row = colors.optJSONObject(i);
            if (row != null && row.optBoolean("selected", false)) {
                if (b.length() > 0) b.append(", ");
                b.append(row.optString("name", "Utente"));
            }
        }
        return b.toString();
    }

    static JSONArray healthCardEntries(SharedPreferences prefs) {
        JSONArray out = new JSONArray();
        JSONArray entries = entryIndex(prefs);
        for (int i = 0; i < entries.length(); i++) {
            String path = entries.optString(i, "");
            String n = normalize(path);
            if ((n.contains("tessera") && n.contains("sanitar")) || n.contains("health_card") || n.contains("healthcard")) {
                out.put(path);
            }
        }
        return out;
    }

    static JSONArray recordsFor(SharedPreferences prefs, String... tokens) {
        return recordsForAnyPath(prefs, tokens, true);
    }

    static int countActive(JSONArray records) {
        if (records == null) return 0;
        int count = 0;
        for (int i = 0; i < records.length(); i++) {
            JSONObject o = records.optJSONObject(i);
            if (o == null) continue;
            if (isInactive(o)) continue;
            count++;
        }
        return count;
    }

    static String latestLabel(JSONArray records) {
        if (records == null || records.length() == 0) return "Nessuno";
        JSONObject best = null;
        String bestDate = "";
        for (int i = 0; i < records.length(); i++) {
            JSONObject o = records.optJSONObject(i);
            if (o == null) continue;
            String d = firstText(o, "date", "data", "createdAt", "updatedAt", "clinicalDate", "startDate", "issueDate");
            if (best == null || d.compareTo(bestDate) > 0) { best = o; bestDate = d; }
        }
        if (best == null) return "Nessuno";
        String label = firstText(best, "title", "description", "descrizione", "diagnosis", "diagnosi", "name", "nome", "type", "tipo", "category");
        if (label.isEmpty()) label = "Evento";
        if (label.length() > 34) label = label.substring(0, 31) + "…";
        return label;
    }

    static String recordTitle(JSONObject o, String fallback) {
        if (o == null) return fallback;
        String s = firstText(o, "title", "name", "nome", "description", "descrizione", "diagnosis", "diagnosi", "farmaco", "drug", "type", "tipo", "category");
        return s.isEmpty() ? fallback : s;
    }

    static String recordSubtitle(JSONObject o) {
        if (o == null) return "";
        String date = firstText(o, "date", "data", "startDate", "clinicalDate", "issueDate", "createdAt", "updatedAt");
        String value = firstText(o, "value", "valore", "dose", "dosage", "principioAttivo", "activeIngredient", "status", "stato");
        if (!date.isEmpty() && !value.isEmpty()) return date + " · " + value;
        return !date.isEmpty() ? date : value;
    }

    static double numericValue(JSONObject o, String... preferredKeys) {
        if (o == null) return Double.NaN;
        for (String k : preferredKeys) {
            double v = asDouble(o.opt(k));
            if (!Double.isNaN(v)) return v;
        }
        Iterator<String> keys = o.keys();
        while (keys.hasNext()) {
            String k = keys.next();
            String n = normalize(k);
            if (n.contains("id") || n.contains("revision") || n.contains("time") || n.contains("timestamp")) continue;
            double v = asDouble(o.opt(k));
            if (!Double.isNaN(v)) return v;
        }
        return Double.NaN;
    }

    private static JSONArray recordsForAnyPath(SharedPreferences prefs, String[] tokens, boolean profilePreferred) {
        JSONArray out = new JSONArray();
        JSONObject all = jsonByPath(prefs);
        Iterator<String> keys = all.keys();
        while (keys.hasNext()) {
            String path = keys.next();
            String lower = normalize(path);
            boolean hit = false;
            for (String token : tokens) if (lower.contains(normalize(token))) { hit = true; break; }
            if (!hit) continue;
            if (profilePreferred && lower.contains("sicurezza")) continue;
            flattenRecords(all.opt(path), out, path, 0);
        }
        return out;
    }

    private static void flattenRecords(Object value, JSONArray out, String path, int depth) {
        if (value == null || value == JSONObject.NULL || depth > 5) return;
        if (value instanceof JSONArray) {
            JSONArray a = (JSONArray) value;
            for (int i = 0; i < a.length(); i++) flattenRecords(a.opt(i), out, path, depth + 1);
            return;
        }
        if (!(value instanceof JSONObject)) return;
        JSONObject o = (JSONObject) value;
        if (looksLikeRecord(o)) {
            try {
                JSONObject copy = new JSONObject(o.toString());
                copy.put("_snapshotPath", path);
                out.put(copy);
            } catch (Exception ignored) {
            }
            return;
        }
        Iterator<String> keys = o.keys();
        while (keys.hasNext()) {
            String k = keys.next();
            Object child = o.opt(k);
            if (child instanceof JSONArray || child instanceof JSONObject) flattenRecords(child, out, path, depth + 1);
        }
    }

    private static boolean looksLikeRecord(JSONObject o) {
        if (o.length() == 0) return false;
        String[] keys = {"id", "title", "name", "nome", "date", "data", "value", "valore", "diagnosis", "diagnosi", "farmaco", "drug", "type", "tipo", "description", "descrizione", "startDate"};
        int hits = 0;
        for (String k : keys) if (o.has(k)) hits++;
        return hits >= 1;
    }

    private static void mergeSettings(JSONObject out, Object value) {
        try {
            if (value instanceof JSONObject) {
                JSONObject o = (JSONObject) value;
                Iterator<String> keys = o.keys();
                while (keys.hasNext()) {
                    String k = keys.next();
                    Object v = o.opt(k);
                    if (v instanceof JSONObject) {
                        JSONObject nested = new JSONObject();
                        mergeSettings(nested, v);
                        out.put(k, nested);
                    } else if (v instanceof JSONArray) {
                        out.put(k, new JSONArray(v.toString()));
                    } else {
                        out.put(k, v);
                    }
                }
            } else if (value instanceof JSONArray) {
                JSONArray a = (JSONArray) value;
                for (int i = 0; i < a.length(); i++) {
                    Object row = a.opt(i);
                    if (row instanceof JSONObject) {
                        JSONObject r = (JSONObject) row;
                        String key = firstText(r, "key", "name", "nome", "setting", "impostazione");
                        Object v = firstObject(r, "value", "valore", "selected", "selection");
                        if (!key.isEmpty() && v != null) out.put(key, v);
                        else mergeSettings(out, r);
                    }
                }
            }
        } catch (Exception ignored) {
        }
    }

    private static Integer findColor(Object value, boolean preferTheme) {
        if (value instanceof JSONObject) {
            JSONObject o = (JSONObject) value;
            Iterator<String> keys = o.keys();
            while (keys.hasNext()) {
                String k = keys.next();
                String n = normalize(k);
                Object v = o.opt(k);
                boolean colorKey = n.contains("color") || n.contains("colore") || n.contains("colour");
                boolean themeKey = n.contains("theme") || n.contains("tema") || n.contains("primary") || n.contains("princip") || n.contains("accent");
                if (colorKey && (!preferTheme || themeKey)) {
                    Integer parsed = parseColor(v);
                    if (parsed != null) return parsed;
                }
                Integer nested = findColor(v, preferTheme);
                if (nested != null) return nested;
            }
        } else if (value instanceof JSONArray) {
            JSONArray a = (JSONArray) value;
            for (int i = 0; i < a.length(); i++) {
                Integer nested = findColor(a.opt(i), preferTheme);
                if (nested != null) return nested;
            }
        }
        return null;
    }

    private static Integer parseColor(Object value) {
        if (value == null || value == JSONObject.NULL) return null;
        if (value instanceof Number) {
            int v = ((Number) value).intValue();
            return (v & 0xff000000) == 0 ? (0xff000000 | v) : v;
        }
        String s = String.valueOf(value).trim();
        try {
            if (s.matches("#?[0-9A-Fa-f]{6}")) return Color.parseColor(s.startsWith("#") ? s : "#" + s);
            if (s.matches("#?[0-9A-Fa-f]{8}")) return Color.parseColor(s.startsWith("#") ? s : "#" + s);
        } catch (Exception ignored) {}
        return null;
    }

    private static Integer findTimeout(Object value) {
        if (value instanceof JSONObject) {
            JSONObject o = (JSONObject) value;
            Iterator<String> keys = o.keys();
            while (keys.hasNext()) {
                String k = keys.next();
                String n = normalize(k);
                Object v = o.opt(k);
                if (n.contains("timeout") || n.contains("inattiv") || n.contains("sessione") || n.contains("session")) {
                    int parsed = parseInteger(v);
                    if (parsed > 0) {
                        if (parsed > 600 && parsed % 60 == 0) parsed /= 60;
                        return parsed;
                    }
                }
                Integer nested = findTimeout(v);
                if (nested != null) return nested;
            }
        } else if (value instanceof JSONArray) {
            JSONArray a = (JSONArray) value;
            for (int i = 0; i < a.length(); i++) {
                Integer nested = findTimeout(a.opt(i));
                if (nested != null) return nested;
            }
        }
        return null;
    }

    private static String findSelectedUsers(Object value) {
        if (value instanceof JSONObject) {
            JSONObject o = (JSONObject) value;
            Iterator<String> keys = o.keys();
            while (keys.hasNext()) {
                String k = keys.next();
                String n = normalize(k);
                Object v = o.opt(k);
                if ((n.contains("user") || n.contains("utent") || n.contains("profil")) && (n.contains("select") || n.contains("selez") || n.contains("visible") || n.contains("attiv"))) {
                    String s = compactValue(v);
                    if (!s.isEmpty()) return s;
                }
                String nested = findSelectedUsers(v);
                if (!nested.isEmpty()) return nested;
            }
        } else if (value instanceof JSONArray) {
            JSONArray a = (JSONArray) value;
            for (int i = 0; i < a.length(); i++) {
                String nested = findSelectedUsers(a.opt(i));
                if (!nested.isEmpty()) return nested;
            }
        }
        return "";
    }

    private static boolean selectedFlag(JSONObject o) {
        String[] keys = {"selected", "selezionato", "visible", "visibile", "active", "attivo"};
        for (String k : keys) if (o.has(k)) return o.optBoolean(k, false);
        return false;
    }

    private static boolean isInactive(JSONObject o) {
        if (o.has("active") && !o.optBoolean("active", true)) return true;
        if (o.has("attiva") && !o.optBoolean("attiva", true)) return true;
        String status = normalize(firstText(o, "status", "stato"));
        return status.contains("termin") || status.contains("sospes") || status.contains("inattiv") || status.contains("cessat");
    }

    private static String firstText(JSONObject o, String... keys) {
        for (String k : keys) {
            Object v = o.opt(k);
            if (v != null && v != JSONObject.NULL) {
                String s = String.valueOf(v).trim();
                if (!s.isEmpty() && !"null".equalsIgnoreCase(s)) return s;
            }
        }
        return "";
    }

    private static Object firstObject(JSONObject o, String... keys) {
        for (String k : keys) if (o.has(k)) return o.opt(k);
        return null;
    }

    private static String compactValue(Object v) {
        if (v == null || v == JSONObject.NULL) return "";
        if (v instanceof JSONArray) {
            JSONArray a = (JSONArray) v;
            StringBuilder b = new StringBuilder();
            for (int i = 0; i < a.length(); i++) {
                if (b.length() > 0) b.append(", ");
                Object x = a.opt(i);
                if (x instanceof JSONObject) b.append(firstText((JSONObject) x, "name", "nome", "displayName", "username", "id"));
                else b.append(String.valueOf(x));
            }
            return b.toString();
        }
        return String.valueOf(v).trim();
    }

    private static int parseInteger(Object v) {
        try {
            if (v instanceof Number) return ((Number) v).intValue();
            String s = String.valueOf(v).replaceAll("[^0-9]", "");
            return s.isEmpty() ? -1 : Integer.parseInt(s);
        } catch (Exception e) { return -1; }
    }

    private static double asDouble(Object v) {
        if (v == null || v == JSONObject.NULL) return Double.NaN;
        try {
            if (v instanceof Number) return ((Number) v).doubleValue();
            String s = String.valueOf(v).trim().replace(',', '.').replaceAll("[^0-9.+-]", "");
            if (s.isEmpty() || ".".equals(s) || "+".equals(s) || "-".equals(s)) return Double.NaN;
            return Double.parseDouble(s);
        } catch (Exception e) { return Double.NaN; }
    }

    private static String normalize(String s) {
        return String.valueOf(s == null ? "" : s).toLowerCase(Locale.ROOT)
                .replace('à', 'a').replace('è', 'e').replace('é', 'e').replace('ì', 'i').replace('ò', 'o').replace('ù', 'u');
    }
}