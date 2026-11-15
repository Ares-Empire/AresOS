package dev.aresos.config;

import java.nio.file.Path;

/** Run only after closing the client and immediately before downgrading the mod. */
public final class RestoreLegacyApps {
    private RestoreLegacyApps() { }
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Expected apps.json path and its schema-1 or schema-2 backup path");
        var retained = AppsConfig.restoreLegacy(Path.of(args[0]), Path.of(args[1]));
        System.out.println("Restored the original apps.json. Compare later edits in " + retained + " before using the older mod.");
    }
}
