from pathlib import Path

CLOUD = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java')
s = CLOUD.read_text(encoding='utf-8')
old = '''    static boolean pendingExistingImportAvailable(String protectedState) {\n        return protectedState != null && protectedState.trim().length() > 20;\n    }\n'''
new = '''    static boolean pendingExistingImportAvailable(String associationStatus, String protectedState) {\n        return "import_pending".equals(String.valueOf(associationStatus))\n                && protectedState != null\n                && protectedState.trim().length() > 20;\n    }\n\n    static boolean pendingExistingImportAvailable(String protectedState) {\n        return protectedState != null && protectedState.trim().length() > 20;\n    }\n'''
if old not in s:
    raise SystemExit('R19 compatibility fix failed: helper marker missing')
s = s.replace(old, new, 1)
CLOUD.write_text(s, encoding='utf-8')
print('R19 regression-test helper compatibility applied')
