package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R34SyncBiometricContactsLayoutTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    private String block(String source, String signature) {
        int start = source.indexOf(signature);
        assertTrue("Metodo non trovato: " + signature, start >= 0);
        int brace = source.indexOf('{', start);
        int depth = 0;
        for (int i = brace; i < source.length(); i++) {
            char c = source.charAt(i);
            if (c == '{') depth++;
            else if (c == '}') {
                depth--;
                if (depth == 0) return source.substring(start, i + 1);
            }
        }
        throw new AssertionError("Metodo non chiuso: " + signature);
    }

    @Test public void remoteChangeZipReadersDoNotCloseTheirParentStreams() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String batch = block(cloud, "private static List<RemoteEvent> parseBatch");
        String event = block(cloud, "private static RemoteEvent parseEvent");
        assertTrue(batch.contains("R25ZipEntryReader.readEntry(zip)"));
        assertTrue(event.contains("R25ZipEntryReader.readEntry(zip)"));
        assertFalse(batch.contains("parseEvent(readAll(zip)"));
        assertFalse(event.contains("byte[] bytes = readAll(zip)"));
    }

    @Test public void remoteMeasurementsAreMirroredIntoExactWindowsData() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String put = block(cloud, "private static void r34MirrorExactPut");
        String stores = block(cloud, "private static boolean r34ExactStore");
        assertTrue(stores.contains("measurements"));
        assertTrue(stores.contains("weightJourneys"));
        assertTrue(put.contains("R27ExactWindows.upsertData"));
        String apply = block(cloud, "private static boolean applyRemoteEvent");
        assertTrue(apply.contains("r34MirrorExactPut"));
        assertTrue(apply.contains("r34MirrorExactDelete"));
    }

    @Test public void biometricIsAnImmediateAlternativeToTotp() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String mfa = block(main, "private void r34ShowSecondFactor");
        assertTrue(mfa.contains("Biometria del dispositivo"));
        assertTrue(mfa.contains("Codice TOTP"));
        assertTrue(mfa.contains("SECOND_FACTOR_BIOMETRIC"));
        assertTrue(mfa.contains("SECOND_FACTOR_TOTP"));
        assertTrue(mfa.contains("R34BiometricAuth.available(this)"));
    }

    @Test public void totpDialogCanSwitchToBiometric() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String totp = block(main, "private void showStartupTotp");
        assertTrue(totp.contains("Usa biometria"));
        assertTrue(totp.contains("r34AuthenticateBiometric"));
    }

    @Test public void preferencesCanChangeSecondFactorMethod() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String prefs = block(main, "private void renderPreferenze()");
        assertTrue(prefs.contains("Metodo di seconda verifica"));
        assertTrue(prefs.contains("Modifica metodo di verifica"));
        String chooser = block(main, "private void r34ChoosePreferredSecondFactor");
        assertTrue(chooser.contains("Chiedi ogni volta"));
        assertTrue(chooser.contains("Biometria del dispositivo"));
        assertTrue(chooser.contains("Codice TOTP"));
        assertTrue(chooser.contains("SECOND_FACTOR_METHOD_KEY"));
    }

    @Test public void biometricBridgeUsesOnlyDeviceBiometricPrompt() throws Exception {
        String bio = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R34BiometricAuth.java");
        assertTrue(bio.contains("BiometricManager.BIOMETRIC_SUCCESS"));
        assertTrue(bio.contains("new BiometricPrompt.Builder(activity)"));
        assertTrue(bio.contains("setNegativeButton(\"Usa codice TOTP\""));
        assertTrue(bio.contains("onAuthenticationSucceeded"));
    }

    @Test public void emailsOpenMailtoAndPhonesOpenDialerWithoutCallingAutomatically() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String contact = block(main, "private void r34MakeContactAction");
        assertTrue(contact.contains("Intent.ACTION_SENDTO"));
        assertTrue(contact.contains("mailto:"));
        assertTrue(contact.contains("Intent.ACTION_DIAL"));
        assertTrue(contact.contains("tel:"));
        assertFalse(contact.contains("Intent.ACTION_CALL"));
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("r34MakeContactAction"));
    }

    @Test public void pressureLandscapeUsesTwoRows() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String landscape = block(main, "private LinearLayout r34MeasurementLandscapeRow");
        assertTrue(landscape.contains("Sistolica"));
        assertTrue(landscape.contains("Diastolica"));
        assertTrue(landscape.contains("Frequenza"));
        assertTrue(landscape.contains("device"));
        assertTrue(landscape.contains("LinearLayout first"));
        assertTrue(landscape.contains("LinearLayout second"));
    }

    @Test public void weighInsUseOneCompactLandscapeRowAndPaletteSeparator() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String history = block(main, "private void r33RenderWeightHistory");
        assertTrue(history.contains("line.setOrientation(LinearLayout.HORIZONTAL)"));
        assertTrue(history.contains("compactButton(\"Modifica\")"));
        assertTrue(history.contains("r34PaletteDivider()"));
        String divider = block(main, "private View r34PaletteDivider");
        assertTrue(divider.contains("R27ExactWindows.globalThemeColor"));
        assertTrue(divider.contains("dp(1)"));
    }

    @Test public void otherMeasurementsAdaptToLandscapeWithoutChangingPortraitCards() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String detail = block(main, "private void r31RenderMonitorDetail");
        assertTrue(detail.contains("boolean landscape=r34Landscape()"));
        assertTrue(detail.contains("r34MeasurementLandscapeRow"));
        assertTrue(detail.contains("LinearLayout c=card()"));
    }

    @Test public void manifestDeclaresBiometricPermissionOnlyAsNeeded() throws Exception {
        String manifest = read("src/main/AndroidManifest.xml");
        assertTrue(manifest.contains("android.permission.USE_BIOMETRIC"));
        assertFalse(manifest.contains("android.permission.CALL_PHONE"));
    }

    @Test public void versionIsR34SyncBiometricsContactsLayoutTest() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 34"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r34-sync-biometrics-contacts-layout-test'"));
    }
}
