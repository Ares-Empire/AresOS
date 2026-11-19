package dev.aresos.shell;

import java.util.List;

/** Immutable town data captured on the integrated server thread. An empty cell has an empty block name. */
public record HomeState(List<App> apps) {
    public HomeState { apps = List.copyOf(apps); }

    /** Standing is tracked so a completed build advances the revision even at an already assigned place. */
    public record App(String id, String name, String shortName, String group, String place, Integer slot,
                      List<String> front, boolean standing) {
        public App { front = List.copyOf(front); }
    }
}
