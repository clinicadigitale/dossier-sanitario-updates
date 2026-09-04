package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import org.junit.Test;
import org.junit.runner.RunWith;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Base64;
import java.util.concurrent.atomic.AtomicInteger;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

@RunWith(AndroidJUnit4.class)
public class R21FastDsl5AndroidTest {
    @Test
    public void fastDsl5VerificationIsPracticalOnAndroidRuntime() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        byte[] key = new byte[32];
        for (int i = 0; i < key.length; i++) key[i] = (byte) (i * 9 + 17);
        byte[] plain = new byte[16 * 1024 * 1024];
        for (int i = 0; i < plain.length; i++) plain[i] = (byte) (i * 29 + (i >>> 12));

        File snapshot = makeDsl5(context, plain, key);
        File verified = new File(context.getCacheDir(), "r21_verified_runtime.zip");
        AtomicInteger callbacks = new AtomicInteger();
        long started = android.os.SystemClock.elapsedRealtime();
        try {
            R21FastDsl5.decryptVerified(snapshot, verified, key, (done, total) -> callbacks.incrementAndGet());
            long elapsed = android.os.SystemClock.elapsedRealtime() - started;
            assertArrayEquals(plain, Files.readAllBytes(verified.toPath()));
            assertTrue("R21 fast verification too slow: " + elapsed + " ms", elapsed < 30000L);
            assertTrue("Progress callbacks unexpectedly excessive: " + callbacks.get(), callbacks.get() <= 20);
        } finally {
            snapshot.delete();
            verified.delete();
        }
    }

    private static File makeDsl5(Context context, byte[] plain, byte[] key) throws Exception {
        byte[] iv = new byte[12];
        for (int i = 0; i < iv.length; i++) iv[i] = (byte) (0x61 + i);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, iv));
        byte[] encrypted = cipher.doFinal(plain);
        String metadata = "{\"format\":\"DSL5-AESGCM\",\"version\":1,\"iv\":\""
                + Base64.getEncoder().encodeToString(iv) + "\"}";
        byte[] meta = metadata.getBytes(StandardCharsets.UTF_8);
        ByteArrayOutputStream packed = new ByteArrayOutputStream();
        packed.write("DSL5ENC1".getBytes(StandardCharsets.US_ASCII));
        packed.write(ByteBuffer.allocate(4).putInt(meta.length).array());
        packed.write(meta);
        packed.write(encrypted);
        File file = new File(context.getCacheDir(), "r21_runtime.dsl5");
        try (FileOutputStream out = new FileOutputStream(file)) {
            out.write(packed.toByteArray());
        }
        return file;
    }
}
