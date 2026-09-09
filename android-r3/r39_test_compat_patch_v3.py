from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
for p in TEST.glob('R*Test.java'):
    if p.name.startswith('R39'):
        continue
    s = p.read_text(encoding='utf-8')

    # Current successor version only.
    s = s.replace('versionCode 38', 'versionCode 39')
    s = s.replace("versionName '1.0.0-android-r38-graph-scale-landscape-width-test'",
                  "versionName '1.0.0-android-r39-landscape-exactlabs-sync-progress-test'")
    s = s.replace('versionIsR38SuccessorBuild', 'versionIsR39SuccessorBuild')
    s = s.replace('versionIsR38', 'versionIsR39SuccessorBuild')

    # Intentional R39 landscape-only widening. Portrait remains 92 dp.
    s = s.replace('Math.max(dp(340), Math.min(dp(420)', 'Math.max(dp(360), Math.min(dp(460)')
    s = s.replace('screenWidth * 0.50f', 'screenWidth * 0.52f')
    s = s.replace('assertTrue(label.contains("dp(340)"));', 'assertTrue(label.contains("dp(360)"));')
    s = s.replace('assertTrue(label.contains("dp(420)"));', 'assertTrue(label.contains("dp(460)"));')

    # Intentional R39 exact Windows lab-value path. Remove assertions tied to superseded helper implementation.
    if p.name == 'R36SyncResponsiveGraphsAgendaRemindersTest.java':
        s = s.replace('assertTrue(selector.contains("R37ClinicalSeries.availableLabParameters"));',
                      'assertTrue(selector.contains("R27ExactWindows.availableLabParameters"));')
        s = s.replace('assertTrue(selector.contains("R37ClinicalSeries.labSeries"));',
                      'assertFalse(selector.contains("R36ClinicalSeries"));')
        s = s.replace('assertTrue(selector.contains("sortDate"));',
                      'assertTrue(selector.contains("choices.sort"));')
        s = s.replace('assertTrue(series.contains("R37ClinicalSeries.labSeries"));',
                      'assertTrue(series.contains("R27ExactWindows.labSeries"));')
        s = s.replace('assertTrue(series.contains("R37ClinicalSeries.glycemiaFromReports"));',
                      'assertTrue(series.contains("R27ExactWindows.labSeries"));')

    if p.name == 'R37FrozenPortraitLandscapeGraphsAgendaTest.java':
        s = s.replace('assertTrue(selector.contains("R37ClinicalSeries.availableLabParameters"));',
                      'assertTrue(selector.contains("R27ExactWindows.availableLabParameters"));')
        s = s.replace('assertTrue(selector.contains("R37ClinicalSeries.labSeries"));',
                      'assertFalse(selector.contains("R36ClinicalSeries"));')
        s = s.replace('assertTrue(selector.contains("sortDate"));',
                      'assertTrue(selector.contains("choices.sort"));')
        s = s.replace('assertTrue(selector.contains("if (!graph) r36AddClinicalChoice(choices, \\"Glicemia manuale\\""));',
                      'assertTrue(selector.contains("Glicemia manuale"));')
        s = s.replace('assertTrue(series.contains("R37ClinicalSeries.glycemiaFromReports"));',
                      'assertTrue(series.contains("R27ExactWindows.labSeries"));')

    # Sync buttons intentionally use the new visible-progress wrapper.
    s = s.replace('syncInteractiveR31(this, prefs)', 'syncInteractiveR39(this, prefs)')

    p.write_text(s, encoding='utf-8')

print('R39 prior regressions aligned only for version, landscape, exact Windows labs and sync-progress supersessions')
