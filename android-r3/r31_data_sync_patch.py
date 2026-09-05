from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
EXACT = BASE / 'R27ExactWindows.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R31 data patch failed: missing {label}')

# ---------------------------------------------------------------------------
# Exact imported data remains editable after the R30 disk-backed import.
# ---------------------------------------------------------------------------
e = EXACT.read_text(encoding='utf-8')
marker = '    static JSONArray profiles(SharedPreferences prefs) { return readArrayPref(prefs, PROFILES); }\n'
require(e, marker, 'R27 profiles marker')
methods = r'''    static boolean replaceData(SharedPreferences prefs, String type, JSONArray rows) {
        if (prefs == null || type == null || type.trim().isEmpty()) return false;
        String prefKey = key(activeProfileId(prefs), type);
        String raw = prefs.getString(prefKey, "[]");
        String payload = rows == null ? "[]" : rows.toString();
        try {
            if (raw != null && raw.startsWith("@file:")) {
                File file = new File(raw.substring("@file:".length()));
                File parent = file.getParentFile();
                if (parent != null && !parent.exists()) parent.mkdirs();
                try (FileOutputStream out = new FileOutputStream(file, false)) {
                    out.write(payload.getBytes(StandardCharsets.UTF_8));
                    out.getFD().sync();
                }
                return true;
            }
            return prefs.edit().putString(prefKey, payload).commit();
        } catch (Throwable failure) {
            return false;
        }
    }

    static boolean upsertData(SharedPreferences prefs, String type, JSONObject row) {
        if (prefs == null || row == null) return false;
        JSONArray source = data(prefs, type);
        JSONArray out = new JSONArray();
        String id = row.optString("id", "");
        boolean replaced = false;
        for (int i = 0; i < source.length(); i++) {
            JSONObject current = source.optJSONObject(i);
            if (current != null && !id.isEmpty() && id.equals(current.optString("id", ""))) {
                out.put(row); replaced = true;
            } else if (current != null) out.put(current);
        }
        if (!replaced) out.put(row);
        return replaceData(prefs, type, out);
    }

    static boolean deleteData(SharedPreferences prefs, String type, String id) {
        JSONArray source = data(prefs, type), out = new JSONArray();
        for (int i = 0; i < source.length(); i++) {
            JSONObject current = source.optJSONObject(i);
            if (current != null && !id.equals(current.optString("id", ""))) out.put(current);
        }
        return replaceData(prefs, type, out);
    }

    static boolean updateActiveProfile(SharedPreferences prefs, JSONObject updated) {
        if (prefs == null || updated == null) return false;
        String id = updated.optString("id", activeProfileId(prefs));
        if (id.isEmpty()) return false;
        JSONArray source = profiles(prefs), out = new JSONArray();
        boolean replaced = false;
        for (int i = 0; i < source.length(); i++) {
            JSONObject current = source.optJSONObject(i);
            if (current != null && id.equals(current.optString("id", ""))) { out.put(updated); replaced = true; }
            else if (current != null) out.put(current);
        }
        if (!replaced) out.put(updated);
        return prefs.edit().putString(PROFILES, out.toString()).commit();
    }

    static boolean updateProfilePreferences(SharedPreferences prefs, JSONObject profilePreferences) {
        JSONObject profile = activeProfile(prefs);
        if (profile == null) return false;
        try {
            JSONObject updated = new JSONObject(profile.toString());
            updated.put("preferences", profilePreferences == null ? new JSONObject() : profilePreferences);
            return updateActiveProfile(prefs, updated);
        } catch (Exception failure) { return false; }
    }

    static boolean updateGlobalPreferences(SharedPreferences prefs, JSONObject global) {
        if (prefs == null) return false;
        JSONObject value = global == null ? new JSONObject() : global;
        JSONArray settings = settingsRows(prefs), out = new JSONArray();
        boolean found = false;
        try {
            for (int i = 0; i < settings.length(); i++) {
                JSONObject row = settings.optJSONObject(i);
                if (row == null) continue;
                if ("globalPreferences".equals(row.optString("key", ""))) {
                    JSONObject copy = new JSONObject(row.toString()); copy.put("value", value); out.put(copy); found = true;
                } else out.put(row);
            }
            if (!found) { JSONObject row = new JSONObject(); row.put("key", "globalPreferences"); row.put("value", value); out.put(row); }
            return prefs.edit().putString(GLOBAL_PREFS, value.toString()).putString(SETTINGS, out.toString()).commit();
        } catch (Exception failure) { return false; }
    }

    static JSONObject documentById(SharedPreferences prefs, String id) {
        if (id == null || id.isEmpty()) return null;
        JSONArray docs = documents(prefs);
        for (int i = 0; i < docs.length(); i++) {
            JSONObject d = docs.optJSONObject(i);
            if (d != null && id.equals(d.optString("id", ""))) return d;
        }
        return null;
    }

'''
e = e.replace(marker, methods + marker, 1)
EXACT.write_text(e, encoding='utf-8')

