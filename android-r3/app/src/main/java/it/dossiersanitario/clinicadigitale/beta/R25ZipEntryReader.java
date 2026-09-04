package it.dossiersanitario.clinicadigitale.beta;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/** Reads the current ZIP entry without closing the caller-owned ZipInputStream. */
final class R25ZipEntryReader {
    private R25ZipEntryReader() {}

    static byte[] readEntry(InputStream in) throws Exception {
        if (in == null) throw new Exception("Stream archivio non disponibile.");
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[65536];
        int n;
        while ((n = in.read(buffer)) >= 0) {
            if (n > 0) out.write(buffer, 0, n);
        }
        return out.toByteArray();
    }
}
