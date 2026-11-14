package dev.aresos.zone;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.world.NetherHome;
import net.minecraft.core.BlockPos;
import net.minecraft.core.UUIDUtil;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * A box that opens an app when the host steps into it, with the blocks the mod built for it ({@code blocks}, which
 * Live mode protects). A gate also records what it placed, so it can be taken down again.
 */
public record AppZone(String id, String app, ResourceKey<Level> dimension, BlockPos min, BlockPos max,
                      NetherHome.Home exit, List<BlockPos> blocks, Optional<Gate> gate) {
    /** One block the mod placed, with the block's ID as text. */
    public record Placed(BlockPos pos, String block) {
        public static final Codec<Placed> CODEC = RecordCodecBuilder.create(i -> i.group(
                BlockPos.CODEC.fieldOf("pos").forGetter(Placed::pos),
                Codec.STRING.fieldOf("block").forGetter(Placed::block)).apply(i, Placed::new));
    }

    /**
     * What makes a zone a gate: every block placed for it (the logo, the light blocks, the doormat), the ground
     * blocks the doormat replaced, the sign's entity, and the grass under it. Removal takes a block away only while
     * it is still the recorded one.
     *
     * @param signPlan where a gate built by hand ({@code /aresos logo}) placed its sign and what it said (review fixes
     *                 2, point 2): removal takes the sign down only while it is still that. Empty in records of
     *                 packages 33 to 35, in records an older mod wrote again (it reads the field and drops it), and in
     *                 the town's records, whose signs the town checks against its own plan: such a sign is never
     *                 taken down by {@code /aresos logo remove}
     */
    public record Gate(List<Placed> placed, List<Placed> ground, Optional<UUID> sign, List<BlockPos> grass, Optional<GatePlan.Sign> signPlan) {
        public static final Codec<Gate> CODEC = RecordCodecBuilder.create(i -> i.group(
                Placed.CODEC.listOf().fieldOf("placed").forGetter(Gate::placed),
                Placed.CODEC.listOf().fieldOf("ground").forGetter(Gate::ground),
                UUIDUtil.CODEC.optionalFieldOf("sign").forGetter(Gate::sign),
                BlockPos.CODEC.listOf().optionalFieldOf("grass", List.of()).forGetter(Gate::grass),
                GatePlan.Sign.CODEC.optionalFieldOf("sign_plan").forGetter(Gate::signPlan)).apply(i, Gate::new));

        /** A record that does not know its sign's place and text. */
        public Gate(List<Placed> placed, List<Placed> ground, Optional<UUID> sign, List<BlockPos> grass) {
            this(placed, ground, sign, grass, Optional.empty());
        }

        public Gate(List<Placed> placed, List<Placed> ground, Optional<UUID> sign) {
            this(placed, ground, sign, List.of());
        }
    }

    // Walls, floors and hand-made zones have no "gate" field, in files written before gates existed and now.
    // An older mod reading a newer file skips the field and sees a zone with protected blocks.
    public static final Codec<AppZone> CODEC = RecordCodecBuilder.create(i -> i.group(
            Codec.STRING.fieldOf("id").forGetter(AppZone::id),
            Codec.STRING.fieldOf("app").forGetter(AppZone::app),
            Level.RESOURCE_KEY_CODEC.fieldOf("dimension").forGetter(AppZone::dimension),
            BlockPos.CODEC.fieldOf("min").forGetter(AppZone::min),
            BlockPos.CODEC.fieldOf("max").forGetter(AppZone::max),
            NetherHome.Home.CODEC.fieldOf("exit").forGetter(AppZone::exit),
            BlockPos.CODEC.listOf().fieldOf("blocks").forGetter(AppZone::blocks),
            Gate.CODEC.optionalFieldOf("gate").forGetter(AppZone::gate)).apply(i, AppZone::new));

    public AppZone(String id, String app, ResourceKey<Level> dimension, BlockPos min, BlockPos max,
                   NetherHome.Home exit, List<BlockPos> blocks) {
        this(id, app, dimension, min, max, exit, blocks, Optional.empty());
    }

    public boolean isGate() { return gate.isPresent(); }

    /** A gate with everything in front of it, out to its exit point: where "here" means this gate. */
    public AABB area() {
        var area = box().minmax(new AABB(BlockPos.containing(exit.position())));
        for (var pos : blocks) area = area.minmax(new AABB(pos));
        return area;
    }

    public AABB box() { return new AABB(min.getX(), min.getY(), min.getZ(), max.getX() + 1, max.getY() + 1, max.getZ() + 1); }
    public boolean touchesPlayer(Vec3 feet) {
        return box().intersects(standingBody(feet));
    }

    public static AABB standingBody(Vec3 feet) {
        return new AABB(feet.x - 0.3, feet.y, feet.z - 0.3, feet.x + 0.3, feet.y + 1.8, feet.z + 0.3);
    }

    public boolean blocksExit(NetherHome.Home home) {
        return dimension.equals(home.dimension()) && blocks.stream().anyMatch(pos -> new AABB(pos).intersects(standingBody(home.position())));
    }

    public static NetherHome.Home exit(ResourceKey<Level> dimension, Vec3 position, AABB box) {
        var center = box.getCenter();
        float yaw = (float)Math.toDegrees(Math.atan2(-(center.x - position.x), center.z - position.z));
        // NBT canonicalizes signed zero; create that same value so exits round-trip exactly.
        if (yaw == 0) yaw = 0;
        return new NetherHome.Home(dimension, position, yaw, 0);
    }
}
