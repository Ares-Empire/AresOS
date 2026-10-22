package dev.aresos.test;

import com.mojang.authlib.GameProfile;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.item.AppItems;
import dev.aresos.mode.LiveMode;
import dev.aresos.world.DesktopWorld;
import io.netty.channel.embedded.EmbeddedChannel;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.LevelData;

import java.util.List;
import java.util.UUID;

public final class AresOsGameTests {
    private static ServerPlayer join(GameTestHelper helper) {
        return join(helper, true);
    }

    private static ServerPlayer join(GameTestHelper helper, boolean desktop) {
        DesktopWorld.setEnabled(helper.getLevel().getServer(), desktop);
        var cookie = CommonListenerCookie.createInitial(new GameProfile(UUID.randomUUID(), "AresTest"), false);
        var player = new ServerPlayer(helper.getLevel().getServer(), helper.getLevel(),
                cookie.gameProfile(), cookie.clientInformation());
        var connection = new Connection(PacketFlow.SERVERBOUND);
        new EmbeddedChannel(connection);
        helper.getLevel().getServer().getPlayerList().placeNewPlayer(connection, player, cookie);
        ModeInventoryFixtures.registerStateReceiver(player);
        player.connection.handleAcceptPlayerLoad(new net.minecraft.network.protocol.game.ServerboundPlayerLoadedPacket());
        player.setGameMode(GameType.SURVIVAL);
        ModeInventoryFixtures.acknowledge(player);
        BlockPos pos = helper.absolutePos(new BlockPos(2, 2, 2));
        player.snapTo(pos.getX() + 0.5, pos.getY(), pos.getZ() + 0.5);
        helper.assertTrue(player.connection.hasClientLoaded()
                && !player.isInvulnerableTo(helper.getLevel(), player.damageSources().lava()),
                "Test player is still protected by vanilla's join immunity");
        return player;
    }

