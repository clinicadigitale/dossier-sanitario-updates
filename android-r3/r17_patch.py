from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R17 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    start = s.find('    private static void verifySnapshotIntegrityProgress(Activity activity, ProgressDialog progress, File snapshot, byte[] recovery) throws Exception {')
    end = s.find('    private static void populateExistingConnectionConfig(', start)
    if start < 0 or end < 0:
        raise SystemExit('R17 patch failed: R16 integrity block not found')

    replacement = r'''    private static InputStream openDsl5ProgressStream(File snapshot, byte[] recovery, ImportProgressCallback callback) throws Exception {
        if (snapshot == null || !snapshot.isFile() || snapshot.length() < 32L) throw new Exception("Snapshot del Dossier non leggibile.");
        FileInputStream source = new FileInputStream(snapshot);
        try {
            byte[] header = new byte[12];
            int offset = 0;
            while (offset < header.length) {
                int n = source.read(header, offset, header.length - offset);
                if (n < 0) throw new Exception("Snapshot del Dossier incompleto.");
                offset += n;
            }
            byte[] magic = "DSL5ENC1".getBytes(StandardCharsets.US_ASCII);
            for (int i = 0; i < magic.length; i++) if (header[i] != magic[i]) throw new Exception("Formato cifrato non riconosciuto.");
            int metaLength = java.nio.ByteBuffer.wrap(header, 8, 4).getInt();
            if (metaLength <= 0 || metaLength > 1024 * 1024) throw new Exception("Metadati archivio non validi.");
            byte[] metaBytes = new byte[metaLength];
            offset = 0;
            while (offset < metaBytes.length) {
                int n = source.read(metaBytes, offset, metaBytes.length - offset);
                if (n < 0) throw new Exception("Snapshot del Dossier incompleto.");
                offset += n;
            }
            JSONObject meta = new JSONObject(new String(metaBytes, StandardCharsets.UTF_8));
            if (!"DSL5-AESGCM".equals(meta.optString("format"))) throw new Exception("Formato archivio cloud non valido.");
            byte[] iv = R12Crypto.unb64(meta.getString("iv"));
            long cipherTotal = snapshot.length() - 12L - metaLength;
            if (cipherTotal <= 16L) throw new Exception("Snapshot del Dossier incompleto.");

            CountingInputStream countedSource = new CountingInputStream(source, cipherTotal, callback);
            javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(javax.crypto.Cipher.DECRYPT_MODE,
                    new javax.crypto.spec.SecretKeySpec(recovery, "AES"),
                    new javax.crypto.spec.GCMParameterSpec(128, iv));
            return new javax.crypto.CipherInputStream(countedSource, cipher);
        } catch (Exception e) {
            try { source.close(); } catch (Exception ignored) {}
            throw e;
        }
    }

    private static void verifySnapshotIntegrityProgress(Activity activity, ProgressDialog progress, File snapshot, byte[] recovery) throws Exception {
        byte[] buffer = new byte[262144];
        try (InputStream decrypted = openDsl5ProgressStream(snapshot, recovery,
                (done, all) -> setImportRangeProgress(activity, progress, 65, 78, done, all, "Verifica integrità del Dossier..."))) {
            while (decrypted.read(buffer) >= 0) {}
        }
        setImportProgress(activity, progress, 78, "Integrità verificata.");
    }

'''
    s = s[:start] + replacement + s[end:]

    old_import = r'''        long total = dsl5PlainBytes(snapshot);

        try (InputStream decryptedBase = R12Crypto.openDsl5File(snapshot, recovery);
             CountingInputStream decrypted = new CountingInputStream(decryptedBase, total,
                     (done, all) -> setImportRangeProgress(activity, progress, 78, 96, done, all, "Importazione dati del Dossier..."));
             ZipInputStream zip = new ZipInputStream(decrypted)) {
'''
    new_import = r'''        try (InputStream decrypted = openDsl5ProgressStream(snapshot, recovery,
                     (done, all) -> setImportRangeProgress(activity, progress, 78, 96, done, all, "Importazione dati del Dossier..."));
             ZipInputStream zip = new ZipInputStream(decrypted)) {
'''
    s = replace_once(s, old_import, new_import, 'encrypted-source import progress')

    s = replace_once(s, '                setImportProgress(activity, progress, 2, "Preparazione archivio...");', '                setImportProgress(activity, progress, 0, "Preparazione archivio...");', 'start at zero')
    s = replace_once(s, '                setImportProgress(activity, progress, 6, "Controllo memoria locale...");', '                setImportProgress(activity, progress, 1, "Controllo memoria locale...");', 'memory progress')
    s = replace_once(s, '                setImportProgress(activity, progress, 10, "Ricerca della copia più recente...");', '                setImportProgress(activity, progress, 2, "Ricerca della copia più recente...");', 'snapshot progress')
    s = replace_once(s, '                setImportProgress(activity, progress, 15, "Controllo spazio disponibile...");', '                setImportProgress(activity, progress, 3, "Controllo spazio disponibile...");', 'space progress')
    s = replace_once(s, '                partial = new File(root, "current_snapshot.dsl5.part");', '                setImportProgress(activity, progress, 4, "Preparazione download...");\n                partial = new File(root, "current_snapshot.dsl5.part");', 'download preparation')
    s = replace_once(s, '                setImportProgress(activity, progress, 20, "Download del Dossier dal cloud...");', '                setImportProgress(activity, progress, 5, "Download del Dossier dal cloud...");', 'download start')
    s = replace_once(s, '(done, total) -> setImportRangeProgress(activity, progress, 20, 65, done, total, "Download del Dossier dal cloud...")', '(done, total) -> setImportRangeProgress(activity, progress, 5, 65, done, total, "Download del Dossier dal cloud...")', 'download range')

    CLOUD.write_text(s, encoding='utf-8')


def patch_main_and_version():
    s = MAIN.read_text(encoding='utf-8')
    s = s.replace('Android R16 TEST', 'Android R17 TEST')
    s = s.replace('Aiuto R16', 'Aiuto R17')
    s = s.replace('R16: struttura presente', 'R17: struttura presente')
    s = s.replace('R16 mantiene lo stesso pacchetto Android', 'R17 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R15', 'Installala sopra la R16')
    MAIN.write_text(s, encoding='utf-8')

    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 16', 'versionCode 17', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r16-test'", "versionName '1.0.0-android-r17-test'", 'versionName')
    GRADLE.write_text(g, encoding='utf-8')


patch_cloud()
patch_main_and_version()
print('R17 true encrypted-source progress patch applied')
