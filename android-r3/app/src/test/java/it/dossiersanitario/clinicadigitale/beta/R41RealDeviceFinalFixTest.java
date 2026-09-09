package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R41RealDeviceFinalFixTest {
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

    @Test public void landscapeRuleIsGlobalWeightBasedAndPortraitRemains92dp() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(label.contains("0.48f"));
        assertTrue(label.contains("0.52f"));
        assertTrue(label.contains("dp(92)"));
        String addIf = block(main, "private void r31AddIf");
        assertTrue(addIf.contains("labelValue(label, value.trim())"));
        String emergency = block(main, "private void renderDatiEmergenza");
        assertTrue(emergency.contains("Nominativo contatto"));
        assertTrue(emergency.contains("Telefono contatto"));
        assertTrue(emergency.contains("Allergie rilevanti"));
        assertTrue(emergency.contains("Condizioni o dispositivi rilevanti"));
    }

    @Test public void allClinicalChartsCanRenderWindowsReferenceRange() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("DashPathEffect"));
        assertTrue(chart.contains("referenceLow"));
        assertTrue(chart.contains("referenceHigh"));
        assertTrue(chart.contains("referenceRange"));
        assertTrue(chart.contains("intervalloRiferimento"));
        assertTrue(chart.contains("scaledBoundsWithReference"));
        assertTrue(chart.contains("span * 0.18"));
        assertTrue(chart.contains("drawReferenceLine"));
        assertTrue(chart.contains("Intervallo "));
        assertTrue(chart.contains("Riferimento dal referto del "));
        assertTrue(chart.contains("Data clinica"));
        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));
    }

    @Test public void chartStillUsesExactRequestedSeriesAndClinicalDates() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("requestedValue(o, preferredKeys)"));
        assertTrue(chart.contains("dateTimes(dates)"));
        assertTrue(chart.contains("times[i] - tMin"));
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(series.contains("R40ClinicalSeries.labSeries"));
    }

    @Test public void syncNoLongerShowsFrozenFakePercentage() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String sync = block(cloud, "public static void syncInteractiveR41");
        assertTrue(sync.contains("progressBarStyleHorizontal"));
        assertTrue(sync.contains("setIndeterminate(true)"));
        assertFalse(sync.contains("setProgress(20)"));
        assertFalse(sync.contains("20%"));
        assertTrue(sync.contains("Fase 1 di 5"));
        assertTrue(sync.contains("Fase 2 di 5"));
        assertTrue(sync.contains("Fase 3 di 5"));
        assertTrue(sync.contains("Fase 4 di 5"));
        assertTrue(sync.contains("Fase 5 di 5"));
        assertTrue(sync.contains("r36RefreshLatestCommittedSnapshot"));
        assertTrue(sync.contains("pullRemoteChanges"));
        assertTrue(sync.contains("uploadPendingChanges"));
        assertTrue(sync.contains("checkCompletionConsumed"));
        String oldEntry = block(cloud, "private static void syncInteractive(Activity activity, SharedPreferences prefs)");
        assertTrue(oldEntry.contains("syncInteractiveR41(activity, prefs)"));
        String r39 = block(cloud, "public static void syncInteractiveR39");
        assertTrue(r39.contains("syncInteractiveR41(activity, prefs)"));
    }

    @Test public void versionIsR41() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 41"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r41-realdevice-final-fixes-test'"));
    }
}
