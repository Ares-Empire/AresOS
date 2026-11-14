package dev.aresos.hub;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.AresOs;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.Placing;
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
 * <p>{@code hub.dat} keeps the shape package 32 gave it (look, numbers, home, the fixed things). The standing logos
 * are saved beside it in {@code data/aresos/town.dat}, a file no mod of packages 32 to 35 knows or writes: such a mod
 * rewrites {@code hub.dat} when a pad block changes and drops every field it does not know, so after going back to
 * one, logos kept in {@code hub.dat} would be lost and stand there as nobody's. In memory it is one record with one
 * block index ({@link #holds}). The town's gates are recorded here and not in the zones file, so an older mod that
 * saves the zones file cannot orphan them either. Their trigger zones stay in {@code zones.dat} without a gate of
 * their own; a zone is the town's while a logo here names its ID ({@link #logoOfZone}).
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

    /** The contents of {@code hub.dat}, as package 32 wrote it. The logos are in {@code town.dat} ({@link TownFile}). */
    public static final Codec<HubData> CODEC = RecordCodecBuilder.create(i -> i.group(
            Codec.STRING.fieldOf("look").forGetter(HubData::look),
            Codec.unboundedMap(Codec.STRING, Codec.INT).fieldOf("numbers").forGetter(HubData::numbers),
            GlobalPos.CODEC.fieldOf("home").forGetter(HubData::home),
            Fixed.CODEC.fieldOf("fixed").forGetter(HubData::fixed)).apply(i, HubData::new));
    // Only a new flat home writes this file. A default here would let a missing or unreadable record be replaced
    // by an empty one, and the mod would then no longer know its own blocks.
    private static final SavedDataType<HubData> TYPE = new SavedDataType<>(AresOs.id("hub"), () -> {
        throw new IllegalStateException("hub.dat is written only when a flat home is created");
    }, CODEC, null);

    /**
     * {@code data/aresos/town.dat}: the standing logos of the town at {@code home}. The home ties the file to its
     * hub: a town file of another home is not this hub's and is never read into it.
     */
    static final class TownFile extends SavedData {
        static final Codec<TownFile> CODEC = RecordCodecBuilder.create(i -> i.group(
                GlobalPos.CODEC.fieldOf("home").forGetter(file -> file.home),
                Logo.CODEC.listOf().fieldOf("logos").forGetter(file -> List.copyOf(file.logos))).apply(i, TownFile::new));
        // A world without the file has no town yet; the hub makes one for its home when it first needs it.
        static final SavedDataType<TownFile> TYPE = new SavedDataType<>(AresOs.id("town"), () -> {
            throw new IllegalStateException("town.dat is made by its hub");
        }, CODEC, null);
        final GlobalPos home;
        final List<Logo> logos;

        TownFile(GlobalPos home, List<Logo> logos) { this.home = home; this.logos = new ArrayList<>(logos); }
    }

    private final String look;
    private final Map<String, Integer> numbers;
    private final GlobalPos home;
    private Fixed fixed;
    /** The logos, saved in town.dat; the server's own file once {@link #attach}ed. */
    private TownFile town;
    private boolean attached;
    /** Every block of the record, the fixed things' and the logos': where, and which block. */
    private final Map<BlockPos, String> placed = new HashMap<>();
    /** Which logo each of the logos' blocks belongs to, by app. */
    private final Map<BlockPos, String> logoBlocks = new HashMap<>();

    public HubData(String look, Map<String, Integer> numbers, GlobalPos home, Fixed fixed) {
        this(look, numbers, home, fixed, List.of());
    }

    public HubData(String look, Map<String, Integer> numbers, GlobalPos home, Fixed fixed, List<Logo> logos) {
        this.look = look;
        this.numbers = Map.copyOf(numbers);
        this.home = home;
        this.fixed = new Fixed(List.copyOf(fixed.blocks()), List.copyOf(fixed.names()));
        for (Placed block : this.fixed.blocks()) placed.put(block.pos(), block.block());
        this.town = new TownFile(home, List.of());
        for (Logo logo : logos) index(logo);
    }

    /** The record of this save's hub, or null: not a flat home, or its record is missing or unreadable. */
    public static HubData get(MinecraftServer server) {
        var hub = server.getDataStorage().get(TYPE);
        if (hub != null && !hub.attached) hub.attach(server.getDataStorage());
        return hub;
    }

    /**
     * Called once, when a new flat home has been built (and by tests, to put a record back). The town of the same
     * home in {@code town.dat} stays this hub's: storing a {@code hub.dat} again loses no logo.
     */
    public static void store(MinecraftServer server, HubData data) {
        server.getDataStorage().set(TYPE, data);
        data.setDirty();
        data.attach(server.getDataStorage());
    }

    /** Joins this record to the server's town file of the same home, or makes that file from this record's logos. */
    private void attach(net.minecraft.world.level.storage.SavedDataStorage storage) {
        var file = attached ? town : storage.get(TownFile.TYPE);
        if (file != null && file != town && home.equals(file.home)) adopt(file);
        else {
            storage.set(TownFile.TYPE, town);
            if (!town.logos.isEmpty()) town.setDirty();
        }
        attached = true;
    }

    /** Takes the logos of a town file as this hub's, in place of its own: the file is this record's from now on. */
    void adopt(TownFile file) {
        if (!home.equals(file.home)) throw new IllegalArgumentException("The town file belongs to another home: " + file.home);
        for (var logo : town.logos) for (var block : logo.gate().placed()) { placed.remove(block.pos()); logoBlocks.remove(block.pos()); }
        var logos = List.copyOf(file.logos);
        file.logos.clear();
        town = file;
        for (var logo : logos) index(logo);
    }

    /** Whether town.dat has changes to write. */
    boolean townChanged() { return town.isDirty(); }

    public String look() { return look; }
    public Map<String, Integer> numbers() { return numbers; }
    /** The origin of all hub coordinates: the block he stands in at home, and its dimension. */
    public GlobalPos home() { return home; }
    public Fixed fixed() { return fixed; }
    /** The town's standing logos, in the order they were built. */
    public List<Logo> logos() { return List.copyOf(town.logos); }

    /** The logo of an app that stands in the town. */
    public Optional<Logo> logo(String app) {
        return town.logos.stream().filter(logo -> logo.app().equals(app)).findFirst();
    }

    /** The logo whose trigger zone in {@code zones.dat} has this ID: such a zone is the town's, not his. */
    public Optional<Logo> logoOfZone(String zone) {
        return town.logos.stream().filter(logo -> logo.zone().equals(zone)).findFirst();
    }

    /** The logo whose record holds the block at this position, while it is still the recorded one. */
    public Optional<Logo> logoAt(ServerLevel level, BlockPos pos) {
        if (!holds(level, pos)) return Optional.empty();
        var app = logoBlocks.get(pos);
        return app == null ? Optional.empty() : logo(app);
    }

    /**
     * Whether an explosion leaves this block alone: a block of a town logo always, as package 33 has it for gates
     * ("explosions are never an edit gesture"); the pad and roads unless the host is in Build mode (package 32).
     */
    public boolean sparesFromExplosion(ServerLevel level, BlockPos pos, boolean buildMode) {
        return holds(level, pos) && (!buildMode || logoBlocks.containsKey(pos));
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
        return town.logos.stream().flatMap(logo -> logo.gate().sign().stream()).collect(Collectors.toUnmodifiableSet());
    }

    /** Records a logo that was just built. One logo an app, and no block in two records. */
    public void add(Logo logo) {
        if (logo(logo.app()).isPresent()) throw new IllegalArgumentException("The town already has a logo of " + logo.app());
        for (var block : logo.gate().placed())
            if (placed.containsKey(block.pos())) throw new IllegalArgumentException("Recorded twice: " + block.pos().toShortString());
        index(logo);
        town.setDirty();
    }

    /**
     * Records road blocks the town just paved. They are fixed things like the pad and the first stretch of road, so
     * they are saved in {@code hub.dat}, where an older mod keeps protecting them.
     */
    public void pave(List<Placed> blocks) {
        if (blocks.isEmpty()) return;
        for (var block : blocks)
            if (placed.containsKey(block.pos())) throw new IllegalArgumentException("Recorded twice: " + block.pos().toShortString());
        var all = new ArrayList<>(fixed.blocks());
        all.addAll(blocks);
        fixed = new Fixed(List.copyOf(all), fixed.names());
        for (var block : blocks) placed.put(block.pos(), block.block());
        setDirty();
    }

    /** Forgets a logo that was taken down; what was left of it is his. */
    public Optional<Logo> remove(String app) {
        var logo = logo(app);
        logo.ifPresent(gone -> {
            town.logos.remove(gone);
            for (var block : gone.gate().placed()) { placed.remove(block.pos()); logoBlocks.remove(block.pos()); }
            town.setDirty();
        });
        return logo;
    }

    private void index(Logo logo) {
        town.logos.add(logo);
        for (var block : logo.gate().placed()) { placed.put(block.pos(), block.block()); logoBlocks.put(block.pos(), logo.app()); }
    }

    /** True while the block at this position is still the one the mod placed there. */
    public boolean holds(ServerLevel level, BlockPos pos) {
        if (!level.dimension().equals(home.dimension())) return false;
        String block = placed.get(pos);
        if (block == null) return false;
        if (Placing.still(level.getBlockState(pos), block)) return true;
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
        if (fixed.blocks().stream().anyMatch(block -> block.pos().equals(pos))) {
            fixed = new Fixed(fixed.blocks().stream().filter(block -> !block.pos().equals(pos)).toList(), fixed.names());
            setDirty();
        }
        var app = logoBlocks.remove(pos);
        if (app == null) return;
        for (int i = 0; i < town.logos.size(); i++) {
            var logo = town.logos.get(i);
            if (logo.app().equals(app)) town.logos.set(i, logo.without(Set.of(pos)));
        }
        town.setDirty();
    }

    /** In Live mode he cannot break the hub's own blocks by hand. */
    public static boolean protectsFrom(ServerPlayer player, BlockPos pos) {
        return protection(player, pos) != null;
    }

    /** What the action bar says when he tries to break one of the hub's blocks in Live mode; null when he may. */
    public static String protection(ServerPlayer player, BlockPos pos) {
        if (!LiveMode.isLive(player)) return null;
        HubData hub = get(player.level().getServer());
        return hub == null ? null : hub.refusal(player.level(), pos);
    }

    /** Names what protects the block: a logo of the town, or the pad and roads. Null for a block that isn't the hub's. */
    public String refusal(ServerLevel level, BlockPos pos) {
        if (!holds(level, pos)) return null;
        return logoAt(level, pos).map(logo -> "The logo of " + logo.name() + " is part of the town and protected. Press G for Build mode.")
                .orElse("The home pad and roads are protected. Press G for Build mode.");
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
