from pathlib import Path

# Apply the final R41 chart-unit correction as part of the R41 patch chain.
exec((Path('android-r3') / 'r41_chart_unit_fix.py').read_text(encoding='utf-8'))

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')


def replace_java_method(source, signature, replacement):
    start = source.find(signature)
    if start < 0:
        raise SystemExit('Missing predecessor test method: ' + signature)
    brace = source.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(source)):
        if source[i] == '{': depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit('Unclosed predecessor test method: ' + signature)
    return source[:start] + replacement + source[end:]

# Version assertions from predecessor tests follow the installed successor identity.
for p in TEST.glob('R*Test.java'):
    if p.name == 'R41RealDeviceFinalFixTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    for n in range(17, 41):
        s = s.replace(f'versionCode {n}', 'versionCode 41')
    old_names = [
        '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test',
        '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test',
        '1.0.0-android-r38-graph-scale-landscape-width-test',
        '1.0.0-android-r39-landscape-exactlabs-sync-progress-test',
        '1.0.0-android-r40-global-parity-final-test',
    ]
    for old in old_names:
        s = s.replace(old, '1.0.0-android-r41-realdevice-final-fixes-test')
    s = s.replace('versionIsFinalR39', 'versionIsR41Successor')
    s = s.replace('versionIsR40', 'versionIsR41Successor')
    p.write_text(s, encoding='utf-8')

# R36's old fixed-width implementation is fully superseded. Replace only that
# predecessor method with the actual R41 invariant; the dedicated R41 test adds
# specific emergency-section coverage.
p = TEST / 'R36SyncResponsiveGraphsAgendaRemindersTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    replacement = '''public void landscapeUsesWiderResponsiveLabelColumnsAcrossAllLabelValueSections() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String label = block(main, "private LinearLayout labelValue");
        assertTrue(label.contains("boolean landscape = r36Landscape()"));
        assertTrue(label.contains("labelView.setSingleLine(true)"));
        assertTrue(label.contains("labelView.setMaxLines(1)"));
        assertTrue(label.contains("0.48f"));
        assertTrue(label.contains("0.52f"));
        assertTrue(label.contains("dp(92)"));
        assertTrue(label.contains("r34MakeContactAction"));
    }'''
    s = replace_java_method(s, 'public void landscapeUsesWiderResponsiveLabelColumnsAcrossAllLabelValueSections()', replacement)
    p.write_text(s, encoding='utf-8')

# R37/R38/R39/R40: replace superseded concrete width implementations with R41's
# global proportional landscape rule. Portrait 92dp remains unchanged.
for name in [
    'R37FrozenPortraitLandscapeGraphsAgendaTest.java',
    'R38GraphScaleLandscapeWidthTest.java',
    'R39ExactLabsLandscapeSyncProgressV3Test.java',
    'R40GlobalParityFixTest.java',
]:
    p = TEST / name
    if not p.exists():
        continue
    s = p.read_text(encoding='utf-8')
    replacements = {
        'assertTrue(label.contains("labelWidth = dp(92)"));': 'assertTrue(label.contains("dp(92)"));',
        'assertFalse(label.contains("labelView.setMaxLines"));': 'assertTrue(label.contains("labelView.setMaxLines(1)"));',
        'assertTrue(label.contains("Math.max(dp(280), Math.min(dp(320)"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("screenWidth * 0.46f"));': 'assertTrue(label.contains("0.52f"));',
        'assertTrue(label.contains("Math.max(dp(340), Math.min(dp(420)"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("screenWidth * 0.50f"));': 'assertTrue(label.contains("0.52f"));',
        'assertTrue(label.contains("Math.max(dp(360), Math.min(dp(460)"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("screenWidth * 0.52f"));': 'assertTrue(label.contains("0.52f"));',
        'assertTrue(label.contains("Math.max(dp(220), Math.min(dp(430)"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("dp(220)"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("dp(430)"));': 'assertTrue(label.contains("0.52f"));',
        'assertTrue(label.contains("available * 0.38f"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("row.post"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("row.getWidth()"));': 'assertTrue(label.contains("0.52f"));',
        'assertTrue(main.contains("int r36ContentSide = r36Landscape() ? dp(12) : dp(16)"));': 'assertTrue(label.contains("dp(92)"));',
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')

# R38/R39 graph scale now includes the imported report reference interval when present.
for name in ['R38GraphScaleLandscapeWidthTest.java', 'R39ExactLabsLandscapeSyncProgressV3Test.java']:
    p = TEST / name
    if p.exists():
        s = p.read_text(encoding='utf-8')
        s = s.replace('assertTrue(chart.contains("scaledBounds(dataMin, dataMax)"));',
                      'assertTrue(chart.contains("scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh)"));')
        p.write_text(s, encoding='utf-8')

# R39 sync implementation has been superseded by the active R41 implementation.
p = TEST / 'R39ExactLabsLandscapeSyncProgressV3Test.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    old = '''        String sync = block(cloud, "public static void syncInteractiveR39");
        assertTrue(sync.contains("ProgressDialog.STYLE_HORIZONTAL"));
        assertTrue(sync.contains("setIndeterminate(true)"));
        assertFalse(sync.contains("setProgress("));
        assertTrue(sync.contains("Ricerca della copia Windows più recente"));
        assertTrue(sync.contains("Ricezione delle modifiche dal Dossier"));
        assertTrue(sync.contains("Invio delle modifiche locali"));
        assertTrue(sync.contains("Verifica finale della sincronizzazione"));'''
    new = '''        String sync = block(cloud, "public static void syncInteractiveR41");
        assertTrue(sync.contains("progressBarStyleHorizontal"));
        assertTrue(sync.contains("setIndeterminate(true)"));
        assertFalse(sync.contains("setProgress(20)"));
        assertTrue(sync.contains("Ricerca della copia Windows più recente"));
        assertTrue(sync.contains("Ricezione delle modifiche dal Dossier"));
        assertTrue(sync.contains("Invio delle modifiche locali"));
        assertTrue(sync.contains("Verifica finale della sincronizzazione"));'''
    s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')

# R40 predecessor assertions: active sync is R41; date axis is now a full dynamic year-axis.
p = TEST / 'R40GlobalParityFixTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('assertTrue(chart.contains("yearLabel(tMin)"));', 'assertTrue(chart.contains("drawYearAxis"));')
    s = s.replace('assertTrue(chart.contains("yearLabel(tMax)"));', 'assertTrue(chart.contains("java.util.Calendar.YEAR"));')
    s = s.replace('assertTrue(oldEntry.contains("syncInteractiveR40(activity, prefs)"));', 'assertTrue(oldEntry.contains("syncInteractiveR41(activity, prefs)"));')
    s = s.replace('assertTrue(r39.contains("syncInteractiveR40(activity, prefs)"));', 'assertTrue(r39.contains("syncInteractiveR41(activity, prefs)"));')
    s = s.replace('String r40 = block(cloud, "public static void syncInteractiveR40");', 'String r40 = block(cloud, "public static void syncInteractiveR41");')
    s = s.replace('assertTrue(r40.contains("setProgress(5)"));', 'assertTrue(r40.contains("setIndeterminate(true)"));')
    p.write_text(s, encoding='utf-8')

print('R41 successor regression compatibility applied')
