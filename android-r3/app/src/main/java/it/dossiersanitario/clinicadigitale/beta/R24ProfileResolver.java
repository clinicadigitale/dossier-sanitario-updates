package it.dossiersanitario.clinicadigitale.beta;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

final class R24ProfileResolver {
    static final class Result {
        final String id;
        final String name;

        Result(String id, String name) {
            this.id = id == null ? "" : id;
            this.name = name == null ? "" : name;
        }
    }

    private R24ProfileResolver() {}

    static Result resolve(File verifiedZip, String linkedProfileId, boolean administrator, String accountDisplayName) throws Exception {
        String linked = clean(linkedProfileId);
        if (!linked.isEmpty()) return new Result(linked, "");
        if (!administrator) throw new Exception("Profilo autorizzato non indicato.");
        if (verifiedZip == null || !verifiedZip.isFile()) throw new Exception("Archivio verificato del Dossier non disponibile.");

        Map<String, String> namesById = new LinkedHashMap<>();
        Set<String> administratorProfiles = new LinkedHashSet<>();
        Set<String> displayMatches = new LinkedHashSet<>();
        String wantedName = normalizeName(accountDisplayName);

        try (ZipFile zip = new ZipFile(verifiedZip)) {
            ZipEntry manifestEntry = zip.getEntry("manifest.json");
            if (manifestEntry != null && !manifestEntry.isDirectory()) {
                JSONObject manifest = new JSONObject(readUtf8(zip.getInputStream(manifestEntry)));
                JSONArray profiles = manifest.optJSONArray("profiles");
                if (profiles != null) {
                    for (int i = 0; i < profiles.length(); i++) {
                        JSONObject row = profiles.optJSONObject(i);
                        if (row == null) continue;
                        String id = clean(row.optString("profileId", row.optString("id", "")));
                        if (id.isEmpty()) continue;
                        String name = clean(row.optString("name", ""));
                        namesById.put(id, name);
                        if (!wantedName.isEmpty() && wantedName.equals(normalizeName(name))) displayMatches.add(id);
                    }
                }
            }

            Enumeration<? extends ZipEntry> entries = zip.entries();
            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                String path = entry.getName();
                if (entry.isDirectory() || !path.startsWith("profili/") || !path.endsWith("/profilo.json")) continue;
                JSONObject profile = new JSONObject(readUtf8(zip.getInputStream(entry)));
                String id = clean(profile.optString("id", ""));
                if (id.isEmpty()) continue;
                String fullName = clean((profile.optString("firstName", "") + " " + profile.optString("lastName", "")).trim());
                if (!fullName.isEmpty()) namesById.put(id, fullName);
                String relation = clean(profile.optString("relation", ""));
                if ("amministratore".equalsIgnoreCase(relation) || "me stesso".equalsIgnoreCase(relation)) administratorProfiles.add(id);
                if (!wantedName.isEmpty() && wantedName.equals(normalizeName(fullName))) displayMatches.add(id);
            }
        }

        if (administratorProfiles.size() == 1) {
            String id = administratorProfiles.iterator().next();
            return new Result(id, namesById.get(id));
        }
        if (displayMatches.size() == 1) {
            String id = displayMatches.iterator().next();
            return new Result(id, namesById.get(id));
        }
        if (namesById.size() == 1) {
            String id = namesById.keySet().iterator().next();
            return new Result(id, namesById.get(id));
        }

        throw new Exception("Non è stato possibile individuare automaticamente il profilo personale dell'amministratore nel Dossier.");
    }

    static String normalizeName(String value) {
        String text = Normalizer.normalize(clean(value), Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        return text.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+", " ").trim().replaceAll("\\s+", " ");
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }

    private static String readUtf8(InputStream input) throws Exception {
        try (InputStream in = input; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
            return new String(out.toByteArray(), StandardCharsets.UTF_8);
        }
    }
}
