package dev.aresos.zone;

import dev.aresos.config.AppDefinition;
import dev.aresos.world.HomeSites;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.FloatTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LightBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.TagValueInput;

import javax.imageio.ImageIO;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Builds a planned gate into the world and takes it down again. A build is all or nothing: every refusal comes
 * before the first block changes. A removal touches only what is still as the mod placed it.
 */
public final class GateBuilder {
    /** How many recorded blocks a removal took away, and how many it left because they had been changed. */
    public record Removal(int removed, int kept) { }

    /**
     * How far a light block melts: ice goes at block light 11 and snow at 12, and a level-15 light block still
     * gives 11 four cells away.
     */
    private static final int LIGHT_MELTS = 4;

    private GateBuilder() { }

    /**
     * The picture of an app's gate: its icon by the rules of HUB.md 3.6, or a plain front in its group's colour
     * when it has no readable icon or nothing of it is visible (HUB.md 2.3).
     */
    public static GatePicture picture(AppDefinition app, int size) {
        if (app.icon() != null) {
            try {
                var icon = ImageIO.read(Path.of(app.icon()).toFile());
                if (icon != null) {
                    var picture = GatePicture.of(icon, size);
                    if (!picture.isEmpty()) return picture;
                }
            } catch (IOException | RuntimeException unreadable) {
                // Falls through to the plain front; the sign says which app it is.
            }
        }
        return GatePicture.plain(GateGroup.concreteFor(app.id()), size);
    }

    /** The gate `/aresos logo <app>` builds: in front of the player, facing him, on the ground he stands on. */
    public static GatePlan planInFrontOf(ServerPlayer player, AppDefinition app) {
        var facing = player.getDirection();
        return GatePlan.of(picture(app, GateNumbers.SIZE), player.level().dimension(),
                GatePlan.originInFrontOf(player.position(), facing, GateNumbers.SIZE), facing, app.name(), null,
                GateGroup.concreteFor(app.id()));
    }

    /** Builds the gate and saves its zone, or throws with the reason and changes nothing. */
    public static AppZone build(ServerLevel level, String app, GatePlan plan) throws IOException {
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
        if (!loaded(level, inspection)) throw new IOException("The place for the gate isn't loaded. Go nearer, then retry. No blocks changed.");
        for (var pos : space) {
            if (pos.getY() < level.getMinY() || pos.getY() >= level.getMaxY() || !level.getWorldBorder().isWithinBounds(pos))
                throw new IOException("Gate would be outside the build limits or world border.");
            if (!level.getBlockState(pos).isAir())
                throw new IOException("Area isn't clear at " + pos.toShortString() + ". No blocks changed. A gate needs its own "
                        + plan.size() + " x " + plan.size() + " x " + GateNumbers.DEPTH + " blocks, one layer in front and the way to its door free; clear them in Build mode, then retry.");
        }
        for (var pos : plan.walkway()) if (!level.getBlockState(pos).isFaceSturdy(level, pos, Direction.UP))
            throw new IOException("The ground on the way to the door isn't solid at " + pos.toShortString() + ". No blocks changed.");
        if (!HomeSites.isSafe(level, plan.exit().position()))
            throw new IOException("The exit point in front of the door isn't safe solid ground. No blocks changed.");
        var doormat = doormat(level, plan);
        var placed = new LinkedHashMap<>(solid);
        for (var pos : plan.lights()) placed.put(pos, Blocks.LIGHT.defaultBlockState().setValue(LightBlock.LEVEL, LightBlock.MAX_LEVEL));
        doormat.ifPresent(mat -> plan.doormat().forEach(pos -> placed.put(pos, mat)));
        var zone = new AppZone(UUID.randomUUID().toString(), app, plan.dimension(), plan.nicheMin(), plan.nicheMax(), plan.exit(),
                List.copyOf(placed.keySet()), Optional.empty());
        String conflict = data.conflict(zone);
        if (conflict != null) throw new IOException(conflict);
        if (Neighbors.occupant(level, solid.keySet(), data.signs()) != null)
            throw new IOException("An entity occupies the gate's place. Move it away, then retry.");
        Neighbors.check(level, placed.keySet(), solid.keySet(), 2);
        if (doormat.isPresent()) Neighbors.check(level, placed.keySet(), plan.doormat(), 2);
        Neighbors.check(level, placed.keySet(), plan.lights(), LIGHT_MELTS);
        var sign = sign(level, plan.sign());

        // The ground the doormat replaces, to put back when the gate is removed.
        var before = new LinkedHashMap<BlockPos, BlockState>();
        if (doormat.isPresent()) for (var pos : plan.doormat()) before.put(pos, level.getBlockState(pos));
        var grass = plan.floor().stream().filter(pos -> level.getBlockState(pos).is(Blocks.GRASS_BLOCK)).toList();
        var record = new ArrayList<AppZone.Placed>();
        for (var block : placed.entrySet()) {
            level.setBlockAndUpdate(block.getKey(), block.getValue());
            record.add(new AppZone.Placed(block.getKey(), id(block.getValue())));
        }
        if (!level.addFreshEntity(sign)) {
            // Nothing is known to make this fail after the checks above; if it does, the world goes back as it was.
            for (var pos : placed.keySet()) level.setBlockAndUpdate(pos, before.getOrDefault(pos, Blocks.AIR.defaultBlockState()));
            throw new IOException("The gate's sign could not be placed. No blocks changed.");
        }
        var ground = before.entrySet().stream().map(block -> new AppZone.Placed(block.getKey(), id(block.getValue()))).toList();
        var built = new AppZone(zone.id(), app, zone.dimension(), zone.min(), zone.max(), zone.exit(), zone.blocks(),
                Optional.of(new AppZone.Gate(List.copyOf(record), ground, Optional.of(sign.getUUID()), grass)));
        data.add(built);
        return built;
    }

