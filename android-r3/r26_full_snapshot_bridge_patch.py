from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'

s = CLOUD.read_text(encoding='utf-8')

start = s.find('    private static void importSnapshotWithProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {')
end = s.find('    private static void finalizeExistingConnectionProgress(', start)
if start < 0 or end < 0:
    raise SystemExit('R26 patch failed: final importSnapshotWithProgress block not found')

method = r'''    private static void importSnapshotWithProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject cfg, File verifiedZip) throws Exception {
        R24ProfileResolver.Result resolvedProfile = R24ProfileResolver.resolve(
                verifiedZip,
                cfg.optString("linkedProfileId", ""),
                "administrator".equals(cfg.optString("accessLevel", "")),
                cfg.optString("accountDisplayName", cfg.optString("profileName", "")));
        String linked = resolvedProfile.id;
        if (linked.isEmpty()) throw new Exception("Profilo autorizzato non indicato.");
        cfg.put("linkedProfileId", linked);
        if (!resolvedProfile.name.isEmpty()) cfg.put("profileName", resolvedProfile.name);

        String linkedFolder = null;
        JSONObject profile = null;
        JSONArray doctors = null, exemptions = null, agenda = null, docs = null;
        JSONObject rawAll = loadRaw(prefs);
        Map<String, String> documentEntries = new HashMap<>();
        R26SnapshotBridge.Capture capture = new R26SnapshotBridge.Capture();

        try (InputStream verifiedInput = new CountingInputStream(new FileInputStream(verifiedZip), Math.max(1L, verifiedZip.length()),
                     (done, all) -> setImportRangeProgress(activity, progress,
                             DATA_PROGRESS_START, DATA_PROGRESS_END,
                             done, all, "Importazione completa del Dossier..."));
             ZipInputStream zip = new ZipInputStream(verifiedInput)) {
            ZipEntry entry;
            byte[] skip = new byte[262144];
            while ((entry = zip.getNextEntry()) != null) {
                if (entry.isDirectory()) { zip.closeEntry(); continue; }
                String name = entry.getName();
                capture.captureEntry(name);

                if (name.toLowerCase(Locale.ROOT).endsWith(".json")) {
                    byte[] data = R25ZipEntryReader.readEntry(zip);
                    capture.captureJson(name, data);
                    String text = new String(data, StandardCharsets.UTF_8);

                    if (name.startsWith("profili/") && name.endsWith("/profilo.json")) {
                        JSONObject p = new JSONObject(text);
                        if (linked.equals(p.optString("id"))) {
                            profile = p;
                            linkedFolder = name.substring(0, name.length() - "profilo.json".length());
                            saveRawInObject(rawAll, "profiles", linked, p);
                        }
                    } else if (linkedFolder != null && name.startsWith(linkedFolder)) {
                        String rel = name.substring(linkedFolder.length());
                        if ("medici.json".equals(rel)) {
                            doctors = new JSONArray(text);
                            saveRawArray(rawAll, "doctors", doctors);
                        } else if ("esenzioni.json".equals(rel)) {
                            exemptions = new JSONArray(text);
                            saveRawArray(rawAll, "exemptions", exemptions);
                        } else if ("agenda.json".equals(rel)) {
                            agenda = new JSONArray(text);
                            saveRawArray(rawAll, "calendarEvents", agenda);
                        } else if ("indice_documenti.json".equals(rel)) {
                            docs = new JSONArray(text);
                        }
                    }
                } else {
                    if (linkedFolder != null && name.startsWith(linkedFolder)) {
                        String rel = name.substring(linkedFolder.length());
                        if (rel.startsWith("documenti/")) {
                            String leaf = rel.substring("documenti/".length());
                            int split = leaf.indexOf("__");
                            String id = split > 0 ? leaf.substring(0, split) : "";
                            if (!id.isEmpty()) documentEntries.put(id, name);
                        }
                    }
                    while (zip.read(skip) >= 0) {}
                }
                zip.closeEntry();
            }
        }

        if (profile == null) throw new Exception("Il profilo autorizzato non è presente nella copia del Dossier.");
        mapProfileToPrefs(prefs, profile);
        prefs.edit().putString(RAW_KEY, rawAll.toString()).apply();
        if (doctors != null) saveArray(prefs, PREF_DOCTORS, mapDoctors(doctors));
        if (exemptions != null) saveArray(prefs, PREF_EXEMPTIONS, mapExemptions(exemptions));
        if (agenda != null) saveArray(prefs, PREF_AGENDA, mapAgendaArray(agenda));
        if (docs != null) {
            JSONArray mapped = new JSONArray();
            for (int i = 0; i < docs.length(); i++) {
                JSONObject d = docs.optJSONObject(i);
                if (d == null) continue;
                JSONObject m = new JSONObject();
                m.put("windows_id", d.optString("id"));
                copyDocMeta(d, m);
                String entryName = documentEntries.get(d.optString("id"));
                if (entryName != null) m.put("zipEntry", entryName);
                else m.put("zipEntry", d.optString("zipEntry", ""));
                mapped.put(m);
            }
            saveArray(prefs, DOCS_KEY, mapped);
        }
        capture.commit(prefs);
        setImportProgress(activity, progress, 96, "Dati, preferenze e impostazioni Windows importati.");
    }

'''
s = s[:start] + method + s[end:]

