package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import org.bouncycastle.crypto.engines.AESEngine;
import org.bouncycastle.crypto.modes.GCMBlockCipher;
import org.bouncycastle.crypto.params.AEADParameters;
import org.bouncycastle.crypto.params.KeyParameter;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.concurrent.atomic.AtomicInteger;

@RunWith(AndroidJUnit4.class)
public class R22LargeStreamingAndroidTest {
    private static final int PLAIN_SIZE = 160 * 1024 * 1024;
    private static final int CHUNK = 1024 * 1024;

    @Test
    public void verifies160MiBWithoutArchiveSizedHeapGrowth() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        File plain = new File(context.getCacheDir(), "r22_large_plain.bin");
        File snapshot = new File(context.getCacheDir(), "r22_large_snapshot.dsl5");
        File verified = new File(context.getCacheDir(), "r22_large_verified.zip");
        plain.delete(); snapshot.delete(); verified.delete();

        byte[] key = new byte[32];
        byte[] iv = new byte[12];
        for (int i = 0; i < key.length; i++) key[i] = (byte) (i * 13 + 11);
        for (int i = 0; i < iv.length; i++) iv[i] = (byte) (0x41 + i);

        try {
            byte[] expectedHash = createPatternFile(plain, PLAIN_SIZE);
            writeDsl5Streaming(plain, snapshot, key, iv);
            assertTrue(snapshot.length() > 150L * 1024L * 1024L);
            assertTrue(plain.delete());

            AtomicInteger callbacks = new AtomicInteger();
            long started = android.os.SystemClock.elapsedRealtime();
            R22StreamingDsl5.decryptVerified(snapshot, verified, key,
                    (done, total) -> callbacks.incrementAndGet());
            long elapsed = android.os.SystemClock.elapsedRealtime() - started;

            assertEquals(PLAIN_SIZE, verified.length());
            assertArrayEquals(expectedHash, sha256(verified));
            assertTrue("No progress callbacks", callbacks.get() > 0);
            assertTrue("R22 160 MiB verification exceeded 180 s: " + elapsed + " ms", elapsed < 180000L);
        } finally {
            plain.delete();
            snapshot.delete();
            verified.delete();
        }
    }

    private static byte[] createPatternFile(File file, int size) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buf = new byte[CHUNK];
        long offset = 0L;
        try (FileOutputStream out = new FileOutputStream(file)) {
            while (offset < size) {
                int n = (int) Math.min(buf.length, size - offset);
                for (int i = 0; i < n; i++) {
                    long p = offset + i;
                    buf[i] = (byte) ((p * 31L + (p >>> 12) + 17L) & 0xff);
                }
                out.write(buf, 0, n);
                digest.update(buf, 0, n);
                offset += n;
            }
            out.getFD().sync();
        }
        return digest.digest();
    }

    private static void writeDsl5Streaming(File plain, File out, byte[] key, byte[] iv) throws Exception {
        String metadata = "{\"format\":\"DSL5-AESGCM\",\"version\":1,\"iv\":\""
                + Base64.getEncoder().encodeToString(iv) + "\"}";
        byte[] meta = metadata.getBytes(StandardCharsets.UTF_8);

        GCMBlockCipher cipher = new GCMBlockCipher(AESEngine.newInstance());
        cipher.init(true, new AEADParameters(new KeyParameter(key), 128, iv));
        byte[] input = new byte[CHUNK];
        byte[] encrypted = new byte[CHUNK + 32];

        try (FileInputStream in = new FileInputStream(plain);
             FileOutputStream output = new FileOutputStream(out)) {
            output.write("DSL5ENC1".getBytes(StandardCharsets.US_ASCII));
            output.write(ByteBuffer.allocate(4).putInt(meta.length).array());
            output.write(meta);

            int n;
            while ((n = in.read(input)) >= 0) {
                if (n == 0) continue;
                int produced = cipher.processBytes(input, 0, n, encrypted, 0);
                if (produced > 0) output.write(encrypted, 0, produced);
            }
            int tail = cipher.doFinal(encrypted, 0);
            if (tail > 0) output.write(encrypted, 0, tail);
            output.getFD().sync();
        }
    }

    private static byte[] sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buf = new byte[CHUNK];
        try (FileInputStream in = new FileInputStream(file)) {
            int n;
            while ((n = in.read(buf)) >= 0) {
                if (n > 0) digest.update(buf, 0, n);
            }
        }
        return digest.digest();
    }
}
