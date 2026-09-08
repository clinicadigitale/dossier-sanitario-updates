from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 36', 'versionCode 37')
    s = s.replace("versionName '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test'", "versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'")
    s = s.replace('versionIsR36SuccessorBuild', 'versionIsR37SuccessorBuild')
    s = s.replace('versionIsR36', 'versionIsR37SuccessorBuild')
    p.write_text(s, encoding='utf-8')
print('R37 prior regression version assertions aligned')
