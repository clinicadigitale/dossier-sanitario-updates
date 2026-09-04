package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R23LoginIvFixTest {

    @Test
    public void localSecretEncryptionUsesProviderGeneratedIv() throws Exception {
        String crypto = new String(Files.readAllBytes(Paths.get("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12Crypto.java")), StandardCharsets.UTF_8);
        int start = crypto.indexOf("public static String protectSecret");
        int end = crypto.indexOf("public static String unprotectSecret", start);
        assertTrue(start >= 0 && end > start);
        String block = crypto.substring(start, end);
        assertTrue(block.contains("cipher.init(Cipher.ENCRYPT_MODE, key);"));
        assertTrue(block.contains("cipher.getIV()"));
        assertFalse(block.contains("Cipher.ENCRYPT_MODE, key, new GCMParameterSpec"));
    }

    @Test
    public void firstSynchronizationUsesCredentialsButNotTotp() throws Exception {
        String cloud = new String(Files.readAllBytes(Paths.get("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java")), StandardCharsets.UTF_8);
        int start = cloud.indexOf("private static void prepareExistingAccount");
        int end = cloud.indexOf("private static JSONObject findExistingAccountInSecurityBundle", start);
        assertTrue(start >= 0 && end > start);
        String block = cloud.substring(start, end);
        assertTrue(block.contains("verifyAccountPassword"));
        assertTrue(block.contains("persistExistingImportCheckpoint"));
        assertTrue(block.contains("safeStartExistingImportProgress"));
        assertFalse(block.contains("showExistingTotpVerification"));
        assertFalse(block.contains("verifyTotp"));
    }

    @Test
    public void startupIsGatedByCredentialsAndTotpOnlyAfterActiveSync() throws Exception {
        String main = new String(Files.readAllBytes(Paths.get("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java")), StandardCharsets.UTF_8);
        assertTrue(main.contains("showStartupGate(state);"));
        assertTrue(main.contains("Il Dossier non viene aperto automaticamente all'avvio."));
        assertTrue(main.contains("Ricorda le credenziali su questo dispositivo"));
        assertTrue(main.contains("boolean dossierSynchronized = \"active\".equals"));
        assertTrue(main.contains("if (!dossierSynchronized)"));
        assertTrue(main.contains("showPendingImportScreen();"));
        assertTrue(main.contains("showStartupTotp(state, secret);"));
        assertTrue(main.contains("Il TOTP non è richiesto finché la prima sincronizzazione del Dossier non è completata."));
    }
}