    private static void leave(ServerPlayer player) {
        player.level().getServer().getPlayerList().remove(player);
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 80)
    public void lavaFallAndAttackCannotDamage(GameTestHelper helper) {
        ServerPlayer player = join(helper);
        helper.setBlock(2, 1, 2, Blocks.STONE);
        helper.setBlock(2, 2, 2, Blocks.LAVA);
        var zombie = new Zombie(EntityTypes.ZOMBIE, helper.getLevel());
        float health = player.getHealth();
        player.hurtServer(helper.getLevel(), player.damageSources().mobAttack(zombie), 1000);
        player.causeFallDamage(100, 1, player.damageSources().fall());
        for (int tick = 1; tick < 60; tick++) {
            // An embedded connection is not in the real network loop; tick its player physics explicitly.
            helper.runAtTickTime(tick, player.connection::tick);
        }
        helper.runAtTickTime(60, () -> {
            player.connection.tick();
            helper.assertTrue(player.isInLava(), "Lava test player was not in lava");
            helper.assertTrue(player.getHealth() == health && player.isAlive(), "Lava, falling or attack damaged Live player");
            leave(player);
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop")
    public void everyDamageTypeIsBlocked(GameTestHelper helper) {
        ServerPlayer player = join(helper);
        float health = player.getHealth();
        for (var type : helper.getLevel().registryAccess().lookupOrThrow(Registries.DAMAGE_TYPE).listElements().toList()) {
            player.hurtServer(helper.getLevel(), new DamageSource(type), Float.MAX_VALUE);
            helper.assertTrue(player.isAlive() && player.getHealth() == health,
                    "Damage type bypassed Live protection: " + type.key().identifier());
        }
        leave(player);
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 160)
    public void sprintingAndJumpingKeepFoodFull(GameTestHelper helper) {
        ServerPlayer player = join(helper);
        player.setSprinting(true);
        for (int tick = 1; tick <= 120; tick++) {
            helper.runAtTickTime(tick, () -> {
                helper.assertTrue(player.getFoodData().getFoodLevel() == 20
                        && player.getFoodData().getSaturationLevel() == 20, "Live hunger or saturation drained");
                player.setOnGround(true);
                player.jumpFromGround();
                player.checkMovementStatistics(5, 0, 0);
                player.causeFoodExhaustion(8);
                player.connection.tick();
            });
        }
        helper.runAtTickTime(122, () -> {
            helper.assertTrue(player.getFoodData().getFoodLevel() == 20
                    && player.getFoodData().getSaturationLevel() == 20, "Food did not stay full after exercise");
            leave(player);
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop", maxTicks = 40)
    public void belowBottomReturnsToPersonalSpawn(GameTestHelper helper) {
        ServerPlayer player = join(helper);
        BlockPos spawn = helper.absolutePos(new BlockPos(4, 2, 4));
        helper.setBlock(4, 1, 4, Blocks.STONE);
        player.setRespawnPosition(new ServerPlayer.RespawnConfig(
                LevelData.RespawnData.of(helper.getLevel().dimension(), spawn, 0, 0), true), false);
        player.setPos(spawn.getX() + 20, helper.getLevel().getMinY() - 1, spawn.getZ() + 20);
        player.fallDistance = 100;
        helper.runAtTickTime(3, () -> {
            helper.assertTrue(player.position().distanceToSqr(net.minecraft.world.phys.Vec3.atCenterOf(spawn)) < 4,
                    "Void recovery missed personal spawn: " + player.position());
            helper.assertTrue(player.isAlive() && player.fallDistance == 0, "Void recovery left player dead or falling");
            leave(player);
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:desktop")
    public void pinnedAppsRespectOccupiedSlotsAndExistingInventory(GameTestHelper helper) {
        ServerPlayer player = join(helper);
        var inventory = player.getInventory();
        inventory.clearContent();
        inventory.setItem(0, new ItemStack(Items.DIAMOND, 7));
        inventory.setItem(2, new ItemStack(Items.STONE, 12));
        AppItems.placePinned(player, AresOs.apps());
        AppItems.placePinned(player, AresOs.apps());
        helper.assertTrue(inventory.getItem(0).is(Items.DIAMOND) && inventory.getItem(0).getCount() == 7,
                "Pinned app overwrote occupied slot");
        helper.assertTrue(inventory.getItem(1).is(AppItems.APP) && inventory.getItem(2).is(Items.STONE),
                "Pinned app missed first free hotbar slot");
        int count = 0;
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            if (inventory.getItem(slot).is(AppItems.APP)) count++;
        }
        helper.assertTrue(count == 1, "Pinned placement duplicated app");
        inventory.setItem(12, inventory.getItem(1));
        inventory.setItem(1, ItemStack.EMPTY);
        AppItems.placePinned(player, AresOs.apps());
        helper.assertTrue(inventory.getItem(1).is(AppItems.APP) && inventory.getItem(12).isEmpty(),
                "Existing pinned app was not moved from main inventory to hotbar");
        inventory.setItem(1, ItemStack.EMPTY);
        inventory.setItem(12, ItemStack.EMPTY);
        inventory.setItem(40, AppItems.create(AresOs.apps().getFirst()));
        AppItems.placePinned(player, AresOs.apps());
        helper.assertTrue(inventory.getItem(1).is(AppItems.APP) && inventory.getItem(40).isEmpty(),
                "Configured offhand pin was not moved into the free hotbar slot");
        inventory.clearContent();
        for (int slot = 0; slot < 9; slot++) inventory.setItem(slot, new ItemStack(Items.STONE));
        AppItems.placePinned(player, AresOs.apps());
        for (int slot = 0; slot < 9; slot++) {
            helper.assertTrue(inventory.getItem(slot).is(Items.STONE), "Full hotbar was overwritten");
        }
        inventory.clearContent();
        AppItems.placePinned(player, List.of(new AppDefinition("unpinned", "Unpinned", List.of("none"),
                "minecraft:paper", false)));
        helper.assertTrue(inventory.isEmpty(), "Unpinned app was added");
        leave(player);
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void catalogueFillsInventoryWithoutOverwritingAndRefreshesSavedItems(GameTestHelper helper) {
        ServerPlayer player = join(helper);
        var inventory = player.getInventory();
        inventory.clearContent();
        inventory.setItem(0, new ItemStack(Items.DIAMOND, 7));
        inventory.setItem(9, new ItemStack(Items.STONE, 12));
        var apps = new java.util.ArrayList<AppDefinition>();
        for (int i = 0; i < 42; i++) apps.add(new AppDefinition("fixture-" + i, "Fixture " + i,
                List.of("fixture.exe"), "minecraft:paper", i == 0));
        inventory.setItem(10, AppItems.create(apps.get(1)));
        inventory.getItem(10).set(net.minecraft.core.component.DataComponents.ITEM_MODEL,
                net.minecraft.resources.Identifier.withDefaultNamespace("writable_book"));
        dev.aresos.item.AppInventory.populate(player, apps);
        dev.aresos.item.AppInventory.populate(player, apps);
        helper.assertTrue(inventory.getItem(0).is(Items.DIAMOND) && inventory.getItem(0).getCount() == 7,
                "Catalogue overwrote a hotbar item");
        helper.assertTrue(inventory.getItem(9).is(Items.STONE) && inventory.getItem(9).getCount() == 12,
                "Catalogue overwrote an inventory item");
        helper.assertTrue("fixture-0".equals(inventory.getItem(1).get(AppItems.APP_ID)), "Pinned fixture missing");
        helper.assertTrue(net.minecraft.resources.Identifier.withDefaultNamespace("paper").equals(
                inventory.getItem(10).get(net.minecraft.core.component.DataComponents.ITEM_MODEL)), "Saved icon model was not refreshed");
        var ids = new java.util.HashSet<String>();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) if (inventory.getItem(slot).is(AppItems.APP)) {
            helper.assertTrue(ids.add(inventory.getItem(slot).get(AppItems.APP_ID)), "Catalogue duplicated an item");
        }
        helper.assertTrue(ids.size() == 27, "Catalogue did not fill exactly the available 26 inventory slots plus pin");
        player.setGameMode(net.minecraft.world.level.GameType.CREATIVE);
        inventory.clearContent();
        dev.aresos.item.AppInventory.populate(player, apps);
        helper.assertTrue(inventory.isEmpty(), "Build mode received catalogue items");
        leave(player);
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void dedicatedServerRejectsModeToggle(GameTestHelper helper) {
        ServerPlayer player = join(helper);
        helper.assertTrue(!LiveMode.toggleForHost(helper.getLevel().getServer(), player),
                "Dedicated server accepted mode toggle");
        helper.assertTrue(player.gameMode.getGameModeForPlayer() == GameType.SURVIVAL,
                "Rejected mode toggle changed game mode");
        leave(player);
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:desktop")
    public void invalidLookFallsBackToVanillaBook(GameTestHelper helper) {
        var app = new AppDefinition("missing-look", "Missing look", List.of("none"),
                "minecraft:nonexistent_aresos_test_item", false);
        var stack = AppItems.create(app);
        helper.assertTrue(net.minecraft.resources.Identifier.withDefaultNamespace("writable_book")
                .equals(stack.get(net.minecraft.core.component.DataComponents.ITEM_MODEL)), "Invalid look had no fallback");
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:normal")
    public void normalWorldAllowsDamageAndDeath(GameTestHelper helper) {
        ServerPlayer player = join(helper, false);
        helper.assertTrue(!LiveMode.isLive(player), "Normal survival player has Live protection");
        player.causeFallDamage(10, 1, player.damageSources().fall());
        helper.assertTrue(player.getHealth() < player.getMaxHealth(), "Normal fall damage was blocked");
        player.invulnerableTime = 0;
        player.hurtServer(helper.getLevel(), player.damageSources().genericKill(), Float.MAX_VALUE);
        helper.assertTrue(player.isDeadOrDying(), "Normal death was blocked");
        leave(player);
        helper.succeed();
    }

    @GameTest(environment = "aresos-test:normal", maxTicks = 30)
    public void normalWorldHungerDrains(GameTestHelper helper) {
        ServerPlayer player = join(helper, false);
        player.getFoodData().setSaturation(0);
        for (int tick = 1; tick <= 10; tick++) {
            helper.runAtTickTime(tick, () -> {
                player.causeFoodExhaustion(8);
                player.connection.tick();
            });
        }
        helper.runAtTickTime(12, () -> {
            helper.assertTrue(player.getFoodData().getFoodLevel() < 20
                    && player.getFoodData().getSaturationLevel() == 0, "Normal hunger was refilled");
            leave(player);
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:normal", maxTicks = 20)
    public void normalWorldVoidDoesNotRescue(GameTestHelper helper) {
        ServerPlayer player = join(helper, false);
        player.setPos(player.getX(), helper.getLevel().getMinY() - 100, player.getZ());
        for (int tick = 1; tick <= 3; tick++) helper.runAtTickTime(tick, player.connection::tick);
        helper.runAtTickTime(4, () -> {
            helper.assertTrue(player.getY() < helper.getLevel().getMinY(), "Normal void fall was rescued");
            helper.assertTrue(player.getHealth() < player.getMaxHealth(), "Normal void damage was blocked");
            leave(player);
            helper.succeed();
        });
    }

    @GameTest(environment = "aresos-test:normal")
    public void normalWorldNeverPlacesPinnedApps(GameTestHelper helper) {
        ServerPlayer player = join(helper, false);
        helper.assertTrue(player.getInventory().isEmpty(), "Join placed app items in a normal world");
        AppItems.placePinned(player, AresOs.apps());
        helper.assertTrue(player.getInventory().isEmpty(), "Normal world accepted pinned app placement");
        leave(player);
        helper.succeed();
    }
}
