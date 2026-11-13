package dev.aresos.test;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.aresos.zone.GatePalette;

import javax.imageio.ImageIO;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * Development only (`gradlew measureBlockColours`): prints the average colour of every gate palette block's side
 * texture, read from the game's own files on the classpath, next to the number in the code. Only the numbers it
 * prints are typed into {@link GatePalette}; no texture is copied anywhere.
 */
public final class BlockColourSurvey {
    private BlockColourSurvey() { }

    public static void main(String[] args) throws IOException {
        int differing = 0;
        for (var entry : GatePalette.BLOCKS) {
            String texture = sideTexture(entry.block());
            int measured = average(texture);
            boolean same = measured == entry.rgb();
            if (!same) differing++;
            System.out.printf("%-22s %-28s measured 0x%06x  code 0x%06x  %s%n", entry.block(), texture, measured, entry.rgb(),
                    same ? "same" : "DIFFERS");
        }
        System.out.println(differing + " of " + GatePalette.BLOCKS.size() + " differ from the code");
    }

    private static JsonObject json(String path) throws IOException {
        try (var input = BlockColourSurvey.class.getResourceAsStream("/assets/minecraft/" + path)) {
            if (input == null) throw new IOException("Not in the game's files: " + path);
            return JsonParser.parseReader(new InputStreamReader(input, StandardCharsets.UTF_8)).getAsJsonObject();
        }
    }

    private static String path(String id) { return id.replaceFirst("^minecraft:", ""); }

    /** The texture a standing block shows on its sides, through its block state file and its model's parents. */
    static String sideTexture(String block) throws IOException {
        var states = json("blockstates/" + block + ".json");
        JsonObject first;
        if (states.has("variants")) {
            var variant = states.getAsJsonObject("variants").entrySet().iterator().next().getValue();
            first = variant.isJsonArray() ? variant.getAsJsonArray().get(0).getAsJsonObject() : variant.getAsJsonObject();
        } else {
            var apply = states.getAsJsonArray("multipart").get(0).getAsJsonObject().get("apply");
            first = apply.isJsonArray() ? apply.getAsJsonArray().get(0).getAsJsonObject() : apply.getAsJsonObject();
        }
        Map<String, String> textures = new HashMap<>();
        for (String model = first.get("model").getAsString(); model != null; ) {
            var file = json("models/" + path(model) + ".json");
            if (file.has("textures")) for (var texture : file.getAsJsonObject("textures").entrySet())
                textures.putIfAbsent(texture.getKey(), texture.getValue().getAsString());
            model = file.has("parent") ? file.get("parent").getAsString() : null;
        }
        for (String key : new String[]{"side", "all", "texture"}) {
            String value = textures.get(key);
            while (value != null && value.startsWith("#")) value = textures.get(value.substring(1));
            if (value != null) return path(value);
        }
        throw new IOException("No side texture found for " + block + ": " + textures);
    }

    /** Plain mean of each sRGB channel over the texture's first frame, weighted by opacity. */
    static int average(String texture) throws IOException {
        try (var input = BlockColourSurvey.class.getResourceAsStream("/assets/minecraft/textures/" + texture + ".png")) {
            if (input == null) throw new IOException("Not in the game's files: " + texture);
            var image = ImageIO.read(input);
            // An animated texture stacks its frames; the first one is the top square.
            int size = Math.min(image.getWidth(), image.getHeight());
            double r = 0, g = 0, b = 0, alpha = 0;
            for (int y = 0; y < size; y++) for (int x = 0; x < size; x++) {
                int argb = image.getRGB(x, y);
                double a = (argb >>> 24) / 255.0;
                alpha += a; r += (argb >> 16 & 255) * a; g += (argb >> 8 & 255) * a; b += (argb & 255) * a;
            }
            if (alpha == 0) throw new IOException("Texture is fully transparent: " + texture);
            return (int)Math.round(r / alpha) << 16 | (int)Math.round(g / alpha) << 8 | (int)Math.round(b / alpha);
        }
    }
}
