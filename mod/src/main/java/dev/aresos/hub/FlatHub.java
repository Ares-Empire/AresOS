package dev.aresos.hub;

import com.mojang.math.Transformation;
import dev.aresos.AresOs;
import dev.aresos.catalogue.AppGroup;
import dev.aresos.mixin.DisplayAccess;
import dev.aresos.mixin.TextDisplayAccess;
import dev.aresos.zone.Placing;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Brightness;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.TagValueInput;
import org.joml.Vector3f;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;

/**
 * Builds the fixed things of a flat home (docs/design/HUB.md 3.2): the home pad, the four avenues and their names.
 * The town keeps them in step later ({@link #pave}, {@link #count}): an avenue grows with its group and is never
 * unpaved, and a group's name shows how many apps stand in it.
 */
public final class FlatHub {
    private FlatHub() { }

    /** Builds around {@code home}, the block he stands in, and returns what was placed. Called once per world. */
    public static HubData.Fixed build(ServerLevel level, BlockPos home) throws IOException {
        var placed = new ArrayList<HubData.Placed>();
        for (int x = -HubLayout.PAD_REACH; x <= HubLayout.PAD_REACH; x++) {
            for (int z = -HubLayout.PAD_REACH; z <= HubLayout.PAD_REACH; z++) {
                place(level, home.offset(x, -1, z), x == 0 && z == 0 ? HubLayout.HOME_MARK : HubLayout.PAVING, placed);
            }
        }
        int side = HubLayout.ROAD / 2;
        for (AppGroup group : AppGroup.clockwise()) {
            // Row 0 with no logos yet; package 36 extends an avenue when its group grows.
            for (int outward = HubLayout.AVENUE_START; outward <= HubLayout.avenueEnd(0); outward++) {
                for (int sideways = -side; sideways <= side; sideways++) {
                    place(level, group.block(home, outward, sideways, -1), sideways == 0 ? group.concrete() : HubLayout.PAVING, placed);
                }
            }
        }
        var names = new ArrayList<UUID>();
        for (AppGroup group : AppGroup.clockwise()) names.add(name(level, home, group));
        return new HubData.Fixed(placed, names);
    }

    /**
     * Paves a group's avenue on to outward {@code avenueEnd(row)} (HUB.md 3.2), never back: it goes on from the
     * farthest road block the record holds, or from where package 32 ended it, through the same {@link #place} as the
     * first build, so it covers only untouched grass and records every block in {@code hub.dat}. It paves whole rows,
     * nearest first, and stops at the first row whose ground is not loaded; no chunk is loaded for it.
     *
     * @return false when part of the road waits for its ground to be loaded
     */
    public static boolean pave(ServerLevel level, HubData hub, AppGroup group, int row) {
        BlockPos home = hub.home().pos();
        int side = HubLayout.ROAD / 2;
        var placed = new ArrayList<HubData.Placed>();
        boolean loaded = true;
        for (int outward = Math.max(HubLayout.avenueEnd(0), reach(hub, group)) + 1; outward <= HubLayout.avenueEnd(row); outward++) {
            for (int sideways = -side; sideways <= side; sideways++) loaded &= loaded(level, group.block(home, outward, sideways, -1));
            if (!loaded) break;
            for (int sideways = -side; sideways <= side; sideways++)
                place(level, group.block(home, outward, sideways, -1), sideways == 0 ? group.concrete() : HubLayout.PAVING, placed);
        }
        hub.pave(placed);
        return loaded;
    }

    /**
     * Whether a block's chunk is loaded now, with its entities, as a gate asks it. A chunk the server has only
     * scheduled says it is there too, and reading a block of it would load it on the spot.
     */
    private static boolean loaded(ServerLevel level, BlockPos pos) {
        return level.hasChunkAt(pos) && level.areEntitiesLoaded(ChunkPos.pack(pos));
    }

    /**
     * The farthest outward index of this group's avenue that the record holds. A road block he changed has left the
     * record; where it was the last one, the road may be paved there again only if he left untouched grass.
     */
    private static int reach(HubData hub, AppGroup group) {
        var home = hub.home().pos();
        var out = group.outward();
        var right = group.right();
        int reach = 0;
        for (var block : hub.fixed().blocks()) {
            var at = block.pos().subtract(home);
            if (at.getY() != -1) continue;
            int outward = at.getX() * out.getStepX() + at.getZ() * out.getStepZ();
            int sideways = at.getX() * right.getStepX() + at.getZ() * right.getStepZ();
            if (outward >= HubLayout.AVENUE_START && Math.abs(sideways) <= HubLayout.ROAD / 2) reach = Math.max(reach, outward);
        }
        return reach;
    }

