package it.dossiersanitario.clinicadigitale.beta;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

final class R57BoundedGcmDecryptor {
    interface Progress { void onBytes(long done, long total); }
    private static final byte[] MAGIC = "DSL5ENC1".getBytes(StandardCharsets.US_ASCII);
    private static final int TAG_BYTES = 16;
    private static final int CHUNK = 1024 * 1024;
    private static final long R_HI = 0xe100000000000000L;

    private R57BoundedGcmDecryptor() {}

    static void decrypt(File source, File target, byte[] keyRaw, Progress progress) throws Exception {
        if (source == null || !source.isFile() || source.length() <= 12L + TAG_BYTES) throw new Exception("Archivio cifrato non disponibile");
        if (keyRaw == null || !(keyRaw.length == 16 || keyRaw.length == 24 || keyRaw.length == 32)) throw new Exception("Chiave archivio non valida");
        if (target.exists() && !target.delete()) throw new Exception("Impossibile preparare il file temporaneo");

        boolean authenticated = false;
        try (FileInputStream in = new FileInputStream(source); FileOutputStream out = new FileOutputStream(target, false)) {
            byte[] header = readExact(in, 12);
            if (!Arrays.equals(Arrays.copyOfRange(header, 0, 8), MAGIC)) throw new Exception("Formato cifrato non riconosciuto");
            int metaLength = ByteBuffer.wrap(header, 8, 4).getInt();
            if (metaLength <= 0 || metaLength > 1024 * 1024) throw new Exception("Metadati archivio non validi");
            byte[] metaBytes = readExact(in, metaLength);
            String meta = new String(metaBytes, StandardCharsets.UTF_8);
            if (!"DSL5-AESGCM".equals(jsonString(meta, "format"))) throw new Exception("Formato archivio cloud non valido");
            byte[] iv = Base64.getDecoder().decode(jsonString(meta, "iv"));
            if (iv.length != 12) throw new Exception("IV archivio non valido");

            long packedPayload = source.length() - 12L - metaLength;
            if (packedPayload <= TAG_BYTES) throw new Exception("Archivio cifrato incompleto");
            long cipherLength = packedPayload - TAG_BYTES;
            if ((cipherLength + 15L) / 16L >= 0xfffffffEL) throw new Exception("Archivio cifrato troppo grande per AES-GCM");

            SecretKeySpec key = new SecretKeySpec(keyRaw, "AES");
            Cipher ecb = Cipher.getInstance("AES/ECB/NoPadding");
            ecb.init(Cipher.ENCRYPT_MODE, key);
            byte[] h = ecb.doFinal(new byte[16]);
            long[] table = buildMultiplyTable(h);

            byte[] j0 = new byte[16];
            System.arraycopy(iv, 0, j0, 0, 12);
            j0[15] = 1;
            byte[] ctrIv = j0.clone();
            increment32(ctrIv);
            Cipher ctr = Cipher.getInstance("AES/CTR/NoPadding");
            ctr.init(Cipher.DECRYPT_MODE, key, new IvParameterSpec(ctrIv));

            long[] ghash = new long[]{0L, 0L};
            byte[] cipherBuf = new byte[CHUNK];
            byte[] plainBuf = new byte[CHUNK + 16];
            long remaining = cipherLength;
            long done = 0L;
            while (remaining > 0L) {
                int want = (int)Math.min((long)cipherBuf.length, remaining);
                readFully(in, cipherBuf, want);
                ghashCipherChunk(ghash, table, cipherBuf, want);
                int produced = ctr.update(cipherBuf, 0, want, plainBuf, 0);
                if (produced > 0) out.write(plainBuf, 0, produced);
                remaining -= want;
                done += want;
                if (progress != null) progress.onBytes(done, Math.max(1L, cipherLength));
            }
            byte[] tail = ctr.doFinal();
            if (tail != null && tail.length > 0) out.write(tail);

            byte[] receivedTag = readExact(in, TAG_BYTES);
            applyLengthBlock(ghash, table, 0L, cipherLength * 8L);
            byte[] e0 = ecb.doFinal(j0);
            byte[] expectedTag = new byte[TAG_BYTES];
            long eHi = readLong(e0, 0), eLo = readLong(e0, 8);
            writeLong(expectedTag, 0, eHi ^ ghash[0]);
            writeLong(expectedTag, 8, eLo ^ ghash[1]);
            if (!MessageDigest.isEqual(expectedTag, receivedTag)) throw new Exception("Verifica autenticità della copia Windows non riuscita");

            out.flush();
            out.getFD().sync();
            authenticated = true;
            if (progress != null) progress.onBytes(cipherLength, Math.max(1L, cipherLength));
        } finally {
            if (!authenticated && target.exists()) target.delete();
        }
        if (!target.isFile()) throw new Exception("Snapshot Windows decifrato non disponibile");
    }

