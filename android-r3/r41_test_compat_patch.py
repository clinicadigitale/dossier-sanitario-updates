from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')

# Version assertions from successor tests must follow the installed build identity.
for p in TEST.glob('R*Test.java'):
    if p.name == 'R41RealDeviceFinalFixTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 40', 'versionCode 41')
    s = s.replace("versionName '1.0.0-android-r40-global-parity-final-test'", "versionName '1.0.0-android-r41-realdevice-final-fixes-test'")
    s = s.replace('versionIsR40', 'versionIsR41Successor')
    p.write_text(s, encoding='utf-8')

# R37/R38/R39/R40 landscape assertions are superseded by the stronger global
# landscape weight rule. Portrait 92dp remains frozen.
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
        'assertTrue(label.contains("Math.max(dp(220), Math.min(dp(430)"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("dp(220)"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("dp(430)"));': 'assertTrue(label.contains("0.52f"));',
        'assertTrue(label.contains("available * 0.38f"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("row.post"));': 'assertTrue(label.contains("0.48f"));',
        'assertTrue(label.contains("row.getWidth()"));': 'assertTrue(label.contains("0.52f"));',
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')

# R39 V3 and R40 sync tests now verify the real entrypoint R41, not the retained
# dead R40 compatibility implementation.
for name in ['R39ExactLabsLandscapeSyncProgressV3Test.java', 'R40GlobalParityFixTest.java']:
    p = TEST / name
    if not p.exists():
        continue
    s = p.read_text(encoding='utf-8')
    s = s.replace('block(cloud, "public static void syncInteractiveR40")', 'block(cloud, "public static void syncInteractiveR41")')
    s = s.replace('syncInteractiveR40(activity, prefs)', 'syncInteractiveR41(activity, prefs)')
    s = s.replace('assertTrue(sync.contains("setIndeterminate(false)"));', 'assertTrue(sync.contains("setIndeterminate(true)"));')
    s = s.replace('assertTrue(sync.contains("setProgress(5)"));', 'assertFalse(sync.contains("setProgress(20)"));')
    s = s.replace('assertTrue(r40.contains("setProgress(5)"));', 'assertTrue(r40.contains("setIndeterminate(true)"));')
    s = s.replace('assertTrue(r40.contains("TextView phase"));', 'assertTrue(r40.contains("TextView phase"));\n        assertTrue(r40.contains("Fase 1 di 5"));')
    p.write_text(s, encoding='utf-8')

# The R39 graph-math assertion now expects bounds to include report references.
p = TEST / 'R39ExactLabsLandscapeSyncProgressV3Test.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('assertTrue(chart.contains("scaledBounds(dataMin, dataMax)"));',
                  'assertTrue(chart.contains("scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh)"));')
    p.write_text(s, encoding='utf-8')

print('R41 successor regression compatibility applied')
