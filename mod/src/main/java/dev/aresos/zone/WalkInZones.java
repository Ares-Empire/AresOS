package dev.aresos.zone;

import dev.aresos.AresOs;
import dev.aresos.hub.HubData;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import dev.aresos.world.HomeSites;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.phys.Vec3;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

public final class WalkInZones {
    private record Pending(long visit, AppZone zone) { }
    private static final class State {
        final Map<UUID, Set<String>> inside = new HashMap<>();
        final Map<UUID, Pending> pending = new HashMap<>();
    }
    // Desktop off/on and rejoining discard State; an older client cancellation must not match a new visit.
    private static final java.util.concurrent.atomic.AtomicLong VISITS = new java.util.concurrent.atomic.AtomicLong();
    private static final Map<MinecraftServer, State> STATES = new WeakHashMap<>();
    private WalkInZones() { }

    public static void register() {
        PayloadTypeRegistry.clientboundPlay().register(ZoneLaunchPayload.TYPE, ZoneLaunchPayload.CODEC);
        PayloadTypeRegistry.serverboundPlay().register(ZoneReturnPayload.TYPE, ZoneReturnPayload.CODEC);
        ServerPlayNetworking.registerGlobalReceiver(ZoneReturnPayload.TYPE,
                (payload, context) -> returned(context.player(), payload));
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (!DesktopWorld.isEnabled(server)) { STATES.remove(server); return; }
            for (var player : server.getPlayerList().getPlayers()) tick(player);
        });
        ServerLifecycleEvents.SERVER_STOPPED.register(STATES::remove);
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
            var state = STATES.get(server);
            if (state != null) { state.inside.remove(handler.player.getUUID()); state.pending.remove(handler.player.getUUID()); }
        });
        PlayerBlockBreakEvents.BEFORE.register((level, player, pos, block, entity) -> {
            if (!(player instanceof ServerPlayer host)) return true;
            String refusal = isProtected(host, pos) ? "Auto-built logo protected. Press G for Build mode." : HubData.protection(host, pos);
            if (refusal == null) return true;
            host.sendSystemMessage(Component.literal(refusal), true);
            return false;
        });
    }

    public static boolean isProtected(ServerPlayer player, net.minecraft.core.BlockPos pos) {
        return LiveMode.isLive(player) && ZoneData.get(player.level().getServer()).zones().stream()
                .anyMatch(zone -> zone.dimension().equals(player.level().dimension()) && zone.blocks().contains(pos));
    }

    /**
     * He was just moved (package 37, {@code /go}): a zone he touches where he arrives is not walked into. He opens it
     * by stepping out and in again, as after joining inside one.
     */
    public static void arrived(ServerPlayer player) {
        var state = STATES.get(player.level().getServer());
        if (state != null) state.inside.put(player.getUUID(), membership(touching(player)));
    }

    private static java.util.List<AppZone> touching(ServerPlayer player) {
        return ZoneData.get(player.level().getServer()).zones().stream().filter(zone -> zone.dimension().equals(player.level().dimension())
                && zone.box().intersects(player.getBoundingBox())).toList();
    }

    private static Set<String> membership(java.util.List<AppZone> touching) {
        return touching.stream().map(AppZone::id).collect(java.util.stream.Collectors.toUnmodifiableSet());
    }

    private static void tick(ServerPlayer player) {
        var server = player.level().getServer();
        if (!DesktopWorld.isHost(server, player)) return;
        var state = STATES.computeIfAbsent(server, ignored -> new State());
        var touching = touching(player);
        var previous = state.inside.put(player.getUUID(), membership(touching));
        // Joining inside is not an entry. Tracking Build movement also prevents a launch when switching mode inside.
        if (previous == null || !LiveMode.isLive(player)) return;
        var entered = touching.stream().filter(zone -> !previous.contains(zone.id())).toList();
        if (entered.isEmpty()) return;
        // Launching two programs would overwrite return ownership. Consume both entries and ask for an unambiguous re-entry.
        if (entered.size() > 1) {
            player.sendSystemMessage(Component.literal("Entered multiple logo zones. Step fully outside, then enter one logo at a time."));
            return;
        }
        var current = entered.getFirst();
        if (AresOs.app(current.app()) == null) {
            player.sendSystemMessage(Component.literal("Unknown AresOS app: " + current.app()));
            return;
        }
        if (!ServerPlayNetworking.canSend(player, ZoneLaunchPayload.TYPE)) return;
        long visit = VISITS.incrementAndGet();
        state.pending.put(player.getUUID(), new Pending(visit, current));
        player.level().playSound(null, player.blockPosition(), SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, 0.5f, 1.2f);
        player.level().sendParticles(ParticleTypes.PORTAL, player.getX(), player.getY() + 1, player.getZ(), 24, 0.4, 0.6, 0.4, 0.1);
        ServerPlayNetworking.send(player, new ZoneLaunchPayload(current.app(), visit));
    }

    private static void returned(ServerPlayer player, ZoneReturnPayload payload) {
        var server = player.level().getServer();
        var state = STATES.get(server);
        if (state == null || !DesktopWorld.isHost(server, player)) return;
        var pending = state.pending.get(player.getUUID());
        if (pending == null || pending.visit != payload.visit()) return;
        state.pending.remove(player.getUUID());
        if (!payload.returned() || !LiveMode.isLive(player)) return;
        if (ZoneData.get(server).zones().stream().noneMatch(zone -> zone.id().equals(pending.zone.id()))) return;
        var exit = pending.zone.exit();
        var level = server.getLevel(exit.dimension());
        if (level == null || !HomeSites.isSafe(level, exit.position())) {
            player.sendSystemMessage(Component.literal("Logo exit is obstructed. Clear it in Build mode; return teleport was refused."));
            return;
        }
        player.stopRiding();
        player.teleportTo(level, exit.position().x, exit.position().y, exit.position().z, Set.of(), exit.yaw(), exit.pitch(), false);
        player.setDeltaMovement(Vec3.ZERO); player.fallDistance = 0; player.clearFire();
        state.inside.put(player.getUUID(), Set.of());
    }
}
