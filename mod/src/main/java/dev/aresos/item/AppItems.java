package dev.aresos.item;

import com.mojang.serialization.Codec;
import dev.aresos.AresOs;
import dev.aresos.config.AppDefinition;
import dev.aresos.world.DesktopWorld;
import net.minecraft.core.Registry;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.UseEffects;

import java.util.List;

public final class AppItems {
    public static final DataComponentType<String> APP_ID = Registry.register(BuiltInRegistries.DATA_COMPONENT_TYPE,
            AresOs.id("app_id"), DataComponentType.<String>builder()
                    .persistent(Codec.STRING).networkSynchronized(ByteBufCodecs.STRING_UTF8).build());
    public static final Item APP = Registry.register(BuiltInRegistries.ITEM, AresOs.id("app"),
            new AppItem(new Item.Properties().setId(ResourceKey.create(Registries.ITEM, AresOs.id("app")))
                    .stacksTo(1)
                    .component(DataComponents.ITEM_MODEL, Identifier.withDefaultNamespace("writable_book"))
                    .component(DataComponents.USE_EFFECTS, new UseEffects(true, false, 1))));

    private AppItems() { }

    public static void register() { }

    public static ItemStack create(AppDefinition app) {
        var stack = new ItemStack(APP);
        stack.set(APP_ID, app.id());
        stack.set(DataComponents.CUSTOM_NAME, Component.literal(app.name()));
        Identifier lookId = Identifier.parse(app.look());
        var look = BuiltInRegistries.ITEM.containsKey(lookId) ? BuiltInRegistries.ITEM.getValue(lookId) : null;
        var model = look == null ? null : look.components().get(DataComponents.ITEM_MODEL);
        if (model == null) {
            AresOs.LOGGER.warn("Unknown item look {} for {}; using writable_book", app.look(), app.id());
            model = Identifier.withDefaultNamespace("writable_book");
        }
        stack.set(DataComponents.ITEM_MODEL, model);
        return stack;
    }

    public static void placePinned(ServerPlayer player, List<AppDefinition> apps) {
        if (!DesktopWorld.isEnabled(player.level().getServer())) return;
        var inventory = player.getInventory();
        for (AppDefinition app : apps) {
            if (!app.pinned()) continue;
            boolean present = false;
            for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
                ItemStack stack = inventory.getItem(slot);
                if (stack.is(APP) && app.id().equals(stack.get(APP_ID))) {
                    present = true;
                    break;
                }
            }
            if (present) continue;
            for (int slot = 0; slot < 9; slot++) {
                if (inventory.getItem(slot).isEmpty()) {
                    inventory.setItem(slot, create(app));
                    break;
                }
            }
        }
    }
}
