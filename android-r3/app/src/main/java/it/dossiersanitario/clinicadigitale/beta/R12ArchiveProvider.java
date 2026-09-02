package it.dossiersanitario.clinicadigitale.beta;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;
import java.net.URLConnection;

public final class R12ArchiveProvider extends ContentProvider {
    @Override public boolean onCreate() { return getContext() != null; }

    private File resolve(Uri uri) throws FileNotFoundException {
        if (getContext() == null) throw new FileNotFoundException("Contesto non disponibile");
        String name = uri.getLastPathSegment();
        if (name == null || !name.matches("[A-Za-z0-9._-]+")) throw new FileNotFoundException("Nome file non valido");
        File dir = new File(getContext().getCacheDir(), "r12_view");
        File file = new File(dir, name);
        try {
            String base = dir.getCanonicalPath() + File.separator;
            if (!file.getCanonicalPath().startsWith(base)) throw new FileNotFoundException("Percorso non valido");
        } catch (Exception e) { throw new FileNotFoundException("Percorso non valido"); }
        if (!file.isFile()) throw new FileNotFoundException("File non disponibile");
        return file;
    }

    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        return ParcelFileDescriptor.open(resolve(uri), ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override public String getType(Uri uri) {
        try {
            String type = URLConnection.guessContentTypeFromName(resolve(uri).getName());
            return type == null ? "application/octet-stream" : type;
        } catch (Exception e) { return "application/octet-stream"; }
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        try {
            File f = resolve(uri);
            MatrixCursor c = new MatrixCursor(new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE});
            c.addRow(new Object[]{f.getName(), f.length()});
            return c;
        } catch (Exception e) { return null; }
    }

    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { try { return resolve(uri).delete() ? 1 : 0; } catch (Exception e) { return 0; } }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) { throw new UnsupportedOperationException(); }
}
