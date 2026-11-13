package dev.aresos.icon;

import dev.aresos.catalogue.WindowsAppCatalogue;
import dev.aresos.config.AppDefinition;
import javax.imageio.ImageIO;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public final class IconPack {
    private IconPack() { }

    /**
     * {@code generated} are the apps that have a pixel icon in the pack now. {@code changed} says a file of the
     * pack was written or deleted by this run, so a game that already loaded the pack has to load it again.
     */
    public record Result(Set<String> generated, boolean changed) { }

    public static Result generate(Path pack, List<AppDefinition> apps, IconConverter converter) throws IOException {
        var generated = new HashSet<String>();
        boolean changed = false;
        for (var app : apps) {
            Path texture = pack.resolve("assets/aresos/textures/item/apps/" + app.id() + ".png");
            Path stamp = pack.resolve("cache/" + app.id() + ".sha256");
            Path item = pack.resolve("assets/aresos/items/apps/" + app.id() + ".json");
            Path model = pack.resolve("assets/aresos/models/item/apps/" + app.id() + ".json");
            boolean success = false;
            if (AppIcons.path(app) != null) try {
                var picture = AppIcons.read(app);
                String fingerprint = WindowsAppCatalogue.hash(picture.bytes()) + ":" + converter.version();
                if (!Files.exists(texture) || !Files.exists(item) || !Files.exists(model) || !Files.exists(stamp)
                        || !Files.readString(stamp).equals(fingerprint)) {
                    var output = new ByteArrayOutputStream(); ImageIO.write(converter.convert(picture.image()), "PNG", output);
                    // From here on files change, also when a later write fails.
                    changed = true;
                    atomic(texture, output.toByteArray());
                    atomic(item, ("{\"model\":{\"type\":\"minecraft:model\",\"model\":\"aresos:item/apps/" + app.id() + "\"}}").getBytes(StandardCharsets.UTF_8));
                    atomic(model, ("{\"parent\":\"minecraft:item/generated\",\"textures\":{\"layer0\":\"aresos:item/apps/" + app.id() + "\"}}").getBytes(StandardCharsets.UTF_8));
                    atomic(stamp, fingerprint.getBytes(StandardCharsets.UTF_8));
                }
                generated.add(app.id()); success = true;
            } catch (IOException | RuntimeException error) {
                System.getLogger("aresos").log(System.Logger.Level.WARNING, "Cannot read icon for " + app.id() + "; using " + app.look());
            }
            if (!success) {
                // No short-circuit: every one of the four must go.
                changed |= Files.deleteIfExists(item) | Files.deleteIfExists(model) | Files.deleteIfExists(texture);
                Files.deleteIfExists(stamp);
            }
        }
        return new Result(Set.copyOf(generated), changed);
    }
    private static void atomic(Path file, byte[] bytes) throws IOException {
        Files.createDirectories(file.getParent());
        Path temporary = Files.createTempFile(file.getParent(), "icon-", ".tmp");
        try { Files.write(temporary, bytes); Files.move(temporary, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
        finally { Files.deleteIfExists(temporary); }
    }
}
