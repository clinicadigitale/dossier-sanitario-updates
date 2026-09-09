package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R38RealGraphDataLandscapeWidthTest {
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

    @Test public void portraitFirstColumnRemainsFrozenAt92Dp() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("dp(92)"));
        assertTrue(label.contains("if (landscape)"));
        assertTrue(label.contains("} else {"));
    }

    @Test public void landscapeFirstColumnUsesRealAvailableWidthInsteadOfDpCap() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("0.48f"));
        assertTrue(label.contains("0.52f"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertFalse(label.contains("Math.max(dp(280)"));
        assertFalse(label.contains("screenWidth * 0.46f"));
    }

    @Test public void selectedGraphNormalizesOnlyTheRequestedNumericField() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chart = block(main, "private void r27Chart");
        assertTrue(chart.contains("R38ClinicalSeries.normalizeGraphSeries(rows, key)"));
        assertTrue(chart.contains("new R38ChartView"));
        assertFalse(chart.contains("new R26ChartView"));
        String clinical = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R38ClinicalSeries.java");
        String normalize = block(clinical, "static JSONArray normalizeGraphSeries");
        assertTrue(normalize.contains("original.opt(key)"));
        assertFalse(normalize.contains("numericValue"));
        assertFalse(normalize.contains("Iterator<String>"));
    }

    @Test public void reportGraphSeriesReconcilesExactAndTolerantWindowsReaders() throws Exception {
        String clinical = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R38ClinicalSeries.java");
        String labs = block(clinical, "static JSONArray labSeries");
        assertTrue(labs.contains("R27ExactWindows.labSeries"));
        assertTrue(labs.contains("R36ClinicalSeries.labSeries"));
        assertTrue(labs.contains("mergeSeries"));
        String merge = block(clinical, "static JSONArray mergeSeries");
        assertTrue(merge.contains("Set<String> seen"));
        assertTrue(merge.contains("canonicalNumber(value)"));
        assertTrue(merge.contains("rows.sort"));
    }

    @Test public void differentFixtureValuesProduceClearlyDifferentVerticalCoordinates() {
        double[] values = new double[]{91.0, 104.0, 97.0};
        R38GraphMath.Domain domain = R38GraphMath.domain(values);
        assertTrue(domain.varied);
        assertTrue(R38GraphMath.visibleSpanRatio(values) > 0.70);
        float low = R38GraphMath.y(91.0, domain, 0f, 100f);
        float high = R38GraphMath.y(104.0, domain, 0f, 100f);
        assertTrue(Math.abs(low - high) > 65f);
    }

    @Test public void equalFixtureValuesAreTheOnlyCaseMarkedFlat() {
        R38GraphMath.Domain domain = R38GraphMath.domain(new double[]{100.0, 100.0, 100.0});
        assertFalse(domain.varied);
    }

    @Test public void chartShowsPointValuesAndExplicitlyReportsTrulyIdenticalData() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R38ChartView.java");
        assertTrue(chart.contains("shortNumber(values.get(i))"));
        assertTrue(chart.contains("Valori identici nelle rilevazioni disponibili"));
        assertTrue(chart.contains("R38GraphMath.y"));
        assertTrue(chart.contains("R38GraphMath.domain"));
    }

    @Test public void priorLoginSyncAndContactFixesRemainPresent() throws Exception {
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
        assertTrue(gradle.contains("versionName '1.0.0-android-r38-real-graph-data-landscape-width-test'"));
    }
}
