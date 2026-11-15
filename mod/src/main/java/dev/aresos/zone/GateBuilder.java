package dev.aresos.zone;

import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppDefinition;
import dev.aresos.icon.AppIcons;
import dev.aresos.mixin.TextDisplayAccess;
import dev.aresos.world.HomeSites;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.FloatTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LightBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.TagValueInput;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Builds a planned gate into the world and takes it down again. A build is all or nothing: every refusal comes
 * before the first block changes. A removal touches only what is still as the mod placed it.
 */
public final class GateBuilder {
    /** How many recorded blocks a removal took away, and how many it left because they had been changed. */
    /**
     * What a removal did: how many recorded blocks it took away, how many stay because he changed them, and whether
     * an entity with the sign's ID stays ({@link SignLeft}).
     */
    public record Removal(int removed, int kept, SignLeft sign) { }

    /** Whether the sign stays after a removal, and why: it is his then. */
    public enum SignLeft {
        /** Taken down, or no entity with its ID was there. */
        NONE,
        /** It is not what the mod made: edited, moved, or another entity that took its ID. */
        CHANGED,
        /** The record does not say where the sign stood and what it said (a gate of packages 33 to 35): never taken down. */
        UNRECORDED
    }

    /**
     * How far a light block melts: ice goes at block light 11 and snow at 12, and a level-15 light block still
     * gives 11 four cells away. The farthest a build or a removal looks around a gate's cells: the town's tests hold
     * ground that reaches this far around every logo they build.
     */
    public static final int LIGHT_MELTS = 4;

    private GateBuilder() { }

    /**
     * The picture of an app's gate: its icon by the rules of HUB.md 3.6, or a plain front in its group's colour
     * when it has no readable icon or nothing of it is visible (HUB.md 2.3). The icon is the one {@link AppIcons}
     * reads for the app's item: the owner's own path first, otherwise the picture the system named, within its limits.
     * It reads a file and may wait seconds for it: never on the server thread ({@link PictureReader}).
     */
    public static GatePicture picture(AppDefinition app, int size) {
        return icon(app, size).orElseGet(() -> GatePicture.plain(concrete(app), size));
    }

    /**
     * The picture of an app's icon by the rules of HUB.md 3.6, or empty when it has no readable icon or nothing of it
     * is visible: then its gate has a plain front in its group's colour ({@link #picture}). The icon does not depend
     * on the group; only the plain front does. It reads a file: never on the server thread.
     */
    public static Optional<GatePicture> icon(AppDefinition app, int size) {
        try {
            var icon = AppIcons.read(app);
            if (icon != null) {
                var picture = GatePicture.of(icon.image(), size);
                if (!picture.isEmpty()) return Optional.of(picture);
            }
        } catch (IOException | RuntimeException unreadable) {
            // Falls through to the plain front; the sign says which app it is.
        }
        return Optional.empty();
    }

    /** The concrete of the app's group, named as the gate names blocks: its doormat and its plain front. */
    public static String concrete(AppDefinition app) { return GatePalette.name(AppGroup.of(app).concrete()); }

    /** The gate `/aresos logo <app>` builds with this picture: in front of where he stood, facing him, on the ground he stood on. */
    public static GatePlan planInFrontOf(Vec3 feet, Direction facing, ResourceKey<Level> dimension, AppDefinition app, GatePicture picture) {
        return GatePlan.of(picture, dimension, GatePlan.originInFrontOf(feet, facing, GateNumbers.SIZE), facing, app.name(),
                dev.aresos.names.NameRules.mainName(app), concrete(app));
    }

    /** Builds the gate and saves its zone, or throws with the reason and changes nothing. */
    public static AppZone build(ServerLevel level, String app, GatePlan plan) throws IOException {
        var built = place(prepare(level, app, plan));
        ZoneData.get(level.getServer()).add(built);
        return built;
    }