marker = '    public static void appendCloudDocuments(Activity activity, LinearLayout content, SharedPreferences prefs) {'
if marker not in s:
    raise SystemExit('R26 patch failed: appendCloudDocuments marker missing')
helpers = r'''    public static int cloudDocumentCount(SharedPreferences prefs) {
        JSONArray docs = readArray(prefs, DOCS_KEY);
        int count = 0;
        for (int i = 0; i < docs.length(); i++) {
            JSONObject d = docs.optJSONObject(i);
            if (d != null && !d.optBoolean("deleted", false)) count++;
        }
        return count;
    }

    public static String lastSyncLabel(SharedPreferences prefs) {
        JSONObject cfg = loadConfig(prefs);
        String value = cfg.optString("lastSyncAt", "");
        return value == null || value.trim().isEmpty() ? "Mai" : value;
    }

    public static void openSnapshotPath(Activity activity, SharedPreferences prefs, String entryName, String mimeType, String displayName) {
        if (entryName == null || entryName.trim().isEmpty()) return;
        runProgress(activity, "Apertura " + (displayName == null ? "documento" : displayName), () -> {
            JSONObject cfg = loadConfig(prefs);
            File snapshot = currentSnapshot(activity, cfg);
            if (snapshot == null) throw new Exception("Archivio Dossier non disponibile.");
            File outputDir = new File(activity.getCacheDir(), "r26_snapshot_view");
            if (!outputDir.exists()) outputDir.mkdirs();
            String leaf = entryName.substring(Math.max(entryName.lastIndexOf('/') + 1, 0));
            File output = new File(outputDir, System.currentTimeMillis() + "_" + safeFileName(leaf));
            extractSnapshotEntry(snapshot, recoveryKey(activity, cfg), entryName, output);
            activity.runOnUiThread(() -> {
                try {
                    Uri uri = Uri.parse("content://" + activity.getPackageName() + ".archiveprovider/view/" + output.getName());
                    Intent intent = new Intent(Intent.ACTION_VIEW);
                    intent.setDataAndType(uri, mimeType == null || mimeType.trim().isEmpty() ? "application/octet-stream" : mimeType);
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    activity.startActivity(Intent.createChooser(intent, "Apri " + (displayName == null ? "documento" : displayName)));
                } catch (Exception e) {
                    Toast.makeText(activity, "Nessuna app disponibile per aprire il contenuto", Toast.LENGTH_LONG).show();
                }
            });
        });
    }

'''
s = s.replace(marker, helpers + marker, 1)

CLOUD.write_text(s, encoding='utf-8')
print('R26 full Windows snapshot bridge patch applied')
