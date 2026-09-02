from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'
CRYPTO = BASE / 'R12Crypto.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R13 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    s = replace_once(
        s,
        '    private boolean pendingEditorNewCapture = false;\n',
        '    private boolean pendingEditorNewCapture = false;\n'
        '    private String pendingCapturePurpose = "document";\n'
        '    private boolean pendingAgendaEditorImport = false;\n',
        'camera purpose state'
    )

    # Import appointment must offer a real choice instead of always opening the file picker.
    start = s.find('    private void chooseAgendaImport() {')
    end = s.find('    private String extractAgendaText(Uri uri) throws Exception {', start)
    if start < 0 or end < 0:
        raise SystemExit('R13 patch failed: Agenda import block not found')
    agenda_import = r'''    private void chooseAgendaImport() {
        String[] choices = {"PDF / file", "Scatta foto", "Scansiona documento"};
        new AlertDialog.Builder(this)
                .setTitle("Importa prenotazione")
                .setItems(choices, (d, which) -> {
                    if (which == 0) chooseAgendaImportFile();
                    else if (which == 1) requestAgendaCamera("agenda_photo");
                    else requestAgendaCamera("agenda_scan");
                })
                .setNegativeButton("Annulla", null)
                .show();
    }

    private void chooseAgendaImportFile() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/pdf", "image/jpeg", "image/png", "image/webp"});
        startActivityForResult(i, IMPORT_AGENDA_DOCUMENT);
    }

    private void requestAgendaCamera(String mode) {
        pendingCapturePurpose = mode;
        if (!getPackageManager().hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)) {
            Toast.makeText(this, "Fotocamera non disponibile su questo dispositivo", Toast.LENGTH_LONG).show();
            pendingCapturePurpose = "document";
            return;
        }
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION);
        } else {
            launchPrivateCamera();
        }
    }

    private void importAgendaDocument(Uri uri) {
        if (uri == null) return;
        Toast.makeText(this, "Lettura della prenotazione in corso…", Toast.LENGTH_SHORT).show();
        dataExecutor.execute(() -> {
            try {
                String mime = getContentResolver().getType(uri);
                if (mime == null || mime.trim().isEmpty()) mime = "application/octet-stream";
                File privateCopy = copyAgendaOriginalToPrivate(uri, mime);
                Uri privateUri = privateDocumentUri(privateCopy);
                parseAgendaPrivateUri(privateUri, mime);
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(this, "Non sono riuscito a leggere automaticamente la prenotazione. Il file non è stato modificato.", Toast.LENGTH_LONG).show());
            }
        });
    }

    private void importAgendaPrivateFile(File file) {
        if (file == null || !file.isFile()) return;
        Toast.makeText(this, "Lettura della prenotazione in corso…", Toast.LENGTH_SHORT).show();
        final Uri uri = privateDocumentUri(file);
        final String mime = file.getName().toLowerCase(Locale.ITALY).endsWith(".pdf") ? "application/pdf" : "image/jpeg";
        dataExecutor.execute(() -> {
            try { parseAgendaPrivateUri(uri, mime); }
            catch (Exception e) { runOnUiThread(() -> Toast.makeText(this, "Non sono riuscito a leggere automaticamente la prenotazione.", Toast.LENGTH_LONG).show()); }
        });
    }

    private void parseAgendaPrivateUri(Uri uri, String mime) throws Exception {
        String raw = extractAgendaText(uri);
        if (raw == null || raw.trim().isEmpty()) throw new Exception("no text");
        JSONObject parsed = parseAgendaText(raw);
        parsed.put("source_uri", uri.toString());
        parsed.put("source_mime", mime == null ? "application/octet-stream" : mime);
        parsed.put("imported", true);
        final JSONObject ready = parsed;
        runOnUiThread(() -> showAgendaDialog(ready));
    }

    private File copyAgendaOriginalToPrivate(Uri uri, String mime) throws Exception {
        String ext = ".bin";
        String lower = String.valueOf(mime).toLowerCase(Locale.ITALY);
        if (lower.contains("pdf")) ext = ".pdf";
        else if (lower.contains("png")) ext = ".png";
        else if (lower.contains("webp")) ext = ".webp";
        else if (lower.contains("jpeg") || lower.contains("jpg") || lower.startsWith("image/")) ext = ".jpg";
        File target = new File(privateDocumentsDir(), "prenotazione_importata_" + System.currentTimeMillis() + ext);
        try (InputStream in = getContentResolver().openInputStream(uri); OutputStream out = new FileOutputStream(target)) {
            if (in == null) throw new Exception("File non leggibile");
            byte[] buffer = new byte[65536]; int n;
            while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
            out.flush();
        }
        if (!target.isFile() || target.length() == 0) { target.delete(); throw new Exception("File vuoto"); }
        return target;
    }

    private Uri privateDocumentUri(File file) {
        return new Uri.Builder().scheme("content").authority(getPackageName() + ".archiveprovider")
                .appendPath("document").appendPath(file.getName()).build();
    }

    private File saveAgendaCameraOriginal(File temp) throws Exception {
        File target = new File(privateDocumentsDir(), "referto_foto_" + System.currentTimeMillis() + ".jpg");
        try (InputStream in = new FileInputStream(temp); OutputStream out = new FileOutputStream(target)) {
            byte[] buffer = new byte[65536]; int n;
            while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
            out.flush();
        }
        if (!target.isFile() || target.length() == 0) { target.delete(); throw new Exception("Foto non salvata"); }
        temp.delete();
        return target;
    }

'''
    s = s[:start] + agenda_import + s[end:]

    # Normal document capture explicitly owns the generic camera purpose.
    s = replace_once(
        s,
        '    private void requestCamera() {\n        if (!getPackageManager().hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)) {',
        '    private void requestCamera() {\n        pendingCapturePurpose = "document";\n        if (!getPackageManager().hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)) {',
        'document camera purpose'
    )

    # Camera result now routes normal documents, appointment photos and appointment scans separately.
    cstart = s.find('        if (requestCode == CAMERA_CAPTURE) {')
    cend = s.find('        if (requestCode == EDIT_DOCUMENT) {', cstart)
    if cstart < 0 or cend < 0:
        raise SystemExit('R13 patch failed: camera result block not found')
    camera_result = r'''        if (requestCode == CAMERA_CAPTURE) {
            File temp = pendingCapture;
            pendingCapture = null;
            String purpose = pendingCapturePurpose;
            pendingCapturePurpose = "document";
            if (resultCode != RESULT_OK || temp == null || !temp.exists() || temp.length() == 0) {
                if (temp != null) temp.delete();
                cleanCameraTemp();
                Toast.makeText(this, "Acquisizione annullata", Toast.LENGTH_SHORT).show();
                return;
            }
            if ("agenda_photo".equals(purpose)) {
                try {
                    File saved = saveAgendaCameraOriginal(temp);
                    R12CloudManager.queueLocalPhotos(this, prefs, privatePhotos());
                    if ("Documenti".equals(currentSection)) refreshDocumentState();
                    importAgendaPrivateFile(saved);
                } catch (Exception e) {
                    temp.delete();
                    Toast.makeText(this, "Salvataggio della fotografia non riuscito", Toast.LENGTH_LONG).show();
                }
                cleanCameraTemp();
                return;
            }
            if ("agenda_scan".equals(purpose)) pendingAgendaEditorImport = true;
            launchEditor(temp, true);
            return;
        }

'''
    s = s[:cstart] + camera_result + s[cend:]

    estart = s.find('        if (requestCode == EDIT_DOCUMENT) {')
    eend = s.find('    }\n\n    private void launchEditor(File source, boolean newCapture) {', estart)
    if estart < 0 or eend < 0:
        raise SystemExit('R13 patch failed: editor result block not found')
    editor_result = r'''        if (requestCode == EDIT_DOCUMENT) {
            cleanCameraTemp();
            if ("Documenti".equals(currentSection)) refreshDocumentState();
            if (resultCode == RESULT_OK) {
                logEvent(pendingEditorNewCapture ? "Nuovo documento fotografico salvato" : "Documento fotografico modificato");
                R12CloudManager.queueLocalPhotos(this, prefs, privatePhotos());
                Toast.makeText(this, "Documento salvato nel Dossier", Toast.LENGTH_SHORT).show();
                if (pendingAgendaEditorImport && data != null) {
                    String savedPath = data.getStringExtra("saved_path");
                    if (savedPath != null && !savedPath.trim().isEmpty()) importAgendaPrivateFile(new File(savedPath));
                }
            }
            pendingAgendaEditorImport = false;
            pendingEditorNewCapture = false;
            return;
        }
'''
    s = s[:estart] + editor_result + s[eend:]

    # Replace the document list so all actions are guaranteed to remain on one visible row.
    rstart = s.find('    private void refreshDocumentState() {')
    rend = s.find('    private void showPhoto(File photo) {', rstart)
    if rstart < 0 or rend < 0:
        raise SystemExit('R13 patch failed: document list block not found')
    document_list = r'''    private void refreshDocumentState() {
        if (savedValue != null) {
            String value = prefs.getString("test_value", "");
            savedValue.setText(value.isEmpty() ? "Nessun dato di prova salvato" : "Dato conservato: " + value);
            if (testField != null && !testField.hasFocus()) testField.setText(value);
        }

        File[] photos = privatePhotos();
        if (photos == null) photos = new File[0];
        Arrays.sort(photos, Comparator.comparingLong(File::lastModified).reversed());
        if (photoCount != null) photoCount.setText("Foto private presenti nel Dossier: " + photos.length);
        if (photoList == null) return;
        photoList.removeAllViews();

        if (photos.length == 0) {
            photoList.addView(text("Nessuna fotografia presente.", 13, MUTED, false));
            return;
        }

        SimpleDateFormat fmt = new SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.ITALY);
        for (int i = 0; i < photos.length; i++) {
            File photo = photos[i];
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setPadding(dp(8), dp(8), dp(8), dp(8));
            row.setBackground(roundRect(Color.rgb(250, 252, 251), BORDER, 10));

            LinearLayout info = new LinearLayout(this);
            info.setOrientation(LinearLayout.HORIZONTAL);
            info.setGravity(Gravity.CENTER_VERTICAL);

            ImageView thumb = new ImageView(this);
            thumb.setScaleType(ImageView.ScaleType.CENTER_CROP);
            Bitmap bitmap = decodeScaledOriented(photo, 420, 420);
            if (bitmap != null) thumb.setImageBitmap(bitmap);
            info.addView(thumb, new LinearLayout.LayoutParams(dp(96), dp(96)));

            LinearLayout meta = new LinearLayout(this);
            meta.setOrientation(LinearLayout.VERTICAL);
            meta.setPadding(dp(12), 0, 0, 0);
            meta.addView(text("Documento fotografico " + (i + 1), 14, TEXT, true));
            meta.addView(text(fmt.format(new Date(photo.lastModified())), 12, MUTED, false));
            info.addView(meta, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            thumb.setOnClickListener(v -> showPhoto(photo));
            row.addView(info);

            LinearLayout actions = new LinearLayout(this);
            actions.setOrientation(LinearLayout.HORIZONTAL);
            actions.setPadding(0, dp(8), 0, 0);
            Button open = documentActionButton("Apri");
            open.setOnClickListener(v -> showPhoto(photo));
            actions.addView(open, new LinearLayout.LayoutParams(0, dp(42), 1f));
            Button edit = documentActionButton("Modifica");
            LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(0, dp(42), 1f); ep.setMargins(dp(6), 0, 0, 0);
            edit.setOnClickListener(v -> launchEditor(photo, false));
            actions.addView(edit, ep);
            Button del = documentActionButton("Elimina");
            LinearLayout.LayoutParams dpv = new LinearLayout.LayoutParams(0, dp(42), 1f); dpv.setMargins(dp(6), 0, 0, 0);
            del.setOnClickListener(v -> confirmDeletePrivateDocument(photo));
            actions.addView(del, dpv);
            row.addView(actions);

            photoList.addView(row, matchWrapBottom(8));
        }
    }

    private Button documentActionButton(String label) {
        Button b = compactButton(label);
        b.setMinWidth(0);
        b.setMinimumWidth(0);
        b.setMinHeight(0);
        b.setMinimumHeight(0);
        b.setSingleLine(true);
        b.setTextSize(11);
        b.setPadding(dp(4), 0, dp(4), 0);
        return b;
    }

    private void confirmDeletePrivateDocument(File photo) {
        if (photo == null) return;
        new AlertDialog.Builder(this)
                .setTitle("Eliminare il documento?")
                .setMessage("Il documento verrà rimosso dal Dossier locale. Se è già sincronizzato, l’eliminazione verrà propagata agli altri dispositivi alla prossima sincronizzazione.")
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Elimina", (d, w) -> {
                    String name = photo.getName();
                    if (!photo.delete()) {
                        Toast.makeText(this, "Non sono riuscito a eliminare il documento", Toast.LENGTH_LONG).show();
                        return;
                    }
                    R12CloudManager.queueLocalPhotoDelete(this, prefs, name);
                    logEvent("Documento fotografico eliminato");
                    refreshDocumentState();
                    Toast.makeText(this, "Documento eliminato", Toast.LENGTH_SHORT).show();
                })
                .show();
    }

'''
    s = s[:rstart] + document_list + s[rend:]

    for old, new in {
        'Android R12 TEST': 'Android R13 TEST',
        'Aiuto R12': 'Aiuto R13',
        'R12: struttura presente': 'R13: struttura presente',
        'R12 mantiene lo stesso pacchetto Android': 'R13 mantiene lo stesso pacchetto Android',
        'Installala sopra la R11': 'Installala sopra la R12'
    }.items():
        s = s.replace(old, new)

    MAIN.write_text(s, encoding='utf-8')


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    old_initial = '''            Button family = button(activity, "Collega a un Dossier familiare esistente");\n            family.setOnClickListener(v -> showFamilyConnect(activity, prefs));\n            card.addView(family, top(12));\n            Button standalone = button(activity, "Crea Dossier su MEGA senza PC");'''
    new_initial = '''            Button existing = button(activity, "Collega questo dispositivo al mio account esistente");\n            existing.setOnClickListener(v -> showFamilyConnect(activity, prefs, true));\n            card.addView(existing, top(12));\n            Button family = button(activity, "Collega un nuovo utente familiare");\n            family.setOnClickListener(v -> showFamilyConnect(activity, prefs, false));\n            card.addView(family, top(8));\n            Button standalone = button(activity, "Crea Dossier su MEGA senza PC");'''
    s = replace_once(s, old_initial, new_initial, 'existing account cloud button')

    s = replace_once(
        s,
        '    private static void showFamilyConnect(Activity activity, SharedPreferences prefs) {',
        '    private static void showFamilyConnect(Activity activity, SharedPreferences prefs, boolean existingAccount) {',
        'family connect signature'
    )
    s = replace_once(
        s,
        '                .setMessage("Inserisci il codice e la password provvisoria generati dall’amministratore del Dossier Windows.")',
        '                .setMessage(existingAccount ? "Sul PC Windows genera un accesso provvisorio per il tuo stesso profilo. Inserisci qui codice e password provvisoria: dopo il controllo userai le credenziali del tuo account già esistente, senza crearne uno nuovo." : "Inserisci il codice e la password provvisoria generati dall’amministratore del Dossier Windows.")',
        'existing account family message'
    )
    s = replace_once(
        s,
        '                    JSONObject payload = R12Crypto.openFamilyPackage(clean(code), clean(temporaryPassword));\n                    activity.runOnUiThread(() -> chooseInitialStorage(activity, prefs, payload));',
        '                    JSONObject payload = R12Crypto.openFamilyPackage(clean(code), clean(temporaryPassword));\n                    payload.put("existingAccountMode", existingAccount);\n                    activity.runOnUiThread(() -> chooseInitialStorage(activity, prefs, payload));',
        'existing account payload flag'
    )

    s = replace_once(
        s,
        '                if (free >= required) b.setPositiveButton("Continua", (d, w) -> showAccountSetup(activity, prefs, payload, cfg, choice, snap, null));',
        '                if (free >= required) b.setPositiveButton("Continua", (d, w) -> { if (payload.optBoolean("existingAccountMode", false)) showExistingAccountLogin(activity, prefs, payload, cfg, choice, snap); else showAccountSetup(activity, prefs, payload, cfg, choice, snap, null); });',
        'preflight existing account route'
    )

    insert = s.find('    private static void showStandaloneMega(Activity activity, SharedPreferences prefs) {')
    if insert < 0:
        raise SystemExit('R13 patch failed: standalone insertion point not found')
    existing_code = r'''    private static void showExistingAccountLogin(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap) {
        LinearLayout form = dialogForm(activity);
        EditText username = field(activity, "Nome utente già esistente", "");
        EditText password = field(activity, "Password del tuo account", "");
        password.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        form.addView(username); form.addView(password);
        new AlertDialog.Builder(activity)
                .setTitle("Account già esistente")
                .setMessage("Queste credenziali vengono verificate localmente contro l’account già presente nel Dossier cifrato. Non viene creato un secondo utente.")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Verifica account", (d, w) -> {
                    String user = clean(username), pass = clean(password);
                    if (user.isEmpty() || pass.isEmpty()) { Toast.makeText(activity, "Inserisci utente e password", Toast.LENGTH_LONG).show(); return; }
                    runProgress(activity, "Verifica account esistente", () -> prepareExistingAccount(activity, prefs, payload, cfg, choice, snap, user, pass));
                }).show();
    }

    private static void prepareExistingAccount(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, String username, String password) throws Exception {
        JSONObject cloud = payload.getJSONObject("cloud");
        File root = ensureRoot(choice.root);
        if (snap == null) snap = latestSnapshot(activity, cfg);
        if (snap == null) throw new Exception("Snapshot familiare non disponibile.");
        if (freeBytes(root) < requiredBytes(snap.size)) throw new Exception("Lo spazio disponibile non è più sufficiente per il Dossier.");
        File partial = new File(root, "current_snapshot.dsl5.part");
        if (partial.exists()) partial.delete();
        R12Rclone.copyFromRemote(activity, cloudRoot(cfg) + "/snapshots/" + snap.name, partial);
        if (snap.size > 0 && partial.length() != snap.size) { partial.delete(); throw new Exception("Il download del Dossier non ha la dimensione attesa."); }
        byte[] recovery = R12Crypto.unb64Url(cloud.getString("recoveryKey"));
        JSONObject account = findExistingAccount(partial, recovery, username);
        if (account == null || !account.optBoolean("active", true)) { partial.delete(); throw new Exception("Account non trovato o non attivo nel Dossier."); }
        if (!R12Crypto.verifyAccountPassword(account, password)) { partial.delete(); throw new Exception("Credenziali dell’account non valide."); }
        if (!account.optBoolean("mfaEnabled", false)) { partial.delete(); throw new Exception("Questo account non ha ancora un TOTP personale configurato. Configuralo prima dalla versione Windows."); }
        String envelope = account.optString("mfaSecretEnvelope", "");
        if (envelope.isEmpty()) { partial.delete(); throw new Exception("Il TOTP di questo account non è ancora trasferibile tra dispositivi. Accedi una volta dalla versione Windows aggiornata e riprova."); }
        String secret = R12Crypto.portableMfaUnprotect(envelope, password);
        final SnapshotInfo readySnap = snap;
        activity.runOnUiThread(() -> showExistingTotpVerification(activity, prefs, payload, cfg, choice, readySnap, account, secret, partial));
    }

    private static JSONObject findExistingAccount(File snapshot, byte[] recovery, String username) throws Exception {
        String wanted = R12Crypto.normalizeUsername(username);
        try (InputStream decrypted = R12Crypto.openDsl5File(snapshot, recovery); ZipInputStream zip = new ZipInputStream(decrypted)) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (!entry.isDirectory() && "sicurezza/archivio_credenziali.json".equals(entry.getName())) {
                    JSONObject bundle = new JSONObject(new String(readAll(zip), StandardCharsets.UTF_8));
                    JSONObject store = bundle.optJSONObject("usersStore");
                    JSONArray users = store == null ? null : store.optJSONArray("users");
                    if (users != null) for (int i = 0; i < users.length(); i++) {
                        JSONObject user = users.optJSONObject(i); if (user == null) continue;
                        String key = R12Crypto.normalizeUsername(user.optString("usernameKey", user.optString("username", "")));
                        if (wanted.equals(key)) return new JSONObject(user.toString());
                    }
                    return null;
                }
                while (zip.read(new byte[65536]) >= 0) {}
                zip.closeEntry();
            }
        }
        throw new Exception("Archivio credenziali del Dossier non disponibile nello snapshot.");
    }

    private static void showExistingTotpVerification(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account, String secret, File partial) {
        String username = account.optString("username", "Account");
        String issuer = "Dossier Sanitario Locale";
        String uri;
        try { uri = "otpauth://totp/" + URLEncoder.encode(issuer, "UTF-8") + ":" + URLEncoder.encode(username, "UTF-8") + "?secret=" + secret + "&issuer=" + URLEncoder.encode(issuer, "UTF-8") + "&algorithm=SHA1&digits=6&period=30"; }
        catch (Exception e) { uri = "otpauth://totp/Dossier?secret=" + secret; }
        final String otpUri = uri;
        LinearLayout box = dialogForm(activity);
        box.addView(body(activity, "Account riconosciuto: " + username + ". Se il tuo Authenticator contiene già questo account, usa direttamente il codice attuale. Altrimenti puoi aggiungerlo su questo telefono senza fotografare il QR."));
        Button openAuth = button(activity, "Apri nell’app Authenticator");
        openAuth.setOnClickListener(v -> { try { activity.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(otpUri))); } catch (ActivityNotFoundException e) { Toast.makeText(activity, "Nessuna app Authenticator ha accettato il collegamento. Usa la chiave manuale.", Toast.LENGTH_LONG).show(); } });
        box.addView(openAuth, top(8));
        EditText manual = field(activity, "Chiave manuale", groupSecret(secret)); manual.setFocusable(false); manual.setLongClickable(true); box.addView(manual);
        try { Bitmap qr = qrBitmap(otpUri, 520); ImageView image = new ImageView(activity); image.setImageBitmap(qr); image.setAdjustViewBounds(true); box.addView(image, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(activity, 260))); } catch (Exception ignored) {}
        EditText otp = field(activity, "Codice a 6 cifre", ""); otp.setInputType(android.text.InputType.TYPE_CLASS_NUMBER); box.addView(otp);
        new AlertDialog.Builder(activity).setTitle("Conferma TOTP personale").setView(box)
                .setNegativeButton("Annulla", (d, w) -> partial.delete())
                .setPositiveButton("Verifica e collega", (d, w) -> {
                    if (!R12Crypto.verifyTotp(secret, clean(otp))) { Toast.makeText(activity, "Il codice TOTP non è valido", Toast.LENGTH_LONG).show(); return; }
                    runProgress(activity, "Collegamento dispositivo", () -> completeExistingFamilyConnection(activity, prefs, payload, cfg, choice, snap, account, partial));
                }).show();
    }

    private static void completeExistingFamilyConnection(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account, File partial) throws Exception {
        JSONObject cloud = payload.getJSONObject("cloud");
        cfg.put("origin", "family-existing-account");
        cfg.put("provider", cloud.optString("provider", "mega"));
        cfg.put("archiveId", cloud.getString("archiveId"));
        cfg.put("displayName", cloud.optString("displayName", "Archivio familiare"));
        cfg.put("basePath", R12Rclone.cleanPath(cloud.optString("basePath", "Dossier Sanitario Locale")));
        String linked = account.optString("linkedProfileId", "");
        if (linked.isEmpty() && payload.optJSONObject("membershipTemplate") != null) linked = payload.optJSONObject("membershipTemplate").optString("linkedProfileId", "");
        cfg.put("linkedProfileId", linked);
        cfg.put("accessLevel", "administrator".equals(account.optString("role")) ? "administrator" : account.optString("accessLevel", "viewer"));
        cfg.put("profileName", payload.optString("profileName", account.optString("displayName", "")));
        cfg.put("associationStatus", "active");
        cfg.put("deviceId", deviceId(prefs));
        cfg.put("storagePath", choice.root.getAbsolutePath()); cfg.put("storageLabel", choice.label);
        cfg.put("recoveryKeyProtected", R12Crypto.protectSecret(context, cloud.getString("recoveryKey")));
        prefs.edit().putString(ACCOUNT_KEY, account.toString()).remove(PENDING_COMPLETION_KEY).apply();
        byte[] recovery = R12Crypto.unb64Url(cloud.getString("recoveryKey"));
        importSnapshot(context, prefs, cfg, partial, recovery);
        File root = ensureRoot(choice.root); File finalFile = new File(root, "current_snapshot.dsl5"); replaceVerified(partial, finalFile);
        cfg.put("lastSnapshotName", snap.name); cfg.put("lastSyncAt", Instant.now().toString()); saveConfig(prefs, cfg);
        pullRemoteChanges(context, prefs, cfg, true);
        queueLocalPhotos(context, prefs, localPhotoFiles(context));
        schedulePeriodic(context, prefs);
    }

'''
    s = s[:insert] + existing_code + s[insert:]

    # Synchronized local-photo deletion and cloud-document deletion.
    queue_insert = s.find('    public static void queueAgendaPut(Context context, SharedPreferences prefs, JSONObject nativeItem) {')
    if queue_insert < 0:
        raise SystemExit('R13 patch failed: document delete insertion point not found')
    delete_code = r'''    public static void queueLocalPhotoDelete(Context context, SharedPreferences prefs, String fileName) {
        try {
            JSONObject map = localPhotoMap(prefs); JSONObject row = map.optJSONObject(String.valueOf(fileName));
            if (row == null) return; String id = row.optString("windowsId", "");
            if (!id.isEmpty() && configured(prefs)) queueDelete(context, prefs, loadConfig(prefs), "documents", id);
            if (!id.isEmpty()) markDocumentDeleted(prefs, id);
            map.remove(String.valueOf(fileName)); prefs.edit().putString(LOCAL_PHOTO_MAP_KEY, map.toString()).apply();
        } catch (Exception ignored) {}
    }

    private static void confirmDeleteCloudDocument(Activity activity, SharedPreferences prefs, JSONObject doc) {
        new AlertDialog.Builder(activity).setTitle("Eliminare il documento?")
                .setMessage("Il documento verrà rimosso dal Dossier e l’eliminazione verrà sincronizzata con gli altri dispositivi.")
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Elimina", (d, w) -> {
                    try {
                        String id = doc.optString("windows_id", ""); if (id.isEmpty()) return;
                        if (configured(prefs)) queueDelete(activity, prefs, loadConfig(prefs), "documents", id);
                        doc.put("deleted", true); markDocumentDeleted(prefs, id);
                        String delta = doc.optString("deltaFile", ""); if (!delta.isEmpty()) new File(delta).delete();
                        Toast.makeText(activity, "Documento eliminato", Toast.LENGTH_SHORT).show();
                    } catch (Exception e) { Toast.makeText(activity, "Eliminazione non riuscita", Toast.LENGTH_LONG).show(); }
                }).show();
    }

'''
    s = s[:queue_insert] + delete_code + s[queue_insert:]

    old_open = '''            Button open = button(activity, "Apri originale");\n            open.setOnClickListener(v -> openCloudDocument(activity, prefs, doc));\n            row.addView(open, top(5));'''
    new_open = '''            LinearLayout actions = new LinearLayout(activity); actions.setOrientation(LinearLayout.HORIZONTAL); actions.setPadding(0, dp(activity, 5), 0, 0);\n            Button open = button(activity, "Apri"); open.setMinWidth(0); open.setMinimumWidth(0); open.setSingleLine(true);\n            open.setOnClickListener(v -> openCloudDocument(activity, prefs, doc)); actions.addView(open, new LinearLayout.LayoutParams(0, dp(activity, 44), 1f));\n            Button del = button(activity, "Elimina"); del.setMinWidth(0); del.setMinimumWidth(0); del.setSingleLine(true);\n            LinearLayout.LayoutParams dpv = new LinearLayout.LayoutParams(0, dp(activity, 44), 1f); dpv.setMargins(dp(activity, 6), 0, 0, 0); del.setOnClickListener(v -> confirmDeleteCloudDocument(activity, prefs, doc)); actions.addView(del, dpv);\n            row.addView(actions);'''
    s = replace_once(s, old_open, new_open, 'cloud document actions')

    CLOUD.write_text(s, encoding='utf-8')


