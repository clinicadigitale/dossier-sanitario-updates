package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R37FrozenPortraitLandscapeGraphsAgendaTest {
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

    @Test public void portraitLabelGeometryIsRestoredToFrozenR34R35Baseline() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("labelWidth = dp(92)"));
        assertTrue(label.contains("row.setPadding(0, dp(5), 0, dp(5))"));
        assertFalse(label.contains("labelView.setMaxLines"));
        assertFalse(label.contains("row.setGravity(Gravity.TOP)"));
        assertTrue(main.contains("int r36ContentSide = r36Landscape() ? dp(12) : dp(16)"));
    }

    @Test public void landscapeLabelColumnIsAlmostDoubleAndSingleLine() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("Math.max(dp(280), Math.min(dp(320)"));
        assertTrue(label.contains("screenWidth * 0.46f"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(main.contains("Nominativo contatto"));
        assertTrue(main.contains("Medico di base"));
    }

    @Test public void agendaNormalCardsDoNotShowReminderTiming() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String agenda = block(main, "private void renderAgenda() {");
        assertFalse(agenda.contains("labelValue(\"Avvisi\""));
        assertFalse(agenda.contains("optJSONArray(\"reminders\")"));
        assertTrue(agenda.contains("Apri documento originale"));
        String edit = block(main, "private void r31EditAgendaEvent");
        assertTrue(edit.contains("Avvisi (es. 1 giorno; 2 ore; 30 minuti)"));
        assertTrue(edit.contains("r36ParseReminderText"));
    }

    @Test public void graphSelectorUsesDirectWindowsReportSeriesAndChronologicalSort() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        assertTrue(selector.contains("R37ClinicalSeries.availableLabParameters"));
        assertTrue(selector.contains("R37ClinicalSeries.labSeries"));
        assertTrue(selector.contains("choices.sort"));
        assertTrue(selector.contains("sortDate"));
        assertTrue(selector.contains("· referti"));
        assertTrue(selector.contains("if (!graph) r36AddClinicalChoice(choices, \"Glicemia manuale\""));
    }

    @Test public void legacyGlucoseGraphIsForcedToReportDerivedGlycaemiaWhenAvailable() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(series.contains("R37ClinicalSeries.glycemiaFromReports"));
        assertTrue(series.contains("glucose"));
        String label = block(main, "private String r31ChoiceLabel");
        assertTrue(label.contains("Glicemia · referti"));
    }

    @Test public void clinicalSeriesPrefersExactWindowsLabValuesAndUnderstandsGlycaemiaAliases() throws Exception {
        String clinical = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R37ClinicalSeries.java");
        assertTrue(clinical.contains("R27ExactWindows.availableLabParameters"));
        assertTrue(clinical.contains("R27ExactWindows.labSeries"));
        assertTrue(clinical.contains("R36ClinicalSeries.labSeries"));
        assertTrue(clinical.contains("glicem"));
        assertTrue(clinical.contains("glucos"));
        assertTrue(clinical.contains("glucose"));
        assertTrue(clinical.contains("rows.sort"));
    }

    @Test public void r35LoginR36SyncAndR34ContactFeaturesRemainPresent() throws Exception {
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

    @Test public void versionIsR37() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 37"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'"));
    }
}
