package it.dossiersanitario.clinicadigitale.beta;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Exact reader for the Windows V8 backup layout produced by App.buildBackupBlob(). */
final class R27ExactWindows {
    private static final String PROFILES = "r27_profiles_json";
    private static final String USERS = "r27_users_json";
    private static final String SETTINGS = "r27_settings_rows_json";
    private static final String GLOBAL_PREFS = "r27_global_preferences_json";
    private static final String ACTIVE_PROFILE = "r27_active_profile_id";
    private static final String LAST_IMPORT = "r27_last_import_at";

    private R27ExactWindows() {}

    static void importSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {
        if (context == null || prefs == null || verifiedZip == null || !verifiedZip.isFile()) throw new Exception("Snapshot Windows non disponibile");
        try (ZipFile zip = new ZipFile(verifiedZip)) {
            Map<String, ZipEntry> entries = new HashMap<>();
            Enumeration<? extends ZipEntry> enumeration = zip.entries();
            while (enumeration.hasMoreElements()) {
                ZipEntry e = enumeration.nextElement();
                if (!e.isDirectory()) entries.put(e.getName(), e);
            }

            JSONArray settingsRows = readArray(zip, entries.get("preferenze/impostazioni.json"));
            JSONArray users = readArray(zip, entries.get("sicurezza/utenti_indicizzati.json"));
            JSONObject global = findSettingsObject(settingsRows, "globalPreferences");

            boolean administrator = "administrator".equalsIgnoreCase(cfg.optString("accessLevel", ""));
            String linked = cfg.optString("linkedProfileId", "");
            String accountDisplayName = cfg.optString("accountDisplayName", cfg.optString("profileName", ""));
            String windowsUserId = findWindowsUserId(users, accountDisplayName);

            JSONArray importedProfiles = new JSONArray();
            Map<String, String> folderByProfile = new HashMap<>();
            Map<String, JSONObject> profileById = new HashMap<>();
            for (Map.Entry<String, ZipEntry> item : entries.entrySet()) {
                String name = item.getKey();
                if (!name.startsWith("profili/") || !name.endsWith("/profilo.json")) continue;
                JSONObject profile = readObject(zip, item.getValue());
                String id = profile.optString("id", "");
                if (id.isEmpty()) continue;
                if (!administrator && !id.equals(linked)) continue;
                String folder = name.substring(0, name.length() - "profilo.json".length());
                folderByProfile.put(id, folder);
                profileById.put(id, profile);
                importedProfiles.put(new JSONObject(profile.toString()));
            }
            if (importedProfiles.length() == 0) throw new Exception("Nessun profilo autorizzato trovato nel backup Windows");

            String active = chooseActiveProfile(settingsRows, windowsUserId, linked, importedProfiles);
            if (active.isEmpty()) active = importedProfiles.optJSONObject(0).optString("id", "");

            SharedPreferences.Editor editor = prefs.edit();
            for (String key : prefs.getAll().keySet()) if (key.startsWith("r27_")) editor.remove(key);
            editor.putString(PROFILES, importedProfiles.toString());
            editor.putString(USERS, users.toString());
            editor.putString(SETTINGS, settingsRows.toString());
            editor.putString(GLOBAL_PREFS, global.toString());
            editor.putString(ACTIVE_PROFILE, active);
            editor.putLong(LAST_IMPORT, System.currentTimeMillis());

            File root = new File(context.getFilesDir(), "r27_windows_snapshot");
            deleteTree(root);
            if (!root.mkdirs() && !root.isDirectory()) throw new Exception("Archivio locale Android non disponibile");

            for (int i = 0; i < importedProfiles.length(); i++) {
                JSONObject profile = importedProfiles.optJSONObject(i);
                if (profile == null) continue;
                String profileId = profile.optString("id", "");
                String folder = folderByProfile.get(profileId);
                if (profileId.isEmpty() || folder == null) continue;

                putArray(editor, profileId, "doctors", readArray(zip, entries.get(folder + "medici.json")));
                putArray(editor, profileId, "therapies", readArray(zip, entries.get(folder + "terapie.json")));
                putArray(editor, profileId, "exemptions", readArray(zip, entries.get(folder + "esenzioni.json")));
                putArray(editor, profileId, "diagnoses", readArray(zip, entries.get(folder + "diagnosi.json")));
                putArray(editor, profileId, "measurements", readArray(zip, entries.get(folder + "misurazioni.json")));
                putArray(editor, profileId, "weightJourneys", readArray(zip, entries.get(folder + "percorsi_peso.json")));
                putArray(editor, profileId, "documentVersions", readArray(zip, entries.get(folder + "versioni_documenti.json")));
                putArray(editor, profileId, "calendarEvents", readArray(zip, entries.get(folder + "agenda.json")));
                putArray(editor, profileId, "calendarSuggestions", readArray(zip, entries.get(folder + "richiami_calendario.json")));

                File profileDir = new File(root, safe(profileId));
                File docsDir = new File(profileDir, "documents");
                if (!docsDir.mkdirs() && !docsDir.isDirectory()) throw new Exception("Cartella documenti Android non disponibile");

                JSONArray docs = readArray(zip, entries.get(folder + "indice_documenti.json"));
                Map<String, ZipEntry> documentEntries = new HashMap<>();
                String docPrefix = folder + "documenti/";
                for (Map.Entry<String, ZipEntry> e : entries.entrySet()) {
                    if (!e.getKey().startsWith(docPrefix)) continue;
                    String leaf = e.getKey().substring(docPrefix.length());
                    int split = leaf.indexOf("__");
                    if (split > 0) documentEntries.put(leaf.substring(0, split), e.getValue());
                }
                JSONArray localDocs = new JSONArray();
                for (int d = 0; d < docs.length(); d++) {
                    JSONObject source = docs.optJSONObject(d);
                    if (source == null) continue;
                    JSONObject copy = new JSONObject(source.toString());
                    String id = source.optString("id", "");
                    ZipEntry original = documentEntries.get(id);
                    if (original != null) {
                        String originalName = source.optString("originalName", original.getName().substring(original.getName().lastIndexOf('/') + 1));
                        File target = new File(docsDir, safe(id) + "__" + safe(originalName));
                        extract(zip, original, target);
                        copy.put("localPath", target.getAbsolutePath());
                    }
                    localDocs.put(copy);
                }
                putArray(editor, profileId, "documents", localDocs);

                String cardPrefix = folder + "tessera_sanitaria/";
                List<ZipEntry> cards = new ArrayList<>();
                for (Map.Entry<String, ZipEntry> e : entries.entrySet()) if (e.getKey().startsWith(cardPrefix)) cards.add(e.getValue());
                Collections.sort(cards, Comparator.comparing(ZipEntry::getName));
                String frontPath = "", backPath = "";
                for (ZipEntry card : cards) {
                    String leaf = card.getName().substring(card.getName().lastIndexOf('/') + 1);
                    String lower = leaf.toLowerCase(Locale.ROOT);
                    boolean back = lower.contains("retro") || lower.contains("back");
                    File target = new File(profileDir, back ? "health_card_back_" + safe(leaf) : "health_card_front_" + safe(leaf));
                    extract(zip, card, target);
                    if (back) backPath = target.getAbsolutePath();
                    else if (frontPath.isEmpty()) frontPath = target.getAbsolutePath();
                    else if (backPath.isEmpty()) backPath = target.getAbsolutePath();
                }
                editor.putString(key(profileId, "healthFront"), frontPath);
                editor.putString(key(profileId, "healthBack"), backPath);
            }
            editor.apply();
        }
    }

