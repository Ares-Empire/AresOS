package dev.aresos.test;

import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;
import java.util.List;

/** Counts additions, including mobs removed before the next assertion. Accessed only on the server thread. */
final class MobAdditions implements AutoCloseable {
    private static final List<MobAdditions> ACTIVE = new ArrayList<>();

    static {
        ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> {
            if (!(entity instanceof Mob)) return;
            for (var counter : ACTIVE) {
                if (counter.level == level && (counter.area == null || counter.area.contains(entity.position()))) {
                    counter.count++;
                    if (counter.examples.size() < 8) counter.examples.add(entity.getType().toShortString() + " at " + entity.blockPosition());
                }
            }
        });
    }

    private final ServerLevel level;
    private final AABB area;
    private int count;
    private final List<String> examples = new ArrayList<>();

    MobAdditions(ServerLevel level, AABB area) {
        this.level = level;
        this.area = area;
        ACTIVE.add(this);
    }

    int count() { return count; }
    List<String> examples() { return List.copyOf(examples); }
    void reset() { count = 0; examples.clear(); }
    @Override public void close() { ACTIVE.remove(this); }
}