    /** The gate's place is not loaded: nothing was looked at closely and nothing changed. Try again when it is. */
    public static final class NotLoaded extends IOException {
        public NotLoaded(String message) { super(message); }
    }

    /**
     * A gate that passed every check, ready to build: nothing in the world has changed yet. {@code zone} is its
     * trigger zone with every block it will place, not saved anywhere.
     */
    public record Prepared(ServerLevel level, GatePlan plan, AppZone zone, Map<BlockPos, BlockState> placed, Entity sign) { }

    /**
     * Gates due to come down before a build, as the build is checked while they still stand (package 37's swap and
     * move), each as its own take-down will leave things ({@link #checkRemoval}): {@code blocks}, the blocks that
     * change and what comes back; {@code zones}, the IDs of their trigger zones, which go with them; {@code disowned},
     * every block their records hold, which is the mod's no longer (a block he changed stays and is his);
     * {@code unrecorded}, their signs' IDs, which leave the records; {@code discarded}, the signs the take-downs
     * discard. A sign a take-down leaves (he moved or edited it) stays in the world, no longer the mod's, and counts
     * like any entity of his (review fixes 1, point 3). Everything else is read from the world as it is.
     */
    public record Gone(Map<BlockPos, BlockState> blocks, java.util.Set<String> zones, java.util.Set<BlockPos> disowned,
                       java.util.Set<UUID> unrecorded, java.util.Set<UUID> discarded) {
        public static final Gone NONE = new Gone(Map.of(), java.util.Set.of(), java.util.Set.of(), java.util.Set.of(), java.util.Set.of());

        public Gone {
            blocks = Map.copyOf(blocks);
            zones = java.util.Set.copyOf(zones);
            disowned = java.util.Set.copyOf(disowned);
            unrecorded = java.util.Set.copyOf(unrecorded);
            discarded = java.util.Set.copyOf(discarded);
        }

        /** What these take-downs leave, with the trigger zones that go with them. */
        public static Gone of(java.util.Collection<TakeDown> takeDowns, java.util.Set<String> zones) {
            var blocks = new HashMap<BlockPos, BlockState>();
            var disowned = new HashSet<BlockPos>();
            var unrecorded = new HashSet<UUID>();
            var discarded = new HashSet<UUID>();
            for (var down : takeDowns) {
                blocks.putAll(down.back());
                down.gate().placed().forEach(placed -> disowned.add(placed.pos()));
                down.gate().sign().ifPresent(unrecorded::add);
                down.discards().ifPresent(discarded::add);
            }
            return new Gone(blocks, zones, disowned, unrecorded, discarded);
        }

        /** A block as it will be once these gates came down. */
        BlockState state(ServerLevel level, BlockPos pos) {
            var left = blocks.get(pos);
            return left != null ? left : level.getBlockState(pos);
        }

        /**
         * The entities a check leaves alone once these gates came down: the mod's signs that keep their records, and the
         * signs the take-downs discard (they are gone). A sign a take-down leaves standing is not among them.
         */
        java.util.Set<UUID> exempt(java.util.Set<UUID> signs) {
            var exempt = new HashSet<>(signs);
            exempt.removeAll(unrecorded);
            exempt.addAll(discarded);
            return exempt;
        }
    }

    /** A block as it would be once the gates in {@code gone} came down. */
    private static BlockState state(ServerLevel level, Gone gone, BlockPos pos) {
        return gone.state(level, pos);
    }

    /**
     * Every refusal of a build, without changing anything: {@link NotLoaded} while the place is not loaded, otherwise
     * an IOException that says what is in the way. What it returns is for {@link #place}, at once.
     */
    public static Prepared prepare(ServerLevel level, String app, GatePlan plan) throws IOException {
        return prepare(level, app, plan, Gone.NONE);
    }

