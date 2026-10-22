package dev.aresos.zone;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.world.NetherHome;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;

public record AppZone(String id, String app, ResourceKey<Level> dimension, BlockPos min, BlockPos max,
                      NetherHome.Home exit, List<BlockPos> blocks) {
    public static final Codec<AppZone> CODEC = RecordCodecBuilder.create(i -> i.group(
            Codec.STRING.fieldOf("id").forGetter(AppZone::id),
            Codec.STRING.fieldOf("app").forGetter(AppZone::app),
            Level.RESOURCE_KEY_CODEC.fieldOf("dimension").forGetter(AppZone::dimension),
            BlockPos.CODEC.fieldOf("min").forGetter(AppZone::min),
            BlockPos.CODEC.fieldOf("max").forGetter(AppZone::max),
            NetherHome.Home.CODEC.fieldOf("exit").forGetter(AppZone::exit),
            BlockPos.CODEC.listOf().fieldOf("blocks").forGetter(AppZone::blocks)).apply(i, AppZone::new));

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
