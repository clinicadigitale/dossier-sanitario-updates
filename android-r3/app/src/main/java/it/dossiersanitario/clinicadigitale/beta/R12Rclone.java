package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class R12Rclone {
    private R12Rclone() {}

    public static File configFile(Context context) {
        File dir = new File(context.getFilesDir(), "r12_cloud");
        if (!dir.exists()) dir.mkdirs();
        return new File(dir, "rclone.conf");
    }

    public static String importRemoteSection(Context context, String section) throws Exception {
        String clean = String.valueOf(section == null ? "" : section).trim();
        Matcher m = Pattern.compile("(?m)^\\s*\\[([^]\\r\\n]+)]").matcher(clean);
        if (!m.find()) throw new Exception("Configurazione cloud familiare non riconosciuta.");
        String remoteName = m.group(1).trim();
        if (remoteName.isEmpty()) throw new Exception("Nome del collegamento cloud non valido.");
        try (FileOutputStream out = new FileOutputStream(configFile(context), false)) {
            out.write((clean + "\n").getBytes(StandardCharsets.UTF_8));
        }
        return remoteName;
    }

    public static String createMegaRemote(Context context, String email, String password) throws Exception {
        String remoteName = "clinica_mobile";
        String obscured = run(context, list("obscure", password)).trim();
        if (obscured.isEmpty()) throw new Exception("Protezione credenziali MEGA non riuscita.");
        String section = "[" + remoteName + "]\n" +
                "type = mega\n" +
                "user = " + String.valueOf(email).trim() + "\n" +
                "pass = " + obscured + "\n";
        importRemoteSection(context, section);
        run(context, list("lsd", remoteName + ":", "--max-depth", "1"));
        return remoteName;
    }

    public static String run(Context context, List<String> args) throws Exception {
        File exe = new File(context.getApplicationInfo().nativeLibraryDir, "librclone.so");
        if (!exe.isFile()) throw new Exception("Connettore cloud Android non disponibile in questa build.");
        List<String> command = new ArrayList<>();
        command.add(exe.getAbsolutePath());
        command.addAll(args);
        boolean hasConfig = false;
        for (String arg : args) if ("--config".equals(arg)) hasConfig = true;
        if (!hasConfig && !args.isEmpty() && !"obscure".equals(args.get(0))) {
            command.add("--config");
            command.add(configFile(context).getAbsolutePath());
        }
        command.add("--log-level");
        command.add("ERROR");
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        builder.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath());
        builder.environment().put("HOME", context.getFilesDir().getAbsolutePath());
        Process process = builder.start();
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) output.append(line).append('\n');
        }
        boolean finished = process.waitFor(15, TimeUnit.MINUTES);
        if (!finished) {
            process.destroyForcibly();
            throw new Exception("Operazione cloud scaduta.");
        }
        if (process.exitValue() != 0) {
            String message = output.toString().trim();
            if (message.length() > 700) message = message.substring(message.length() - 700);
            throw new Exception(message.isEmpty() ? "Operazione cloud non riuscita." : message);
        }
        return output.toString();
    }

    public static JSONArray lsJson(Context context, String remote, boolean recursive) throws Exception {
        List<String> args = list("lsjson", remote, "--files-only");
        if (recursive) args.add("--recursive");
        String raw = run(context, args).trim();
        return raw.isEmpty() ? new JSONArray() : new JSONArray(raw);
    }

    public static JSONObject stat(Context context, String remote) throws Exception {
        String raw = run(context, list("lsjson", remote, "--stat")).trim();
        return raw.isEmpty() ? new JSONObject() : new JSONObject(raw);
    }

    public static boolean exists(Context context, String remote) {
        try {
            stat(context, remote);
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    public static void mkdir(Context context, String remote) throws Exception {
        run(context, list("mkdir", remote));
    }

    public static void copyFromRemote(Context context, String remote, File local) throws Exception {
        File parent = local.getParentFile();
        if (parent != null && !parent.exists()) parent.mkdirs();
        run(context, list("copyto", remote, local.getAbsolutePath(), "--retries", "3", "--low-level-retries", "5"));
        if (!local.isFile()) throw new Exception("Download cloud non completato.");
    }

    public static void copyToRemote(Context context, File local, String remote) throws Exception {
        if (!local.isFile()) throw new Exception("File locale da sincronizzare non disponibile.");
        run(context, list("copyto", local.getAbsolutePath(), remote, "--retries", "3", "--low-level-retries", "5"));
    }

    public static void deleteRemote(Context context, String remote) throws Exception {
        run(context, list("deletefile", remote));
    }

    public static List<String> list(String... values) {
        ArrayList<String> out = new ArrayList<>();
        java.util.Collections.addAll(out, values);
        return out;
    }

    public static String cleanPath(String value) {
        String text = String.valueOf(value == null ? "" : value).replace('\\', '/').trim();
        while (text.startsWith("/")) text = text.substring(1);
        while (text.endsWith("/")) text = text.substring(0, text.length() - 1);
        return text.isEmpty() ? "Dossier Sanitario Locale" : text;
    }

    public static String safePart(String value) {
        String out = String.valueOf(value == null ? "" : value).replaceAll("[^A-Za-z0-9._-]+", "_");
        out = out.replaceAll("^_+|_+$", "");
        return out.isEmpty() ? "device" : out.toLowerCase(Locale.ROOT);
    }
}
