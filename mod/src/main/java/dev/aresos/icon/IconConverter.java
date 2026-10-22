package dev.aresos.icon;

import java.awt.image.BufferedImage;

/** The style boundary: an AI converter can replace this without changing discovery or caching. */
public interface IconConverter {
    String version();
    BufferedImage convert(BufferedImage source);
}
