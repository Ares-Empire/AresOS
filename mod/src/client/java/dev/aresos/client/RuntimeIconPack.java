package dev.aresos.client;

import dev.aresos.AresOs;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.Component;
import net.minecraft.server.packs.*;
import net.minecraft.server.packs.repository.*;
import java.nio.file.Files;
import java.io.IOException;
import java.util.*;

public final class RuntimeIconPack {
    private RuntimeIconPack() { }
    public static RepositorySource source() {
        return result -> {
            try {
                var path = AresOs.iconPackPath();
                Files.createDirectories(path);
                var format = SharedConstants.getCurrentVersion().packVersion(PackType.CLIENT_RESOURCES);
                String version = "[" + format.major() + "," + format.minor() + "]";
                Files.writeString(path.resolve("pack.mcmeta"), "{\"pack\":{\"description\":\"AresOS generated app icons\",\"min_format\":" + version + ",\"max_format\":" + version + "}}");
                var info = new PackLocationInfo("aresos/app-icons", Component.literal("AresOS app icons"), PackSource.BUILT_IN, Optional.empty());
                var pack = Pack.readMetaAndCreate(info, new PathPackResources.PathResourcesSupplier(path), PackType.CLIENT_RESOURCES,
                        new PackSelectionConfig(true, Pack.Position.TOP, true));
                if (pack != null) result.accept(pack);
            } catch (IOException error) { AresOs.LOGGER.error("Cannot mount generated icons", error); }
        };
    }
}
