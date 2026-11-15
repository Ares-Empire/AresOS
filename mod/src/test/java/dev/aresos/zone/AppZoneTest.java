package dev.aresos.zone;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.UUIDUtil;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/** Review fixes 2, point 3: a hand-built gate's sign plan, and what a mod of packages 33 to 35 does with it. */
class AppZoneTest {
    /** The gate's codec of packages 33 to 35 (AppZone.java on main), without "sign_plan". */
    private static final Codec<AppZone.Gate> OLDER = RecordCodecBuilder.create(i -> i.group(
            AppZone.Placed.CODEC.listOf().fieldOf("placed").forGetter(AppZone.Gate::placed),
            AppZone.Placed.CODEC.listOf().fieldOf("ground").forGetter(AppZone.Gate::ground),
            UUIDUtil.CODEC.optionalFieldOf("sign").forGetter(AppZone.Gate::sign),
            BlockPos.CODEC.listOf().optionalFieldOf("grass", List.of()).forGetter(AppZone.Gate::grass)).apply(i, AppZone.Gate::new));

    @BeforeAll static void bootstrap() {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
    }

    @Test void anOlderModReadsAGateWithItsSignPlanAndDropsThePlanWhenItWritesTheGateAgain() {
        var plan = new GatePlan.Sign(new Vec3(10.5, 70.0625, -3.25), "Terminal", "term");
        var gate = new AppZone.Gate(List.of(new AppZone.Placed(new BlockPos(1, 2, 3), "minecraft:stone")), List.of(),
                Optional.of(UUID.randomUUID()), List.of(new BlockPos(1, 1, 3)), Optional.of(plan));
        var saved = AppZone.Gate.CODEC.encodeStart(NbtOps.INSTANCE, gate).getOrThrow();
        assertEquals(gate, AppZone.Gate.CODEC.parse(NbtOps.INSTANCE, saved).getOrThrow(), "this mod reads it back whole");

        // An older mod reads the record without an error and keeps the gate; the field it does not know is dropped.
        var older = OLDER.parse(NbtOps.INSTANCE, saved).getOrThrow();
        assertEquals(new AppZone.Gate(gate.placed(), gate.ground(), gate.sign(), gate.grass()), older);
        // When it writes zones.dat again the field is gone, and this mod reads a record without it (point 2).
        var rewritten = (CompoundTag)OLDER.encodeStart(NbtOps.INSTANCE, older).getOrThrow();
        assertFalse(rewritten.contains("sign_plan"));
        assertEquals(Optional.empty(), AppZone.Gate.CODEC.parse(NbtOps.INSTANCE, rewritten).getOrThrow().signPlan());

        // A sign with no short name, and one with a blank short name, are saved the same way.
        var bare = new GatePlan.Sign(Vec3.ZERO, "Notes", null);
        assertEquals(bare, GatePlan.Sign.CODEC.parse(NbtOps.INSTANCE, GatePlan.Sign.CODEC.encodeStart(NbtOps.INSTANCE, bare).getOrThrow()).getOrThrow());
        assertEquals(bare, GatePlan.Sign.CODEC.parse(NbtOps.INSTANCE, GatePlan.Sign.CODEC.encodeStart(NbtOps.INSTANCE, new GatePlan.Sign(Vec3.ZERO, "Notes", " ")).getOrThrow()).getOrThrow());
    }
}