    /**
     * {@link #prepare} as if the gates in {@code gone} had come down first: their blocks read as what their take-down
     * leaves, their zones as gone. Only for checking; build with a {@code prepare} after they came down.
     */
    public static Prepared prepare(ServerLevel level, String app, GatePlan plan, Gone gone) throws IOException {
        if (!level.dimension().equals(plan.dimension())) throw new IOException("The gate is planned for another dimension.");
        var data = ZoneData.get(level.getServer());
        var solid = new LinkedHashMap<BlockPos, BlockState>();
        for (var block : plan.blocks().entrySet()) solid.put(block.getKey(), Neighbors.block(block.getValue()).defaultBlockState());
        var space = new ArrayList<>(plan.space());
        space.addAll(plan.signSpace());
        var inspection = new HashSet<>(space);
        inspection.addAll(plan.walkway());
        inspection.addAll(plan.doormatSurround());
        inspection.addAll(plan.floor());
        inspection.addAll(Neighbors.footprint(solid.keySet(), 2));
        inspection.addAll(Neighbors.footprint(plan.doormat(), 2));
        inspection.addAll(Neighbors.footprint(plan.lights(), LIGHT_MELTS));
        if (!loaded(level, inspection)) throw new NotLoaded("The place for the gate isn't loaded. Go nearer, then retry. No blocks changed.");
        for (var pos : space) {
            if (pos.getY() < level.getMinY() || pos.getY() >= level.getMaxY() || !level.getWorldBorder().isWithinBounds(pos))
                throw new IOException("Gate would be outside the build limits or world border.");
            if (!state(level, gone, pos).isAir())
                throw new IOException("Area isn't clear at " + pos.toShortString() + ". No blocks changed. A gate needs its own "
                        + plan.size() + " x " + plan.size() + " x " + GateNumbers.DEPTH + " blocks, one layer in front and the way to its door free; clear them in Build mode, then retry.");
        }
        for (var pos : plan.walkway()) if (!state(level, gone, pos).isFaceSturdy(level, pos, Direction.UP))
            throw new IOException("The ground on the way to the door isn't solid at " + pos.toShortString() + ". No blocks changed.");
        if (!HomeSites.isSafe(level, plan.exit().position()))
            throw new IOException("The exit point in front of the door isn't safe solid ground. No blocks changed.");
        var doormat = doormat(level, plan, gone);
        var placed = new LinkedHashMap<>(solid);
        for (var pos : plan.lights()) placed.put(pos, Blocks.LIGHT.defaultBlockState().setValue(LightBlock.LEVEL, LightBlock.MAX_LEVEL));
        doormat.ifPresent(mat -> plan.doormat().forEach(pos -> placed.put(pos, mat)));
        var zone = new AppZone(UUID.randomUUID().toString(), app, plan.dimension(), plan.nicheMin(), plan.nicheMax(), plan.exit(),
                List.copyOf(placed.keySet()), Optional.empty());
        String conflict = data.conflict(zone, gone.zones());
        if (conflict != null) throw new IOException(conflict);
        if (Neighbors.occupant(level, solid.keySet(), gone.exempt(Neighbors.signs(level.getServer()))) != null)
            throw new IOException("An entity occupies the gate's place. Move it away, then retry.");
        Neighbors.check(level, placed.keySet(), solid.keySet(), 2, gone);
        if (doormat.isPresent()) Neighbors.check(level, placed.keySet(), plan.doormat(), 2, gone);
        Neighbors.check(level, placed.keySet(), plan.lights(), LIGHT_MELTS, gone);
        return new Prepared(level, plan, zone, java.util.Collections.unmodifiableMap(placed), sign(level, plan.sign()));
    }

