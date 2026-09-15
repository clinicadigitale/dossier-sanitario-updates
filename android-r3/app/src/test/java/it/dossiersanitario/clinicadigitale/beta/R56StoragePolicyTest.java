package it.dossiersanitario.clinicadigitale.beta;

import org.junit.Test;
import static org.junit.Assert.*;

public class R56StoragePolicyTest {
    @Test public void enoughSpaceReportsExpectedRemaining() {
        long gb=1024L*1024L*1024L;
        R56StoragePolicy.Result r=R56StoragePolicy.evaluate(250L*1024L*1024L, 4L*gb);
        assertTrue(r.enough);
        assertEquals(4L*gb-250L*1024L*1024L,r.remainingBytes);
        assertFalse(r.lowAfter);
    }

    @Test public void insufficientSpaceBlocksOfflineCopy() {
        R56StoragePolicy.Result r=R56StoragePolicy.evaluate(600L*1024L*1024L, 500L*1024L*1024L);
        assertFalse(r.enough);
        assertEquals(0L,r.remainingBytes);
    }

    @Test public void lowSpaceWarningKeepsUserInControl() {
        R56StoragePolicy.Result r=R56StoragePolicy.evaluate(800L*1024L*1024L, 1024L*1024L*1024L);
        assertTrue(r.enough);
        assertTrue(r.lowAfter);
    }
}
