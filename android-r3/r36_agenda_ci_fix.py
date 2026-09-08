from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
s = MAIN.read_text(encoding='utf-8')
sig = '    private void renderAgenda() {'
start = s.find(sig)
if start < 0:
    raise SystemExit('R36 agenda fix: renderAgenda missing')
brace = s.find('{', start)
depth = 0
end = -1
for i in range(brace, len(s)):
    if s[i] == '{': depth += 1
    elif s[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
if end < 0:
    raise SystemExit('R36 agenda fix: renderAgenda unclosed')
block = s[start:end]

if 'Apri documento originale' not in block:
    candidates = [
        '            Button edit = button("Modifica appuntamento");',
        '            Button edit=button("Modifica appuntamento");',
    ]
    marker = next((m for m in candidates if m in block), None)
    if marker is None:
        raise SystemExit('R36 agenda fix: edit marker missing in renderAgenda')
    insertion = '''            JSONObject sourceDoc = r36AgendaSourceDocument(row);\n            if (sourceDoc != null) {\n                Button original = button("Apri documento originale");\n                original.setOnClickListener(v -> R27ExactWindows.openDocument(this, sourceDoc));\n                c.addView(original, matchWrapTop(8));\n            }\n'''
    block = block.replace(marker, insertion + marker, 1)
    s = s[:start] + block + s[end:]

# Hard local gate on the exact method, not merely on a global string.
start = s.find(sig)
brace = s.find('{', start)
depth = 0
end = -1
for i in range(brace, len(s)):
    if s[i] == '{': depth += 1
    elif s[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
final_block = s[start:end]
if 'Apri documento originale' not in final_block or 'r36AgendaSourceDocument' not in final_block:
    raise SystemExit('R36 agenda fix: source-document button not inside renderAgenda')
MAIN.write_text(s, encoding='utf-8')
print('R36 agenda source-document button verified inside renderAgenda')
