package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.json.JSONObject;
import org.junit.Test;

import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.List;

public class R18ResumeRuntimeTest {

    @Test
    public void pendingAuthenticatedImportIsRecognizedWithoutRepeatingLogin() throws Exception {
        JSONObject cfg = new JSONObject();
        cfg.put("associationStatus", "import_pending");
        assertTrue(R12CloudManager.pendingExistingImportAvailable(cfg, "123456789012345678901234567890"));

        cfg.put("associationStatus", "active");
        assertFalse(R12CloudManager.pendingExistingImportAvailable(cfg, "123456789012345678901234567890"));

        cfg.put("associationStatus", "import_pending");
        assertFalse(R12CloudManager.pendingExistingImportAvailable(cfg, "short"));
    }

    @Test
    public void completedDownloadedSnapshotCanBeReusedOnResume() throws Exception {
        File partial = File.createTempFile("r18_resume_", ".dsl5.part");
        try (FileOutputStream out = new FileOutputStream(partial)) {
            out.write(new byte[4096]);
        }
        try {
            assertTrue(R12CloudManager.reusablePartialSnapshot(partial, 4096L));
            assertFalse(R12CloudManager.reusablePartialSnapshot(partial, 4095L));
        } finally {
            partial.delete();
        }
    }

    @Test
    public void integrityProgressIsRealButThrottledToAvoidUiSlowdown() throws Exception {
        byte[] recovery = new byte[32];
        for (int i = 0; i < recovery.length; i++) recovery[i] = (byte) (i * 11 + 5);

        byte[] plain = new byte[8 * 1024 * 1024];
        for (int i = 0; i < plain.length; i++) plain[i] = (byte) (i * 17 + (i >>> 9));

        JSONObject meta = new JSONObject();
        meta.put("kind", "r18-progress-throttle-test");
        byte[] packed = R12Crypto.encryptDsl5(plain, recovery, meta);

        File snapshot = File.createTempFile("r18_integrity_", ".dsl5");
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

        assertFalse("No integrity progress callbacks", percentages.isEmpty());
        boolean intermediate = false;
        for (int value : percentages) {
            if (value > 65 && value < 78) intermediate = true;
        }
        assertTrue("Integrity progress did not move inside 65-78", intermediate);
        assertTrue("Progress callbacks were not throttled", percentages.size() < 200);
        assertTrue("Integrity progress did not reach 78", percentages.get(percentages.size() - 1) == 78);
    }
}
