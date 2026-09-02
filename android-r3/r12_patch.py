from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R12 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    s = replace_once(
        s,
        '        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);\n        cleanCameraTemp();',
        '        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);\n        cleanCameraTemp();\n        R12CloudManager.schedulePeriodic(this, prefs);',
        'startup sync scheduling'
    )

    s = replace_once(
        s,
        '            profileName.setText(profileDisplayName());\n            logEvent("Dati profilo aggiornati");',
        '            profileName.setText(profileDisplayName());\n            R12CloudManager.queueProfilePut(this, prefs);\n            logEvent("Dati profilo aggiornati");',
        'profile cloud queue'
    )

    s = replace_once(
        s,
        '                        upsertRecord(PREF_EXEMPTIONS, obj);\n                        logEvent(existing == null ? "Esenzione aggiunta: " + c : "Esenzione aggiornata: " + c);',
        '                        upsertRecord(PREF_EXEMPTIONS, obj);\n                        R12CloudManager.queueExemptionPut(this, prefs, obj);\n                        logEvent(existing == null ? "Esenzione aggiunta: " + c : "Esenzione aggiornata: " + c);',
        'exemption cloud queue'
    )

    s = replace_once(
        s,
        '                        upsertRecord(PREF_DOCTORS, obj);\n                        logEvent(existing == null ? "Medico/specialista aggiunto: " + n : "Medico/specialista aggiornato: " + n);',
        '                        upsertRecord(PREF_DOCTORS, obj);\n                        R12CloudManager.queueDoctorPut(this, prefs, obj);\n                        logEvent(existing == null ? "Medico/specialista aggiunto: " + n : "Medico/specialista aggiornato: " + n);',
        'doctor cloud queue'
    )

    delete_start = s.find('    private void confirmDeleteRecord(String key, long id, String question, String eventText, String returnSection) {')
    delete_end = s.find('    private void logEvent(String text) {', delete_start)
    if delete_start < 0 or delete_end < 0:
        raise SystemExit('R12 patch failed: generic delete block not found')
    delete_method = r'''    private void confirmDeleteRecord(String key, long id, String question, String eventText, String returnSection) {
        new AlertDialog.Builder(this)
                .setTitle("Conferma eliminazione")
                .setMessage(question)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Elimina", (d, w) -> {
                    JSONArray array = readArray(key);
                    JSONObject previous = null;
                    for (int i = array.length() - 1; i >= 0; i--) {
                        JSONObject obj = array.optJSONObject(i);
                        if (obj != null && obj.optLong("id", -1L) == id) {
                            previous = obj;
                            array.remove(i);
                        }
                    }
                    saveArray(key, array);
                    R12CloudManager.queueNativeDelete(this, prefs, key, previous);
                    logEvent(eventText);
                    renderSection(returnSection);
                })
                .show();
    }

'''
    s = s[:delete_start] + delete_method + s[delete_end:]

    s = replace_once(
        s,
        '        content.addView(legacy, matchWrapBottom(14));\n\n        refreshDocumentState();\n    }',
        '        content.addView(legacy, matchWrapBottom(14));\n\n        refreshDocumentState();\n        R12CloudManager.appendCloudDocuments(this, content, prefs);\n    }',
        'cloud documents panel'
    )

    # Every successful photo acquisition/edit is queued after the editor has committed it locally.
    s = replace_once(
        s,
        '            if (resultCode == RESULT_OK) {\n                logEvent(pendingEditorNewCapture ? "Nuovo documento fotografico salvato" : "Documento fotografico modificato");\n                Toast.makeText(this, "Documento salvato nel Dossier", Toast.LENGTH_SHORT).show();\n            }',
        '            if (resultCode == RESULT_OK) {\n                logEvent(pendingEditorNewCapture ? "Nuovo documento fotografico salvato" : "Documento fotografico modificato");\n                R12CloudManager.queueLocalPhotos(this, prefs, privatePhotos());\n                Toast.makeText(this, "Documento salvato nel Dossier", Toast.LENGTH_SHORT).show();\n            }',
        'photo cloud queue'
    )

    old_cloud = '''        LinearLayout cloud = card();\n        cloud.addView(sectionHeader("Sincronizzazione cloud"));\n        cloud.addView(text("In questa fase verifichiamo prima che Android sappia creare e ricostruire autonomamente un backup completo e cifrato. Il collegamento diretto al cloud familiare verrà attivato solo dopo questo test di integrità.", 13, MUTED, false));\n        content.addView(cloud, matchWrapBottom(14));'''
    s = replace_once(
        s,
        old_cloud,
        '        R12CloudManager.renderCloudPanel(this, content, prefs);',
        'backup cloud panel'
    )

    # The Windows/Dossier identity must survive duplicate resolution. Google linkage already uses the same helper.
    s = replace_once(
        s,
        '        String[] keys = {"google_event_id", "google_calendar_id", "google_sync_state", "google_updated"};',
        '        String[] keys = {"google_event_id", "google_calendar_id", "google_sync_state", "google_updated", "windows_id"};',
        'agenda Dossier identity preservation'
    )

    old_duplicate_save = '''                        if (isNew) {\n                            JSONObject duplicate = findSimilarAgendaItem(obj);\n                            if (duplicate != null) {\n                                obj.put("duplicate_hold", true);\n                                upsertRecord(PREF_AGENDA, obj);\n                                refreshAgendaCard(obj);\n                                showDuplicateAgendaDialog(obj, duplicate);\n                            }\n                        }\n                        Toast.makeText(this, "Appuntamento salvato", Toast.LENGTH_SHORT).show();'''
    new_duplicate_save = '''                        if (isNew) {\n                            JSONObject duplicate = findSimilarAgendaItem(obj);\n                            if (duplicate != null) {\n                                obj.put("duplicate_hold", true);\n                                upsertRecord(PREF_AGENDA, obj);\n                                refreshAgendaCard(obj);\n                                showDuplicateAgendaDialog(obj, duplicate);\n                            } else {\n                                R12CloudManager.queueAgendaPut(this, prefs, obj);\n                            }\n                        } else {\n                            R12CloudManager.queueAgendaPut(this, prefs, obj);\n                        }\n                        Toast.makeText(this, "Appuntamento salvato", Toast.LENGTH_SHORT).show();'''
    s = replace_once(s, old_duplicate_save, new_duplicate_save, 'agenda duplicate-gated sync')

    s = replace_once(
        s,
        '            upsertRecord(PREF_AGENDA, item);\n            refreshAgendaCard(item);\n            mirrorAgendaToClinicalAsync(item);',
        '            upsertRecord(PREF_AGENDA, item);\n            refreshAgendaCard(item);\n            mirrorAgendaToClinicalAsync(item);\n            R12CloudManager.queueAgendaPut(this, prefs, item);',
        'keep both cloud queue'
    )

    s = replace_once(
        s,
        '            upsertRecord(PREF_AGENDA, merged);\n            refreshAgendaCard(merged);\n            mirrorAgendaToClinicalAsync(merged);\n            deleteAgendaLocal(drop.optLong("id", -1L));',
        '            upsertRecord(PREF_AGENDA, merged);\n            refreshAgendaCard(merged);\n            mirrorAgendaToClinicalAsync(merged);\n            R12CloudManager.queueAgendaPut(this, prefs, merged);\n            deleteAgendaLocal(drop.optLong("id", -1L));',
        'resolved duplicate cloud queue'
    )

    agenda_delete_start = s.find('    private void confirmDeleteAgenda(long id) {')
    agenda_delete_end = s.find('    private void renderMonitoraggio() {', agenda_delete_start)
    if agenda_delete_start < 0 or agenda_delete_end < 0:
        raise SystemExit('R12 patch failed: agenda delete block not found')
    agenda_delete = r'''    private void confirmDeleteAgenda(long id) {
        new AlertDialog.Builder(this)
                .setTitle("Eliminare l'appuntamento?")
                .setMessage("Verrà rimosso anche l'evento collegato dalla Cronologia clinica.")
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Elimina", (d, w) -> {
                    JSONArray agenda = readArray(PREF_AGENDA);
                    JSONObject previous = null;
                    for (int i = agenda.length() - 1; i >= 0; i--) {
                        JSONObject obj = agenda.optJSONObject(i);
                        if (obj != null && obj.optLong("id", -1L) == id) {
                            previous = obj;
                            agenda.remove(i);
                        }
                    }
                    saveArray(PREF_AGENDA, agenda);
                    R12CloudManager.queueAgendaDelete(this, prefs, previous);
                    removeAgendaCard(id);
                    removeAgendaClinicalMirrorAsync(id);
                    Toast.makeText(this, "Appuntamento eliminato", Toast.LENGTH_SHORT).show();
                })
                .show();
    }

'''
    s = s[:agenda_delete_start] + agenda_delete + s[agenda_delete_end:]

    visible = {
        'Android R11 TEST': 'Android R12 TEST',
        'Aiuto R11': 'Aiuto R12',
        'R11: struttura presente': 'R12: struttura presente',
        'R11 mantiene lo stesso pacchetto Android': 'R12 mantiene lo stesso pacchetto Android',
        'Installala sopra la R10': 'Installala sopra la R11'
    }
    for old, new in visible.items():
        s = s.replace(old, new)

    MAIN.write_text(s, encoding='utf-8')


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    s = replace_once(
        s,
        '    private static final String POLICY_KEY = "r12_sync_policy";\n',
        '    private static final String POLICY_KEY = "r12_sync_policy";\n'
        '    private static final String LOCAL_PHOTO_MAP_KEY = "r12_local_photo_map_json";\n',
        'local photo map constant'
    )

    # Avoid showing a second copy of a photo already rendered by the native Android document list.
    s = replace_once(
        s,
        '            if (doc == null || doc.optBoolean("deleted", false)) continue;\n            LinearLayout row = new LinearLayout(activity);',
        '            if (doc == null || doc.optBoolean("deleted", false)) continue;\n'
        '            String originalName = doc.optString("originalName", "");\n'
        '            if (!originalName.isEmpty() && new File(new File(activity.getFilesDir(), "dossier_documents"), originalName).isFile()) continue;\n'
        '            LinearLayout row = new LinearLayout(activity);',
        'cloud document duplicate display suppression'
    )

    # Existing Android photos become normal Dossier document changes after a family connection.
    s = replace_once(
        s,
        '        pullRemoteChanges(context, prefs, cfg, true);\n        schedulePeriodic(context, prefs);',
        '        pullRemoteChanges(context, prefs, cfg, true);\n'
        '        queueLocalPhotos(context, prefs, localPhotoFiles(context));\n'
        '        schedulePeriodic(context, prefs);',
        'family local photo adoption'
    )

    # Standalone snapshot uses stable document IDs instead of inventing a different ID at each rebuild.
    s = replace_once(
        s,
        '            int pi=0;for(File photo:photos){String id="document_"+UUID.randomUUID();JSONObject d=new JSONObject();',
        '            int pi=0;for(File photo:photos){String id=ensureLocalPhotoId(prefs,photo);JSONObject d=new JSONObject();',
        'standalone stable local photo IDs'
    )

    s = replace_once(
        s,
        '        importSnapshot(context, prefs, cfg, snapshot, recovery);\n        schedulePeriodic(context, prefs);',
        '        importSnapshot(context, prefs, cfg, snapshot, recovery);\n'
        '        markAllLocalPhotoFingerprints(prefs, localPhotoFiles(context));\n'
        '        schedulePeriodic(context, prefs);',
        'standalone local photo fingerprint baseline'
    )

    insert_marker = '    public static void queueAgendaPut(Context context, SharedPreferences prefs, JSONObject nativeItem) {'
    if insert_marker not in s:
        raise SystemExit('R12 patch failed: cloud local queue insertion point missing')
    local_photo_code = r'''    public static void queueLocalPhotos(Context context, SharedPreferences prefs, File[] photos) {
        try {
            JSONObject cfg = loadConfig(prefs);
            if (cfg.optString("archiveId", "").isEmpty() || photos == null) return;
            JSONObject map = localPhotoMap(prefs);
            JSONArray docs = readArray(prefs, DOCS_KEY);
            for (File photo : photos) {
                if (photo == null || !photo.isFile()) continue;
                String key = photo.getName();
                JSONObject row = map.optJSONObject(key);
                if (row == null) { row = new JSONObject(); row.put("windowsId", "document_" + UUID.randomUUID()); map.put(key, row); }
                String fingerprint = photo.length() + ":" + photo.lastModified();
                if (fingerprint.equals(row.optString("fingerprint", "")) && hasPendingOrRawDocument(prefs, row.optString("windowsId", ""))) continue;
                String id = row.optString("windowsId", "");
                if (id.isEmpty()) { id = "document_" + UUID.randomUUID(); row.put("windowsId", id); }
                JSONObject entity = rawEntity(prefs, "documents", id);
                if (entity == null) entity = new JSONObject();
                entity.put("id", id);
                entity.put("profileId", cfg.optString("linkedProfileId", ""));
                entity.put("title", "Documento fotografico");
                entity.put("originalName", photo.getName());
                entity.put("mimeType", "image/jpeg");
                entity.put("size", photo.length());
                entity.put("addedAt", entity.optString("addedAt", Instant.ofEpochMilli(photo.lastModified()).toString()));
                entity.put("updatedAt", Instant.now().toString());
                JSONObject blob = new JSONObject();
                blob.put("__blob", "blobs/document.bin");
                blob.put("name", photo.getName());
                blob.put("type", "image/jpeg");
                blob.put("size", photo.length());
                entity.put("fileBlob", blob);
                queueDocumentPut(context, prefs, cfg, id, entity, photo);
                row.put("fingerprint", fingerprint);
                row.put("updatedAt", Instant.now().toString());
                upsertCloudDocIndex(docs, entity);
            }
            prefs.edit().putString(LOCAL_PHOTO_MAP_KEY, map.toString()).apply();
            saveArray(prefs, DOCS_KEY, docs);
        } catch (Exception ignored) {}
    }

    private static void queueDocumentPut(Context context, SharedPreferences prefs, JSONObject cfg, String entityId, JSONObject entity, File localFile) throws Exception {
        JSONObject previous = rawEntity(prefs, "documents", entityId);
        JSONObject oldMeta = previous == null ? null : previous.optJSONObject("_syncMeta");
        int baseRevision = oldMeta == null ? 0 : oldMeta.optInt("revision", 0);
        String eventId = "change_" + UUID.randomUUID();
        String now = Instant.now().toString();
        JSONObject fields = oldMeta == null || oldMeta.optJSONObject("fields") == null ? new JSONObject() : new JSONObject(oldMeta.optJSONObject("fields").toString());
        for (String field : Arrays.asList("title", "originalName", "mimeType", "size", "fileBlob")) {
            JSONObject stamp = new JSONObject(); stamp.put("at", now); stamp.put("deviceId", cfg.optString("deviceId", deviceId(prefs))); stamp.put("eventId", eventId); fields.put(field, stamp);
        }
        JSONObject meta = new JSONObject(); meta.put("revision", baseRevision + 1); meta.put("baseRevision", baseRevision); meta.put("eventId", eventId); meta.put("deviceId", cfg.optString("deviceId")); meta.put("updatedAt", now); meta.put("fields", fields);
        entity.put("_syncMeta", meta); entity.put("updatedAt", now); saveRawEntity(prefs, "documents", entityId, entity);
        JSONObject event = new JSONObject(); event.put("id", eventId); event.put("profileId", entity.optString("profileId", "")); event.put("status", "pending"); event.put("operation", "put"); event.put("store", "documents"); event.put("entityId", entityId); event.put("baseRevision", baseRevision); event.put("revision", baseRevision + 1); event.put("deviceId", cfg.optString("deviceId")); event.put("createdAt", now); event.put("entity", entity); event.put("localFilePath", localFile.getAbsolutePath()); event.put("blobName", "blobs/document.bin"); event.put("large", localFile.length() >= 5L * MB);
        enqueueEvent(prefs, event); scheduleImmediate(context, prefs);
    }

'''
    s = s.replace(insert_marker, local_photo_code + insert_marker, 1)

    event_start = s.find('    private static byte[] eventBlob(JSONObject event, byte[] recovery, String deviceId) throws Exception {')
    event_end = s.find('    private static int pullRemoteChanges(', event_start)
    if event_start < 0 or event_end < 0:
        raise SystemExit('R12 patch failed: event blob block not found')
    event_blob = r'''    private static byte[] eventBlob(JSONObject event, byte[] recovery, String deviceId) throws Exception {
        JSONObject clone = new JSONObject(event.toString());
        clone.remove("entity"); clone.remove("previous"); clone.remove("localFilePath"); clone.remove("blobName"); clone.remove("large");
        JSONObject payload = new JSONObject(); payload.put("event", clone); payload.put("entity", event.optJSONObject("entity"));
        ByteArrayOutputStream zipBytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(zipBytes)) {
            zip.putNextEntry(new ZipEntry("event.json")); zip.write(payload.toString().getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
            String localPath = event.optString("localFilePath", "");
            if (!localPath.isEmpty()) {
                File file = new File(localPath);
                if (!file.isFile()) throw new Exception("Documento locale da sincronizzare non più disponibile.");
                String blobName = event.optString("blobName", "blobs/document.bin");
                zip.putNextEntry(new ZipEntry(blobName));
                try (FileInputStream in = new FileInputStream(file)) { byte[] buffer = new byte[65536]; int n; while ((n = in.read(buffer)) >= 0) zip.write(buffer, 0, n); }
                zip.closeEntry();
            }
        }
        JSONObject meta = new JSONObject(); meta.put("kind", "change"); meta.put("eventId", event.optString("id")); meta.put("deviceId", deviceId);
        return R12Crypto.encryptDsl5(zipBytes.toByteArray(), recovery, meta);
    }

'''
    s = s[:event_start] + event_blob + s[event_end:]

    # Smart mode: metadata may travel immediately on any network; large document payloads and periodic maintenance wait for unmetered Wi-Fi.
    old_schedule = '''    public static void schedulePeriodic(Context context, SharedPreferences prefs) {\n        String policy = prefs.getString(POLICY_KEY, "smart"); WorkManager wm = WorkManager.getInstance(context);\n        if ("manual".equals(policy) || !configured(prefs)) { wm.cancelUniqueWork(WORK_PERIODIC); return; }\n        NetworkType type = "wifi".equals(policy) ? NetworkType.UNMETERED : NetworkType.CONNECTED;\n        Constraints constraints = new Constraints.Builder().setRequiredNetworkType(type).build();\n        PeriodicWorkRequest request = new PeriodicWorkRequest.Builder(R12SyncWorker.class, 6, TimeUnit.HOURS).setConstraints(constraints).build();\n        wm.enqueueUniquePeriodicWork(WORK_PERIODIC, ExistingPeriodicWorkPolicy.UPDATE, request);\n    }\n\n    private static void scheduleImmediate(Context context, SharedPreferences prefs) {\n        String policy = prefs.getString(POLICY_KEY, "smart"); if ("manual".equals(policy)) return; NetworkType type = "wifi".equals(policy) ? NetworkType.UNMETERED : NetworkType.CONNECTED;\n        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(R12SyncWorker.class).setConstraints(new Constraints.Builder().setRequiredNetworkType(type).build()).build();\n        WorkManager.getInstance(context).enqueueUniqueWork(WORK_IMMEDIATE, ExistingWorkPolicy.REPLACE, request);\n    }'''
    new_schedule = '''    public static void schedulePeriodic(Context context, SharedPreferences prefs) {\n        String policy = prefs.getString(POLICY_KEY, "smart"); WorkManager wm = WorkManager.getInstance(context);\n        if ("manual".equals(policy) || !configured(prefs)) { wm.cancelUniqueWork(WORK_PERIODIC); return; }\n        NetworkType type = ("wifi".equals(policy) || "smart".equals(policy)) ? NetworkType.UNMETERED : NetworkType.CONNECTED;\n        Constraints.Builder cb = new Constraints.Builder().setRequiredNetworkType(type);\n        if ("smart".equals(policy)) cb.setRequiresCharging(true);\n        PeriodicWorkRequest request = new PeriodicWorkRequest.Builder(R12SyncWorker.class, 6, TimeUnit.HOURS).setConstraints(cb.build()).build();\n        wm.enqueueUniquePeriodicWork(WORK_PERIODIC, ExistingPeriodicWorkPolicy.UPDATE, request);\n    }\n\n    private static void scheduleImmediate(Context context, SharedPreferences prefs) {\n        String policy = prefs.getString(POLICY_KEY, "smart"); if ("manual".equals(policy)) return;\n        NetworkType type;\n        if ("wifi".equals(policy)) type = NetworkType.UNMETERED;\n        else if ("smart".equals(policy) && hasLargePending(prefs)) type = NetworkType.UNMETERED;\n        else type = NetworkType.CONNECTED;\n        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(R12SyncWorker.class).setConstraints(new Constraints.Builder().setRequiredNetworkType(type).build()).build();\n        WorkManager.getInstance(context).enqueueUniqueWork(WORK_IMMEDIATE, ExistingWorkPolicy.REPLACE, request);\n    }'''
    s = replace_once(s, old_schedule, new_schedule, 'smart synchronization policy')

    helper_marker = '    private static JSONObject findById(JSONArray array,String id)'
    if helper_marker not in s:
        raise SystemExit('R12 patch failed: local photo helper insertion point missing')
    helper_code = r'''    private static boolean hasLargePending(SharedPreferences prefs){JSONArray a=readArray(prefs,QUEUE_KEY);for(int i=0;i<a.length();i++){JSONObject e=a.optJSONObject(i);if(e!=null&&e.optBoolean("large",false))return true;}return false;}
    private static JSONObject localPhotoMap(SharedPreferences prefs){try{return new JSONObject(prefs.getString(LOCAL_PHOTO_MAP_KEY,"{}"));}catch(Exception e){return new JSONObject();}}
    private static String ensureLocalPhotoId(SharedPreferences prefs,File photo)throws Exception{JSONObject map=localPhotoMap(prefs);JSONObject row=map.optJSONObject(photo.getName());if(row==null){row=new JSONObject();row.put("windowsId","document_"+UUID.randomUUID());map.put(photo.getName(),row);prefs.edit().putString(LOCAL_PHOTO_MAP_KEY,map.toString()).apply();}return row.optString("windowsId");}
    private static void markAllLocalPhotoFingerprints(SharedPreferences prefs,File[] photos){try{JSONObject map=localPhotoMap(prefs);if(photos!=null)for(File photo:photos){if(photo==null||!photo.isFile())continue;JSONObject row=map.optJSONObject(photo.getName());if(row==null){row=new JSONObject();row.put("windowsId","document_"+UUID.randomUUID());map.put(photo.getName(),row);}row.put("fingerprint",photo.length()+":"+photo.lastModified());row.put("updatedAt",Instant.now().toString());}prefs.edit().putString(LOCAL_PHOTO_MAP_KEY,map.toString()).apply();}catch(Exception ignored){}}
    private static File[] localPhotoFiles(Context context){File dir=new File(context.getFilesDir(),"dossier_documents");File[] files=dir.listFiles((d,n)->n.startsWith("referto_foto_")&&n.endsWith(".jpg"));return files==null?new File[0]:files;}
    private static boolean hasPendingOrRawDocument(SharedPreferences prefs,String id){if(id==null||id.isEmpty())return false;if(rawEntity(prefs,"documents",id)!=null)return true;return hasPendingFor(prefs,"documents",id);}
    private static void upsertCloudDocIndex(JSONArray docs,JSONObject entity)throws Exception{String id=entity.optString("id","");JSONObject target=null;for(int i=0;i<docs.length();i++){JSONObject d=docs.optJSONObject(i);if(d!=null&&id.equals(d.optString("windows_id"))){target=d;break;}}if(target==null){target=new JSONObject();target.put("windows_id",id);docs.put(target);}copyDocMeta(entity,target);}

'''
    s = s.replace(helper_marker, helper_code + helper_marker, 1)

    # Keep a little more document metadata when converting a Windows snapshot/index.
    s = s.replace('String[]keys={"title","originalName","mimeType","clinicalDate","issueDate","addedAt","updatedAt","category","notes"};',
                  'String[]keys={"title","originalName","mimeType","size","clinicalDate","issueDate","addedAt","updatedAt","category","notes"};')

    CLOUD.write_text(s, encoding='utf-8')


patch_main()
patch_cloud()
print('Android R12 family/cloud/offline patch applied successfully')
