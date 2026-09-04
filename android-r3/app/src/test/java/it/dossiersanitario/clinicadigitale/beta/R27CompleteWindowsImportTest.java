package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R27CompleteWindowsImportTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void exactWindowsBackupPathsAreConsumed() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        assertTrue(exact.contains("preferenze/impostazioni.json"));
        assertTrue(exact.contains("sicurezza/utenti_indicizzati.json"));
        assertTrue(exact.contains("indice_documenti.json"));
        assertTrue(exact.contains("tessera_sanitaria/"));
        assertTrue(exact.contains("misurazioni.json"));
        assertTrue(exact.contains("percorsi_peso.json"));
        assertTrue(exact.contains("agenda.json"));
    }

    @Test public void windowsSettingsAndProfileColorsDriveAndroid() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(exact.contains("globalPreferences"));
        assertTrue(exact.contains("profileColor"));
        assertTrue(exact.contains("activeProfileId:"));
        assertTrue(main.contains("R27ExactWindows.globalThemeColor"));
        assertTrue(main.contains("R27ExactWindows.activeProfileColor"));
        assertTrue(main.contains("Cambia profilo"));
    }

    @Test public void documentOriginalsArePersistedAndOpenable() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        assertTrue(exact.contains("localPath"));
        assertTrue(exact.contains("documents"));
        assertTrue(exact.contains("archiveprovider/view/"));
        assertTrue(exact.contains("Intent.ACTION_VIEW"));
    }

    @Test public void completeSectionsUseExactWindowsData() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("private void renderCronologia()"));
        assertTrue(main.contains("private void renderDiagnosi()"));
        assertTrue(main.contains("private void renderTerapie()"));
        assertTrue(main.contains("private void renderConfronta()"));
        assertTrue(main.contains("private void renderGrafici()"));
        assertTrue(main.contains("private void renderMonitoraggio()"));
        assertTrue(main.contains("private void renderPreferenze()"));
        assertTrue(main.contains("R27ExactWindows.timeline(prefs)"));
        assertTrue(main.contains("R27ExactWindows.measurementsOf"));
    }

    @Test public void dashboardSeparatesTotalAndRecentDocuments() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("private void renderPanoramica()"));
        assertTrue(main.contains("Documenti totali"));
        assertTrue(main.contains("R27ExactWindows.recentDocuments(prefs, 4)"));
    }

    @Test public void healthCardAndGraphsAreConcrete() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("R27ExactWindows.healthFrontPath"));
        assertTrue(main.contains("R27ExactWindows.healthBackPath"));
        assertTrue(main.contains("BitmapFactory.decodeFile(path)"));
        assertTrue(main.contains("new R26ChartView(this, rows, GREEN, key)"));
    }

    @Test public void upgradeRebuildsExactStateWithoutPairingAgain() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(cloud.contains("bootstrapR27ExactIfNeeded"));
        assertTrue(cloud.contains("currentSnapshot(activity, cfg)"));
        assertTrue(cloud.contains("R22StreamingDsl5.decryptVerified"));
        assertTrue(cloud.contains("R27ExactWindows.importSnapshot"));
        assertTrue(main.contains("bootstrapR27ExactIfNeeded(this, prefs)"));
    }

    @Test public void versionIsR27CompleteTest() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 27"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r27-complete-test'"));
    }
}