    static byte[] computeTagForTest(byte[] keyRaw, byte[] iv, byte[] ciphertext) throws Exception {
        SecretKeySpec key = new SecretKeySpec(keyRaw, "AES");
        Cipher ecb = Cipher.getInstance("AES/ECB/NoPadding");
        ecb.init(Cipher.ENCRYPT_MODE, key);
        byte[] h = ecb.doFinal(new byte[16]);
        long[] table = buildMultiplyTable(h);
        long[] ghash = new long[]{0L, 0L};
        ghashCipherChunk(ghash, table, ciphertext, ciphertext.length);
        applyLengthBlock(ghash, table, 0L, ((long)ciphertext.length) * 8L);
        byte[] j0 = new byte[16];
        System.arraycopy(iv, 0, j0, 0, 12);
        j0[15] = 1;
        byte[] e0 = ecb.doFinal(j0);
        byte[] tag = new byte[16];
        writeLong(tag, 0, readLong(e0, 0) ^ ghash[0]);
        writeLong(tag, 8, readLong(e0, 8) ^ ghash[1]);
        return tag;
    }

    private static String jsonString(String json, String field) throws Exception {
        Pattern p = Pattern.compile("\\\"" + Pattern.quote(field) + "\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"");
        Matcher m = p.matcher(json == null ? "" : json);
        if (!m.find()) throw new Exception("Metadati archivio incompleti");
        return m.group(1);
    }

    private static byte[] readExact(FileInputStream in, int length) throws Exception {
        byte[] out = new byte[length];
        readFully(in, out, length);
        return out;
    }

    private static void readFully(FileInputStream in, byte[] out, int length) throws Exception {
        int offset = 0;
        while (offset < length) {
            int n = in.read(out, offset, length - offset);
            if (n < 0) throw new Exception("Archivio cifrato incompleto");
            if (n == 0) continue;
            offset += n;
        }
    }

    private static void increment32(byte[] block) {
        for (int i = 15; i >= 12; i--) {
            block[i]++;
            if (block[i] != 0) return;
        }
    }

    private static long[] buildMultiplyTable(byte[] h) {
        long hHi = readLong(h, 0), hLo = readLong(h, 8);
        long[] table = new long[16 * 256 * 2];
        for (int pos = 0; pos < 16; pos++) {
            for (int value = 1; value < 256; value++) {
                long xHi = 0L, xLo = 0L;
                if (pos < 8) xHi = ((long)value & 0xffL) << ((7 - pos) * 8);
                else xLo = ((long)value & 0xffL) << ((15 - pos) * 8);
                long[] z = multiplyBitwise(xHi, xLo, hHi, hLo);
                int off = (pos * 256 + value) * 2;
                table[off] = z[0]; table[off + 1] = z[1];
            }
        }
        return table;
    }

    private static long[] multiplyBitwise(long xHi, long xLo, long hHi, long hLo) {
        long zHi = 0L, zLo = 0L, vHi = hHi, vLo = hLo;
        for (int i = 0; i < 128; i++) {
            boolean set = i < 64 ? ((xHi >>> (63 - i)) & 1L) != 0L : ((xLo >>> (127 - i)) & 1L) != 0L;
            if (set) { zHi ^= vHi; zLo ^= vLo; }
            boolean lsb = (vLo & 1L) != 0L;
            vLo = (vLo >>> 1) | (vHi << 63);
            vHi >>>= 1;
            if (lsb) vHi ^= R_HI;
        }
        return new long[]{zHi, zLo};
    }

    private static void ghashCipherChunk(long[] state, long[] table, byte[] data, int length) {
        int offset = 0;
        while (offset + 16 <= length) {
            long xHi = state[0] ^ readLong(data, offset);
            long xLo = state[1] ^ readLong(data, offset + 8);
            multiplyTableInto(state, table, xHi, xLo);
            offset += 16;
        }
        if (offset < length) {
            byte[] last = new byte[16];
            System.arraycopy(data, offset, last, 0, length - offset);
            long xHi = state[0] ^ readLong(last, 0);
            long xLo = state[1] ^ readLong(last, 8);
            multiplyTableInto(state, table, xHi, xLo);
        }
    }

    private static void applyLengthBlock(long[] state, long[] table, long aadBits, long cipherBits) {
        long xHi = state[0] ^ aadBits;
        long xLo = state[1] ^ cipherBits;
        multiplyTableInto(state, table, xHi, xLo);
    }

    private static void multiplyTableInto(long[] out, long[] table, long xHi, long xLo) {
        long zHi = 0L, zLo = 0L;
        for (int pos = 0; pos < 8; pos++) {
            int value = (int)((xHi >>> ((7 - pos) * 8)) & 0xffL);
            int off = (pos * 256 + value) * 2;
            zHi ^= table[off]; zLo ^= table[off + 1];
        }
        for (int pos = 8; pos < 16; pos++) {
            int value = (int)((xLo >>> ((15 - pos) * 8)) & 0xffL);
            int off = (pos * 256 + value) * 2;
            zHi ^= table[off]; zLo ^= table[off + 1];
        }
        out[0] = zHi; out[1] = zLo;
    }

    private static long readLong(byte[] a, int off) {
        return ((long)(a[off] & 0xff) << 56) | ((long)(a[off+1] & 0xff) << 48) |
               ((long)(a[off+2] & 0xff) << 40) | ((long)(a[off+3] & 0xff) << 32) |
               ((long)(a[off+4] & 0xff) << 24) | ((long)(a[off+5] & 0xff) << 16) |
               ((long)(a[off+6] & 0xff) << 8) | (long)(a[off+7] & 0xff);
    }

    private static void writeLong(byte[] a, int off, long value) {
        for (int i = 7; i >= 0; i--) { a[off + i] = (byte)value; value >>>= 8; }
    }
}
