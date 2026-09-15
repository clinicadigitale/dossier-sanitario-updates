package it.dossiersanitario.clinicadigitale.beta;

import java.util.Locale;

final class R56StoragePolicy {
    static final long SAFETY_RESERVE_BYTES = 512L * 1024L * 1024L;

    static final class Result {
        final long requiredBytes;
        final long availableBytes;
        final long remainingBytes;
        final boolean enough;
        final boolean lowAfter;
        Result(long required, long available) {
            requiredBytes = Math.max(0L, required);
            availableBytes = Math.max(0L, available);
            remainingBytes = Math.max(0L, availableBytes - requiredBytes);
            enough = requiredBytes <= availableBytes;
            lowAfter = enough && remainingBytes < SAFETY_RESERVE_BYTES;
        }
    }

    static Result evaluate(long requiredBytes, long availableBytes) {
        return new Result(requiredBytes, availableBytes);
    }

    static String formatBytes(long bytes) {
        double b = Math.max(0L, bytes);
        if (b < 1024d) return String.format(Locale.ITALY, "%.0f B", b);
        if (b < 1024d * 1024d) return String.format(Locale.ITALY, "%.1f KB", b / 1024d);
        if (b < 1024d * 1024d * 1024d) return String.format(Locale.ITALY, "%.1f MB", b / (1024d * 1024d));
        return String.format(Locale.ITALY, "%.2f GB", b / (1024d * 1024d * 1024d));
    }

    private R56StoragePolicy() {}
}
