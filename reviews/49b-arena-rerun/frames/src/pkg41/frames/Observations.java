package pkg41.frames;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Base64;

/** Development observations only; GUI labels/bounds never invoke game behavior. */
public final class Observations {
    private static final String UI = System.getProperty("pkg49b.ui");
    private static final String CREATION = System.getProperty("pkg49b.creation_marks");
    private static String previous;
    private Observations() { }

    public static void screen() {
        if (UI == null) return;
        var client = Minecraft.getInstance();
        var screen = client.gui.screen();
        var window = client.getWindow();
        var text = new StringBuilder().append(window.getGuiScaledWidth()).append('\t')
                .append(window.getGuiScaledHeight()).append('\t')
                .append(screen == null ? "world" : screen.getClass().getName()).append('\n');
        if (screen != null) for (var child : screen.children()) {
            if (child instanceof Button button) {
                text.append(Base64.getEncoder().encodeToString(button.getMessage().getString().getBytes(StandardCharsets.UTF_8)))
                        .append('\t').append(button.getX()).append('\t').append(button.getY())
                        .append('\t').append(button.getWidth()).append('\t').append(button.getHeight())
                        .append('\t').append(button.active).append('\t').append(button.visible).append('\n');
            }
        }
        String value = text.toString();
        if (value.equals(previous)) return;
        try {
            var path = Path.of(UI);
            var temp = path.resolveSibling(path.getFileName()+".tmp");
            Files.writeString(temp, value);
            Files.move(temp, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            Files.writeString(path.resolveSibling("ui-history.txt"), System.nanoTime()+"\n"+value+"\n",
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
            previous = value;
        } catch (IOException error) { throw new IllegalStateException("rig GUI observation failed", error); }
    }

    public static void creation(String kind) {
        if (CREATION == null) return;
        try {
            Files.writeString(Path.of(CREATION), kind+"\t"+System.nanoTime()+"\n",
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException error) { throw new IllegalStateException("rig creation observation failed", error); }
    }
}
