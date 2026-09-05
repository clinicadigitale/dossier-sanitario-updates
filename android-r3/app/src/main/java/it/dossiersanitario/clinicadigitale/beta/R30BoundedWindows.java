package it.dossiersanitario.clinicadigitale.beta;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Bounded-memory importer for the exact Windows V8 backup layout.
 *
 * Large per-profile JSON files and document originals are never accumulated in
 * SharedPreferences or duplicated as JSONArray/String pairs during import.
 * They are streamed directly from the verified ZIP into app-private storage and
 * referenced by small pointer strings. Existing R27 UI readers keep working via
 * the pointer-aware compatibility hook applied by R30.
 */
final class R30BoundedWindows {
    private static final String POINTER = "@file:";
    private static final String ROOT_NAME = "r30_windows_snapshot";
    private static final String STAGE_NAME = "r30_windows_snapshot_stage";
    private static final int BUFFER = 256 * 1024;

    private static final String[][] DATA_FILES = {
            {"medici.json", "doctors", "Medici e specialisti"},
            {"terapie.json", "therapies", "Terapie"},
            {"esenzioni.json", "exemptions", "Esenzioni"},
            {"diagnosi.json", "diagnoses", "Diagnosi"},
            {"misurazioni.json", "measurements", "Monitoraggio e misurazioni"},
            {"percorsi_peso.json", "weightJourneys", "Percorso peso e grafici"},
            {"versioni_documenti.json", "documentVersions", "Storico documenti"},
            {"agenda.json", "calendarEvents", "Agenda ed eventi"},
            {"richiami_calendario.json", "calendarSuggestions", "Richiami e scadenze"},
            {"indice_documenti.json", "documents", "Indice documenti"}
    };

    private R30BoundedWindows() {}

