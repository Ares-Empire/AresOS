package dev.aresos.mode;

import com.mojang.serialization.Codec;
import com.mojang.serialization.Dynamic;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.aresos.AresOs;
import dev.aresos.item.AppInventory;
import dev.aresos.item.AppMenuPins;
import dev.aresos.mixin.GameModeAccess;
import dev.aresos.world.DesktopWorld;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundGameEventPacket;
import net.minecraft.network.protocol.game.ClientboundSetHeldSlotPacket;
import net.minecraft.network.protocol.game.ClientboundSetPlayerInventoryPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.ValueInput;
import net.minecraft.world.level.storage.ValueOutput;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;

/** Both snapshots travel in the same vanilla player save as the active inventory and game mode. */
public final class ModeInventories {
    public static final String SAVE_KEY = "aresos_mode_inventories";
    public static final int ACK_TIMEOUT_TICKS = 200;
    private static final Codec<Tag> RAW = Codec.PASSTHROUGH.xmap(
            dynamic -> dynamic.convert(NbtOps.INSTANCE).getValue(), tag -> new Dynamic<>(NbtOps.INSTANCE, tag));

    private record Snapshot(List<ItemStack> items, int selected) {
        private static final Codec<Snapshot> CODEC = RecordCodecBuilder.create(i -> i.group(
                ItemStack.OPTIONAL_CODEC.listOf().fieldOf("items").forGetter(Snapshot::items),
                Codec.intRange(0, 8).fieldOf("selected").forGetter(Snapshot::selected)).apply(i, Snapshot::new));

        static Snapshot capture(ServerPlayer player) {
            var inventory = player.getInventory();
            var items = new ArrayList<ItemStack>(inventory.getContainerSize());
            for (int slot = 0; slot < inventory.getContainerSize(); slot++) items.add(inventory.getItem(slot).copy());
            return new Snapshot(List.copyOf(items), inventory.getSelectedSlot());
        }

        void validateSize(ServerPlayer player) {
            if (items.size() != player.getInventory().getContainerSize())
                throw new IllegalStateException("Stored inventory has an unexpected slot count");
        }

        void apply(ServerPlayer player) {
            for (int slot = 0; slot < items.size(); slot++) player.getInventory().setItem(slot, items.get(slot).copy());
            player.getInventory().setSelectedSlot(selected);
            player.getInventory().setChanged();
        }

        boolean matches(Snapshot other) {
            return selected == other.selected && ItemStack.listMatches(items, other.items);
        }
    }

    private record Stored(int version, Snapshot live, Snapshot build, Optional<Boolean> buildActive) {
        private static final Codec<Stored> CODEC = RecordCodecBuilder.create(i -> i.group(
                Codec.intRange(1, 1).fieldOf("version").forGetter(Stored::version),
                Snapshot.CODEC.fieldOf("live").forGetter(Stored::live),
                Snapshot.CODEC.fieldOf("build").forGetter(Stored::build),
                Codec.BOOL.optionalFieldOf("build_active").forGetter(Stored::buildActive)).apply(i, Stored::new));
    }

