package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class R20CheckpointAndroidTest {
    @Test
    public void androidKeystoreCheckpointRoundTripWorksOnRealAndroidRuntime() throws Exception {
        Context context = ApplicationProvider.getApplicationContext();
        assertTrue(R20CheckpointCrypto.runtimeSelfTest(context));

        StringBuilder large = new StringBuilder(220_000);
        for (int i = 0; i < 220_000; i++) large.append((char) ('A' + (i % 26)));
        String plain = large.toString();
        String packed = R20CheckpointCrypto.protect(context, plain);
        assertTrue(packed.startsWith("R20K1."));
        assertEquals(plain, R20CheckpointCrypto.unprotect(context, packed));
    }
}
