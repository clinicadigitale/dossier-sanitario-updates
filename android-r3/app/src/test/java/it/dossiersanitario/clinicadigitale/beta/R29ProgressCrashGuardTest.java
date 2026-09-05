package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R29ProgressCrashGuardTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void migrationUsesDeterminateRealProgress() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("progressBarStyleHorizontal"));
        assertTrue(main.contains("setIndeterminate(false)"));
        assertTrue(main.contains("scaleR29(done, total, 0, 55)"));
        assertTrue(main.contains("scaleR29(done, total, 55, 44)"));
        assertTrue(main.contains("La percentuale segue i byte realmente verificati e gli elementi realmente importati."));
    }

    @Test public void decryptionProgressUsesActualBytes() throws Exception {
        String stream = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R22StreamingDsl5.java");
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(stream.contains("callback.onProgress(Math.min(done, total), total)"));
        assertTrue(cloud.contains("R22StreamingDsl5.decryptVerified(snapshot, verified, recovery, decryptProgress)"));
    }

    @Test public void windowsImportProgressUsesActualItems() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        assertTrue(exact.contains("interface ProgressCallback"));
        assertTrue(exact.contains("totalWork += readArray(zip, entries.get(folderForWork + \"indice_documenti.json\")).length()"));
        assertTrue(exact.contains("notifyProgress(progress, ++workDone, totalWork, \"Terapie\")"));
        assertTrue(exact.contains("notifyProgress(progress, ++workDone, totalWork, \"Documento: \" + progressName)"));
        assertTrue(exact.contains("Tessera Sanitaria · fronte"));
    }

    @Test public void backgroundImportCannotCloseAppOnThrowable() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(cloud.contains("catch (Throwable failure)"));
        assertTrue(main.contains("catch (Throwable failure)"));
        assertTrue(main.contains("showR29WindowsMigrationFailure"));
        assertTrue(main.contains("L'app resta aperta e il Dossier non viene mostrato con dati parziali."));
    }

    @Test public void postImportUiOpenIsCrashGuarded() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("private void safeOpenMainUiR29(Bundle state)"));
        assertTrue(main.contains("showR29UiFailure(state)"));
        assertTrue(main.contains("La sincronizzazione è stata conservata. L'app resta aperta invece di chiudersi."));
    }

    @Test public void loginStillOpensThroughAsyncGateAndNotOnCreate() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int start = main.indexOf("@Override protected void onCreate(Bundle state)");
        int end = main.indexOf("@Override protected void onSaveInstanceState", start);
        assertTrue(start >= 0 && end > start);
        String onCreate = main.substring(start, end);
        assertFalse(onCreate.contains("bootstrapR29ExactIfNeeded"));
        assertTrue(main.contains("dataExecutor.execute(() ->"));
        assertTrue(main.contains("openAuthenticatedDossierR28(state)"));
    }

    @Test public void priorSecurityAndWindowsImportRemain() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        assertTrue(main.contains("Ricorda le credenziali su questo dispositivo"));
        assertTrue(main.contains("passwordEye"));
        assertTrue(main.contains("showStartupTotp"));
        assertTrue(exact.contains("preferenze/impostazioni.json"));
        assertTrue(exact.contains("sicurezza/utenti_indicizzati.json"));
        assertTrue(exact.contains("tessera_sanitaria/"));
        assertTrue(exact.contains("indice_documenti.json"));
    }

    @Test public void packageVersionIsR29() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 29"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r29-progress-crashguard-test'"));
    }
}
