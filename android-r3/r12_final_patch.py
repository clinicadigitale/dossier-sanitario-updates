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

old3 = '                .setMessage("La memoria viene controllata prima di qualsiasi download. La scelta potrà essere cambiata successivamente con copia, verifica e solo dopo rimozione della vecchia copia.")'
new3 = '                .setMessage("La memoria viene controllata prima di qualsiasi download. Se scegli una scheda SD, il Dossier verrà conservato cifrato per proteggere i dati sanitari; l’accesso a documenti e contenuti di archivio può risultare più lento rispetto alla memoria interna, in funzione delle prestazioni della scheda. La scelta potrà essere cambiata successivamente con copia, verifica e solo dopo rimozione della vecchia copia.")'
if old3 not in s:
    raise SystemExit('R12 final patch failed: initial storage warning not found')
s = s.replace(old3, new3, 1)

old4 = '        new AlertDialog.Builder(activity).setTitle("Memoria del Dossier").setSingleChoiceItems(labels, 0, null)\n                .setNegativeButton("Annulla", null)'
new4 = '        new AlertDialog.Builder(activity).setTitle("Memoria del Dossier").setSingleChoiceItems(labels, 0, null)\n                .setMessage("Se scegli una scheda SD, il Dossier verrà conservato cifrato per proteggere i dati sanitari. L’accesso a documenti e contenuti di archivio può risultare più lento rispetto alla memoria interna, in funzione delle prestazioni della scheda.")\n                .setNegativeButton("Annulla", null)'
if old4 not in s:
    raise SystemExit('R12 final patch failed: standalone storage warning insertion point not found')
s = s.replace(old4, new4, 1)

old5 = '        new AlertDialog.Builder(activity).setTitle("Sposta archivio Dossier").setSingleChoiceItems(labels,0,null).setNegativeButton("Annulla",null).setPositiveButton("Sposta",(dialog,which)->{'
new5 = '        new AlertDialog.Builder(activity).setTitle("Sposta archivio Dossier").setSingleChoiceItems(labels,0,null).setMessage("Se scegli una scheda SD, il Dossier resterà cifrato per proteggere i dati sanitari. L’accesso ai contenuti di archivio può risultare più lento rispetto alla memoria interna.").setNegativeButton("Annulla",null).setPositiveButton("Sposta",(dialog,which)->{'
if old5 not in s:
    raise SystemExit('R12 final patch failed: move storage warning insertion point not found')
s = s.replace(old5, new5, 1)

CLOUD.write_text(s, encoding='utf-8')
print('Android R12 final invariants and SD warning patch applied successfully')
