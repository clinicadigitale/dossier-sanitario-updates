package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R38GraphScaleLandscapeWidthTest {
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

    @Test public void requestedGraphValuesRemainNumericallyDifferent() {
        double av = R26ChartView.parseRequestedRaw("81,20 kg");
        double bv = R26ChartView.parseRequestedRaw("80.75");
        assertEquals(81.20, av, 0.00001);
        assertEquals(80.75, bv, 0.00001);
        assertTrue(Math.abs(av - bv) > 0.4);
    }

    @Test public void parserRejectsNonMetricDateTextInsteadOfInventingAValue() {
        assertTrue(Double.isNaN(R26ChartView.parseRequestedRaw("nessun valore")));
        String chart;
        try { chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java"); }
        catch (Exception e) { throw new AssertionError(e); }
        String requested = block(chart, "static double requestedValue");
        assertTrue(requested.contains("o.has(key)"));
        assertTrue(requested.contains("parseRequestedRaw(o.opt(key))"));
        assertFalse(requested.contains("keys()"));
        assertFalse(requested.contains("numericValue"));
    }

    @Test public void smallRealVariationUsesTightVerticalRangeInsteadOfOldFlatHalfUnitPadding() {
        double[] bounds = R26ChartView.scaledBounds(80.0, 80.1);
        assertTrue(bounds[0] < 80.0);
        assertTrue(bounds[1] > 80.1);
        assertTrue("La scala deve amplificare visivamente 0,1 kg", bounds[1] - bounds[0] < 0.20);
        assertTrue("La variazione reale deve occupare oltre metà altezza utile", 0.1 / (bounds[1] - bounds[0]) > 0.5);
    }

    @Test public void ordinaryClinicalRangeKeepsActualMinAndMaxDistinct() {
        double[] bounds = R26ChartView.scaledBounds(92.0, 104.0);
        assertTrue(bounds[0] < 92.0);
        assertTrue(bounds[1] > 104.0);
        assertTrue(bounds[1] - bounds[0] < 16.0);
    }

    @Test public void landscapeColumnIsReallyWiderWhilePortraitStaysFrozen() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("Math.max(dp(340), Math.min(dp(420)"));
        assertTrue(label.contains("screenWidth * 0.50f"));
        assertTrue(label.contains("labelWidth = dp(92)"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertFalse(label.contains("Math.max(dp(280), Math.min(dp(320)"));
    }

    @Test public void graphHeightAndCompactLandscapeFieldsAreActuallyExpanded() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("r36Landscape() ? dp(330) : dp(280)"));
        assertTrue(main.contains("r31First(row,\"date\",\"createdAt\"), 1.45f"));
        assertTrue(main.contains("row.optString(\"time\",\"\"), 0.9f"));
        assertTrue(main.contains("r31Display(row,\"date\",\"createdAt\"),1.55f"));
        assertTrue(main.contains("row.optString(\"time\",\"\"),0.95f"));
    }

    @Test public void genericChartNoLongerUsesArbitraryNumericFallbackOrOldFixedMargin() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("requestedValue(o, preferredKeys)"));
        assertTrue(chart.contains("scaledBounds(dataMin, dataMax)"));
        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));
        assertFalse(chart.contains("Math.max((max - min) * 0.08, 0.5)"));
    }

    @Test public void authenticationSyncAndContactFrozenPathsRemainPresent() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chooser = block(main, "private void r34ShowSecondFactor");
        assertTrue(chooser.contains("setPositiveButton(\"Biometria del dispositivo\""));
        assertTrue(chooser.contains("setNeutralButton(\"Codice TOTP\""));
        assertTrue(main.contains("mailto:"));
        assertTrue(main.contains("Intent.ACTION_DIAL"));
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("r36RefreshLatestCommittedSnapshot"));
        assertTrue(cloud.contains("R25ZipEntryReader.readEntry(zip)"));
    }

    @Test public void versionIsR38() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 38"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r38-graph-scale-landscape-width-test'"));
    }
}
