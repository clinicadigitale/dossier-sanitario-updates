package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R32OrderingMonitorTest {
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

    @Test public void dashboardAgendaIsChronologicalNearestToFarthest() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String method = block(main, "private void renderPanoramica()");
        assertTrue(method.contains("r31SortedByDate(events, true"));
        assertTrue(method.contains("labelValue(\"Data\""));
    }

    @Test public void clinicalTimelineExcludesAgendaAndMeasurementsAndCanReverseOrder() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String method = block(main, "private void renderCronologia()");
        assertTrue(method.contains("r32ClinicalTimeline()"));
        assertTrue(method.contains("r32_timeline_oldest_first"));
        String helper = block(main, "private JSONArray r32ClinicalTimeline()");
        assertTrue(helper.contains("\"Agenda\".equalsIgnoreCase(kind)"));
        assertTrue(helper.contains("\"Rilevazione\".equalsIgnoreCase(kind)"));
    }

    @Test public void allMainRecordListsExposeOrderingControls() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(block(main, "private void renderEsenzioni()").contains("r32_exemptions_oldest_first"));
        assertTrue(block(main, "private void renderDiagnosi()").contains("r32_diagnoses_oldest_first"));
        assertTrue(block(main, "private void renderMedici()").contains("r32_doctors_name_asc"));
        assertTrue(block(main, "private void renderAgenda()").contains("r32_agenda_nearest_first"));
        assertTrue(block(main, "private void renderDocumenti()").contains("r31_documents_oldest_first"));
    }

    @Test public void therapiesDefaultToTimeOrderAndProvideSelector() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String method = block(main, "private void renderTerapie()");
        assertTrue(method.contains("therapySort"));
        assertTrue(method.contains("time-asc"));
        assertTrue(method.contains("r32ShowTherapySort"));
        assertTrue(main.contains("Orario crescente"));
        assertTrue(main.contains("Orario decrescente"));
        assertTrue(main.contains("Farmaco A-Z"));
    }

    @Test public void monitoringDetailHasPerSectionGraphsAndDateOrdering() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String method = block(main, "private void r31RenderMonitorDetail(String type,String label)");
        assertTrue(method.contains("r32AddMonitorGraphs(type,label,rows)"));
        assertTrue(method.contains("r32_monitor_"));
        assertTrue(method.contains("Ordine: meno recenti prima"));
        assertTrue(method.contains("Ordine: più recenti prima"));
    }

    @Test public void monitoringGraphsMatchWindowsMeasurementFamilies() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String helper = block(main, "private void r32AddMonitorGraphs(String type,String label,JSONArray rows)");
        assertTrue(helper.contains("Pressione sistolica"));
        assertTrue(helper.contains("Pressione diastolica"));
        assertTrue(helper.contains("Frequenza cardiaca"));
        assertTrue(helper.contains("r31BodyLabel(bodyType)"));
        assertTrue(helper.contains("r27Chart(\"Andamento \"+label"));
    }

    @Test public void weightHistoryIsCompactInsteadOfOneLargeCardPerReading() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String method = block(main, "private void r31RenderMonitorDetail(String type,String label)");
        assertTrue(method.contains("Storico pesate"));
        assertTrue(method.contains("line.setOrientation(LinearLayout.HORIZONTAL)"));
        assertTrue(method.contains("dp(40)"));
        assertTrue(method.contains("return;"));
    }

    @Test public void r31FrozenFunctionalityRemainsPresent() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Cambia utente / profilo"));
        assertTrue(main.contains("Dati di emergenza"));
        assertTrue(main.contains("Apri documento di riferimento"));
        assertTrue(main.contains("Modifica terapia"));
        assertTrue(main.contains("Aggiungi medico"));
        assertTrue(main.contains("Sincronizza Agenda"));
        assertTrue(main.contains("Ricorda le credenziali su questo dispositivo"));
        assertTrue(main.contains("showStartupTotp"));
    }

    @Test public void versionIsR32OrderingMonitorTest() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 32"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r32-ordering-monitor-test'"));
    }
}
