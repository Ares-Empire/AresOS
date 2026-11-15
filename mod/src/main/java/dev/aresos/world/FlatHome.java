package dev.aresos.world;

import dev.aresos.hub.FlatHub;
import dev.aresos.hub.HubData;
import dev.aresos.hub.HubLayout;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.HolderSet;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Difficulty;
import net.minecraft.world.clock.WorldClocks;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.gamerules.GameRules;
import net.minecraft.world.level.levelgen.FlatLevelSource;
import net.minecraft.world.level.levelgen.WorldDimensions;
import net.minecraft.world.level.levelgen.flat.FlatLayerInfo;
import net.minecraft.world.level.levelgen.flat.FlatLevelGeneratorSettings;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.storage.LevelData;
import net.minecraft.world.phys.Vec3;

import java.io.IOException;
import java.util.List;
import java.util.Optional;

/** The flat home (docs/design/HUB.md 2.1): its world, its rules, and what a new one gets built. */
public final class FlatHome {
    private FlatHome() { }

    /** A flat world looks the same for every seed; a fixed one keeps the save reproducible. */
    public static final long SEED = 0;
    public static final long NOON = 6000;
    /** The floor block under his feet, as the home data's site. */
    public static final NetherHome.Site SITE = new NetherHome.Site(SEED, HubLayout.HOME.getX(), HubLayout.HOME.getY() - 1,
            HubLayout.HOME.getZ(), HubLayout.HOME_YAW);

    /**
     * Bottom to top: bedrock at y -64, stone to y 59, dirt to y 62, grass at y 63. Deep ground costs nothing and
     * cannot be added later, and the surface sits at the usual Overworld height, so clouds and horizon look normal.
     */
    public static List<FlatLayerInfo> layers() {
        return List.of(new FlatLayerInfo(1, Blocks.BEDROCK), new FlatLayerInfo(123, Blocks.STONE),
                new FlatLayerInfo(3, Blocks.DIRT), new FlatLayerInfo(1, Blocks.GRASS_BLOCK));
    }

    /** A normal world's dimensions with the Overworld made flat: plains everywhere, no structures, no features. */
    public static WorldDimensions dimensions(HolderLookup.Provider registries) {
        var plains = registries.lookupOrThrow(Registries.BIOME).getOrThrow(Biomes.PLAINS);
        Optional<HolderSet<StructureSet>> noStructures = Optional.of(HolderSet.empty());
        var settings = new FlatLevelGeneratorSettings(noStructures, plains,
                FlatLevelGeneratorSettings.createLakesList(registries.lookupOrThrow(Registries.PLACED_FEATURE)))
                .withBiomeAndLayers(layers(), noStructures, plains);
        return WorldPresets.createNormalWorldDimensions(registries).replaceOverworldGenerator(registries, new FlatLevelSource(settings));
    }

    /** True for the world {@link #dimensions} creates and no other: the hub is built on nothing else. */
    public static boolean isFlatHome(ChunkGenerator generator) {
        if (!(generator instanceof FlatLevelSource flat) || !flat.settings().getBiome().is(Biomes.PLAINS)) return false;
        var expected = layers();
        var actual = flat.settings().getLayersInfo();
        if (actual.size() != expected.size()) return false;
        for (int i = 0; i < expected.size(); i++) {
            if (actual.get(i).getHeight() != expected.get(i).getHeight()
                    || !actual.get(i).getBlockState().equals(expected.get(i).getBlockState())) return false;
        }
        return true;
    }

    /** The Nether home's rules, and a world that stays at one time of day in one weather. */
    public static void applyRules(GameRules rules, MinecraftServer server) {
        NetherHome.applyRules(rules, server);
        rules.set(GameRules.ADVANCE_TIME, false, server);
        rules.set(GameRules.ADVANCE_WEATHER, false, server);
    }

    /**
     * Runs once, for a world this session created, after provisioning was claimed (NetherHome's start handler).
     * Rules, time and weather are set here and never again, so a change he makes later is kept.
     */
    static void initialize(MinecraftServer server, NetherHome.Site site) throws IOException {
        ServerLevel level = server.overworld();
        if (!site.equals(SITE)) throw new IOException("The home manifest does not describe a flat home; nothing was built");
        if (!isFlatHome(level.getChunkSource().getGenerator())) {
            throw new IOException("This save is not the flat AresOS world; nothing was built");
        }
        applyRules(server.getGameRules(), server);
        server.setDifficulty(Difficulty.NORMAL, true);
        server.clockManager().setTotalTicks(server.registryAccess().lookupOrThrow(Registries.WORLD_CLOCK).getOrThrow(WorldClocks.OVERWORLD), NOON);
        server.setWeatherParameters(0, 0, false, false);
        BlockPos home = site.floor().above();
        HubData.Fixed fixed = FlatHub.build(level, home);
        server.setRespawnData(LevelData.RespawnData.of(Level.OVERWORLD, home, HubLayout.HOME_YAW, HubLayout.HOME_PITCH));
        DesktopWorld.setEnabled(server, true);
        NetherHome.store(server, site, new NetherHome.Home(Level.OVERWORLD, Vec3.atBottomCenterOf(home), HubLayout.HOME_YAW, HubLayout.HOME_PITCH));
        HubData.store(server, new HubData(HubLayout.LOOK, HubLayout.numbers(), GlobalPos.of(Level.OVERWORLD, home), fixed));
    }
}
