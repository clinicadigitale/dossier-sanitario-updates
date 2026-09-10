from pathlib import Path

TEST=Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
p=TEST/'R45YearAxisProgressiveBackupTest.java'
s=p.read_text(encoding='utf-8')
marker='@Test public void decryptProgressUsesStreamingCipherBytes()'
start=s.find(marker)
if start<0: raise SystemExit('R48 final compat missing decryptProgressUsesStreamingCipherBytes')
line=s.rfind('\n',0,start)+1
brace=s.find('{',start); depth=0; end=-1
for i in range(brace,len(s)):
    if s[i]=='{': depth+=1
    elif s[i]=='}':
        depth-=1
        if depth==0:
            end=i+1; break
if end<0: raise SystemExit('R48 final compat unclosed method')
repl='''    @Test public void decryptProgressUsesStreamingCipherBytes() throws Exception {\n        String decryptor = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R22StreamingDsl5.java");\n        assertTrue(decryptor.contains("GCMBlockCipher"));\n        assertTrue(decryptor.contains("cipher.processBytes"));\n        assertTrue(decryptor.contains("cipher.doFinal"));\n        assertTrue(decryptor.contains("callback.onProgress"));\n        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");\n        assertTrue(cloud.contains("R22StreamingDsl5.decryptVerified(encryptedPart, plainZip, recovery"));\n        assertTrue(cloud.contains("R46ProgressMath.importPercent(done, total)"));\n    }'''
p.write_text(s[:line]+repl+s[end:],encoding='utf-8')
print('R48 final streaming regression assertion aligned')