# ---------------------------------------------------------------------------
# Generic exact-entity queue for the sections edited by the mobile UI.
# ---------------------------------------------------------------------------
c = CLOUD.read_text(encoding='utf-8')
marker = '    private static void queuePut(Context context, SharedPreferences prefs, JSONObject cfg, String store, String entityId, JSONObject entity, List<String> changedFields) throws Exception {\n'
require(c, marker, 'queuePut marker')
methods = r'''    public static void queueR31EntityPut(Context context, SharedPreferences prefs, String store, JSONObject source) {
        if (context == null || prefs == null || source == null || store == null || store.trim().isEmpty()) return;
        try {
            JSONObject cfg = loadConfig(prefs);
            if (cfg.optString("archiveId", "").isEmpty()) return;
            JSONObject entity = new JSONObject(source.toString());
            String id = entity.optString("id", "");
            if (id.isEmpty()) { id = store + "_android_" + UUID.randomUUID(); entity.put("id", id); }
            if (!"profiles".equals(store) && !"settings".equals(store) && entity.optString("profileId", "").isEmpty()) {
                entity.put("profileId", R27ExactWindows.activeProfileId(prefs));
            }
            List<String> changed = new ArrayList<>();
            java.util.Iterator<String> keys = entity.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                if (!"id".equals(key) && !"profileId".equals(key) && !"_syncMeta".equals(key) && !"createdAt".equals(key)) changed.add(key);
            }
            queuePut(context, prefs, cfg, store, id, entity, changed);
        } catch (Exception ignored) {}
    }

    public static void queueR31EntityDelete(Context context, SharedPreferences prefs, String store, String id) {
        if (id == null || id.isEmpty()) return;
        try { queueDelete(context, prefs, loadConfig(prefs), store, id); } catch (Exception ignored) {}
    }

    public static void syncInteractiveR31(Activity activity, SharedPreferences prefs) {
        runProgress(activity, "Sincronizzazione Dossier", () -> {
            String result = syncNow(activity, prefs, false);
            activity.runOnUiThread(() -> Toast.makeText(activity, "Sincronizzazione completata · " + result, Toast.LENGTH_LONG).show());
        });
    }

'''
c = c.replace(marker, methods + marker, 1)
CLOUD.write_text(c, encoding='utf-8')

# ---------------------------------------------------------------------------
# Version.
# ---------------------------------------------------------------------------
g = GRADLE.read_text(encoding='utf-8')
require(g, 'versionCode 30', 'versionCode 30')
require(g, "versionName '1.0.0-android-r30-bounded-import-test'", 'R30 versionName')
g = g.replace('versionCode 30', 'versionCode 31', 1)
g = g.replace("versionName '1.0.0-android-r30-bounded-import-test'", "versionName '1.0.0-android-r31-mobile-parity-test'", 1)
GRADLE.write_text(g, encoding='utf-8')
print('R31 editable data and sync queue patch applied')