    static void importSnapshot(
            Context context,
            SharedPreferences prefs,
            JSONObject cfg,
            File verifiedZip,
            R27ExactWindows.ProgressCallback progress) throws Exception {
        if (context == null || prefs == null || verifiedZip == null || !verifiedZip.isFile()) {
            throw new Exception("Snapshot Windows non disponibile");
        }

        File stageRoot = new File(context.getFilesDir(), STAGE_NAME);
        File finalRoot = new File(context.getFilesDir(), ROOT_NAME);
        File oldRoot = new File(context.getFilesDir(), ROOT_NAME + "_old");
        deleteTree(stageRoot);
        if (!stageRoot.mkdirs() && !stageRoot.isDirectory()) {
            throw new Exception("Archivio temporaneo Android non disponibile");
        }

        boolean stagePromoted = false;
        try (ZipFile zip = new ZipFile(verifiedZip)) {
            Map<String, ZipEntry> entries = new HashMap<>();
            Enumeration<? extends ZipEntry> enumeration = zip.entries();
            while (enumeration.hasMoreElements()) {
                ZipEntry e = enumeration.nextElement();
                if (!e.isDirectory()) entries.put(e.getName(), e);
            }

            JSONArray settingsRows = readArraySmall(zip, entries.get("preferenze/impostazioni.json"));
            JSONArray users = readArraySmall(zip, entries.get("sicurezza/utenti_indicizzati.json"));
            JSONObject global = findSettingsObject(settingsRows, "globalPreferences");

            boolean administrator = "administrator".equalsIgnoreCase(cfg.optString("accessLevel", ""));
            String linked = cfg.optString("linkedProfileId", "");
            String accountDisplayName = cfg.optString("accountDisplayName", cfg.optString("profileName", ""));
            String windowsUserId = findWindowsUserId(users, accountDisplayName);

            JSONArray importedProfiles = new JSONArray();
            Map<String, String> folderByProfile = new HashMap<>();
            for (Map.Entry<String, ZipEntry> item : entries.entrySet()) {
                String name = item.getKey();
                if (!name.startsWith("profili/") || !name.endsWith("/profilo.json")) continue;
                JSONObject profile = readObjectSmall(zip, item.getValue());
                String id = profile.optString("id", "");
                if (id.isEmpty()) continue;
                if (!administrator && !id.equals(linked)) continue;
                importedProfiles.put(profile);
                folderByProfile.put(id, name.substring(0, name.length() - "profilo.json".length()));
            }
            if (importedProfiles.length() == 0) {
                throw new Exception("Nessun profilo autorizzato trovato nel backup Windows");
            }

            String active = chooseActiveProfile(settingsRows, windowsUserId, linked, importedProfiles);
            if (active.isEmpty()) active = importedProfiles.optJSONObject(0).optString("id", "");

            int totalWork = 1;
            for (int i = 0; i < importedProfiles.length(); i++) {
                JSONObject profile = importedProfiles.optJSONObject(i);
                if (profile == null) continue;
                String folder = folderByProfile.get(profile.optString("id", ""));
                if (folder == null) continue;
                for (String[] map : DATA_FILES) if (entries.containsKey(folder + map[0])) totalWork++;
                String docPrefix = folder + "documenti/";
                String cardPrefix = folder + "tessera_sanitaria/";
                for (String name : entries.keySet()) {
                    if (name.startsWith(docPrefix) || name.startsWith(cardPrefix)) totalWork++;
                }
            }
            int done = 1;
            notifyProgress(progress, done, totalWork, "Profili, utenti e preferenze Windows");

            Map<String, String> prefPointers = new HashMap<>();
            Map<String, String> healthFront = new HashMap<>();
            Map<String, String> healthBack = new HashMap<>();

            for (int i = 0; i < importedProfiles.length(); i++) {
                JSONObject profile = importedProfiles.optJSONObject(i);
                if (profile == null) continue;
                String profileId = profile.optString("id", "");
                String folder = folderByProfile.get(profileId);
                if (profileId.isEmpty() || folder == null) continue;

                File profileStage = new File(stageRoot, safe(profileId));
                File dataStage = new File(profileStage, "data");
                File docsStage = new File(profileStage, "documents");
                if ((!dataStage.mkdirs() && !dataStage.isDirectory()) || (!docsStage.mkdirs() && !docsStage.isDirectory())) {
                    throw new Exception("Cartella dati Android non disponibile");
                }

                File profileFinal = new File(finalRoot, safe(profileId));
                File dataFinal = new File(profileFinal, "data");

                for (String[] map : DATA_FILES) {
                    ZipEntry source = entries.get(folder + map[0]);
                    File targetStage = new File(dataStage, map[1] + ".json");
                    if (source != null) {
                        extract(zip, source, targetStage);
                        notifyProgress(progress, ++done, totalWork, map[2]);
                    } else {
                        writeEmptyArray(targetStage);
                    }
                    File targetFinal = new File(dataFinal, map[1] + ".json");
                    prefPointers.put(key(profileId, map[1]), POINTER + targetFinal.getAbsolutePath());
                }

                String docPrefix = folder + "documenti/";
                for (Map.Entry<String, ZipEntry> item : entries.entrySet()) {
                    String name = item.getKey();
                    if (!name.startsWith(docPrefix)) continue;
                    String leaf = name.substring(docPrefix.length());
                    if (leaf.isEmpty()) continue;
                    int split = leaf.indexOf("__");
                    String id = split > 0 ? leaf.substring(0, split) : leaf;
                    String originalName = split > 0 ? leaf.substring(split + 2) : "documento.bin";
                    File target = new File(docsStage, safe(id) + "__" + safe(originalName));
                    extract(zip, item.getValue(), target);
                    notifyProgress(progress, ++done, totalWork, "Documento: " + originalName);
                }

                String cardPrefix = folder + "tessera_sanitaria/";
                String frontRelative = "";
                String backRelative = "";
                for (Map.Entry<String, ZipEntry> item : entries.entrySet()) {
                    String name = item.getKey();
                    if (!name.startsWith(cardPrefix)) continue;
                    String leaf = name.substring(name.lastIndexOf('/') + 1);
                    String lower = leaf.toLowerCase(Locale.ROOT);
                    boolean isBack = lower.contains("retro") || lower.contains("back");
                    String localName;
                    if (isBack) localName = "health_card_back_" + safe(leaf);
                    else if (frontRelative.isEmpty()) localName = "health_card_front_" + safe(leaf);
                    else localName = "health_card_back_" + safe(leaf);
                    File target = new File(profileStage, localName);
                    extract(zip, item.getValue(), target);
                    if (isBack || !frontRelative.isEmpty()) backRelative = localName;
                    else frontRelative = localName;
                    notifyProgress(progress, ++done, totalWork, isBack ? "Tessera Sanitaria · retro" : "Tessera Sanitaria · fronte");
                }
                if (!frontRelative.isEmpty()) healthFront.put(profileId, new File(profileFinal, frontRelative).getAbsolutePath());
                if (!backRelative.isEmpty()) healthBack.put(profileId, new File(profileFinal, backRelative).getAbsolutePath());
            }

            deleteTree(oldRoot);
            if (finalRoot.exists() && !finalRoot.renameTo(oldRoot)) {
                throw new Exception("Archivio Android precedente non spostabile");
            }
            if (!stageRoot.renameTo(finalRoot)) {
                if (oldRoot.exists()) oldRoot.renameTo(finalRoot);
                throw new Exception("Archivio Android nuovo non attivabile");
            }
            stagePromoted = true;

            SharedPreferences.Editor editor = prefs.edit();
            for (String prefKey : prefs.getAll().keySet()) {
                if (prefKey.startsWith("r27_")) editor.remove(prefKey);
            }
            editor.putString("r27_profiles_json", importedProfiles.toString());
            editor.putString("r27_users_json", users.toString());
            editor.putString("r27_settings_rows_json", settingsRows.toString());
            editor.putString("r27_global_preferences_json", global.toString());
            editor.putString("r27_active_profile_id", active);
            editor.putLong("r27_last_import_at", System.currentTimeMillis());
            for (Map.Entry<String, String> p : prefPointers.entrySet()) editor.putString(p.getKey(), p.getValue());
            for (int i = 0; i < importedProfiles.length(); i++) {
                JSONObject profile = importedProfiles.optJSONObject(i);
                if (profile == null) continue;
                String profileId = profile.optString("id", "");
                editor.putString(key(profileId, "healthFront"), healthFront.getOrDefault(profileId, ""));
                editor.putString(key(profileId, "healthBack"), healthBack.getOrDefault(profileId, ""));
            }
            if (!editor.commit()) throw new Exception("Impostazioni Android non salvate");

            deleteTree(oldRoot);
            deleteTree(new File(context.getFilesDir(), "r27_windows_snapshot"));
            notifyProgress(progress, totalWork, totalWork, "Dati Windows importati");
        } finally {
            if (!stagePromoted) deleteTree(stageRoot);
        }
    }

