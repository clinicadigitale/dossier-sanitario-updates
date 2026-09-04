package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.List;

@RunWith(RobolectricTestRunner.class)
@Config(manifest = Config.NONE, sdk = 34)
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

        JSONObject meta = new JSONObject();
        meta.put("kind", "r17-runtime-progress-test");
        byte[] packed = R12Crypto.encryptDsl5(plain, recovery, meta);

        File snapshot = File.createTempFile("r17_progress_", ".dsl5");
        try (FileOutputStream out = new FileOutputStream(snapshot)) {
            out.write(packed);
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
