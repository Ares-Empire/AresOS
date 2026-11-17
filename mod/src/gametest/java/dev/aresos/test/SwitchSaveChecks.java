package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.client.HomeScreen;
import dev.aresos.client.HomeSwitch;
import dev.aresos.client.ShellFocusClient;
import dev.aresos.client.WorldSaves;
import dev.aresos.shell.FakeSupervisor;
import dev.aresos.shell.LifecycleClient;
import dev.aresos.test.mixin.HudTestAccess;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.screen.v1.Screens;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.renderer.state.gui.GuiRenderState;
import net.minecraft.world.level.storage.LevelResource;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;

/** Package 46/48: exercise the real channel and drawing throughout the menu test's switches and recoveries. */
final class SwitchSaveChecks implements AutoCloseable {
    private final Path folder;
    private final FakeSupervisor supervisor;
    private final LifecycleClient lifecycle;
    private int requests;
    private int switches;
    private int probes;
    private int framesBeforeSwitch;
    private final Set<String> worlds = new HashSet<>();

    SwitchSaveChecks(ClientGameTestContext context) throws IOException {
        // Relative Unix socket paths stay short even in a long worktree name. Everything stays in the dev run.
        folder = Files.createTempDirectory(Path.of("."), "a46switch");
        supervisor = new FakeSupervisor(folder.resolve("d.sock"));
        lifecycle = supervisor.client(WorldSaves.INSTANCE);
        lifecycle.start();
        context.waitFor(client -> !supervisor.received("lifecycle_hello").isEmpty());
        SavingText.start();
        // Positive control: an actually extracted frame draws the fully visible indicator outside the home gate.
        context.runOnClient(client -> {
            int before = SavingText.frames();
            draw(client);
            check(SavingText.frames() == before + 1, "Fixture: the saving-indicator drawing probe never drew text");
        });
    }

    /** Queue and join while the server waits at the test barrier; confirm in the same task, before it can save. */
    void confirm(ClientGameTestContext context) {
        context.runOnClient(client -> {
            try {
                var server = client.getSingleplayerServer();
                int first = send(), joined = send();
                supervisor.awaitHandled(lifecycle, requests);
                check(WorldSaves.INSTANCE.queued().size() == 1 && WorldSaves.INSTANCE.queued().contains(server),
                        "Fixture: two requests did not join one queued save before the switch");
                check(supervisor.answers(first).isEmpty() && supervisor.answers(joined).isEmpty(),
                        "Fixture: a queued save already finished");
                framesBeforeSwitch = SavingText.frames();
                Screens.getWidgets(client.gui.screen()).stream().filter(Button.class::isInstance).map(Button.class::cast)
                        .filter(button -> button.getMessage().getString().equals("Make the new home")).findFirst().orElseThrow()
                        .onPress(new KeyEvent(InputConstants.KEY_RETURN, 0, 0));
                check(HomeSwitch.busy(), "Confirmation did not start New home");
                refused(first);
                refused(joined);
                int during = send();
                supervisor.awaitHandled(lifecycle, requests);
                refused(during);
                switches++;
                observe(client);
            } catch (IOException error) {
                throw new UncheckedIOException(error);
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
                throw new AssertionError(error);
            }
        });
    }

    /** Every tick, including staging, closing and recovery: no save can start and no drawing can show the text. */
    void observe(Minecraft client) {
        if (!HomeSwitch.busy()) return;
        check(SavingText.frames() == framesBeforeSwitch, "A frame between switch probes drew Saving world");
        check(ShellFocusClient.readyWorld(client) == null, "A switching world was reported ready");
        var answer = WorldSaves.INSTANCE.save(() -> { throw new AssertionError("A save started during New home"); })
                .toCompletableFuture().getNow(null);
        check(answer != null && "no_world".equals(answer.reason()), "New home did not refuse immediately: " + answer);
        int before = SavingText.frames();
        draw(client);
        check(SavingText.frames() == before, "New home drew the Saving world text");
        var server = client.getSingleplayerServer();
        worlds.add(server == null ? "closed" : server.getWorldPath(LevelResource.ROOT).normalize().getFileName().toString());
        probes++;
    }

    /** After successful arrival or recovery, use the channel again and check the exact ready-world identity. */
    void arrived(ClientGameTestContext context) {
        int id;
        try { id = send(); }
        catch (IOException error) { throw new UncheckedIOException(error); }
        context.waitFor(client -> !supervisor.answers(id).isEmpty(), 1200);
        var answer = supervisor.answers(id).getFirst();
        String ready = context.computeOnClient(ShellFocusClient::readyWorld);
        check(answer.get("ok").getAsBoolean() && ready != null
                && ready.equals(answer.getAsJsonObject("world").get("id").getAsString()), "Save after arrival: " + answer);
        check(SavingText.frames() == framesBeforeSwitch, "New home or recovery drew Saving world before arrival");
    }

    private int send() throws IOException {
        supervisor.save(++requests, "backup");
        return requests;
    }

    private void refused(int id) throws InterruptedException {
        var answer = supervisor.answer(id, 5);
        check(answer.keySet().equals(Set.of("op", "id", "ok", "reason")) && !answer.get("ok").getAsBoolean()
                && "no_world".equals(answer.get("reason").getAsString()), "Switching save was not refused: " + answer);
    }

    /** Force a visible indicator through the real HUD extractor, even in the gap without a desktop world. */
    private static void draw(Minecraft client) {
        var hud = (HudTestAccess) client.gui.hud;
        float current = hud.aresos$savingIndicator(), last = hud.aresos$lastSavingIndicator();
        boolean session = HomeScreen.session();
        try {
            HomeScreen.forTests(false, null);
            hud.aresos$savingIndicator(1);
            hud.aresos$lastSavingIndicator(1);
            var graphics = new GuiGraphicsExtractor(client, new GuiRenderState(), 0, 0);
            hud.aresos$drawSavingIndicator(graphics, DeltaTracker.ONE);
        } finally {
            hud.aresos$savingIndicator(current);
            hud.aresos$lastSavingIndicator(last);
            HomeScreen.forTests(session, null);
        }
    }

    @Override public void close() throws IOException {
        lifecycle.close();
        supervisor.close();
        Files.delete(folder);
        SavingText.stop();
    }

    void verify() {
        check(switches >= 3 && probes > switches && worlds.contains("closed")
                && worlds.stream().anyMatch(name -> name.startsWith("AresHub-new-")),
                "Switch probes missed a stage: " + switches + " switches, " + probes + " probes, " + worlds);
        dev.aresos.AresOs.LOGGER.info("46/48 switch-save checks passed: {} switches, {} drawing/execution probes; "
                + "queued and joined requests and requests during New home answered no_world; arrivals saved normally; worlds {}",
                switches, probes, worlds);
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
