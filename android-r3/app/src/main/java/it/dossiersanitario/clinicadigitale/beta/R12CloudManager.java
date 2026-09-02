package it.dossiersanitario.clinicadigitale.beta;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.ProgressDialog;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Environment;
import android.os.StatFs;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.ContextCompat;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

public final class R12CloudManager {
    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    private static final String CONFIG_KEY = "r12_cloud_config_json";
    private static final String ACCOUNT_KEY = "r12_account_json";
    private static final String PENDING_COMPLETION_KEY = "r12_pending_completion_json";
    private static final String QUEUE_KEY = "r12_sync_queue_json";
    private static final String CONFLICTS_KEY = "r12_sync_conflicts_json";
    private static final String RAW_KEY = "r12_raw_entities_json";
    private static final String DOCS_KEY = "r12_cloud_documents_json";
    private static final String DEVICE_KEY = "r12_device_id";
    private static final String POLICY_KEY = "r12_sync_policy";
    private static final String PREF_EXEMPTIONS = "android_exemptions_json";
    private static final String PREF_DOCTORS = "android_doctors_json";
    private static final String PREF_AGENDA = "android_agenda_json";
    private static final long MB = 1024L * 1024L;
    private static final String WORK_PERIODIC = "clinica_r12_cloud_periodic";
    private static final String WORK_IMMEDIATE = "clinica_r12_cloud_immediate";
    private static volatile boolean syncing = false;

    private R12CloudManager() {}

    public static boolean configured(SharedPreferences prefs) {
        return loadConfig(prefs).optString("archiveId", "").length() > 0;
    }

