package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R39LandscapeLabSeriesSyncProgressTest {
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

    @Test public void portraitRemainsFrozenAndLandscapeLabelsAreOneLine() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("labelWidth = Math.max(dp(360), Math.min(dp(460)"));
        assertTrue(label.contains("screenWidth * 0.52f"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(label.contains("new LinearLayout.LayoutParams(dp(92)"));
    }

    @Test public void clinicalSelectorDoesNotRescanEveryReportForEveryOption() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        assertTrue(selector.contains("availableLabParameters(prefs)"));
        assertFalse(selector.contains("R36ClinicalSeries.labSeries(prefs, id)"));
        assertTrue(selector.contains("· referti"));
    }

    @Test public void labIndexIsSinglePassAndSeriesStayReportBacked() throws Exception {
        String series = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R36ClinicalSeries.java");
        String index = block(series, "private static JSONObject buildIndex");
        assertTrue(index.contains("R27ExactWindows.documents(prefs)"));
        assertTrue(index.contains("collectLabRows(doc, rows, 0)"));
        assertTrue(index.contains("sourceDocumentId"));
        String available = block(series, "static JSONArray availableLabParameters");
        assertTrue(available.contains("buildIndex(prefs)"));
        assertFalse(available.contains("labSeries(prefs"));
    }

    @Test public void syncShowsStagesAndRealProgressBar() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String interactive = block(cloud, "public static void syncInteractive");
        assertTrue(interactive.contains("ProgressDialog.STYLE_HORIZONTAL"));
        assertTrue(interactive.contains("setMax(100)"));
        assertTrue(interactive.contains("syncNowWithProgress"));
        assertTrue(cloud.contains("Controllo aggiornamenti Windows"));
        assertTrue(cloud.contains("Ricerca della copia Windows più recente"));
        assertTrue(cloud.contains("Ricezione modifiche completata"));
        assertTrue(cloud.contains("Verifica finale e aggiornamento stato"));
    }

    @Test public void r38GraphFixesRemainFrozen() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("requestedValue(o, preferredKeys)"));
        assertTrue(chart.contains("scaledBounds(dataMin, dataMax)"));
        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));
    }

    @Test public void versionIsR39() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 39"));
        assertTrue(gradle.contains("1.0.0-android-r39-landscape-labseries-sync-progress-test"));
    }
}
