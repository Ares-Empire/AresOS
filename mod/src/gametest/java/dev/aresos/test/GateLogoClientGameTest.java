package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.client.AresOsClient;
import dev.aresos.config.AppDefinition;
import dev.aresos.test.mixin.AppsTestAccess;
import dev.aresos.test.mixin.HudTestAccess;
import dev.aresos.test.mixin.WindowTestAccess;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GateNumbers;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.GatePlan;
import dev.aresos.zone.ZoneData;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Display;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Consumer;

import static dev.aresos.test.WalkInLogosClientGameTest.command;
import static dev.aresos.test.WalkInLogosClientGameTest.focusRoundTrip;
import static dev.aresos.test.WalkInLogosClientGameTest.walkUntilLaunch;
import static dev.aresos.test.WalkInLogosClientGameTest.zoneCount;

/**
 * The gate as he meets it: `/aresos logo` builds it in front of him, walking past opens nothing, stepping into
 * the doorway opens the app once, closing the app puts him on the exit point, and `/aresos logo remove` takes it
 * down, also after the world was closed and opened again. The screenshots show gates from icons this test draws.
 */
public final class GateLogoClientGameTest implements FabricClientGameTest {
    private static final int Y = 150;
    /** Four gates side by side with the town's two-block gap. */
    private static final int SPACING = GateNumbers.SIZE + 2;
    private static final int PINWHEEL = -SPACING, SUNNY = 0, TREE = SPACING, PLAIN = 2 * SPACING;
    /** He stands here when he builds a gate, facing north. Its front layer is then at z 14, its front face at z 15. */
    private static final double BUILD_Z = 20.5, FACE_Z = 15;
    /**
     * Opt-in, for looking at gates from real app icons without putting them into the repo: a folder holding
     * {@code icons/<name>.png}. Screenshots go to its {@code screenshots} folder.
     */
    private static final String LOOK = System.getenv("ARESOS_GATE_LOOK");