    private record Rollback(Snapshot inventory, GameType mode, GameType previousMode, boolean flying,
                            Tag stored, GameType activeInventory) {
        static Rollback capture(ServerPlayer player, ModeInventories modes) {
            return new Rollback(Snapshot.capture(player), player.gameMode(), player.gameMode.getPreviousGameModeForPlayer(),
                    player.getAbilities().flying, modes.stored == null ? null : modes.stored.copy(), modes.activeInventory(player));
        }

        void restore(ServerPlayer player, ModeInventories modes) {
            Snapshot retainedInventory = inventory;
            Tag retainedStored = stored;
            Snapshot current = Snapshot.capture(player);
            if (!current.matches(modes.synchronizedInventory)) {
                if (modes.activeInventory(player) == activeInventory) {
                    // A refused/failed switch kept this inventory active. External changes still belong to it.
                    retainedInventory = current;
                } else {
                    // Void setters and in-place stack edits cannot reject a transfer safely. Keep the changed
                    // destination as the inactive inventory before restoring the original owner.
                    var ops = player.registryAccess().createSerializationContext(NbtOps.INSTANCE);
                    Snapshot empty = new Snapshot(Collections.nCopies(inventory.items.size(), ItemStack.EMPTY), 0);
                    Stored before = stored == null ? new Stored(1,
                            activeInventory == GameType.SURVIVAL ? inventory : empty,
                            activeInventory == GameType.CREATIVE ? inventory : empty, Optional.empty())
                            : Stored.CODEC.parse(ops, stored).getOrThrow();
                    Stored retained = modes.activeInventory(player) == GameType.SURVIVAL
                            ? new Stored(1, current, before.build, Optional.of(activeInventory == GameType.CREATIVE))
                            : new Stored(1, before.live, current, Optional.of(activeInventory == GameType.CREATIVE));
                    retainedStored = Stored.CODEC.encodeStart(ops, retained).getOrThrow();
                    Stored decoded = Stored.CODEC.parse(ops, retainedStored).getOrThrow();
                    if (!retained.live.matches(decoded.live) || !retained.build.matches(decoded.build))
                        throw new IllegalStateException("Recovery serialization changed an item");
                }
            }
            retainedInventory.apply(player);
            ((GameModeAccess) player.gameMode).aresos$setMode(mode, previousMode);
            player.getAbilities().flying = flying;
            modes.stored = retainedStored;
            modes.activeInventory = activeInventory;
            ((AppMenuPins) player.inventoryMenu).aresos$resetMove();
        }
    }

    // Keep unreadable data verbatim. Treating a broken inventory as empty would destroy its items.
    private Tag stored;
    private String loginError;
    private boolean restoredForLogin;
    private GameType activeInventory;
    private boolean changingMode;
    private boolean pending;
    private boolean completionSent;
    private long transaction;
    private int startedAtTick;
    private Rollback rollback;
    private Snapshot synchronizedInventory;

    public GameType activeInventory(ServerPlayer player) {
        if (activeInventory == null) activeInventory = player.gameMode.getGameModeForPlayer() == GameType.CREATIVE
                ? GameType.CREATIVE : GameType.SURVIVAL;
        return activeInventory;
    }

    public boolean changingMode() { return changingMode; }
    public boolean pending() { return pending; }
    public boolean blocksInsertions() { return pending && !changingMode; }
    public long pendingTransaction() { return transaction; }

    public void acknowledge(long id) {
        if (pending && completionSent && id == transaction) {
            pending = false;
            completionSent = false;
            rollback = null;
            synchronizedInventory = null;
        }
    }

    public void tick(ServerPlayer player) {
        if (!pending || player.level().getServer().getTickCount() - startedAtTick < ACK_TIMEOUT_TICKS) return;
        changingMode = true;
        try { rollback.restore(player, this); }
        finally { changingMode = false; }
        // The client may already be using the destination. Close its connection before accepting any more item input.
        player.connection.disconnect(Component.literal(
                "AresOS mode switch timed out; your original inventory and mode were restored. Reconnect to continue."));
        pending = false;
        completionSent = false;
        rollback = null;
        synchronizedInventory = null;
    }

    public static ModeInventories of(ServerPlayer player) {
        return ((ModeInventoryAccess) player).aresos$modeInventories();
    }

    public boolean hasStoredInventories() { return stored != null; }
    public boolean restoredForLogin() { return restoredForLogin; }

