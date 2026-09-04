package it.dossiersanitario.clinicadigitale.beta;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.bouncycastle.crypto.engines.AESEngine;
import org.bouncycastle.crypto.modes.GCMBlockCipher;
import org.bouncycastle.crypto.params.AEADParameters;
import org.bouncycastle.crypto.params.KeyParameter;

/**
 * Bounded-memory DSL5 AES-GCM verifier/decrypter.
 *
 * Android's platform AES/GCM provider is allowed to retain plaintext until
 * authentication succeeds. With a single large GCM record this can make heap
 * usage grow with the archive size. This implementation uses Bouncy Castle's
 * lightweight GCM engine, which retains only the authentication tail while
 * streaming plaintext into a temporary file. The file is promoted/used only
 * after doFinal() verifies the GCM tag; on any failure it is deleted.
 */
final class R22StreamingDsl5 {
    interface ProgressCallback {
        void onProgress(long done, long total);
    }

    private static final byte[] MAGIC = "DSL5ENC1".getBytes(StandardCharsets.US_ASCII);
    private static final int INPUT_BUFFER = 1024 * 1024;
    private static final long PROGRESS_MIN_INTERVAL_MS = 200L;

    private R22StreamingDsl5() {}

    static File decryptVerified(File snapshot, File output, byte[] recovery, ProgressCallback callback) throws Exception {
        if (snapshot == null || !snapshot.isFile() || snapshot.length() < 32L) {
            throw new Exception("Snapshot del Dossier non leggibile.");
        }
        if (output == null) throw new Exception("Area temporanea non disponibile.");
        if (recovery == null || !(recovery.length == 16 || recovery.length == 24 || recovery.length == 32)) {
            throw new Exception("Chiave di recupero del Dossier non valida.");
        }

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

            GCMBlockCipher cipher = new GCMBlockCipher(AESEngine.newInstance());
            cipher.init(false, new AEADParameters(new KeyParameter(recovery), 128, iv));

            byte[] input = new byte[INPUT_BUFFER];
            byte[] decoded = new byte[INPUT_BUFFER + 32];
            long done = 0L;
            long lastProgressAt = 0L;
            int n;

            while ((n = source.read(input)) >= 0) {
                if (n == 0) continue;
                int produced = cipher.processBytes(input, 0, n, decoded, 0);
                if (produced > 0) plain.write(decoded, 0, produced);
                done += n;

                if (callback != null) {
                    long now = android.os.SystemClock.elapsedRealtime();
                    if (lastProgressAt == 0L || now - lastProgressAt >= PROGRESS_MIN_INTERVAL_MS || done >= total) {
                        callback.onProgress(Math.min(done, total), total);
                        lastProgressAt = now;
                    }
                }
            }

            int tail = cipher.doFinal(decoded, 0);
            if (tail > 0) plain.write(decoded, 0, tail);
            plain.getFD().sync();

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
