package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R42RealDeviceLandscapeGraphSyncFixTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    private String block(String source, String signature) {
        int start = source.indexOf(signature);
        assertTrue("Metodo non trovato: " + signature, start >= 0);
        int brace = source.indexOf('{', start), depth = 0;
        for (int i = brace; i < source.length(); i++) {
            char c = source.charAt(i);
            if (c == '{') depth++;
            else if (c == '}' && --depth == 0) return source.substring(start, i + 1);
        }
        throw new AssertionError("Metodo non chiuso: " + signature);
    }

    @Test public void emergencyAndEveryStandardRowActuallyFillLandscapeCardWidth() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(label.contains("0.48f"));
        assertTrue(label.contains("0.52f"));
        assertTrue(label.contains("dp(92)"));
        String addIf = block(main, "private void r31AddIf");
        assertTrue(addIf.contains("labelValue(label, value.trim())"));
        String emergency = block(main, "private void renderDatiEmergenza");
        assertTrue(emergency.contains("r31AddIf(c, \"Nominativo contatto\""));
        assertTrue(emergency.contains("r31AddIf(c, \"Telefono contatto\""));
        assertTrue(emergency.contains("r31AddIf(c, \"Allergie rilevanti\""));
        assertTrue(emergency.contains("r31AddIf(c, \"Condizioni o dispositivi rilevanti\""));
    }

    @Test public void clinicalYearAxisCannotEmitOverlappingEveryTwoYearLabelsOnNarrowPhone() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        String axis = block(chart, "private void drawYearAxis");
        assertTrue(axis.contains("minimumSpacing"));
        assertTrue(axis.contains("maximumLabels"));
        assertTrue(axis.contains("rawStep"));
        assertTrue(axis.contains("years.remove(years.size() - 2)"));
        assertTrue(axis.contains("years.add(y1)"));
        assertTrue(axis.contains("years.add(y2)"));
        assertTrue(chart.contains("private float yearX"));
        assertFalse(axis.contains("span <= 30 ? 2"));
    }

    @Test public void allChartsStillKeepWindowsReferenceLinesAndClinicalDateAxis() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("DashPathEffect"));
        assertTrue(chart.contains("drawReferenceLine"));
        assertTrue(chart.contains("Intervallo "));
        assertTrue(chart.contains("Riferimento dal referto del "));
        assertTrue(chart.contains("Data clinica"));
        assertTrue(chart.contains("scaledBoundsWithReference"));
        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));
    }

    @Test public void remoteCopyHasOuterRetryForMegaTransientJsonFailure() throws Exception {
        String rclone = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12Rclone.java");
        String copy = block(rclone, "public static void copyFromRemote");
        assertTrue(copy.contains("attempt <= 3"));
        assertTrue(copy.contains("--retries\", \"4"));
        assertTrue(copy.contains("--low-level-retries\", \"10"));
        assertTrue(copy.contains("unexpected end of json input"));
        assertTrue(copy.contains("Thread.sleep"));
    }

    @Test public void syncStartsAtRealPhaseOneAndNeverShowsFakePercentage() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String sync = block(cloud, "public static void syncInteractiveR42");
        assertTrue(sync.contains("Fase 1 di 4"));
        assertTrue(sync.contains("Ricerca della copia Windows più recente"));
        assertTrue(sync.contains("Fase 2 di 4"));
        assertTrue(sync.contains("Fase 3 di 4"));
        assertTrue(sync.contains("Fase 4 di 4"));
        assertTrue(sync.contains("setIndeterminate(true)"));
        assertFalse(sync.contains("setProgress("));
        assertFalse(sync.contains("20%"));
        assertTrue(sync.contains("r36RefreshLatestCommittedSnapshot"));
        assertTrue(sync.contains("pullRemoteChanges"));
        assertTrue(sync.contains("uploadPendingChanges"));
        assertTrue(sync.contains("checkCompletionConsumed"));
        String oldEntry = block(cloud, "private static void syncInteractive(Activity activity, SharedPreferences prefs)");
        assertTrue(oldEntry.contains("syncInteractiveR42(activity, prefs)"));
    }

    @Test public void versionIsR42() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 42"));
        assertTrue(gradle.contains("1.0.0-android-r42-realdevice-landscape-graph-sync-final-test"));
    }
}
