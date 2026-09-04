package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class R17ProgressRuntimeTest {

    @Test
    public void fullProgressModelStartsAtZeroAndUsesRequiredRanges() {
        assertEquals(0, R12CloudManager.IMPORT_PROGRESS_START);
        assertEquals(5, R12CloudManager.DOWNLOAD_PROGRESS_START);
        assertEquals(65, R12CloudManager.DOWNLOAD_PROGRESS_END);
        assertEquals(65, R12CloudManager.INTEGRITY_PROGRESS_START);
        assertEquals(78, R12CloudManager.INTEGRITY_PROGRESS_END);
        assertEquals(78, R12CloudManager.DATA_PROGRESS_START);
        assertEquals(96, R12CloudManager.DATA_PROGRESS_END);

        assertEquals(5, R12CloudManager.importRangePercent(5, 65, 0, 1000));
        assertEquals(35, R12CloudManager.importRangePercent(5, 65, 500, 1000));
        assertEquals(65, R12CloudManager.importRangePercent(5, 65, 1000, 1000));
        assertEquals(65, R12CloudManager.importRangePercent(65, 78, 0, 1000));
        assertEquals(71, R12CloudManager.importRangePercent(65, 78, 500, 1000));
        assertEquals(78, R12CloudManager.importRangePercent(65, 78, 1000, 1000));
    }

    @Test
    public void integrityVerificationProducesIntermediateProgressInsteadOfStickingAt65() throws Exception {
        byte[] recovery = new byte[32];
        for (int i = 0; i < recovery.length; i++) recovery[i] = (byte) (i * 7 + 3);

        byte[] plain = new byte[4 * 1024 * 1024];
        for (int i = 0; i < plain.length; i++) plain[i] = (byte) (i * 31 + (i >>> 8));

        byte[] iv = new byte[12];
        for (int i = 0; i < iv.length; i++) iv[i] = (byte) (0x41 + i);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(recovery, "AES"), new GCMParameterSpec(128, iv));
        byte[] encrypted = cipher.doFinal(plain);

        String metadata = "{\"format\":\"DSL5-AESGCM\",\"version\":1,\"iv\":\""
                + Base64.getEncoder().encodeToString(iv)
                + "\",\"kind\":\"r17-runtime-progress-test\"}";
        byte[] metaBytes = metadata.getBytes(StandardCharsets.UTF_8);

        ByteArrayOutputStream packed = new ByteArrayOutputStream();
        packed.write("DSL5ENC1".getBytes(StandardCharsets.US_ASCII));
        packed.write(ByteBuffer.allocate(4).putInt(metaBytes.length).array());
        packed.write(metaBytes);
        packed.write(encrypted);

        File snapshot = File.createTempFile("r17_progress_", ".dsl5");
        try (FileOutputStream out = new FileOutputStream(snapshot)) {
            out.write(packed.toByteArray());
        }

        List<Integer> percentages = new ArrayList<>();
        try {
            R12CloudManager.verifySnapshotIntegrityCore(snapshot, recovery, (done, total) -> {
                percentages.add(R12CloudManager.importRangePercent(
                        R12CloudManager.INTEGRITY_PROGRESS_START,
                        R12CloudManager.INTEGRITY_PROGRESS_END,
                        done,
                        total));
            });
        } finally {
            snapshot.delete();
        }

        assertFalse("No progress callbacks were emitted", percentages.isEmpty());

        boolean sawIntermediate = false;
        int previous = 65;
        for (int value : percentages) {
            assertTrue("Progress regressed", value >= previous);
            assertTrue("Progress exceeded integrity range", value <= 78);
            if (value > 65 && value < 78) sawIntermediate = true;
            previous = value;
        }

        assertTrue("Integrity progress never moved between 65 and 78", sawIntermediate);
        assertEquals("Integrity progress did not reach 78", 78, (int) percentages.get(percentages.size() - 1));
    }
}
