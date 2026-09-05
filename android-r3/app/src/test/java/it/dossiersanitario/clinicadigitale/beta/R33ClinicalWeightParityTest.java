package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R33ClinicalWeightParityTest {
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

    @Test public void timelineUsesOnlyClinicalDocumentsInsteadOfTherapiesOrAgenda() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String render = block(main, "private void renderCronologia()");
        assertTrue(render.contains("r33ClinicalTimelineDocuments()"));
        assertTrue(render.contains("Referti, visite ed esami"));
        assertFalse(render.contains("R27ExactWindows.therapies"));
        String filter = block(main, "private JSONArray r33ClinicalTimelineDocuments()");
        assertTrue(filter.contains("R27ExactWindows.documents(prefs)"));
        assertTrue(filter.contains("timelineVisible"));
        assertTrue(filter.contains("sourceSection"));
        assertTrue(filter.contains("prenot"));
        assertTrue(filter.contains("terapia"));
        assertTrue(filter.contains("referto"));
        assertTrue(filter.contains("visita"));
        assertTrue(filter.contains("esame"));
    }

    @Test public void weightDetailConsumesTheExactWindowsJourneyFields() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String detail = block(main, "private void r33RenderWeightDetail()");
        assertTrue(detail.contains("R27ExactWindows.weightJourneys(prefs)"));
        assertTrue(detail.contains("startDate"));
        assertTrue(detail.contains("startWeight"));
        assertTrue(detail.contains("targetDate"));
        assertTrue(detail.contains("targetWeight"));
        assertTrue(detail.contains("heightCm"));
        assertTrue(detail.contains("sex"));
        assertTrue(detail.contains("activityLevel"));
        assertTrue(detail.contains("status"));
        assertTrue(detail.contains("notes"));
        assertTrue(detail.contains("Data stimata dal trend"));
        assertTrue(detail.contains("Scostamento dalla traiettoria"));
        assertTrue(detail.contains("Giorni rimanenti"));
    }

    @Test public void weightProjectionMatchesWindowsRobustTrendRules() throws Exception {
        String model = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R33WeightJourneyModel.java");
        assertTrue(model.contains("actual.size() - 8"));
        assertTrue(model.contains("recent.size() >= 4"));
        assertTrue(model.contains("Math.abs(robust) >= 0.003"));
        assertTrue(model.contains("Math.abs(netSlope) >= 0.003"));
        assertTrue(model.contains("Math.max(365.0, plannedDays * 3.0)"));
        assertTrue(model.contains("pathDeviationKg"));
        assertTrue(model.contains("pathDelayDays"));
        assertTrue(model.contains("forecastDeltaDays"));
    }

    @Test public void weightGraphMatchesWindowsThreeSeriesAndLegend() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R33WeightJourneyChartView.java");
        assertTrue(chart.contains("Color.rgb(37, 99, 168)"));
        assertTrue(chart.contains("Color.rgb(47, 125, 74)"));
        assertTrue(chart.contains("Color.rgb(180, 35, 24)"));
        assertTrue(chart.contains("DashPathEffect"));
        assertTrue(chart.contains("Pesate"));
        assertTrue(chart.contains("Percorso previsto"));
        assertTrue(chart.contains("Proiezione reale"));
        assertTrue(chart.contains("model.startDay"));
        assertTrue(chart.contains("model.targetDay"));
    }

    @Test public void pressureIsOneTwoSeriesGraph() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String helper = block(main, "private void r32AddMonitorGraphs(String type,String label,JSONArray rows)");
        assertTrue(helper.contains("new R33PressureChartView"));
        assertFalse(helper.contains("r27Chart(\"Pressione sistolica\""));
        assertFalse(helper.contains("r27Chart(\"Pressione diastolica\""));
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R33PressureChartView.java");
        assertTrue(chart.contains("Sistolica"));
        assertTrue(chart.contains("Diastolica"));
        assertTrue(chart.contains("Color.rgb(122, 122, 122)"));
        assertTrue(chart.contains("systolic"));
        assertTrue(chart.contains("diastolic"));
    }

    @Test public void globalGraphSelectorAlsoUsesOnePressureChoice() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue(boolean graph)");
        assertTrue(selector.contains("Pressione arteriosa"));
        assertTrue(selector.contains("p|blood_pressure|both|Pressione arteriosa"));
        String render = block(main, "private void r31RenderSelectedGraph(String choice)");
        assertTrue(render.contains("new R33PressureChartView"));
    }

    @Test public void landscapeKeepsChartsOutsideSystemBarsWithoutChangingPortrait() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("Configuration.ORIENTATION_LANDSCAPE"));
        assertTrue(main.contains("landscape ? insets.getSystemWindowInsetLeft() : 0"));
        assertTrue(main.contains("landscape ? insets.getSystemWindowInsetRight() : 0"));
        assertTrue(main.contains("v.setPadding(left, top, right, bottom)"));
    }

    @Test public void monitorBackNavigationHasPriorityOverGlobalHistory() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String back = block(main, "@Override public void onBackPressed()");
        int monitor = back.indexOf("r33MonitorDetailOpen");
        int history = back.indexOf("navigationHistory");
        assertTrue(monitor >= 0 && history > monitor);
        assertTrue(back.contains("renderSection(\"Monitoraggio\")"));
        String detail = block(main, "private void r31RenderMonitorDetail(String type,String label)");
        assertTrue(detail.contains("r33MonitorDetailOpen = true"));
    }

    @Test public void weightHistoryUsesWindowsPreviousAndInitialDifferences() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String history = block(main, "private void r33RenderWeightHistory(JSONArray rows,boolean oldestFirst,JSONObject journey)");
        assertTrue(history.contains("Diff. precedente"));
        assertTrue(history.contains("Diff. iniziale"));
        assertTrue(history.contains("startDate"));
        assertTrue(history.contains("java.util.Collections.reverse"));
    }

    @Test public void bmiAndCaloriePanelsUseWindowsFieldsAndFormulas() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String bmi = block(main, "private void r33RenderBmiCalculator(R33WeightJourneyModel.Model model,double height)");
        assertTrue(bmi.contains("Calcolatore BMI"));
        assertTrue(bmi.contains("non vengono salvati"));
        String kcal = block(main, "private void r33RenderCalorieEstimate(R33WeightJourneyModel.Model model,JSONObject journey,double height)");
        assertTrue(kcal.contains("10*model.latestWeight+6.25*height-5*age"));
        assertTrue(kcal.contains("7700.0"));
        assertTrue(kcal.contains("Mantenimento calorico stimato"));
        assertTrue(kcal.contains("Metabolismo a riposo stimato"));
    }

    @Test public void versionIsR33ClinicalWeightParityTest() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 33"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r33-clinical-weight-parity-test'"));
    }
}
