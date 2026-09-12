from pathlib import Path
import base64
import hashlib
import zlib

root = Path('android-r3/r54_payload')
parts = [
    (root / 'chunk0.txt').read_text(encoding='utf-8').strip(),
    (root / 'chunk1.txt').read_text(encoding='utf-8').strip(),
    (root / 'chunk2.txt').read_text(encoding='utf-8').strip(),
    (root / 'chunk3.txt').read_text(encoding='utf-8').strip(),
]
parts[2] = parts[2][:-1]
expected = [
    (2000, '833d35ed85bdce2889af9f7b9b57547ad3b117a9c2fd890b6bc85dd5f069bf96'),
    (2000, '01538c828eff8c192dcb475e2466dac9e10f3b70b9a316eeb0352b52c0ccb904'),
    (2000, '965628e8b12ff7697b9600d6243552740f2cbef63699ed8b44c3a505519dc908'),
    (1952, '1a1cce60f53564c356e1aba980528a2fde23311078e2cf9e4f0b3543f6c9709a'),
]
for i, part in enumerate(parts):
    digest = hashlib.sha256(part.encode()).hexdigest()
    print('R54_CHUNK', i, len(part), digest)
    if (len(part), digest) != expected[i]:
        raise SystemExit(f'R54 payload chunk {i} mismatch')
payload = ''.join(parts)
source = zlib.decompress(base64.b64decode(payload)).decode('utf-8')
exec(compile(source, 'r54_ui_export_fix_payload.py', 'exec'))
