package dev.aresos.catalogue;

import com.google.gson.*;
import dev.aresos.config.AppDefinition;
import dev.aresos.config.WindowsLaunchIdentity;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.regex.*;

public final class WindowsAppCatalogue implements AppCatalogue {
    private static final Pattern ENVIRONMENT_VARIABLE = Pattern.compile("%([^%]+)%");
    private final Path cache;
    private List<AppDefinition> configured = List.of();
    private final List<Path> roots;
    private final JsonArray uwpFixtures;
    private final List<String> diagnostics = new ArrayList<>();

    public WindowsAppCatalogue(Path cache) { this(cache, null, null); }
    public WindowsAppCatalogue(Path cache, List<AppDefinition> configured) {
        this(cache); this.configured = List.copyOf(configured);
    }
    /** Supplying roots and UWP records prevents any inspection of the real Start Menu/packages. */
    public WindowsAppCatalogue(Path cache, List<Path> roots, JsonArray uwpFixtures) {
        this.cache = cache.toAbsolutePath(); this.roots = roots; this.uwpFixtures = uwpFixtures;
    }
    public WindowsAppCatalogue(Path cache, List<AppDefinition> configured, List<Path> roots, JsonArray uwpFixtures) {
        this(cache, roots, uwpFixtures); this.configured = List.copyOf(configured);
    }
    public List<String> diagnostics() { return List.copyOf(diagnostics); }
    private void diagnose(String message) {
        diagnostics.add(message); System.getLogger("aresos").log(System.Logger.Level.WARNING, message);
    }
    @Override public List<AppDefinition> listApps() throws IOException {
        Files.createDirectories(cache);
        Path script = cache.resolve("discover.ps1");
        try (var input = getClass().getResourceAsStream("/aresos/windows-discovery.ps1")) {
            if (input == null) throw new IOException("Missing Windows discovery adapter");
            Files.copy(input, script, StandardCopyOption.REPLACE_EXISTING);
        }
        var request = new JsonObject();
        if (roots != null) {
            var paths = new JsonArray(); roots.forEach(path -> paths.add(path.toAbsolutePath().toString()));
            request.add("roots", paths);
            request.add("uwp", uwpFixtures == null ? new JsonArray() : uwpFixtures);
        }
        var icons = new JsonArray();
        for (var app : configured) if ("command".equals(app.type()) && !explorer(app.command())) {
            var entry = new JsonObject(); entry.addProperty("id", app.id()); entry.addProperty("path", app.command().getFirst());
            entry.addProperty("extractIcon", ownedIcon(app.icon()));
            icons.add(entry);
        }
        request.add("configuredIcons", icons);
        Path requestFile = cache.resolve("request.json"), output = cache.resolve("result.json"), errors = cache.resolve("discovery-errors.txt");
        Files.writeString(requestFile, request.toString());
        var process = new ProcessBuilder("powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                "-File", script.toString(), "-RequestFile", requestFile.toString(), "-OutputFile", output.toString())
                .redirectOutput(ProcessBuilder.Redirect.DISCARD).redirectError(errors.toFile()).start();
        try {
            if (!process.waitFor(60, TimeUnit.SECONDS)) { process.destroyForcibly(); throw new IOException("Windows app discovery timed out"); }
            if (process.exitValue() != 0) throw new IOException("Windows app discovery failed; see " + errors);
        } catch (InterruptedException error) { process.destroyForcibly(); Thread.currentThread().interrupt(); throw new IOException(error); }
        try { return decodeConfigured(JsonParser.parseString(Files.readString(output).replace("\ufeff", "")).getAsJsonArray(), cache); }
        catch (RuntimeException error) { throw new IOException("Invalid Windows discovery data", error); }
    }

    public static List<AppDefinition> decode(JsonArray records, Path cache) throws IOException {
        return new WindowsAppCatalogue(cache).decodeConfigured(records, cache);
    }
    private AppDefinition configuredApp(String id) { return configured.stream().filter(app -> app.id().equals(id)).findFirst().orElse(null); }
    List<AppDefinition> decodeConfigured(JsonArray records, Path cache) throws IOException {
        diagnostics.clear();
        var result = new LinkedHashMap<String, AppDefinition>();
        var keys = new HashSet<String>();
        var configuredTargets = new HashMap<String, String>();
        var rows = new ArrayList<JsonObject>();
        for (var element : records) {
            var row = element.getAsJsonObject();
            String kind = row.get("kind").getAsString(), key = row.get("key").getAsString();
            if (kind.equals("configured")) {
                if (!text(row, "target").isBlank()) configuredTargets.put(key, text(row, "target"));
                var old = configuredApp(key);
                if (old != null && ownedIcon(old.icon())) {
                    String icon = refreshIcon(row, cache, key);
                    result.put(key, new AppDefinition(key, old.name(), old.command(), old.look(), old.pinned(),
                            old.type(), old.url(), icon, old.launchIdentity()));
                }
                continue;
            }
            if (!(kind.equals("shortcut") || kind.equals("uwp")) || key.isBlank()) throw new IOException("Invalid discovery kind/key");
            // A common shortcut with the same relative name can still launch a different app.
            if (keys.add(rowKey(row) + ":" + command(row))) rows.add(row);
        }
        // Resolve every existing launch against all shortcuts BEFORE selecting representatives.
        var identities = new HashMap<String, WindowsLaunchIdentity>();
        for (var old : configured) {
            if (!old.type().equals("command")) continue;
            var exact = rows.stream().filter(row -> sameCommand(old.command(), command(row))).findFirst();
            WindowsLaunchIdentity identity = exact.isPresent() ? launchIdentity(exact.get())
                    : explorer(old.command()) ? old.launchIdentity()
                    : new WindowsLaunchIdentity(configuredTargets.getOrDefault(old.id(), old.command().getFirst()), old.command().subList(1, old.command().size()), "", "");
            if (identity != null) identities.put(old.id(), identity);
            else if (exact.isEmpty()) diagnose("Cannot reconcile existing Windows app " + old.id()
                    + ": original shortcut absent and no saved launch identity; keeping the entry");
        }
        var groups = new LinkedHashMap<Object, List<JsonObject>>();
        var notepad = configuredApp("notepad");
        boolean reconcileNotepad = notepad == null || defaultNotepad(notepad, rows);
        for (var row : rows) {
            var identity = launchIdentity(row);
            if (identity == null) diagnose("Incomplete Windows launch identity for " + text(row, "key") + "; keeping shortcut separate");
            Object key = reconcileNotepad && notepadAlias(identity) ? "notepad"
                    : identity == null ? rowKey(row) + ":" + command(row) : identity;
            groups.computeIfAbsent(key, ignored -> new ArrayList<>()).add(row);
        }
        var reconciled = new HashMap<String, Set<Object>>();
        for (var old : configured) {
            var identity = identities.get(old.id());
            var certain = new HashSet<Object>();
            var candidates = new HashSet<Object>();
            for (var entry : groups.entrySet()) {
                // Stale metadata must not turn a repurposed owner entry back into Notepad.
                if (old.id().equals("notepad") && !reconcileNotepad && entry.getValue().stream()
                        .anyMatch(row -> notepadAlias(launchIdentity(row)))) continue;
                if ((old.id().equals("notepad") && reconcileNotepad && entry.getKey().equals("notepad"))
                        || entry.getValue().stream().anyMatch(row -> sameCommand(old.command(), command(row))
                        || (identity != null && identity.rawArguments() != null && identity.equals(launchIdentity(row))))) {
                    certain.add(entry.getKey());
                }
                if (identity != null && entry.getValue().stream().anyMatch(row -> sameArgv(identity, launchIdentity(row))))
                    candidates.add(entry.getKey());
            }
            if (certain.isEmpty() && !candidates.isEmpty()) {
                // Parsed argv cannot distinguish shell quoting or recover raw text lost by old metadata.
                boolean safeArgv = !explorer(old.command()) && !shellArguments(identity)
                        && candidates.stream().allMatch(key -> groups.get(key).stream().allMatch(row ->
                        !text(row, "arguments").matches("(?s).*[&|<>^%!\\r\\n].*")));
                boolean emptyArguments = identity.arguments().isEmpty() && candidates.stream().allMatch(key ->
                        groups.get(key).stream().allMatch(row -> "".equals(launchIdentity(row).rawArguments())));
                if (candidates.size() == 1 && (safeArgv || emptyArguments)) certain.addAll(candidates);
                else diagnose("Ambiguous raw Windows shortcut arguments for existing app " + old.id()
                        + ": " + candidates.size() + " candidate launch groups; keeping entries separate");
            }
            reconciled.put(old.id(), certain);
        }
        for (var entry : groups.entrySet()) {
            var group = entry.getValue();
            var first = group.getFirst(); var identity = launchIdentity(first);
            var matches = configured.stream().filter(old -> reconciled.get(old.id()).contains(entry.getKey())).toList();
            if (matches.size() > 1) {
                String message = "Ambiguous Windows launch for " + text(first, "key") + ": keeping existing ids "
                        + matches.stream().map(AppDefinition::id).toList();
                diagnose(message);
            }
            if (!matches.isEmpty()) {
                for (var old : matches) {
                    var representative = group.stream().filter(row -> sameCommand(old.command(), command(row))).findFirst().orElse(first);
                    // Configured-command extraction is authoritative even when it failed.
                    String icon = result.containsKey(old.id()) ? result.get(old.id()).icon()
                            : ownedIcon(old.icon()) ? refreshIcon(representative, cache, old.id()) : old.icon();
                    result.put(old.id(), new AppDefinition(old.id(), old.name(), old.command(), old.look(), old.pinned(), old.type(), old.url(), icon,
                            explorer(old.command()) ? launchIdentity(representative) : old.launchIdentity()));
                }
            } else {
                String id = "win-" + hash(rowKey(first).getBytes(StandardCharsets.UTF_8)).substring(0, 24);
                if (entry.getKey().equals("notepad")) id = "notepad";
                // An owner may have repurposed a discovered id. Keep that entry and give the distinct launch its own id.
                int collision = 0;
                while (configuredApp(id) != null || result.containsKey(id)) {
                    id = "win-" + hash((rowKey(first) + ":" + identity + ":" + command(first) + ":" + collision++).getBytes(StandardCharsets.UTF_8)).substring(0, 24);
                }
                result.put(id, new AppDefinition(id, text(first, "name"), command(first), "minecraft:paper", false,
                        "command", null, refreshIcon(first, cache, id), identity));
            }
        }
        return List.copyOf(result.values());
    }
    private static String text(JsonObject row, String key) { return row.has(key) && !row.get(key).isJsonNull() ? row.get(key).getAsString() : ""; }
    private static String rowKey(JsonObject row) { return text(row, "kind") + ":" + WindowsLaunchIdentity.path(text(row, "key")); }
    private static WindowsLaunchIdentity launchIdentity(JsonObject row) {
        if (text(row, "kind").equals("uwp")) return new WindowsLaunchIdentity("", List.of(), "", text(row, "key"), "");
        if (text(row, "target").isBlank() && text(row, "aumid").isBlank()) return null;
        var arguments = new ArrayList<String>();
        if (row.has("argv")) for (var arg : row.getAsJsonArray("argv")) arguments.add(arg.getAsString());
        else if (!text(row, "arguments").isBlank()) return null; // Never guess an unparsed command line.
        if (!row.has("arguments") && !arguments.isEmpty()) return null;
        return new WindowsLaunchIdentity(text(row, "target"), arguments, text(row, "workingDirectory"), text(row, "aumid"), text(row, "arguments"));
    }
    private static boolean sameArgv(WindowsLaunchIdentity left, WindowsLaunchIdentity right) {
        return right != null && left.target().equals(right.target()) && left.arguments().equals(right.arguments())
                && left.workingDirectory().equals(right.workingDirectory()) && left.aumid().equals(right.aumid());
    }
    private static boolean shellArguments(WindowsLaunchIdentity identity) {
        String name = identity.target().substring(identity.target().lastIndexOf('/') + 1);
        return !identity.arguments().isEmpty() && Set.of("cmd.exe", "cmd", "powershell.exe", "powershell", "pwsh.exe", "pwsh").contains(name);
    }
    private static boolean notepadAlias(WindowsLaunchIdentity identity) {
        return identity != null && identity.arguments().isEmpty() && "".equals(identity.rawArguments())
                && identity.workingDirectory().isEmpty() && (windowsNotepadPath(identity.target())
                || identity.aumid().startsWith("microsoft.windowsnotepad_"));
    }
    private static boolean windowsNotepadPath(String value) {
        String target = normalizedFullPath(value);
        if (target.isEmpty()) return false;
        String windows = normalizedFullPath(System.getenv().getOrDefault("WINDIR",
                System.getenv().getOrDefault("SystemRoot", "C:\\Windows")));
        return target.equals(windows + "/notepad.exe") || target.equals(windows + "/system32/notepad.exe")
                || target.equals(windows + "/syswow64/notepad.exe");
    }
    private static String normalizedFullPath(String value) {
        String expanded = ENVIRONMENT_VARIABLE.matcher(value).replaceAll(match -> Matcher.quoteReplacement(
                System.getenv().entrySet().stream().filter(entry -> entry.getKey().equalsIgnoreCase(match.group(1)))
                        .map(Map.Entry::getValue).findFirst().orElse(match.group())));
        try {
            Path path = Path.of(expanded);
            return path.isAbsolute() ? WindowsLaunchIdentity.path(path.normalize().toString()) : "";
        } catch (InvalidPathException error) {
            return "";
        }
    }
    private static boolean defaultNotepad(AppDefinition app, List<JsonObject> rows) {
        if (!app.type().equals("command")) return false;
        if (app.command().size() == 1) {
            String target = app.command().getFirst();
            return target.equalsIgnoreCase("notepad.exe") || windowsNotepadPath(target);
        }
        if (!explorer(app.command())) return false;
        return WindowsLaunchIdentity.path(app.command().get(1)).startsWith("shell:appsfolder/microsoft.windowsnotepad_")
                || rows.stream().anyMatch(row -> sameCommand(app.command(), command(row)) && notepadAlias(launchIdentity(row)));
    }
    private static List<String> command(JsonObject row) {
        return List.of("explorer.exe", text(row, "kind").equals("uwp") ? "shell:AppsFolder\\" + text(row, "key") : text(row, "launch"));
    }
    private static boolean explorer(List<String> command) {
        return command.size() == 2 && (WindowsLaunchIdentity.path(command.getFirst()).equals("explorer.exe")
                || WindowsLaunchIdentity.path(command.getFirst()).endsWith("/explorer.exe"));
    }
    private static boolean sameCommand(List<String> left, List<String> right) {
        return explorer(left) && explorer(right) && WindowsLaunchIdentity.path(left.get(1)).equals(WindowsLaunchIdentity.path(right.get(1)));
    }
    private static boolean ownedIcon(String icon) {
        return icon == null || WindowsLaunchIdentity.path(icon).contains("/aresos-runtime/discovery/sources/");
    }
    private static String refreshIcon(JsonObject row, Path cache, String id) throws IOException {
        Path path = cache.toAbsolutePath().resolve("sources").resolve(id + ".png");
        if (!row.has("icon") || row.get("icon").isJsonNull()) { Files.deleteIfExists(path); return null; }
        byte[] bytes = Base64.getDecoder().decode(row.get("icon").getAsString());
        Files.createDirectories(path.getParent());
        if (!Files.exists(path) || !Arrays.equals(Files.readAllBytes(path), bytes)) Files.write(path, bytes);
        return path.toString();
    }
    public static String hash(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
}
