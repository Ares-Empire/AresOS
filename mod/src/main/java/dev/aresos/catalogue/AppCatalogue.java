package dev.aresos.catalogue;

import dev.aresos.config.AppDefinition;
import java.io.IOException;
import java.util.List;

/** Local list_apps side of aresos-shell/1.0; Linux will replace this stub with the helper transport. */
public interface AppCatalogue {
    List<AppDefinition> listApps() throws IOException;
}
