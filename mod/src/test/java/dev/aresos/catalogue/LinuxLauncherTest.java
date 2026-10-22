package dev.aresos.catalogue;

import dev.aresos.client.launch.LinuxAppLauncher;
import dev.aresos.config.AppDefinition;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class LinuxLauncherTest {
 @Test void commandsAndUrlsFailClosedWithoutAHelper() {
  var launcher=new LinuxAppLauncher();
  var error=assertThrows(java.util.concurrent.CompletionException.class,()->launcher.launch(List.of("must-never-run")).toCompletableFuture().join());
  assertTrue(error.getCause().getMessage().contains("aresos-shell/1.0"));
  assertThrows(java.util.concurrent.CompletionException.class,()->launcher.launch(new AppDefinition("site","Site",List.of(),"minecraft:paper",false,"url","https://example.test",null)).toCompletableFuture().join());
 }
}