    /**
     * Builds what {@link #prepare} checked, every block through {@link Placing}, and returns its zone with what was
     * placed for it as its gate. The caller records it: a gate built by hand in {@code zones.dat}, a town logo in
     * {@code hub.dat}. If the world changed since the check, everything placed goes back and nothing is recorded.
     */
    public static AppZone place(Prepared prepared) throws IOException {
        var level = prepared.level();
        var plan = prepared.plan();
        // The grass under the gate turns to dirt in the dark; it is put back when the gate goes.
        var grass = plan.floor().stream().filter(pos -> level.getBlockState(pos).is(Blocks.GRASS_BLOCK)).toList();
        var done = new ArrayList<Placing.Change>();
        for (var block : prepared.placed().entrySet()) {
            var change = Placing.set(level, block.getKey(), null, block.getValue());
            if (change.isEmpty()) {
                undo(level, done);
                throw new IOException("Something changed at " + block.getKey().toShortString() + " while the gate was built. No blocks changed.");
            }
            done.add(change.get());
        }
        var sign = prepared.sign();
        if (!level.addFreshEntity(sign)) {
            // Nothing is known to make this fail after the checks above; if it does, the world goes back as it was.
            undo(level, done);
            throw new IOException("The gate's sign could not be placed. No blocks changed.");
        }
        var record = done.stream().map(change -> new AppZone.Placed(change.pos(), change.block())).toList();
        // The ground the doormat replaced, to put back when the gate is removed. Everything else went into air.
        var ground = done.stream().filter(change -> !Placing.state(change.before()).isAir())
                .map(change -> new AppZone.Placed(change.pos(), change.before())).toList();
        var zone = prepared.zone();
        return new AppZone(zone.id(), zone.app(), zone.dimension(), zone.min(), zone.max(), zone.exit(), zone.blocks(),
                Optional.of(new AppZone.Gate(record, ground, Optional.of(sign.getUUID()), grass, Optional.of(plan.sign()))));
    }

    /** Puts back what a build placed, newest first, each block only while it is still the one placed. */
    private static void undo(ServerLevel level, List<Placing.Change> done) {
        for (var change : done.reversed()) Placing.set(level, change.pos(), change.block(), Placing.state(change.before()));
    }

    /**
     * Grass or dirt under the doormat and its whole ring. These blocks cannot establish provenance, but stone
     * and other landscaping are never paved over. The original kind of every replaced block is recorded.
     */
    private static Optional<BlockState> doormat(ServerLevel level, GatePlan plan, Gone gone) {
        for (var pos : plan.doormatSurround()) {
            var state = state(level, gone, pos);
            if (!state.is(Blocks.GRASS_BLOCK) && !state.is(Blocks.DIRT)) return Optional.empty();
        }
        return Optional.of(Neighbors.block(plan.doormatBlock()).defaultBlockState());
    }

    /**
     * The sign as HUB.md 3.2 describes it. A display's setters are private, so it is made from the same data a
     * saved one has. It has no hit box and takes no damage, in any mode.
     */
    private static Entity sign(ServerLevel level, GatePlan.Sign sign) throws IOException {
        var tag = new CompoundTag();
        tag.put("text", ComponentSerialization.CODEC.encodeStart(level.registryAccess().createSerializationContext(NbtOps.INSTANCE), text(sign)).getOrThrow());
        tag.putInt("line_width", GateNumbers.SIGN_LINE_WIDTH);
        tag.putInt("background", GateNumbers.SIGN_BACKGROUND);
        // Turns around the upright axis only.
        tag.putString("billboard", "vertical");
        tag.putFloat("view_range", GateNumbers.SIGN_VIEW_RANGE);
        var brightness = new CompoundTag();
        brightness.putInt("sky", 15); brightness.putInt("block", 15);
        tag.put("brightness", brightness);
        var transformation = new CompoundTag();
        transformation.put("translation", floats(0, 0, 0));
        transformation.put("left_rotation", floats(0, 0, 0, 1));
        transformation.put("scale", floats(GateNumbers.SIGN_SCALE, GateNumbers.SIGN_SCALE, GateNumbers.SIGN_SCALE));
        transformation.put("right_rotation", floats(0, 0, 0, 1));
        tag.put("transformation", transformation);
        var entity = EntityType.create(EntityTypes.TEXT_DISPLAY, TagValueInput.create(ProblemReporter.DISCARDING, level.registryAccess(), tag),
                level, EntitySpawnReason.COMMAND).orElseThrow(() -> new IOException("The gate's sign could not be made. No blocks changed."));
        entity.snapTo(sign.position().x, sign.position().y, sign.position().z, 0, 0);
        return entity;
    }

