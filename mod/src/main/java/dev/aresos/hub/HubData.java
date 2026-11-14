package dev.aresos.hub;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.AresOs;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.AppZone;
import net.minecraft.core.BlockPos;
import net.minecraft.core.GlobalPos;
import net.minecraft.core.UUIDUtil;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * What the mod built in a flat home, saved with the world as {@code data/aresos/hub.dat} (docs/design/HUB.md 3.5):
 * the pad, the avenues and the group names ({@link Fixed}) and the town's standing logos ({@link Logo}). A changed
 * block permanently leaves the record, even if he later puts the original material back.
 *
 * <p>The town's gates are recorded here and not in the zones file, so an older mod that saves the zones file cannot
 * orphan them. Their trigger zones stay in {@code zones.dat} without a gate of their own; a zone is the town's while
 * a logo here names its ID ({@link #logoOfZone}). A mod of packages 32 to 35 rewrites this file when one of the
 * pad's blocks changes and then drops the logos: going back to such a mod and changing the pad loses the record.
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

    /**
     * A logo of the town as it stands (HUB.md 3.5): its app and place; the picture it shows, as {@link
     * dev.aresos.zone.GatePicture#hash} and the converter's version that drew it; the name and short name on its sign;
     * its zone's ID in {@code zones.dat}; and everything placed for it, in the form a gate built by hand records it:
     * every block with its ID, the ground the doormat replaced, the sign's entity ID and the grass it stands on.
     *
     * @param place     the place's name, for example {@code "N0R0"}; text, so a later mod's name never makes the
     *                  file unreadable
     * @param shortName the main short name on the sign's second line, without the slash; empty when it had none
     */
    public record Logo(String app, String place, String picture, int converter, String name, Optional<String> shortName,
                       String zone, AppZone.Gate gate) {
        public static final Codec<Logo> CODEC = RecordCodecBuilder.create(i -> i.group(
                Codec.STRING.fieldOf("app").forGetter(Logo::app),
                Codec.STRING.fieldOf("place").forGetter(Logo::place),
                Codec.STRING.fieldOf("picture").forGetter(Logo::picture),
                Codec.INT.fieldOf("converter").forGetter(Logo::converter),
                Codec.STRING.fieldOf("name").forGetter(Logo::name),
                Codec.STRING.optionalFieldOf("short_name").forGetter(Logo::shortName),
                Codec.STRING.fieldOf("zone").forGetter(Logo::zone),
                AppZone.Gate.CODEC.fieldOf("gate").forGetter(Logo::gate)).apply(i, Logo::new));

        public Logo {
            gate = new AppZone.Gate(List.copyOf(gate.placed()), List.copyOf(gate.ground()), gate.sign(), List.copyOf(gate.grass()));
        }

        /** The same logo without the blocks at these positions: he changed them, they are his now. */
        Logo without(Set<BlockPos> his) {
            return new Logo(app, place, picture, converter, name, shortName, zone, new AppZone.Gate(
                    gate.placed().stream().filter(block -> !his.contains(block.pos())).toList(), gate.ground(), gate.sign(), gate.grass()));
        }
    }

    /** The contents of {@code hub.dat}. A file written before the town (packages 32 to 35) has no logos. */
    public static final Codec<HubData> CODEC = RecordCodecBuilder.create(i -> i.group(
            Codec.STRING.fieldOf("look").forGetter(HubData::look),
            Codec.unboundedMap(Codec.STRING, Codec.INT).fieldOf("numbers").forGetter(HubData::numbers),
            GlobalPos.CODEC.fieldOf("home").forGetter(HubData::home),
            Fixed.CODEC.fieldOf("fixed").forGetter(HubData::fixed),
            Logo.CODEC.listOf().optionalFieldOf("logos", List.of()).forGetter(HubData::logos)).apply(i, HubData::new));
    // Only a new flat home writes this file. A default here would let a missing or unreadable record be replaced
    // by an empty one, and the mod would then no longer know its own blocks.
    private static final SavedDataType<HubData> TYPE = new SavedDataType<>(AresOs.id("hub"), () -> {
        throw new IllegalStateException("hub.dat is written only when a flat home is created");
    }, CODEC, null);

    private final String look;
    private final Map<String, Integer> numbers;
    private final GlobalPos home;
    private Fixed fixed;
    private final List<Logo> logos = new ArrayList<>();
    /** Every block of the record, the fixed things' and the logos': where, and which block. */
    private final Map<BlockPos, String> placed = new HashMap<>();

    public HubData(String look, Map<String, Integer> numbers, GlobalPos home, Fixed fixed) {
        this(look, numbers, home, fixed, List.of());
    }

    public HubData(String look, Map<String, Integer> numbers, GlobalPos home, Fixed fixed, List<Logo> logos) {
        this.look = look;
        this.numbers = Map.copyOf(numbers);
        this.home = home;
        this.fixed = new Fixed(List.copyOf(fixed.blocks()), List.copyOf(fixed.names()));
        for (Placed block : this.fixed.blocks()) placed.put(block.pos(), block.block());
        for (Logo logo : logos) index(logo);
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
    /** The town's standing logos, in the order they were built. */
    public List<Logo> logos() { return List.copyOf(logos); }

    /** The logo of an app that stands in the town. */
    public Optional<Logo> logo(String app) {
        return logos.stream().filter(logo -> logo.app().equals(app)).findFirst();
    }

    /** The logo whose trigger zone in {@code zones.dat} has this ID: such a zone is the town's, not his. */
    public Optional<Logo> logoOfZone(String zone) {
        return logos.stream().filter(logo -> logo.zone().equals(zone)).findFirst();
    }

    /** The logo whose record holds the block at this position, while it is still the recorded one. */
    public Optional<Logo> logoAt(ServerLevel level, BlockPos pos) {
        if (!holds(level, pos)) return Optional.empty();
        return logos.stream().filter(logo -> logo.gate().placed().stream().anyMatch(block -> block.pos().equals(pos))).findFirst();
    }

    /** Whether a zone of {@code zones.dat} belongs to the town of this world. False where there is no flat home. */
    public static boolean town(MinecraftServer server, AppZone zone) {
        HubData hub = get(server);
        return hub != null && zone.dimension().equals(hub.home.dimension()) && hub.logoOfZone(zone.id()).isPresent();
    }

    /** Every block the record holds in this dimension, by position: what the mod built here and owns. */
    public Map<BlockPos, String> blocks(ResourceKey<Level> dimension) {
        return dimension.equals(home.dimension()) ? Map.copyOf(placed) : Map.of();
    }

    /** The entity IDs of the town's signs. */
    public Set<UUID> signs() {
        return logos.stream().flatMap(logo -> logo.gate().sign().stream()).collect(Collectors.toUnmodifiableSet());
    }

    /** Records a logo that was just built. One logo an app, and no block in two records. */
    public void add(Logo logo) {
        if (logo(logo.app()).isPresent()) throw new IllegalArgumentException("The town already has a logo of " + logo.app());
        for (var block : logo.gate().placed())
            if (placed.containsKey(block.pos())) throw new IllegalArgumentException("Recorded twice: " + block.pos().toShortString());
        index(logo);
        setDirty();
    }

    /** Forgets a logo that was taken down; what was left of it is his. */
    public Optional<Logo> remove(String app) {
        var logo = logo(app);
        logo.ifPresent(gone -> {
            logos.remove(gone);
            for (var block : gone.gate().placed()) placed.remove(block.pos());
            setDirty();
        });
        return logo;
    }

    private void index(Logo logo) {
        logos.add(logo);
        for (var block : logo.gate().placed()) placed.put(block.pos(), block.block());
    }

    /** True while the block at this position is still the one the mod placed there. */
    public boolean holds(ServerLevel level, BlockPos pos) {
        if (!level.dimension().equals(home.dimension())) return false;
        String block = placed.get(pos);
        if (block == null) return false;
        if (block.equals(net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()).toString())) return true;
        forget(pos);
        return false;
    }

    /** Called after an actual block-kind change, including mining, explosions and pistons. */
    public static void blockChanged(ServerLevel level, BlockPos pos) {
        HubData hub = get(level.getServer());
        if (hub != null && level.dimension().equals(hub.home.dimension())) hub.forget(pos);
    }

    private void forget(BlockPos pos) {
        if (placed.remove(pos) == null) return;
        if (fixed.blocks().stream().anyMatch(block -> block.pos().equals(pos)))
            fixed = new Fixed(fixed.blocks().stream().filter(block -> !block.pos().equals(pos)).toList(), fixed.names());
        for (int i = 0; i < logos.size(); i++) {
            var logo = logos.get(i);
            if (logo.gate().placed().stream().anyMatch(block -> block.pos().equals(pos))) logos.set(i, logo.without(Set.of(pos)));
        }
        setDirty();
    }

    /** In Live mode he cannot break the hub's own blocks by hand. */
    public static boolean protectsFrom(ServerPlayer player, BlockPos pos) {
        if (!LiveMode.isLive(player)) return false;
        HubData hub = get(player.level().getServer());
        return hub != null && hub.holds(player.level(), pos);
    }

    /** Only the singleplayer host chooses the explosion policy; LAN guests cannot disable protection. */
    public static boolean protectsFromExplosions(MinecraftServer server) {
        return server.getPlayerList().getPlayers().stream()
                .filter(player -> DesktopWorld.isHost(server, player))
                .findFirst().map(player -> protectsFromExplosions(player.gameMode.getGameModeForPlayer())).orElse(true);
    }

    /** Unknown host means protected, just like Live mode. */
    public static boolean protectsFromExplosions(GameType hostMode) {
        return hostMode != GameType.CREATIVE;
    }
}
