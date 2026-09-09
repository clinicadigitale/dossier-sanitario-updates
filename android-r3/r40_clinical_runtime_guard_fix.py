from pathlib import Path

P = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R40ClinicalSeries.java')
s = P.read_text(encoding='utf-8')
old = '''        double low = median / 50.0;\n        double high = median * 50.0;\n        List<JSONObject> out = new ArrayList<>();\n        for (JSONObject row : source) {\n            double v = Math.abs(row.optDouble("value", Double.NaN));\n            if (!Double.isFinite(v) || v == 0.0 || v < low || v > high) continue;\n            out.add(row);\n        }'''
new = '''        List<JSONObject> out = new ArrayList<>();\n        for (JSONObject row : source) {\n            double v = Math.abs(row.optDouble("value", Double.NaN));\n            if (!keepAgainstMedian(v, median)) continue;\n            out.add(row);\n        }'''
if old not in s:
    raise SystemExit('R40 clinical guard failed: filter block missing')
s = s.replace(old, new, 1)
marker = '''    private static double parse(Object raw) {'''
helper = '''    static boolean keepAgainstMedian(double value, double median) {\n        if (!Double.isFinite(value) || !Double.isFinite(median) || median <= 0.0) return false;\n        double v = Math.abs(value);\n        return v > 0.0 && v >= median / 50.0 && v <= median * 50.0;\n    }\n\n'''
if marker not in s:
    raise SystemExit('R40 clinical guard failed: parse marker missing')
s = s.replace(marker, helper + marker, 1)
P.write_text(s, encoding='utf-8')
print('R40 clinical runtime guard applied')
