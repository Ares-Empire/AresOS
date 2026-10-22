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
    public static Set<String> generate(Path pack, List<AppDefinition> apps, IconConverter converter) throws IOException {
        var generated = new HashSet<String>();
        for (var app : apps) {
            Path texture = pack.resolve("assets/aresos/textures/item/apps/" + app.id() + ".png");
            Path stamp = pack.resolve("cache/" + app.id() + ".sha256");
            Path item = pack.resolve("assets/aresos/items/apps/" + app.id() + ".json");
            Path model = pack.resolve("assets/aresos/models/item/apps/" + app.id() + ".json");
            boolean success = false;
            if (app.icon() != null) try {
                byte[] bytes = Files.readAllBytes(Path.of(app.icon()));
                String fingerprint = WindowsAppCatalogue.hash(bytes) + ":" + converter.version();
                if (!Files.exists(texture) || !Files.exists(item) || !Files.exists(model) || !Files.exists(stamp)
                        || !Files.readString(stamp).equals(fingerprint)) {
                    var source = ImageIO.read(new ByteArrayInputStream(bytes));
                    if (source == null) throw new IOException("Unsupported icon image");
                    var output = new ByteArrayOutputStream(); ImageIO.write(converter.convert(source), "PNG", output);
                    atomic(texture, output.toByteArray());
                    atomic(item, ("{\"model\":{\"type\":\"minecraft:model\",\"model\":\"aresos:item/apps/" + app.id() + "\"}}").getBytes(StandardCharsets.UTF_8));
                    atomic(model, ("{\"parent\":\"minecraft:item/generated\",\"textures\":{\"layer0\":\"aresos:item/apps/" + app.id() + "\"}}").getBytes(StandardCharsets.UTF_8));
                    atomic(stamp, fingerprint.getBytes(StandardCharsets.UTF_8));
                }
                generated.add(app.id()); success = true;
            } catch (IOException | RuntimeException error) {
                System.getLogger("aresos").log(System.Logger.Level.WARNING, "Cannot read icon for " + app.id() + "; using " + app.look());
            }
            if (!success) { Files.deleteIfExists(item); Files.deleteIfExists(model); Files.deleteIfExists(texture); Files.deleteIfExists(stamp); }
        }
        return Set.copyOf(generated);
    }
    private static void atomic(Path file, byte[] bytes) throws IOException {
        Files.createDirectories(file.getParent());
        Path temporary = Files.createTempFile(file.getParent(), "icon-", ".tmp");
        try { Files.write(temporary, bytes); Files.move(temporary, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
        finally { Files.deleteIfExists(temporary); }
    }
}