    static JSONArray profiles(SharedPreferences prefs) { return readArrayPref(prefs, PROFILES); }
    static JSONArray users(SharedPreferences prefs) { return readArrayPref(prefs, USERS); }
    static JSONArray settingsRows(SharedPreferences prefs) { return readArrayPref(prefs, SETTINGS); }
    static JSONObject globalPreferences(SharedPreferences prefs) { return readObjectPref(prefs, GLOBAL_PREFS); }
    static String activeProfileId(SharedPreferences prefs) { return prefs.getString(ACTIVE_PROFILE, ""); }

    static JSONObject activeProfile(SharedPreferences prefs) {
        String id = activeProfileId(prefs);
        JSONArray profiles = profiles(prefs);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            if (p != null && id.equals(p.optString("id", ""))) return p;
        }
        return profiles.optJSONObject(0);
    }

    static String activeProfileName(SharedPreferences prefs) {
        JSONObject p = activeProfile(prefs);
        if (p == null) return "Profilo sanitario";
        String name = (p.optString("firstName", "") + " " + p.optString("lastName", "")).trim();
        if (name.isEmpty()) name = p.optString("name", p.optString("displayName", "Profilo sanitario"));
        return name;
    }

    static void setActiveProfile(SharedPreferences prefs, String profileId) {
        if (prefs == null || profileId == null || profileId.trim().isEmpty()) return;
        JSONArray profiles = profiles(prefs);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            if (p != null && profileId.equals(p.optString("id", ""))) {
                prefs.edit().putString(ACTIVE_PROFILE, profileId).apply();
                return;
            }
        }
    }

    static JSONArray data(SharedPreferences prefs, String type) {
        return readArrayPref(prefs, key(activeProfileId(prefs), type));
    }
    static JSONArray documents(SharedPreferences prefs) { return data(prefs, "documents"); }
    static JSONArray doctors(SharedPreferences prefs) { return data(prefs, "doctors"); }
    static JSONArray therapies(SharedPreferences prefs) { return data(prefs, "therapies"); }
    static JSONArray exemptions(SharedPreferences prefs) { return data(prefs, "exemptions"); }
    static JSONArray diagnoses(SharedPreferences prefs) { return data(prefs, "diagnoses"); }
    static JSONArray measurements(SharedPreferences prefs) { return data(prefs, "measurements"); }
    static JSONArray weightJourneys(SharedPreferences prefs) { return data(prefs, "weightJourneys"); }
    static JSONArray calendarEvents(SharedPreferences prefs) { return data(prefs, "calendarEvents"); }
    static JSONArray calendarSuggestions(SharedPreferences prefs) { return data(prefs, "calendarSuggestions"); }

    static JSONArray measurementsOf(SharedPreferences prefs, String type) {
        JSONArray source = measurements(prefs), out = new JSONArray();
        for (int i = 0; i < source.length(); i++) {
            JSONObject row = source.optJSONObject(i);
            if (row != null && type.equalsIgnoreCase(row.optString("type", ""))) out.put(row);
        }
        return sortAscending(out, "date", "createdAt", "updatedAt");
    }

    static JSONArray labSeries(SharedPreferences prefs, String parameterId) {
        JSONArray out = new JSONArray();
        JSONArray docs = documents(prefs);
        for (int i = 0; i < docs.length(); i++) {
            JSONObject doc = docs.optJSONObject(i);
            if (doc == null) continue;
            JSONArray labs = doc.optJSONArray("labValues");
            if (labs == null) continue;
            for (int j = 0; j < labs.length(); j++) {
                JSONObject lab = labs.optJSONObject(j);
                if (lab == null) continue;
                String id = lab.optString("parameterId", "");
                if (!parameterId.equals(id)) continue;
                try {
                    JSONObject row = new JSONObject(lab.toString());
                    row.put("date", doc.optString("clinicalDate", doc.optString("createdAt", "")));
                    out.put(row);
                } catch (Exception ignored) {}
            }
        }
        return sortAscending(out, "date");
    }

    static JSONArray availableLabParameters(SharedPreferences prefs) {
        JSONObject seen = new JSONObject();
        JSONArray docs = documents(prefs), out = new JSONArray();
        for (int i = 0; i < docs.length(); i++) {
            JSONObject doc = docs.optJSONObject(i);
            JSONArray labs = doc == null ? null : doc.optJSONArray("labValues");
            if (labs == null) continue;
            for (int j = 0; j < labs.length(); j++) {
                JSONObject lab = labs.optJSONObject(j);
                if (lab == null) continue;
                String id = lab.optString("parameterId", "");
                if (id.isEmpty() || seen.has(id)) continue;
                try {
                    seen.put(id, true);
                    JSONObject p = new JSONObject();
                    p.put("id", id);
                    p.put("name", lab.optString("parameterName", id));
                    p.put("unit", lab.optString("unit", ""));
                    out.put(p);
                } catch (Exception ignored) {}
            }
        }
        return out;
    }

    static JSONObject profilePreferences(SharedPreferences prefs) {
        JSONObject p = activeProfile(prefs);
        JSONObject o = p == null ? null : p.optJSONObject("preferences");
        return o == null ? new JSONObject() : o;
    }

    static int globalThemeColor(SharedPreferences prefs, int fallback) {
        String palette = globalPreferences(prefs).optString("palette", "teal").toLowerCase(Locale.ROOT);
        switch (palette) {
            case "green": return Color.parseColor("#2f7d4a");
            case "blue": return Color.parseColor("#2563a8");
            case "burgundy": return Color.parseColor("#8a3347");
            case "violet": return Color.parseColor("#6c4aa1");
            case "graphite": return Color.parseColor("#52616b");
            case "teal": return Color.parseColor("#0f766e");
            default: return fallback;
        }
    }

    static int activeProfileColor(SharedPreferences prefs, int fallback) {
        String value = profilePreferences(prefs).optString("profileColor", "");
        try { if (value.matches("#[0-9A-Fa-f]{6}")) return Color.parseColor(value); } catch (Exception ignored) {}
        return globalThemeColor(prefs, fallback);
    }

    static String healthFrontPath(SharedPreferences prefs) { return prefs.getString(key(activeProfileId(prefs), "healthFront"), ""); }
    static String healthBackPath(SharedPreferences prefs) { return prefs.getString(key(activeProfileId(prefs), "healthBack"), ""); }

    static JSONArray recentDocuments(SharedPreferences prefs, int max) {
        JSONArray docs = documents(prefs);
        List<JSONObject> list = new ArrayList<>();
        for (int i = 0; i < docs.length(); i++) if (docs.optJSONObject(i) != null) list.add(docs.optJSONObject(i));
        list.sort((a, b) -> documentDate(b).compareTo(documentDate(a)));
        JSONArray out = new JSONArray();
        for (int i = 0; i < Math.min(max, list.size()); i++) out.put(list.get(i));
        return out;
    }

    static JSONArray timeline(SharedPreferences prefs) {
        List<JSONObject> rows = new ArrayList<>();
        addTimeline(rows, documents(prefs), "Documento", "clinicalDate", "title", "originalName");
        addTimeline(rows, diagnoses(prefs), "Diagnosi", "date", "name", "diagnosis", "description");
        addTimeline(rows, therapies(prefs), "Terapia", "validFrom", "medication", "farmaco", "name");
        addTimeline(rows, calendarEvents(prefs), "Agenda", "startDate", "title", "category");
        addTimeline(rows, measurements(prefs), "Rilevazione", "date", "type");
        rows.sort((a, b) -> b.optString("date", "").compareTo(a.optString("date", "")));
        JSONArray out = new JSONArray();
        for (JSONObject row : rows) out.put(row);
        return out;
    }

    static void openDocument(Activity activity, JSONObject doc) {
        if (activity == null || doc == null) return;
        try {
            String path = doc.optString("localPath", "");
            File source = new File(path);
            if (!source.isFile()) throw new Exception("File originale non disponibile");
            File viewDir = new File(activity.getCacheDir(), "r12_view");
            if (!viewDir.exists()) viewDir.mkdirs();
            String original = doc.optString("originalName", source.getName());
            File target = new File(viewDir, "r27_" + System.currentTimeMillis() + "_" + safe(original));
            copy(source, target);
            Uri uri = Uri.parse("content://" + activity.getPackageName() + ".archiveprovider/view/" + target.getName());
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, mime(doc, original));
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            activity.startActivity(Intent.createChooser(intent, "Apri documento"));
        } catch (Exception e) {
            Toast.makeText(activity, "Documento non apribile: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    static String label(JSONObject row, String fallback) {
        if (row == null) return fallback;
        String[] keys = {"title", "name", "nome", "description", "descrizione", "diagnosis", "diagnosi", "medication", "farmaco", "category", "type"};
        for (String key : keys) {
            String value = row.optString(key, "").trim();
            if (!value.isEmpty()) return value;
        }
        return fallback;
    }

    static String detail(JSONObject row) {
        if (row == null) return "";
        String date = first(row, "clinicalDate", "date", "startDate", "validFrom", "createdAt", "updatedAt");
        String value = first(row, "value", "dosage", "dose", "unit", "status", "stato");
        return date + ((!date.isEmpty() && !value.isEmpty()) ? " · " : "") + value;
    }

    static double number(JSONObject row, String... keys) {
        if (row == null) return Double.NaN;
        for (String key : keys) {
            Object v = row.opt(key);
            if (v instanceof Number) return ((Number) v).doubleValue();
            if (v != null) {
                try { return Double.parseDouble(String.valueOf(v).replace(',', '.')); } catch (Exception ignored) {}
            }
        }
        return Double.NaN;
    }

    private static String chooseActiveProfile(JSONArray settings, String windowsUserId, String linked, JSONArray profiles) {
        if (!windowsUserId.isEmpty()) {
            String exact = settingString(settings, "activeProfileId:" + windowsUserId);
            if (containsProfile(profiles, exact)) return exact;
        }
        if (containsProfile(profiles, linked)) return linked;
        for (int i = 0; i < settings.length(); i++) {
            JSONObject row = settings.optJSONObject(i);
            if (row == null || !row.optString("key", "").startsWith("activeProfileId:")) continue;
            String value = jsonStringValue(row.opt("value"));
            if (containsProfile(profiles, value)) return value;
        }
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            String relation = p == null ? "" : p.optString("relation", "");
            if ("Amministratore".equalsIgnoreCase(relation) || "Me stesso".equalsIgnoreCase(relation)) return p.optString("id", "");
        }
        return profiles.optJSONObject(0) == null ? "" : profiles.optJSONObject(0).optString("id", "");
    }

    private static JSONObject findSettingsObject(JSONArray settings, String key) {
        for (int i = 0; i < settings.length(); i++) {
            JSONObject row = settings.optJSONObject(i);
            if (row != null && key.equals(row.optString("key", "")) && row.opt("value") instanceof JSONObject) return row.optJSONObject("value");
        }
        return new JSONObject();
    }

    private static String settingString(JSONArray settings, String key) {
        for (int i = 0; i < settings.length(); i++) {
            JSONObject row = settings.optJSONObject(i);
            if (row != null && key.equals(row.optString("key", ""))) return jsonStringValue(row.opt("value"));
        }
        return "";
    }

    private static String jsonStringValue(Object value) {
        if (value == null || value == JSONObject.NULL) return "";
        return String.valueOf(value).replace("\"", "").trim();
    }

    private static String findWindowsUserId(JSONArray users, String displayName) {
        String wanted = normalize(displayName);
        for (int i = 0; i < users.length(); i++) {
            JSONObject u = users.optJSONObject(i);
            if (u == null) continue;
            String candidate = normalize(u.optString("displayName", u.optString("username", "")));
            if (!wanted.isEmpty() && wanted.equals(candidate)) return u.optString("id", "");
        }
        return "";
    }

    private static boolean containsProfile(JSONArray profiles, String id) {
        if (id == null || id.isEmpty()) return false;
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            if (p != null && id.equals(p.optString("id", ""))) return true;
        }
        return false;
    }

    private static void addTimeline(List<JSONObject> out, JSONArray source, String kind, String dateKey, String... titleKeys) {
        for (int i = 0; i < source.length(); i++) {
            JSONObject r = source.optJSONObject(i);
            if (r == null) continue;
            try {
                JSONObject row = new JSONObject();
                row.put("kind", kind);
                row.put("date", first(r, dateKey, "date", "clinicalDate", "startDate", "validFrom", "createdAt", "updatedAt"));
                String title = "";
                for (String k : titleKeys) { title = r.optString(k, "").trim(); if (!title.isEmpty()) break; }
                row.put("title", title.isEmpty() ? kind : title);
                row.put("source", r);
                out.add(row);
            } catch (Exception ignored) {}
        }
    }

    private static JSONArray sortAscending(JSONArray source, String... dateKeys) {
        List<JSONObject> list = new ArrayList<>();
        for (int i = 0; i < source.length(); i++) if (source.optJSONObject(i) != null) list.add(source.optJSONObject(i));
        list.sort(Comparator.comparing(o -> first(o, dateKeys)));
        JSONArray out = new JSONArray();
        for (JSONObject row : list) out.put(row);
        return out;
    }

    private static String documentDate(JSONObject d) { return first(d, "clinicalDate", "createdAt", "updatedAt"); }

    private static String first(JSONObject o, String... keys) {
        if (o == null) return "";
        for (String key : keys) {
            String s = o.optString(key, "").trim();
            if (!s.isEmpty()) return s;
        }
        return "";
    }

    private static void putArray(SharedPreferences.Editor editor, String profileId, String type, JSONArray value) {
        editor.putString(key(profileId, type), value == null ? "[]" : value.toString());
    }

    private static String key(String profileId, String type) { return "r27_" + safe(profileId) + "_" + type; }

    private static JSONArray readArrayPref(SharedPreferences prefs, String key) {
        try { return new JSONArray(prefs.getString(key, "[]")); } catch (Exception e) { return new JSONArray(); }
    }

    private static JSONObject readObjectPref(SharedPreferences prefs, String key) {
        try { return new JSONObject(prefs.getString(key, "{}")); } catch (Exception e) { return new JSONObject(); }
    }

    private static JSONArray readArray(ZipFile zip, ZipEntry entry) {
        if (entry == null) return new JSONArray();
        try { return new JSONArray(readText(zip, entry)); } catch (Exception e) { return new JSONArray(); }
    }

    private static JSONObject readObject(ZipFile zip, ZipEntry entry) throws Exception { return new JSONObject(readText(zip, entry)); }

    private static String readText(ZipFile zip, ZipEntry entry) throws Exception {
        try (InputStream in = zip.getInputStream(entry)) {
            byte[] buffer = new byte[65536];
            java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
            int n;
            while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
            return out.toString(StandardCharsets.UTF_8.name());
        }
    }

    private static void extract(ZipFile zip, ZipEntry entry, File target) throws Exception {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists()) parent.mkdirs();
        try (InputStream in = zip.getInputStream(entry); FileOutputStream out = new FileOutputStream(target)) {
            byte[] buffer = new byte[262144];
            int n;
            while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
            out.getFD().sync();
        }
        if (!target.isFile() || target.length() == 0) throw new Exception("Contenuto estratto vuoto: " + entry.getName());
    }

    private static void copy(File source, File target) throws Exception {
        try (java.io.FileInputStream in = new java.io.FileInputStream(source); FileOutputStream out = new FileOutputStream(target)) {
            byte[] buffer = new byte[262144]; int n;
            while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
            out.getFD().sync();
        }
    }

    private static String mime(JSONObject doc, String name) {
        String mime = doc.optString("mimeType", "").trim();
        if (!mime.isEmpty()) return mime;
        String lower = String.valueOf(name).toLowerCase(Locale.ROOT);
        if (lower.endsWith(".pdf")) return "application/pdf";
        if (lower.endsWith(".png")) return "image/png";
        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
        if (lower.endsWith(".webp")) return "image/webp";
        return "application/octet-stream";
    }

    private static String safe(String value) {
        String s = String.valueOf(value == null ? "" : value).replaceAll("[^A-Za-z0-9._-]+", "_");
        if (s.length() > 110) s = s.substring(0, 110);
        return s.isEmpty() ? "item" : s;
    }

    private static String normalize(String value) {
        return String.valueOf(value == null ? "" : value).trim().toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
    }

    private static void deleteTree(File file) {
        if (file == null || !file.exists()) return;
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) for (File child : children) deleteTree(child);
        }
        file.delete();
    }
}
