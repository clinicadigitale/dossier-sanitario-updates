package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class R23LocalSecretAndroidTest {
    @Test
    public void localSecretRoundTripUsesAndroidKeyStoreWithoutCallerIvFailure() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        String plain = "r23-local-secret-" + System.nanoTime();
        String packed = R12Crypto.protectSecret(context, plain);
        assertTrue(packed != null && packed.length() > 20);
        assertEquals(plain, R12Crypto.unprotectSecret(context, packed));
    }
}
