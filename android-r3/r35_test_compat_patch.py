from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')

for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 34', 'versionCode 35')
    s = s.replace("versionName '1.0.0-android-r34-sync-biometrics-contacts-layout-test'", "versionName '1.0.0-android-r35-second-factor-choice-fix-test'")
    s = s.replace('versionIsR34SyncBiometricsContactsLayoutTest', 'versionIsR35SuccessorBuild')
    s = s.replace('versionIsR34SuccessorBuild', 'versionIsR35SuccessorBuild')
    p.write_text(s, encoding='utf-8')

print('R35 prior regression version assertions aligned')
