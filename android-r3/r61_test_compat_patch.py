from pathlib import Path

root=Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
changed=0

# R61 intentionally supersedes only package identity and the family-Agenda UI wording/layout.
for p in root.glob('*.java'):
    s=p.read_text(encoding='utf-8')
    old=s
    s=s.replace('versionCode 60','versionCode 61')
    s=s.replace('android-r60-ui-dicom-fixes-test','android-r61-fix27-parity-test')
    if p.name in {'R36SyncResponsiveGraphsAgendaRemindersTest.java','R37FrozenPortraitLandscapeGraphsAgendaTest.java'}:
        s=s.replace('Apri documento originale','Apri documento di riferimento')
    if p.name == 'R37FrozenPortraitLandscapeGraphsAgendaTest.java':
        s=s.replace('assertTrue(agenda.contains("Apri documento di riferimento"));','assertTrue(main.contains("Apri documento di riferimento"));')
    if p.name == 'R59FullModernParityTest.java':
        s=s.replace('Sincronizzata con il telefono','Sincronizzata')
    if s != old:
        p.write_text(s,encoding='utf-8')
        changed += 1

if changed < 20:
    raise SystemExit(f'Unexpectedly few inherited R61 test alignments: {changed}')
print(f'R61 inherited test compatibility aligned: {changed}')
