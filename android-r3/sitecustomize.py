import atexit
import os
from pathlib import Path


def _patch_r16b():
    cloud = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java')
    if not cloud.is_file():
        raise SystemExit('R16B fix failed: cloud source missing')
    s = cloud.read_text(encoding='utf-8')

    start = s.find('    private static void verifySnapshotIntegrityProgress(Activity activity, ProgressDialog progress, File snapshot, byte[] recovery) throws Exception {')
    end = s.find('    private static void populateExistingConnectionConfig(', start)
    if start < 0 or end < 0:
        raise SystemExit('R16B fix failed: integrity block not found')

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

    old_import = '''        long total = dsl5PlainBytes(snapshot);\n\n        try (InputStream decryptedBase = R12Crypto.openDsl5File(snapshot, recovery);\n             CountingInputStream decrypted = new CountingInputStream(decryptedBase, total,\n                     (done, all) -> setImportRangeProgress(activity, progress, 78, 96, done, all, "Importazione dati del Dossier..."));\n             ZipInputStream zip = new ZipInputStream(decrypted)) {\n'''
    new_import = '''        try (InputStream decrypted = openDsl5ProgressStream(snapshot, recovery,\n                     (done, all) -> setImportRangeProgress(activity, progress, 78, 96, done, all, "Importazione dati del Dossier..."));\n             ZipInputStream zip = new ZipInputStream(decrypted)) {\n'''
    if old_import not in s:
        raise SystemExit('R16B fix failed: import progress block not found')
    s = s.replace(old_import, new_import, 1)

    replacements = [
        ('                setImportProgress(activity, progress, 2, "Preparazione archivio...");', '                setImportProgress(activity, progress, 0, "Preparazione archivio...");'),
        ('                setImportProgress(activity, progress, 6, "Controllo memoria locale...");', '                setImportProgress(activity, progress, 1, "Controllo memoria locale...");'),
        ('                setImportProgress(activity, progress, 10, "Ricerca della copia più recente...");', '                setImportProgress(activity, progress, 2, "Ricerca della copia più recente...");'),
        ('                setImportProgress(activity, progress, 15, "Controllo spazio disponibile...");', '                setImportProgress(activity, progress, 3, "Controllo spazio disponibile...");'),
        ('                setImportProgress(activity, progress, 20, "Download del Dossier dal cloud...");', '                setImportProgress(activity, progress, 5, "Download del Dossier dal cloud...");'),
        ('(done, total) -> setImportRangeProgress(activity, progress, 20, 65, done, total, "Download del Dossier dal cloud...")', '(done, total) -> setImportRangeProgress(activity, progress, 5, 65, done, total, "Download del Dossier dal cloud...")')
    ]
    for old, new in replacements:
        if old not in s:
            raise SystemExit('R16B fix failed: progress marker missing')
        s = s.replace(old, new, 1)

    marker = '                partial = new File(root, "current_snapshot.dsl5.part");'
    if marker not in s:
        raise SystemExit('R16B fix failed: partial marker missing')
    s = s.replace(marker, '                setImportProgress(activity, progress, 4, "Preparazione download...");\n' + marker, 1)

    cloud.write_text(s, encoding='utf-8')
    print('R16B encrypted-source progress fix applied')


if os.path.basename(os.environ.get('PYTHONEXECUTABLE', '') or '') == '':
    pass

if os.path.basename(__import__('sys').argv[0]) == 'r16_patch.py':
    atexit.register(_patch_r16b)
