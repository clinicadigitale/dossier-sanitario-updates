package it.dossiersanitario.clinicadigitale.beta;

/** Pure graph-domain math used by R38 charts and JVM regression tests. */
final class R38GraphMath {
    static final class Domain {
        final double min;
        final double max;
        final boolean varied;
        Domain(double min, double max, boolean varied) {
            this.min = min;
            this.max = max;
            this.varied = varied;
        }
    }

    private R38GraphMath() {}

    static Domain domain(double[] values) {
        if (values == null || values.length == 0) return new Domain(0.0, 1.0, false);
        double min = Double.POSITIVE_INFINITY;
        double max = Double.NEGATIVE_INFINITY;
        for (double v : values) {
            if (!Double.isFinite(v)) continue;
            min = Math.min(min, v);
            max = Math.max(max, v);
        }
        if (!Double.isFinite(min) || !Double.isFinite(max)) return new Domain(0.0, 1.0, false);
        double span = max - min;
        if (span <= 0.0000001) {
            double half = Math.max(1.0, Math.abs(max) * 0.05);
            return new Domain(min - half, max + half, false);
        }
        double margin = Math.max(span * 0.12, Math.abs(max) * 0.002);
        return new Domain(min - margin, max + margin, true);
    }

    static float y(double value, Domain domain, float top, float bottom) {
        double span = domain.max - domain.min;
        if (!Double.isFinite(value) || span <= 0.0) return (top + bottom) / 2f;
        return bottom - (float) ((value - domain.min) / span) * (bottom - top);
    }

    static double visibleSpanRatio(double[] values) {
        Domain d = domain(values);
        if (!d.varied || values == null || values.length == 0) return 0.0;
        double min = Double.POSITIVE_INFINITY;
        double max = Double.NEGATIVE_INFINITY;
        for (double v : values) {
            if (!Double.isFinite(v)) continue;
            min = Math.min(min, v);
            max = Math.max(max, v);
        }
        if (!Double.isFinite(min) || !Double.isFinite(max)) return 0.0;
        return (max - min) / (d.max - d.min);
    }
}