    /** What a gate's sign says: the app's name in white and, on a second line, its main short name in gold. */
    private static Component text(GatePlan.Sign sign) {
        var text = Component.literal(sign.name()).withStyle(ChatFormatting.WHITE);
        if (sign.shortName() != null && !sign.shortName().isBlank())
            text.append(Component.literal("\n/" + sign.shortName()).withStyle(ChatFormatting.GOLD));
        return text;
    }

    /**
     * Whether an entity is still the sign the mod made (review fixes 1, step B, point 2, and review fixes 2, point 2):
     * a text display at the place the record names with the text it names, compared in its saved form. Anything else
     * is his: an entity of his that took the recorded ID, a sign whose text he edited or that was moved, and any sign
     * of a record that does not name its place and text ({@code made} null).
     */
    private static boolean made(ServerLevel level, Entity entity, GatePlan.Sign made) {
        if (made == null || !(entity instanceof Display.TextDisplay display)) return false;
        if (entity.position().distanceToSqr(made.position()) > 1.0E-6) return false;
        var ops = level.registryAccess().createSerializationContext(NbtOps.INSTANCE);
        var shown = ComponentSerialization.CODEC.encodeStart(ops, ((TextDisplayAccess)display).aresos$text()).result();
        return shown.isPresent() && shown.equals(ComponentSerialization.CODEC.encodeStart(ops, text(made)).result());
    }

    /**
     * Whether the world around these blocks is loaded with its entities. Where it is not, entities in the way
     * and a gate's own sign cannot be seen, so nothing is built or removed there.
     */
    private static boolean loaded(ServerLevel level, Iterable<BlockPos> cells) {
        var chunks = new HashSet<Long>();
        for (var pos : cells) chunks.add(ChunkPos.pack(pos));
        for (long chunk : chunks)
            if (!level.hasChunk(ChunkPos.getX(chunk), ChunkPos.getZ(chunk)) || !level.areEntitiesLoaded(chunk)) return false;
        return true;
    }

    private static ListTag floats(float... values) {
        var list = new ListTag();
        for (float value : values) list.add(FloatTag.valueOf(value));
        return list;
    }

    /**
     * Takes a gate down: each recorded block that is still that block (the doormat goes back to the ground it
     * replaced), the sign and the zone. A block he changed since is his and stays. Refuses, changing nothing,
     * while the gate's place is not loaded: its sign could not be found then.
     */
    public static Removal remove(MinecraftServer server, AppZone zone) throws IOException {
        var gate = zone.gate().orElseThrow(() -> new IOException("Not a gate."));
        var level = server.getLevel(zone.dimension());
        if (level == null) throw new IOException("The gate's dimension does not exist.");
        Removal removal;
        try {
            // The sign goes only while it is still where and what the record says it was built (review fixes 2,
            // point 2); a record without that leaves it standing.
            removal = takeDown(level, gate, gate.signPlan().orElse(null));
        } catch (NotLoaded notLoaded) {
            throw new NotLoaded("The gate of " + zone.app() + " isn't loaded. Go to it and use /aresos logo remove here. Nothing changed.");
        }
        ZoneData.get(server).remove(saved -> saved.id().equals(zone.id()));
        return removal;
    }