    /**
     * Grass or dirt under the doormat and its whole ring. These blocks cannot establish provenance, but stone
     * and other landscaping are never paved over. The original kind of every replaced block is recorded.
     */
    private static Optional<BlockState> doormat(ServerLevel level, GatePlan plan) {
        for (var pos : plan.doormatSurround()) {
            var state = level.getBlockState(pos);
            if (!state.is(Blocks.GRASS_BLOCK) && !state.is(Blocks.DIRT)) return Optional.empty();
        }
        return Optional.of(Neighbors.block(plan.doormatBlock()).defaultBlockState());
    }

    /**
     * The sign as HUB.md 3.2 describes it. A display's setters are private, so it is made from the same data a
     * saved one has. It has no hit box and takes no damage, in any mode.
     */
    private static Entity sign(ServerLevel level, GatePlan.Sign sign) throws IOException {
        var text = Component.literal(sign.name()).withStyle(ChatFormatting.WHITE);
        if (sign.shortName() != null && !sign.shortName().isBlank())
            text.append(Component.literal("\n/" + sign.shortName()).withStyle(ChatFormatting.GOLD));
        var tag = new CompoundTag();
        tag.put("text", ComponentSerialization.CODEC.encodeStart(level.registryAccess().createSerializationContext(NbtOps.INSTANCE), text).getOrThrow());
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

    private static String id(BlockState state) { return BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString(); }

    private static boolean unchanged(BlockState state, AppZone.Placed placed) {
        return id(state).equals(placed.block()) && (!state.is(Blocks.LIGHT)
                || state.getValue(LightBlock.LEVEL) == LightBlock.MAX_LEVEL && !state.getValue(LightBlock.WATERLOGGED));
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
        var recorded = gate.placed().stream().map(AppZone.Placed::pos).collect(java.util.stream.Collectors.toSet());
        recorded.addAll(gate.grass());
        var inspection = Neighbors.footprint(recorded, 2);
        inspection.addAll(Neighbors.footprint(gate.placed().stream().filter(placed -> placed.block().equals("minecraft:light")).map(AppZone.Placed::pos).toList(), LIGHT_MELTS));
        if (!loaded(level, inspection))
            throw new IOException("The gate of " + zone.app() + " isn't loaded. Go to it and use /aresos logo remove here. Nothing changed.");
        var ground = new HashMap<BlockPos, String>();
        for (var replaced : gate.ground()) ground.put(replaced.pos(), replaced.block());
        var removing = new LinkedHashMap<BlockPos, BlockState>();
        int kept = 0;
        for (var placed : gate.placed()) {
            if (!unchanged(level.getBlockState(placed.pos()), placed)) { kept++; continue; }
            var before = Optional.ofNullable(ground.get(placed.pos())).map(Identifier::tryParse).flatMap(BuiltInRegistries.BLOCK::getOptional);
            removing.put(placed.pos(), before.orElse(Blocks.AIR).defaultBlockState());
        }
        for (var pos : gate.grass()) if (level.getBlockState(pos).is(Blocks.DIRT)) removing.put(pos, Blocks.GRASS_BLOCK.defaultBlockState());
        // Refuse the whole operation before touching the sign, the record or any block.
        Neighbors.checkRemoval(level, removing.keySet());
        removing.forEach(level::setBlockAndUpdate);
        gate.sign().map(level::getEntity).ifPresent(Entity::discard);
        ZoneData.get(server).remove(saved -> saved.id().equals(zone.id()));
        return new Removal(gate.placed().size() - kept, kept);
    }
}
