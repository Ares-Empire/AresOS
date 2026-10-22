package dev.aresos.zone;

import org.junit.jupiter.api.Test;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

class LogoPixelsTest {
    private static final String SYMBOLS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkl";

    @Test void fixtureMatchesFrozenBlockLayoutAndUsesSourceResolution() throws Exception {
        try (var input = getClass().getResourceAsStream("/icons/compass.png");
             var golden = getClass().getResourceAsStream("/logos/compass-layout.txt")) {
            var source = ImageIO.read(input);
            var image = LogoPixels.convert(source);
            assertEquals(32, image.width()); assertEquals(32, image.height());
            char[][] layout = new char[image.height()][image.width()];
            for (var row : layout) java.util.Arrays.fill(row, '.');
            for (var pixel : image.pixels()) {
                int index = java.util.stream.IntStream.range(0, LogoPixels.PALETTE.size())
                        .filter(i -> LogoPixels.PALETTE.get(i).block().equals(pixel.block())).findFirst().orElseThrow();
                layout[pixel.y()][pixel.x()] = SYMBOLS.charAt(index);
            }
            String actual = java.util.Arrays.stream(layout).map(String::new).collect(java.util.stream.Collectors.joining("\n")) + "\n";
            assertEquals(new String(golden.readAllBytes(), StandardCharsets.UTF_8).replace("\r\n", "\n"), actual);
            assertEquals(image, LogoPixels.convert(source));
        }
    }

    @Test void transparentPixelsPlaceNothingAndDownsamplingPreservesAspectAndAlpha() {
        var source = new BufferedImage(64, 32, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < 32; y++) for (int x = 32; x < 64; x++) source.setRGB(x, y, 0xff8e2020);
        source.setRGB(0, 0, 0x00ffffff);
        var image = LogoPixels.convert(source);
        assertEquals(32, image.width()); assertEquals(16, image.height());
        assertEquals(256, image.pixels().size());
        assertTrue(image.pixels().stream().allMatch(p -> p.x() >= 16 && p.block().equals("red_concrete")));
        assertTrue(LogoPixels.convert(new BufferedImage(1, 1, BufferedImage.TYPE_INT_ARGB)).pixels().isEmpty());
        for (var color : LogoPixels.PALETTE) assertEquals(color.block(), LogoPixels.nearest(color.rgb()));
    }
}
