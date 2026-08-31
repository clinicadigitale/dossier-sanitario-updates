package it.dossiersanitario.clinicadigitale.beta;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Arrays;
import java.util.Comparator;

public final class MainActivity extends Activity {
    private static final int CAMERA_PERMISSION = 5101;
    private static final int CAMERA_CAPTURE = 5102;
    private static final String PREFS = "clinica_android_beta";

    private SharedPreferences prefs;
    private EditText testField;
    private TextView savedValue;
    private TextView photoCount;
    private ImageView preview;
    private File pendingCapture;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        cleanCameraTemp();
        setContentView(buildUi());
        refreshState();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(246, 249, 248));

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(18), dp(14), dp(18), dp(14));
        header.setBackgroundColor(Color.rgb(23, 138, 114));

        ImageView icon = new ImageView(this);
        icon.setImageResource(it.dossiersanitario.clinicadigitale.beta.R.drawable.ic_clinica);
        header.addView(icon, new LinearLayout.LayoutParams(dp(46), dp(46)));

        LinearLayout titleBox = new LinearLayout(this);
        titleBox.setOrientation(LinearLayout.VERTICAL);
        titleBox.setPadding(dp(12), 0, 0, 0);
        TextView kicker = text("CLINICA DIGITALE", 12, Color.WHITE, true);
        TextView title = text("Dossier Sanitario", 21, Color.WHITE, true);
        titleBox.addView(kicker);
        titleBox.addView(title);
        header.addView(titleBox, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        root.addView(header);

        ScrollView scroll = new ScrollView(this);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(dp(18), dp(20), dp(18), dp(30));

        body.addView(text("Android R3 TEST", 22, Color.rgb(32, 48, 45), true));
        TextView info = text("Prima APK installabile dedicata ai test fondamentali di persistenza e acquisizione privata dei referti.", 15, Color.rgb(72, 86, 82), false);
        info.setPadding(0, dp(6), 0, dp(16));
        body.addView(info);

        LinearLayout card1 = card();
        card1.addView(text("Persistenza dati", 18, Color.rgb(32, 48, 45), true));
        card1.addView(text("Salva una frase, poi potremo verificare che rimanga dopo disinstallazione con \"Mantieni dati\" e reinstallazione della release successiva.", 14, Color.DKGRAY, false));
        testField = new EditText(this);
        testField.setHint("Dato di prova");
        testField.setSingleLine(true);
        card1.addView(testField, matchWrap());
        Button save = button("Salva dato di prova");
        save.setOnClickListener(v -> {
            String value = testField.getText().toString().trim();
            prefs.edit().putString("test_value", value).putLong("saved_at", System.currentTimeMillis()).apply();
            refreshState();
            Toast.makeText(this, "Dato salvato nello spazio privato dell'app", Toast.LENGTH_SHORT).show();
        });
        card1.addView(save, matchWrap());
        savedValue = text("", 14, Color.rgb(20, 103, 84), true);
        savedValue.setPadding(0, dp(10), 0, 0);
        card1.addView(savedValue);
        body.addView(card1, spaced());

        LinearLayout card2 = card();
        card2.addView(text("Fotocamera referti", 18, Color.rgb(32, 48, 45), true));
        card2.addView(text("La foto viene scritta prima in una cache privata temporanea e poi spostata nell'archivio privato dell'app. Non viene inserita in Galleria, DCIM, Pictures o Download.", 14, Color.DKGRAY, false));
        Button camera = button("Fotografa un referto");
        camera.setOnClickListener(v -> requestCamera());
        card2.addView(camera, matchWrap());
        photoCount = text("", 14, Color.rgb(20, 103, 84), true);
        photoCount.setPadding(0, dp(10), 0, dp(8));
        card2.addView(photoCount);
        preview = new ImageView(this);
        preview.setAdjustViewBounds(true);
        preview.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        card2.addView(preview, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(220)));
        body.addView(card2, spaced());

        LinearLayout card3 = card();
        card3.addView(text("Vincoli di questa linea test", 18, Color.rgb(32, 48, 45), true));
        card3.addView(text("• package beta fisso tra tutte le release di test\n• nessun permesso di archiviazione generale\n• nessun accesso a contatti, SMS, telefono, posizione o microfono\n• backup automatico Android/Google disabilitato\n• dati e foto confinati nello spazio privato dell'app\n• cache privata ripulita automaticamente", 14, Color.DKGRAY, false));
        body.addView(card3, spaced());

        TextView footer = text("Build 1.0.0 Android R3 TEST", 12, Color.GRAY, false);
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(0, dp(12), 0, 0);
        body.addView(footer);

        scroll.addView(body);
        root.addView(scroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        return root;
    }

    private void requestCamera() {
        if (!getPackageManager().hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)) {
            Toast.makeText(this, "Fotocamera non disponibile su questo dispositivo", Toast.LENGTH_LONG).show();
            return;
        }
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION);
        } else {
            launchPrivateCamera();
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                launchPrivateCamera();
            } else {
                Toast.makeText(this, "Senza autorizzazione alla fotocamera non posso acquisire il referto", Toast.LENGTH_LONG).show();
            }
        }
    }

    private void launchPrivateCamera() {
        cleanCameraTemp();
        File dir = new File(getCacheDir(), "clinica_camera");
        if (!dir.exists() && !dir.mkdirs()) {
            Toast.makeText(this, "Impossibile preparare la fotocamera", Toast.LENGTH_LONG).show();
            return;
        }
        pendingCapture = new File(dir, "capture_" + System.currentTimeMillis() + ".jpg");
        Uri uri = new Uri.Builder()
                .scheme("content")
                .authority(getPackageName() + ".fileprovider")
                .appendPath("camera")
                .appendPath(pendingCapture.getName())
                .build();

        Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        intent.putExtra(MediaStore.EXTRA_OUTPUT, uri);
        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (intent.resolveActivity(getPackageManager()) == null) {
            pendingCapture = null;
            Toast.makeText(this, "Applicazione fotocamera non disponibile", Toast.LENGTH_LONG).show();
            return;
        }
        startActivityForResult(intent, CAMERA_CAPTURE);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != CAMERA_CAPTURE) return;

        File temp = pendingCapture;
        pendingCapture = null;
        if (resultCode != RESULT_OK || temp == null || !temp.exists() || temp.length() == 0) {
            if (temp != null) temp.delete();
            cleanCameraTemp();
            Toast.makeText(this, "Acquisizione annullata", Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            File target = new File(privateDocumentsDir(), "referto_foto_" + System.currentTimeMillis() + ".jpg");
            movePrivate(temp, target);
            cleanCameraTemp();
            refreshState();
            Toast.makeText(this, "Foto salvata solo nel Dossier", Toast.LENGTH_LONG).show();
        } catch (IOException e) {
            temp.delete();
            cleanCameraTemp();
            Toast.makeText(this, "Salvataggio della foto non riuscito", Toast.LENGTH_LONG).show();
        }
    }

    private void refreshState() {
        String value = prefs.getString("test_value", "");
        savedValue.setText(value.isEmpty() ? "Nessun dato di prova salvato" : "Dato conservato: " + value);

        File[] photos = privateDocumentsDir().listFiles((d, n) -> n.startsWith("referto_foto_") && n.endsWith(".jpg"));
        int count = photos == null ? 0 : photos.length;
        photoCount.setText("Foto private presenti nel Dossier: " + count);
        preview.setImageDrawable(null);
        if (photos != null && photos.length > 0) {
            Arrays.sort(photos, Comparator.comparingLong(File::lastModified).reversed());
            Bitmap bitmap = decodeScaled(photos[0], 1200, 800);
            if (bitmap != null) preview.setImageBitmap(bitmap);
        }
    }

    private File privateDocumentsDir() {
        File dir = new File(getFilesDir(), "dossier_documents");
        if (!dir.exists()) dir.mkdirs();
        return dir;
    }

    private void cleanCameraTemp() {
        File dir = new File(getCacheDir(), "clinica_camera");
        File[] files = dir.listFiles();
        if (files != null) {
            for (File f : files) f.delete();
        }
        if (dir.exists()) dir.delete();
    }

    private static void movePrivate(File source, File target) throws IOException {
        if (source.renameTo(target)) return;
        try (FileInputStream in = new FileInputStream(source); FileOutputStream out = new FileOutputStream(target)) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
            out.getFD().sync();
        }
        source.delete();
    }

    private static Bitmap decodeScaled(File file, int maxW, int maxH) {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(file.getAbsolutePath(), bounds);
        int sample = 1;
        while (bounds.outWidth / sample > maxW * 2 || bounds.outHeight / sample > maxH * 2) sample *= 2;
        BitmapFactory.Options opts = new BitmapFactory.Options();
        opts.inSampleSize = sample;
        return BitmapFactory.decodeFile(file.getAbsolutePath(), opts);
    }

    private LinearLayout card() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(16), dp(16), dp(16), dp(16));
        c.setBackgroundColor(Color.WHITE);
        c.setElevation(dp(2));
        return c;
    }

    private LinearLayout.LayoutParams spaced() {
        LinearLayout.LayoutParams p = matchWrap();
        p.setMargins(0, 0, 0, dp(16));
        return p;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private Button button(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(15);
        return b;
    }

    private TextView text(String s, int sp, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(s);
        v.setTextSize(sp);
        v.setTextColor(color);
        if (bold) v.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        v.setLineSpacing(0, 1.12f);
        return v;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
