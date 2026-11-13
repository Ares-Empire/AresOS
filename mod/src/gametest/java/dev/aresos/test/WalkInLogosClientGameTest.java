package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.config.AppDefinition;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.MinecraftTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.*;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public final class WalkInLogosClientGameTest implements FabricClientGameTest {
    private static final int Y = 150;
    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var calls = new CopyOnWriteArrayList<List<String>>();
        var previousLauncher = context.computeOnClient(client -> AresOsClient.replaceLauncher(command -> {
            calls.add(List.copyOf(command)); return CompletableFuture.completedFuture(null);
        }));
        try {
            Path icon = Path.of("walk-in-fixtures/compass.png").toAbsolutePath();
            Files.createDirectories(icon.getParent());
            try (var input = getClass().getResourceAsStream("/icons/compass.png")) {
                Files.copy(input, icon, StandardCopyOption.REPLACE_EXISTING);
            }
            var notes = new AppDefinition("zone-notes", "Zone Notes", List.of("fixture-notes.exe"), "minecraft:book", false,
                    "command", null, icon.toString());
            var site = new AppDefinition("zone-site", "Zone Site", List.of(), "minecraft:paper", false,
                    "url", "https://example.test/zone", icon.toString());
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(List.of(notes, site)));
            TestWorldSave save;
            List<AppZone> savedZones;
            try (var world = context.worldBuilder().adjustSettings(settings -> {
                settings.setGameMode(net.minecraft.client.gui.screens.worldselection.WorldCreationUiState.SelectedGameMode.SURVIVAL);
                settings.setAllowCommands(false);
            }).create()) {
                save = world.getWorldSave();
                world.getConnection().waitForChunksRender();
                world.getServer().runOnServer(server -> {
                    check(!server.getWorldData().isAllowCommands(), "Test has cheats enabled");
                    var level = world.getConnection().getServerLevel();
                    // Elevated deterministic fixtures avoid world generation and never touch real saves.
                    for (int x = -24; x <= 85; x++) for (int z = -28; z <= 34; z++) {
                        level.setBlock(new BlockPos(x, Y - 2, z), Blocks.STONE.defaultBlockState(), 2);
                        if (x < 40 || z < -2) level.setBlock(new BlockPos(x, Y - 1, z), Blocks.STONE.defaultBlockState(), 2);
                    }
                });
                move(context, world, new Vec3(0.5, Y, 5.5));
                command(context, world, "aresos zone pos1");
                world.getServer().runOnServer(server -> check(ZoneData.get(server).zones().isEmpty(), "Normal command created a zone"));
                command(context, world, "aresos desktop on");
                world.getServer().runOnServer(server -> {
                    var guest = new ServerPlayer(server, world.getConnection().getServerLevel(), new GameProfile(UUID.randomUUID(), "Guest"), ClientInformation.createDefault());
                    try {
                        for (var cmd : List.of("aresos zone pos1", "aresos zone pos2", "aresos zone set zone-notes",
                                "aresos zone list", "aresos zone remove zone-notes", "aresos logo zone-notes floor"))
                            check(server.getCommands().getDispatcher().execute(cmd, server.createCommandSourceStack().withEntity(guest)) == 0, "Guest command accepted: " + cmd);
                    } catch (com.mojang.brigadier.exceptions.CommandSyntaxException error) { throw new AssertionError(error); }
                });
                mark(context, world, "zone-notes", new Vec3(-1.5, Y, 10.5), new Vec3(1.5, Y, 12.5), new Vec3(0.5, Y, 5.5));
                check(zoneCount(world) == 1, "Zone set failed without cheats");
                command(context, world, "aresos zone set zone-site");
                check(zoneCount(world) == 1, "Overlapping zone accepted");
                command(context, world, "aresos zone list");
                move(context, world, new Vec3(0.5, Y, 11.5));
                context.waitFor(client -> calls.size() == 1);
                check(calls.getFirst().equals(notes.command()), "Wrong program launched");
                context.waitTicks(20); check(calls.size() == 1, "Standing inside relaunched");
                focusRoundTrip(context, true);
                world.getConnection().waitForServerboundPackets();
                context.waitFor(client -> client.player.position().distanceToSqr(new Vec3(0.5, Y, 5.5)) < 0.01);
                context.waitTicks(12); check(calls.size() == 1, "Return retriggered zone");
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    var towardLogo = new Vec3(0, Y, 11.5).subtract(player.position()).normalize();
                    check(player.getLookAngle().dot(towardLogo) > 0.99, "Exit does not face logo: " + player.getYRot());
                });
                move(context, world, new Vec3(0.5, Y, 11.5));
                context.waitFor(client -> calls.size() == 2);
                focusRoundTrip(context, false);
                context.waitFor(client -> client.player.position().distanceToSqr(new Vec3(0.5, Y, 5.5)) < 0.01);
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE);
                move(context, world, new Vec3(0.5, Y, 11.5));
                world.getServer().runOnServer(server -> net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.send(
                        world.getConnection().getServerPlayer(), new ZoneLaunchPayload(notes.id(), 999)));
                context.waitTicks(8); check(calls.size() == 2, "Build entry launched");
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.SURVIVAL);
                context.waitTicks(8); check(calls.size() == 2, "Live switch inside launched");
                move(context, world, new Vec3(0.5, Y, 5.5));
                command(context, world, "aresos desktop off");
                move(context, world, new Vec3(0.5, Y, 11.5));
                world.getServer().runOnServer(server -> net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.send(
                        world.getConnection().getServerPlayer(), new ZoneLaunchPayload(notes.id(), 1000)));
                context.waitTicks(8); check(calls.size() == 2, "Normal world entry launched");
                command(context, world, "aresos zone remove here");
                command(context, world, "aresos logo zone-notes");
                check(zoneCount(world) == 1, "Normal world commands edited zones");
                command(context, world, "aresos desktop on");
                context.waitTicks(8); check(calls.size() == 2, "Enabling marker inside launched");
                mark(context, world, "zone-site", new Vec3(9.5, Y, 10.5), new Vec3(11.5, Y, 12.5), new Vec3(10.5, Y, 5.5));
                move(context, world, new Vec3(10.5, Y, 11.5));
                context.waitFor(client -> calls.size() == 3);
                context.waitTicks(15);
                check(calls.size() == 3 && calls.getLast().equals(List.of(site.url())), "URL zone did not launch exactly once");
                focusRoundTrip(context, true);
                context.waitFor(client -> client.player.position().distanceToSqr(new Vec3(10.5, Y, 5.5)) < 0.01);
                context.runOnClient(client -> ClientPlayNetworking.send(new ZoneReturnPayload(Long.MAX_VALUE, true)));
                world.getConnection().waitForServerboundPackets();
                context.runOnClient(client -> check(client.player.position().distanceToSqr(new Vec3(10.5, Y, 5.5)) < 0.01, "Unowned return moved player"));

                // Reject occupied space before any block write, then build the full source icon.
                move(context, world, new Vec3(0.5, Y, -4.5));
                var wall = world.getServer().computeOnServer(server -> LogoBuilder.plan(world.getConnection().getServerPlayer(), notes.id(), read(notes), false));
                var obstruction = wall.blocks().keySet().iterator().next();
                world.getServer().runOnServer(server -> world.getConnection().getServerLevel().setBlockAndUpdate(obstruction, Blocks.DIAMOND_BLOCK.defaultBlockState()));
                command(context, world, "aresos logo zone-notes wall");
                check(zoneCount(world) == 2, "Obstructed logo created a zone");
                world.getServer().runOnServer(server -> {
                    var level = world.getConnection().getServerLevel();
                    check(level.getBlockState(obstruction).is(Blocks.DIAMOND_BLOCK), "Overwrote obstruction");
                    check(wall.blocks().keySet().stream().filter(p -> !p.equals(obstruction)).allMatch(p -> level.getBlockState(p).isAir()), "Failed logo partially wrote");
                    level.setBlockAndUpdate(obstruction, Blocks.AIR.defaultBlockState());
                });
                command(context, world, "aresos logo zone-notes wall");
                check(zoneCount(world) == 3, "Wall logo command failed");
                var savedWall = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().get(2));
                world.getServer().runOnServer(server -> {
                    check(wall.blocks().size() > 700, "Logo lost the 32x32 source resolution");
                    check(wall.blocks().entrySet().stream().allMatch(e -> world.getConnection().getServerLevel().getBlockState(e.getKey()).equals(e.getValue())), "Wall layout differs from converted fixture");
                    check(!world.getConnection().getServerPlayer().gameMode.destroyBlock(obstruction), "Live destroyed logo block");
                    check(world.getConnection().getServerLevel().getBlockState(obstruction).equals(wall.blocks().get(obstruction)), "Denied break changed block");
                });
                walkUntilLaunch(context, calls, 4);
                focusRoundTrip(context, true);
                context.waitFor(client -> client.player.position().distanceToSqr(savedWall.exit().position()) < 0.01);
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE);
                world.getServer().runOnServer(server -> {
                    check(world.getConnection().getServerPlayer().gameMode.destroyBlock(obstruction), "Build could not break logo");
                    check(world.getConnection().getServerLevel().getBlockState(obstruction).isAir(), "Build break left block");
                    world.getConnection().getServerLevel().setBlockAndUpdate(obstruction, wall.blocks().get(obstruction));
                });
                frame(world, savedWall);
                move(context, world, new Vec3(0.5, Y + 16, -27.5));
                fly(context, world);
                context.getInput().lookAt(0, 0);
                screenshot(context, world, "08-wall-logo-zone");

                move(context, world, new Vec3(64.5, Y, -4.5));
                context.getInput().lookAt(0, 0);
                command(context, world, "aresos logo zone-site floor");
                check(zoneCount(world) == 4, "Floor logo command failed");
                var savedFloor = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().get(3));
                world.getServer().runOnServer(server -> {
                    check(savedFloor.box().getYsize() == 2, "Floor zone is not on top");
                    check(savedFloor.blocks().stream().allMatch(p -> p.getY() == Y - 1), "Floor was built vertically");
                });
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.SURVIVAL);
                walkUntilLaunch(context, calls, 5);
                focusRoundTrip(context, true);
                context.waitFor(client -> client.player.position().distanceToSqr(savedFloor.exit().position()) < 0.01);
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.CREATIVE);
                frame(world, savedFloor);
                move(context, world, new Vec3(64.5, Y + 32, -19.5));
                fly(context, world);
                context.getInput().lookAt(0, 45);
                screenshot(context, world, "08-floor-logo-zone");
                // Rejoin while standing inside an owner zone must not look like a fresh entry.
                move(context, world, new Vec3(0.5, Y, 11.5));
                context.getInput().pressKey(InputConstants.KEY_G);
                context.waitFor(client -> client.gameMode.getPlayerMode() == GameType.SURVIVAL);
                savedZones = world.getServer().computeOnServer(server -> ZoneData.get(server).zones());
            }
            try (var reopened = save.open()) {
                reopened.getConnection().waitForChunksRender();
                context.waitTicks(12); check(calls.size() == 5, "Rejoining inside launched");
                reopened.getServer().runOnServer(server -> {
                    check(DesktopWorld.isEnabled(server) && ZoneData.get(server).zones().size() == 4, "Zones did not persist");
                    for (int i = 0; i < savedZones.size(); i++) {
                        var expected = savedZones.get(i); var actual = ZoneData.get(server).zones().get(i);
                        check(expected.id().equals(actual.id()) && expected.app().equals(actual.app()) && expected.dimension().equals(actual.dimension()), "Zone identity changed across rejoin");
                        check(expected.min().equals(actual.min()) && expected.max().equals(actual.max()), "Zone box changed across rejoin");
                        check(expected.exit().equals(actual.exit()), "Zone exit changed across rejoin: " + expected.exit() + " -> " + actual.exit());
                        check(expected.blocks().equals(actual.blocks()), "Zone protected blocks changed across rejoin");
                    }
                    var wall = ZoneData.get(server).zones().get(2);
                    check(WalkInZones.isProtected(reopened.getConnection().getServerPlayer(), wall.blocks().getFirst()), "Saved auto-logo lost protection");
                });
                command(context, reopened, "aresos zone remove here");
                check(zoneCount(reopened) == 3, "Remove here failed");
                command(context, reopened, "aresos zone remove zone-site");
                check(zoneCount(reopened) == 1, "Remove app did not remove all matching zones");
                move(context, reopened, new Vec3(0.5, Y, 5.5));
                move(context, reopened, new Vec3(0.5, Y, 11.5));
                context.waitTicks(8); check(calls.size() == 5, "Removed zone launched");
                context.runOnClient(client -> AresOsClient.replaceLauncher(command -> {
                    calls.add(List.copyOf(command)); return CompletableFuture.failedFuture(new java.io.IOException("Fixture launch failure"));
                }));
                move(context, reopened, new Vec3(0.5, Y, -4.5));
                move(context, reopened, new Vec3(0.5, Y, -2.5));
                context.waitFor(client -> calls.size() == 6);
                context.waitTicks(12); check(calls.size() == 6, "Failed launch retried while inside");
                context.runOnClient(client -> ClientPlayNetworking.send(new ZoneReturnPayload(1, true)));
                reopened.getConnection().waitForServerboundPackets();
                context.runOnClient(client -> check(client.player.position().distanceToSqr(new Vec3(0.5, Y, -2.5)) < 0.01, "Failed or stale launch teleported player"));
                context.runOnClient(client -> AresOsClient.replaceLauncher(command -> {
                    calls.add(List.copyOf(command)); return CompletableFuture.completedFuture(null);
                }));
                move(context, reopened, new Vec3(0.5, Y, -4.5));
                move(context, reopened, new Vec3(0.5, Y, -2.5));
                context.waitFor(client -> calls.size() == 7);
                // Leave an older successful launch armed while server membership/pending state is reset.
                command(context, reopened, "aresos desktop off");
                command(context, reopened, "aresos desktop on");
                move(context, reopened, new Vec3(0.5, Y, -4.5));
                move(context, reopened, new Vec3(0.5, Y, -2.5));
                context.waitFor(client -> calls.size() == 8);
                focusRoundTrip(context, true);
                context.waitFor(client -> client.player.position().distanceToSqr(new Vec3(0.5, Y, -4.5)) < 0.01);
                context.waitTicks(8); check(calls.size() == 8, "Reset-state return retriggered");
            }
            AresOs.LOGGER.info("08 client checks passed: host/no-cheats, program and URL entry edges, standing/rejoin/Build/normal gating, focus return with/without pause, stale return, overlap refusal, zone persistence/removal, atomic refusal, 32x32 wall/floor builds, actual Live/Build breaks and persisted protection; two fixture screenshots");
        } catch (Exception error) { throw new RuntimeException(error); }
        finally {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(previousApps); AresOsClient.replaceLauncher(previousLauncher); AresOsClient.FOCUS_RETURN.reset();
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            });
        }
    }

    private static LogoPixels.Image read(AppDefinition app) { try { return LogoBuilder.readIcon(app); } catch (Exception error) { throw new AssertionError(error); } }
    static int zoneCount(TestSingleplayerContext world) { return world.getServer().computeOnServer(server -> ZoneData.get(server).zones().size()); }
    static void command(ClientGameTestContext context, TestSingleplayerContext world, String command) {
        context.runOnClient(client -> client.player.connection.sendCommand(command));
        world.getConnection().waitForServerboundPackets(); context.waitTicks(3);
    }
    private static void mark(ClientGameTestContext context, TestSingleplayerContext world, String app, Vec3 first, Vec3 second, Vec3 exit) {
        move(context, world, first); command(context, world, "aresos zone pos1");
        move(context, world, second); command(context, world, "aresos zone pos2");
        move(context, world, exit); command(context, world, "aresos zone set " + app);
    }
    static void move(ClientGameTestContext context, TestSingleplayerContext world, Vec3 point) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.teleportTo(player.level(), point.x, point.y, point.z, Set.of(), 0, 0, false);
            player.setDeltaMovement(Vec3.ZERO);
        });
        context.waitFor(client -> client.player.position().distanceToSqr(point) < 0.01);
        context.waitTicks(3);
    }
    static void fly(ClientGameTestContext context, TestSingleplayerContext world) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer(); player.getAbilities().flying = true; player.onUpdateAbilities();
        });
        context.waitFor(client -> client.player.getAbilities().flying);
    }
    static void focusRoundTrip(ClientGameTestContext context, boolean pause) {
        context.runOnClient(client -> {
            boolean previous = client.options.pauseOnLostFocus;
            try {
                client.options.pauseOnLostFocus = pause;
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(false);
                ((MinecraftTestAccess)client).aresos$setLastActiveTime(0);
                ((MinecraftTestAccess)client).aresos$pauseIfInactive();
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
                ((MinecraftTestAccess)client).aresos$pauseIfInactive();
                check(client.gui.screen() == null, "Focus return left pause open");
            } finally { client.options.pauseOnLostFocus = previous; }
        });
    }
    static void walkUntilLaunch(ClientGameTestContext context, List<List<String>> calls, int expected) {
        context.getInput().holdKey(options -> options.keyUp);
        try { context.waitFor(client -> calls.size() == expected); }
        finally { context.getInput().releaseKey(options -> options.keyUp); }
        context.waitTicks(5);
        check(calls.size() == expected, "Walking or standing inside relaunched");
    }
    private static void frame(TestSingleplayerContext world, AppZone zone) {
        world.getServer().runOnServer(server -> {
            var level = world.getConnection().getServerLevel(); var a = zone.min(); var b = zone.max();
            // Test-only lime-glass outline sits just outside the saved trigger box.
            for (int x = a.getX() - 1; x <= b.getX() + 1; x++) for (int z : new int[]{a.getZ() - 1, b.getZ() + 1}) {
                level.setBlockAndUpdate(new BlockPos(x, a.getY() - 1, z), net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(net.minecraft.resources.Identifier.withDefaultNamespace("lime_stained_glass")).defaultBlockState());
                level.setBlockAndUpdate(new BlockPos(x, b.getY() + 1, z), net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(net.minecraft.resources.Identifier.withDefaultNamespace("lime_stained_glass")).defaultBlockState());
            }
            for (int z = a.getZ() - 1; z <= b.getZ() + 1; z++) for (int x : new int[]{a.getX() - 1, b.getX() + 1}) {
                level.setBlockAndUpdate(new BlockPos(x, a.getY() - 1, z), net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(net.minecraft.resources.Identifier.withDefaultNamespace("lime_stained_glass")).defaultBlockState());
                level.setBlockAndUpdate(new BlockPos(x, b.getY() + 1, z), net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(net.minecraft.resources.Identifier.withDefaultNamespace("lime_stained_glass")).defaultBlockState());
            }
            for (int y = a.getY(); y <= b.getY(); y++) for (int x : new int[]{a.getX() - 1, b.getX() + 1}) for (int z : new int[]{a.getZ() - 1, b.getZ() + 1})
                level.setBlockAndUpdate(new BlockPos(x, y, z), net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(net.minecraft.resources.Identifier.withDefaultNamespace("lime_stained_glass")).defaultBlockState());
        });
    }
    private static void screenshot(ClientGameTestContext context, TestSingleplayerContext world, String name) {
        world.getConnection().waitForChunksRender(); context.waitTicks(8);
        context.waitFor(client -> ((dev.aresos.test.mixin.HudTestAccess)client.gui.hud).aresos$overlayTime() == 0);
        context.runOnClient(client -> client.gui.hud.getChat().clearMessages(true));
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.logoReviewDir"))));
    }
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
}
