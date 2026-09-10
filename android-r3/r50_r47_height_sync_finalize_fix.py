from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
TRANSFER = BASE / 'R47RcloneTransfer.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit('R50 missing ' + label)


def replace_block(text, signature, replacement, label):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('R50 missing ' + label)
    brace = text.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit('R50 unclosed ' + label)
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# 1) GRAPH: exact R47 renderer and data path. Only raise the plot top edge.
chart = CHART.read_text(encoding='utf-8')
old_geometry = 'float left = dp(66), right = getWidth() - dp(12), top = dp(38);'
require(chart, old_geometry, 'R47 chart geometry')
chart = chart.replace(old_geometry, 'float left = dp(66), right = getWidth() - dp(12), top = dp(20);', 1)
CHART.write_text(chart, encoding='utf-8')

# 2) SYNC TRANSPORT: keep R47 low-memory settings, but enforce a real watchdog
# while output is drained on a dedicated reader thread. This removes indefinite
# readLine stalls while retaining actual rclone percentage updates.
TRANSFER.write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class R47RcloneTransfer {
    interface Progress { void onPercent(int percent); }
    private static final Pattern PERCENT = Pattern.compile("(?:^|\\s)(\\d{1,3})%(?:,|\\s|$)");
    private static final long STALL_MS = 90_000L;
    private static final long HARD_LIMIT_MS = 20L * 60L * 1000L;
    private R47RcloneTransfer() {}

    static void download(Context context, String remote, File local, Progress progress) throws Exception {
        File parent = local.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Impossibile preparare la cartella locale.");
        File exe = new File(context.getApplicationInfo().nativeLibraryDir, "librclone.so");
        if (!exe.isFile()) throw new Exception("Connettore cloud Android non disponibile in questa build.");

        List<String> command = new ArrayList<>();
        command.add(exe.getAbsolutePath());
        command.add("copyto"); command.add(remote); command.add(local.getAbsolutePath());
        command.add("--config"); command.add(R12Rclone.configFile(context).getAbsolutePath());
        command.add("--transfers"); command.add("1");
        command.add("--checkers"); command.add("1");
        command.add("--buffer-size"); command.add("512K");
        command.add("--multi-thread-streams"); command.add("1");
        command.add("--retries"); command.add("2");
        command.add("--low-level-retries"); command.add("4");
        command.add("--contimeout"); command.add("15s");
        command.add("--timeout"); command.add("60s");
        command.add("--stats"); command.add("1s");
        command.add("--stats-one-line");
        command.add("--log-level"); command.add("NOTICE");

        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        builder.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath());
        builder.environment().put("HOME", context.getFilesDir().getAbsolutePath());
        Process process = builder.start();
        ArrayDeque<String> tail = new ArrayDeque<>();
        Object tailLock = new Object();
        AtomicLong lastActivity = new AtomicLong(System.nanoTime() / 1_000_000L);
        long started = lastActivity.get();

        Thread readerThread = new Thread(() -> {
            int last = -1;
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    lastActivity.set(System.nanoTime() / 1_000_000L);
                    synchronized (tailLock) {
                        if (tail.size() >= 30) tail.removeFirst();
                        tail.addLast(line);
                    }
                    Matcher m = PERCENT.matcher(line);
                    int seen = -1;
                    while (m.find()) seen = Integer.parseInt(m.group(1));
                    if (seen >= 0) {
                        seen = Math.max(0, Math.min(100, seen));
                        if (seen > last) {
                            last = seen;
                            if (progress != null) progress.onPercent(seen);
                        }
                    }
                }
            } catch (Exception ignored) {}
        }, "clinica-r50-rclone-output");
        readerThread.setDaemon(true);
        readerThread.start();

        while (process.isAlive()) {
            if (process.waitFor(1, TimeUnit.SECONDS)) break;
            long now = System.nanoTime() / 1_000_000L;
            if (now - lastActivity.get() > STALL_MS) {
                process.destroyForcibly();
                throw new Exception("Download cloud fermo: nessun avanzamento per 90 secondi.");
            }
            if (now - started > HARD_LIMIT_MS) {
                process.destroyForcibly();
                throw new Exception("Download cloud oltre il tempo massimo consentito.");
            }
        }
        readerThread.join(3000L);
        if (process.exitValue() != 0) {
            StringBuilder message = new StringBuilder();
            synchronized (tailLock) { for (String line : tail) message.append(line).append('\n'); }
            String text = message.toString().trim();
            if (text.length() > 900) text = text.substring(text.length() - 900);
            throw new Exception(text.isEmpty() ? "Download cloud non riuscito." : text);
        }
        if (!local.isFile() || local.length() <= 0L) throw new Exception("Download cloud non completato.");
        if (progress != null) progress.onPercent(100);
    }
}
''', encoding='utf-8')

# 3) FINAL PROMOTION: R47 could complete import/decrypt and still fail on Java
# renameTo. Preserve the atomic rename path first; if the filesystem rejects it,
# use a verified streaming-copy fallback with rollback of the previous snapshot.
cloud = CLOUD.read_text(encoding='utf-8')
replacement = r'''    private static void replaceVerified(File partial, File target) throws Exception {
        if (partial == null || !partial.isFile()) throw new Exception("Nuova copia sincronizzata non disponibile.");
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Cartella della copia sincronizzata non disponibile.");
        File old = new File(target.getParentFile(), target.getName() + ".old");
        if (old.exists()) old.delete();

        // First preserve the old R47 atomic path.
        if (target.exists()) {
            if (target.renameTo(old)) {
                if (partial.renameTo(target)) {
                    old.delete();
                    return;
                }
                old.renameTo(target);
            }
        } else if (partial.renameTo(target)) {
            return;
        }

        // Filesystems/storage layers may reject renameTo even within the same
        // directory. Fall back to bounded streaming copy, verify it, and roll
        // back the previous snapshot if anything fails.
        boolean hadTarget = target.isFile();
        if (hadTarget) r50CopyVerified(target, old);
        try {
            r50CopyVerified(partial, target);
            if (!partial.delete() && partial.exists()) partial.deleteOnExit();
            if (old.exists()) old.delete();
        } catch (Exception failure) {
            if (old.isFile()) {
                try { r50CopyVerified(old, target); } catch (Exception ignored) {}
            }
            throw new Exception("Impossibile rendere definitiva la nuova copia: " + String.valueOf(failure.getMessage()), failure);
        }
    }

    private static void r50CopyVerified(File source, File target) throws Exception {
        if (source == null || !source.isFile()) throw new Exception("File sorgente non disponibile.");
        java.security.MessageDigest sourceDigest = java.security.MessageDigest.getInstance("SHA-256");
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Cartella destinazione non disponibile.");
        try (FileInputStream in = new FileInputStream(source); FileOutputStream out = new FileOutputStream(target, false)) {
            byte[] buffer = new byte[256 * 1024];
            int n;
            while ((n = in.read(buffer)) >= 0) {
                if (n == 0) continue;
                sourceDigest.update(buffer, 0, n);
                out.write(buffer, 0, n);
            }
            out.flush();
            out.getFD().sync();
        }
        if (!target.isFile() || target.length() != source.length()) throw new Exception("Copia finale incompleta.");
        java.security.MessageDigest targetDigest = java.security.MessageDigest.getInstance("SHA-256");
        try (FileInputStream in = new FileInputStream(target)) {
            byte[] buffer = new byte[256 * 1024];
            int n;
            while ((n = in.read(buffer)) >= 0) if (n > 0) targetDigest.update(buffer, 0, n);
        }
        if (!java.util.Arrays.equals(sourceDigest.digest(), targetDigest.digest())) throw new Exception("Verifica della copia finale non riuscita.");
    }'''
cloud = replace_block(cloud, '    private static void replaceVerified(File partial,File target)throws Exception{', replacement, 'replaceVerified')
CLOUD.write_text(cloud, encoding='utf-8')

# Version only.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 50', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', 'versionName "1.0.0-android-r50-r47-height-sync-finalize-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

# Tests that specifically protect the user's requested rollback scope.
TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R50R47HeightSyncFinalizeTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R50R47HeightSyncFinalizeTest {
    private String read(String p) throws Exception { return new String(Files.readAllBytes(Paths.get(p)), StandardCharsets.UTF_8); }

    @Test public void graphIsR47ExceptRaisedTop() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(c.contains("float left = dp(66), right = getWidth() - dp(12), top = dp(20);"));
        assertTrue(c.contains("hasReference ? 154 : 116"));
        assertTrue(c.contains("R47GraphGeometry.yearStart(tMin)"));
        assertTrue(c.contains("R47GraphGeometry.yearEndExclusive(tMax)"));
    }

    @Test public void r48GraphAndProfileChangesAreAbsent() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        String e = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        assertFalse(c.contains("setMinimumHeight(dp(400))"));
        assertFalse(e.contains("documentsForProfile(SharedPreferences prefs, String profileId)"));
    }

    @Test public void syncHasRealWatchdogAndBoundedReader() throws Exception {
        String t = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R47RcloneTransfer.java");
        assertTrue(t.contains("STALL_MS = 90_000L"));
        assertTrue(t.contains("process.waitFor(1, TimeUnit.SECONDS)"));
        assertTrue(t.contains("ArrayDeque<String> tail"));
        assertTrue(t.contains("--buffer-size"));
        assertTrue(t.contains("512K"));
    }

    @Test public void finalizationHasVerifiedCopyFallbackAndRollback() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(c.contains("r50CopyVerified(partial, target)"));
        assertTrue(c.contains("r50CopyVerified(old, target)"));
        assertTrue(c.contains("SHA-256"));
        assertTrue(c.contains("out.getFD().sync()"));
    }
}
''', encoding='utf-8')

print('R50 exact R47 baseline: graph raised only; sync watchdog/finalization fixed')
