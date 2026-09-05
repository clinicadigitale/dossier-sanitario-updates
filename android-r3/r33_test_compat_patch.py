from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')

# All previous release-identity tests must follow the successor build without weakening their functional gates.
for name in [
    'R26NearFinalTest.java',
    'R27CompleteWindowsImportTest.java',
    'R28StartupAsyncTest.java',
    'R29ProgressCrashGuardTest.java',
    'R30BoundedImportTest.java',
    'R31MobileParityTest.java',
    'R32OrderingMonitorTest.java',
]:
    p = TEST / name
    s = p.read_text(encoding='utf-8')
    if 'versionCode 32' in s:
        s = s.replace('versionCode 32', 'versionCode 33')
    if "versionName '1.0.0-android-r32-ordering-monitor-test'" in s:
        s = s.replace("versionName '1.0.0-android-r32-ordering-monitor-test'", "versionName '1.0.0-android-r33-clinical-weight-parity-test'")
    p.write_text(s, encoding='utf-8')

# R32 deliberately had a broader timeline and two pressure charts; R33 tightens both to the Windows rules.
p = TEST / 'R32OrderingMonitorTest.java'
s = p.read_text(encoding='utf-8')
s = s.replace('assertTrue(method.contains("r32ClinicalTimeline()"));', 'assertTrue(method.contains("r33ClinicalTimelineDocuments()"));')
s = s.replace('String helper = block(main, "private JSONArray r32ClinicalTimeline()");\n        assertTrue(helper.contains("\\\"Agenda\\\".equalsIgnoreCase(kind)"));\n        assertTrue(helper.contains("\\\"Rilevazione\\\".equalsIgnoreCase(kind)"));',
'''String helper = block(main, "private JSONArray r33ClinicalTimelineDocuments()");
        assertTrue(helper.contains("timelineVisible"));
        assertTrue(helper.contains("sourceSection"));
        assertTrue(helper.contains("prenot"));''')
s = s.replace('assertTrue(helper.contains("Pressione sistolica"));\n        assertTrue(helper.contains("Pressione diastolica"));\n        assertTrue(helper.contains("Frequenza cardiaca"));',
'''assertTrue(helper.contains("new R33PressureChartView"));
        assertTrue(helper.contains("Frequenza cardiaca"));''')
old_weight = '''        String method = block(main, "private void r31RenderMonitorDetail(String type,String label)");
        assertTrue(method.contains("Storico pesate"));
        assertTrue(method.contains("line.setOrientation(LinearLayout.HORIZONTAL)"));
        assertTrue(method.contains("dp(40)"));
        assertTrue(method.contains("return;"));'''
new_weight = '''        String method = block(main, "private void r31RenderMonitorDetail(String type,String label)");
        assertTrue(method.contains("r33RenderWeightDetail()"));
        String history = block(main, "private void r33RenderWeightHistory(JSONArray rows,boolean oldestFirst,JSONObject journey)");
        assertTrue(history.contains("Storico pesate"));
        assertTrue(history.contains("Diff. precedente"));
        assertTrue(history.contains("Diff. iniziale"));'''
if old_weight not in s:
    raise SystemExit('R33 compatibility failed: R32 weight-history assertion block missing')
s = s.replace(old_weight, new_weight, 1)
s = s.replace('versionIsR32OrderingMonitorTest', 'versionIsR33SuccessorBuild')
p.write_text(s, encoding='utf-8')

print('R33 prior regression tests aligned')
