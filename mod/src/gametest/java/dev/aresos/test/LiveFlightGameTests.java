package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.config.AppDefinition;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import dev.aresos.zone.AppZone;
import dev.aresos.zone.ZoneData;
import io.netty.channel.embedded.EmbeddedChannel;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.ClientboundBundlePacket;
import net.minecraft.network.protocol.game.ClientboundGameEventPacket;
import net.minecraft.network.protocol.game.ClientboundLoginPacket;
import net.minecraft.network.protocol.game.ClientboundPlayerAbilitiesPacket;
import net.minecraft.network.protocol.game.ClientboundRespawnPacket;
import net.minecraft.network.protocol.game.ClientboundUpdateAttributesPacket;
import net.minecraft.network.protocol.game.ServerboundPlayerAbilitiesPacket;
import net.minecraft.network.protocol.game.ServerboundPlayerActionPacket;
import net.minecraft.network.protocol.game.ServerboundSetCreativeModeSlotPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Abilities;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.world.level.storage.TagValueOutput;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

import java.util.List;
import java.util.UUID;

import static dev.aresos.test.ModeInventoryFixtures.acknowledge;
import static dev.aresos.test.ModeInventoryFixtures.check;
import static dev.aresos.test.ModeInventoryFixtures.registerStateReceiver;
import static dev.aresos.test.ModeInventoryFixtures.switchAndAcknowledge;

/**
 * Package 40, D: in a desktop world Live mode flies like creative and nothing hurts him, both modes walk faster, and
 * Live still keeps the taskbar and the logos as they are. Each check is made twice: on the server, and in what the
 * player's client is told, replayed packet by packet as the client applies them ({@link #clientView}), because the
 * client gives itself a mode's own abilities whenever it hears the game mode.
 *
 * <p>Every test runs within one server tick, so tests running beside it that switch the desktop marker off and on
 * again (other files' join fixtures) never land between two of its steps.
 */
public final class LiveFlightGameTests {
    private record Joined(ServerPlayer player, EmbeddedChannel channel) { }

    /** Joins as the game does: a new player, his save read into it if he has one, then the login. */
    private static Joined join(GameTestHelper helper, GameProfile profile, boolean desktop, CompoundTag saved) {
        var server = helper.getLevel().getServer();
        DesktopWorld.setEnabled(server, desktop);
        var cookie = CommonListenerCookie.createInitial(profile, false);
        var player = new ServerPlayer(server, helper.getLevel(), cookie.gameProfile(), cookie.clientInformation());
        if (saved != null) player.load(TagValueInput.create(ProblemReporter.DISCARDING, server.registryAccess(), saved));
        var connection = new Connection(PacketFlow.SERVERBOUND);
        var channel = new EmbeddedChannel(connection);
        server.getPlayerList().placeNewPlayer(connection, player, cookie);
        registerStateReceiver(player);
        player.connection.handleAcceptPlayerLoad(new net.minecraft.network.protocol.game.ServerboundPlayerLoadedPacket());
        return new Joined(player, channel);
    }

    private static Joined joinLive(GameTestHelper helper, boolean desktop) {
        var joined = join(helper, new GameProfile(UUID.randomUUID(), "LiveFlight"), desktop, null);
        joined.player.setGameMode(GameType.SURVIVAL);
        acknowledge(joined.player);
        BlockPos floor = helper.absolutePos(new BlockPos(2, 1, 2));
        helper.getLevel().setBlockAndUpdate(floor, Blocks.STONE.defaultBlockState());
        joined.player.snapTo(floor.getX() + 0.5, floor.getY() + 1, floor.getZ() + 0.5, -90, 0);
        return joined;
    }

    private static void leave(ServerPlayer player) {
        player.level().getServer().getPlayerList().remove(player);
    }

