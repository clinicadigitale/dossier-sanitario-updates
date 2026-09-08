package it.dossiersanitario.clinicadigitale.beta;

import android.app.Activity;
import android.content.Context;
import android.hardware.biometrics.BiometricManager;
import android.hardware.biometrics.BiometricPrompt;
import android.os.CancellationSignal;
import android.widget.Toast;

import java.util.concurrent.atomic.AtomicBoolean;

/** Biometric second-factor bridge using the biometric enrollment already configured on Android. */
final class R34BiometricAuth {
    interface Callback {
        void onAuthenticated();
        void onUseTotp();
    }

    private R34BiometricAuth() {}

    static boolean available(Context context) {
        if (context == null) return false;
        try {
            BiometricManager manager = (BiometricManager) context.getSystemService(Context.BIOMETRIC_SERVICE);
            return manager != null && manager.canAuthenticate() == BiometricManager.BIOMETRIC_SUCCESS;
        } catch (Throwable ignored) {
            return false;
        }
    }

    static void authenticate(Activity activity, Callback callback) {
        if (activity == null || callback == null) return;
        if (!available(activity)) {
            Toast.makeText(activity, "Biometria non disponibile o non configurata su questo dispositivo", Toast.LENGTH_LONG).show();
            callback.onUseTotp();
            return;
        }

        AtomicBoolean fallbackUsed = new AtomicBoolean(false);
        BiometricPrompt prompt = new BiometricPrompt.Builder(activity)
                .setTitle("Verifica biometrica")
                .setSubtitle("Usa l'impronta digitale o la biometria configurata sul dispositivo")
                .setDescription("La verifica resta locale al dispositivo e non viene inviata al Dossier o al cloud.")
                .setNegativeButton("Usa codice TOTP", activity.getMainExecutor(), (dialog, which) -> {
                    if (fallbackUsed.compareAndSet(false, true)) callback.onUseTotp();
                })
                .build();

        CancellationSignal cancel = new CancellationSignal();
        prompt.authenticate(cancel, activity.getMainExecutor(), new BiometricPrompt.AuthenticationCallback() {
            @Override public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                if (fallbackUsed.compareAndSet(false, true)) callback.onAuthenticated();
            }

            @Override public void onAuthenticationFailed() {
                Toast.makeText(activity, "Biometria non riconosciuta", Toast.LENGTH_SHORT).show();
            }

            @Override public void onAuthenticationError(int errorCode, CharSequence errString) {
                if (fallbackUsed.get()) return;
                if (errorCode == BiometricPrompt.BIOMETRIC_ERROR_USER_CANCELED
                        || errorCode == BiometricPrompt.BIOMETRIC_ERROR_CANCELED) {
                    return;
                }
                Toast.makeText(activity, "Verifica biometrica non disponibile", Toast.LENGTH_LONG).show();
            }
        });
    }
}