    /**
     * Rewrites the items of the inventory he is not holding right now (Build's while he is in Live, and the other
     * way round), slot by slot; an app's item is taken out of it this way. Never during a switch. The result is
     * checked the way a switch checks it, saved, read back and compared, before anything is kept; on any doubt
     * this throws and the saved inventory stays as it was.
     *
     * @return true when a slot changed
     */
    public boolean mapInactive(ServerPlayer player, java.util.function.UnaryOperator<ItemStack> change) {
        if (pending || changingMode) throw new IllegalStateException("The saved inventory cannot change during a mode switch");
        if (stored == null) return false;
        var ops = player.registryAccess().createSerializationContext(NbtOps.INSTANCE);
        Stored before = Stored.CODEC.parse(ops, stored).getOrThrow();
        boolean build = activeInventory(player) != GameType.CREATIVE;
        Snapshot inactive = build ? before.build : before.live;
        var items = new ArrayList<ItemStack>(inactive.items.size());
        boolean changed = false;
        for (ItemStack stack : inactive.items) {
            ItemStack mapped = change.apply(stack.copy());
            changed |= !ItemStack.matches(stack, mapped);
            items.add(mapped);
        }
        if (!changed) return false;
        Snapshot mapped = new Snapshot(List.copyOf(items), inactive.selected);
        Stored next = build ? new Stored(before.version, before.live, mapped, before.buildActive)
                : new Stored(before.version, mapped, before.build, before.buildActive);
        Tag encoded = Stored.CODEC.encodeStart(ops, next).getOrThrow();
        Stored prepared = Stored.CODEC.parse(ops, encoded).getOrThrow();
        if (!next.live.matches(prepared.live) || !next.build.matches(prepared.build))
            throw new IllegalStateException("Inventory serialization changed an item");
        stored = encoded;
        return true;
    }

    public void read(ValueInput input) {
        stored = input.read(SAVE_KEY, RAW).map(Tag::copy).orElse(null);
        activeInventory = stored instanceof net.minecraft.nbt.CompoundTag tag
                ? tag.getBoolean("build_active").map(build -> build ? GameType.CREATIVE : GameType.SURVIVAL).orElse(null) : null;
    }
    public void write(ValueOutput output) { if (stored != null) output.store(SAVE_KEY, RAW, stored); }

    public void copyFrom(ModeInventories previous) {
        stored = previous.stored == null ? null : previous.stored.copy();
        activeInventory = previous.activeInventory;
        // A replacement player keeps the connection; its client has already seen these transaction IDs.
        transaction = previous.transaction;
        pending = previous.pending;
        completionSent = previous.completionSent;
        startedAtTick = previous.startedAtTick;
        rollback = previous.rollback;
        synchronizedInventory = previous.synchronizedInventory;
    }

    public void reportLoginError(ServerPlayer player) {
        if (loginError != null) player.sendSystemMessage(Component.literal(loginError));
    }

    /** Before the login packet exists, use vanilla's mode setter without sending play packets. */
    public boolean enterLiveBeforeLogin(ServerPlayer player) {
        if (activeInventory(player) != GameType.CREATIVE) return true;
        restoredForLogin = switchTo(player, GameType.SURVIVAL, false);
        return restoredForLogin;
    }

    public boolean switchTo(ServerPlayer player, GameType target, boolean connected) {
        if (!DesktopWorld.isEnabled(player.level().getServer())) return false;
        if (connected && !supportsProtocol(player)) return false;
        if (pending) return fail(player, connected, "Wait for the AresOS inventory switch to finish", null);
        if (target == activeInventory(player) && target == player.gameMode.getGameModeForPlayer()) return false;
        if (connected) begin(player);
        changingMode = true;
        try { return transact(player, target, connected); }
        finally {
            changingMode = false;
            if (connected) sync(player);
        }
    }

    public void rejectToggle(ServerPlayer player) {
        if (pending) return;
        if (!supportsProtocol(player)) return;
        begin(player);
        sync(player);
    }

    private void begin(ServerPlayer player) {
        rollback = Rollback.capture(player, this);
        startedAtTick = player.level().getServer().getTickCount();
        pending = true;
        completionSent = false;
        transaction++;
        ServerPlayNetworking.send(player, new ModeSwitchStatePayload(transaction, false));
    }

    private boolean supportsProtocol(ServerPlayer player) {
        if (ServerPlayNetworking.canSend(player, ModeSwitchStatePayload.TYPE)) return true;
        return fail(player, true, "Cannot switch AresOS mode: this client does not support inventory-switch acknowledgements. Update AresOS and reconnect.", null);
    }

