from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
MANIFEST = Path('android-r3/app/src/main/AndroidManifest.xml')
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R18 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    s = replace_once(
        s,
        '    private static final String PREF_AGENDA = "android_agenda_json";\n',
        '    private static final String PREF_AGENDA = "android_agenda_json";\n'
        '    private static final String PENDING_EXISTING_IMPORT_KEY = "r18_pending_existing_import_secure";\n',
        'pending import constant'
    )

    old_counter = r'''    private static final class CountingInputStream extends java.io.FilterInputStream {
        private long count = 0L;
        private final long total;
        private final ImportProgressCallback callback;

        CountingInputStream(InputStream in, long total, ImportProgressCallback callback) {
            super(in);
            this.total = Math.max(1L, total);
            this.callback = callback;
        }

        private void report(int n) {
            if (n <= 0) return;
            count += n;
            if (callback != null) callback.onProgress(count, total);
        }
'''
    new_counter = r'''    private static final class CountingInputStream extends java.io.FilterInputStream {
        private long count = 0L;
        private long lastReported = 0L;
        private long lastReportAt = 0L;
        private final long total;
        private final ImportProgressCallback callback;

        CountingInputStream(InputStream in, long total, ImportProgressCallback callback) {
            super(in);
            this.total = Math.max(1L, total);
            this.callback = callback;
        }

        private void report(int n) {
            if (n <= 0) return;
            count += n;
            if (callback == null) return;
            long now = android.os.SystemClock.elapsedRealtime();
            boolean complete = count >= total;
            boolean enoughBytes = count - lastReported >= 1024L * 1024L;
            boolean enoughTime = now - lastReportAt >= 250L;
            if (complete || enoughBytes || enoughTime) {
                lastReported = count;
                lastReportAt = now;
                callback.onProgress(count, total);
            }
        }
'''
    s = replace_once(s, old_counter, new_counter, 'throttled progress counter')

    render_marker = '            String state = cfg.optString("associationStatus", "active");\n'
    render_add = render_marker + r'''            if (pendingExistingImportAvailable(cfg, prefs.getString(PENDING_EXISTING_IMPORT_KEY, ""))) {
                card.addView(warning(activity, "Importazione del Dossier incompleta. Il dispositivo è già autenticato: non devi reinserire chiave Dossier, account o TOTP."));
                Button resumeImport = button(activity, "Riprendi importazione del Dossier");
                resumeImport.setOnClickListener(v -> resumeExistingImport(activity, prefs));
                card.addView(resumeImport, top(12));
                card.addView(note(activity, "La procedura riparte dall'ultimo archivio locale completo disponibile e conserva l'associazione già verificata."));
                content.addView(card, bottom(14));
                return;
            }
'''
    s = replace_once(s, render_marker, render_add, 'pending import resume panel')

    helper_marker = '    private static void showFamilyConnect(Activity activity, SharedPreferences prefs, boolean existingAccount) {'
    helpers = r'''    static boolean pendingExistingImportAvailable(JSONObject cfg, String protectedState) {
        return cfg != null
                && "import_pending".equals(cfg.optString("associationStatus", ""))
                && protectedState != null
                && protectedState.trim().length() > 20;
    }

    static boolean reusablePartialSnapshot(File partial, long expectedBytes) {
        return partial != null && partial.isFile() && expectedBytes > 0L && partial.length() == expectedBytes;
    }

    private static void persistExistingImportCheckpoint(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account) throws Exception {
        populateExistingConnectionConfig(context, prefs, payload, cfg, choice, account);
        cfg.put("associationStatus", "import_pending");
        saveConfig(prefs, cfg);
        prefs.edit().putString(ACCOUNT_KEY, account.toString()).remove(PENDING_COMPLETION_KEY).apply();

        JSONObject state = new JSONObject();
        state.put("payload", new JSONObject(payload.toString()));
        state.put("account", new JSONObject(account.toString()));
        state.put("storagePath", choice.root.getAbsolutePath());
        state.put("storageLabel", choice.label);
        state.put("snapshotName", snap == null ? "" : snap.name);
        state.put("snapshotSize", snap == null ? 0L : snap.size);
        state.put("savedAt", Instant.now().toString());
        String protectedState = R12Crypto.protectSecret(context, state.toString());
        prefs.edit().putString(PENDING_EXISTING_IMPORT_KEY, protectedState).apply();
    }

    private static void resumeExistingImport(Activity activity, SharedPreferences prefs) {
        try {
            String protectedState = prefs.getString(PENDING_EXISTING_IMPORT_KEY, "");
            JSONObject cfg = loadConfig(prefs);
            if (!pendingExistingImportAvailable(cfg, protectedState)) throw new Exception("Nessuna importazione da riprendere.");
            JSONObject state = new JSONObject(R12Crypto.unprotectSecret(activity, protectedState));
            JSONObject payload = state.getJSONObject("payload");
            JSONObject account = state.getJSONObject("account");
            File root = new File(state.getString("storagePath"));
            String label = state.optString("storageLabel", "Memoria del Dossier");
            StorageChoice choice = new StorageChoice(root, label, freeBytes(root));
            String snapshotName = state.optString("snapshotName", "");
            long snapshotSize = state.optLong("snapshotSize", 0L);
            SnapshotInfo snap = snapshotName.isEmpty() ? null : new SnapshotInfo(snapshotName, snapshotSize);
            startExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);
        } catch (Exception e) {
            String message = String.valueOf(e.getMessage());
            new AlertDialog.Builder(activity)
                    .setTitle("Ripresa importazione non disponibile")
                    .setMessage(message == null || message.trim().isEmpty() ? "Lo stato di ripresa non è leggibile." : message)
                    .setPositiveButton("Chiudi", null)
                    .show();
        }
    }

'''
    s = replace_once(s, helper_marker, helpers + helper_marker, 'resume helpers')

    old_totp = r'''                    if (!R12Crypto.verifyTotp(secret, clean(otp))) { Toast.makeText(activity, "Il codice TOTP non è valido", Toast.LENGTH_LONG).show(); return; }
                    startExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);
'''
    new_totp = r'''                    if (!R12Crypto.verifyTotp(secret, clean(otp))) { Toast.makeText(activity, "Il codice TOTP non è valido", Toast.LENGTH_LONG).show(); return; }
                    try {
                        persistExistingImportCheckpoint(activity, prefs, payload, cfg, choice, snap, account);
                        Toast.makeText(activity, "Dispositivo autenticato. Avvio importazione Dossier.", Toast.LENGTH_SHORT).show();
                        startExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);
                    } catch (Exception e) {
                        Toast.makeText(activity, "Non è stato possibile memorizzare il collegamento del dispositivo.", Toast.LENGTH_LONG).show();
                    }
'''
    s = replace_once(s, old_totp, new_totp, 'persist after TOTP')

    old_show = r'''        progress.setMessage("Preparazione archivio...");
        progress.setCancelable(false);
        progress.show();

        EXECUTOR.execute(() -> {
'''
    new_show = r'''        progress.setMessage("Preparazione archivio...");
        progress.setCancelable(false);
        activity.getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        android.os.PowerManager power = (android.os.PowerManager) activity.getSystemService(Context.POWER_SERVICE);
        final android.os.PowerManager.WakeLock wakeLock = power == null ? null : power.newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK, "ClinicaDigitale:ImportDossier");
        if (wakeLock != null) wakeLock.acquire(java.util.concurrent.TimeUnit.MINUTES.toMillis(30));
        progress.show();

        EXECUTOR.execute(() -> {
'''
    s = replace_once(s, old_show, new_show, 'screen and cpu wake protection')

    old_download = r'''                partial = new File(root, "current_snapshot.dsl5.part");
                if (partial.exists()) partial.delete();
                final File partialRef = partial;

                setImportProgress(activity, progress, DOWNLOAD_PROGRESS_START, "Download del Dossier dal cloud...");
                R12Rclone.copyFromRemoteWithProgress(
                        activity,
                        cloudRoot(cfg) + "/snapshots/" + readySnap.name,
                        partialRef,
                        readySnap.size,
                        (done, total) -> setImportRangeProgress(activity, progress, DOWNLOAD_PROGRESS_START, DOWNLOAD_PROGRESS_END, done, total, "Download del Dossier dal cloud...")
                );
                if (readySnap.size > 0 && partialRef.length() != readySnap.size) {
                    partialRef.delete();
                    throw new Exception("Il download del Dossier non ha la dimensione attesa.");
                }

                setImportProgress(activity, progress, INTEGRITY_PROGRESS_START, "Verifica integrità del Dossier...");
'''
    new_download = r'''                partial = new File(root, "current_snapshot.dsl5.part");
                final File partialRef = partial;

                if (reusablePartialSnapshot(partialRef, readySnap.size)) {
                    setImportProgress(activity, progress, DOWNLOAD_PROGRESS_END, "Download già completato. Ripresa dalla verifica integrità...");
                } else {
                    if (partialRef.exists()) partialRef.delete();
                    setImportProgress(activity, progress, DOWNLOAD_PROGRESS_START, "Download del Dossier dal cloud...");
                    R12Rclone.copyFromRemoteWithProgress(
                            activity,
                            cloudRoot(cfg) + "/snapshots/" + readySnap.name,
                            partialRef,
                            readySnap.size,
                            (done, total) -> setImportRangeProgress(activity, progress, DOWNLOAD_PROGRESS_START, DOWNLOAD_PROGRESS_END, done, total, "Download del Dossier dal cloud...")
                    );
                    if (readySnap.size > 0 && partialRef.length() != readySnap.size) {
                        partialRef.delete();
                        throw new Exception("Il download del Dossier non ha la dimensione attesa.");
                    }
                }

                setImportProgress(activity, progress, INTEGRITY_PROGRESS_START, "Verifica integrità del Dossier...");
'''
    s = replace_once(s, old_download, new_download, 'reuse completed local download')

    old_catch = r'''            } catch (Exception e) {
                if (partial != null && partial.exists()) partial.delete();
                String message = String.valueOf(e.getMessage());
                activity.runOnUiThread(() -> {
                    progress.dismiss();
                    new AlertDialog.Builder(activity)
                            .setTitle("Importazione non riuscita")
                            .setMessage(message == null || message.trim().isEmpty() ? "Operazione cloud non riuscita." : message)
                            .setPositiveButton("Chiudi", null)
                            .show();
                });
            }
        });
    }
'''
    new_catch = r'''            } catch (Exception e) {
                String message = String.valueOf(e.getMessage());
                activity.runOnUiThread(() -> {
                    progress.dismiss();
                    new AlertDialog.Builder(activity)
                            .setTitle("Importazione interrotta")
                            .setMessage((message == null || message.trim().isEmpty() ? "Operazione cloud non riuscita." : message) + "\n\nIl dispositivo resta autenticato. Puoi riprendere l'importazione senza reinserire chiave, account o TOTP.")
                            .setPositiveButton("Chiudi", null)
                            .show();
                });
            } finally {
                if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
                activity.runOnUiThread(() -> activity.getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON));
            }
        });
    }
'''
    s = replace_once(s, old_catch, new_catch, 'preserve checkpoint and release wake lock')

    finalize_marker = r'''        cfg.put("lastSnapshotName", snap.name);
        cfg.put("lastSyncAt", Instant.now().toString());
        saveConfig(prefs, cfg);

        setImportProgress(activity, progress, 98, "Preparazione sincronizzazione automatica...");
'''
    finalize_new = r'''        cfg.put("lastSnapshotName", snap.name);
        cfg.put("lastSyncAt", Instant.now().toString());
        cfg.put("associationStatus", "active");
        saveConfig(prefs, cfg);
        prefs.edit().remove(PENDING_EXISTING_IMPORT_KEY).apply();

        setImportProgress(activity, progress, 98, "Preparazione sincronizzazione automatica...");
'''
    s = replace_once(s, finalize_marker, finalize_new, 'clear pending checkpoint only after success')

    CLOUD.write_text(s, encoding='utf-8')


def patch_manifest():
    s = MANIFEST.read_text(encoding='utf-8')
    if 'android.permission.WAKE_LOCK' not in s:
        s = replace_once(
            s,
            '<uses-permission android:name="android.permission.INTERNET" />',
            '<uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.WAKE_LOCK" />',
            'wake lock permission'
        )
    MANIFEST.write_text(s, encoding='utf-8')


def patch_version():
    s = MAIN.read_text(encoding='utf-8')
    s = s.replace('Android R17 TEST', 'Android R18 TEST')
    s = s.replace('Aiuto R17', 'Aiuto R18')
    s = s.replace('R17: struttura presente', 'R18: struttura presente')
    s = s.replace('R17 mantiene lo stesso pacchetto Android', 'R18 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R16', 'Installala sopra la R17')
    MAIN.write_text(s, encoding='utf-8')

    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 17', 'versionCode 18', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r17-test'", "versionName '1.0.0-android-r18-test'", 'versionName')
    GRADLE.write_text(g, encoding='utf-8')


patch_cloud()
patch_manifest()
patch_version()
print('R18 secure resumable authenticated import patch applied')
