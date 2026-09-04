package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class R19TransactionRuntimeTest {

    @Test
    public void pendingCheckpointCanBeResumedWithoutPrimaryConfigState() {
        String protectedCheckpoint = "123456789012345678901234567890";
        assertTrue(R12CloudManager.pendingExistingImportAvailable(protectedCheckpoint));
        assertFalse(R12CloudManager.pendingExistingImportAvailable("short"));
    }

    @Test
    public void previousR18PendingStateContractStillWorksForExistingInstallations() {
        String protectedCheckpoint = "123456789012345678901234567890";
        assertTrue(R12CloudManager.pendingExistingImportAvailable("import_pending", protectedCheckpoint));
        assertFalse(R12CloudManager.pendingExistingImportAvailable("active", protectedCheckpoint));
    }

    @Test
    public void progressRangesRemainFrozenFromR17R18() {
        assertTrue(R12CloudManager.IMPORT_PROGRESS_START == 0);
        assertTrue(R12CloudManager.DOWNLOAD_PROGRESS_START == 5);
        assertTrue(R12CloudManager.DOWNLOAD_PROGRESS_END == 65);
        assertTrue(R12CloudManager.INTEGRITY_PROGRESS_START == 65);
        assertTrue(R12CloudManager.INTEGRITY_PROGRESS_END == 78);
        assertTrue(R12CloudManager.DATA_PROGRESS_START == 78);
        assertTrue(R12CloudManager.DATA_PROGRESS_END == 96);
    }
}
