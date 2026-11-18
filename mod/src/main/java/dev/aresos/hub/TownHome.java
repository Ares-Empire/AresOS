package dev.aresos.hub;

import dev.aresos.AresOs;
import dev.aresos.catalogue.AppGroup;
import dev.aresos.config.AppDefinition;
import dev.aresos.mode.ModeInventories;
import dev.aresos.names.NameRules;
import dev.aresos.shell.HomeState;
import dev.aresos.shell.ShellClient;
import dev.aresos.zone.GatePicture;
import net.minecraft.server.level.ServerPlayer;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

/** Captures the town on its server thread, including the host's Live slots. */
final class TownHome {
    private ShellClient publishedTo;
    private List<AppDefinition> capturedApps;
    private Map<String, Integer> capturedSlots;
    private long capturedLogos;
    private int firstPass = -1;
    private boolean ready;

    void passed(int tick, boolean emptyBefore, boolean waiting) {
        if (firstPass == -1) {
            firstPass = tick;
            ready = !emptyBefore;
        }
        if (!waiting) ready = true;
    }

    void picturesChanged() { capturedApps = null; }

    void clear() {
        if (publishedTo != null) publishedTo.home(null);
        publishedTo = null;
    }

    void publish(ServerPlayer host, HubData hub, Function<AppDefinition, Optional<GatePicture>> pictures) {
        var shell = AresOs.shell();
        if (shell == null || !shell.tracksHome() || firstPass == -1) return;
        if (!ready && host.level().getServer().getTickCount() - firstPass < TownLines.FirstBuild.WAIT_TICKS) return;
        var slots = ModeInventories.of(host).liveHotbar(host);
        if (slots.isEmpty()) return;
        var apps = AresOs.apps();
        long logos = hub.logoRevision();
        if (shell == publishedTo && apps == capturedApps && logos == capturedLogos && slots.get().equals(capturedSlots)) return;
        var snapshot = capture(apps, hub, slots.get(), pictures);
        if (snapshot.isEmpty()) return;
        ready = true;
        shell.home(snapshot.get());
        capturedApps = apps;
        capturedSlots = slots.get();
        capturedLogos = logos;
        publishedTo = shell;
    }

    static Optional<HomeState> capture(List<AppDefinition> apps, HubData hub, Map<String, Integer> slots,
                                       Function<AppDefinition, Optional<GatePicture>> pictures) {
        var standing = new HashMap<String, HubData.Logo>();
        for (var logo : hub.logos()) standing.put(logo.app(), logo);
        var rows = new ArrayList<HomeState.App>();
        boolean waitingForName = false;
        for (var app : apps) {
            if (!app.mine()) continue;
            String shortName = NameRules.mainName(app);
            if (shortName.isEmpty()) {
                waitingForName = true;
                continue;
            }

            var logo = standing.get(app.id());
            var place = Place.parse(logo == null ? app.place() : logo.place());
            List<String> front;
            if (logo != null && place.isPresent()) front = hub.front(logo, place.get());
            else {
                var picture = pictures.apply(app);
                // Removed programs keep their My apps and place reservations. The helper's catalogue filters them.
                if (picture.isEmpty() && app.absent()) picture = Optional.of(TownKeeper.plainFront(app));
                if (picture.isEmpty()) return Optional.empty();
                front = front(picture.get());
            }
            rows.add(new HomeState.App(app.id(), app.name(), shortName, AppGroup.of(app).key(),
                    place.map(Place::name).orElse(null), slots.get(app.id()), front, logo != null));
        }
        if (rows.isEmpty() && waitingForName) return Optional.empty();
        return Optional.of(new HomeState(rows));
    }

    private static List<String> front(GatePicture picture) {
        var front = new ArrayList<String>(HubLayout.SIZE * HubLayout.SIZE);
        for (int row = HubLayout.SIZE - 1; row >= 0; row--) for (int x = 0; x < HubLayout.SIZE; x++) {
            String block = picture.at(x, row);
            front.add(block == null ? "" : block);
        }
        return front;
    }
}
