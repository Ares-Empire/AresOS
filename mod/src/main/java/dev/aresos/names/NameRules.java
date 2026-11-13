package dev.aresos.names;

import dev.aresos.config.AppDefinition;
import dev.aresos.config.MyApps;

import java.text.Normalizer;
import java.util.*;

/** HUB.md 4.1–4.4. No game state: the caller supplies commands and names already held. */
public final class NameRules {
    public static final Set<String> OWN = Set.of("aresos", "home", "go", "open", "apps");
    private static final Set<String> MAKERS = Set.of("google", "microsoft", "mozilla", "kde", "gnome", "gnu",
            "apache", "adobe", "jetbrains", "libreoffice", "bazzite", "system", "the");
    private static final Set<String> FILLERS = Set.of("client", "launcher", "app", "apps", "application", "desktop",
            "for", "linux", "browser", "web", "and", "of", "media", "player", "game", "games", "stable", "beta",
            "edition", "configuration", "config", "tool", "tools", "manager", "viewer", "editor", "studio");
    private static final Set<String> WRAPPERS = Set.of("flatpak", "env", "sh", "bash", "python", "python3", "pkexec",
            "sudo", "xdg-open", "xdg-terminal-exec", "gtk-launch");
    private static final Set<String> ID_ENDINGS = Set.of("app", "desktop", "client", "launcher", "gtk", "qt", "gui", "main");
    private record Nickname(Set<String> matches, String name) { }
    private static final List<Nickname> NICKNAMES = List.of(
            new Nickname(Set.of("com.discordapp.discord", "discord"), "dc"),
            new Nickname(Set.of("org.mozilla.firefox", "firefox"), "ff"),
            new Nickname(Set.of("com.visualstudio.code", "code"), "vscode"),
            new Nickname(Set.of("org.telegram.desktop"), "tg"),
            new Nickname(Set.of("org.qbittorrent.qbittorrent"), "qbit"),
            new Nickname(Set.of("com.mojang.minecraft", "minecraft-launcher"), "mc"),
            new Nickname(Set.of("org.kde.dolphin"), "files"),
            new Nickname(Set.of("org.mozilla.thunderbird"), "mail"));

    /** wmClass is optional; shell/1.1 does not supply it. exec may also be a Flatpak ID. */
    public record Program(String id, String name, String exec, String desktopId, String wmClass) { }

    private NameRules() { }

    /** Saved main name, shared by the Apps screen, gate signs and the future hub builder. */
    public static String mainName(AppDefinition app) { return app.names().isEmpty() ? "" : app.names().getFirst(); }

    public static Program of(AppDefinition app) {
        var system = app.system();
        return new Program(app.id(), app.name(), system != null && system.execName() != null ? system.execName()
                : app.command().isEmpty() ? null : app.command().getFirst(),
                system == null ? null : system.desktopId(), null);
    }

    public static String squeeze(String value) {
        return Normalizer.normalize(value == null ? "" : value.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "").replaceAll("[^a-z0-9]", "");
    }

    public static boolean valid(String name) { return name != null && name.matches("[a-z][a-z0-9]{1,15}"); }
    public static boolean reserved(String name, Set<String> commands) { return OWN.contains(name) || commands.contains(name); }
    public static boolean free(String name, Set<String> held, Set<String> commands) {
        return valid(name) && !held.contains(name) && !reserved(name, commands);
    }

    public static List<String> words(String name) {
        String unbracketed = name;
        String previous;
        do {
            previous = unbracketed;
            unbracketed = unbracketed.replaceAll("\\([^()]*\\)|\\[[^\\[\\]]*\\]|\\{[^{}]*\\}", " ");
        } while (!previous.equals(unbracketed));
        var words = new ArrayList<>(Arrays.stream(unbracketed.split("[\\s_/:\\-]+"))
                .filter(word -> !word.matches("[0-9]+"))
                .map(NameRules::squeeze).filter(word -> !word.isEmpty()).toList());
        while (words.size() > 1 && MAKERS.contains(words.getFirst())) words.removeFirst();
        var telling = words.stream().filter(word -> !FILLERS.contains(word)).toList();
        return telling.isEmpty() ? List.copyOf(words) : telling;
    }

