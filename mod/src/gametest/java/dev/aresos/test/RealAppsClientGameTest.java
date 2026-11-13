package dev.aresos.test;

import com.mojang.blaze3d.platform.InputConstants;
import dev.aresos.AresOs;
import dev.aresos.client.*;
import dev.aresos.config.*;
import dev.aresos.icon.*;
import dev.aresos.item.AppItems;
import dev.aresos.test.mixin.AppsTestAccess;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.*;
import net.fabricmc.fabric.api.client.gametest.v1.screenshot.TestScreenshotOptions;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.gui.screens.worldselection.WorldCreationUiState;
import net.minecraft.client.input.*;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.level.GameType;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public final class RealAppsClientGameTest implements FabricClientGameTest {
    @Override public void runTest(ClientGameTestContext context) {
        var previousApps=AresOs.apps(); var previousIcons=AresOs.generatedIcons;
        String previousConfig=System.getProperty("aresos.appsConfig");
        var calls=new CopyOnWriteArrayList<List<String>>();
        var previousLauncher=AresOsClient.replaceLauncher(command->{calls.add(List.copyOf(command));return CompletableFuture.completedFuture(null);});
        try {
            Path root=Path.of("real-app-fixtures").toAbsolutePath(); Files.createDirectories(root);
            for(String name:List.of("compass","sunset")) try(var input=getClass().getResourceAsStream("/icons/"+name+".png")) {
                Files.copy(input,root.resolve(name+".png"),StandardCopyOption.REPLACE_EXISTING);
            }
            var fixtures=new ArrayList<AppDefinition>();
            fixtures.add(new AppDefinition("fixture-notes","Fixture Notes",List.of("fixture-notes.exe"),"minecraft:book",true,"command",null,root.resolve("compass.png").toString()));
            // The inventory holds My apps and nothing else: every fixture this test expects an item for is his.
            fixtures.add(new AppDefinition("fixture-site","Fixture Moodle",List.of(),"minecraft:paper",false,"url","https://example.test/moodle",null).withMine(true));
            for(int i=0;i<40;i++) fixtures.add(new AppDefinition("fixture-"+i,"Fixture "+(i+1),List.of("fixture-"+i+".exe"),"minecraft:paper",false,"command",null,root.resolve((i%2==0?"sunset":"compass")+".png").toString()).withMine(true));
            Path config=root.resolve("apps.json");AppsConfig.save(config,fixtures);System.setProperty("aresos.appsConfig",config.toString());
            context.runOnClient(client->AppsTestAccess.aresos$setApps(List.copyOf(fixtures)));
            AresOs.generatedIcons=IconPack.generate(AresOs.iconPackPath(),fixtures,new PixelIconConverter()).generated();
            var reload=context.computeOnClient(client->client.reloadResourcePacks());
            context.waitFor(client->reload.isDone());reload.join();
            TestWorldSave save;
            try(var world=context.worldBuilder().adjustSettings(settings->{settings.setGameMode(WorldCreationUiState.SelectedGameMode.SURVIVAL);settings.setAllowCommands(false);}).create()) {
                save=world.getWorldSave();world.getConnection().waitForChunksRender();
                context.getInput().pressKey(options->options.keyInventory);context.waitForScreen(InventoryScreen.class);
                check(!context.tryClickScreenButton("Apps…"),"Normal inventory got an Apps button");
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
                context.runOnClient(client->client.player.connection.sendCommand("aresos desktop on"));
                context.waitFor(client->"fixture-notes".equals(client.player.getInventory().getItem(0).get(AppItems.APP_ID)));
                context.runOnClient(client->{
                    var inventory=client.player.getInventory();
                    check("fixture-site".equals(inventory.getItem(9).get(AppItems.APP_ID)),"URL missing from inventory");
                    check(AresOs.id("apps/fixture-notes").equals(inventory.getItem(0).get(DataComponents.ITEM_MODEL)),"Generated icon model missing");
                    check(AresOs.id("apps/fixture-0").equals(inventory.getItem(10).get(DataComponents.ITEM_MODEL)),"Fixture generated model missing");
                    check(client.getResourceManager().getResource(AresOs.id("textures/item/apps/fixture-0.png")).isPresent(),"Runtime icon pack was not mounted");
                    check(client.getModelManager().getItemModel(AresOs.id("apps/fixture-0")) != client.getModelManager().getItemModel(AresOs.id("missing-fixture-model")),"Generated item resolved to missing model");
                });
                context.getInput().pressKey(options->options.keyInventory);context.waitForScreen(InventoryScreen.class);
                context.waitTicks(5);screenshot(context,"07-inventory-fixtures");
                // Vanilla pickup/drag/place sends real container clicks to the integrated server.
                clickSlot(context,9);context.waitTick();
                context.runOnClient(client->check(!client.player.inventoryMenu.getCarried().isEmpty(),"Did not pick up URL item"));
                check(!AppsConfig.load(config).apps().get(1).pinned(),"Pickup alone changed pins");
                clickSlot(context,37);
                world.getConnection().waitForServerboundPackets();
                context.waitFor(client->AresOs.app("fixture-site").pinned());
                check(AppsConfig.load(config).apps().get(1).pinned(),"URL pin was not persisted");
                // Move the original pinned app out of the hotbar as well.
                clickSlot(context,36);clickSlot(context,9);
                world.getConnection().waitForServerboundPackets();
                context.waitFor(client->!AresOs.app("fixture-notes").pinned());
                check(!AppsConfig.load(config).apps().getFirst().pinned(),"Unpin was not persisted");
                context.clickScreenButton("Apps…");context.waitForScreen(AppsScreen.class);
                context.clickScreenButton("›");screenshot(context,"07-apps-page-2");
                context.clickScreenButton("    Fixture 40");context.waitForScreen(InventoryScreen.class);
                context.waitFor(client->"fixture-39".equals(client.player.inventoryMenu.getCarried().get(AppItems.APP_ID)));
                clickSlot(context,38);world.getConnection().waitForServerboundPackets();
                context.waitFor(client->AresOs.app("fixture-39").pinned());
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
                context.getInput().pressKey(InputConstants.KEY_2);
                context.getInput().holdKeyFor(options->options.keyUse,12);context.waitTicks(3);
                check(calls.equals(List.of(List.of("https://example.test/moodle"))),"Held URL click did not launch exactly once: "+calls);
                context.getInput().pressKey(options->options.keyUse);context.waitTicks(3);
                check(calls.size()==2,"New URL click did not launch once");
                context.getInput().pressKey(InputConstants.KEY_G);context.waitFor(client->client.gameMode.getPlayerMode()==GameType.CREATIVE);
                context.runOnClient(client->check(!AppsScreen.active(client),"Apps active in Build mode"));
                context.getInput().pressKey(InputConstants.KEY_G);context.waitFor(client->client.gameMode.getPlayerMode()==GameType.SURVIVAL);
            }
            context.runOnClient(client->AppsTestAccess.aresos$setApps(readConfig(config)));
            try(var reopened=save.open()) {
                reopened.getConnection().waitForChunksRender();
                context.waitFor(client->"fixture-site".equals(client.player.getInventory().getItem(1).get(AppItems.APP_ID)));
                check(AresOs.app("fixture-site").pinned(),"Pin did not survive config reload/rejoin");
                check(!AresOs.app("fixture-notes").pinned(),"Unpin did not survive config reload/rejoin");
                context.getInput().pressKey(options->options.keyInventory);context.waitForScreen(InventoryScreen.class);
                screenshot(context,"07-pins-after-rejoin");
                context.getInput().pressKey(InputConstants.KEY_ESCAPE);
            }
            AresOs.LOGGER.info("07 client checks passed: fixture textures and mounted models, normal/Build gating, inventory and page 2, vanilla drag pin/unpin persisted across config reload and rejoin, overflow item pickup, URL one launch per click");
        } catch(Exception error) {throw new RuntimeException(error);}
        finally {
            context.runOnClient(client->{AppsTestAccess.aresos$setApps(previousApps);AresOs.generatedIcons=previousIcons;AresOsClient.replaceLauncher(previousLauncher);AresOsClient.FOCUS_RETURN.reset();});
            if(previousConfig==null) System.clearProperty("aresos.appsConfig");else System.setProperty("aresos.appsConfig",previousConfig);
        }
    }
    private static List<AppDefinition> readConfig(Path file) {try{return AppsConfig.load(file).apps();}catch(Exception error){throw new RuntimeException(error);}}
    private static void clickSlot(ClientGameTestContext context,int slotId) {
        context.runOnClient(client->{
            var screen=(InventoryScreen)client.gui.screen();var slot=client.player.inventoryMenu.getSlot(slotId);
            double x=(screen.width-176)/2.0+slot.x+8,y=(screen.height-166)/2.0+slot.y+8;
            var event=new MouseButtonEvent(x,y,new MouseButtonInfo(0,0));
            screen.mouseClicked(event,false);screen.mouseDragged(event,0,0);screen.mouseReleased(event);
        });context.waitTick();
    }
    private static void screenshot(ClientGameTestContext context,String name) {
        context.takeScreenshot(TestScreenshotOptions.of(name).withDestinationDir(Path.of(System.getProperty("aresos.appsReviewDir"))));
    }
    private static void check(boolean condition,String message){if(!condition)throw new AssertionError(message);}
}
