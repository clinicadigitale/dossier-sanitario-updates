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
print('R61_FIX27_PARITY_PATCH=APPLIED')
