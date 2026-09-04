package it.dossiersanitario.clinicadigitale.beta;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

final class R21FastDsl5 {
    interface ProgressCallback {
        void onProgress(long done, long total);
    }

    private static final byte[] MAGIC = "DSL5ENC1".getBytes(StandardCharsets.US_ASCII);
    private static final int INPUT_BUFFER = 1024 * 1024;

    private R21FastDsl5() {}

    static File decryptVerified(File snapshot, File output, byte[] recovery, ProgressCallback callback) throws Exception {
        if (snapshot == null || !snapshot.isFile() || snapshot.length() < 32L) {
            throw new Exception("Snapshot del Dossier non leggibile.");
        }
        if (output == null) throw new Exception("Area temporanea non disponibile.");
        File parent = output.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new Exception("Area temporanea non disponibile.");
        }
        if (output.exists() && !output.delete()) {
            throw new Exception("Area temporanea non disponibile.");
        }

        boolean success = false;
        try (FileInputStream source = new FileInputStream(snapshot);
             FileOutputStream plain = new FileOutputStream(output)) {
            byte[] header = readExact(source, 12);
            for (int i = 0; i < MAGIC.length; i++) {
                if (header[i] != MAGIC[i]) throw new Exception("Formato cifrato non riconosciuto.");
            }
            int metaLength = ByteBuffer.wrap(header, 8, 4).getInt();
            if (metaLength <= 0 || metaLength > 1024 * 1024) {
                throw new Exception("Metadati archivio non validi.");
            }
            byte[] metaBytes = readExact(source, metaLength);
            String metaText = new String(metaBytes, StandardCharsets.UTF_8);
            if (!Pattern.compile("\\\"format\\\"\\s*:\\s*\\\"DSL5-AESGCM\\\"").matcher(metaText).find()) {
                throw new Exception("Formato archivio cloud non valido.");
            }
            Matcher ivMatcher = Pattern.compile("\\\"iv\\\"\\s*:\\s*\\\"([A-Za-z0-9+/=]+)\\\"").matcher(metaText);
            if (!ivMatcher.find()) throw new Exception("IV archivio cloud non disponibile.");
            byte[] iv = Base64.getDecoder().decode(ivMatcher.group(1));
            if (iv.length != 12) throw new Exception("IV archivio cloud non valido.");

            long total = snapshot.length() - 12L - metaLength;
            if (total <= 16L) throw new Exception("Snapshot del Dossier incompleto.");

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(recovery, "AES"), new GCMParameterSpec(128, iv));

            byte[] input = new byte[INPUT_BUFFER];
            long done = 0L;
            int n;
            while ((n = source.read(input)) >= 0) {
                if (n == 0) continue;
                byte[] decoded = cipher.update(input, 0, n);
                if (decoded != null && decoded.length > 0) plain.write(decoded);
                done += n;
                if (callback != null) callback.onProgress(Math.min(done, total), total);
            }
            byte[] tail = cipher.doFinal();
            if (tail != null && tail.length > 0) plain.write(tail);
            if (callback != null) callback.onProgress(total, total);
            success = true;
            return output;
        } finally {
            if (!success && output.exists()) output.delete();
        }
    }

    private static byte[] readExact(FileInputStream in, int length) throws Exception {
        byte[] out = new byte[length];
        int offset = 0;
        while (offset < length) {
            int n = in.read(out, offset, length - offset);
            if (n < 0) throw new Exception("Snapshot del Dossier incompleto.");
            offset += n;
        }
        return out;
    }
}