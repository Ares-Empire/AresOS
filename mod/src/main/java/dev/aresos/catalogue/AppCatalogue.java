package dev.aresos.catalogue;

import dev.aresos.config.AppDefinition;
import java.io.IOException;
import java.util.List;

/** Where the list of apps comes from: Windows discovery, or list_apps of the AresOS app helper on Linux. */
public interface AppCatalogue {
    List<AppDefinition> listApps() throws IOException;
}