def patch_crypto():
    s = CRYPTO.read_text(encoding='utf-8')
    marker = '    public static String portableMfaEnvelope(String secret, String password) throws Exception {'
    if marker not in s:
        raise SystemExit('R13 patch failed: crypto insertion point not found')
    code = r'''    public static boolean verifyAccountPassword(JSONObject account, String password) {
        try {
            byte[] salt = unb64Url(account.getString("passwordSalt"));
            byte[] expected = unb64Url(account.getString("passwordHash"));
            int iterations = account.optInt("passwordIterations", PBKDF2_ITERATIONS);
            PBEKeySpec spec = new PBEKeySpec(String.valueOf(password).toCharArray(), salt, iterations, 256);
            byte[] actual;
            try { actual = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded(); }
            finally { spec.clearPassword(); }
            return MessageDigest.isEqual(expected, actual);
        } catch (Exception e) { return false; }
    }

    public static String portableMfaUnprotect(String value, String password) throws Exception {
        String packedValue = String.valueOf(value == null ? "" : value);
        if (!packedValue.startsWith("pwv1:")) throw new Exception("Segreto personale del secondo fattore non valido");
        byte[] packed = unb64Url(packedValue.substring(5));
        if (packed.length < 65) throw new Exception("Segreto personale del secondo fattore incompleto");
        byte[] salt = java.util.Arrays.copyOfRange(packed, 0, 16);
        byte[] nonce = java.util.Arrays.copyOfRange(packed, 16, 32);
        byte[] cipherText = java.util.Arrays.copyOfRange(packed, 32, packed.length - 32);
        byte[] tag = java.util.Arrays.copyOfRange(packed, packed.length - 32, packed.length);
        PBEKeySpec spec = new PBEKeySpec(String.valueOf(password).toCharArray(), salt, PBKDF2_ITERATIONS, 512);
        byte[] material;
        try { material = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded(); }
        finally { spec.clearPassword(); }
        byte[] encKey = java.util.Arrays.copyOfRange(material, 0, 32);
        byte[] macKey = java.util.Arrays.copyOfRange(material, 32, 64);
        Mac mac = Mac.getInstance("HmacSHA256"); mac.init(new SecretKeySpec(macKey, "HmacSHA256"));
        ByteArrayOutputStream signed = new ByteArrayOutputStream(); signed.write("Dossier-MFA-V1\0".getBytes(StandardCharsets.ISO_8859_1)); signed.write(salt); signed.write(nonce); signed.write(cipherText);
        byte[] expected = mac.doFinal(signed.toByteArray());
        if (!MessageDigest.isEqual(expected, tag)) throw new Exception("Password non valida per il secondo fattore");
        byte[] stream = mfaStream(encKey, nonce, cipherText.length); byte[] plain = new byte[cipherText.length];
        for (int i = 0; i < cipherText.length; i++) plain[i] = (byte)(cipherText[i] ^ stream[i]);
        return new String(plain, StandardCharsets.US_ASCII);
    }

'''
    s = s.replace(marker, code + marker, 1)
    CRYPTO.write_text(s, encoding='utf-8')


patch_main()
patch_cloud()
patch_crypto()
print('Android R13 patch applied successfully')
