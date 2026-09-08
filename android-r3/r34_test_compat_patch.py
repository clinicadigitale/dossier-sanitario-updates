from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')

for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 33', 'versionCode 34')
    s = s.replace("versionName '1.0.0-android-r33-clinical-weight-parity-test'", "versionName '1.0.0-android-r34-sync-biometrics-contacts-layout-test'")
    s = s.replace('versionIsR33ClinicalWeightParityTest', 'versionIsR34SuccessorBuild')
    s = s.replace('versionIsR33SuccessorBuild', 'versionIsR34SuccessorBuild')
    p.write_text(s, encoding='utf-8')

print('R34 prior regression version assertions aligned')
