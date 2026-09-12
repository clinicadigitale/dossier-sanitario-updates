from pathlib import Path
import base64
import zlib

root = Path('android-r3/r54_payload')
parts = [
    (root / 'chunk0.txt').read_text(encoding='utf-8').strip(),
    (root / 'chunk1.txt').read_text(encoding='utf-8').strip(),
    (root / 'chunk2.txt').read_text(encoding='utf-8').strip(),
    (root / 'chunk3.txt').read_text(encoding='utf-8').strip(),
]
# chunk2 was uploaded with one duplicated boundary character; discard it.
payload = parts[0] + parts[1] + parts[2][:-1] + parts[3]
source = zlib.decompress(base64.b64decode(payload)).decode('utf-8')
exec(compile(source, 'r54_ui_export_fix_payload.py', 'exec'))