    /**
     * Takes down what a gate placed, through {@link Placing}: each recorded block that is still that block (the
     * doormat goes back to the ground it replaced), the grass under it where it turned to dirt, and the sign while it
     * is still the one the mod made ({@code sign}: where it stands and what it says, or null when the record does not
     * know; then it is never taken down). A sign that is not is his and stays. Its record and zone are the
     * caller's. Refuses, changing nothing, while the place is not loaded ({@link NotLoaded}) or when something of his
     * could fall or break with it.
     */
    public static Removal takeDown(ServerLevel level, AppZone.Gate gate, GatePlan.Sign sign) throws IOException {
        // Refuse the whole operation before touching the sign, the record or any block; then do what was decided.
        var down = checkRemoval(level, gate, sign);
        down.back().forEach((pos, state) -> Placing.set(level, pos, down.expected().get(pos), state));
        down.discards().map(level::getEntity).ifPresent(Entity::discard);
        return new Removal(gate.placed().size() - down.kept(), down.kept(), down.left());
    }

    /**
     * What a take-down does, decided before anything changes: each block that goes, with what the record says stands
     * there ({@code expected}) and what comes back in its place ({@code back}); {@code kept}, recorded blocks he
     * changed, which stay his; the sign it discards ({@code discards}: still the one the mod made) or why an entity
     * with the sign's ID stays ({@code left}).
     */
    public record TakeDown(AppZone.Gate gate, Map<BlockPos, String> expected, Map<BlockPos, BlockState> back, int kept,
                           Optional<UUID> discards, SignLeft left) { }

    /** The blocks of a take-down, before its sign is looked at. */
    private record Undo(Map<BlockPos, String> expected, Map<BlockPos, BlockState> back, int kept) { }

    /**
     * Throws, changing nothing, unless {@link #takeDown} would take this gate down now: {@link NotLoaded} while its
     * place is not loaded, otherwise an IOException naming what of his could fall or break with it. Otherwise what
     * the take-down will do. The very code {@code takeDown} runs first (review fixes 1, point 3), so a check before a
     * swap or move ({@link Gone#of}) and the take-down itself cannot disagree, about the blocks or the sign.
     */
    public static TakeDown checkRemoval(ServerLevel level, AppZone.Gate gate, GatePlan.Sign sign) throws IOException {
        var recorded = gate.placed().stream().map(AppZone.Placed::pos).collect(java.util.stream.Collectors.toSet());
        recorded.addAll(gate.grass());
        var inspection = Neighbors.footprint(recorded, 2);
        inspection.addAll(Neighbors.footprint(gate.placed().stream().filter(placed -> placed.block().equals("minecraft:light")).map(AppZone.Placed::pos).toList(), LIGHT_MELTS));
        if (!loaded(level, inspection)) throw new NotLoaded("The gate isn't loaded. Nothing changed.");
        var undo = undoing(level, gate);
        Neighbors.checkRemoval(level, undo.back().keySet());
        var entity = gate.sign().map(level::getEntity);
        Optional<UUID> discards = Optional.empty();
        var left = SignLeft.NONE;
        if (entity.isPresent()) {
            if (made(level, entity.get(), sign)) discards = Optional.of(entity.get().getUUID());
            else left = sign == null ? SignLeft.UNRECORDED : SignLeft.CHANGED;
        }
        return new TakeDown(gate, undo.expected(), undo.back(), undo.kept(), discards, left);
    }

    private static Undo undoing(ServerLevel level, AppZone.Gate gate) {
        var ground = new HashMap<BlockPos, String>();
        for (var replaced : gate.ground()) ground.put(replaced.pos(), replaced.block());
        var expected = new HashMap<BlockPos, String>();
        var back = new LinkedHashMap<BlockPos, BlockState>();
        int kept = 0;
        for (var placed : gate.placed()) {
            if (!Placing.still(level.getBlockState(placed.pos()), placed.block())) { kept++; continue; }
            expected.put(placed.pos(), placed.block());
            back.put(placed.pos(), Placing.state(ground.getOrDefault(placed.pos(), "minecraft:air")));
        }
        for (var pos : gate.grass()) if (level.getBlockState(pos).is(Blocks.DIRT)) {
            expected.put(pos, "minecraft:dirt");
            back.put(pos, Blocks.GRASS_BLOCK.defaultBlockState());
        }
        return new Undo(expected, back, kept);
    }
}