    private boolean transact(ServerPlayer player, GameType target, boolean connected) {
        GameType originalMode = player.gameMode.getGameModeForPlayer();
        GameType originalInventory = activeInventory(player);
        if (target != GameType.SURVIVAL && target != GameType.CREATIVE)
            return fail(player, connected, "AresOS supports only Live (survival) and Build (creative) mode", null);
        if (player.containerMenu != player.inventoryMenu || !player.inventoryMenu.getCarried().isEmpty()
                || !player.inventoryMenu.getCraftSlots().isEmpty()) {
            return fail(player, connected, "Close the menu and finish moving or crafting items before switching AresOS mode", null);
        }

        Snapshot original = Snapshot.capture(player);
        var previousMode = player.gameMode.getPreviousGameModeForPlayer();
        boolean flying = player.getAbilities().flying;
        Tag previousStored = stored;
        boolean changed = false;
        try {
            var ops = player.registryAccess().createSerializationContext(NbtOps.INSTANCE);
            Snapshot empty = new Snapshot(Collections.nCopies(original.items.size(), ItemStack.EMPTY), 0);
            Stored before = stored == null ? new Stored(1, empty, empty, Optional.empty()) : Stored.CODEC.parse(ops, stored).getOrThrow();
            before.live.validateSize(player);
            before.build.validateSize(player);
            Stored next = originalInventory == GameType.SURVIVAL
                    ? new Stored(1, original, before.build, Optional.of(target == GameType.CREATIVE))
                    : new Stored(1, before.live, original, Optional.of(target == GameType.CREATIVE));
            // Prepare both save and load completely before touching the player; reject even partial codec errors.
            Tag encoded = Stored.CODEC.encodeStart(ops, next).getOrThrow();
            Stored prepared = Stored.CODEC.parse(ops, encoded).getOrThrow();
            if (!next.live.matches(prepared.live) || !next.build.matches(prepared.build))
                throw new IllegalStateException("Inventory serialization changed an item");
            Snapshot destination = target == GameType.SURVIVAL ? prepared.live : prepared.build;

            player.stopUsingItem();
            changed = true;
            if (connected) {
                if (originalMode != target && !player.setGameMode(target)) throw new IllegalStateException("Game mode change was refused");
            } else ((GameModeAccess) player.gameMode).aresos$setMode(target, originalMode);
            destination.apply(player);
            if (previousStored == null && target == GameType.SURVIVAL) {
                AppInventory.populate(player);
                next = new Stored(1, Snapshot.capture(player), original, Optional.of(false));
                encoded = Stored.CODEC.encodeStart(ops, next).getOrThrow();
            }
            ((AppMenuPins) player.inventoryMenu).aresos$resetMove();
            stored = encoded;
            activeInventory = target;
            return true;
        } catch (RuntimeException error) {
            stored = previousStored;
            if (changed) {
                original.apply(player);
                ((GameModeAccess) player.gameMode).aresos$setMode(originalMode, previousMode);
                player.getAbilities().flying = flying;
                if (connected) {
                    player.onUpdateAbilities();
                }
            }
            return fail(player, connected, "Could not switch AresOS mode; your inventory and mode were kept. Restore the world backup if this persists.", error);
        }
    }

    private static void sync(ServerPlayer player) {
        player.connection.send(new ClientboundGameEventPacket(ClientboundGameEventPacket.CHANGE_GAME_MODE,
                player.gameMode.getGameModeForPlayer().getId()));
        player.inventoryMenu.sendAllDataToRemote();
        // InventoryMenu omits player equipment slots such as body armor. Acknowledgement covers every slot.
        for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++)
            player.connection.send(new ClientboundSetPlayerInventoryPacket(slot, player.getInventory().getItem(slot).copy()));
        player.connection.send(new ClientboundSetHeldSlotPacket(player.getInventory().getSelectedSlot()));
        var modes = of(player);
        if (modes.pending) {
            modes.synchronizedInventory = Snapshot.capture(player);
            modes.completionSent = true;
            ServerPlayNetworking.send(player, new ModeSwitchStatePayload(modes.transaction, true));
        }
    }

    private boolean fail(ServerPlayer player, boolean connected, String message, RuntimeException error) {
        if (error != null) AresOs.LOGGER.error("AresOS inventory switch failed; original state kept", error);
        if (connected) player.sendSystemMessage(Component.literal(message));
        else loginError = message;
        return false;
    }
}
