from pathlib import Path

CLOUD = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java')
s = CLOUD.read_text(encoding='utf-8')
old = '            if (wanted.equals(key)) return new JSONObject(user.toString());\n'
new = '            if (wanted.equals(key)) return user;\n'
if old not in s:
    raise SystemExit('R15 compile fix failed: account return line not found')
CLOUD.write_text(s.replace(old, new, 1), encoding='utf-8')
print('R15 compile fix applied')
