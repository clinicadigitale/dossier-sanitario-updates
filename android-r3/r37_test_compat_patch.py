from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 36', 'versionCode 37')
    s = s.replace("versionName '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test'", "versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'")
    s = s.replace('versionIsR36SuccessorBuild', 'versionIsR37SuccessorBuild')
    s = s.replace('versionIsR36', 'versionIsR37SuccessorBuild')

    # R37 deliberately supersedes the R36 landscape column widths and report-series helper.
    if p.name == 'R36SyncResponsiveGraphsAgendaRemindersTest.java':
        s = s.replace('screenWidth * 0.34f', 'screenWidth * 0.46f')
        s = s.replace('assertTrue(label.contains("dp(160)"));', 'assertTrue(label.contains("dp(280)"));')
        s = s.replace('assertTrue(label.contains("dp(270)"));', 'assertTrue(label.contains("dp(320)"));')
        s = s.replace('R36ClinicalSeries.availableLabParameters', 'R37ClinicalSeries.availableLabParameters')
        s = s.replace('R36ClinicalSeries.labSeries', 'R37ClinicalSeries.labSeries')

    p.write_text(s, encoding='utf-8')
print('R37 prior regression assertions aligned only where R37 intentionally supersedes R36')