    public static void renderCloudPanel(Activity activity, LinearLayout content, SharedPreferences prefs) {
        JSONObject cfg = loadConfig(prefs);
        LinearLayout card = card(activity);
        card.addView(title(activity, "Dossier e sincronizzazione cloud"));
        if (cfg.optString("archiveId", "").isEmpty()) {
            card.addView(body(activity, "Collega l’app al Dossier familiare esistente senza scaricare manualmente un backup. Il cloud è il canale di sincronizzazione; il Dossier resta disponibile localmente anche offline."));
            Button family = button(activity, "Collega a un Dossier familiare esistente");
            family.setOnClickListener(v -> showFamilyConnect(activity, prefs));
            card.addView(family, top(12));
            Button standalone = button(activity, "Crea Dossier su MEGA senza PC");
            standalone.setOnClickListener(v -> showStandaloneMega(activity, prefs));
            card.addView(standalone, top(8));
        } else {
            String storage = cfg.optString("storageLabel", "Memoria interna");
            boolean storageOk = archiveRoot(activity, cfg, false) != null;
            String state = cfg.optString("associationStatus", "active");
            card.addView(kv(activity, "Archivio", cfg.optString("displayName", "Dossier familiare")));
            card.addView(kv(activity, "Profilo collegato", cfg.optString("profileName", cfg.optString("linkedProfileId", ""))));
            card.addView(kv(activity, "Memoria locale", storage));
            card.addView(kv(activity, "Ultima sincronizzazione", cfg.optString("lastSyncAt", "Mai")));
            card.addView(kv(activity, "Modifiche in attesa", String.valueOf(readArray(prefs, QUEUE_KEY).length())));
            card.addView(kv(activity, "Conflitti da verificare", String.valueOf(readArray(prefs, CONFLICTS_KEY).length())));
            if (!storageOk) card.addView(warning(activity, "Archivio Dossier non disponibile. Reinserisci la memoria selezionata. Clinica Digitale non creerà un archivio vuoto in un’altra posizione."));
            if ("pending_admin".equals(state)) card.addView(warning(activity, "Associazione inviata all’amministratore. Il completamento viene confermato automaticamente dal Dossier Windows alla prossima sincronizzazione dell’amministratore."));

            Button sync = button(activity, "Sincronizza adesso");
            sync.setEnabled(storageOk);
            sync.setOnClickListener(v -> syncInteractive(activity, prefs));
            card.addView(sync, top(12));

            TextView policyLabel = body(activity, "Sincronizzazione automatica");
            policyLabel.setPadding(0, dp(activity, 12), 0, dp(activity, 4));
            card.addView(policyLabel);
            Spinner policy = new Spinner(activity);
            String[] labels = {"Automatica intelligente · consigliata", "Solo Wi-Fi", "Wi-Fi e rete mobile", "Manuale"};
            String[] values = {"smart", "wifi", "any", "manual"};
            policy.setAdapter(new ArrayAdapter<>(activity, android.R.layout.simple_spinner_dropdown_item, labels));
            String current = prefs.getString(POLICY_KEY, "smart");
            int selected = 0;
            for (int i = 0; i < values.length; i++) if (values[i].equals(current)) selected = i;
            policy.setSelection(selected);
            policy.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
                @Override public void onItemSelected(android.widget.AdapterView<?> parent, View view, int position, long id) {
                    String next = values[Math.max(0, Math.min(values.length - 1, position))];
                    if (!next.equals(prefs.getString(POLICY_KEY, "smart"))) {
                        prefs.edit().putString(POLICY_KEY, next).apply();
                        schedulePeriodic(activity, prefs);
                    }
                }
                @Override public void onNothingSelected(android.widget.AdapterView<?> parent) {}
            });
            card.addView(policy, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

            Button storageButton = button(activity, "Cambia memoria del Dossier");
            storageButton.setOnClickListener(v -> chooseStorageMove(activity, prefs));
            card.addView(storageButton, top(8));
            Button conflicts = button(activity, "Verifica conflitti");
            conflicts.setOnClickListener(v -> showConflicts(activity, prefs));
            card.addView(conflicts, top(8));
        }
        card.addView(note(activity, "Offline: dopo la prima sincronizzazione il Dossier resta consultabile e modificabile senza Internet. Le modifiche vengono accodate e inviate quando la connessione torna disponibile."));
        card.addView(note(activity, "Memoria esterna: il Dossier resta cifrato. L’accesso a documenti e contenuti di archivio può risultare più lento in funzione delle prestazioni della scheda. Se la memoria viene rimossa o diventa illeggibile, i dati su di essa restano indisponibili fino al ripristino."));
        content.addView(card, bottom(14));
    }

    public static void appendCloudDocuments(Activity activity, LinearLayout content, SharedPreferences prefs) {
        if (!configured(prefs)) return;
        JSONArray docs = readArray(prefs, DOCS_KEY);
        if (docs.length() == 0) return;
        LinearLayout card = card(activity);
        card.addView(title(activity, "Documenti del Dossier sincronizzato"));
        card.addView(body(activity, "Gli originali restano nel Dossier cifrato locale. L’apertura può richiedere qualche secondo, soprattutto se l’archivio si trova su scheda SD."));
        int shown = Math.min(docs.length(), 80);
        for (int i = 0; i < shown; i++) {
            JSONObject doc = docs.optJSONObject(i);
            if (doc == null || doc.optBoolean("deleted", false)) continue;
            LinearLayout row = new LinearLayout(activity);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setPadding(0, dp(activity, 9), 0, dp(activity, 9));
            TextView name = body(activity, doc.optString("title", doc.optString("originalName", "Documento")));
            name.setTextColor(Color.rgb(28, 47, 43));
            row.addView(name);
            String date = doc.optString("clinicalDate", doc.optString("issueDate", ""));
            if (!date.isEmpty()) row.addView(note(activity, date));
            Button open = button(activity, "Apri originale");
            open.setOnClickListener(v -> openCloudDocument(activity, prefs, doc));
            row.addView(open, top(5));
            card.addView(row);
        }
        content.addView(card, bottom(14));
    }

    private static void showFamilyConnect(Activity activity, SharedPreferences prefs) {
        LinearLayout form = dialogForm(activity);
        EditText code = field(activity, "Codice accesso provvisorio", "");
        code.setMinLines(4);
        code.setMaxLines(7);
        EditText temporaryPassword = field(activity, "Password provvisoria", "");
        temporaryPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        form.addView(code); form.addView(temporaryPassword);
        new AlertDialog.Builder(activity)
                .setTitle("Collega Dossier familiare")
                .setMessage("Inserisci il codice e la password provvisoria generati dall’amministratore del Dossier Windows.")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Verifica", (d, w) -> runProgress(activity, "Verifica accesso", () -> {
                    JSONObject payload = R12Crypto.openFamilyPackage(clean(code), clean(temporaryPassword));
                    activity.runOnUiThread(() -> chooseInitialStorage(activity, prefs, payload));
                }))
                .show();
    }

    private static void chooseInitialStorage(Activity activity, SharedPreferences prefs, JSONObject payload) {
        List<StorageChoice> choices = storageChoices(activity);
        String[] labels = new String[choices.size()];
        for (int i = 0; i < choices.size(); i++) labels[i] = choices.get(i).label + " · liberi " + formatBytes(choices.get(i).freeBytes);
        new AlertDialog.Builder(activity)
                .setTitle("Dove conservare il Dossier?")
                .setSingleChoiceItems(labels, 0, null)
                .setMessage("La memoria viene controllata prima di qualsiasi download. La scelta potrà essere cambiata successivamente con copia, verifica e solo dopo rimozione della vecchia copia.")
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Continua", (dialog, which) -> {
                    AlertDialog ad = (AlertDialog) dialog;
                    int pos = ad.getListView().getCheckedItemPosition();
                    if (pos < 0) pos = 0;
                    StorageChoice choice = choices.get(pos);
                    preflightFamily(activity, prefs, payload, choice);
                }).show();
    }

    private static void preflightFamily(Activity activity, SharedPreferences prefs, JSONObject payload, StorageChoice choice) {
        runProgress(activity, "Controllo Dossier", () -> {
            JSONObject cloud = payload.getJSONObject("cloud");
            String remoteName = R12Rclone.importRemoteSection(activity, cloud.getString("remoteSection"));
            JSONObject cfg = new JSONObject();
            cfg.put("provider", cloud.optString("provider", "mega"));
            cfg.put("remoteName", remoteName);
            cfg.put("archiveId", cloud.getString("archiveId"));
            cfg.put("displayName", cloud.optString("displayName", "Archivio familiare"));
            cfg.put("basePath", R12Rclone.cleanPath(cloud.optString("basePath", "Dossier Sanitario Locale")));
            cfg.put("profileName", payload.optString("profileName", ""));
            cfg.put("linkedProfileId", payload.optJSONObject("membershipTemplate") == null ? "" : payload.optJSONObject("membershipTemplate").optString("linkedProfileId", ""));
            cfg.put("accessLevel", payload.optJSONObject("membershipTemplate") == null ? "viewer" : payload.optJSONObject("membershipTemplate").optString("accessLevel", "viewer"));
            verifyArchiveManifest(activity, cfg);
            SnapshotInfo snap = latestSnapshot(activity, cfg);
            if (snap == null) throw new Exception("Nessuna copia valida trovata nell’archivio familiare.");
            long required = requiredBytes(snap.size);
            long free = freeBytes(choice.root);
            activity.runOnUiThread(() -> {
                String message = "Dimensione Dossier: " + formatBytes(snap.size) + "\n" +
                        "Spazio richiesto con margine operativo: " + formatBytes(required) + "\n" +
                        "Spazio disponibile: " + formatBytes(free) + "\n\n" +
                        (free >= required ? "Lo spazio è sufficiente. Nessun dato verrà scaricato finché non confermi." : "Spazio insufficiente. La sincronizzazione non verrà avviata.");
                AlertDialog.Builder b = new AlertDialog.Builder(activity).setTitle("Controllo spazio").setMessage(message).setNegativeButton("Chiudi", null);
                if (free >= required) b.setPositiveButton("Continua", (d, w) -> showAccountSetup(activity, prefs, payload, cfg, choice, snap, null));
                b.show();
            });
        });
    }

    private static void showStandaloneMega(Activity activity, SharedPreferences prefs) {
        LinearLayout form = dialogForm(activity);
        EditText megaEmail = field(activity, "E-mail account MEGA", "");
        EditText megaPassword = field(activity, "Password MEGA", "");
        megaPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText archiveName = field(activity, "Nome archivio", "Dossier sanitario");
        EditText firstName = field(activity, "Nome del profilo sanitario", prefs.getString("profile_first_name", ""));
        EditText lastName = field(activity, "Cognome del profilo sanitario", prefs.getString("profile_last_name", ""));
        form.addView(megaEmail); form.addView(megaPassword); form.addView(archiveName); form.addView(firstName); form.addView(lastName);
        new AlertDialog.Builder(activity)
                .setTitle("Crea Dossier su MEGA")
                .setMessage("Usa questa modalità se non esiste ancora un Dossier Windows. Le credenziali MEGA restano nella configurazione privata del connettore e non vengono mostrate agli altri dispositivi che verranno associati in futuro.")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Continua", (d, w) -> {
                    if (!clean(megaEmail).contains("@") || clean(megaPassword).isEmpty() || clean(firstName).isEmpty()) {
                        Toast.makeText(activity, "Compila account MEGA e nome del profilo", Toast.LENGTH_LONG).show();
                        return;
                    }
                    JSONObject standalone = new JSONObject();
                    try {
                        standalone.put("megaEmail", clean(megaEmail));
                        standalone.put("megaPassword", clean(megaPassword));
                        standalone.put("archiveName", clean(archiveName));
                        standalone.put("firstName", clean(firstName));
                        standalone.put("lastName", clean(lastName));
                    } catch (Exception ignored) {}
                    chooseStandaloneStorage(activity, prefs, standalone);
                }).show();
    }

    private static void chooseStandaloneStorage(Activity activity, SharedPreferences prefs, JSONObject standalone) {
        List<StorageChoice> choices = storageChoices(activity);
        String[] labels = new String[choices.size()];
        for (int i = 0; i < choices.size(); i++) labels[i] = choices.get(i).label + " · liberi " + formatBytes(choices.get(i).freeBytes);
        new AlertDialog.Builder(activity).setTitle("Memoria del Dossier").setSingleChoiceItems(labels, 0, null)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Continua", (dialog, which) -> {
                    AlertDialog ad = (AlertDialog) dialog;
                    int pos = ad.getListView().getCheckedItemPosition(); if (pos < 0) pos = 0;
                    JSONObject cfg = new JSONObject();
                    try {
                        cfg.put("origin", "standalone");
                        cfg.put("provider", "mega");
                        cfg.put("displayName", standalone.optString("archiveName", "Dossier sanitario"));
                        cfg.put("profileName", (standalone.optString("firstName") + " " + standalone.optString("lastName")).trim());
                    } catch (Exception ignored) {}
                    showAccountSetup(activity, prefs, standalone, cfg, choices.get(pos), null, standalone);
                }).show();
    }

    private static void showAccountSetup(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject standalone) {
        LinearLayout form = dialogForm(activity);
        EditText displayName = field(activity, "Nome visualizzato", cfg.optString("profileName", ""));
        EditText email = field(activity, "E-mail personale", standalone == null ? "" : standalone.optString("megaEmail", ""));
        EditText username = field(activity, "Nome utente", "");
        EditText password = field(activity, "Password personale · minimo 10 caratteri", "");
        password.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText confirm = field(activity, "Conferma password", "");
        confirm.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        EditText recoveryQuestion = field(activity, "Domanda personale di recupero", "");
        EditText recoveryAnswer = field(activity, "Risposta personale", "");
        form.addView(displayName); form.addView(email); form.addView(username); form.addView(password); form.addView(confirm); form.addView(recoveryQuestion); form.addView(recoveryAnswer);
        new AlertDialog.Builder(activity).setTitle("Credenziali personali").setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Continua", (d, w) -> {
                    AccountDraft draft = new AccountDraft(clean(displayName), clean(email), clean(username), clean(password), clean(recoveryQuestion), clean(recoveryAnswer));
                    if (draft.displayName.isEmpty() || draft.username.isEmpty() || draft.password.length() < 10 || !draft.email.contains("@")) {
                        Toast.makeText(activity, "Controlla nome, e-mail, utente e password", Toast.LENGTH_LONG).show(); return;
                    }
                    if (!draft.password.equals(clean(confirm))) { Toast.makeText(activity, "Le password non coincidono", Toast.LENGTH_LONG).show(); return; }
                    if (draft.recoveryQuestion.length() < 5 || draft.recoveryAnswer.length() < 3) { Toast.makeText(activity, "Completa domanda e risposta di recupero", Toast.LENGTH_LONG).show(); return; }
                    showTotpSetup(activity, prefs, payload, cfg, choice, snap, standalone, draft);
                }).show();
    }

    private static void showTotpSetup(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject standalone, AccountDraft draft) {
        String secret = R12Crypto.newTotpSecret();
        String issuer = "Dossier Sanitario Locale";
        String uri;
        try {
            uri = "otpauth://totp/" + URLEncoder.encode(issuer, "UTF-8") + ":" + URLEncoder.encode(draft.username, "UTF-8") +
                    "?secret=" + secret + "&issuer=" + URLEncoder.encode(issuer, "UTF-8") + "&algorithm=SHA1&digits=6&period=30";
        } catch (Exception e) { uri = "otpauth://totp/Dossier?secret=" + secret; }
        final String otpUri = uri;

        LinearLayout box = dialogForm(activity);
        box.addView(body(activity, "Sul telefono non devi fotografare il QR visualizzato sullo stesso schermo. Puoi aprire direttamente un’app Authenticator compatibile oppure inserire la chiave manuale. Il QR resta disponibile se vuoi configurare il generatore da un secondo dispositivo."));
        Button openAuth = button(activity, "Apri nell’app Authenticator");
        openAuth.setOnClickListener(v -> {
            try { activity.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(otpUri))); }
            catch (ActivityNotFoundException e) { Toast.makeText(activity, "Nessuna app Authenticator ha accettato il collegamento. Usa la chiave manuale.", Toast.LENGTH_LONG).show(); }
        });
        box.addView(openAuth, top(8));
        EditText manual = field(activity, "Chiave manuale", groupSecret(secret));
        manual.setFocusable(false); manual.setLongClickable(true); box.addView(manual);
        try {
            Bitmap qr = qrBitmap(otpUri, 520);
            ImageView image = new ImageView(activity); image.setImageBitmap(qr); image.setAdjustViewBounds(true);
            box.addView(image, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(activity, 260)));
        } catch (Exception ignored) {}
        EditText otp = field(activity, "Codice a 6 cifre", "");
        otp.setInputType(android.text.InputType.TYPE_CLASS_NUMBER); box.addView(otp);
        new AlertDialog.Builder(activity).setTitle("Configura autenticazione TOTP").setView(box)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Verifica e collega", (d, w) -> {
                    if (!R12Crypto.verifyTotp(secret, clean(otp))) { Toast.makeText(activity, "Il codice TOTP non è valido", Toast.LENGTH_LONG).show(); return; }
                    String[] recoveryCodes = R12Crypto.recoveryCodes();
                    runProgress(activity, "Collegamento Dossier", () -> {
                        if (standalone == null) completeFamilyConnection(activity, prefs, payload, cfg, choice, snap, draft, secret, recoveryCodes);
                        else completeStandaloneConnection(activity, prefs, standalone, cfg, choice, draft, secret, recoveryCodes);
                        activity.runOnUiThread(() -> showRecoveryCodes(activity, recoveryCodes));
                    });
                }).show();
    }

    private static void completeFamilyConnection(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, AccountDraft draft, String secret, String[] recoveryCodes) throws Exception {
        JSONObject cloud = payload.getJSONObject("cloud");
        cfg.put("origin", "family");
        cfg.put("provider", cloud.optString("provider", "mega"));
        cfg.put("archiveId", cloud.getString("archiveId"));
        cfg.put("displayName", cloud.optString("displayName", "Archivio familiare"));
        cfg.put("basePath", R12Rclone.cleanPath(cloud.optString("basePath", "Dossier Sanitario Locale")));
        cfg.put("linkedProfileId", payload.optJSONObject("membershipTemplate") == null ? "" : payload.optJSONObject("membershipTemplate").optString("linkedProfileId", ""));
        cfg.put("accessLevel", payload.optJSONObject("membershipTemplate") == null ? "viewer" : payload.optJSONObject("membershipTemplate").optString("accessLevel", "viewer"));
        cfg.put("profileName", payload.optString("profileName", ""));
        cfg.put("activationId", payload.getString("activationId"));
        cfg.put("associationStatus", "pending_admin");
        cfg.put("deviceId", deviceId(prefs));
        cfg.put("storagePath", choice.root.getAbsolutePath());
        cfg.put("storageLabel", choice.label);
        cfg.put("recoveryKeyProtected", R12Crypto.protectSecret(context, cloud.getString("recoveryKey")));
        JSONObject account = buildAccount(draft, secret, recoveryCodes, false);
        prefs.edit().putString(ACCOUNT_KEY, account.toString()).apply();

        File root = ensureRoot(choice.root);
        if (snap == null) snap = latestSnapshot(context, cfg);
        if (snap == null) throw new Exception("Snapshot familiare non disponibile.");
        if (freeBytes(root) < requiredBytes(snap.size)) throw new Exception("Lo spazio disponibile non è più sufficiente per il Dossier.");
        File partial = new File(root, "current_snapshot.dsl5.part");
        if (partial.exists()) partial.delete();
        R12Rclone.copyFromRemote(context, cloudRoot(cfg) + "/snapshots/" + snap.name, partial);
        if (snap.size > 0 && partial.length() != snap.size) throw new Exception("Il download del Dossier non ha la dimensione attesa.");
        importSnapshot(context, prefs, cfg, partial, R12Crypto.unb64Url(cloud.getString("recoveryKey")));
        File finalFile = new File(root, "current_snapshot.dsl5");
        replaceVerified(partial, finalFile);
        cfg.put("lastSnapshotName", snap.name);
        cfg.put("lastSyncAt", Instant.now().toString());
        saveConfig(prefs, cfg);
        JSONObject pending = new JSONObject();
        pending.put("activationId", payload.getString("activationId"));
        pending.put("profileId", cfg.optString("linkedProfileId", ""));
        pending.put("account", account);
        prefs.edit().putString(PENDING_COMPLETION_KEY, pending.toString()).apply();
        publishPendingCompletion(context, prefs, cfg);
        pullRemoteChanges(context, prefs, cfg, true);
        schedulePeriodic(context, prefs);
    }

    private static void completeStandaloneConnection(Context context, SharedPreferences prefs, JSONObject standalone, JSONObject cfg, StorageChoice choice, AccountDraft draft, String secret, String[] recoveryCodes) throws Exception {
        String remoteName = R12Rclone.createMegaRemote(context, standalone.getString("megaEmail"), standalone.getString("megaPassword"));
        String archiveId = "archive_" + UUID.randomUUID();
        String profileId = "profile_" + UUID.randomUUID();
        byte[] recovery = R12Crypto.randomBytes(32);
        cfg.put("origin", "standalone"); cfg.put("provider", "mega"); cfg.put("remoteName", remoteName);
        cfg.put("archiveId", archiveId); cfg.put("basePath", "Dossier Sanitario Locale");
        cfg.put("displayName", standalone.optString("archiveName", "Dossier sanitario"));
        cfg.put("linkedProfileId", profileId); cfg.put("profileName", (standalone.optString("firstName") + " " + standalone.optString("lastName")).trim());
        cfg.put("accessLevel", "administrator"); cfg.put("associationStatus", "active"); cfg.put("deviceId", deviceId(prefs));
        cfg.put("storagePath", choice.root.getAbsolutePath()); cfg.put("storageLabel", choice.label);
        cfg.put("recoveryKeyProtected", R12Crypto.protectSecret(context, R12Crypto.b64Url(recovery)));
        JSONObject account = buildAccount(draft, secret, recoveryCodes, true);
        prefs.edit().putString(ACCOUNT_KEY, account.toString())
                .putString("profile_first_name", standalone.optString("firstName", ""))
                .putString("profile_last_name", standalone.optString("lastName", ""))
                .apply();
        String rootRemote = cloudRoot(cfg);
        R12Rclone.mkdir(context, rootRemote); R12Rclone.mkdir(context, rootRemote + "/snapshots"); R12Rclone.mkdir(context, rootRemote + "/changes"); R12Rclone.mkdir(context, rootRemote + "/family");
        JSONObject manifest = new JSONObject();
        manifest.put("app", "Dossier Sanitario Locale"); manifest.put("format", "DSL5-CLOUD"); manifest.put("archiveId", archiveId);
        manifest.put("displayName", cfg.optString("displayName")); manifest.put("provider", "mega"); manifest.put("basePath", "Dossier Sanitario Locale"); manifest.put("createdAt", Instant.now().toString()); manifest.put("version", "5.0.0");
        uploadBytes(context, manifest.toString().getBytes(StandardCharsets.UTF_8), rootRemote + "/archive.json", "archive_manifest");
        File plainZip = new File(context.getCacheDir(), "r12_initial_snapshot.zip");
        buildStandaloneSnapshot(context, prefs, cfg, account, plainZip);
        byte[] plain = readAll(new FileInputStream(plainZip));
        JSONObject meta = new JSONObject(); meta.put("kind", "snapshot"); meta.put("archiveId", archiveId); meta.put("deviceId", cfg.optString("deviceId"));
        byte[] encrypted = R12Crypto.encryptDsl5(plain, recovery, meta);
        long required = requiredBytes(encrypted.length);
        if (freeBytes(choice.root) < required) throw new Exception("Spazio insufficiente: servono " + formatBytes(required) + ".");
        File root = ensureRoot(choice.root); File snapshot = new File(root, "current_snapshot.dsl5"); writeBytes(snapshot, encrypted);
        String name = "snapshot23_" + Instant.now().toString().replace(':', '-').replace('.', '-') + "_" + R12Rclone.safePart(cfg.optString("deviceId")) + "_" + UUID.randomUUID() + ".dsl5";
        uploadBytes(context, encrypted, rootRemote + "/snapshots/" + name, "initial_snapshot");
        JSONObject commit = new JSONObject(); commit.put("format", "DSL5-COMMIT"); commit.put("kind", "snapshot"); commit.put("name", name); commit.put("size", encrypted.length); commit.put("at", Instant.now().toString());
        uploadBytes(context, commit.toString().getBytes(StandardCharsets.UTF_8), rootRemote + "/snapshots/" + name + ".commit", "snapshot_commit");
        cfg.put("lastSnapshotName", name); cfg.put("lastSyncAt", Instant.now().toString()); saveConfig(prefs, cfg);
        importSnapshot(context, prefs, cfg, snapshot, recovery);
        schedulePeriodic(context, prefs);
        if (plainZip.exists()) plainZip.delete();
    }

    private static JSONObject buildAccount(AccountDraft draft, String secret, String[] recoveryCodes, boolean administrator) throws Exception {
        byte[] passwordSalt = R12Crypto.randomBytes(16);
        byte[] clientSalt = R12Crypto.randomBytes(16);
        byte[] recoverySalt = R12Crypto.randomBytes(16);
        String normalizedAnswer = R12Crypto.normalizeRecoveryAnswer(draft.recoveryAnswer);
        JSONObject account = new JSONObject();
        account.put("id", "user_" + R12Crypto.randomHex(16)); account.put("displayName", draft.displayName); account.put("username", draft.username);
        account.put("usernameKey", R12Crypto.normalizeUsername(draft.username)); account.put("email", draft.email.trim().toLowerCase(Locale.ROOT));
        account.put("passwordSalt", R12Crypto.b64Url(passwordSalt)); account.put("passwordHash", R12Crypto.passwordHash(draft.password, passwordSalt)); account.put("passwordIterations", 260000);
        account.put("clientSalt", R12Crypto.b64Url(clientSalt)); account.put("mfaEnabled", true); account.put("mfaSecretEnvelope", R12Crypto.portableMfaEnvelope(secret, draft.password));
        account.put("recoveryQuestion", draft.recoveryQuestion); account.put("recoveryAnswerSalt", R12Crypto.b64Url(recoverySalt)); account.put("recoveryAnswerHash", R12Crypto.passwordHash(normalizedAnswer, recoverySalt)); account.put("recoveryAnswerIterations", 260000);
        account.put("recoveryFailedAttempts", 0); account.put("recoveryLockUntil", 0); account.put("failedAttempts", 0); account.put("lockUntil", 0);
        JSONArray hashes = new JSONArray(); for (String code : recoveryCodes) hashes.put(R12Crypto.recoveryCodeHash(code)); account.put("recoveryCodeHashes", hashes);
        account.put("role", administrator ? "administrator" : "member"); account.put("credentialOwnership", "personal"); account.put("active", true); account.put("pendingAssociation", !administrator);
        if (administrator) account.put("accessLevel", "administrator");
        account.put("createdAt", Instant.now().toString()); account.put("updatedAt", Instant.now().toString());
        return account;
    }

    private static void publishPendingCompletion(Context context, SharedPreferences prefs, JSONObject cfg) throws Exception {
        String raw = prefs.getString(PENDING_COMPLETION_KEY, ""); if (raw == null || raw.trim().isEmpty()) return;
        JSONObject pending = new JSONObject(raw); String activationId = pending.optString("activationId", ""); if (activationId.isEmpty()) return;
        byte[] key = recoveryKey(context, cfg);
        JSONObject plain = new JSONObject(); plain.put("format", "DSL5-FAMILY-COMPLETION"); plain.put("version", 1); plain.put("activationId", activationId);
        plain.put("profileId", pending.optString("profileId", "")); plain.put("account", pending.getJSONObject("account")); plain.put("completedAt", Instant.now().toString());
        JSONObject meta = new JSONObject(); meta.put("kind", "family-completion"); meta.put("activationId", activationId);
        byte[] encrypted = R12Crypto.encryptDsl5(plain.toString().getBytes(StandardCharsets.UTF_8), key, meta);
        String root = cloudRoot(cfg); R12Rclone.mkdir(context, root + "/family"); R12Rclone.mkdir(context, root + "/family/completions");
        uploadBytes(context, encrypted, root + "/family/completions/" + R12Rclone.safePart(activationId) + ".dslf", "family_completion");
    }

    private static void checkCompletionConsumed(Context context, SharedPreferences prefs, JSONObject cfg) {
        if (!"pending_admin".equals(cfg.optString("associationStatus"))) return;
        String activationId = cfg.optString("activationId", ""); if (activationId.isEmpty()) return;
        String remote = cloudRoot(cfg) + "/family/completions/" + R12Rclone.safePart(activationId) + ".dslf";
        if (!R12Rclone.exists(context, remote)) {
            try { cfg.put("associationStatus", "active"); saveConfig(prefs, cfg); prefs.edit().remove(PENDING_COMPLETION_KEY).apply(); } catch (Exception ignored) {}
        }
    }

    public static void queueAgendaPut(Context context, SharedPreferences prefs, JSONObject nativeItem) {
        try {
            JSONObject cfg = loadConfig(prefs); if (cfg.optString("archiveId").isEmpty()) return;
            String id = windowsId(nativeItem, "calevent");
            JSONObject entity = rawEntity(prefs, "calendarEvents", id);
            if (entity == null) entity = new JSONObject();
            entity.put("id", id); entity.put("profileId", cfg.optString("linkedProfileId"));
            entity.put("category", nativeItem.optString("type", "Visita")); entity.put("title", nativeItem.optString("title", "Appuntamento sanitario"));
            entity.put("startDate", toIsoDate(nativeItem.optString("date", ""))); entity.put("startTime", nativeItem.optString("time", "")); entity.put("allDay", nativeItem.optString("time", "").isEmpty());
            if (!entity.has("durationMinutes")) entity.put("durationMinutes", 60); if (!entity.has("status")) entity.put("status", "programmato");
            entity.put("location", nativeItem.optString("location", "")); entity.put("notes", nativeItem.optString("notes", ""));
            JSONArray reminders = new JSONArray(); for (String part : nativeItem.optString("alerts", "1440").split(",")) { try { reminders.put(Integer.parseInt(part.trim())); } catch (Exception ignored) {} } entity.put("reminders", reminders);
            nativeItem.put("windows_id", id); replaceNativeById(prefs, PREF_AGENDA, nativeItem);
            queuePut(context, prefs, cfg, "calendarEvents", id, entity, Arrays.asList("category","title","startDate","startTime","allDay","location","notes","reminders"));
        } catch (Exception ignored) {}
    }

    public static void queueDoctorPut(Context context, SharedPreferences prefs, JSONObject nativeItem) {
        try {
            JSONObject cfg = loadConfig(prefs); if (cfg.optString("archiveId").isEmpty()) return; String id = windowsId(nativeItem, "doctor");
            JSONObject entity = rawEntity(prefs, "doctors", id); if (entity == null) entity = new JSONObject();
            entity.put("id", id); entity.put("profileId", cfg.optString("linkedProfileId")); entity.put("name", nativeItem.optString("name")); entity.put("specialty", nativeItem.optString("specialty")); entity.put("phone", nativeItem.optString("phone")); entity.put("email", nativeItem.optString("email")); entity.put("notes", nativeItem.optString("notes"));
            nativeItem.put("windows_id", id); replaceNativeById(prefs, PREF_DOCTORS, nativeItem);
            queuePut(context, prefs, cfg, "doctors", id, entity, Arrays.asList("name","specialty","phone","email","notes"));
        } catch (Exception ignored) {}
    }

    public static void queueExemptionPut(Context context, SharedPreferences prefs, JSONObject nativeItem) {
        try {
            JSONObject cfg = loadConfig(prefs); if (cfg.optString("archiveId").isEmpty()) return; String id = windowsId(nativeItem, "exemption");
            JSONObject entity = rawEntity(prefs, "exemptions", id); if (entity == null) entity = new JSONObject();
            entity.put("id", id); entity.put("profileId", cfg.optString("linkedProfileId")); entity.put("code", nativeItem.optString("code")); entity.put("description", nativeItem.optString("description")); entity.put("expiry", nativeItem.optString("expiry")); entity.put("notes", nativeItem.optString("notes"));
            nativeItem.put("windows_id", id); replaceNativeById(prefs, PREF_EXEMPTIONS, nativeItem);
            queuePut(context, prefs, cfg, "exemptions", id, entity, Arrays.asList("code","description","expiry","notes"));
        } catch (Exception ignored) {}
    }

    public static void queueProfilePut(Context context, SharedPreferences prefs) {
        try {
            JSONObject cfg = loadConfig(prefs); String id = cfg.optString("linkedProfileId", ""); if (id.isEmpty()) return;
            JSONObject entity = rawEntity(prefs, "profiles", id); if (entity == null) entity = new JSONObject();
            entity.put("id", id); entity.put("firstName", prefs.getString("profile_first_name", "")); entity.put("lastName", prefs.getString("profile_last_name", ""));
            entity.put("birthDate", toIsoDate(prefs.getString("profile_birth", ""))); entity.put("address", prefs.getString("profile_address", "")); entity.put("postalCode", prefs.getString("profile_zip", "")); entity.put("city", prefs.getString("profile_city", "")); entity.put("province", prefs.getString("profile_province", ""));
            queuePut(context, prefs, cfg, "profiles", id, entity, Arrays.asList("firstName","lastName","birthDate","address","postalCode","city","province"));
        } catch (Exception ignored) {}
    }

    public static void queueNativeDelete(Context context, SharedPreferences prefs, String nativeKey, JSONObject previous) {
        if (previous == null) return;
        String store = PREF_DOCTORS.equals(nativeKey) ? "doctors" : PREF_EXEMPTIONS.equals(nativeKey) ? "exemptions" : "";
        if (store.isEmpty()) return;
        String id = previous.optString("windows_id", ""); if (id.isEmpty()) return;
        try { queueDelete(context, prefs, loadConfig(prefs), store, id); } catch (Exception ignored) {}
    }

    public static void queueAgendaDelete(Context context, SharedPreferences prefs, JSONObject previous) {
        if (previous == null) return; String id = previous.optString("windows_id", ""); if (id.isEmpty()) return;
        try { queueDelete(context, prefs, loadConfig(prefs), "calendarEvents", id); } catch (Exception ignored) {}
    }

    private static void queuePut(Context context, SharedPreferences prefs, JSONObject cfg, String store, String entityId, JSONObject entity, List<String> changedFields) throws Exception {
        if (cfg.optString("archiveId", "").isEmpty()) return;
        JSONObject previous = rawEntity(prefs, store, entityId); JSONObject oldMeta = previous == null ? null : previous.optJSONObject("_syncMeta");
        int baseRevision = oldMeta == null ? 0 : oldMeta.optInt("revision", 0); String eventId = "change_" + UUID.randomUUID(); String now = Instant.now().toString();
        JSONObject fields = oldMeta == null || oldMeta.optJSONObject("fields") == null ? new JSONObject() : new JSONObject(oldMeta.optJSONObject("fields").toString());
        for (String field : changedFields) { JSONObject stamp = new JSONObject(); stamp.put("at", now); stamp.put("deviceId", cfg.optString("deviceId", deviceId(prefs))); stamp.put("eventId", eventId); fields.put(field, stamp); }
        JSONObject meta = new JSONObject(); meta.put("revision", baseRevision + 1); meta.put("baseRevision", baseRevision); meta.put("eventId", eventId); meta.put("deviceId", cfg.optString("deviceId")); meta.put("updatedAt", now); meta.put("fields", fields);
        entity.put("_syncMeta", meta); entity.put("updatedAt", now); saveRawEntity(prefs, store, entityId, entity);
        JSONObject event = new JSONObject(); event.put("id", eventId); event.put("profileId", entity.optString("profileId", "")); event.put("status", "pending"); event.put("operation", "put"); event.put("store", store); event.put("entityId", entityId); event.put("baseRevision", baseRevision); event.put("revision", baseRevision + 1); event.put("deviceId", cfg.optString("deviceId")); event.put("createdAt", now); event.put("entity", entity);
        enqueueEvent(prefs, event); scheduleImmediate(context, prefs);
    }

    private static void queueDelete(Context context, SharedPreferences prefs, JSONObject cfg, String store, String entityId) throws Exception {
        if (cfg.optString("archiveId", "").isEmpty()) return; JSONObject previous = rawEntity(prefs, store, entityId); int base = previous == null || previous.optJSONObject("_syncMeta") == null ? 0 : previous.optJSONObject("_syncMeta").optInt("revision", 0);
        JSONObject event = new JSONObject(); event.put("id", "change_" + UUID.randomUUID()); event.put("profileId", previous == null ? cfg.optString("linkedProfileId") : previous.optString("profileId", cfg.optString("linkedProfileId"))); event.put("status", "pending"); event.put("operation", "delete"); event.put("store", store); event.put("entityId", entityId); event.put("baseRevision", base); event.put("revision", base + 1); event.put("deviceId", cfg.optString("deviceId")); event.put("createdAt", Instant.now().toString());
        enqueueEvent(prefs, event); scheduleImmediate(context, prefs);
    }

    private static void enqueueEvent(SharedPreferences prefs, JSONObject event) {
        JSONArray old = readArray(prefs, QUEUE_KEY); JSONArray next = new JSONArray();
        String store = event.optString("store"), entityId = event.optString("entityId");
        for (int i = 0; i < old.length(); i++) { JSONObject e = old.optJSONObject(i); if (e == null) continue; if (store.equals(e.optString("store")) && entityId.equals(e.optString("entityId"))) continue; next.put(e); }
        next.put(event); saveArray(prefs, QUEUE_KEY, next);
    }

    public static String syncNow(Context context, SharedPreferences prefs, boolean background) throws Exception {
        synchronized (R12CloudManager.class) { if (syncing) return "Sincronizzazione già in corso"; syncing = true; }
        try {
            JSONObject cfg = loadConfig(prefs); if (cfg.optString("archiveId", "").isEmpty()) return "Dossier cloud non configurato";
            if (archiveRoot(context, cfg, false) == null) throw new Exception("Archivio Dossier non disponibile. Reinserisci la memoria selezionata.");
            if (prefs.getString(PENDING_COMPLETION_KEY, "").length() > 2) { try { publishPendingCompletion(context, prefs, cfg); } catch (Exception ignored) {} }
            int received = pullRemoteChanges(context, prefs, cfg, false);
            int sent = uploadPendingChanges(context, prefs, cfg);
            checkCompletionConsumed(context, prefs, cfg);
            cfg.put("lastSyncAt", Instant.now().toString()); saveConfig(prefs, cfg);
            return sent + " inviate · " + received + " ricevute";
        } finally { synchronized (R12CloudManager.class) { syncing = false; } }
    }

    private static int uploadPendingChanges(Context context, SharedPreferences prefs, JSONObject cfg) throws Exception {
        JSONArray queue = readArray(prefs, QUEUE_KEY); if (queue.length() == 0) return 0; byte[] recovery = recoveryKey(context, cfg);
        String batchId = "batch23_" + Instant.now().toString().replace(':','-').replace('.','-') + "_" + UUID.randomUUID();
        ByteArrayOutputStream batchBytes = new ByteArrayOutputStream();
        try (ZipOutputStream batchZip = new ZipOutputStream(batchBytes)) {
            for (int i = 0; i < queue.length(); i++) {
                JSONObject event = queue.optJSONObject(i); if (event == null) continue;
                byte[] eventPacked = eventBlob(event, recovery, cfg.optString("deviceId"));
                ZipEntry entry = new ZipEntry("events/" + event.optString("id") + ".dslc"); batchZip.putNextEntry(entry); batchZip.write(eventPacked); batchZip.closeEntry();
            }
        }
        JSONObject meta = new JSONObject(); meta.put("kind", "change-batch"); meta.put("batchId", batchId); meta.put("deviceId", cfg.optString("deviceId")); meta.put("events", queue.length());
        byte[] encryptedBatch = R12Crypto.encryptDsl5(batchBytes.toByteArray(), recovery, meta);
        String remoteDir = cloudRoot(cfg) + "/changes/" + R12Rclone.safePart(cfg.optString("deviceId")); R12Rclone.mkdir(context, remoteDir);
        uploadBytes(context, encryptedBatch, remoteDir + "/" + batchId + ".dslb", "change_batch");
        JSONObject commit = new JSONObject(); commit.put("format", "DSL5-COMMIT"); commit.put("kind", "changes"); commit.put("batchId", batchId); commit.put("size", encryptedBatch.length); commit.put("events", queue.length()); commit.put("deviceId", cfg.optString("deviceId")); commit.put("at", Instant.now().toString());
        uploadBytes(context, commit.toString().getBytes(StandardCharsets.UTF_8), remoteDir + "/" + batchId + ".commit", "change_commit");
        saveArray(prefs, QUEUE_KEY, new JSONArray());
        return queue.length();
    }

    private static byte[] eventBlob(JSONObject event, byte[] recovery, String deviceId) throws Exception {
        JSONObject clone = new JSONObject(event.toString()); clone.remove("entity"); clone.remove("previous"); JSONObject payload = new JSONObject(); payload.put("event", clone); payload.put("entity", event.optJSONObject("entity"));
        ByteArrayOutputStream zipBytes = new ByteArrayOutputStream(); try (ZipOutputStream zip = new ZipOutputStream(zipBytes)) { zip.putNextEntry(new ZipEntry("event.json")); zip.write(payload.toString().getBytes(StandardCharsets.UTF_8)); zip.closeEntry(); }
        JSONObject meta = new JSONObject(); meta.put("kind", "change"); meta.put("eventId", event.optString("id")); meta.put("deviceId", deviceId);
        return R12Crypto.encryptDsl5(zipBytes.toByteArray(), recovery, meta);
    }

    private static int pullRemoteChanges(Context context, SharedPreferences prefs, JSONObject cfg, boolean initial) throws Exception {
        JSONArray listed; try { listed = R12Rclone.lsJson(context, cloudRoot(cfg) + "/changes", true); } catch (Exception e) { return 0; }
        Set<String> names = new HashSet<>(); for (int i = 0; i < listed.length(); i++) { JSONObject x = listed.optJSONObject(i); if (x != null) names.add(x.optString("Path", x.optString("Name"))); }
        Set<String> processed = jsonStringSet(cfg.optJSONArray("processedBatches")); List<JSONObject> batches = new ArrayList<>(); String own = R12Rclone.safePart(cfg.optString("deviceId")) + "/";
        for (int i = 0; i < listed.length(); i++) {
            JSONObject x = listed.optJSONObject(i); if (x == null) continue; String path = x.optString("Path", x.optString("Name")); if (!path.endsWith(".dslb") || path.startsWith(own)) continue;
            String leaf = path.substring(path.lastIndexOf('/') + 1); String id = leaf.substring(0, leaf.length() - 5); String dir = path.contains("/") ? path.substring(0, path.lastIndexOf('/') + 1) : "";
            if (!names.contains(dir + id + ".commit") && !names.contains(id + ".commit")) continue; if (processed.contains(id)) continue; batches.add(x);
        }
        batches.sort(Comparator.comparing(o -> o.optString("Path", o.optString("Name")))); int applied = 0;
        for (JSONObject item : batches) {
            String path = item.optString("Path", item.optString("Name")); String leaf = path.substring(path.lastIndexOf('/') + 1); String id = leaf.substring(0, leaf.length() - 5);
            File temp = new File(context.getCacheDir(), "r12_remote_" + R12Rclone.safePart(id) + ".dslb"); R12Rclone.copyFromRemote(context, cloudRoot(cfg) + "/changes/" + path, temp);
            List<RemoteEvent> events = parseBatch(temp, recoveryKey(context, cfg));
            for (RemoteEvent event : events) if (applyRemoteEvent(context, prefs, cfg, event, false)) applied++;
            processed.add(id); if (temp.exists()) temp.delete();
        }
        cfg.put("processedBatches", new JSONArray(processed)); saveConfig(prefs, cfg); return applied;
    }

    private static List<RemoteEvent> parseBatch(File file, byte[] recovery) throws Exception {
        byte[] packed = readAll(new FileInputStream(file)); byte[] plain = R12Crypto.decryptDsl5(packed, recovery); List<RemoteEvent> out = new ArrayList<>();
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(plain))) {
            ZipEntry entry; while ((entry = zip.getNextEntry()) != null) { if (!entry.isDirectory() && entry.getName().endsWith(".dslc")) out.add(parseEvent(readAll(zip), recovery)); zip.closeEntry(); }
        }
        out.sort(Comparator.comparing(x -> x.event.optString("createdAt", ""))); return out;
    }

    private static RemoteEvent parseEvent(byte[] packed, byte[] recovery) throws Exception {
        byte[] plain = R12Crypto.decryptDsl5(packed, recovery); Map<String, byte[]> files = new HashMap<>(); JSONObject payload = null;
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(plain))) { ZipEntry entry; while ((entry = zip.getNextEntry()) != null) { if (entry.isDirectory()) continue; byte[] bytes = readAll(zip); if ("event.json".equals(entry.getName())) payload = new JSONObject(new String(bytes, StandardCharsets.UTF_8)); else files.put(entry.getName(), bytes); zip.closeEntry(); } }
        if (payload == null) throw new Exception("Evento cloud non leggibile"); return new RemoteEvent(payload.getJSONObject("event"), payload.optJSONObject("entity"), files);
    }

    private static boolean applyRemoteEvent(Context context, SharedPreferences prefs, JSONObject cfg, RemoteEvent remote, boolean force) throws Exception {
        String store = remote.event.optString("store"), entityId = remote.event.optString("entityId"), operation = remote.event.optString("operation");
        if (!force && hasPendingFor(prefs, store, entityId)) { addConflict(prefs, remote); return false; }
        if ("delete".equals(operation)) { removeRawEntity(prefs, store, entityId); removeNativeByWindowsId(prefs, store, entityId); if ("documents".equals(store)) markDocumentDeleted(prefs, entityId); return true; }
        JSONObject entity = remote.entity; if (entity == null) return false; String profileId = entity.optString("profileId", ""); if (!profileId.isEmpty() && !profileId.equals(cfg.optString("linkedProfileId")) && !"profiles".equals(store)) return false;
        saveRawEntity(prefs, store, entityId, entity);
        if ("profiles".equals(store) && entityId.equals(cfg.optString("linkedProfileId"))) mapProfileToPrefs(prefs, entity);
        else if ("doctors".equals(store)) upsertNativeMapped(prefs, PREF_DOCTORS, mapDoctor(entity));
        else if ("exemptions".equals(store)) upsertNativeMapped(prefs, PREF_EXEMPTIONS, mapExemption(entity));
        else if ("calendarEvents".equals(store)) upsertNativeMapped(prefs, PREF_AGENDA, mapAgenda(entity));
        else if ("documents".equals(store)) applyDocumentEvent(context, prefs, cfg, entity, remote.files);
        return true;
    }

    private static void applyDocumentEvent(Context context, SharedPreferences prefs, JSONObject cfg, JSONObject entity, Map<String, byte[]> files) throws Exception {
        JSONArray docs = readArray(prefs, DOCS_KEY); String id = entity.optString("id", ""); JSONObject doc = null; for (int i = 0; i < docs.length(); i++) { JSONObject d = docs.optJSONObject(i); if (d != null && id.equals(d.optString("windows_id"))) { doc = d; break; } }
        if (doc == null) { doc = new JSONObject(); doc.put("windows_id", id); docs.put(doc); }
        copyDocMeta(entity, doc); JSONObject blobRef = entity.optJSONObject("fileBlob"); if (blobRef != null) { byte[] data = files.get(blobRef.optString("__blob")); if (data != null) { File root = archiveRoot(context, cfg, true); File deltaDir = new File(root, "delta_documents"); if (!deltaDir.exists()) deltaDir.mkdirs(); JSONObject meta = new JSONObject(); meta.put("kind", "android-delta-document"); meta.put("documentId", id); byte[] encrypted = R12Crypto.encryptDsl5(data, recoveryKey(context, cfg), meta); File target = new File(deltaDir, R12Rclone.safePart(id) + ".dsl5"); writeBytes(target, encrypted); doc.put("deltaFile", target.getAbsolutePath()); } }
        saveArray(prefs, DOCS_KEY, docs);
    }

    private static void addConflict(SharedPreferences prefs, RemoteEvent remote) {
        try { JSONArray conflicts = readArray(prefs, CONFLICTS_KEY); JSONObject c = new JSONObject(); c.put("id", "conflict_" + UUID.randomUUID()); c.put("store", remote.event.optString("store")); c.put("entityId", remote.event.optString("entityId")); c.put("remoteEvent", remote.event); if (remote.entity != null) c.put("remoteEntity", remote.entity); c.put("createdAt", Instant.now().toString()); conflicts.put(c); saveArray(prefs, CONFLICTS_KEY, conflicts); } catch (Exception ignored) {}
    }

    private static void showConflicts(Activity activity, SharedPreferences prefs) {
        JSONArray conflicts = readArray(prefs, CONFLICTS_KEY); if (conflicts.length() == 0) { Toast.makeText(activity, "Nessun conflitto da verificare", Toast.LENGTH_SHORT).show(); return; }
        JSONObject c = conflicts.optJSONObject(0); if (c == null) return;
        String message = "Lo stesso elemento è stato modificato sia su questo dispositivo sia su un altro dispositivo mentre erano disallineati.\n\nSe mantieni la modifica locale, verrà inviata al cloud. Se mantieni quella remota, la modifica locale in attesa viene scartata.";
        new AlertDialog.Builder(activity).setTitle("Conflitto · " + c.optString("store")).setMessage(message)
                .setNeutralButton("Chiudi", null)
                .setNegativeButton("Mantieni locale", (d,w) -> { removeConflict(prefs, c.optString("id")); Toast.makeText(activity, "Modifica locale mantenuta", Toast.LENGTH_SHORT).show(); })
                .setPositiveButton("Mantieni remota", (d,w) -> runProgress(activity, "Risoluzione conflitto", () -> {
                    removePendingFor(prefs, c.optString("store"), c.optString("entityId"));
                    JSONObject event = c.optJSONObject("remoteEvent"); JSONObject entity = c.optJSONObject("remoteEntity");
                    if (event != null) applyRemoteEvent(activity, prefs, loadConfig(prefs), new RemoteEvent(event, entity, new HashMap<>()), true);
                    removeConflict(prefs, c.optString("id"));
                })).show();
    }

    private static void syncInteractive(Activity activity, SharedPreferences prefs) {
        runProgress(activity, "Sincronizzazione Dossier", () -> { String result = syncNow(activity, prefs, false); activity.runOnUiThread(() -> Toast.makeText(activity, "Sincronizzazione completata · " + result, Toast.LENGTH_LONG).show()); });
    }

    public static void schedulePeriodic(Context context, SharedPreferences prefs) {
        String policy = prefs.getString(POLICY_KEY, "smart"); WorkManager wm = WorkManager.getInstance(context);
        if ("manual".equals(policy) || !configured(prefs)) { wm.cancelUniqueWork(WORK_PERIODIC); return; }
        NetworkType type = "wifi".equals(policy) ? NetworkType.UNMETERED : NetworkType.CONNECTED;
        Constraints constraints = new Constraints.Builder().setRequiredNetworkType(type).build();
        PeriodicWorkRequest request = new PeriodicWorkRequest.Builder(R12SyncWorker.class, 6, TimeUnit.HOURS).setConstraints(constraints).build();
        wm.enqueueUniquePeriodicWork(WORK_PERIODIC, ExistingPeriodicWorkPolicy.UPDATE, request);
    }

    private static void scheduleImmediate(Context context, SharedPreferences prefs) {
        String policy = prefs.getString(POLICY_KEY, "smart"); if ("manual".equals(policy)) return; NetworkType type = "wifi".equals(policy) ? NetworkType.UNMETERED : NetworkType.CONNECTED;
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(R12SyncWorker.class).setConstraints(new Constraints.Builder().setRequiredNetworkType(type).build()).build();
        WorkManager.getInstance(context).enqueueUniqueWork(WORK_IMMEDIATE, ExistingWorkPolicy.REPLACE, request);
    }

    private static void chooseStorageMove(Activity activity, SharedPreferences prefs) {
        JSONObject cfg = loadConfig(prefs); File current = archiveRoot(activity, cfg, false); if (current == null) { Toast.makeText(activity, "La memoria attuale non è disponibile", Toast.LENGTH_LONG).show(); return; }
        List<StorageChoice> choices = storageChoices(activity); String[] labels = new String[choices.size()]; for (int i=0;i<choices.size();i++) labels[i]=choices.get(i).label+" · liberi "+formatBytes(choices.get(i).freeBytes);
        new AlertDialog.Builder(activity).setTitle("Sposta archivio Dossier").setSingleChoiceItems(labels,0,null).setNegativeButton("Annulla",null).setPositiveButton("Sposta",(dialog,which)->{
            AlertDialog ad=(AlertDialog)dialog;int pos=ad.getListView().getCheckedItemPosition();if(pos<0)pos=0;StorageChoice target=choices.get(pos);if(current.getAbsolutePath().equals(target.root.getAbsolutePath()))return;
            runProgress(activity,"Spostamento archivio",()->moveArchive(activity,prefs,cfg,current,target));
        }).show();
    }

    private static void moveArchive(Context context, SharedPreferences prefs, JSONObject cfg, File source, StorageChoice target) throws Exception {
        long bytes = directoryBytes(source); long required = requiredBytes(bytes); if (freeBytes(target.root) < required) throw new Exception("Spazio insufficiente nella memoria di destinazione.");
        File targetRoot = ensureRoot(target.root); File staging = new File(targetRoot.getParentFile(), targetRoot.getName()+".moving"); deleteTree(staging); copyTree(source, staging); if (!verifyTrees(source, staging)) { deleteTree(staging); throw new Exception("Verifica della copia non superata. L’archivio originale è rimasto intatto."); }
        deleteTree(targetRoot); if (!staging.renameTo(targetRoot)) { copyTree(staging,targetRoot); if(!verifyTrees(source,targetRoot)) throw new Exception("Verifica finale della copia non superata."); deleteTree(staging); }
        cfg.put("storagePath", targetRoot.getAbsolutePath()); cfg.put("storageLabel", target.label); saveConfig(prefs,cfg); deleteTree(source);
    }

    private static void openCloudDocument(Activity activity, SharedPreferences prefs, JSONObject doc) {
        runProgress(activity, "Apertura documento", () -> {
            JSONObject cfg = loadConfig(prefs); File outputDir = new File(activity.getCacheDir(), "r12_view"); deleteTree(outputDir); outputDir.mkdirs(); String original = safeFileName(doc.optString("originalName", doc.optString("title", "documento.bin"))); File output = new File(outputDir, System.currentTimeMillis()+"_"+original);
            String delta = doc.optString("deltaFile", ""); if (!delta.isEmpty() && new File(delta).isFile()) { byte[] plain = R12Crypto.decryptDsl5(readAll(new FileInputStream(new File(delta))), recoveryKey(activity,cfg)); writeBytes(output, plain); }
            else { File snapshot = currentSnapshot(activity,cfg); if (snapshot == null) throw new Exception("Archivio Dossier non disponibile."); String entryName = doc.optString("zipEntry", ""); if (entryName.isEmpty()) throw new Exception("Riferimento al documento originale non disponibile."); extractSnapshotEntry(snapshot,recoveryKey(activity,cfg),entryName,output); }
            activity.runOnUiThread(() -> { try { Uri uri = Uri.parse("content://"+activity.getPackageName()+".archiveprovider/view/"+output.getName()); Intent intent = new Intent(Intent.ACTION_VIEW); intent.setDataAndType(uri, doc.optString("mimeType","application/octet-stream")); intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION); activity.startActivity(Intent.createChooser(intent,"Apri documento")); } catch(Exception e){Toast.makeText(activity,"Nessuna app disponibile per aprire il documento",Toast.LENGTH_LONG).show();} });
        });
    }

    private static void extractSnapshotEntry(File snapshot, byte[] recovery, String wanted, File output) throws Exception {
        boolean found = false; try (InputStream decrypted = R12Crypto.openDsl5File(snapshot,recovery); ZipInputStream zip = new ZipInputStream(decrypted)) { ZipEntry entry; byte[] buf=new byte[65536]; while((entry=zip.getNextEntry())!=null){ if(!entry.isDirectory()&&wanted.equals(entry.getName())){try(FileOutputStream out=new FileOutputStream(output)){int n;while((n=zip.read(buf))>=0)out.write(buf,0,n);}found=true;} else {while(zip.read(buf)>=0){}} zip.closeEntry(); } }
        if(!found)throw new Exception("Documento originale non trovato nello snapshot locale.");
    }

    private static void importSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, File snapshot, byte[] recovery) throws Exception {
        String linked = cfg.optString("linkedProfileId", ""); if (linked.isEmpty()) throw new Exception("Profilo autorizzato non indicato."); String linkedFolder = null; JSONObject profile = null; JSONArray doctors = null, exemptions = null, agenda = null, docs = null; JSONObject rawAll = loadRaw(prefs);
        try (InputStream decrypted = R12Crypto.openDsl5File(snapshot, recovery); ZipInputStream zip = new ZipInputStream(decrypted)) {
            ZipEntry entry; while ((entry = zip.getNextEntry()) != null) {
                if (entry.isDirectory()) continue; String name = entry.getName();
                if (name.startsWith("profili/") && name.endsWith("/profilo.json")) { byte[] data=readAll(zip); JSONObject p=new JSONObject(new String(data,StandardCharsets.UTF_8)); if(linked.equals(p.optString("id"))){profile=p;linkedFolder=name.substring(0,name.length()-"profilo.json".length());saveRawInObject(rawAll,"profiles",linked,p);} }
                else if (linkedFolder != null && name.startsWith(linkedFolder)) {
                    String rel = name.substring(linkedFolder.length());
                    if ("medici.json".equals(rel)) { doctors = new JSONArray(new String(readAll(zip),StandardCharsets.UTF_8)); saveRawArray(rawAll,"doctors",doctors); }
                    else if ("esenzioni.json".equals(rel)) { exemptions = new JSONArray(new String(readAll(zip),StandardCharsets.UTF_8)); saveRawArray(rawAll,"exemptions",exemptions); }
                    else if ("agenda.json".equals(rel)) { agenda = new JSONArray(new String(readAll(zip),StandardCharsets.UTF_8)); saveRawArray(rawAll,"calendarEvents",agenda); }
                    else if ("indice_documenti.json".equals(rel)) { docs = new JSONArray(new String(readAll(zip),StandardCharsets.UTF_8)); }
                    else if (rel.startsWith("documenti/")) { String leaf=rel.substring("documenti/".length());int split=leaf.indexOf("__");String id=split>0?leaf.substring(0,split):""; if(docs!=null&&!id.isEmpty()){JSONObject d=findById(docs,id);if(d!=null)d.put("zipEntry",name);} while(zip.read(new byte[65536])>=0){} }
                    else { while(zip.read(new byte[65536])>=0){} }
                } else { while(zip.read(new byte[65536])>=0){} }
                zip.closeEntry();
            }
        }
        if(profile==null)throw new Exception("Il profilo autorizzato non è presente nella copia del Dossier."); mapProfileToPrefs(prefs,profile); prefs.edit().putString(RAW_KEY,rawAll.toString()).apply();
        if(doctors!=null)saveArray(prefs,PREF_DOCTORS,mapDoctors(doctors)); if(exemptions!=null)saveArray(prefs,PREF_EXEMPTIONS,mapExemptions(exemptions)); if(agenda!=null)saveArray(prefs,PREF_AGENDA,mapAgendaArray(agenda)); if(docs!=null){JSONArray mapped=new JSONArray();for(int i=0;i<docs.length();i++){JSONObject d=docs.optJSONObject(i);if(d==null)continue;JSONObject m=new JSONObject();m.put("windows_id",d.optString("id"));copyDocMeta(d,m);m.put("zipEntry",d.optString("zipEntry",""));mapped.put(m);}saveArray(prefs,DOCS_KEY,mapped);}
    }

    private static void buildStandaloneSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, JSONObject account, File output) throws Exception {
        JSONObject profile = profileEntity(prefs,cfg); JSONArray doctors = nativeDoctorsToWindows(prefs,cfg); JSONArray exemptions=nativeExemptionsToWindows(prefs,cfg); JSONArray agenda=nativeAgendaToWindows(prefs,cfg); File photoDir=new File(context.getFilesDir(),"dossier_documents");File[] photos=photoDir.listFiles((d,n)->n.startsWith("referto_foto_")&&n.endsWith(".jpg"));if(photos==null)photos=new File[0];
        String folder="profili/"+slug(profile.optString("firstName")+"_"+profile.optString("lastName"))+"_"+last8(cfg.optString("linkedProfileId"))+"/"; JSONArray docIndex=new JSONArray();JSONArray entries=new JSONArray();
        try(ZipOutputStream zip=new ZipOutputStream(new FileOutputStream(output))){
            addZipJson(zip,entries,"preferenze/impostazioni.json",new JSONArray(),"settings","");addZipJson(zip,entries,"sicurezza/utenti_indicizzati.json",new JSONArray().put(account),"security-index","");addZipJson(zip,entries,"sicurezza/dispositivi.json",new JSONArray(),"devices","");addZipJson(zip,entries,"sicurezza/registro_attivita.json",new JSONArray(),"audit","");
            JSONObject usersStore=new JSONObject();usersStore.put("version",6);usersStore.put("users",new JSONArray().put(account));usersStore.put("invitations",new JSONArray());usersStore.put("temporaryFamilyAccesses",new JSONArray());JSONObject securityBundle=new JSONObject();securityBundle.put("formatVersion",1);securityBundle.put("createdAt",Instant.now().toString());securityBundle.put("exportedBy",account.optString("id"));securityBundle.put("usersStore",usersStore);securityBundle.put("authAudit","");addZipJson(zip,entries,"sicurezza/archivio_credenziali.json",securityBundle,"security-credentials","");
            addZipJson(zip,entries,"sincronizzazione/impostazioni_cloud.json",new JSONArray(),"cloud","");addZipJson(zip,entries,"sincronizzazione/coda.json",new JSONArray(),"sync","");addZipJson(zip,entries,folder+"profilo.json",profile,"profile",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"medici.json",doctors,"doctors",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"terapie.json",new JSONArray(),"therapies",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"esenzioni.json",exemptions,"exemptions",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"diagnosi.json",new JSONArray(),"diagnoses",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"misurazioni.json",new JSONArray(),"measurements",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"percorsi_peso.json",new JSONArray(),"weightJourneys",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"versioni_documenti.json",new JSONArray(),"documentVersions",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"agenda.json",agenda,"calendarEvents",cfg.optString("linkedProfileId"));addZipJson(zip,entries,folder+"richiami_calendario.json",new JSONArray(),"calendarSuggestions",cfg.optString("linkedProfileId"));
            int pi=0;for(File photo:photos){String id="document_"+UUID.randomUUID();JSONObject d=new JSONObject();d.put("id",id);d.put("profileId",cfg.optString("linkedProfileId"));d.put("title","Documento fotografico "+(++pi));d.put("originalName",photo.getName());d.put("mimeType","image/jpeg");d.put("size",photo.length());d.put("addedAt",Instant.ofEpochMilli(photo.lastModified()).toString());docIndex.put(d);}
            addZipJson(zip,entries,folder+"indice_documenti.json",docIndex,"document-index",cfg.optString("linkedProfileId"));pi=0;for(File photo:photos){JSONObject d=docIndex.optJSONObject(pi++);addZipFile(zip,entries,folder+"documenti/"+d.optString("id")+"__"+photo.getName(),photo,"document",cfg.optString("linkedProfileId"));}addZipJson(zip,entries,folder+"cestino.json",new JSONArray(),"trash",cfg.optString("linkedProfileId"));
            JSONObject counts=new JSONObject();counts.put("profiles",1);counts.put("documents",photos.length);JSONObject per=new JSONObject();per.put("profileId",cfg.optString("linkedProfileId"));per.put("name",cfg.optString("profileName"));per.put("documents",photos.length);JSONObject manifest=new JSONObject();manifest.put("app","Dossier Sanitario Locale");manifest.put("version","5.0.0");manifest.put("formatVersion",6);manifest.put("createdAt",Instant.now().toString());manifest.put("counts",counts);manifest.put("profiles",new JSONArray().put(per));manifest.put("entries",entries);manifest.put("securityIncluded",true);addRawZip(zip,"manifest.json",manifest.toString(2).getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void addZipJson(ZipOutputStream zip,JSONArray entries,String path,Object value,String kind,String profileId)throws Exception{byte[] data=(value instanceof JSONObject?((JSONObject)value).toString(2):value instanceof JSONArray?((JSONArray)value).toString(2):String.valueOf(value)).getBytes(StandardCharsets.UTF_8);addRawZip(zip,path,data);JSONObject e=new JSONObject();e.put("path",path);e.put("size",data.length);e.put("sha256",sha256(data));e.put("required",true);e.put("kind",kind);e.put("profileId",profileId);entries.put(e);}
    private static void addZipFile(ZipOutputStream zip,JSONArray entries,String path,File file,String kind,String profileId)throws Exception{byte[] data=readAll(new FileInputStream(file));addRawZip(zip,path,data);JSONObject e=new JSONObject();e.put("path",path);e.put("size",data.length);e.put("sha256",sha256(data));e.put("required",true);e.put("kind",kind);e.put("profileId",profileId);entries.put(e);}
    private static void addRawZip(ZipOutputStream zip,String path,byte[] data)throws Exception{zip.putNextEntry(new ZipEntry(path));zip.write(data);zip.closeEntry();}

    private static JSONObject profileEntity(SharedPreferences prefs,JSONObject cfg)throws Exception{JSONObject p=rawEntity(prefs,"profiles",cfg.optString("linkedProfileId"));if(p==null)p=new JSONObject();p.put("id",cfg.optString("linkedProfileId"));p.put("firstName",prefs.getString("profile_first_name",""));p.put("lastName",prefs.getString("profile_last_name",""));p.put("birthDate",toIsoDate(prefs.getString("profile_birth","")));p.put("address",prefs.getString("profile_address",""));p.put("postalCode",prefs.getString("profile_zip",""));p.put("city",prefs.getString("profile_city",""));p.put("province",prefs.getString("profile_province",""));p.put("updatedAt",Instant.now().toString());saveRawEntity(prefs,"profiles",cfg.optString("linkedProfileId"),p);return p;}
    private static JSONArray nativeDoctorsToWindows(SharedPreferences prefs,JSONObject cfg)throws Exception{JSONArray a=readArray(prefs,PREF_DOCTORS),out=new JSONArray();for(int i=0;i<a.length();i++){JSONObject n=a.optJSONObject(i);if(n==null)continue;String id=windowsId(n,"doctor");JSONObject e=rawEntity(prefs,"doctors",id);if(e==null)e=new JSONObject();e.put("id",id);e.put("profileId",cfg.optString("linkedProfileId"));e.put("name",n.optString("name"));e.put("specialty",n.optString("specialty"));e.put("phone",n.optString("phone"));e.put("email",n.optString("email"));e.put("notes",n.optString("notes"));n.put("windows_id",id);out.put(e);saveRawEntity(prefs,"doctors",id,e);}saveArray(prefs,PREF_DOCTORS,a);return out;}
    private static JSONArray nativeExemptionsToWindows(SharedPreferences prefs,JSONObject cfg)throws Exception{JSONArray a=readArray(prefs,PREF_EXEMPTIONS),out=new JSONArray();for(int i=0;i<a.length();i++){JSONObject n=a.optJSONObject(i);if(n==null)continue;String id=windowsId(n,"exemption");JSONObject e=rawEntity(prefs,"exemptions",id);if(e==null)e=new JSONObject();e.put("id",id);e.put("profileId",cfg.optString("linkedProfileId"));e.put("code",n.optString("code"));e.put("description",n.optString("description"));e.put("expiry",n.optString("expiry"));e.put("notes",n.optString("notes"));n.put("windows_id",id);out.put(e);saveRawEntity(prefs,"exemptions",id,e);}saveArray(prefs,PREF_EXEMPTIONS,a);return out;}
    private static JSONArray nativeAgendaToWindows(SharedPreferences prefs,JSONObject cfg)throws Exception{JSONArray a=readArray(prefs,PREF_AGENDA),out=new JSONArray();for(int i=0;i<a.length();i++){JSONObject n=a.optJSONObject(i);if(n==null)continue;String id=windowsId(n,"calevent");JSONObject e=rawEntity(prefs,"calendarEvents",id);if(e==null)e=new JSONObject();e.put("id",id);e.put("profileId",cfg.optString("linkedProfileId"));e.put("category",n.optString("type","Visita"));e.put("title",n.optString("title"));e.put("startDate",toIsoDate(n.optString("date")));e.put("startTime",n.optString("time"));e.put("allDay",n.optString("time").isEmpty());e.put("durationMinutes",e.optInt("durationMinutes",60));e.put("status",e.optString("status","programmato"));e.put("location",n.optString("location"));e.put("notes",n.optString("notes"));JSONArray rem=new JSONArray();for(String part:n.optString("alerts","1440").split(","))try{rem.put(Integer.parseInt(part.trim()));}catch(Exception ignored){}e.put("reminders",rem);n.put("windows_id",id);out.put(e);saveRawEntity(prefs,"calendarEvents",id,e);}saveArray(prefs,PREF_AGENDA,a);return out;}

    private static void verifyArchiveManifest(Context context,JSONObject cfg)throws Exception{String raw=R12Rclone.run(context,R12Rclone.list("cat",cloudRoot(cfg)+"/archive.json")).trim();JSONObject m=new JSONObject(raw);if(!"DSL5-CLOUD".equals(m.optString("format"))||!cfg.optString("archiveId").equals(m.optString("archiveId")))throw new Exception("L’archivio indicato non corrisponde al Dossier autorizzato.");if(!m.optString("displayName").isEmpty())cfg.put("displayName",m.optString("displayName"));}
    private static SnapshotInfo latestSnapshot(Context context,JSONObject cfg)throws Exception{JSONArray items=R12Rclone.lsJson(context,cloudRoot(cfg)+"/snapshots",false);Set<String>names=new HashSet<>();for(int i=0;i<items.length();i++){JSONObject x=items.optJSONObject(i);if(x!=null)names.add(x.optString("Path",x.optString("Name")));}List<SnapshotInfo>list=new ArrayList<>();for(int i=0;i<items.length();i++){JSONObject x=items.optJSONObject(i);if(x==null)continue;String n=x.optString("Path",x.optString("Name"));if(!n.endsWith(".dsl5"))continue;String leaf=n.substring(n.lastIndexOf('/')+1);if(leaf.startsWith("snapshot23_")&&!names.contains(leaf+".commit")&&!names.contains(n+".commit"))continue;list.add(new SnapshotInfo(leaf,x.optLong("Size",0)));}list.sort((a,b)->b.name.compareTo(a.name));return list.isEmpty()?null:list.get(0);}
    private static String cloudRoot(JSONObject cfg){return cfg.optString("remoteName")+":"+R12Rclone.cleanPath(cfg.optString("basePath"))+"/"+cfg.optString("archiveId");}
    private static byte[] recoveryKey(Context context,JSONObject cfg)throws Exception{return R12Crypto.unb64Url(R12Crypto.unprotectSecret(context,cfg.getString("recoveryKeyProtected")));}

    private static void uploadBytes(Context context,byte[] data,String remote,String prefix)throws Exception{File temp=File.createTempFile("r12_"+prefix,".bin",context.getCacheDir());writeBytes(temp,data);try{R12Rclone.copyToRemote(context,temp,remote);}finally{temp.delete();}}
    private static File archiveRoot(Context context,JSONObject cfg,boolean create){String path=cfg.optString("storagePath","");File root=path.isEmpty()?new File(context.getFilesDir(),"r12_dossier_archive"):new File(path);if(!root.exists()){if(create&&isSelectedStorageMounted(context,cfg))root.mkdirs();else return null;}return root;}
    private static boolean isSelectedStorageMounted(Context context,JSONObject cfg){String path=cfg.optString("storagePath","");if(path.isEmpty()||path.startsWith(context.getFilesDir().getAbsolutePath()))return true;File[] dirs=ContextCompat.getExternalFilesDirs(context,null);if(dirs!=null)for(File d:dirs)if(d!=null&&path.startsWith(d.getAbsolutePath()))return Environment.MEDIA_MOUNTED.equals(Environment.getExternalStorageState(d));return false;}
    private static File ensureRoot(File root)throws Exception{if(!root.exists()&&!root.mkdirs())throw new Exception("Impossibile preparare la memoria selezionata.");return root;}
    private static File currentSnapshot(Context context,JSONObject cfg){File root=archiveRoot(context,cfg,false);if(root==null)return null;File f=new File(root,"current_snapshot.dsl5");return f.isFile()?f:null;}
    private static List<StorageChoice> storageChoices(Context context){List<StorageChoice>out=new ArrayList<>();File internal=new File(context.getFilesDir(),"r12_dossier_archive");out.add(new StorageChoice(internal,"Memoria interna · prestazioni consigliate",freeBytes(internal)));File[] dirs=ContextCompat.getExternalFilesDirs(context,null);if(dirs!=null)for(File d:dirs){if(d==null)continue;try{if(Environment.isExternalStorageRemovable(d)&&Environment.MEDIA_MOUNTED.equals(Environment.getExternalStorageState(d))){File root=new File(d,"dossier_archive");out.add(new StorageChoice(root,"Memoria esterna / scheda SD · archivio cifrato",freeBytes(root)));}}catch(Exception ignored){}}return out;}
    private static long freeBytes(File path){try{File base=path.exists()?path:path.getParentFile();if(base==null)base=path;StatFs stat=new StatFs(base.getAbsolutePath());return stat.getAvailableBytes();}catch(Exception e){return 0;}}
    private static long requiredBytes(long size){return size+Math.max((long)Math.ceil(size*0.30d),100L*MB);}

    private static void mapProfileToPrefs(SharedPreferences prefs,JSONObject p){prefs.edit().putString("profile_first_name",p.optString("firstName","")).putString("profile_last_name",p.optString("lastName","")).putString("profile_birth",toDisplayDate(p.optString("birthDate","")).trim()).putString("profile_address",p.optString("address","")).putString("profile_zip",p.optString("postalCode","")).putString("profile_city",p.optString("city","")).putString("profile_province",p.optString("province","")).apply();}
    private static JSONArray mapDoctors(JSONArray source)throws Exception{JSONArray out=new JSONArray();for(int i=0;i<source.length();i++){JSONObject e=source.optJSONObject(i);if(e!=null)out.put(mapDoctor(e));}return out;}
    private static JSONObject mapDoctor(JSONObject e)throws Exception{JSONObject n=new JSONObject();n.put("id",localId(e.optString("id")));n.put("windows_id",e.optString("id"));n.put("name",e.optString("name"));n.put("specialty",e.optString("specialty"));n.put("phone",e.optString("phone"));n.put("email",e.optString("email"));n.put("notes",e.optString("notes"));return n;}
    private static JSONArray mapExemptions(JSONArray source)throws Exception{JSONArray out=new JSONArray();for(int i=0;i<source.length();i++){JSONObject e=source.optJSONObject(i);if(e!=null)out.put(mapExemption(e));}return out;}
    private static JSONObject mapExemption(JSONObject e)throws Exception{JSONObject n=new JSONObject();n.put("id",localId(e.optString("id")));n.put("windows_id",e.optString("id"));n.put("code",e.optString("code"));n.put("description",e.optString("description"));n.put("expiry",e.optString("expiry"));n.put("notes",e.optString("notes"));return n;}
    private static JSONArray mapAgendaArray(JSONArray source)throws Exception{JSONArray out=new JSONArray();for(int i=0;i<source.length();i++){JSONObject e=source.optJSONObject(i);if(e!=null)out.put(mapAgenda(e));}return out;}
    private static JSONObject mapAgenda(JSONObject e)throws Exception{JSONObject n=new JSONObject();n.put("id",localId(e.optString("id")));n.put("windows_id",e.optString("id"));n.put("type",e.optString("category",e.optString("type","Visita")));n.put("title",e.optString("title","Appuntamento sanitario"));n.put("date",toDisplayDate(e.optString("startDate",e.optString("date",""))));n.put("time",e.optString("startTime",e.optString("time","")));n.put("location",e.optString("location",""));n.put("notes",e.optString("notes",""));JSONArray rem=e.optJSONArray("reminders");StringBuilder csv=new StringBuilder();if(rem!=null)for(int i=0;i<rem.length();i++){if(csv.length()>0)csv.append(',');csv.append(rem.optInt(i));}n.put("alerts",csv.length()==0?"1440":csv.toString());return n;}
    private static void copyDocMeta(JSONObject from,JSONObject to)throws Exception{String[]keys={"title","originalName","mimeType","clinicalDate","issueDate","addedAt","updatedAt","category","notes"};for(String k:keys)if(from.has(k))to.put(k,from.opt(k));}

    private static JSONObject loadRaw(SharedPreferences prefs){try{return new JSONObject(prefs.getString(RAW_KEY,"{}"));}catch(Exception e){return new JSONObject();}}
    private static JSONObject rawEntity(SharedPreferences prefs,String store,String id){JSONObject all=loadRaw(prefs),bucket=all.optJSONObject(store);return bucket==null?null:bucket.optJSONObject(id);}
    private static void saveRawEntity(SharedPreferences prefs,String store,String id,JSONObject entity)throws Exception{JSONObject all=loadRaw(prefs);saveRawInObject(all,store,id,entity);prefs.edit().putString(RAW_KEY,all.toString()).apply();}
    private static void saveRawInObject(JSONObject all,String store,String id,JSONObject entity)throws Exception{JSONObject bucket=all.optJSONObject(store);if(bucket==null){bucket=new JSONObject();all.put(store,bucket);}bucket.put(id,entity);}
    private static void saveRawArray(JSONObject all,String store,JSONArray array)throws Exception{JSONObject bucket=new JSONObject();for(int i=0;i<array.length();i++){JSONObject e=array.optJSONObject(i);if(e!=null&&!e.optString("id").isEmpty())bucket.put(e.optString("id"),e);}all.put(store,bucket);}
    private static void removeRawEntity(SharedPreferences prefs,String store,String id){try{JSONObject all=loadRaw(prefs),bucket=all.optJSONObject(store);if(bucket!=null)bucket.remove(id);prefs.edit().putString(RAW_KEY,all.toString()).apply();}catch(Exception ignored){}}

    private static void replaceNativeById(SharedPreferences prefs,String key,JSONObject object){JSONArray a=readArray(prefs,key);long id=object.optLong("id",-1);boolean found=false;for(int i=0;i<a.length();i++){JSONObject x=a.optJSONObject(i);if(x!=null&&x.optLong("id",-2)==id){try{a.put(i,object);}catch(Exception ignored){}found=true;break;}}if(!found)a.put(object);saveArray(prefs,key,a);}
    private static void upsertNativeMapped(SharedPreferences prefs,String key,JSONObject object){replaceNativeById(prefs,key,object);}
    private static void removeNativeByWindowsId(SharedPreferences prefs,String store,String windowsId){String key="doctors".equals(store)?PREF_DOCTORS:"exemptions".equals(store)?PREF_EXEMPTIONS:"calendarEvents".equals(store)?PREF_AGENDA:"";if(key.isEmpty())return;JSONArray a=readArray(prefs,key),out=new JSONArray();for(int i=0;i<a.length();i++){JSONObject x=a.optJSONObject(i);if(x!=null&&!windowsId.equals(x.optString("windows_id")))out.put(x);}saveArray(prefs,key,out);}
    private static String windowsId(JSONObject nativeItem,String prefix)throws Exception{String id=nativeItem.optString("windows_id","");if(id.isEmpty()){id=prefix+"_"+UUID.randomUUID();nativeItem.put("windows_id",id);}return id;}
    private static long localId(String windowsId){try{byte[]d=MessageDigest.getInstance("SHA-256").digest(windowsId.getBytes(StandardCharsets.UTF_8));long v=0;for(int i=0;i<8;i++)v=(v<<8)|(d[i]&0xffL);v&=Long.MAX_VALUE;return v==0?1:v;}catch(Exception e){return Math.abs((long)windowsId.hashCode())+1;}}

    private static boolean hasPendingFor(SharedPreferences prefs,String store,String entityId){JSONArray a=readArray(prefs,QUEUE_KEY);for(int i=0;i<a.length();i++){JSONObject e=a.optJSONObject(i);if(e!=null&&store.equals(e.optString("store"))&&entityId.equals(e.optString("entityId")))return true;}return false;}
    private static void removePendingFor(SharedPreferences prefs,String store,String entityId){JSONArray a=readArray(prefs,QUEUE_KEY),out=new JSONArray();for(int i=0;i<a.length();i++){JSONObject e=a.optJSONObject(i);if(e!=null&&store.equals(e.optString("store"))&&entityId.equals(e.optString("entityId")))continue;if(e!=null)out.put(e);}saveArray(prefs,QUEUE_KEY,out);}
    private static void removeConflict(SharedPreferences prefs,String id){JSONArray a=readArray(prefs,CONFLICTS_KEY),out=new JSONArray();for(int i=0;i<a.length();i++){JSONObject e=a.optJSONObject(i);if(e!=null&&!id.equals(e.optString("id")))out.put(e);}saveArray(prefs,CONFLICTS_KEY,out);}
    private static void markDocumentDeleted(SharedPreferences prefs,String id){JSONArray a=readArray(prefs,DOCS_KEY);for(int i=0;i<a.length();i++){JSONObject d=a.optJSONObject(i);if(d!=null&&id.equals(d.optString("windows_id")))try{d.put("deleted",true);}catch(Exception ignored){}}saveArray(prefs,DOCS_KEY,a);}

    private static JSONObject findById(JSONArray array,String id){for(int i=0;i<array.length();i++){JSONObject x=array.optJSONObject(i);if(x!=null&&id.equals(x.optString("id")))return x;}return null;}
    private static JSONObject loadConfig(SharedPreferences prefs){try{return new JSONObject(prefs.getString(CONFIG_KEY,"{}"));}catch(Exception e){return new JSONObject();}}
    private static void saveConfig(SharedPreferences prefs,JSONObject cfg){prefs.edit().putString(CONFIG_KEY,cfg.toString()).apply();}
    private static JSONArray readArray(SharedPreferences prefs,String key){try{return new JSONArray(prefs.getString(key,"[]"));}catch(Exception e){return new JSONArray();}}
    private static void saveArray(SharedPreferences prefs,String key,JSONArray array){prefs.edit().putString(key,array.toString()).apply();}
    private static Set<String> jsonStringSet(JSONArray array){Set<String>out=new HashSet<>();if(array!=null)for(int i=0;i<array.length();i++)out.add(array.optString(i));return out;}
    private static String deviceId(SharedPreferences prefs){String id=prefs.getString(DEVICE_KEY,"");if(id.isEmpty()){id="android_"+UUID.randomUUID();prefs.edit().putString(DEVICE_KEY,id).apply();}return id;}

    private static void showRecoveryCodes(Activity activity,String[] codes){StringBuilder b=new StringBuilder("Conservali separatamente dal telefono. Ogni codice può essere usato una sola volta.\n\n");for(String code:codes)b.append(code).append('\n');new AlertDialog.Builder(activity).setTitle("Codici di recupero personali").setMessage(b.toString()).setPositiveButton("Ho salvato i codici",null).show();}
    private static Bitmap qrBitmap(String text,int size)throws Exception{BitMatrix m=new QRCodeWriter().encode(text, BarcodeFormat.QR_CODE,size,size);Bitmap b=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888);for(int y=0;y<size;y++)for(int x=0;x<size;x++)b.setPixel(x,y,m.get(x,y)?Color.BLACK:Color.WHITE);return b;}
    private static String groupSecret(String secret){StringBuilder b=new StringBuilder();for(int i=0;i<secret.length();i++){if(i>0&&i%4==0)b.append(' ');b.append(secret.charAt(i));}return b.toString();}

    private static void runProgress(Activity activity,String title,ThrowingRunnable work){ProgressDialog p=new ProgressDialog(activity);p.setTitle(title);p.setMessage("Operazione in corso…");p.setIndeterminate(true);p.setCancelable(false);p.show();EXECUTOR.execute(()->{try{work.run();activity.runOnUiThread(()->{if(p.isShowing())p.dismiss();});}catch(Exception e){activity.runOnUiThread(()->{if(p.isShowing())p.dismiss();new AlertDialog.Builder(activity).setTitle("Operazione non completata").setMessage(String.valueOf(e.getMessage())).setPositiveButton("Chiudi",null).show();});}});}
    private interface ThrowingRunnable{void run()throws Exception;}

    private static LinearLayout card(Context c){LinearLayout v=new LinearLayout(c);v.setOrientation(LinearLayout.VERTICAL);v.setPadding(dp(c,14),dp(c,14),dp(c,14),dp(c,14));android.graphics.drawable.GradientDrawable g=new android.graphics.drawable.GradientDrawable();g.setColor(Color.WHITE);g.setCornerRadius(dp(c,14));g.setStroke(dp(c,1),Color.rgb(224,232,229));v.setBackground(g);return v;}
    private static TextView title(Context c,String s){TextView v=new TextView(c);v.setText(s);v.setTextSize(18);v.setTextColor(Color.rgb(32,48,45));v.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);return v;}
    private static TextView body(Context c,String s){TextView v=new TextView(c);v.setText(s);v.setTextSize(14);v.setTextColor(Color.rgb(55,72,68));v.setPadding(0,dp(c,5),0,0);return v;}
    private static TextView note(Context c,String s){TextView v=body(c,s);v.setTextSize(12);v.setTextColor(Color.rgb(91,105,101));v.setPadding(0,dp(c,10),0,0);return v;}
    private static TextView warning(Context c,String s){TextView v=body(c,s);v.setTextColor(Color.rgb(145,78,0));v.setBackgroundColor(Color.rgb(255,247,226));v.setPadding(dp(c,10),dp(c,10),dp(c,10),dp(c,10));return v;}
    private static TextView kv(Context c,String k,String value){TextView v=body(c,k+": "+(value==null||value.isEmpty()?"—":value));v.setPadding(0,dp(c,6),0,0);return v;}
    private static Button button(Context c,String s){Button b=new Button(c);b.setText(s);b.setAllCaps(false);b.setTextSize(14);return b;}
    private static EditText field(Context c,String hint,String value){EditText e=new EditText(c);e.setHint(hint);e.setText(value);e.setSingleLine(true);e.setTextSize(15);e.setPadding(dp(c,8),dp(c,8),dp(c,8),dp(c,8));return e;}
    private static LinearLayout dialogForm(Context c){LinearLayout l=new LinearLayout(c);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(c,18),dp(c,5),dp(c,18),dp(c,5));return l;}
    private static LinearLayout.LayoutParams top(int px){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(0,px,0,0);return p;}
    private static LinearLayout.LayoutParams bottom(int px){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);p.setMargins(0,0,0,px);return p;}
    private static int dp(Context c,int value){return Math.round(value*c.getResources().getDisplayMetrics().density);}
    private static String clean(EditText e){return e.getText()==null?"":e.getText().toString().trim();}

    private static String formatBytes(long value){if(value<MB)return String.format(Locale.ITALY,"%.1f MB",value/1024d/1024d);if(value<1024L*MB)return String.format(Locale.ITALY,"%.0f MB",value/(double)MB);return String.format(Locale.ITALY,"%.2f GB",value/(1024d*MB));}
    private static String toIsoDate(String value){String s=String.valueOf(value==null?"":value).trim();if(s.matches("\\d{4}-\\d{2}-\\d{2}"))return s;if(s.matches("\\d{1,2}/\\d{1,2}/\\d{4}")){String[]p=s.split("/");return String.format(Locale.ROOT,"%04d-%02d-%02d",Integer.parseInt(p[2]),Integer.parseInt(p[1]),Integer.parseInt(p[0]));}return s;}
    private static String toDisplayDate(String value){String s=String.valueOf(value==null?"":value).trim();if(s.matches("\\d{4}-\\d{2}-\\d{2}")){String[]p=s.split("-");return p[2]+"/"+p[1]+"/"+p[0];}return s;}
    private static String safeFileName(String name){String s=String.valueOf(name==null?"documento.bin":name).replaceAll("[^A-Za-z0-9._-]+","_");return s.isEmpty()?"documento.bin":s;}
    private static String slug(String value){String s=java.text.Normalizer.normalize(String.valueOf(value),java.text.Normalizer.Form.NFD).replaceAll("\\p{M}","").toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+","_").replaceAll("^_+|_+$","");return s.isEmpty()?"profilo":s;}
    private static String last8(String value){String s=String.valueOf(value);return s.length()<=8?s:s.substring(s.length()-8);}
    private static String sha256(byte[] data)throws Exception{byte[]d=MessageDigest.getInstance("SHA-256").digest(data);StringBuilder b=new StringBuilder();for(byte x:d)b.append(String.format(Locale.ROOT,"%02x",x&0xff));return b.toString();}
    private static byte[] readAll(InputStream in)throws Exception{try(InputStream src=in;ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[]buf=new byte[65536];int n;while((n=src.read(buf))>=0)out.write(buf,0,n);return out.toByteArray();}}
    private static void writeBytes(File f,byte[] data)throws Exception{File p=f.getParentFile();if(p!=null&&!p.exists())p.mkdirs();try(FileOutputStream out=new FileOutputStream(f)){out.write(data);out.getFD().sync();}}
    private static void replaceVerified(File partial,File target)throws Exception{if(target.exists()){File old=new File(target.getParentFile(),target.getName()+".old");if(old.exists())old.delete();if(!target.renameTo(old))throw new Exception("Impossibile proteggere la copia precedente.");if(!partial.renameTo(target)){old.renameTo(target);throw new Exception("Impossibile rendere definitiva la nuova copia.");}old.delete();}else if(!partial.renameTo(target))throw new Exception("Impossibile rendere definitiva la copia scaricata.");}
    private static long directoryBytes(File f){if(f==null||!f.exists())return 0;if(f.isFile())return f.length();long n=0;File[]a=f.listFiles();if(a!=null)for(File x:a)n+=directoryBytes(x);return n;}
    private static void copyTree(File s,File d)throws Exception{if(s.isDirectory()){if(!d.exists()&&!d.mkdirs())throw new Exception("Impossibile creare la cartella di destinazione");File[]a=s.listFiles();if(a!=null)for(File x:a)copyTree(x,new File(d,x.getName()));}else{try(FileInputStream in=new FileInputStream(s);FileOutputStream out=new FileOutputStream(d)){byte[]b=new byte[65536];int n;while((n=in.read(b))>=0)out.write(b,0,n);out.getFD().sync();}}}
    private static boolean verifyTrees(File a,File b)throws Exception{if(a.isDirectory()!=b.isDirectory())return false;if(a.isFile())return a.length()==b.length()&&sha256(readAll(new FileInputStream(a))).equals(sha256(readAll(new FileInputStream(b))));File[]aa=a.listFiles();if(aa==null)aa=new File[0];for(File x:aa){File y=new File(b,x.getName());if(!y.exists()||!verifyTrees(x,y))return false;}return true;}
    private static void deleteTree(File f){if(f==null||!f.exists())return;if(f.isDirectory()){File[]a=f.listFiles();if(a!=null)for(File x:a)deleteTree(x);}f.delete();}

    private static final class StorageChoice{final File root;final String label;final long freeBytes;StorageChoice(File r,String l,long f){root=r;label=l;freeBytes=f;}}
    private static final class SnapshotInfo{final String name;final long size;SnapshotInfo(String n,long s){name=n;size=s;}}
    private static final class AccountDraft{final String displayName,email,username,password,recoveryQuestion,recoveryAnswer;AccountDraft(String d,String e,String u,String p,String q,String a){displayName=d;email=e;username=u;password=p;recoveryQuestion=q;recoveryAnswer=a;}}
    private static final class RemoteEvent{final JSONObject event,entity;final Map<String,byte[]>files;RemoteEvent(JSONObject e,JSONObject en,Map<String,byte[]>f){event=e;entity=en;files=f;}}
}
