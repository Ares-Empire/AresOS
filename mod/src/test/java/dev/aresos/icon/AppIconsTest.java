package dev.aresos.icon;

import dev.aresos.config.AppDefinition;
import dev.aresos.config.SystemInfo;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

/** The picture the system names for a program (aresos-shell/1.1 {@code icon}) is read only within tight limits. */
class AppIconsTest {
    @TempDir Path directory;

    private static AppDefinition app(String own, String system) {
        return new AppDefinition("fixture", "Fixture", List.of(), "minecraft:paper", false, "helper", null, own)
                .withSystem(new SystemInfo("user", system, null, null, null, null, null, null));
    }

    /** A picture the test draws itself: a plain square, or noise in all four channels, which PNG cannot make small. */
    private Path png(String name, int width, int height, int colour, boolean noise) throws IOException {
        var image = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        var random = new Random(34);
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++)
            image.setRGB(x, y, noise ? random.nextInt() : colour);
        Path file = directory.resolve(name);
        assertTrue(ImageIO.write(image, "PNG", file.toFile()));
        return file;
    }

    @Test void theSystemsPictureFeedsThePixelIconAndTheOwnersOwnPathWins() throws Exception {
        Path system = png("system.png", 64, 64, 0xffcc0000, false), own = png("own.png", 64, 64, 0xff0000cc, false);
        Path pack = directory.resolve("pack"), texture = pack.resolve("assets/aresos/textures/item/apps/fixture.png");
        var converter = new PixelIconConverter();

        assertEquals(system.toString(), AppIcons.path(app(null, system.toString())));
        assertEquals(Set.of("fixture"), IconPack.generate(pack, List.of(app(null, system.toString())), converter).generated());
        assertEquals(0xffcc0000, ImageIO.read(texture.toFile()).getRGB(8, 8), "The item does not show the system's picture");

        assertEquals(own.toString(), AppIcons.path(app(own.toString(), system.toString())));
        assertTrue(IconPack.generate(pack, List.of(app(own.toString(), system.toString())), converter).changed());
        assertEquals(0xff0000cc, ImageIO.read(texture.toFile()).getRGB(8, 8), "The owner's own icon must win");

        // Neither path: no picture, and that is not an error.
        assertNull(AppIcons.path(app(null, null)));
        assertNull(AppIcons.read(app(null, null)));
        assertNull(AppIcons.read(new AppDefinition("plain", "Plain", List.of("plain"), "minecraft:paper", false)));
        var none = IconPack.generate(pack, List.of(app(null, null)), converter);
        assertTrue(none.generated().isEmpty() && none.changed() && !Files.exists(texture));
    }

    @Test void aPictureOfExactlyTheLargestSizeIsRead() throws Exception {
        Path largest = png("largest.png", AppIcons.MAX_SIDE, AppIcons.MAX_SIDE, 0xff00aa00, false);
        var picture = AppIcons.read(app(null, largest.toString()));
        assertTrue(picture.system());
        assertEquals(AppIcons.MAX_SIDE, picture.image().getWidth());
    }

    @Test void anythingButASmallPngInARegularFileIsNoPicture() throws Exception {
        Path good = png("good.png", 32, 32, 0xff00aa00, false);
        byte[] bytes = Files.readAllBytes(good);

        Path text = Files.writeString(directory.resolve("text.png"), "not a picture, whatever the name says");
        Path jpeg = directory.resolve("photo.png");
        assertTrue(ImageIO.write(new BufferedImage(32, 32, BufferedImage.TYPE_INT_RGB), "jpg", jpeg.toFile()));
        Path wide = png("wide.png", AppIcons.MAX_SIDE + 1, 1, 0xff00aa00, false);
        Path tall = png("tall.png", 1, AppIcons.MAX_SIDE + 1, 0xff00aa00, false);
        Path heavy = png("heavy.png", AppIcons.MAX_SIDE, AppIcons.MAX_SIDE, 0, true);
        assertTrue(Files.size(heavy) > AppIcons.MAX_BYTES, "The noise fixture must be over the size limit");
        Path stub = Files.write(directory.resolve("stub.png"), Arrays.copyOf(bytes, 20));
        Path folder = Files.createDirectory(directory.resolve("folder.png"));
        Path relative = Path.of("good.png");

        for (Path refused : List.of(text, jpeg, wide, tall, heavy, stub, folder, relative, directory.resolve("missing.png"))) {
            var app = app(null, refused.toString());
            assertThrows(IOException.class, () -> AppIcons.read(app), refused.getFileName() + " was read");
            var result = IconPack.generate(directory.resolve("pack-" + refused.getFileName()), List.of(app), new PixelIconConverter());
            assertTrue(result.generated().isEmpty(), refused.getFileName() + " became an icon");
        }
        assertThrows(IOException.class, () -> AppIcons.read(app(null, "bad\0path.png")));

        // A file that starts like a PNG and is broken further in: read, but it does not decode, so no icon.
        byte[] broken = bytes.clone();
        Arrays.fill(broken, 40, broken.length, (byte) 0x55);
        Path cut = Files.write(directory.resolve("cut.png"), broken);
        assertThrows(IOException.class, () -> AppIcons.read(app(null, cut.toString())).image());
        assertTrue(IconPack.generate(directory.resolve("pack-cut"), List.of(app(null, cut.toString())), new PixelIconConverter())
                .generated().isEmpty());
    }

    @Test void theOwnersOwnIconIsReadAsBefore() throws Exception {
        // His own path is his own choice: the limits are for what the system names.
        Path large = png("large.png", AppIcons.MAX_SIDE + 88, AppIcons.MAX_SIDE + 88, 0xff00aa00, false);
        var picture = AppIcons.read(app(large.toString(), null));
        assertFalse(picture.system());
        assertEquals(AppIcons.MAX_SIDE + 88, picture.image().getWidth());
        assertEquals(Set.of("fixture"), IconPack.generate(directory.resolve("pack-own"),
                List.of(app(large.toString(), null)), new PixelIconConverter()).generated());
    }

    @Test void aStuckReadIsAbandonedAndDoesNotHoldUpTheNextPicture() throws Exception {
        Path good = png("good.png", 32, 32, 0xff00aa00, false);
        var release = new CountDownLatch(1);
        var finished = new CountDownLatch(1);
        try {
            var error = assertThrows(IOException.class, () -> AppIcons.read(app(null, good.toString()),
                    Duration.ofMillis(100), () -> {
                        // A filesystem call can ignore interruption. Keep this worker stuck until the test ends.
                        try { while (true) try { release.await(); break; } catch (InterruptedException ignored) { } }
                        finally { finished.countDown(); }
                    }));
            assertTrue(error.getMessage().contains("timed out"));
            assertEquals(1, finished.getCount(), "The fixture did not leave a stuck worker behind");
            assertEquals(32, AppIcons.read(app(null, good.toString())).image().getWidth(),
                    "A later read queued behind the stuck worker");
        } finally { release.countDown(); }
        assertTrue(finished.await(5, TimeUnit.SECONDS));
    }

    @Test void aFinalSymlinkIsRefusedAlsoWhenItReplacesTheFileDuringOpen() throws Exception {
        org.junit.jupiter.api.Assumptions.assumeTrue(directory.getFileSystem().supportedFileAttributeViews().contains("unix"));
        Path target = png("target.png", 32, 32, 0xff00aa00, false);
        Path link = directory.resolve("link.png");
        Files.createSymbolicLink(link, target);
        assertThrows(IOException.class, () -> AppIcons.read(app(null, link.toString())));
        Path replaced = png("replaced.png", 32, 32, 0xff00aa00, false);
        assertThrows(IOException.class, () -> AppIcons.read(app(null, replaced.toString()), Duration.ofSeconds(2), () -> {
            try { Files.delete(replaced); Files.createSymbolicLink(replaced, target); }
            catch (IOException error) { throw new java.io.UncheckedIOException(error); }
        }));
    }

    @Test void aFifoReplacementCannotBlockLaterIconReads() throws Exception {
        org.junit.jupiter.api.Assumptions.assumeTrue(System.getProperty("os.name").equals("Linux"));
        Path replaced = png("fifo.png", 32, 32, 0xff00aa00, false);
        try {
            var error = assertThrows(IOException.class, () -> AppIcons.read(app(null, replaced.toString()),
                    Duration.ofMillis(200), () -> {
                        try {
                            Files.delete(replaced);
                            if (new ProcessBuilder("mkfifo", replaced.toString()).start().waitFor() != 0)
                                throw new AssertionError("Could not create the FIFO fixture");
                        } catch (IOException | InterruptedException failure) { throw new AssertionError(failure); }
                    }));
            assertTrue(error.getMessage().contains("timed out"), error.getMessage());
            Path next = png("next.png", 32, 32, 0xff00aa00, false);
            assertEquals(32, AppIcons.read(app(null, next.toString())).image().getWidth());
        } finally {
            // O_RDWR opens a Linux FIFO without waiting and releases the abandoned reader's open.
            try (var release = java.nio.channels.FileChannel.open(replaced,
                    java.nio.file.StandardOpenOption.READ, java.nio.file.StandardOpenOption.WRITE)) { }
        }
    }
}
