from pathlib import Path
import re

ROOT = Path('android-r3')
TEST = ROOT / 'app/src/test/java/it/dossiersanitario/clinicadigitale/beta'
GRADLE = ROOT / 'app/build.gradle'
R43_NAME = '1.0.0-android-r43-windows-parity-landscape-sync-test'


def replace_test_method(text, name, body):
    m = re.search(r'    @Test public void ' + re.escape(name) + r'\(\)(?: throws Exception)? \{', text)
    if not m:
        return text
    brace = text.find('{', m.start())
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f'R43 test compat: unclosed {name}')
    return text[:m.start()] + body.rstrip() + text[end:]


# Final successor identity in every historical package/version regression.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s+\d+', 'versionCode 43', g, count=1)
g = re.sub(r'versionName\s+[\"\'][^\"\']+[\"\']', f'versionName "{R43_NAME}"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

for p in TEST.glob('R*Test.java'):
    if p.name == 'R43WindowsParityLandscapeSyncTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    for n in range(17, 44):
        s = s.replace(f'versionCode {n}', 'versionCode 43')
    s = re.sub(r'1\.0\.0-android-r\d+[A-Za-z0-9._-]*', R43_NAME, s)
    s = re.sub(
        r'assertTrue\(gradle\.contains\("versionName .*?"\)\);',
        f'assertTrue(gradle.contains("{R43_NAME}"));',
        s
    )
    # All historical interactive entry points now converge on the R43 path.
    for old in ('syncInteractiveR39(activity, prefs)', 'syncInteractiveR40(activity, prefs)',
                'syncInteractiveR41(activity, prefs)', 'syncInteractiveR42(activity, prefs)'):
        s = s.replace(old, 'syncInteractiveR43(activity, prefs)')
    p.write_text(s, encoding='utf-8')

landscape_body = r'''    @Test public void __NAME__() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("ViewGroup.LayoutParams.MATCH_PARENT"));
        assertTrue(label.contains("R43LayoutGeometry.landscapeLabelWidthPx"));
        assertTrue(label.contains("R43LayoutGeometry.portraitLabelWidthPx"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(main.contains("onConfigurationChanged(Configuration newConfig)"));
        String addIf = block(main, "private void r31AddIf");
        assertTrue(addIf.contains("labelValue(label, value.trim())"));
    }'''

landscape_methods = {
    'R36SyncResponsiveGraphsAgendaRemindersTest.java': ['landscapeUsesWiderResponsiveLabelColumnsAcrossAllLabelValueSections'],
    'R37FrozenPortraitLandscapeGraphsAgendaTest.java': ['landscapeLabelColumnIsAlmostDoubleAndSingleLine', 'portraitLabelGeometryIsRestoredToFrozenR34R35Baseline'],
    'R38GraphScaleLandscapeWidthTest.java': ['landscapeColumnIsReallyWiderWhilePortraitStaysFrozen'],
    'R39ExactLabsLandscapeSyncProgressV2Test.java': ['landscapeOnlyUsesWideSingleLineFirstColumn'],
    'R39ExactLabsLandscapeSyncProgressV3Test.java': ['portraitFrozenLandscapeWideSingleLine'],
    'R39LandscapeLabSeriesSyncProgressTest.java': ['portraitRemainsFrozenAndLandscapeLabelsAreOneLine'],
    'R40GlobalParityFixTest.java': ['everyStandardSectionRowUsesOneGlobalLandscapeRuleAndPortraitStaysFrozen'],
    'R41RealDeviceFinalFixTest.java': ['landscapeRuleIsGlobalWeightBasedAndPortraitRemains92dp'],
    'R42RealDeviceLandscapeGraphSyncFixTest.java': ['emergencyAndEveryStandardRowActuallyFillLandscapeCardWidth'],
}
for filename, names in landscape_methods.items():
    p = TEST / filename
    if not p.exists(): continue
    s = p.read_text(encoding='utf-8')
    for name in names:
        s = replace_test_method(s, name, landscape_body.replace('__NAME__', name))
    p.write_text(s, encoding='utf-8')

sync_body = r'''    @Test public void __NAME__() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String sync = block(cloud, "public static void syncInteractiveR43");
        assertTrue(sync.contains("Fase 1 di 4"));
        assertTrue(sync.contains("Ricerca della copia Windows più recente"));
        assertTrue(sync.contains("Fase 2 di 4"));
        assertTrue(sync.contains("Fase 3 di 4"));
        assertTrue(sync.contains("Fase 4 di 4"));
        assertTrue(sync.contains("setIndeterminate(true)"));
        assertFalse(sync.contains("setProgress("));
        assertFalse(sync.contains("20%"));
        assertTrue(sync.contains("verifyArchiveManifestR43"));
        assertTrue(sync.contains("r36RefreshLatestCommittedSnapshot"));
        assertTrue(sync.contains("pullRemoteChanges"));
        assertTrue(sync.contains("uploadPendingChanges"));
        assertTrue(sync.contains("checkCompletionConsumed"));
        String oldEntry = block(cloud, "private static void syncInteractive(Activity activity, SharedPreferences prefs)");
        assertTrue(oldEntry.contains("syncInteractiveR43(activity, prefs)"));
    }'''

sync_methods = {
    'R39ExactLabsLandscapeSyncProgressV2Test.java': ['syncHasVisibleStagedProgress'],
    'R39LandscapeLabSeriesSyncProgressTest.java': ['syncShowsStagesAndRealProgressBar'],
    'R40GlobalParityFixTest.java': ['everyInteractiveCloudSyncPathUsesVisibleR40ProgressUi'],
    'R41RealDeviceFinalFixTest.java': ['syncNoLongerShowsFrozenFakePercentage'],
    'R42RealDeviceLandscapeGraphSyncFixTest.java': ['syncStartsAtRealPhaseOneAndNeverShowsFakePercentage'],
}
for filename, names in sync_methods.items():
    p = TEST / filename
    if not p.exists(): continue
    s = p.read_text(encoding='utf-8')
    for name in names:
        s = replace_test_method(s, name, sync_body.replace('__NAME__', name))
    p.write_text(s, encoding='utf-8')

graph_body = r'''    @Test public void __NAME__() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("private final List<String> dates"));
        assertTrue(chart.contains("pointXForIndex(i, values.size(), left, right)"));
        assertTrue(chart.contains("dateLabelRotationDegrees()"));
        assertTrue(chart.contains("return -45f"));
        assertTrue(chart.contains("shortClinicalDate(dates.get(i))"));
        assertTrue(chart.contains("scaledBoundsWithReference"));
        assertTrue(chart.contains("drawReferenceLine"));
        assertTrue(chart.contains("Data clinica"));
        assertFalse(chart.contains("maximumLabels"));
        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));
    }'''

graph_methods = {
    'R39ExactLabsLandscapeSyncProgressV2Test.java': ['r38GraphMathRemainsPresent'],
    'R39LandscapeLabSeriesSyncProgressTest.java': ['r38GraphFixesRemainFrozen'],
    'R40GlobalParityFixTest.java': ['graphUsesClinicalDatesForHorizontalAxis'],
    'R41RealDeviceFinalFixTest.java': ['chartStillUsesExactRequestedSeriesAndClinicalDates'],
    'R42RealDeviceLandscapeGraphSyncFixTest.java': ['clinicalYearAxisCannotEmitOverlappingEveryTwoYearLabelsOnNarrowPhone'],
}
for filename, names in graph_methods.items():
    p = TEST / filename
    if not p.exists(): continue
    s = p.read_text(encoding='utf-8')
    for name in names:
        s = replace_test_method(s, name, graph_body.replace('__NAME__', name))
    p.write_text(s, encoding='utf-8')

# Historical R39 exact-lab tests are kept, but their implementation target is
# the current single Windows-backed R40 clinical-series bridge.
lab_body = r'''    @Test public void __NAME__() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String selector = block(main, "private void r31SelectClinicalValue");
        String series = block(main, "private JSONArray r31SeriesForChoice");
        assertTrue(selector.contains("R40ClinicalSeries.availableLabParameters(prefs)"));
        assertTrue(series.contains("R40ClinicalSeries.labSeries(prefs, p[1])"));
        assertFalse(series.contains("R26SnapshotBridge.numericValue"));
    }'''
for filename, names in {
    'R39ExactLabsLandscapeSyncProgressV2Test.java': ['reportGraphsUseExactWindowsLabValues'],
    'R39LandscapeLabSeriesSyncProgressTest.java': ['labIndexIsSinglePassAndSeriesStayReportBacked'],
}.items():
    p = TEST / filename
    if not p.exists(): continue
    s = p.read_text(encoding='utf-8')
    for name in names:
        s = replace_test_method(s, name, lab_body.replace('__NAME__', name))
    p.write_text(s, encoding='utf-8')

print('R43 predecessor regressions aligned only for intentional landscape, graph, sync and version supersessions')
