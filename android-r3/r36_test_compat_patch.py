from pathlib import Path
import runpy

# Final source-placement gate after all R36 source transformations.
runpy.run_path('android-r3/r36_agenda_ci_fix.py', run_name='__main__')

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 35', 'versionCode 36')
    s = s.replace("versionName '1.0.0-android-r35-second-factor-choice-fix-test'", "versionName '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test'")
    s = s.replace('versionIsR35SecondFactorChoiceFix', 'versionIsR36SuccessorBuild')
    s = s.replace('versionIsR35SuccessorBuild', 'versionIsR36SuccessorBuild')
    p.write_text(s, encoding='utf-8')
print('R36 prior regression version assertions aligned')
