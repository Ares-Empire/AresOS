package dev.aresos.hub;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.AresOs;
import dev.aresos.mode.LiveMode;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.core.UUIDUtil;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * What the mod built in a flat home, saved with the world as {@code data/aresos/hub.dat} (docs/design/HUB.md 3.5).
 * A block is the mod's only while the world still holds the recorded block at that position: one he changed in
 * Build mode is his, so nothing here is rewritten when he edits.
 */
public final class HubData extends SavedData {
    /** One block the mod placed; the block as its ID, for example "minecraft:gold_block". */
    public record Placed(BlockPos pos, String block) {
        public static final Codec<Placed> CODEC = RecordCodecBuilder.create(i -> i.group(
                BlockPos.CODEC.fieldOf("pos").forGetter(Placed::pos),
                Codec.STRING.fieldOf("block").forGetter(Placed::block)).apply(i, Placed::new));
    }

    /** The pad and the avenues, and the IDs of the four group names (text displays). */
    public record Fixed(List<Placed> blocks, List<UUID> names) {
        public static final Codec<Fixed> CODEC = RecordCodecBuilder.create(i -> i.group(
                Placed.CODEC.listOf().fieldOf("blocks").forGetter(Fixed::blocks),
                UUIDUtil.CODEC.listOf().fieldOf("names").forGetter(Fixed::names)).apply(i, Fixed::new));
    }

    private static final Codec<HubData> CODEC = RecordCodecBuilder.create(i -> i.group(
            Codec.STRING.fieldOf("look").forGetter(HubData::look),
            Codec.unboundedMap(Codec.STRING, Codec.INT).fieldOf("numbers").forGetter(HubData::numbers),
            GlobalPos.CODEC.fieldOf("home").forGetter(HubData::home),
            Fixed.CODEC.fieldOf("fixed").forGetter(HubData::fixed)).apply(i, HubData::new));
    // Only a new flat home writes this file. A default here would let a missing or unreadable record be replaced
    // by an empty one, and the mod would then no longer know its own blocks.
    private static final SavedDataType<HubData> TYPE = new SavedDataType<>(AresOs.id("hub"), () -> {
        throw new IllegalStateException("hub.dat is written only when a flat home is created");
    }, CODEC, null);

    private final String look;
    private final Map<String, Integer> numbers;
    private final GlobalPos home;
    private final Fixed fixed;
    private final Map<BlockPos, String> placed = new HashMap<>();

    public HubData(String look, Map<String, Integer> numbers, GlobalPos home, Fixed fixed) {
        this.look = look;
        this.numbers = Map.copyOf(numbers);
        this.home = home;
        this.fixed = new Fixed(List.copyOf(fixed.blocks()), List.copyOf(fixed.names()));
        for (Placed block : this.fixed.blocks()) placed.put(block.pos(), block.block());
    }

    /** The record of this save's hub, or null: not a flat home, or its record is missing or unreadable. */
    public static HubData get(MinecraftServer server) {
        return server.getDataStorage().get(TYPE);
    }

    /** Called once, when a new flat home has been built. */
    public static void store(MinecraftServer server, HubData data) {
        server.getDataStorage().set(TYPE, data);
        data.setDirty();
    }

    public String look() { return look; }
    public Map<String, Integer> numbers() { return numbers; }
    /** The origin of all hub coordinates: the block he stands in at home, and its dimension. */
    public GlobalPos home() { return home; }
    public Fixed fixed() { return fixed; }

    /** True while the block at this position is still the one the mod placed there. */
    public boolean holds(ServerLevel level, BlockPos pos) {
        String block = placed.get(pos);
        return block != null && level.dimension().equals(home.dimension())
                && block.equals(BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()).toString());
    }

    /** In Live mode he cannot break the hub's own blocks by hand. */
    public static boolean protectsFrom(ServerPlayer player, BlockPos pos) {
        if (!LiveMode.isLive(player)) return false;
        HubData hub = get(player.level().getServer());
        return hub != null && hub.holds(player.level(), pos);
    }

    /** Explosions spare the hub's own blocks, except while somebody is in Build mode, where anything may change. */
    public static boolean protectsFromExplosions(MinecraftServer server) {
        return server.getPlayerList().getPlayers().stream()
                .noneMatch(player -> player.gameMode.getGameModeForPlayer() == GameType.CREATIVE);
    }
}
