from pathlib import Path

CHART = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java')
s = CHART.read_text(encoding='utf-8')

s = s.replace('private final List<Double> values = new ArrayList<>();', 'private final List<Double> values = new ArrayList<>();\n    private final List<String> dates = new ArrayList<>();', 1)
old = '''                double v = requestedValue(o, preferredKeys);\n                if (!Double.isNaN(v) && !Double.isInfinite(v)) values.add(v);'''
new = '''                double v = requestedValue(o, preferredKeys);\n                if (!Double.isNaN(v) && !Double.isInfinite(v)) {\n                    values.add(v);\n                    dates.add(o == null ? "" : o.optString("date", o.optString("clinicalDate", o.optString("createdAt", ""))));\n                }'''
if old not in s:
    raise SystemExit('R40 chart patch failed: ingest block missing')
s = s.replace(old, new, 1)

old_draw = '''        Path p = new Path();\n        for (int i = 0; i < values.size(); i++) {\n            float x = values.size() == 1 ? (left + right) / 2f : left + (right - left) * i / (values.size() - 1f);\n            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);\n            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);\n            canvas.drawCircle(x, y, dp(4.0f), point);\n        }'''
new_draw = '''        long[] times = dateTimes(dates);\n        long tMin = Long.MAX_VALUE, tMax = Long.MIN_VALUE;\n        for (long t : times) if (t > 0) { tMin = Math.min(tMin, t); tMax = Math.max(tMax, t); }\n        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;\n        Path p = new Path();\n        for (int i = 0; i < values.size(); i++) {\n            float x;\n            if (values.size() == 1) x = (left + right) / 2f;\n            else if (dated && times[i] > 0) x = left + (right - left) * (times[i] - tMin) / (float) (tMax - tMin);\n            else x = left + (right - left) * i / (values.size() - 1f);\n            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);\n            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);\n            canvas.drawCircle(x, y, dp(4.0f), point);\n        }\n        if (dated) {\n            String first = yearLabel(tMin), last = yearLabel(tMax);\n            canvas.drawText(first, left, bottom + dp(18), label);\n            float w = label.measureText(last);\n            canvas.drawText(last, Math.max(left, right - w), bottom + dp(18), label);\n        }'''
if old_draw not in s:
    raise SystemExit('R40 chart patch failed: draw block missing')
s = s.replace(old_draw, new_draw, 1)

helpers = r'''
    private static long[] dateTimes(List<String> dates) {
        long[] out = new long[dates == null ? 0 : dates.size()];
        java.text.SimpleDateFormat iso = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.ITALY);
        java.text.SimpleDateFormat ita = new java.text.SimpleDateFormat("dd/MM/yyyy", Locale.ITALY);
        iso.setLenient(false);
        ita.setLenient(false);
        for (int i = 0; i < out.length; i++) {
            String raw = dates.get(i) == null ? "" : dates.get(i).trim();
            String value = raw.length() >= 10 ? raw.substring(0, 10) : raw;
            try { out[i] = iso.parse(value).getTime(); continue; } catch (Exception ignored) {}
            try { out[i] = ita.parse(value).getTime(); } catch (Exception ignored) { out[i] = 0L; }
        }
        return out;
    }

    private static String yearLabel(long time) {
        return new java.text.SimpleDateFormat("yyyy", Locale.ITALY).format(new java.util.Date(time));
    }
'''
marker = '\n    private String shortNumber(double v) {'
if marker not in s:
    raise SystemExit('R40 chart patch failed: helper marker missing')
s = s.replace(marker, helpers + marker, 1)
s = s.replace('/** R38 clinical line chart:', '/** R40 clinical line chart:', 1)
CHART.write_text(s, encoding='utf-8')
print('R40 chart date axis fix applied')
