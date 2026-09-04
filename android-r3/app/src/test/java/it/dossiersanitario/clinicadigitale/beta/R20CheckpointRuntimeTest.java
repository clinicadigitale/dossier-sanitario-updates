package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.file.Files;
import java.nio.file.Path;

public class R20CheckpointRuntimeTest {
    @Test
    public void r20PatchUsesDedicatedCheckpointCryptoAndPreservesResume() throws Exception {
        String cloud = Files.readString(Path.of("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java"));
        String crypto = Files.readString(Path.of("src/main/java/it/dossiersanitario/clinicadigitale/beta/R20CheckpointCrypto.java"));

        assertTrue(cloud.contains("R20CheckpointCrypto.protect(context, state.toString())"));
        assertTrue(cloud.contains("R20CheckpointCrypto.unprotect(activity, protectedState)"));
        assertTrue(cloud.contains("Riprendi importazione del Dossier"));
        assertTrue(cloud.contains("safeStartExistingImportProgress"));
        assertTrue(crypto.contains("clinica_digitale_r20_import_checkpoint"));
        assertTrue(crypto.contains("Self-test on the exact value before it is persisted"));
        assertTrue(crypto.contains("new int[]{256, 128}"));
        assertTrue(crypto.contains("store.deleteEntry(ALIAS)"));
        assertFalse(cloud.contains("R12Crypto.protectSecret(context, state.toString())"));
    }
}
