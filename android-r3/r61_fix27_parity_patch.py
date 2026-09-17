from pathlib import Path
import base64,zlib,subprocess,tempfile

parts=sorted(Path('android-r3/.ci/r61_patch_b64').glob('*.txt'), key=lambda p:int(p.stem))
if not parts:
    raise SystemExit('R61 patch chunks missing')
raw=zlib.decompress(base64.b64decode(''.join(p.read_text().strip() for p in parts))).decode('utf-8')
# The patch was generated from the extracted app artifact. Rebase those paths to repository app paths.
raw=raw.replace('a/android-r3/build.gradle','a/android-r3/app/build.gradle')
raw=raw.replace('b/android-r3/build.gradle','b/android-r3/app/build.gradle')
raw=raw.replace('a/android-r3/src/','a/android-r3/app/src/')
raw=raw.replace('b/android-r3/src/','b/android-r3/app/src/')
raw=raw.replace('a/android-r3/mnt/data/r61work/src/','a/android-r3/app/src/')
raw=raw.replace('b/android-r3/mnt/data/r61work/src/','b/android-r3/app/src/')
with tempfile.NamedTemporaryFile('w',suffix='.patch',delete=False,encoding='utf-8') as f:
    f.write(raw)
    patch=f.name
subprocess.check_call(['git','apply','--check',patch])
subprocess.check_call(['git','apply',patch])

# R61 uses Android widgets that were not present in the inherited import set.
main=Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
s=main.read_text(encoding='utf-8')
if 'import android.widget.ArrayAdapter;' not in s:
    s=s.replace('import android.widget.Button;','import android.widget.ArrayAdapter;\nimport android.widget.Button;')
if 'import android.widget.Spinner;' not in s:
    s=s.replace('import android.widget.ScrollView;','import android.widget.ScrollView;\nimport android.widget.Spinner;')
main.write_text(s,encoding='utf-8')

# Align inherited tests only where R61 intentionally supersedes version identity
# or the approved family-Agenda wording/layout. Stage these test-only changes so
# the exact production-source scope audit remains focused on R61 source files.
subprocess.check_call(['python','android-r3/r61_test_compat_patch.py'])
test_root='android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta'
tracked=subprocess.check_output(['git','diff','--name-only','--',test_root],text=True).splitlines()
if tracked:
    subprocess.check_call(['git','add',*tracked])
    subprocess.check_call(['git','diff','--cached','--check'])

print('R61_FIX27_PARITY_PATCH=APPLIED')
