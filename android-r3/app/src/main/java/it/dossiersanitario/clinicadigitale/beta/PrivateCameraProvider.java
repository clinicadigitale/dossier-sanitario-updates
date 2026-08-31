package it.dossiersanitario.clinicadigitale.beta;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.content.UriMatcher;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

public final class PrivateCameraProvider extends ContentProvider {
    private static final int CAMERA_TEMP = 1;
    private final UriMatcher matcher = new UriMatcher(UriMatcher.NO_MATCH);

    @Override public boolean onCreate() {
        Context c = getContext();
        if (c == null) return false;
        matcher.addURI(c.getPackageName() + ".fileprovider", "camera/*", CAMERA_TEMP);
        return true;
    }

    private File resolve(Uri uri) throws FileNotFoundException {
        if (matcher.match(uri) != CAMERA_TEMP) throw new FileNotFoundException("URI non consentito");
        String name = uri.getLastPathSegment();
        if (name == null || !name.matches("capture_[0-9]+\\.jpg")) throw new FileNotFoundException("Nome non valido");
        File dir = new File(providerContext().getCacheDir(), "clinica_camera");
        File file = new File(dir, name);
        try {
            String base = dir.getCanonicalPath() + File.separator;
            if (!file.getCanonicalPath().startsWith(base)) throw new FileNotFoundException("Percorso non valido");
        } catch (IOException e) { throw new FileNotFoundException("Percorso non valido"); }
        return file;
    }

    private Context providerContext() throws FileNotFoundException {
        Context c = getContext();
        if (c == null) throw new FileNotFoundException("Contesto non disponibile");
        return c;
    }

    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        File file = resolve(uri);
        int flags = mode != null && mode.contains("w")
                ? ParcelFileDescriptor.MODE_CREATE | ParcelFileDescriptor.MODE_TRUNCATE | ParcelFileDescriptor.MODE_WRITE_ONLY
                : ParcelFileDescriptor.MODE_READ_ONLY;
        return ParcelFileDescriptor.open(file, flags);
    }

    @Override public String getType(Uri uri) { return matcher.match(uri) == CAMERA_TEMP ? "image/jpeg" : null; }

    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        try {
            File f = resolve(uri);
            MatrixCursor c = new MatrixCursor(new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE});
            c.addRow(new Object[]{f.getName(), f.exists() ? f.length() : 0L});
            return c;
        } catch (FileNotFoundException e) { return null; }
    }

    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { try { return resolve(uri).delete() ? 1 : 0; } catch (Exception e) { return 0; } }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) { throw new UnsupportedOperationException(); }
}
