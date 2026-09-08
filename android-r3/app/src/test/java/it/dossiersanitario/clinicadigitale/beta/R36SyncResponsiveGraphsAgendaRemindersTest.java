package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R36SyncResponsiveGraphsAgendaRemindersTest {
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

    @Test public void syncReconcilesNewestCommittedSnapshotBeforeChangeBatches() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String sync = block(cloud, "public static String syncNow");
        assertTrue(sync.contains("readArray(prefs, QUEUE_KEY).length() == 0"));
        assertTrue(sync.contains("r36RefreshLatestCommittedSnapshot"));
        assertTrue(sync.indexOf("r36RefreshLatestCommittedSnapshot") < sync.indexOf("pullRemoteChanges"));
        String refresh = block(cloud, "private static int r36RefreshLatestCommittedSnapshot");
        assertTrue(refresh.contains("latestSnapshot(context, cfg)"));
        assertTrue(refresh.contains("R12Crypto.openDsl5File"));
        assertTrue(refresh.contains("R30BoundedWindows.importSnapshot"));
        assertTrue(refresh.contains("r36ReconciledSnapshotName"));
        assertTrue(refresh.contains("replaceVerified"));
    }

    @Test public void fullSnapshotRefreshRemainsBoundedAndDoesNotRunOverPendingAndroidChanges() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String sync = block(cloud, "public static String syncNow");
        assertTrue(sync.contains("snapshotSafe"));
        String refresh = block(cloud, "private static int r36RefreshLatestCommittedSnapshot");
        assertTrue(refresh.contains("byte[] buffer = new byte[256 * 1024]"));
        assertFalse(refresh.contains("readAll(new FileInputStream"));
        assertTrue(cloud.contains("R25ZipEntryReader.readEntry(zip)"));
    }

    @Test public void landscapeUsesWiderResponsiveLabelColumnsAcrossAllLabelValueSections() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("r36Landscape()"));
        assertTrue(label.contains("screenWidth * 0.34f"));
        assertTrue(label.contains("dp(160)"));
        assertTrue(label.contains("dp(270)"));
        assertTrue(label.contains("r34MakeContactAction"));
        assertTrue(main.contains("r36ContentSide = r36Landscape() ? dp(24) : dp(16)"));
    }

    @Test public void graphSelectorIsChronologicalAndLaboratoryValuesComeFromReports() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        assertTrue(selector.contains("R36ClinicalSeries.availableLabParameters"));
        assertTrue(selector.contains("R36ClinicalSeries.labSeries"));
        assertTrue(selector.contains("sortDate"));
        assertTrue(selector.contains("choices.sort"));
        assertTrue(selector.contains("· referti"));
        assertTrue(selector.contains("Glicemia manuale"));
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(series.contains("R36ClinicalSeries.labSeries"));
        assertTrue(series.contains("findParameterByName(prefs, \"glicem\")"));
    }

    @Test public void reportSeriesReaderUsesDocumentLabValuesAndChronologicalDates() throws Exception {
        String clinical = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R36ClinicalSeries.java");
        assertTrue(clinical.contains("R27ExactWindows.documents(prefs)"));
        assertTrue(clinical.contains("collectLabRows"));
        assertTrue(clinical.contains("sourceDocumentId"));
        assertTrue(clinical.contains("clinicalDate"));
        assertTrue(clinical.contains("found.sort"));
        assertTrue(clinical.contains("parseClinicalNumber"));
    }

    @Test public void agendaOriginalButtonExistsOnlyForDocumentDerivedVisitsAndExams() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String agenda = block(main, "private void renderAgenda");
        assertTrue(agenda.contains("Apri documento originale"));
        assertTrue(agenda.contains("r36AgendaSourceDocument"));
        String eligible = block(main, "private boolean r36AgendaDocumentEligible");
        assertTrue(eligible.contains("farmac"));
        assertTrue(eligible.contains("telefon"));
        assertTrue(eligible.contains("visita"));
        assertTrue(eligible.contains("esame"));
        assertTrue(eligible.contains("prenotaz"));
        String source = block(main, "private JSONObject r36AgendaSourceDocument");
        assertTrue(source.contains("sourceDocumentId"));
        assertTrue(source.contains("R27ExactWindows.documentById"));
    }

    @Test public void reminderMinutesAreShownAndEditedAsHumanIntervals() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String format = block(main, "private String r36FormatMinutes");
        assertTrue(format.contains("10080"));
        assertTrue(format.contains("1440"));
        assertTrue(format.contains("1 settimana"));
        assertTrue(format.contains("1 giorno"));
        assertTrue(format.contains("ore"));
        String agendaEdit = block(main, "private void r31EditAgendaEvent");
        assertTrue(agendaEdit.contains("1 giorno; 2 ore; 30 minuti"));
        assertTrue(agendaEdit.contains("r36ParseReminderText"));
        String prefsEdit = block(main, "private void r31EditGlobalPreferences");
        assertTrue(prefsEdit.contains("Avvisi Agenda (es. 1 giorno; 2 ore; 30 minuti)"));
        assertTrue(prefsEdit.contains("r36ParseReminderText"));
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("r36HumanReminderDisplay"));
    }

    @Test public void r35LoginFixAndR34FeaturesRemainPresent() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String chooser = block(main, "private void r34ShowSecondFactor");
        assertTrue(chooser.contains("setPositiveButton(\"Biometria del dispositivo\""));
        assertTrue(chooser.contains("setNeutralButton(\"Codice TOTP\""));
        assertFalse(chooser.contains("setItems("));
        assertTrue(main.contains("mailto:"));
        assertTrue(main.contains("Intent.ACTION_DIAL"));
        assertTrue(main.contains("r34MeasurementLandscapeRow"));
        assertTrue(main.contains("r34PaletteDivider"));
    }

    @Test public void versionIsR36() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 36"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test'"));
    }
}