    static JSONArray readArrayFile(File file) {
        if (file == null || !file.isFile()) return new JSONArray();
        try (FileInputStream in = new FileInputStream(file)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream((int) Math.min(Math.max(1024L, file.length()), 4L * 1024L * 1024L));
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) >= 0) {
                if (n > 0) out.write(buffer, 0, n);
            }
            return new JSONArray(out.toString(StandardCharsets.UTF_8.name()));
        } catch (Throwable failure) {
            return new JSONArray();
        }
    }

    static File resolveDocumentFile(Activity activity, JSONObject doc) {
        if (activity == null || doc == null) return new File("");
        SharedPreferences prefs = activity.getSharedPreferences("clinica_android_beta", Context.MODE_PRIVATE);
        String profileId = R27ExactWindows.activeProfileId(prefs);
        File docsDir = new File(new File(new File(activity.getFilesDir(), ROOT_NAME), safe(profileId)), "documents");
        String id = safe(doc.optString("id", ""));
        String originalName = safe(doc.optString("originalName", "documento.bin"));
        File exact = new File(docsDir, id + "__" + originalName);
        if (exact.isFile()) return exact;
        File[] matches = docsDir.listFiles((dir, name) -> name.startsWith(id + "__"));
        if (matches != null && matches.length > 0) return matches[0];
        return exact;
    }

    private static void notifyProgress(R27ExactWindows.ProgressCallback callback, int done, int total, String stage) {
        if (callback == null) return;
        int safeTotal = Math.max(1, total);
        callback.onProgress(Math.max(0, Math.min(done, safeTotal)), safeTotal, stage == null ? "" : stage);
    }

    private static JSONArray readArraySmall(ZipFile zip, ZipEntry entry) {
        if (entry == null) return new JSONArray();
        try { return new JSONArray(readTextSmall(zip, entry)); } catch (Throwable failure) { return new JSONArray(); }
    }

    private static JSONObject readObjectSmall(ZipFile zip, ZipEntry entry) throws Exception {
        if (entry == null) throw new Exception("Voce profilo Windows assente");
        return new JSONObject(readTextSmall(zip, entry));
    }

    private static String readTextSmall(ZipFile zip, ZipEntry entry) throws Exception {
        long declared = entry.getSize();
        if (declared > 8L * 1024L * 1024L) throw new Exception("Metadati Windows anomali");
        try (InputStream in = zip.getInputStream(entry); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) >= 0) if (n > 0) out.write(buffer, 0, n);
            return out.toString(StandardCharsets.UTF_8.name());
        }
    }

    private static JSONObject findSettingsObject(JSONArray settings, String key) {
        for (int i = 0; i < settings.length(); i++) {
            JSONObject row = settings.optJSONObject(i);
            if (row == null || !key.equals(row.optString("key", ""))) continue;
            Object value = row.opt("value");
            if (value instanceof JSONObject) return (JSONObject) value;
            if (value != null) {
                try { return new JSONObject(String.valueOf(value)); } catch (Exception ignored) {}
            }
        }
        return new JSONObject();
    }

    private static String findWindowsUserId(JSONArray users, String displayName) {
        String wanted = normalize(displayName);
        for (int i = 0; i < users.length(); i++) {
            JSONObject user = users.optJSONObject(i);
            if (user == null) continue;
            String candidate = normalize(user.optString("displayName", user.optString("username", "")));
            if (!wanted.isEmpty() && wanted.equals(candidate)) return user.optString("id", "");
        }
        return "";
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
        JSONObject first = profiles.optJSONObject(0);
        return first == null ? "" : first.optString("id", "");
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

    private static boolean containsProfile(JSONArray profiles, String id) {
        if (id == null || id.isEmpty()) return false;
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            if (p != null && id.equals(p.optString("id", ""))) return true;
        }
        return false;
    }

    private static void extract(ZipFile zip, ZipEntry entry, File target) throws Exception {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Cartella Android non disponibile");
        try (InputStream in = zip.getInputStream(entry); FileOutputStream out = new FileOutputStream(target)) {
            byte[] buffer = new byte[BUFFER];
            int n;
            while ((n = in.read(buffer)) >= 0) if (n > 0) out.write(buffer, 0, n);
            out.getFD().sync();
        }
        if (!target.isFile()) throw new Exception("Contenuto Windows non estratto");
    }

    private static void writeEmptyArray(File target) throws Exception {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Cartella Android non disponibile");
        try (FileOutputStream out = new FileOutputStream(target)) {
            out.write("[]".getBytes(StandardCharsets.UTF_8));
            out.getFD().sync();
        }
    }

    private static String key(String profileId, String type) {
        return "r27_" + safe(profileId) + "_" + type;
    }

    private static String safe(String value) {
        String s = value == null ? "" : value.trim();
        s = s.replaceAll("[^A-Za-z0-9._-]+", "_");
        if (s.isEmpty()) s = "item";
        return s.length() > 160 ? s.substring(0, 160) : s;
    }

    private static String normalize(String value) {
        return value == null ? "" : java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "")
                .replaceAll("[^A-Za-z0-9]+", " ")
                .trim()
                .toLowerCase(Locale.ROOT);
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
