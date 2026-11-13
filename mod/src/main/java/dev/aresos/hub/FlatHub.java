package dev.aresos.hub;

import com.mojang.math.Transformation;
import dev.aresos.AresOs;
import dev.aresos.catalogue.AppGroup;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Brightness;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.TagValueInput;
import org.joml.Vector3f;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/** Builds the fixed things of a flat home (docs/design/HUB.md 3.2): the home pad, the four avenues and their names. */
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
     * The one place the hub changes a block. It paves only the untouched ground with nothing standing on it;
     * anything else is his, or another build's, and stays. What it places is recorded with its position.
     */
    private static void place(ServerLevel level, BlockPos pos, String id, List<HubData.Placed> placed) {
        var ground = level.getBlockState(pos);
        var above = level.getBlockState(pos.above());
        if (!ground.is(Blocks.GRASS_BLOCK) || !above.isAir()) {
            AresOs.LOGGER.warn("AresOS hub: left {} unbuilt, something stands there (ground {}, above it {})", pos.toShortString(), ground, above);
            return;
        }
        Block block = BuiltInRegistries.BLOCK.getValue(Identifier.parse(id));
        level.setBlock(pos, block.defaultBlockState(), Block.UPDATE_CLIENTS);
        placed.add(new HubData.Placed(pos.immutable(), id));
    }

    /** The group's name over its avenue: a text display, so it cannot be hit or broken in either mode. */
    private static UUID name(ServerLevel level, BlockPos home, AppGroup group) throws IOException {
        // A display's settings have no public setters; its saved form is the one /summon takes.
        var tag = new CompoundTag();
        tag.store(Display.TextDisplay.TAG_TEXT, ComponentSerialization.CODEC, level.registryAccess().createSerializationContext(NbtOps.INSTANCE),
                Component.literal(group.title().toUpperCase(Locale.ROOT)).withColor(group.colour()));
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
