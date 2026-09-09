package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R39ExactLabsLandscapeSyncProgressV2Test {
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

    @Test public void landscapeOnlyUsesWideSingleLineFirstColumn() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("Math.max(dp(360), Math.min(dp(460)"));
        assertTrue(label.contains("screenWidth * 0.52f"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(label.contains("labelWidth = dp(92)"));
    }

    @Test public void reportGraphsUseExactWindowsLabValues() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        assertTrue(selector.contains("R27ExactWindows.availableLabParameters(prefs)"));
        assertTrue(selector.contains("R27ExactWindows.labSeries(prefs, id)"));
        assertFalse(selector.contains("R36ClinicalSeries.availableLabParameters"));
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(series.contains("R27ExactWindows.labSeries(prefs, p[1])"));
    }

    @Test public void r27ExactReaderUsesImportedWindowsLabValues() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        assertTrue(exact.contains("doc.optJSONArray(\"labValues\")"));
        assertTrue(exact.contains("lab.optString(\"parameterId\""));
        assertTrue(exact.contains("row.put(\"date\""));
    }

    @Test public void syncHasVisibleStagedProgress() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String sync = block(cloud, "public static void syncInteractiveR39");
        assertTrue(sync.contains("ProgressDialog.STYLE_HORIZONTAL"));
        assertTrue(sync.contains("setMax(100)"));
        assertTrue(sync.contains("Ricerca della copia Windows più recente"));
        assertTrue(sync.contains("Ricezione delle modifiche dal Dossier"));
        assertTrue(sync.contains("Invio delle modifiche locali"));
        assertTrue(sync.contains("Verifica finale della sincronizzazione"));
    }

    @Test public void r38GraphMathRemainsPresent() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("requestedValue(o, preferredKeys)"));
        assertTrue(chart.contains("scaledBounds(dataMin, dataMax)"));
        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));
    }

    @Test public void versionIsR39V2() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 39"));
        assertTrue(gradle.contains("1.0.0-android-r39-landscape-exactlabs-sync-progress-test"));
    }
}
