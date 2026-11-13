package dev.aresos.catalogue;

import dev.aresos.config.AppDefinition;
import dev.aresos.shell.ShellClient;
import java.io.IOException;
import java.time.Duration;
import java.util.List;

/** list_apps over aresos-shell: what the OS helper lists becomes helper-type entries without any command. */
public final class LinuxAppCatalogue implements AppCatalogue {
    public static final String PROTOCOL = ShellClient.PROTOCOL;
    public static final String UNAVAILABLE = "AresOS app helper is unavailable (" + PROTOCOL + ")";
    private final ShellClient shell;
    private final Duration wait;

    /** No helper connection: fails closed. */
    public LinuxAppCatalogue() { this(null, Duration.ZERO); }

    public LinuxAppCatalogue(ShellClient shell, Duration wait) {
        this.shell = shell;
        this.wait = wait;
    }

    @Override public List<AppDefinition> listApps() throws IOException {
        if (shell == null) throw new IOException(UNAVAILABLE);
        return definitions(shell.awaitApps(wait));
    }

    /** Names come from the helper only as a fallback: merging keeps the owner's names, looks and pins. */
    public static List<AppDefinition> definitions(List<ShellClient.App> apps) {
        return apps.stream().map(app -> new AppDefinition(app.id(), app.name(), List.of(), look(app.id()), false,
                "helper", null, null)).toList();
    }

    static String look(String id) {
        return switch (id) {
            case "terminal" -> "minecraft:command_block";
            case "notepad" -> "minecraft:writable_book";
            case "browser" -> "minecraft:compass";
            default -> "minecraft:paper";
        };
    }
}
