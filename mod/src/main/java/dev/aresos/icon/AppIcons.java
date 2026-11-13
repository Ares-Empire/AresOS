package dev.aresos.icon;

import dev.aresos.config.AppDefinition;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Where an app's picture comes from and how its file is read. One place, so the item's pixel icon and anything
 * else that draws an app (the logos) read the same file by the same rules.
 *
 * The owner's own {@code icon} path (on Windows: the one discovery cached) wins and is read as it always was.
 * Otherwise the path the system named is used, and that file is not trusted: it must be a regular file of at most
 * {@link #MAX_BYTES} that is a PNG of at most {@link #MAX_SIDE} pixels a side. Anything else means "no picture".
 */
public final class AppIcons {
    public static final int MAX_BYTES = 1 << 20;
    public static final int MAX_SIDE = 512;
    private static final byte[] PNG_START = {(byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n', 0, 0, 0, 13, 'I', 'H', 'D', 'R'};

    private AppIcons() { }

    /** A picture file's bytes; {@code system} says the path came from the system and the limits were applied. */
    public record Picture(byte[] bytes, boolean system) {
        /** The decoded picture. A file that does not decode is "no picture": this throws. */
        public BufferedImage image() throws IOException {
            BufferedImage image;
            try {
                image = system ? decodePng(bytes) : ImageIO.read(new ByteArrayInputStream(bytes));
            } catch (RuntimeException broken) {
                throw new IOException("Icon does not decode: " + broken.getMessage(), broken);
            }
            if (image == null) throw new IOException("Unsupported icon image");
            return image;
        }
    }

    /** The path that {@link #read} would read, or null when the app names no picture at all. */
    public static String path(AppDefinition app) {
        if (app.icon() != null) return app.icon();
        return app.system() == null ? null : app.system().icon();
    }

    /** The app's picture file, or null when it names none. Throws when the file cannot be used. */
    public static Picture read(AppDefinition app) throws IOException {
        try {
            if (app.icon() != null) return new Picture(Files.readAllBytes(Path.of(app.icon())), false);
            String path = app.system() == null ? null : app.system().icon();
            return path == null ? null : new Picture(readSystem(Path.of(path)), true);
        } catch (java.nio.file.InvalidPathException invalid) {
            throw new IOException("Icon path is not a path", invalid);
        }
    }

    private static byte[] readSystem(Path file) throws IOException {
        if (!file.isAbsolute()) throw new IOException("Icon path is not absolute");
        if (!Files.isRegularFile(file)) throw new IOException("Icon is not a regular file");
        byte[] bytes;
        // The size is checked on what is actually read: the file may grow after a look at its size.
        try (var input = Files.newInputStream(file)) { bytes = input.readNBytes(MAX_BYTES + 1); }
        if (bytes.length > MAX_BYTES) throw new IOException("Icon is larger than 1 MiB");
        if (bytes.length < 24 || !java.util.Arrays.equals(bytes, 0, PNG_START.length, PNG_START, 0, PNG_START.length))
            throw new IOException("Icon is not a PNG");
        // Width and height stand right behind the header, so an oversized picture is refused before decoding it.
        int width = java.nio.ByteBuffer.wrap(bytes, 16, 4).getInt(), height = java.nio.ByteBuffer.wrap(bytes, 20, 4).getInt();
        if (width < 1 || height < 1 || width > MAX_SIDE || height > MAX_SIDE)
            throw new IOException("Icon is larger than " + MAX_SIDE + " x " + MAX_SIDE);
        return bytes;
    }

    /** Only the PNG reader: a file that merely starts like a PNG is never handed to another format's decoder. */
    private static BufferedImage decodePng(byte[] bytes) throws IOException {
        var readers = ImageIO.getImageReadersByFormatName("png");
        if (!readers.hasNext()) throw new IOException("No PNG reader");
        var reader = readers.next();
        try (var input = ImageIO.createImageInputStream(new ByteArrayInputStream(bytes))) {
            reader.setInput(input, true, true);
            if (reader.getWidth(0) > MAX_SIDE || reader.getHeight(0) > MAX_SIDE)
                throw new IOException("Icon is larger than " + MAX_SIDE + " x " + MAX_SIDE);
            return reader.read(0);
        } finally { reader.dispose(); }
    }
}
