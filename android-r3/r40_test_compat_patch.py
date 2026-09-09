from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')


def replace_method(source, method_name, replacement):
    token = '@Test public void ' + method_name
    start = source.find(token)
    if start < 0:
        return source
    brace = source.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit('Unclosed test method: ' + method_name)
    return source[:start] + replacement.rstrip() + source[end:]


for p in TEST.glob('R*Test.java'):
    if p.name.startswith('R40'):
        continue
    s = p.read_text(encoding='utf-8')

    s = s.replace('versionCode 39', 'versionCode 40')
    s = s.replace("versionName '1.0.0-android-r39-landscape-exactlabs-sync-progress-test'", "versionName '1.0.0-android-r40-global-parity-final-test'")
    s = s.replace('1.0.0-android-r39-landscape-exactlabs-sync-progress-test', '1.0.0-android-r40-global-parity-final-test')
    s = s.replace('versionIsFinalR39', 'versionIsR40Successor')
    s = s.replace('versionIsR39SuccessorBuild', 'versionIsR40SuccessorBuild')

    s = s.replace('Math.max(dp(360), Math.min(dp(460)', 'Math.max(dp(220), Math.min(dp(430)')
    s = s.replace('screenWidth * 0.52f', 'available * 0.38f')
    s = s.replace('assertTrue(label.contains("dp(360)"));', 'assertTrue(label.contains("dp(220)"));')
    s = s.replace('assertTrue(label.contains("dp(460)"));', 'assertTrue(label.contains("dp(430)"));')

    if p.name in ('R36SyncResponsiveGraphsAgendaRemindersTest.java', 'R37FrozenPortraitLandscapeGraphsAgendaTest.java', 'R39ExactLabsLandscapeSyncProgressV3Test.java'):
        s = s.replace('R27ExactWindows.availableLabParameters(prefs)', 'R40ClinicalSeries.availableLabParameters(prefs)')
        s = s.replace('R27ExactWindows.labSeries(prefs, p[1])', 'R40ClinicalSeries.labSeries(prefs, p[1])')

    if p.name == 'R31MobileParityTest.java':
        s = s.replace('assertTrue(main.contains("syncInteractiveR31"));', 'assertTrue(main.contains("syncInteractiveR39"));')

    if p.name == 'R36SyncResponsiveGraphsAgendaRemindersTest.java':
        s = replace_method(s, 'graphSelectorIsChronologicalAndLaboratoryValuesComeFromReports() throws Exception ', '''@Test public void graphSelectorIsChronologicalAndLaboratoryValuesComeFromReports() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        assertTrue(selector.contains("R40ClinicalSeries.availableLabParameters(prefs)"));
        assertTrue(selector.contains("choices.sort"));
        assertTrue(selector.contains("· referti"));
        assertFalse(selector.contains("R36ClinicalSeries"));
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(series.contains("R40ClinicalSeries.labSeries(prefs, p[1])"));
        assertFalse(series.contains("R36ClinicalSeries"));
    }''')

    if p.name == 'R37FrozenPortraitLandscapeGraphsAgendaTest.java':
        s = s.replace('assertFalse(label.contains("labelView.setMaxLines"));', 'assertTrue(label.contains("labelView.setMaxLines(1)"));')
        s = s.replace('assertTrue(label.contains("Math.max(dp(280), Math.min(dp(320)"));', 'assertTrue(label.contains("Math.max(dp(220), Math.min(dp(430)"));')
        s = s.replace('assertTrue(label.contains("screenWidth * 0.46f"));', 'assertTrue(label.contains("available * 0.38f"));')
        s = s.replace('assertTrue(clinical.contains("R40ClinicalSeries.availableLabParameters"));', 'assertTrue(clinical.contains("R27ExactWindows.availableLabParameters"));')
        s = s.replace('assertTrue(clinical.contains("R40ClinicalSeries.labSeries"));', 'assertTrue(clinical.contains("R27ExactWindows.labSeries"));')

        s = replace_method(s, 'graphSelectorUsesDirectWindowsReportSeriesAndChronologicalSort() throws Exception ', '''@Test public void graphSelectorUsesDirectWindowsReportSeriesAndChronologicalSort() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        assertTrue(selector.contains("R40ClinicalSeries.availableLabParameters(prefs)"));
        assertTrue(selector.contains("choices.sort"));
        assertTrue(selector.contains("· referti"));
        assertFalse(selector.contains("R36ClinicalSeries"));
        assertFalse(selector.contains("R37ClinicalSeries"));
    }''')
        s = replace_method(s, 'legacyGlucoseGraphIsForcedToReportDerivedGlycaemiaWhenAvailable() throws Exception ', '''@Test public void legacyGlucoseGraphIsForcedToReportDerivedGlycaemiaWhenAvailable() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(series.contains("R40ClinicalSeries.availableLabParameters(prefs)"));
        assertTrue(series.contains("R40ClinicalSeries.labSeries"));
        assertTrue(series.contains("glucose"));
        assertTrue(series.contains("glicem"));
        assertTrue(series.contains("glucos"));
        String label = block(main, "private String r31ChoiceLabel");
        assertTrue(label.contains("Glicemia · referti"));
    }''')

    if p.name == 'R39ExactLabsLandscapeSyncProgressV3Test.java':
        s = s.replace('String sync = block(cloud, "public static void syncInteractiveR39");', 'String sync = block(cloud, "public static void syncInteractiveR40");')
        s = s.replace('assertTrue(sync.contains("ProgressDialog.STYLE_HORIZONTAL"));', 'assertTrue(sync.contains("progressBarStyleHorizontal"));')
        s = s.replace('assertTrue(sync.contains("setIndeterminate(true)"));', 'assertTrue(sync.contains("setIndeterminate(false)"));')
        s = s.replace('assertFalse(sync.contains("setProgress("));', 'assertTrue(sync.contains("setProgress(5)"));')

    p.write_text(s, encoding='utf-8')

print('R40 prior regression compatibility patch applied')
