package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class R22StreamingIntegrityTest {
    @Test
    public void decryptsStandardJceDsl5AndMatchesPlaintext() throws Exception {
        File dir = new File(System.getProperty("java.io.tmpdir"), "r22-jvm-" + System.nanoTime());
        assertTrue(dir.mkdirs());
        File encrypted = new File(dir, "snapshot.dsl5");
        File verified = new File(dir, "verified.zip");

        byte[] key = new byte[32];
        byte[] iv = new byte[12];
        new SecureRandom().nextBytes(key);
        new SecureRandom().nextBytes(iv);

        byte[] plain = new byte[3 * 1024 * 1024 + 333];
        for (int i = 0; i < plain.length; i++) plain[i] = (byte) (i * 31 + 7);
        writeDsl5Jce(encrypted, plain, key, iv);

        R22StreamingDsl5.decryptVerified(encrypted, verified, key, null);
        assertTrue(verified.isFile());
        assertArrayEquals(plain, readAll(verified));

        verified.delete();
        encrypted.delete();
        dir.delete();
    }

    @Test
    public void invalidTagNeverLeavesVerifiedPlaintext() throws Exception {
        File dir = new File(System.getProperty("java.io.tmpdir"), "r22-jvm-bad-" + System.nanoTime());
        assertTrue(dir.mkdirs());
        File encrypted = new File(dir, "snapshot.dsl5");
        File verified = new File(dir, "verified.zip");

        byte[] key = new byte[32];
        byte[] iv = new byte[12];
        new SecureRandom().nextBytes(key);
        new SecureRandom().nextBytes(iv);
        byte[] plain = "payload-test-r22".getBytes(StandardCharsets.UTF_8);
        writeDsl5Jce(encrypted, plain, key, iv);

        try (java.io.RandomAccessFile raf = new java.io.RandomAccessFile(encrypted, "rw")) {
            raf.seek(raf.length() - 1);
            int b = raf.read();
            raf.seek(raf.length() - 1);
            raf.write(b ^ 0x01);
        }

        try {
            R22StreamingDsl5.decryptVerified(encrypted, verified, key, null);
            fail("Expected authentication failure");
        } catch (Exception expected) {
            // expected
        }
        assertFalse(verified.exists());

        encrypted.delete();
        dir.delete();
    }

    private static void writeDsl5Jce(File out, byte[] plain, byte[] key, byte[] iv) throws Exception {
        String meta = "{\"format\":\"DSL5-AESGCM\",\"iv\":\"" + Base64.getEncoder().encodeToString(iv) + "\"}";
        byte[] metaBytes = meta.getBytes(StandardCharsets.UTF_8);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, iv));

        try (FileOutputStream output = new FileOutputStream(out)) {
            output.write("DSL5ENC1".getBytes(StandardCharsets.US_ASCII));
            output.write(ByteBuffer.allocate(4).putInt(metaBytes.length).array());
            output.write(metaBytes);
            byte[] encrypted = cipher.doFinal(plain);
            output.write(encrypted);
        }
    }

    private static byte[] readAll(File file) throws Exception {
        try (FileInputStream in = new FileInputStream(file); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) >= 0) {
                if (n > 0) out.write(buf, 0, n);
            }
            return out.toByteArray();
        }
    }
}
