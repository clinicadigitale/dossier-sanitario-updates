from pathlib import Path
import base64
import zlib

payload = Path('android-r3/r53_payload')
encoded = ''.join((payload / f'chunk{i}.txt').read_text(encoding='utf-8').strip() for i in range(7))
source = zlib.decompress(base64.b64decode(encoded)).decode('utf-8')
exec(compile(source, 'r53_prepare_visit_search_payload.py', 'exec'))
