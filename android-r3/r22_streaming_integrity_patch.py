from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R22 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')
    s = s.replace('R21FastDsl5.decryptVerified(', 'R22StreamingDsl5.decryptVerified(')
    s = replace_once(
        s,
        'File verified = File.createTempFile("r21_verify_", ".zip", parent);',
        'File verified = File.createTempFile("r22_verify_", ".zip", parent);',
        'core verified temp name',
    )
    s = replace_once(
        s,
        'File verified = File.createTempFile("r21_verified_", ".zip", activity.getCacheDir());',
        'File verified = File.createTempFile("r22_verified_", ".zip", snapshot.getParentFile());',
        'verified temp on snapshot storage',
    )
    CLOUD.write_text(s, encoding='utf-8')


def patch_version_and_dependency():
    m = MAIN.read_text(encoding='utf-8')
    m = m.replace('Android R21 TEST', 'Android R22 TEST')
    m = m.replace('Aiuto R21', 'Aiuto R22')
    m = m.replace('R21: struttura presente', 'R22: struttura presente')
    m = m.replace('R21 mantiene lo stesso pacchetto Android', 'R22 mantiene lo stesso pacchetto Android')
    m = m.replace('Installala sopra la R20', 'Installala sopra la R21')
    MAIN.write_text(m, encoding='utf-8')

    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 21', 'versionCode 22', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r21-test'", "versionName '1.0.0-android-r22-test'", 'versionName')
    dep = "    implementation 'org.bouncycastle:bcprov-jdk18on:1.78.1'\n"
    if dep not in g:
        g = replace_once(g, 'dependencies {\n', 'dependencies {\n' + dep, 'dependencies block')
    GRADLE.write_text(g, encoding='utf-8')


patch_cloud()
patch_version_and_dependency()
print('R22 bounded-memory streaming integrity patch applied')