    @Override public void runTest(ClientGameTestContext context) {
        var previousApps = AresOs.apps();
        var calls = new CopyOnWriteArrayList<List<String>>();
        var previousLauncher = context.computeOnClient(client -> AresOsClient.replaceLauncher(command -> {
            calls.add(List.copyOf(command)); return CompletableFuture.completedFuture(null);
        }));
        try {
            Path icons = Path.of("gate-fixtures").toAbsolutePath();
            Files.createDirectories(icons);
            // The starter IDs have a group, and with it a doormat colour; any other app's doormat is light grey.
            var pinwheel = new AppDefinition("browser", "Pinwheel", List.of("fixture-pinwheel.exe"), "minecraft:compass", false,
                    "command", null, write(icons.resolve("pinwheel.png"), pinwheel()));
            var sunny = new AppDefinition("terminal", "Sunny Notes", List.of("fixture-sunny.exe"), "minecraft:book", false,
                    "command", null, write(icons.resolve("sunny.png"), sunny()));
            var tree = new AppDefinition("gate-tree", "Tall Tree", List.of("fixture-tree.exe"), "minecraft:paper", false,
                    "command", null, write(icons.resolve("tree.png"), tree()));
            var plain = new AppDefinition("notepad", "No Picture", List.of("fixture-plain.exe"), "minecraft:paper", false,
                    "command", null, null);
            context.runOnClient(client -> AppsTestAccess.aresos$setApps(List.of(pinwheel, sunny, tree, plain)));
            TestWorldSave save;
            AppZone pinwheelGate, sunnyGate;
            try (var world = context.worldBuilder().adjustSettings(settings -> {
                settings.setGameMode(net.minecraft.client.gui.screens.worldselection.WorldCreationUiState.SelectedGameMode.SURVIVAL);
                settings.setAllowCommands(false);
            }).create()) {
                save = world.getWorldSave();
                world.getConnection().waitForChunksRender();
                world.getServer().runOnServer(server -> {
                    var level = world.getConnection().getServerLevel();
                    // A grass field in the sky: nothing of the generated world is in the pictures.
                    for (int x = -64; x <= (LOOK == null ? 80 : 170); x++) for (int z = -44; z <= 76; z++) {
                        level.setBlock(new BlockPos(x, Y - 2, z), Blocks.STONE.defaultBlockState(), 2);
                        level.setBlock(new BlockPos(x, Y - 1, z), Blocks.GRASS_BLOCK.defaultBlockState(), 2);
                    }
                    server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), "time set 6000");
                });
                stand(context, world, new Vec3(PINWHEEL, Y, BUILD_Z), 180, 0);
                command(context, world, "aresos desktop on");

                // The command builds each gate six blocks in front of him, facing him, with its door on his line.
                var apps = List.of(pinwheel, sunny, tree, plain);
                int[] lines = {PINWHEEL, SUNNY, TREE, PLAIN};
                String[] doormats = {"light_blue_concrete", "yellow_concrete", "light_gray_concrete", "yellow_concrete"};
                for (int i = 0; i < apps.size(); i++) {
                    int line = lines[i], index = i;
                    stand(context, world, new Vec3(line, Y, BUILD_Z), 180, 0);
                    command(context, world, "aresos logo " + apps.get(i).id());
                    check(zoneCount(world) == i + 1, "No gate was built for " + apps.get(i).id());
                    world.getServer().runOnServer(server -> {
                        var level = world.getConnection().getServerLevel();
                        var zone = ZoneData.get(server).zones().getLast();
                        var gate = zone.gate().orElseThrow(() -> new AssertionError("The default logo is not a gate"));
                        check(zone.min().equals(new BlockPos(line - 1, Y, 13)) && zone.max().equals(new BlockPos(line, Y + 2, 14)), "Trigger zone is not the niche: " + zone.min() + " to " + zone.max());
                        check(zone.exit().position().equals(new Vec3(line, Y, BUILD_Z)) && zone.exit().yaw() == 180 && zone.exit().pitch() == -10, "Exit is not where he stood: " + zone.exit());
                        for (var placed : gate.placed()) check(id(level, placed.pos()).equals(placed.block()), "Recorded block is not in the world: " + placed);
                        for (var pos : BlockPos.betweenClosed(zone.min(), zone.max())) check(level.getBlockState(pos).isAir(), "The niche is not open at " + pos);
                        for (int x = line - 1; x <= line; x++) for (int z = 13; z <= 16; z++)
                            check(id(level, new BlockPos(x, Y - 1, z)).equals("minecraft:" + doormats[index]), "Doormat at " + x + ", " + z + ": " + id(level, new BlockPos(x, Y - 1, z)));
                        check(level.getEntity(gate.sign().orElseThrow()) instanceof Display.TextDisplay sign
                                && sign.position().equals(new Vec3(line, Y + GateNumbers.SIZE + 0.5, 14.5)), "The sign is missing or misplaced");
                    });
                }
                pinwheelGate = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().get(0));
                sunnyGate = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().get(1));
                world.getServer().runOnServer(server -> {
                    // No icon: a plain front in the group's colour with the black door frame's back.
                    var blocks = ZoneData.get(server).zones().get(3).gate().orElseThrow().placed().stream().map(AppZone.Placed::block).collect(java.util.stream.Collectors.toSet());
                    check(blocks.equals(Set.of("minecraft:yellow_concrete", "minecraft:black_concrete", "minecraft:light")), "Plain gate is built from " + blocks);
                    check(pinwheelGate.gate().orElseThrow().placed().stream().noneMatch(placed -> placed.pos().equals(new BlockPos(PINWHEEL - GateNumbers.SIZE / 2, Y + GateNumbers.SIZE - 1, 14))),
                            "The round icon's gate has a block in its top corner");
                });
                // A second gate on the same place is refused and changes nothing.
                stand(context, world, new Vec3(SUNNY, Y, BUILD_Z), 180, 0);
                command(context, world, "aresos logo gate-tree");
                check(zoneCount(world) == 4, "A gate was built into another gate");

                // Walking along the front, as close as the face allows, opens nothing.
                stand(context, world, new Vec3(PINWHEEL - GateNumbers.SIZE / 2.0 - 3.5, Y, FACE_Z + 0.31), -90, 0);
                context.getInput().holdKey(options -> options.keyUp);
                try { context.waitFor(client -> client.player.getX() > PINWHEEL + GateNumbers.SIZE / 2.0 + 1.5, 400); }
                finally { context.getInput().releaseKey(options -> options.keyUp); }
                context.waitTicks(5);
                check(calls.isEmpty(), "Walking past the front opened " + calls);
                context.runOnClient(client -> check(Math.abs(client.player.getZ() - (FACE_Z + 0.31)) < 0.05, "He did not walk along the front: z " + client.player.getZ()));

                // Walking into the doorway opens the app once; closing it puts him on the exit point, looking at the door.
                stand(context, world, pinwheelGate.exit().position(), 180, 0);
                walkUntilLaunch(context, calls, 1);
                check(calls.getFirst().equals(pinwheel.command()), "Wrong program launched: " + calls);
                world.getServer().runOnServer(server -> check(pinwheelGate.touchesPlayer(world.getConnection().getServerPlayer().position()), "It opened before he was in the doorway"));
                context.waitTicks(20);
                check(calls.size() == 1, "Standing in the doorway opened it again");
                focusRoundTrip(context, true);
                world.getConnection().waitForServerboundPackets();
                context.waitFor(client -> client.player.position().distanceToSqr(pinwheelGate.exit().position()) < 0.01);
                context.waitTicks(12);
                check(calls.size() == 1, "The return opened it again");
                world.getServer().runOnServer(server -> {
                    var player = world.getConnection().getServerPlayer();
                    check(player.position().distanceToSqr(new Vec3(PINWHEEL, Y, BUILD_Z)) < 1e-6 && Math.abs(Mth.wrapDegrees(player.getYRot() - 180)) < 0.01 && player.getXRot() == -10,
                            "Return is not the exit point looking at the door: " + player.position() + " " + player.getYRot() + " " + player.getXRot());
                    // Live mode protects everything the gate placed.
                    var front = new BlockPos(PINWHEEL - 3, Y + 5, 14);
                    var doormat = new BlockPos(PINWHEEL, Y - 1, 16);
                    check(!level(world).getBlockState(front).isAir() && !player.gameMode.destroyBlock(front) && !player.gameMode.destroyBlock(doormat), "Live mode broke a gate block");
                    check(!level(world).getBlockState(front).isAir() && id(level(world), doormat).equals("minecraft:light_blue_concrete"), "A refused break changed a block");
                });

                // What he sees, from eye height.
                screenshot(context, world, new Vec3(PINWHEEL, Y, FACE_Z + 20), 180, -12, "gate-pinwheel-from-20");
                screenshot(context, world, new Vec3(SUNNY, Y, FACE_Z + 20), 180, -12, "gate-sunny-from-20");
                screenshot(context, world, new Vec3(TREE, Y, FACE_Z + 20), 180, -12, "gate-tree-from-20");
                screenshot(context, world, new Vec3(SUNNY, Y, FACE_Z + 10), 180, -25, "gate-sunny-from-10");
                screenshot(context, world, new Vec3(PINWHEEL - GateNumbers.SIZE / 2.0 - 16, Y, 13.5), -90, -12, "gate-pinwheel-from-the-side");
                var corner = new Vec3(PINWHEEL - 15, Y, FACE_Z + 13);
                var towards = new Vec3(PINWHEEL, Y + 7, 13.5).subtract(corner.add(0, 1.62, 0));
                screenshot(context, world, corner, (float)Math.toDegrees(Math.atan2(-towards.x, towards.z)),
                        (float)-Math.toDegrees(Math.atan2(towards.y, Math.hypot(towards.x, towards.z))), "gate-pinwheel-from-the-corner");
                screenshot(context, world, new Vec3(PINWHEEL, Y, 12 - 20), 0, -12, "gate-pinwheel-from-behind");
                screenshot(context, world, new Vec3((PINWHEEL + PLAIN) / 2.0, Y, FACE_Z + 34), 180, -8, "gates-in-a-row");
                world.getServer().runOnServer(server -> server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), "time set 18000"));
                context.waitTicks(40);
                screenshot(context, world, new Vec3((PINWHEEL + PLAIN) / 2.0, Y, FACE_Z + 34), 180, -8, "gates-at-night");
                world.getServer().runOnServer(server -> server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), "time set 6000"));
                if (LOOK != null) look(context, world, Path.of(LOOK));

                // `zone remove` leaves a gate alone; `logo remove` takes it down, by name or where he stands.
                command(context, world, "aresos zone remove notepad");
                check(zoneCount(world) == 4, "zone remove took a gate's zone and left its blocks");
                var plainGate = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().get(3));
                stand(context, world, plainGate.exit().position(), 180, 0);
                command(context, world, "aresos logo remove here");
                check(zoneCount(world) == 3, "logo remove here did not remove the gate he stands at");
                world.getServer().runOnServer(server -> gone(level(world), plainGate));
                var treeGate = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().get(2));
                command(context, world, "aresos logo remove gate-tree");
                check(zoneCount(world) == 2, "logo remove by name did not remove the gate");
                world.getServer().runOnServer(server -> gone(level(world), treeGate));
                command(context, world, "aresos logo remove gate-tree");
                check(zoneCount(world) == 2, "logo remove without a logo changed zones");

                // The wall is still built on request, and `logo remove` only takes its zone.
                stand(context, world, new Vec3(TREE + 0.5, Y, BUILD_Z), 180, 0);
                command(context, world, "aresos logo gate-tree wall");
                check(zoneCount(world) == 3, "The wall logo was not built");
                var wall = world.getServer().computeOnServer(server -> ZoneData.get(server).zones().get(2));
                check(!wall.isGate() && wall.blocks().size() > 100, "The wall form changed: " + wall.blocks().size() + " blocks");
                command(context, world, "aresos logo remove gate-tree");
                check(zoneCount(world) == 2, "logo remove did not remove the wall's zone");
                world.getServer().runOnServer(server -> check(wall.blocks().stream().noneMatch(pos -> level(world).getBlockState(pos).isAir()), "logo remove took a wall's blocks"));
                stand(context, world, pinwheelGate.exit().position(), 180, 0);
            }
            // A gate is still his to take down after the world was closed: its record and its sign were saved.
            try (var reopened = save.open()) {
                reopened.getConnection().waitForChunksRender();
                context.waitTicks(12);
                check(calls.size() == 1, "Rejoining in front of a gate opened it");
                reopened.getServer().runOnServer(server -> {
                    check(ZoneData.get(server).zones().equals(List.of(pinwheelGate, sunnyGate)), "The gates' zones changed across the rejoin");
                    for (var zone : ZoneData.get(server).zones())
                        check(level(reopened).getEntity(zone.gate().orElseThrow().sign().orElseThrow()) instanceof Display.TextDisplay, "A sign was lost across the rejoin");
                });
                command(context, reopened, "aresos logo remove here");
                check(zoneCount(reopened) == 1, "logo remove here failed after the rejoin");
                reopened.getServer().runOnServer(server -> {
                    gone(level(reopened), pinwheelGate);
                    check(level(reopened).getEntitiesOfClass(Display.TextDisplay.class, pinwheelGate.area().inflate(20)).size() == 1, "Not exactly the other gate's sign is left");
                });
            }
            AresOs.LOGGER.info("33 client checks passed: four gates by command with niche, exit, doormat and sign; refusal on an occupied place; walking past opens nothing; one launch per entry and the return on the exit point; Live protection; zone remove leaves gates; logo remove here and by name, also after a rejoin; the wall still built and its blocks kept; nine screenshots");
        } catch (IOException error) { throw new RuntimeException(error); }
        finally {
            context.runOnClient(client -> {
                AppsTestAccess.aresos$setApps(previousApps); AresOsClient.replaceLauncher(previousLauncher); AresOsClient.FOCUS_RETURN.reset();
                ((WindowTestAccess)(Object)client.getWindow()).aresos$setFocused(true);
            });
        }
    }

    /**
     * The gates of the icons in a folder, at every size, for a person to look at. Each size is built, pictured
     * and taken down again. Nothing here is checked and nothing is written into the repo.
     */
    private static void look(ClientGameTestContext context, TestSingleplayerContext world, Path folder) throws IOException {
        List<Path> icons;
        try (var files = Files.list(folder.resolve("icons"))) { icons = files.filter(file -> file.toString().endsWith(".png")).sorted().toList(); }
        Path out = folder.resolve("screenshots");
        for (int size : new int[]{12, 10, 14, 16}) {
            var built = new java.util.ArrayList<AppZone>();
            for (int i = 0; i < icons.size(); i++) {
                var icon = ImageIO.read(icons.get(i).toFile());
                String name = icons.get(i).getFileName().toString().replace(".png", "");
                var origin = new BlockPos(110 + 20 * i - size / 2, Y, 14);
                // Near enough that the place is loaded, as it is when he builds a gate himself.
                stand(context, world, new Vec3(110 + 20 * i, Y, FACE_Z + 20), 180, -12);
                built.add(world.getServer().computeOnServer(server -> {
                    try {
                        return GateBuilder.build(level(world), "look-" + name, GatePlan.of(GatePicture.of(icon, size), level(world).dimension(), origin, Direction.NORTH, name, null, "light_gray_concrete"));
                    } catch (IOException error) { throw new AssertionError(error); }
                }));
                shot(context, world, new Vec3(110 + 20 * i, Y, FACE_Z + 20), 180, -12, out, name + "-" + size + "-from-20");
                if (size == GateNumbers.SIZE) shot(context, world, new Vec3(110 + 20 * i, Y, FACE_Z + 10), 180, -25, out, name + "-" + size + "-from-10");
            }
            shot(context, world, new Vec3(110 + 10 * (icons.size() - 1), Y, FACE_Z + 30), 180, -10, out, "all-" + size + "-from-30");
            world.getServer().runOnServer(server -> {
                try { for (var zone : built) GateBuilder.remove(server, zone); } catch (IOException error) { throw new AssertionError(error); }
            });
        }
    }

    /** Every block the gate placed is gone, the ground under its doormat is back, and so is its sign. */
    private static void gone(ServerLevel level, AppZone zone) {
        var gate = zone.gate().orElseThrow();
        var ground = gate.ground().stream().map(AppZone.Placed::pos).collect(java.util.stream.Collectors.toSet());
        for (var placed : gate.placed()) check(ground.contains(placed.pos()) ? level.getBlockState(placed.pos()).is(Blocks.GRASS_BLOCK) : level.getBlockState(placed.pos()).isAir(),
                "After the removal " + placed.pos() + " is " + level.getBlockState(placed.pos()));
        check(ground.size() == 8, "The doormat replaced " + ground.size() + " ground blocks");
        var sign = level.getEntity(gate.sign().orElseThrow());
        check(sign == null || sign.isRemoved(), "The sign is still there");
    }

    private static ServerLevel level(TestSingleplayerContext world) { return world.getConnection().getServerLevel(); }

    private static String id(ServerLevel level, BlockPos pos) { return BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()).toString(); }

    private static void stand(ClientGameTestContext context, TestSingleplayerContext world, Vec3 point, float yaw, float pitch) {
        world.getServer().runOnServer(server -> {
            var player = world.getConnection().getServerPlayer();
            player.teleportTo(player.level(), point.x, point.y, point.z, Set.of(), yaw, pitch, false);
            player.setDeltaMovement(Vec3.ZERO);
        });
        context.waitFor(client -> client.player.position().distanceToSqr(point) < 0.01 && Math.abs(Mth.wrapDegrees(client.player.getYRot() - yaw)) < 0.01);
        context.waitTicks(3);
    }

    private static void screenshot(ClientGameTestContext context, TestSingleplayerContext world, Vec3 point, float yaw, float pitch, String name) {
        shot(context, world, point, yaw, pitch, Path.of(System.getProperty("aresos.gateReviewDir")), name);
    }

    private static void shot(ClientGameTestContext context, TestSingleplayerContext world, Vec3 point, float yaw, float pitch, Path folder, String name) {
        stand(context, world, point, yaw, pitch);
        world.getConnection().waitForChunksRender(); context.waitTicks(8);
        context.waitFor(client -> ((HudTestAccess)client.gui.hud).aresos$overlayTime() == 0);
        context.runOnClient(client -> client.gui.hud.getChat().clearMessages(true));
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(folder));
    }

    private static String write(Path file, BufferedImage icon) throws IOException {
        ImageIO.write(icon, "png", file.toFile());
        return file.toString();
    }

    private static BufferedImage draw(int width, int height, Consumer<java.awt.Graphics2D> picture) {
        var icon = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        var graphics = icon.createGraphics();
        graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        picture.accept(graphics);
        graphics.dispose();
        return icon;
    }

    /** A round icon: four coloured quarters around a white middle. Its gate is round too. */
    private static BufferedImage pinwheel() {
        return draw(96, 96, graphics -> {
            Color[] quarters = {new Color(0xf57c00), new Color(0x7b1fa2), new Color(0x00acc1), new Color(0x7cb342)};
            for (int quarter = 0; quarter < 4; quarter++) { graphics.setColor(quarters[quarter]); graphics.fillArc(2, 2, 92, 92, 90 * quarter, 90); }
            graphics.setColor(Color.WHITE); graphics.fillOval(32, 32, 32, 32);
        });
    }

    /** The design drawing's icon: a small sun on a plain plate. The sun is enlarged and the plate fills the gate. */
    private static BufferedImage sunny() {
        return draw(96, 96, graphics -> {
            graphics.setColor(new Color(0x17748a)); graphics.fillRoundRect(0, 0, 96, 96, 24, 24);
            graphics.setColor(new Color(0xf1af15)); graphics.fillOval(30, 30, 36, 36);
            graphics.setColor(new Color(0xe06101)); graphics.fillOval(40, 40, 16, 16);
        });
    }

    /** A tall icon with nothing beside its foot: it stands in the middle, and the door gets its black frame. */
    private static BufferedImage tree() {
        return draw(48, 96, graphics -> {
            graphics.setColor(new Color(0x6d4c41)); graphics.fillRect(18, 56, 12, 40);
            graphics.setColor(new Color(0x2e7d32)); graphics.fillOval(0, 0, 48, 64);
        });
    }

    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
}
