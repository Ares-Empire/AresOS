package dev.aresos.test;

import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.Level;

/** Test-only observation of every Level block write during placeholder-off provisioning. */
public final class ProvisioningAudit {
    private static MinecraftServer active;
    private static int writes;
    public static int completed;

    private ProvisioningAudit() { }

    public static void start(MinecraftServer server, boolean placeholder) {
        if (!placeholder) { active = server; writes = 0; }
    }

    public static void blockWrite(Level level) {
        if (active != null && level.getServer() == active) writes++;
    }

    public static void finish(MinecraftServer server, boolean placeholder) {
        if (placeholder) return;
        active = null;
        if (writes != 0) throw new AssertionError("Placeholder OFF attempted " + writes + " block writes");
        completed++;
    }
}