    /** Clean before squeezing: hyphens and dots are needed to recognise prefixes and suffixes. */
    public static String cleanProgram(String program) {
        if (program == null) return "";
        String name = program.replace('\\', '/');
        name = name.substring(name.lastIndexOf('/') + 1).toLowerCase(Locale.ROOT);
        name = name.replaceFirst("\\.(appimage|sh|py|bin|exe|x86_64)$", "");
        if (WRAPPERS.contains(name)) return "";
        String previous;
        do {
            previous = name;
            name = name.replaceFirst("^(bazzite-|gnome-|kde-|plasma-|org\\.)", "");
        } while (!previous.equals(name));
        name = name.replaceFirst("-(stable|bin|gtk|qt|gui|app|launcher|wrapper|desktop|client)$", "");
        name = name.replaceFirst("[0-9]+$", "");
        int hyphen = name.indexOf('-');
        if (hyphen > 0 && MAKERS.contains(name.substring(0, hyphen))) name = name.substring(hyphen + 1);
        return squeeze(name);
    }

    public static String cleanDesktop(String id) {
        if (id == null) return "";
        String[] parts = id.toLowerCase(Locale.ROOT).split("\\.");
        String last = parts[parts.length - 1];
        return cleanProgram(parts.length >= 3 ? parts.length >= 4 && ID_ENDINGS.contains(last)
                ? parts[parts.length - 2] : last : id);
    }

    public static List<String> candidates(Program app) {
        var words = words(app.name());
        String exec = cleanProgram(app.exec()), desktop = cleanDesktop(app.desktopId());
        var result = new LinkedHashSet<String>();
        if (words.size() == 1) result.add(words.getFirst());
        if (exec.length() >= 2 && exec.length() <= 12) result.add(exec);
        if (desktop.length() >= 2 && desktop.length() <= 12) result.add(desktop);
        if (!words.isEmpty()) result.add(words.getFirst());
        for (String candidate : List.of(exec, desktop, squeeze(app.name())))
            if (!candidate.isEmpty()) result.add(cut(candidate, 16));
        return List.copyOf(result);
    }

    public static String main(Program app, Set<String> held, Set<String> commands) {
        var candidates = candidates(app);
        for (String candidate : candidates) if (free(candidate, held, commands)) return candidate;
        // 4.2's last rule numbers the first candidate. Judge it with its number: "a" alone is too short, "a2" is
        // valid. "app" only when no candidate can take a number (it starts with a digit).
        String base = candidates.stream().filter(candidate -> valid(cut(candidate, 15) + "2")).findFirst().orElse("app");
        for (long number = 2; ; number++) {
            String suffix = Long.toString(number), candidate = cut(base, 16 - suffix.length()) + suffix;
            if (free(candidate, held, commands)) return candidate;
        }
    }

    public static List<String> assign(Program app, Set<String> held, Set<String> commands) {
        var result = new ArrayList<String>();
        var used = new HashSet<>(held);
        String main = main(app, used, commands);
        result.add(main); used.add(main);
        var matches = new HashSet<>(List.of(lower(app.exec()), lower(app.desktopId()), lower(app.wmClass()),
                cleanProgram(app.exec()), squeeze(app.name())));
        for (var row : NICKNAMES) if (!Collections.disjoint(row.matches(), matches)) {
            add(row.name(), result, used, commands);
            break;
        }
        if (app.id().equals("terminal")) add("term", result, used, commands);
        if (MyApps.STARTERS.contains(app.id())) add(app.id(), result, used, commands);
        return List.copyOf(result);
    }

    /** Stable sort: starters first, preserving joining order within both sets. */
    public static List<Program> order(List<Program> programs) {
        return programs.stream().sorted(Comparator.comparing(app -> !MyApps.STARTERS.contains(app.id()))).toList();
    }

    private static void add(String name, List<String> result, Set<String> used, Set<String> commands) {
        if (free(name, used, commands)) { result.add(name); used.add(name); }
    }
    private static String lower(String value) { return value == null ? "" : value.toLowerCase(Locale.ROOT); }
    private static String cut(String value, int limit) { return value.substring(0, Math.min(value.length(), limit)); }
}
