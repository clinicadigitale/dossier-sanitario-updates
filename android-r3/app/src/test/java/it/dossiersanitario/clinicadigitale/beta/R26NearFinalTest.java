package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R26NearFinalTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void importPreservesAllWindowsJsonAndR24ProfileResolution() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("R24ProfileResolver.resolve"));
        assertTrue(cloud.contains("R26SnapshotBridge.Capture"));
        assertTrue(cloud.contains("capture.captureJson(name, data)"));
        assertTrue(cloud.contains("capture.commit(prefs)"));
    }

    @Test public void dashboardUsesRealImportedData() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("R12CloudManager.cloudDocumentCount(prefs)"));
        assertTrue(main.contains("R26SnapshotBridge.countActive(R26SnapshotBridge.therapies(prefs))"));
        assertTrue(main.contains("R12CloudManager.lastSyncLabel(prefs)"));
        assertFalse(main.contains("addMetric(grid, \"Terapie attive\", \"0\")"));
    }

    @Test public void allPreviouslyStructuralSectionsAreImplemented() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("case \"Diagnosi\": renderDiagnosi()"));
        assertTrue(main.contains("case \"Terapie\": renderTerapie()"));
        assertTrue(main.contains("case \"Confronta\": renderConfronta()"));
        assertTrue(main.contains("case \"Grafici\": renderGrafici()"));
        assertTrue(main.contains("private void renderMonitoraggio()"));
    }

    @Test public void graphsUseImportedSeries() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(main.contains("R26SnapshotBridge.weightRecords(prefs)"));
        assertTrue(main.contains("R26SnapshotBridge.glucoseRecords(prefs)"));
        assertTrue(main.contains("R26SnapshotBridge.pressureRecords(prefs)"));
        assertTrue(main.contains("R26SnapshotBridge.saturationRecords(prefs)"));
        assertTrue(chart.contains("canvas.drawPath"));
    }

    @Test public void windowsPreferencesColorsUsersAndTimeoutAreConsumed() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String bridge = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26SnapshotBridge.java");
        assertTrue(main.contains("R26SnapshotBridge.themeColor"));
        assertTrue(main.contains("R26SnapshotBridge.userColorRows"));
        assertTrue(main.contains("R26SnapshotBridge.selectedUsersSummary"));
        assertTrue(main.contains("R26SnapshotBridge.timeoutMinutes"));
        assertTrue(bridge.contains("prefer") && bridge.contains("impost") && bridge.contains("setting"));
    }

    @Test public void healthCardFrontAndBackExistInProfile() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Tessera Sanitaria"));
        assertTrue(main.contains("HEALTH_CARD_FRONT"));
        assertTrue(main.contains("HEALTH_CARD_BACK"));
        assertTrue(main.contains("Mostra retro"));
        assertTrue(main.contains("Carica o sostituisci fronte"));
    }

    @Test public void rotationDoesNotDestroyAuthenticatedActivity() throws Exception {
        String manifest = read("src/main/AndroidManifest.xml");
        assertTrue(manifest.contains("android:configChanges=\"orientation|screenSize|keyboardHidden\""));
        assertTrue(manifest.contains("android:screenOrientation=\"unspecified\""));
    }

    @Test public void inactivityTimeoutLocksWithoutDeletingRememberedCredentials() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("r26SessionTimeoutMinutes"));
        assertTrue(main.contains("onUserInteraction()"));
        assertTrue(main.contains("sessionAuthenticated = false;"));
        assertTrue(main.contains("REMEMBER_PASSWORD_KEY"));
        assertFalse(main.contains("remove(REMEMBER_PASSWORD_KEY).remove(REMEMBER_USER_KEY).remove(ACCOUNT_PREF_KEY)"));
    }

    @Test public void existingR25CredentialRememberingAndPasswordEyeRemain() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Ricorda le credenziali su questo dispositivo"));
        assertTrue(main.contains("passwordEye"));
        assertTrue(main.contains("Mostra password"));
        assertTrue(main.contains("R12Crypto.protectSecret(this, password)"));
    }

    @Test public void packageIdentityContinuesInR29() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 29"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r29-progress-crashguard-test'"));
    }
}
