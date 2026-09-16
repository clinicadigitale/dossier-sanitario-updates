from pathlib import Path

root=Path('android-r3/app/src/test')
if not root.exists():
    raise SystemExit('test root missing')

changed=0
for p in root.rglob('*.java'):
    s=p.read_text(encoding='utf-8')
    old=s
    s=s.replace('versionCode 59','versionCode 60')
    s=s.replace('1.0.0-android-r59-full-modern-parity-test','1.0.0-android-r60-ui-dicom-fixes-test')
    s=s.replace('android-r59-full-modern-parity-test','android-r60-ui-dicom-fixes-test')
    if p.name=='R27CompleteWindowsImportTest.java':
        s=s.replace('R27ExactWindows.recentDocuments(prefs, 4)','R27ExactWindows.recentDocuments(prefs,4)')
    if p.name=='R31MobileParityTest.java':
        s=s.replace('R27ExactWindows.openDocument(this, d)','R27ExactWindows.openDocument(this,d)')
    if p.name=='R32OrderingMonitorTest.java':
        s=s.replace('r31SortedByDate(events, true','r31SortedByDate(events,true')
    if p.name=='R58ModernUiMediaTest.java':
        s=s.replace('Archivio imaging','Imaging e media')
        s=s.replace('Spazio richiesto:','Dimensione studio:')
        s=s.replace('Rendi disponibile offline','Porta lo studio sul dispositivo')
    if p.name=='R59FullModernParityTest.java':
        s=s.replace('Imaging DICOM','DICOM e Imaging')
        s=s.replace('non vengono scaricati automaticamente','Il catalogo è già sincronizzato')
    if s!=old:
        p.write_text(s,encoding='utf-8')
        changed+=1

if changed < 20:
    raise SystemExit(f'expected inherited compatibility updates, got {changed}')
print(f'R60 inherited test compatibility aligned: {changed}')
