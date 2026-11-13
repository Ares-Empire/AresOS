package dev.aresos.client;

import dev.aresos.icon.IconRefresh;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;

/**
 * The game's side of {@link IconRefresh}: loads the resource packs again when the icon pack changed. How often is
 * the refresher's decision; it asks for one reload at a time and waits for it.
 */
final class IconReload {
    private static final AtomicReference<CompletableFuture<Void>> WANTED = new AtomicReference<>();

    private IconReload() { }

    static void register(IconRefresh refresh) {
        refresh.reloader(() -> {
            var wanted = new CompletableFuture<Void>();
            var before = WANTED.getAndSet(wanted);
            // Never left hanging: an earlier request is served by the same reload.
            if (before != null) wanted.whenComplete((done, error) -> {
                if (error == null) before.complete(null); else before.completeExceptionally(error);
            });
            return wanted;
        });
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            // While another reload runs (the game's start, F3+T) a new one would be answered with that one, which
            // may have read the pack before it changed. Wait until it is over.
            if (WANTED.get() == null || client.gui.overlay() != null) return;
            var wanted = WANTED.getAndSet(null);
            client.reloadResourcePacks().whenComplete((done, error) -> {
                if (error == null) wanted.complete(null); else wanted.completeExceptionally(error);
            });
        });
    }
}
