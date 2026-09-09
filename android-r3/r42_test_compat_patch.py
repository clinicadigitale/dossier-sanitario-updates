from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')

for p in TEST.glob('R*Test.java'):
    if p.name == 'R42RealDeviceLandscapeGraphSyncFixTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 41', 'versionCode 42')
    s = s.replace('1.0.0-android-r41-realdevice-final-fixes-test', '1.0.0-android-r42-realdevice-landscape-graph-sync-final-test')
    s = s.replace('syncInteractiveR41(activity, prefs)', 'syncInteractiveR42(activity, prefs)')
    p.write_text(s, encoding='utf-8')

p = TEST / 'R41RealDeviceFinalFixTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('String sync = block(cloud, "public static void syncInteractiveR41");',
                  'String sync = block(cloud, "public static void syncInteractiveR42");')
    s = s.replace('assertTrue(sync.contains("Fase 1 di 5"));', 'assertTrue(sync.contains("Fase 1 di 4"));')
    s = s.replace('assertTrue(sync.contains("Fase 2 di 5"));', 'assertTrue(sync.contains("Fase 2 di 4"));')
    s = s.replace('assertTrue(sync.contains("Fase 3 di 5"));', 'assertTrue(sync.contains("Fase 3 di 4"));')
    s = s.replace('assertTrue(sync.contains("Fase 4 di 5"));', 'assertTrue(sync.contains("Fase 4 di 4"));')
    s = s.replace('        assertTrue(sync.contains("Fase 5 di 5"));\n', '')
    s = s.replace('void versionIsR41()', 'void versionIsR42Successor()')
    p.write_text(s, encoding='utf-8')

print('R42 predecessor regression compatibility applied')
