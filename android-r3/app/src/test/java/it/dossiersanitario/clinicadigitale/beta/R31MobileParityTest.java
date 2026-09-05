package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R31MobileParityTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void homeHasExplicitProfileSwitcherAndNoReleaseNoticeCall() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int a = main.indexOf("private void renderPanoramica()");
        int b = main.indexOf("private void renderDatiProfilo()", a);
        String method = main.substring(a, b);
        assertTrue(method.contains("Cambia utente / profilo"));
        assertTrue(method.contains("showR27ProfilePicker()"));
        assertFalse(method.contains("addReleaseNotice()"));
    }

    @Test public void dashboardAgendaUsesSeparatedItalianFieldsAndDate() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("labelValue(\"Data\""));
        assertTrue(main.contains("labelValue(\"Ora\""));
        assertTrue(main.contains("labelValue(\"Tipo\""));
        assertTrue(main.contains("Tutto il giorno"));
    }

    @Test public void emergencyDataIsARealSectionWithWindowsFields() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("\"Dati di emergenza\""));
        assertTrue(main.contains("renderDatiEmergenza()"));
        assertTrue(main.contains("emergencyContactName"));
        assertTrue(main.contains("emergencyAllergies"));
        assertTrue(main.contains("emergencyCriticalTherapies"));
        assertTrue(main.contains("primaryDoctorPhone"));
    }

    @Test public void exemptionsHaveCompactAndExtendedViews() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Passa alla vista compatta"));
        assertTrue(main.contains("Passa alla vista estesa"));
        assertTrue(main.contains("Ente rilasciante"));
        assertTrue(main.contains("Limitazioni"));
    }

    @Test public void documentsCanReverseDateOrderWithoutBreakingOriginalOpen() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Più vecchi prima") || main.contains("più vecchi prima"));
        assertTrue(main.contains("Più recenti prima") || main.contains("più recenti prima"));
        assertTrue(main.contains("R27ExactWindows.openDocument(this, d)"));
    }

    @Test public void diagnosesAreItalianAndOpenSourceDocument() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Note ed evoluzione"));
        assertTrue(main.contains("Specializzazione"));
        assertTrue(main.contains("Apri documento di riferimento"));
        assertTrue(main.contains("documentById"));
    }

    @Test public void therapiesHaveFullEditableWindowsFields() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Modifica terapia"));
        assertTrue(main.contains("Principio attivo"));
        assertTrue(main.contains("Produttore / Marca"));
        assertTrue(main.contains("Decorrenza modifica piano"));
        assertTrue(main.contains("Unità nella confezione"));
        assertTrue(main.contains("Numero confezioni disponibili"));
        assertTrue(main.contains("Gestisci scorta e riordino"));
        assertTrue(main.contains("queueR31EntityPut(this, prefs, \"therapies\""));
    }

    @Test public void doctorsCanBeAddedAndEdited() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Aggiungi medico"));
        assertTrue(main.contains("Nome e cognome"));
        assertTrue(main.contains("Specializzazione"));
        assertTrue(main.contains("queueR31EntityPut(this,prefs,\"doctors\""));
    }

    @Test public void compareStartsWithSelectorAndOnlyRendersChosenValue() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int a = main.indexOf("private void renderConfronta()");
        int b = main.indexOf("private void renderGrafici()", a);
        String method = main.substring(a, b);
        assertTrue(method.contains("Seleziona valore da confrontare"));
        assertTrue(method.contains("r31RenderSelectedComparison"));
        assertFalse(method.contains("r27Comparison(\"Peso\""));
    }

    @Test public void graphsStartWithSelectorAndOnlyOpenChosenGraph() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int a = main.indexOf("private void renderGrafici()");
        int b = main.indexOf("private void renderAgenda()", a);
        String method = main.substring(a, b);
        assertTrue(method.contains("Seleziona valore da visualizzare"));
        assertTrue(method.contains("r31RenderSelectedGraph"));
        assertFalse(method.contains("r27Chart(\"Percorso peso\""));
    }

    @Test public void agendaIsItalianEditableAndHasExplicitSync() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Nuovo appuntamento"));
        assertTrue(main.contains("Modifica appuntamento"));
        assertTrue(main.contains("Sincronizza Agenda"));
        assertTrue(main.contains("syncInteractiveR31"));
        assertTrue(main.contains("Durata in minuti"));
        assertTrue(main.contains("Luogo / struttura"));
    }

    @Test public void monitoringOpensDedicatedPagesAndSupportsManualEntry() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Apri la sezione desiderata"));
        assertTrue(main.contains("Misurazioni corporee"));
        assertTrue(main.contains("Pressione arteriosa"));
        assertTrue(main.contains("Saturazione ossigeno"));
        assertTrue(main.contains("Aggiungi rilevazione"));
        assertTrue(main.contains("r31EditMeasurement"));
        assertTrue(main.contains("queueR31EntityPut(this,prefs,\"measurements\""));
    }

    @Test public void preferencesAreEditableAndProfileSwitcherIsNotInNewPreferences() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int a = main.indexOf("private void renderPreferenze()");
        int b = main.indexOf("private void renderBackup()", a);
        String block = main.substring(a, b);
        assertTrue(block.contains("Modifica preferenze generali"));
        assertTrue(block.contains("Modifica preferenze del profilo"));
        assertTrue(block.contains("Colore del programma"));
        assertTrue(block.contains("Frequenza backup"));
        assertFalse(block.substring(0, block.indexOf("private void r31SelectClinicalValue")).contains("Profili disponibili e colori"));
    }

    @Test public void helpContainsAllTwentySixWindowsTopics() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("1. Che cos'è Clinica Digitale"));
        assertTrue(main.contains("4. Aggiungere un familiare"));
        assertTrue(main.contains("9. Diagnosi"));
        assertTrue(main.contains("13. Scorte e riordino dei farmaci"));
        assertTrue(main.contains("17. Google Calendar: collegamento semplice"));
        assertTrue(main.contains("20. Monitoraggio personale"));
        assertTrue(main.contains("25. Privacy e trattamento dei dati"));
        assertTrue(main.contains("26. Se qualcosa non funziona"));
    }

    @Test public void exactDiskBackedDataCanBeEditedWithoutUndoingR30MemoryFix() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        String bounded = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R30BoundedWindows.java");
        assertTrue(exact.contains("static boolean replaceData"));
        assertTrue(exact.contains("raw.startsWith(\"@file:\")"));
        assertTrue(exact.contains("new FileOutputStream(file, false)"));
        assertTrue(bounded.contains("private static final String POINTER = \"@file:\""));
    }

    @Test public void editedExactEntitiesUseExistingEncryptedSyncQueue() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("public static void queueR31EntityPut"));
        assertTrue(cloud.contains("queuePut(context, prefs, cfg, store, id, entity, changed)"));
        assertTrue(cloud.contains("public static void syncInteractiveR31"));
    }

    @Test public void securityAndBoundedImportRemainFrozen() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(main.contains("Ricorda le credenziali su questo dispositivo"));
        assertTrue(main.contains("passwordEye"));
        assertTrue(main.contains("showStartupTotp"));
        assertTrue(main.contains("progressBarStyleHorizontal"));
        assertTrue(cloud.contains("R30BoundedWindows.importSnapshot"));
    }

    @Test public void versionIsR31MobileParityTest() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 31"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r31-mobile-parity-test'"));
    }
}
