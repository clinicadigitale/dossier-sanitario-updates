package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.json.JSONObject;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

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
        assertTrue(addIf.contains("labelValue(label, value)"));
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

    @Test public void canonicalGraphValueWinsOverRawParsedValue() throws Exception {
        JSONObject lab = new JSONObject();
        lab.put("value", "113113");
        lab.put("normalizedValue", 113.0);
        assertEquals(113.0, R40ClinicalSeries.canonicalValue(lab), 0.0001);
    }

    @Test public void invalidRowsAndParserExplosionsAreRejected() throws Exception {
        JSONObject invalid = new JSONObject();
        invalid.put("value", 101);
        invalid.put("validForGraph", false);
        assertTrue(R40ClinicalSeries.explicitInvalid(invalid));

        double[] values = {95, 100, 103, 108, 112, 115, 118, 121, 130, 140, 150, 158, 0, 0, 113113};
        List<JSONObject> rows = new ArrayList<>();
        for (double value : values) {
            JSONObject row = new JSONObject();
            row.put("value", value);
            rows.add(row);
        }
        List<JSONObject> cleaned = R40ClinicalSeries.removeObviousParserExplosions(rows);
        assertEquals(12, cleaned.size());
        for (JSONObject row : cleaned) {
            assertTrue(row.getDouble("value") >= 95.0);
            assertTrue(row.getDouble("value") <= 158.0);
        }
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
