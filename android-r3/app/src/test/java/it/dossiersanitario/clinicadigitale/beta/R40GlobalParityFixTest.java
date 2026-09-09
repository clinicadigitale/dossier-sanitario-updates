package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R40GlobalParityFixTest {
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

    @Test public void landscapeDetectionUsesRealViewportNotOnlyConfigurationFlag() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String landscape = block(main, "private boolean r36Landscape");
        assertTrue(landscape.contains("dm.widthPixels > dm.heightPixels"));
        assertTrue(landscape.contains("Configuration.ORIENTATION_LANDSCAPE"));
    }

    @Test public void everyStandardSectionRowUsesOneGlobalLandscapeRuleAndPortraitStaysFrozen() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("labelWidth = dp(92)"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(label.contains("labelView.setMaxLines(1)"));
        assertTrue(label.contains("row.post"));
        assertTrue(label.contains("row.getWidth()"));
        String addIf = block(main, "private void r31AddIf");
        assertTrue(addIf.contains("labelValue(label, value.trim())"));
        String emergency = block(main, "private void renderDatiEmergenza");
        assertTrue(emergency.contains("Nominativo contatto"));
        assertTrue(emergency.contains("Allergie rilevanti"));
        assertTrue(emergency.contains("r31AddIf"));
    }

    @Test public void allReportGraphsUseSingleR40WindowsBackedSeries() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(selector.contains("R40ClinicalSeries.availableLabParameters(prefs)"));
        assertTrue(series.contains("R40ClinicalSeries.labSeries(prefs, p[1])"));
        assertFalse(selector.contains("R36ClinicalSeries"));
        assertFalse(series.contains("R36ClinicalSeries"));
    }

    @Test public void canonicalFieldsArePreferredBeforeRawGraphValues() throws Exception {
        String clinical = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R40ClinicalSeries.java");
        int normalized = clinical.indexOf("\"normalizedValue\"");
        int raw = clinical.indexOf("\"value\"", normalized);
        assertTrue(normalized >= 0);
        assertTrue(raw > normalized);
        assertTrue(clinical.contains("\"normalizedUnit\""));
        assertTrue(clinical.contains("explicitInvalid(lab)"));
    }

    @Test public void parserExplosionGuardExecutesOnRealNumbers() {
        double median = 112.0;
        assertTrue(R40ClinicalSeries.keepAgainstMedian(95.0, median));
        assertTrue(R40ClinicalSeries.keepAgainstMedian(158.0, median));
        assertFalse(R40ClinicalSeries.keepAgainstMedian(0.0, median));
        assertFalse(R40ClinicalSeries.keepAgainstMedian(113113.0, median));
    }

    @Test public void graphUsesClinicalDatesForHorizontalAxis() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("private final List<String> dates"));
        assertTrue(chart.contains("dateTimes(dates)"));
        assertTrue(chart.contains("times[i] - tMin"));
        assertTrue(chart.contains("yearLabel(tMin)"));
        assertTrue(chart.contains("yearLabel(tMax)"));
    }

    @Test public void everyInteractiveCloudSyncPathUsesVisibleR40ProgressUi() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String panel = block(cloud, "public static void renderCloudPanel");
        assertTrue(panel.contains("syncInteractive(activity, prefs)"));
        String oldEntry = block(cloud, "private static void syncInteractive(Activity activity, SharedPreferences prefs)");
        assertTrue(oldEntry.contains("syncInteractiveR40(activity, prefs)"));
        assertFalse(oldEntry.contains("runProgress"));
        String r39 = block(cloud, "public static void syncInteractiveR39");
        assertTrue(r39.contains("syncInteractiveR40(activity, prefs)"));
        String r40 = block(cloud, "public static void syncInteractiveR40");
        assertTrue(r40.contains("progressBarStyleHorizontal"));
        assertTrue(r40.contains("TextView phase"));
        assertTrue(r40.contains("setProgress(5)"));
        assertTrue(r40.contains("Ricerca della copia Windows più recente"));
        assertTrue(r40.contains("Ricezione delle modifiche dal Dossier"));
        assertTrue(r40.contains("Verifica finale della sincronizzazione"));
    }

    @Test public void versionIsR40() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 40"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r40-global-parity-final-test'"));
    }
}
