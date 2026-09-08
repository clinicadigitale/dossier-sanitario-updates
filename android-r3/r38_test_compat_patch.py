from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 37', 'versionCode 38')
    s = s.replace("versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'", "versionName '1.0.0-android-r38-real-graph-data-landscape-width-test'")
    s = s.replace('versionIsR37SuccessorBuild', 'versionIsR38SuccessorBuild')
    s = s.replace('versionIsR37', 'versionIsR38SuccessorBuild')

    # R38 deliberately supersedes R37's capped landscape width and R37 report reader.
    if p.name == 'R36SyncResponsiveGraphsAgendaRemindersTest.java':
        s = s.replace('assertTrue(label.contains("screenWidth * 0.46f"));', 'assertTrue(label.contains("0.48f"));')
        s = s.replace('assertTrue(label.contains("dp(280)"));', 'assertTrue(label.contains("0.48f"));')
        s = s.replace('assertTrue(label.contains("dp(320)"));', 'assertTrue(label.contains("0.52f"));')
        s = s.replace('R37ClinicalSeries.availableLabParameters', 'R38ClinicalSeries.availableLabParameters')
        s = s.replace('R37ClinicalSeries.labSeries', 'R38ClinicalSeries.labSeries')
        s = s.replace('R37ClinicalSeries.glycemiaFromReports', 'R38ClinicalSeries.glycemiaFromReports')

    if p.name == 'R37FrozenPortraitLandscapeGraphsAgendaTest.java':
        s = s.replace('assertTrue(label.contains("Math.max(dp(280), Math.min(dp(320)"));', 'assertTrue(label.contains("0.48f"));')
        s = s.replace('assertTrue(label.contains("screenWidth * 0.46f"));', 'assertTrue(label.contains("0.52f"));')
        s = s.replace('assertTrue(label.contains("labelView.setSingleLine(true)"));', 'assertTrue(label.contains("labelView.setMaxLines(3)"));')
        s = s.replace('R37ClinicalSeries.availableLabParameters', 'R38ClinicalSeries.availableLabParameters')
        s = s.replace('R37ClinicalSeries.labSeries', 'R38ClinicalSeries.labSeries')
        s = s.replace('R37ClinicalSeries.glycemiaFromReports', 'R38ClinicalSeries.glycemiaFromReports')
        s = s.replace('R37ClinicalSeries.java', 'R38ClinicalSeries.java')

    p.write_text(s, encoding='utf-8')
print('R38 prior regression assertions aligned only where R38 intentionally supersedes R37')
