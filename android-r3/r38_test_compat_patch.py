from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    # Intentional R38 landscape supersession only.
    s = s.replace('Math.max(dp(280), Math.min(dp(320)', 'Math.max(dp(340), Math.min(dp(420)')
    s = s.replace('screenWidth * 0.46f', 'screenWidth * 0.50f')
    s = s.replace('Math.max(dp(160), Math.min(dp(270)', 'Math.max(dp(340), Math.min(dp(420)')
    s = s.replace('screenWidth * 0.34f', 'screenWidth * 0.50f')

    # Current successor version assertions only.
    s = s.replace('versionCode 37', 'versionCode 38')
    s = s.replace("versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'",
                  "versionName '1.0.0-android-r38-graph-scale-landscape-width-test'")
    s = s.replace('versionIsR37SuccessorBuild', 'versionIsR38SuccessorBuild')
    s = s.replace('versionIsR37', 'versionIsR38SuccessorBuild')
    p.write_text(s, encoding='utf-8')
print('R38 prior regression assertions aligned only for intentional graph/landscape/version supersession')
