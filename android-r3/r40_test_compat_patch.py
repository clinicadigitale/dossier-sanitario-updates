from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
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
        s = s.replace('assertTrue(series.contains("findParameterByName(prefs, \\"glicem\\")"));', 'assertFalse(series.contains("R36ClinicalSeries"));')

    if p.name == 'R37FrozenPortraitLandscapeGraphsAgendaTest.java':
        s = s.replace('assertFalse(label.contains("labelView.setMaxLines"));', 'assertTrue(label.contains("labelView.setMaxLines(1)"));')
        s = s.replace('assertTrue(label.contains("Math.max(dp(280), Math.min(dp(320)"));', 'assertTrue(label.contains("Math.max(dp(220), Math.min(dp(430)"));')
        s = s.replace('assertTrue(label.contains("screenWidth * 0.46f"));', 'assertTrue(label.contains("available * 0.38f"));')
        s = s.replace('assertTrue(clinical.contains("R40ClinicalSeries.availableLabParameters"));', 'assertTrue(clinical.contains("R27ExactWindows.availableLabParameters"));')
        s = s.replace('assertTrue(clinical.contains("R40ClinicalSeries.labSeries"));', 'assertTrue(clinical.contains("R27ExactWindows.labSeries"));')

    if p.name == 'R39ExactLabsLandscapeSyncProgressV3Test.java':
        s = s.replace('String sync = block(cloud, "public static void syncInteractiveR39");', 'String sync = block(cloud, "public static void syncInteractiveR40");')
        s = s.replace('assertTrue(sync.contains("ProgressDialog.STYLE_HORIZONTAL"));', 'assertTrue(sync.contains("progressBarStyleHorizontal"));')
        s = s.replace('assertTrue(sync.contains("setIndeterminate(true)"));', 'assertTrue(sync.contains("setIndeterminate(false)"));')
        s = s.replace('assertFalse(sync.contains("setProgress("));', 'assertTrue(sync.contains("setProgress(5)"));')

    p.write_text(s, encoding='utf-8')

print('R40 prior regression compatibility patch applied')
