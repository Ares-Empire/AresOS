package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.launch.AppLauncher;
import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.config.AppDefinition;
import dev.aresos.shell.ShellClient;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.test.mixin.MinecraftTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.ZoneData;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.CopyOnWriteArrayList;

/** Package 24: the AresOS (Linux) launcher and focus handling inside the game, driven without a real helper. */
public final class ShellFocusClientGameTest implements FabricClientGameTest {
    private static final int Y = 150;
    private static final Vec3 EXIT = new Vec3(0.5, Y, -1.5);

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var opened = new CopyOnWriteArrayList<String>();
        var previousLauncher = context.computeOnClient(client -> AresOsClient.replaceLauncher(command -> {
            opened.add(String.join(" ", command));
            return CompletableFuture.completedFuture(null);
        }));
        try {
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(List.of(
                    new AppDefinition("notepad", "Notepad", List.of(), "minecraft:writable_book", false, "helper", null, null))));
            try (var world = context.worldBuilder().create()) {
                world.getServer().runOnServer(server -> {
                    var level = world.getConnection().getServerLevel();
                    for (int x = -4; x <= 6; x++) for (int z = -4; z <= 8; z++)
                        level.setBlockAndUpdate(new BlockPos(x, Y - 1, z), Blocks.STONE.defaultBlockState());
                    DesktopWorld.setEnabled(server, true);
                    world.getConnection().getServerPlayer().setGameMode(GameType.SURVIVAL);
                    var min = new BlockPos(0, Y, 2);
                    ZoneData.get(server).add(new AppZone("shell-notepad", "notepad", level.dimension(), min, min.offset(1, 1, 3),
                            AppZone.exit(level.dimension(), EXIT, new AABB(min)), List.of()));
                });
                move(context, world, EXIT);
                context.runOnClient(client -> check(ShellFocusClient.readyWorld(client) != null,
                        "The loaded desktop world was not reported ready"));

                // Without a helper the Linux launcher never runs anything and says why.
                context.runOnClient(client -> {
                    AresOsClient.replaceLauncher(new LinuxAppLauncher(() -> null));
                    AresOsClient.launch("notepad");
                });
                context.waitFor(client -> overlay(client).equals("Couldn't open Notepad: app helper unavailable"));
                context.runOnClient(client -> AresOsClient.replaceLauncher(command -> {
                    opened.add(String.join(" ", command));
                    return CompletableFuture.completedFuture(null);
                }));

                // Walk into the logo: the launch goes out, then the helper reports the app in front.
                move(context, world, new Vec3(0.5, Y, 3.5));
                context.waitFor(client -> opened.size() == 1);
                context.runOnClient(client -> {
                    client.options.keyUp.setDown(true);
                    ShellFocusClient.apply(client, new ShellClient.Focus(false, "app_activated", "notepad", false));
                    check(!client.options.keyUp.isDown(), "A held key survived the app taking focus");
                    check(!client.mouseHandler.isMouseGrabbed(), "The pointer stayed captured behind the app");
                    check(client.player.position().distanceToSqr(new Vec3(0.5, Y, 3.5)) < 0.01,
                            "Background focus moved the player");
                    ShellFocusClient.apply(client, new ShellClient.Focus(true, "app_closed", "notepad", true));
                });
                world.getConnection().waitForServerboundPackets();
                context.waitFor(client -> client.player.position().distanceToSqr(EXIT) < 0.01);
                context.runOnClient(client -> check(opened.size() == 1, "Focus return relaunched the app: " + opened));

                // Without window tracking a launch counts once started and a failure can follow later. Launches are
                // told apart by request ID: the first Notepad's late failure must not end the second one's visit.
                var requests = new java.util.concurrent.atomic.AtomicInteger();
                context.runOnClient(client -> AresOsClient.replaceLauncher(new AppLauncher() {
                    @Override public CompletionStage<Void> launch(List<String> command) {
                        throw new AssertionError("Tracked launches only");
                    }
                    @Override public CompletionStage<String> launchTracked(AppDefinition app) {
                        opened.add(app.id());
                        return CompletableFuture.completedFuture("r-" + requests.incrementAndGet());
                    }
                }));
                // The real return path: the app takes the screen (focus lost), the first launch's failure arrives,
                // the owner comes back (focus regained). Only the second launch's own focus token returns the player.
                boolean pauseSetting = context.computeOnClient(client -> client.options.pauseOnLostFocus);
                try {
                    context.runOnClient(client -> client.options.pauseOnLostFocus = false);
                    context.runOnClient(client -> AresOsClient.launch("notepad"));  // r-1, from the hotbar
                    move(context, world, new Vec3(0.5, Y, 3.5));  // r-2, walking into the logo
                    context.waitFor(client -> opened.size() == 3);
                    context.runOnClient(ShellFocusClientGameTest::loseFocus);
                    context.runOnClient(client -> AresOsClient.launchFailedLater("r-1", "notepad", "it failed to start"));
                    context.waitFor(client -> overlay(client).equals("Couldn't open Notepad: it failed to start"));
                    context.runOnClient(ShellFocusClientGameTest::regainFocus);
                    world.getConnection().waitForServerboundPackets();
                    context.waitFor(client -> client.player.position().distanceToSqr(EXIT) < 0.01);

                    // The logo launch's own late failure ends its visit: regaining focus no longer returns the player.
                    move(context, world, new Vec3(0.5, Y, 3.5));  // r-3
                    context.waitFor(client -> opened.size() == 4);
                    context.runOnClient(ShellFocusClientGameTest::loseFocus);
                    context.runOnClient(client ->
                            AresOsClient.launchFailedLater("r-3", "notepad", "no answer from the app helper"));
                    context.waitFor(client -> overlay(client).equals("Couldn't open Notepad: no answer from the app helper"));
                    context.runOnClient(ShellFocusClientGameTest::regainFocus);
                    world.getConnection().waitForServerboundPackets();
                    context.waitTicks(10);
                    context.runOnClient(client -> check(client.player.position().distanceToSqr(new Vec3(0.5, Y, 3.5)) < 0.01,
                            "A failed launch still teleported the player out of the logo"));
                } finally {
                    context.runOnClient(client -> {
                        ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(true);
                        client.options.pauseOnLostFocus = pauseSetting;
                    });
                }
                AresOs.LOGGER.info("24 shell focus checks passed: helper-less failure text, held keys and pointer "
                        + "released on background, logo return on foreground, a late failure ends only its own "
                        + "launch's visit, world readiness");
            }
        } finally {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(previousApps);
                AresOsClient.replaceLauncher(previousLauncher);
                AresOsClient.FOCUS_RETURN.reset();
                client.options.keyUp.setDown(false);
            });
        }
    }

    private static void move(ClientGameTestContext context, TestSingleplayerContext world, Vec3 point) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.teleportTo(player.level(), point.x, point.y, point.z, Set.of(), 0, 0, false);
            player.setDeltaMovement(Vec3.ZERO);
        });
        context.waitFor(client -> client.player.position().distanceToSqr(point) < 0.01);
        context.waitTicks(5);
    }

    private static void loseFocus(net.minecraft.client.Minecraft client) {
        ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(false);
        ((MinecraftTestAccess) client).aresos$setLastActiveTime(0);
        ((MinecraftTestAccess) client).aresos$pauseIfInactive();
    }

    private static void regainFocus(net.minecraft.client.Minecraft client) {
        ((WindowTestAccess) (Object) client.getWindow()).aresos$setFocused(true);
        ((MinecraftTestAccess) client).aresos$pauseIfInactive();
    }

    private static String overlay(net.minecraft.client.Minecraft client) {
        var message = ((HudTestAccess) client.gui.hud).aresos$overlayMessage();
        return message == null ? "" : message.getString();
    }

    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
}
