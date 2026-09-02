package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.work.Worker;
import androidx.work.WorkerParameters;

public final class R12SyncWorker extends Worker {
    private static final String PREFS = "clinica_android_beta";

    public R12SyncWorker(Context context, WorkerParameters params) {
        super(context, params);
    }

    @Override public Result doWork() {
        SharedPreferences prefs = getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (!R12CloudManager.configured(prefs)) return Result.success();
        try {
            R12CloudManager.syncNow(getApplicationContext(), prefs, true);
            return Result.success();
        } catch (Exception error) {
            return Result.retry();
        }
    }
}
