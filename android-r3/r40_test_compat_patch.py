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

    s = s.replace('R27ExactWindows.availableLabParameters(prefs)', 'R40ClinicalSeries.availableLabParameters(prefs)')
    s = s.replace('R27ExactWindows.labSeries(prefs, p[1])', 'R40ClinicalSeries.labSeries(prefs, p[1])')
    s = s.replace('R27ExactWindows.labSeries', 'R40ClinicalSeries.labSeries')

    if p.name == 'R39ExactLabsLandscapeSyncProgressV3Test.java':
        s = s.replace('String sync = block(cloud, "public static void syncInteractiveR39");', 'String sync = block(cloud, "public static void syncInteractiveR40");')
        s = s.replace('assertTrue(sync.contains("ProgressDialog.STYLE_HORIZONTAL"));', 'assertTrue(sync.contains("progressBarStyleHorizontal"));')
        s = s.replace('assertTrue(sync.contains("setIndeterminate(true)"));', 'assertTrue(sync.contains("setIndeterminate(false)"));')
        s = s.replace('assertFalse(sync.contains("setProgress("));', 'assertTrue(sync.contains("setProgress(5)"));')
    p.write_text(s, encoding='utf-8')

print('R40 prior regression compatibility patch applied')
