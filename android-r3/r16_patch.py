from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
RCLONE = BASE / 'R12Rclone.java'
MAIN = BASE / 'R6MainActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R16 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_rclone():
    s = RCLONE.read_text(encoding='utf-8')

    marker = 'public final class R12Rclone {\n    private R12Rclone() {}\n'
    if marker not in s:
        raise SystemExit('R16 patch failed: R12Rclone class marker not found')
    s = s.replace(
        marker,
        'public final class R12Rclone {\n'
        '    public interface ProgressCallback { void onProgress(long done, long total); }\n\n'
        '    private R12Rclone() {}\n',
        1
    )

    old = r'''    public static void copyFromRemote(Context context, String remote, File local) throws Exception {
        File parent = local.getParentFile();
        if (parent != null && !parent.exists()) parent.mkdirs();
        run(context, list("copyto", remote, local.getAbsolutePath(), "--retries", "3", "--low-level-retries", "5"));
        if (!local.isFile()) throw new Exception("Download cloud non completato.");
    }

'''
    new = old + r'''    public static void copyFromRemoteWithProgress(Context context, String remote, File local, long expectedBytes, ProgressCallback callback) throws Exception {
        File parent = local.getParentFile();
        if (parent != null && !parent.exists()) parent.mkdirs();
        if (local.exists()) local.delete();

        File exe = new File(context.getApplicationInfo().nativeLibraryDir, "librclone.so");
        if (!exe.isFile()) throw new Exception("Connettore cloud Android non disponibile in questa build.");

        List<String> command = new ArrayList<>();
        command.add(exe.getAbsolutePath());
        command.add("copyto");
        command.add(remote);
        command.add(local.getAbsolutePath());
        command.add("--retries");
        command.add("3");
        command.add("--low-level-retries");
        command.add("5");
        command.add("--inplace");
        command.add("--config");
        command.add(configFile(context).getAbsolutePath());
        command.add("--log-level");
        command.add("ERROR");

        File log = File.createTempFile("r12_progress_", ".log", context.getCacheDir());
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        builder.redirectOutput(log);
        builder.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath());
        builder.environment().put("HOME", context.getFilesDir().getAbsolutePath());

        Process process = builder.start();
        long deadline = System.currentTimeMillis() + TimeUnit.MINUTES.toMillis(15);
        long maxSeen = 0L;
        try {
            while (true) {
                boolean finished = process.waitFor(250, TimeUnit.MILLISECONDS);
                long current = local.isFile() ? local.length() : 0L;
                if (current > maxSeen) maxSeen = current;
                if (callback != null) callback.onProgress(maxSeen, expectedBytes);
                if (finished) break;
                if (System.currentTimeMillis() >= deadline) {
                    process.destroyForcibly();
                    throw new Exception("Operazione cloud scaduta.");
                }
            }
            if (process.exitValue() != 0) {
                String message = "";
                try {
                    message = new String(java.nio.file.Files.readAllBytes(log.toPath()), StandardCharsets.UTF_8).trim();
                } catch (Exception ignored) {}
                if (message.length() > 700) message = message.substring(message.length() - 700);
                throw new Exception(message.isEmpty() ? "Operazione cloud non riuscita." : message);
            }
            if (!local.isFile()) throw new Exception("Download cloud non completato.");
            if (callback != null) callback.onProgress(local.length(), expectedBytes);
        } finally {
            if (log.exists()) log.delete();
        }
    }

'''
    s = replace_once(s, old, new, 'progress download method')
    RCLONE.write_text(s, encoding='utf-8')


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    start = s.find('    private static void startExistingImportProgress(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account) {')
    end = s.find('    private static void completeExistingFamilyConnection(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account, File partial) throws Exception {', start)
    if start < 0 or end < 0:
        raise SystemExit('R16 patch failed: R15 import progress block not found')

    replacement = r'''    private interface ImportProgressCallback {
        void onProgress(long done, long total);
    }

    private static final class CountingInputStream extends java.io.FilterInputStream {
        private long count = 0L;
        private final long total;
        private final ImportProgressCallback callback;

        CountingInputStream(InputStream in, long total, ImportProgressCallback callback) {
            super(in);
            this.total = Math.max(1L, total);
            this.callback = callback;
        }

        private void report(int n) {
            if (n <= 0) return;
            count += n;
            if (callback != null) callback.onProgress(count, total);
        }

        @Override public int read() throws java.io.IOException {
            int value = super.read();
            if (value >= 0) report(1);
            return value;
        }

        @Override public int read(byte[] b, int off, int len) throws java.io.IOException {
            int n = super.read(b, off, len);
            report(n);
            return n;
        }
    }

    private static void setImportProgress(Activity activity, ProgressDialog progress, int percent, String message) {
        activity.runOnUiThread(() -> {
            int safe = Math.max(0, Math.min(100, percent));
            if (safe > progress.getProgress()) progress.setProgress(safe);
            progress.setMessage(message);
        });
    }

    private static void setImportRangeProgress(Activity activity, ProgressDialog progress, int start, int end, long done, long total, String label) {
        long safeTotal = Math.max(1L, total);
        long safeDone = Math.max(0L, Math.min(done, safeTotal));
        int value = start + (int) Math.floor((safeDone * (double) (end - start)) / safeTotal);
        setImportProgress(activity, progress, value, label + "\n" + formatBytes(safeDone) + " / " + formatBytes(safeTotal));
    }

    private static long dsl5PlainBytes(File snapshot) throws Exception {
        if (snapshot == null || !snapshot.isFile() || snapshot.length() < 32L) throw new Exception("Snapshot del Dossier non leggibile.");
        try (FileInputStream in = new FileInputStream(snapshot)) {
            byte[] header = new byte[12];
            int offset = 0;
            while (offset < header.length) {
                int n = in.read(header, offset, header.length - offset);
                if (n < 0) throw new Exception("Snapshot del Dossier incompleto.");
                offset += n;
            }
            int metaLength = java.nio.ByteBuffer.wrap(header, 8, 4).getInt();
            long plain = snapshot.length() - 12L - metaLength - 16L;
            if (metaLength <= 0 || metaLength > 1024 * 1024 || plain <= 0L) throw new Exception("Struttura del Dossier non valida.");
            return plain;
        }
    }

    private static void verifySnapshotIntegrityProgress(Activity activity, ProgressDialog progress, File snapshot, byte[] recovery) throws Exception {
        long total = dsl5PlainBytes(snapshot);
        byte[] buffer = new byte[262144];
        try (InputStream decrypted = R12Crypto.openDsl5File(snapshot, recovery);
             CountingInputStream counted = new CountingInputStream(decrypted, total,
                     (done, all) -> setImportRangeProgress(activity, progress, 65, 78, done, all, "Verifica integrità del Dossier..."))) {
            while (counted.read(buffer) >= 0) {}
        }
        setImportProgress(activity, progress, 78, "Integrità verificata.");
    }

    private static void populateExistingConnectionConfig(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, JSONObject account) throws Exception {
        JSONObject cloud = payload.getJSONObject("cloud");
        cfg.put("origin", "family-existing-account");
        cfg.put("provider", cloud.optString("provider", "mega"));
        cfg.put("archiveId", cloud.getString("archiveId"));
        cfg.put("displayName", cloud.optString("displayName", "Archivio familiare"));
        cfg.put("basePath", R12Rclone.cleanPath(cloud.optString("basePath", "Dossier Sanitario Locale")));
        String linked = account.optString("linkedProfileId", "");
        if (linked.isEmpty() && payload.optJSONObject("membershipTemplate") != null) linked = payload.optJSONObject("membershipTemplate").optString("linkedProfileId", "");
        cfg.put("linkedProfileId", linked);
        cfg.put("accessLevel", "administrator".equals(account.optString("role")) ? "administrator" : account.optString("accessLevel", "viewer"));
        cfg.put("profileName", payload.optString("profileName", account.optString("displayName", "")));
        cfg.put("associationStatus", "active");
        cfg.put("deviceId", deviceId(prefs));
        cfg.put("storagePath", choice.root.getAbsolutePath());
        cfg.put("storageLabel", choice.label);
        cfg.put("recoveryKeyProtected", R12Crypto.protectSecret(context, cloud.getString("recoveryKey")));
    }

    private static void importSnapshotWithProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject cfg, File snapshot, byte[] recovery) throws Exception {
        String linked = cfg.optString("linkedProfileId", "");
        if (linked.isEmpty()) throw new Exception("Profilo autorizzato non indicato.");
        String linkedFolder = null;
        JSONObject profile = null;
        JSONArray doctors = null, exemptions = null, agenda = null, docs = null;
        JSONObject rawAll = loadRaw(prefs);
        long total = dsl5PlainBytes(snapshot);

        try (InputStream decryptedBase = R12Crypto.openDsl5File(snapshot, recovery);
             CountingInputStream decrypted = new CountingInputStream(decryptedBase, total,
                     (done, all) -> setImportRangeProgress(activity, progress, 78, 96, done, all, "Importazione dati del Dossier..."));
             ZipInputStream zip = new ZipInputStream(decrypted)) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (entry.isDirectory()) continue;
                String name = entry.getName();
                if (name.startsWith("profili/") && name.endsWith("/profilo.json")) {
                    byte[] data = readAll(zip);
                    JSONObject p = new JSONObject(new String(data, StandardCharsets.UTF_8));
                    if (linked.equals(p.optString("id"))) {
                        profile = p;
                        linkedFolder = name.substring(0, name.length() - "profilo.json".length());
                        saveRawInObject(rawAll, "profiles", linked, p);
                    }
                } else if (linkedFolder != null && name.startsWith(linkedFolder)) {
                    String rel = name.substring(linkedFolder.length());
                    if ("medici.json".equals(rel)) {
                        doctors = new JSONArray(new String(readAll(zip), StandardCharsets.UTF_8));
                        saveRawArray(rawAll, "doctors", doctors);
                    } else if ("esenzioni.json".equals(rel)) {
                        exemptions = new JSONArray(new String(readAll(zip), StandardCharsets.UTF_8));
                        saveRawArray(rawAll, "exemptions", exemptions);
                    } else if ("agenda.json".equals(rel)) {
                        agenda = new JSONArray(new String(readAll(zip), StandardCharsets.UTF_8));
                        saveRawArray(rawAll, "calendarEvents", agenda);
                    } else if ("indice_documenti.json".equals(rel)) {
                        docs = new JSONArray(new String(readAll(zip), StandardCharsets.UTF_8));
                    } else if (rel.startsWith("documenti/")) {
                        String leaf = rel.substring("documenti/".length());
                        int split = leaf.indexOf("__");
                        String id = split > 0 ? leaf.substring(0, split) : "";
                        if (docs != null && !id.isEmpty()) {
                            JSONObject d = findById(docs, id);
                            if (d != null) d.put("zipEntry", name);
                        }
                        byte[] skip = new byte[262144];
                        while (zip.read(skip) >= 0) {}
                    } else {
                        byte[] skip = new byte[262144];
                        while (zip.read(skip) >= 0) {}
                    }
                } else {
                    byte[] skip = new byte[262144];
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
                m.put("zipEntry", d.optString("zipEntry", ""));
                mapped.put(m);
            }
            saveArray(prefs, DOCS_KEY, mapped);
        }
        setImportProgress(activity, progress, 96, "Dati del Dossier importati.");
    }

    private static void finalizeExistingConnectionProgress(Activity activity, ProgressDialog progress, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account, File partial) throws Exception {
        setImportProgress(activity, progress, 96, "Salvataggio archivio locale...");
        File root = ensureRoot(choice.root);
        File finalFile = new File(root, "current_snapshot.dsl5");
        replaceVerified(partial, finalFile);

        setImportProgress(activity, progress, 97, "Salvataggio account e collegamento...");
        prefs.edit().putString(ACCOUNT_KEY, account.toString()).remove(PENDING_COMPLETION_KEY).apply();
        cfg.put("lastSnapshotName", snap.name);
        cfg.put("lastSyncAt", Instant.now().toString());
        saveConfig(prefs, cfg);

        setImportProgress(activity, progress, 98, "Preparazione sincronizzazione automatica...");
        queueLocalPhotos(activity, prefs, localPhotoFiles(activity));

        setImportProgress(activity, progress, 99, "Attivazione sincronizzazione...");
        schedulePeriodic(activity, prefs);
        scheduleImmediate(activity, prefs);

        setImportProgress(activity, progress, 100, "Completamento...");
    }

    private static void startExistingImportProgress(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account) {
        ProgressDialog progress = new ProgressDialog(activity);
        progress.setTitle("Importazione del Dossier");
        progress.setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);
        progress.setIndeterminate(false);
        progress.setMax(100);
        progress.setProgress(0);
        progress.setMessage("Preparazione archivio...");
        progress.setCancelable(false);
        progress.show();

        EXECUTOR.execute(() -> {
            File partial = null;
            try {
                setImportProgress(activity, progress, 2, "Preparazione archivio...");
                JSONObject cloud = payload.getJSONObject("cloud");

                setImportProgress(activity, progress, 6, "Controllo memoria locale...");
                File root = ensureRoot(choice.root);

                setImportProgress(activity, progress, 10, "Ricerca della copia più recente...");
                SnapshotInfo readySnap = snap == null ? latestSnapshot(activity, cfg) : snap;
                if (readySnap == null) throw new Exception("Snapshot familiare non disponibile.");

                setImportProgress(activity, progress, 15, "Controllo spazio disponibile...");
                if (freeBytes(root) < requiredBytes(readySnap.size)) throw new Exception("Lo spazio disponibile non è più sufficiente per il Dossier.");

                partial = new File(root, "current_snapshot.dsl5.part");
                if (partial.exists()) partial.delete();
                final File partialRef = partial;

                setImportProgress(activity, progress, 20, "Download del Dossier dal cloud...");
                R12Rclone.copyFromRemoteWithProgress(
                        activity,
                        cloudRoot(cfg) + "/snapshots/" + readySnap.name,
                        partialRef,
                        readySnap.size,
                        (done, total) -> setImportRangeProgress(activity, progress, 20, 65, done, total, "Download del Dossier dal cloud...")
                );
                if (readySnap.size > 0 && partialRef.length() != readySnap.size) {
                    partialRef.delete();
                    throw new Exception("Il download del Dossier non ha la dimensione attesa.");
                }

                setImportProgress(activity, progress, 65, "Verifica integrità del Dossier...");
                byte[] recovery = R12Crypto.unb64Url(cloud.getString("recoveryKey"));
                verifySnapshotIntegrityProgress(activity, progress, partialRef, recovery);

                populateExistingConnectionConfig(activity, prefs, payload, cfg, choice, account);

                setImportProgress(activity, progress, 78, "Importazione dati del Dossier...");
                importSnapshotWithProgress(activity, progress, prefs, cfg, partialRef, recovery);

                finalizeExistingConnectionProgress(activity, progress, prefs, payload, cfg, choice, readySnap, account, partialRef);

                activity.runOnUiThread(() -> {
                    progress.dismiss();
                    Toast.makeText(activity, "Dossier importato e dispositivo collegato", Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                if (partial != null && partial.exists()) partial.delete();
                String message = String.valueOf(e.getMessage());
                activity.runOnUiThread(() -> {
                    progress.dismiss();
                    new AlertDialog.Builder(activity)
                            .setTitle("Importazione non riuscita")
                            .setMessage(message == null || message.trim().isEmpty() ? "Operazione cloud non riuscita." : message)
                            .setPositiveButton("Chiudi", null)
                            .show();
                });
            }
        });
    }

'''
    s = s[:start] + replacement + s[end:]
    CLOUD.write_text(s, encoding='utf-8')


def patch_main():
    s = MAIN.read_text(encoding='utf-8')
    s = s.replace('Android R15 TEST', 'Android R16 TEST')
    s = s.replace('Aiuto R15', 'Aiuto R16')
    s = s.replace('R15: struttura presente', 'R16: struttura presente')
    s = s.replace('R15 mantiene lo stesso pacchetto Android', 'R16 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R14', 'Installala sopra la R15')
    MAIN.write_text(s, encoding='utf-8')


patch_rclone()
patch_cloud()
patch_main()
print('R16 continuous criterion-based import progress patch applied')
