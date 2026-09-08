package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R35SecondFactorChoiceFixTest {
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

    @Test public void secondFactorChooserUsesVisibleDialogButtonsNotHiddenListItems() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chooser = block(main, "private void r34ShowSecondFactor");
        assertTrue(chooser.contains("Scegli il metodo di verifica"));
        assertTrue(chooser.contains("setPositiveButton(\"Biometria\""));
        assertTrue(chooser.contains("setNeutralButton(\"Codice TOTP\""));
        assertTrue(chooser.contains("setNegativeButton(\"Esci\""));
        assertFalse(chooser.contains("setItems("));
    }

    @Test public void onlyActuallyAvailableMethodsAreOffered() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chooser = block(main, "private void r34ShowSecondFactor");
        assertTrue(chooser.contains("boolean biometric = R34BiometricAuth.available(this)"));
        assertTrue(chooser.contains("boolean totp = account != null"));
        assertTrue(chooser.contains("if (biometric)"));
        assertTrue(chooser.contains("if (totp)"));
        assertTrue(chooser.contains("if (!biometric && totp)"));
        assertTrue(chooser.contains("if (biometric && !totp)"));
    }

    @Test public void biometricAndTotpActionsRouteToExistingVerifiedFlows() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chooser = block(main, "private void r34ShowSecondFactor");
        assertTrue(chooser.contains("r34AuthenticateBiometricForAccount(state, account, password)"));
        assertTrue(chooser.contains("r34ShowTotpForAccount(state, account, password)"));
    }

    @Test public void allR34FeaturesRemainPresent() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("R25ZipEntryReader.readEntry(zip)"));
        assertTrue(cloud.contains("r34MirrorExactPut"));
        assertTrue(main.contains("r34MakeContactAction"));
        assertTrue(main.contains("Intent.ACTION_DIAL"));
        assertTrue(main.contains("mailto:"));
        assertTrue(main.contains("r34MeasurementLandscapeRow"));
        assertTrue(main.contains("r34PaletteDivider"));
        assertTrue(main.contains("r33RenderWeightDetail"));
    }

    @Test public void preferencesStillAllowChangingThePreferredMethod() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chooser = block(main, "private void r34ChoosePreferredSecondFactor");
        assertTrue(chooser.contains("Chiedi ogni volta"));
        assertTrue(chooser.contains("Biometria del dispositivo"));
        assertTrue(chooser.contains("Codice TOTP"));
        assertTrue(chooser.contains("SECOND_FACTOR_METHOD_KEY"));
    }

    @Test public void versionIsR35SecondFactorChoiceFix() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 35"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r35-second-factor-choice-fix-test'"));
    }
}
