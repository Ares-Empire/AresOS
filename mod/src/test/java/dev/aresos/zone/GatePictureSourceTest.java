package dev.aresos.zone;

import dev.aresos.config.AppDefinition;
import dev.aresos.config.SystemInfo;
import dev.aresos.icon.AppIcons;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Where a gate's picture comes from (brief 36, step 1): the same file {@link AppIcons} reads for the app's item, so
 * a program the helper names a picture for gets its logo. Every picture here is drawn by the test.
 */
class GatePictureSourceTest {
    private static final int SIZE = GateNumbers.SIZE;
    @TempDir Path directory;

    private static AppDefinition app(String id, String own, String system, List<String> categories) {
        return new AppDefinition(id, "Fixture", List.of(), "minecraft:paper", false, "helper", null, own)
                .withSystem(new SystemInfo("system", system, categories, null, null, null, null, null));
    }

    /** Two bands, so the picture is not one block: red above, blue below, on a transparent margin. */
    private Path draw(String name, int side, int top, int bottom, String format) throws IOException {
        var image = new BufferedImage(side, side, format.equals("png") ? BufferedImage.TYPE_INT_ARGB : BufferedImage.TYPE_INT_RGB);
        for (int y = side / 8; y < side - side / 8; y++) for (int x = side / 8; x < side - side / 8; x++)
            image.setRGB(x, y, y < side / 2 ? top : bottom);
        Path file = directory.resolve(name);
        assertTrue(ImageIO.write(image, format, file.toFile()));
        return file;
    }

    private static void assertSamePicture(GatePicture expected, GatePicture actual) {
        assertEquals(expected.size(), actual.size());
        for (int v = 0; v < expected.size(); v++) for (int u = 0; u < expected.size(); u++)
            assertEquals(expected.at(u, v), actual.at(u, v), "cell " + u + ", " + v);
    }

    private static GatePicture of(Path file) throws IOException { return GatePicture.of(ImageIO.read(file.toFile()), SIZE); }

    @Test void theHelpersPictureBecomesTheLogo() throws IOException {
        // A path the helper names: absolute, a PNG within the limits, not the owner's own.
        Path picture = draw("chat.png", 128, 0xffcc2020, 0xff2040c0, "png");
        var app = app("chat", null, picture.toString(), List.of("Network", "InstantMessaging"));
        var gate = GateBuilder.picture(app, SIZE);
        assertSamePicture(of(picture), gate);
        var blocks = new HashSet<String>();
        for (int v = 0; v < SIZE; v++) for (int u = 0; u < SIZE; u++) if (gate.at(u, v) != null) blocks.add(gate.at(u, v));
        assertTrue(blocks.size() >= 2, "The drawn bands did not come through: " + blocks);
        assertFalse(blocks.contains("light_blue_concrete"), "The plain front was built although the helper named a picture");
    }

    @Test void theOwnersOwnPictureWins() throws IOException {
        Path own = draw("own.png", 64, 0xff20a040, 0xfff0f0f0, "png"), system = draw("system.png", 64, 0xffcc2020, 0xff2040c0, "png");
        assertSamePicture(of(own), GateBuilder.picture(app("chat", own.toString(), system.toString(), List.of("Network")), SIZE));
        // His own path is read as it always was: any format the game reads, any size.
        Path big = draw("own.bmp", 600, 0xff20a040, 0xfff0f0f0, "bmp");
        assertSamePicture(of(big), GateBuilder.picture(app("chat", big.toString(), null, List.of("Network")), SIZE));
    }

    @Test void withoutAUsablePictureTheFrontIsTheGroupsConcrete() throws IOException {
        // The helper's picture outside its limits: too large, or not a PNG.
        Path large = draw("large.png", AppIcons.MAX_SIDE + 1, 0xffcc2020, 0xff2040c0, "png");
        Path bitmap = draw("chat.bmp", 64, 0xffcc2020, 0xff2040c0, "bmp");
        for (var path : List.of(large, bitmap))
            assertSamePicture(GatePicture.plain("light_blue_concrete", SIZE), GateBuilder.picture(app("chat", null, path.toString(), List.of("Network")), SIZE));
        // No picture at all, or one that is missing: the group decides the colour, also for apps that are no starter.
        assertSamePicture(GatePicture.plain("red_concrete", SIZE), GateBuilder.picture(app("game", null, null, List.of("Game")), SIZE));
        assertSamePicture(GatePicture.plain("purple_concrete", SIZE),
                GateBuilder.picture(app("editor", null, directory.resolve("missing.png").toString(), List.of("Development")), SIZE));
        assertSamePicture(GatePicture.plain("yellow_concrete", SIZE), GateBuilder.picture(app("tool", null, null, null), SIZE));
        assertSamePicture(GatePicture.plain("light_blue_concrete", SIZE),
                GateBuilder.picture(new AppDefinition("browser", "Browser", List.of("browser"), "minecraft:compass", true), SIZE));
        assertEquals("yellow_concrete", GateBuilder.concrete(new AppDefinition("gate-tree", "Tall Tree", List.of("tree"), "minecraft:paper", false)));
    }

    @Test void aGateNamesTheGroupsConcreteWithoutItsNamespace() {
        assertEquals("light_blue_concrete", GatePalette.name("minecraft:light_blue_concrete"));
        assertEquals("black_concrete", GatePalette.name("black_concrete"));
        assertThrows(IllegalArgumentException.class, () -> GatePalette.name("othermod:concrete"));
        assertThrows(IllegalArgumentException.class, () -> GatePalette.name("minecraft:"));
    }
}
