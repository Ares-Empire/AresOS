package dev.aresos.catalogue;

import dev.aresos.config.AppDefinition;
import java.util.List;

public final class LinuxAppCatalogue implements AppCatalogue {
    public static final String PROTOCOL = "aresos-shell/1.0";
    public static final String UNAVAILABLE = "AresOS app helper is unavailable (" + PROTOCOL + ")";
    @Override public List<AppDefinition> listApps() { return List.of(); }
}