    @GameTest(environment = "aresos-test:desktop")
    public void joiningLivePlayerFliesAndCannotBeHurt(GameTestHelper helper) {
        var joined = joinLive(helper, true);
        var player = joined.player;
        check(LiveMode.isLive(player) && player.gameMode() == GameType.SURVIVAL, "Fixture: the player is not in Live mode");
        assertLive(player.getAbilities(), "Live on the server");
        assertLive(clientView(joined.channel), "Live on his client");

        // Double space: his client asks to fly, and the server lets him.
        var wanted = new Abilities();
        wanted.flying = true;
        player.connection.handlePlayerAbilities(new ServerboundPlayerAbilitiesPacket(wanted));
        check(player.getAbilities().flying, "The server refused Live mode's flight");

        float health = player.getHealth();
        player.hurtServer(helper.getLevel(), player.damageSources().fall(), 1000);
        player.hurtServer(helper.getLevel(), player.damageSources().lava(), 1000);
        player.causeFallDamage(100, 1, player.damageSources().fall());
        check(player.isAlive() && player.getHealth() == health, "Live mode was hurt");
        // The game's own invulnerability, not only the mod's damage rule: he does not even catch fire.
        player.igniteForSeconds(8);
        check(player.getRemainingFireTicks() <= 1, "Live mode caught fire: " + player.getRemainingFireTicks() + " ticks");

        // Joining again from his save, flying, as after a restart.
        var profile = player.getGameProfile();
        var output = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, player.registryAccess());
        player.saveWithoutId(output);
        leave(player);
        joined.channel.finishAndReleaseAll();
        var again = join(helper, profile, true, output.buildResult());
        try {
            check(LiveMode.isLive(again.player), "He did not join again in Live mode");
            assertLive(again.player.getAbilities(), "Live after joining again, on the server");
            assertLive(clientView(again.channel), "Live after joining again, on his client");
            check(again.player.getAbilities().flying, "Joining again landed a Live player who was flying");
        } finally { leave(again.player); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void speedSurvivesSwitchesDeathAndRespawn(GameTestHelper helper) {
        var joined = joinLive(helper, true);
        var players = new ServerPlayer[]{joined.player};
        try {
            assertSpeed(players[0], "Live");

            check(switchAndAcknowledge(players[0], GameType.CREATIVE), "G to Build failed");
            assertSpeed(players[0], "Build");
            check(players[0].getAbilities().instabuild, "Build mode lost creative's building");
            check(clientView(joined.channel).getWalkingSpeed() == LiveMode.DESKTOP_WALKING_SPEED,
                    "His client walks at the game's speed in Build mode");

            check(switchAndAcknowledge(players[0], GameType.SURVIVAL), "G back to Live failed");
            assertSpeed(players[0], "Live after Build");
            assertLive(players[0].getAbilities(), "Live after Build, on the server");
            assertLive(clientView(joined.channel), "Live after Build, on his client");

            // Death in Build mode (Live cannot die), and the game's respawn.
            check(switchAndAcknowledge(players[0], GameType.CREATIVE), "G to Build before dying failed");
            players[0].hurtServer(helper.getLevel(), players[0].damageSources().genericKill(), Float.MAX_VALUE);
            check(players[0].isDeadOrDying(), "Fixture: the Build player did not die");
            players[0] = respawn(players[0], false, Entity.RemovalReason.KILLED);
            check(players[0].gameMode() == GameType.CREATIVE, "He came back from death in another mode");
            assertSpeed(players[0], "Build after death");
            check(clientView(joined.channel).getWalkingSpeed() == LiveMode.DESKTOP_WALKING_SPEED,
                    "His client walks at the game's speed after dying");

            check(switchAndAcknowledge(players[0], GameType.SURVIVAL), "G to Live after death failed");
            assertSpeed(players[0], "Live after death");
            assertLive(clientView(joined.channel), "Live after death, on his client");

            // A respawn in Live mode keeping everything, as coming back from the End does.
            players[0] = respawn(players[0], true, Entity.RemovalReason.CHANGED_DIMENSION);
            check(LiveMode.isLive(players[0]), "The respawn left Live mode");
            assertSpeed(players[0], "Live after a respawn");
            assertLive(players[0].getAbilities(), "Live after a respawn, on the server");
            assertLive(clientView(joined.channel), "Live after a respawn, on his client");
        } finally { leave(players[0]); }
        helper.succeed();
    }

    /**
     * The speed reaches his client as the movement attribute (the game sends changed attributes with its entity
     * updates, a tick or two later), not only as the abilities' walking speed: his client moves him by the attribute.
     * Not within one tick, so a test beside it may switch the marker off and on in between; the last value counts.
     */
    @GameTest(environment = "aresos-test:desktop", maxTicks = 40)
    public void hisClientIsToldTheSpeed(GameTestHelper helper) {
        var joined = joinLive(helper, true);
        helper.runAtTickTime(10, () -> {
            try {
                var updates = joined.channel.outboundMessages().stream()
                        .filter(message -> message instanceof ClientboundUpdateAttributesPacket packet
                                && packet.getEntityId() == joined.player.getId())
                        .map(ClientboundUpdateAttributesPacket.class::cast)
                        .flatMap(packet -> packet.getValues().stream())
                        .filter(value -> value.attribute().equals(Attributes.MOVEMENT_SPEED))
                        .toList();
                check(!updates.isEmpty(), "His client was never told a movement speed");
                double base = updates.getLast().base();
                check(Math.abs(base - LiveMode.DESKTOP_WALKING_SPEED) < 1e-6, "His client was told movement speed " + base
                        + " (" + updates.stream().map(value -> String.valueOf(value.base())).toList() + ")");
            } finally { leave(joined.player); }
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop")
    public void liveFlightStillBreaksAndPlacesNothing(GameTestHelper helper) {
        var joined = joinLive(helper, true);
        var player = joined.player;
        var level = helper.getLevel();
        var server = level.getServer();
        BlockPos logo = helper.absolutePos(new BlockPos(4, 2, 2));
        level.setBlockAndUpdate(logo, Blocks.CONCRETE.red().defaultBlockState());
        var exit = AppZone.exit(level.dimension(), player.position(), new net.minecraft.world.phys.AABB(logo));
        var zone = new AppZone("live-flight-" + UUID.randomUUID(), "live-flight", level.dimension(), logo, logo, exit,
                List.of(logo));
        ZoneData.get(server).add(zone);
        try {
            var wanted = new Abilities();
            wanted.flying = true;
            player.connection.handlePlayerAbilities(new ServerboundPlayerAbilitiesPacket(wanted));
            check(player.getAbilities().flying, "Fixture: the Live player is not flying");

            // The creative inventory's way into the taskbar is closed.
            int slot = 8;
            ItemStack before = player.getInventory().getItem(slot).copy();
            player.connection.handleSetCreativeModeSlot(new ServerboundSetCreativeModeSlotPacket(36 + slot,
                    new ItemStack(Items.STONE)));
            check(ItemStack.matches(before, player.getInventory().getItem(slot)), "A creative slot packet put "
                    + player.getInventory().getItem(slot) + " into Live mode's taskbar");

            // Left-click does not break a logo at once, and breaking it is refused.
            player.gameMode.handleBlockBreakAction(logo, ServerboundPlayerActionPacket.Action.START_DESTROY_BLOCK,
                    Direction.WEST, level.getMaxY(), 0);
            check(level.getBlockState(logo).is(Blocks.CONCRETE.red()), "Left-click broke a logo at once in Live mode");
            check(!player.gameMode.destroyBlock(logo) && level.getBlockState(logo).is(Blocks.CONCRETE.red()),
                    "Live mode broke a logo");

            // Right-click with a taskbar item on the ground places nothing.
            player.getInventory().setSelectedSlot(0);
            player.getInventory().setItem(0, AppItems.create(new AppDefinition("live-flight", "Live flight",
                    List.of("none"), "minecraft:writable_book", false)));
            BlockPos ground = helper.absolutePos(new BlockPos(2, 1, 3));
            level.setBlockAndUpdate(ground, Blocks.STONE.defaultBlockState());
            player.gameMode.useItemOn(player, level, player.getMainHandItem(), InteractionHand.MAIN_HAND,
                    new BlockHitResult(Vec3.atCenterOf(ground).add(0, 0.5, 0), Direction.UP, ground, false));
            check(level.getBlockState(ground.above()).isAir(), "A taskbar item placed a block in Live mode");
            check(!player.getAbilities().instabuild && player.gameMode() == GameType.SURVIVAL,
                    "Live mode builds like creative");
        } finally {
            ZoneData.get(server).remove(z -> z.id().equals(zone.id()));
            leave(player);
        }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:normal")
    public void normalWorldKeepsTheGamesSurvival(GameTestHelper helper) {
        var joined = joinLive(helper, false);
        try {
            assertGameSurvival(joined.player.getAbilities(), "A normal world's survival, on the server");
            assertGameSurvival(clientView(joined.channel), "A normal world's survival, on his client");
            double movement = joined.player.getAttributeValue(Attributes.MOVEMENT_SPEED);
            check(Math.abs(movement - new Abilities().getWalkingSpeed()) < 1e-6, "A normal world's player moves at " + movement);
        } finally { leave(joined.player); }
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void markerOffGivesBackTheGamesSurvival(GameTestHelper helper) {
        var joined = joinLive(helper, true);
        var server = helper.getLevel().getServer();
        try {
            assertLive(joined.player.getAbilities(), "Fixture: Live");
            DesktopWorld.setEnabled(server, false);
            assertGameSurvival(joined.player.getAbilities(), "Survival after the marker went off, on the server");
            assertGameSurvival(clientView(joined.channel), "Survival after the marker went off, on his client");
            DesktopWorld.setEnabled(server, true);
            assertLive(joined.player.getAbilities(), "Live after the marker came back, on the server");
            assertLive(clientView(joined.channel), "Live after the marker came back, on his client");
        } finally {
            DesktopWorld.setEnabled(server, true);
            leave(joined.player);
        }
        helper.succeed();
    }

    private static ServerPlayer respawn(ServerPlayer player, boolean keepEverything, Entity.RemovalReason reason) {
        var replacement = player.level().getServer().getPlayerList().respawn(player, keepEverything, reason);
        // The game's packet handler makes the connection the new player's; the server-only fixture does it here.
        player.connection.player = replacement;
        return replacement;
    }

    private static void assertLive(Abilities abilities, String where) {
        check(abilities.mayfly, where + ": he cannot fly");
        check(abilities.invulnerable, where + ": he is not invulnerable");
        check(!abilities.instabuild, where + ": he builds like creative");
        check(abilities.getWalkingSpeed() == LiveMode.DESKTOP_WALKING_SPEED,
                where + ": walking speed " + abilities.getWalkingSpeed());
    }

    private static void assertGameSurvival(Abilities abilities, String where) {
        check(!abilities.mayfly && !abilities.flying && !abilities.invulnerable && !abilities.instabuild,
                where + ": abilities other than the game's survival");
        check(abilities.getWalkingSpeed() == new Abilities().getWalkingSpeed(),
                where + ": walking speed " + abilities.getWalkingSpeed());
    }

    /** Both halves of the speed, and the speed he really moves at when not sprinting. */
    private static void assertSpeed(ServerPlayer player, String where) {
        check(!player.isSprinting(), "Fixture: sprinting");
        check(player.getAbilities().getWalkingSpeed() == LiveMode.DESKTOP_WALKING_SPEED,
                where + ": walking speed " + player.getAbilities().getWalkingSpeed());
        double movement = player.getAttributeValue(Attributes.MOVEMENT_SPEED);
        check(Math.abs(movement - LiveMode.DESKTOP_WALKING_SPEED) < 1e-6, where + ": movement speed " + movement);
        check(player.getActiveEffects().isEmpty(), where + ": the speed shows as an effect");
    }

    /**
     * His client's abilities after every packet sent so far, applied as the client applies them: a new player on
     * login and respawn, the mode's own abilities whenever it hears the game mode, the server's values on an
     * abilities packet.
     */
    private static Abilities clientView(EmbeddedChannel channel) {
        var abilities = new Abilities();
        for (Object message : channel.outboundMessages()) abilities = apply(abilities, message);
        return abilities;
    }

    private static Abilities apply(Abilities abilities, Object message) {
        switch (message) {
            case ClientboundBundlePacket bundle -> {
                for (var packet : bundle.subPackets()) abilities = apply(abilities, packet);
            }
            case ClientboundLoginPacket login -> {
                abilities = new Abilities();
                login.commonPlayerSpawnInfo().gameType().updatePlayerAbilities(abilities);
            }
            case ClientboundRespawnPacket respawn -> {
                abilities = new Abilities();
                respawn.commonPlayerSpawnInfo().gameType().updatePlayerAbilities(abilities);
            }
            case ClientboundGameEventPacket event when event.getEvent() == ClientboundGameEventPacket.CHANGE_GAME_MODE ->
                    GameType.byId((int) event.getParam()).updatePlayerAbilities(abilities);
            case ClientboundPlayerAbilitiesPacket packet -> {
                abilities.flying = packet.isFlying();
                abilities.instabuild = packet.canInstabuild();
                abilities.invulnerable = packet.isInvulnerable();
                abilities.mayfly = packet.canFly();
                abilities.setFlyingSpeed(packet.getFlyingSpeed());
                abilities.setWalkingSpeed(packet.getWalkingSpeed());
            }
            default -> { }
        }
        return abilities;
    }
}
