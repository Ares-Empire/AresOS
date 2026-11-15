package dev.aresos.test;

import dev.aresos.AresOs;
import dev.aresos.zone.GateBuilder;
import dev.aresos.zone.GateNumbers;
import dev.aresos.zone.GatePicture;
import dev.aresos.zone.GatePlan;
import dev.aresos.zone.LogoIcons;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Package 39: how an icon's colours come out as blocks (HUB.md 3.6), in pictures under
 * {@code reviews/39-logo-colours/screenshots}. The ten icons of {@link LogoIcons} stand as logos in one row on a grass
 * field at noon, and two pictures show five each from 32 blocks away, about as far as the town's front logos are
 * from the pad. Every icon is drawn by the tests; none is a real app's icon.
 *
 * Last in the list, so no other package's pictures are renumbered.
 */
public final class LogoColoursClientGameTest implements FabricClientGameTest {
    /**
     * Opt-in, for looking at the logos of real app icons without putting them into the repo: a folder outside the
     * repo holding {@code chrome.png}, {@code discord.png} and {@code lunar-client.png}. The three stand in the same
     * row, further along, and their picture goes to the folder's {@code screenshots}.
     */
    private static final String LOOK = System.getenv("ARESOS_LOGO_LOOK");
    private static final List<String[]> REAL = List.of(new String[]{"chrome.png", "Chrome"}, new String[]{"discord.png", "Discord"},
            new String[]{"lunar-client.png", "Lunar Client"});
    /**
     * Which rules drew the pictures. The two "before" pictures beside these were taken by this test with the rules
     * of converter 1, in the commit before the rules changed, and are kept to compare.
     */
    private static final String RULES = "after";
    private static final int Y = 150, SPACING = GateNumbers.SIZE + 2, ROW = 5;
    private static final double FACE_Z = 15;

    @Override public void runTest(ClientGameTestContext context) {
        var icons = LogoIcons.all();
        // The real three stand one place on from the drawn ten.
        int real = icons.size() + 1, places = real + REAL.size();
        context.getInput().resizeWindow(960, 540);
        try (var world = context.worldBuilder().adjustSettings(settings -> {
            settings.setGameMode(net.minecraft.client.gui.screens.worldselection.WorldCreationUiState.SelectedGameMode.SURVIVAL);
            settings.setAllowCommands(false);
        }).create()) {
            world.getConnection().waitForChunksRender();
            world.getServer().runOnServer(server -> {
                var level = world.getConnection().getServerLevel();
                // A grass field in the sky: nothing of the generated world stands between him and the logos.
                for (int x = -30; x <= SPACING * places + 30; x++) for (int z = -10; z <= 64; z++) {
                    level.setBlock(new BlockPos(x, Y - 2, z), Blocks.STONE.defaultBlockState(), 2);
                    level.setBlock(new BlockPos(x, Y - 1, z), Blocks.GRASS_BLOCK.defaultBlockState(), 2);
                }
                server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), "time set 6000");
            });
            for (int i = 0; i < icons.size(); i++) build(context, world, i, icons.get(i).name(), icons.get(i).image());
            Path folder = Files.createDirectories(Path.of(System.getProperty("aresos.coloursReviewDir")));
            for (int row = 0; row * ROW < icons.size(); row++)
                GateLogoClientGameTest.shot(context, world, new Vec3(SPACING * (row * ROW + (ROW - 1) / 2.0), Y, FACE_Z + 32), 180, -8,
                        folder, "logos-" + RULES + "-row-" + (row + 1));
            if (LOOK != null) {
                for (int i = 0; i < REAL.size(); i++)
                    build(context, world, real + i, REAL.get(i)[1], ImageIO.read(Path.of(LOOK, REAL.get(i)[0]).toFile()));
                Path look = Files.createDirectories(Path.of(LOOK, "screenshots"));
                GateLogoClientGameTest.shot(context, world, new Vec3(SPACING * (real + 1), Y, FACE_Z + 24), 180, -10, look, "real-three-" + RULES);
                AresOs.LOGGER.info("39 pictures: the logos of the three icons in {} are pictured in {}", LOOK, look);
            }
            AresOs.LOGGER.info("39 pictures taken ({}): ten drawn icons as logos, five a picture, from 32 blocks", RULES);
        } catch (IOException error) {
            throw new RuntimeException(error);
        } finally {
            context.getInput().resizeWindow(854, 480);
        }
    }

    /** One logo in the row, built as the town builds it: from the icon's picture, facing him. */
    private static void build(ClientGameTestContext context, TestSingleplayerContext world, int place, String name, BufferedImage icon) {
        var picture = GatePicture.of(icon, GateNumbers.SIZE);
        if (picture.isEmpty()) throw new AssertionError(name + " gave an empty picture");
        // Near enough that the place is loaded, as it is when he builds a gate himself.
        GateLogoClientGameTest.stand(context, world, new Vec3(SPACING * place, Y, FACE_Z + 20), 180, -8);
        world.getServer().runOnServer(server -> {
            var level = world.getConnection().getServerLevel();
            try {
                GateBuilder.build(level, "colours-" + place, GatePlan.of(picture, level.dimension(),
                        new BlockPos(SPACING * place - GateNumbers.SIZE / 2, Y, 14), Direction.NORTH, name, null, "light_gray_concrete"));
            } catch (IOException error) {
                throw new AssertionError(name + " was not built", error);
            }
        });
    }
}
