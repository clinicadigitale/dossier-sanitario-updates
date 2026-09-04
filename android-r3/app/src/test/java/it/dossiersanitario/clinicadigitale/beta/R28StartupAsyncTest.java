package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R28StartupAsyncTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void onCreateNeverRebuildsWindowsSnapshotSynchronously() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int start = main.indexOf("@Override protected void onCreate(Bundle state)");
        int end = main.indexOf("@Override protected void onSaveInstanceState", start);
        assertTrue(start >= 0 && end > start);
        String onCreate = main.substring(start, end);
        assertFalse(onCreate.contains("bootstrapR27ExactIfNeeded"));
        assertTrue(onCreate.contains("showStartupGate(state)"));
    }

    @Test public void exactWindowsMigrationRunsOnlyAfterAuthenticationAndOffUiThread() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("private void openAuthenticatedDossierR28(Bundle state)"));
        assertTrue(main.contains("dataExecutor.execute(() ->"));
        assertTrue(main.contains("R12CloudManager.bootstrapR27ExactIfNeeded(this, prefs)"));
        assertTrue(main.contains("showR28WindowsMigrationScreen()"));
        assertTrue(main.contains("showR28WindowsMigrationFailure(state)"));
    }

    @Test public void passwordAndTotpSuccessUseSameAuthenticatedOpenGate() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int first = main.indexOf("openAuthenticatedDossierR28(state)");
        int second = main.indexOf("openAuthenticatedDossierR28(state)", first + 1);
        assertTrue(first >= 0 && second > first);
    }

    @Test public void securityAndR27ExactImportRemain() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(main.contains("Ricorda le credenziali su questo dispositivo"));
        assertTrue(main.contains("passwordEye"));
        assertTrue(main.contains("Mostra password"));
        assertTrue(main.contains("showStartupTotp"));
        assertTrue(cloud.contains("R27ExactWindows.importSnapshot(activity, prefs, cfg, verifiedZip)"));
    }

    @Test public void packageVersionIsR28() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 28"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r28-startup-async-test'"));
    }
}