    /**
     * Writes how many apps stand in a group on its name: {@code INTERNET · 2} (HUB.md 2.6).
     *
     * @return false when the name's ground or its entities are not loaded yet, so it could not be written now
     */
    public static boolean count(ServerLevel level, HubData hub, AppGroup group, int apps) {
        int index = AppGroup.clockwise().indexOf(group);
        if (index >= hub.fixed().names().size()) return true;
        BlockPos at = group.block(hub.home().pos(), HubLayout.NAME_OUTWARD, 0, HubLayout.NAME_HEIGHT);
        if (!loaded(level, at)) return false;
        // A name that is gone (only a command can remove one) stays gone; there is nothing to write on.
        if (level.getEntity(hub.fixed().names().get(index)) instanceof Display.TextDisplay name) {
            ((TextDisplayAccess) name).aresos$setText(title(group, apps));
            // A name that an earlier version built larger takes today's size with its count, so the count fits.
            ((DisplayAccess) name).aresos$setTransformation(new Transformation(null, null, new Vector3f(HubLayout.NAME_SCALE), null));
        }
        return true;
    }

    /** A group's name as it hangs over its avenue; with the count once the town has stood up. */
    public static Component title(AppGroup group, Integer apps) {
        return Component.literal(group.title().toUpperCase(Locale.ROOT) + (apps == null ? "" : " \u00b7 " + apps)).withColor(group.colour());
    }

    /**
     * Paves one block through {@link Placing}, the one way the mod changes a block, and records what it placed. The
     * pad and roads go on the untouched grass only, with nothing standing on it; anything else is his, or another
     * build's, and stays. No neighbour updates: paving the ground changes nothing around it.
     */
    private static void place(ServerLevel level, BlockPos pos, String id, List<HubData.Placed> placed) {
        var ground = level.getBlockState(pos);
        var change = ground.is(Blocks.GRASS_BLOCK) ? Placing.set(level, pos, null, Placing.state(id), Block.UPDATE_CLIENTS) : Optional.<Placing.Change>empty();
        change.ifPresentOrElse(done -> placed.add(new HubData.Placed(done.pos(), done.block())),
                () -> AresOs.LOGGER.warn("AresOS hub: left {} unbuilt, something stands there (ground {}, above it {})", pos.toShortString(),
                        ground, level.getBlockState(pos.above())));
    }

    /** The group's name over its avenue: a text display, so it cannot be hit or broken in either mode. */
    private static UUID name(ServerLevel level, BlockPos home, AppGroup group) throws IOException {
        // A display's settings have no public setters; its saved form is the one /summon takes.
        var tag = new CompoundTag();
        tag.store(Display.TextDisplay.TAG_TEXT, ComponentSerialization.CODEC, level.registryAccess().createSerializationContext(NbtOps.INSTANCE),
                title(group, null));
        tag.store(Display.TAG_BILLBOARD, Display.BillboardConstraints.CODEC, Display.BillboardConstraints.VERTICAL);
        tag.store(Display.TAG_BRIGHTNESS, Brightness.CODEC, Brightness.FULL_BRIGHT);
        tag.putFloat(Display.TAG_VIEW_RANGE, HubLayout.NAME_VIEW_RANGE);
        // The game keeps this tag's name private; "background" is the saved form's own word for it.
        tag.putInt("background", HubLayout.NAME_BACKGROUND);
        tag.store(Display.TAG_TRANSFORMATION, Transformation.EXTENDED_CODEC,
                new Transformation(null, null, new Vector3f(HubLayout.NAME_SCALE), null));
        var display = EntityType.create(EntityTypes.TEXT_DISPLAY, TagValueInput.create(ProblemReporter.DISCARDING, level.registryAccess(), tag),
                level, EntitySpawnReason.COMMAND).orElseThrow(() -> new IOException("Could not create the name of " + group.title()));
        BlockPos at = group.block(home, HubLayout.NAME_OUTWARD, 0, HubLayout.NAME_HEIGHT);
        display.snapTo(at.getX() + 0.5, at.getY(), at.getZ() + 0.5, 0, 0);
        if (!level.addFreshEntity(display)) throw new IOException("Could not place the name of " + group.title());
        return display.getUUID();
    }
}
