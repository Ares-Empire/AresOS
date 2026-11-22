package dev.aresos.mode;

import dev.aresos.world.DesktopWorld;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Abilities;
import net.minecraft.world.level.GameType;

/**
 * Live mode is the game's survival mode in a desktop world: the hotbar is his taskbar, mining is disabled,
 * and nothing can hurt or starve him.
 *
 * <p>Package 40 (the owner: "put the user into creative and give him speed to travel faster"): Live stays survival,
 * so the creative inventory never reaches the taskbar and left-click never breaks a logo at once, but it gets
 * creative's flight and invulnerability. Both modes walk faster ({@link #DESKTOP_WALKING_SPEED}). The game resets
 * these with every change of game mode, so they are put back right there ({@link #applyDesktopAbilities}), which
 * covers joining, respawning and both switches; the client resets its copy whenever it is told the game mode, so the
 * server sends the abilities again after each such packet ({@code ModeInventories.sync}, the respawn below).
 */
public final class LiveMode {
    /**
     * The walking speed in desktop worlds, in both modes: 1.5 times the game's 0.1, so he walks 6.5 blocks a second
     * instead of 4.3 and sprints 8.4 instead of 5.6. The front row's doorway (21 blocks, HUB.md) is 2.5 seconds away
     * sprinting instead of 3.7, the farthest of forty apps (64 blocks) 7.6 seconds instead of 11.3. Walking is now
     * faster than the game's sprint, so he need not hold a key to cross the town. It stays below flight (16.4 a
     * second), the fast way, and at 0.42 blocks a tick a 2-wide doorway is still easy to hit.
     *
     * <p>It is the walking speed of his abilities and the base of his movement speed together, as the game itself keeps
     * them (it loads the base from the walking speed), so the field of view does not widen as it would with an effect
     * or a modifier: the game widens it by the ratio of the two.
     */
    public static final float DESKTOP_WALKING_SPEED = 0.15f;
    /** Both desktop modes fly at 1.5 times the game's 0.05: about 16.4 blocks/s, 32.7 sprinting. */
    public static final float DESKTOP_FLYING_SPEED = 0.075f;
    private static final float GAME_WALKING_SPEED = new Abilities().getWalkingSpeed();
    private static final float GAME_FLYING_SPEED = new Abilities().getFlyingSpeed();

    private LiveMode() { }

    public static boolean isLive(ServerPlayer player) {
        return isLive(DesktopWorld.isEnabled(player.level().getServer()), player.gameMode.getGameModeForPlayer());
    }

    public static boolean isLive(boolean desktopWorld, GameType mode) {
        return desktopWorld && mode == GameType.SURVIVAL;
    }

    public static void register() {
        ServerLivingEntityEvents.ALLOW_DAMAGE.register((entity, source, amount) ->
                !(entity instanceof ServerPlayer player && isLive(player)));
        ServerLivingEntityEvents.ALLOW_DEATH.register((entity, source, amount) -> {
            if (entity instanceof ServerPlayer player && isLive(player)) {
                player.setHealth(player.getMaxHealth());
                return false;
            }
            return true;
        });
        // The client makes a new player from the respawn packet's game mode, with survival's abilities in Live and the
        // game's walking speed: tell it the real ones after that packet.
        ServerPlayerEvents.AFTER_RESPAWN.register((before, after, alive) -> {
            if (DesktopWorld.isEnabled(after.level().getServer())) after.onUpdateAbilities();
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            // A switch timeout can disconnect and remove a player during this loop.
            for (ServerPlayer player : java.util.List.copyOf(server.getPlayerList().getPlayers())) {
                ModeInventories.of(player).tick(player);
                protect(player);
            }
        });
    }

    /**
     * Called whenever the game has just set a player's game mode and with it his abilities (on joining, on a respawn,
     * on every switch, and while a failed switch is rolled back). In a desktop world it gives back what the game took:
     * the speed in both modes, and in Live creative's flight and invulnerability, never its instant building. A Live
     * player who was flying keeps flying, as in a switch between creative and spectator; the game itself then lands him
     * when he is close to the ground.
     */
    public static void applyDesktopAbilities(ServerPlayer player, boolean wasFlying) {
        if (!DesktopWorld.isEnabled(player.level().getServer())) return;
        setWalkingSpeed(player, DESKTOP_WALKING_SPEED);
        player.getAbilities().setFlyingSpeed(DESKTOP_FLYING_SPEED);
        if (!isLive(player)) return;
        var abilities = player.getAbilities();
        abilities.mayfly = true;
        abilities.invulnerable = true;
        abilities.flying = wasFlying;
    }

    /** The desktop marker was switched on or off with the player in the world: his abilities follow at once. */
    public static void markerChanged(ServerPlayer player, boolean enabled) {
        if (enabled) applyDesktopAbilities(player, player.getAbilities().flying);
        else {
            // The game's own abilities for his mode, and its walking speed if it was this mod's.
            player.gameMode.getGameModeForPlayer().updatePlayerAbilities(player.getAbilities());
            if (player.getAbilities().getWalkingSpeed() == DESKTOP_WALKING_SPEED) setWalkingSpeed(player, GAME_WALKING_SPEED);
            if (player.getAbilities().getFlyingSpeed() == DESKTOP_FLYING_SPEED) player.getAbilities().setFlyingSpeed(GAME_FLYING_SPEED);
        }
        player.onUpdateAbilities();
    }

    private static void setWalkingSpeed(ServerPlayer player, float speed) {
        player.getAbilities().setWalkingSpeed(speed);
        var movement = player.getAttribute(Attributes.MOVEMENT_SPEED);
        if (movement != null) movement.setBaseValue(speed);
    }

    public static void protect(ServerPlayer player) {
        if (!isLive(player)) return;
        player.getFoodData().setFoodLevel(20);
        player.getFoodData().setSaturation(20);
        if (player.getY() < player.level().getMinY()) {
            player.teleport(player.findRespawnPositionAndUseSpawnBlock(false,
                    net.minecraft.world.level.portal.TeleportTransition.DO_NOTHING));
            player.fallDistance = 0;
            dev.aresos.zone.WalkInZones.arrived(player);
            // Moved by the mod: a /go still loading is no longer his wish (review fixes 2, point 2).
            dev.aresos.world.Arrivals.cancel(player);
        }
    }

    public static boolean toggleForHost(MinecraftServer server, ServerPlayer player) {
        if (!DesktopWorld.isEnabled(server)) {
            player.sendSystemMessage(Component.literal("Not an AresOS world"), true);
            return false;
        }
        if (!DesktopWorld.isHost(server, player)) return false;
        GameType mode = ModeInventories.of(player).activeInventory(player);
        if (!ModeInventories.of(player).switchTo(player,
                mode == GameType.CREATIVE ? GameType.SURVIVAL : GameType.CREATIVE, true)) return false;
        protect(player);
        return true;
    }
}
