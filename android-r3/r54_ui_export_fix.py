from pathlib import Path
import base64
import zlib

payload = Path('android-r3/r54_payload.txt').read_text(encoding='utf-8').strip()
source = zlib.decompress(base64.b64decode(payload)).decode('utf-8')
exec(compile(source, 'r54_ui_export_fix_payload.py', 'exec'))
