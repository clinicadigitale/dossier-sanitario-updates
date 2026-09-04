package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R24AdminProfileResumeTest {

    @Test
    public void verifiedAccountIsPersistedBeforeFirstImport() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        int start = cloud.indexOf("private static void prepareExistingAccount");
        int end = cloud.indexOf("private static JSONObject findExistingAccountInSecurityBundle", start);
        assertTrue(start >= 0 && end > start);
        String block = cloud.substring(start, end);
        assertTrue(block.contains("persistExistingImportCheckpoint"));
        assertTrue(block.contains("putString(ACCOUNT_KEY, account.toString())"));
        assertFalse(block.contains("verifyTotp"));
    }

    @Test
    public void startupRecoversPendingAccountAndStillRequiresLogin() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("recoverPendingAccountForLogin(this, prefs)"));
        assertTrue(main.contains("showLoginScreen(state, account)"));
        assertTrue(main.contains("Il Dossier non viene aperto automaticamente all'avvio."));
        assertTrue(main.contains("if (!dossierSynchronized)"));
        assertTrue(main.contains("showPendingImportScreen();"));
    }

    @Test
    public void existingImportResolvesProfileBeforeRejectingGenericInvite() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        int start = cloud.indexOf("private static void importSnapshotWithProgress");
        int end = cloud.indexOf("private static void finalizeExistingConnectionProgress", start);
        assertTrue(start >= 0 && end > start);
        String block = cloud.substring(start, end);
        assertTrue(block.contains("R24ProfileResolver.resolve"));
        assertTrue(block.contains("cfg.put(\"linkedProfileId\", linked)"));
        assertTrue(block.contains("cfg.put(\"profileName\", resolvedProfile.name)"));
    }

    @Test
    public void windowsGenericInviteIsHandledAsAdministratorResolutionNotAsMissingProfile() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("cfg.put(\"accountDisplayName\", account.optString(\"displayName\", \"\"))"));
        assertTrue(cloud.contains("\"administrator\".equals(cfg.optString(\"accessLevel\", \"\"))"));
    }

    private static String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }
}
