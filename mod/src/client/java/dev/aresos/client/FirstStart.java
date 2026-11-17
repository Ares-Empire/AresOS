package dev.aresos.client;

import dev.aresos.AresOs;
import dev.aresos.world.HomeRules;
import dev.aresos.world.NetherHome;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.network.chat.Component;

import java.nio.file.Files;
import java.nio.file.LinkOption;

/**
 * Package 48, B: the first start. A game the AresOS session started that reaches its first title screen while no
 * AresHub folder exists makes the flat home at once, through the title screen's own create path, instead of showing
 * the title screen. He arrives in Live mode in the flat home; the Nether home is one Esc away ("New home…").
 *
 * <p>Decided once per game start, at the first title screen, so a failed creation's error screen leads to the title
 * screen with the AresOS button as before. An AresHub that exists, damaged or not, is never touched, and neither is
 * any other save. Outside a session the title screen shows as it always has. Client thread only.
 */
public final class FirstStart {
    static final Component WORKING = Component.literal("Making your home…");
    private static boolean decided;

    private FirstStart() { }

    /** What {@code Gui.setScreen} gets ({@code GuiScreenMixin}): the first title screen may become the flat home. */
    public static Screen screenComing(Minecraft client, Screen screen) {
        if (!(screen instanceof TitleScreen || (screen == null && client.level == null))) return screen;
        boolean session = HomeScreen.session();
        // Only the folder's name counts: a link, a file or a damaged save named AresHub is left alone.
        boolean hub = session && !decided && Files.exists(
                client.getLevelSource().getBaseDir().resolve(NetherHome.SAVE_FOLDER), LinkOption.NOFOLLOW_LINKS);
        var plan = HomeRules.firstStart(session, decided, hub, HomeSwitch.busy());
        decided = true;
        if (plan != HomeRules.FirstStart.CREATE_FLAT) return screen;
        AresOs.LOGGER.info("First start: no AresHub yet, making the flat home");
        // From a task, not from inside setScreen: the create flow sets screens and loads the world itself.
        client.schedule(() -> HomeButton.createFlat(client, new TitleScreen()));
        return new HomeWorkingScreen(WORKING);
    }

    /** A home switch has begun: this game start is past its first start (see {@link HomeSwitch}). */
    static void decided() { decided = true; }

    /** Client game tests: the next title screen decides again, as the first one of a game start does. */
    public static void forTests() { decided = false; }
}
