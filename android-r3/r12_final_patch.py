from pathlib import Path

CLOUD = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java')

s = CLOUD.read_text(encoding='utf-8')

old = '            if (!entity.has("durationMinutes")) entity.put("durationMinutes", 60); if (!entity.has("status")) entity.put("status", "programmato");'
new = '            if (!entity.has("status")) entity.put("status", "programmato");'
if old not in s:
    raise SystemExit('R12 final patch failed: Agenda duration default not found')
s = s.replace(old, new, 1)

old2 = 'e.put("allDay",n.optString("time").isEmpty());e.put("durationMinutes",e.optInt("durationMinutes",60));e.put("status",e.optString("status","programmato"));'
new2 = 'e.put("allDay",n.optString("time").isEmpty());e.put("status",e.optString("status","programmato"));'
if old2 not in s:
    raise SystemExit('R12 final patch failed: standalone Agenda duration default not found')
s = s.replace(old2, new2, 1)

CLOUD.write_text(s, encoding='utf-8')
print('Android R12 final no-invented-duration patch applied successfully')
