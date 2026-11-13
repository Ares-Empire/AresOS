package dev.aresos.icon;

import dev.aresos.config.AppDefinition;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import javax.imageio.ImageIO;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class IconTest {
    @TempDir Path directory;
    @Test void conversionMatchesHandmadeFixtureGoldens() throws Exception {
        for (String name : List.of("compass", "sunset")) {
            var source = ImageIO.read(getClass().getResource("/icons/"+name+".png"));
            var golden = ImageIO.read(getClass().getResource("/icons/"+name+"-golden.png"));
            var output = new PixelIconConverter().convert(source);
            assertEquals(16,output.getWidth()); assertEquals(16,output.getHeight());
            assertArrayEquals(golden.getRGB(0,0,16,16,null,0,16),output.getRGB(0,0,16,16,null,0,16));
            var colors=new HashSet<Integer>();
            for(int color:output.getRGB(0,0,16,16,null,0,16)) {colors.add(color);assertTrue(color>>>24==0 || color>>>24==255);}
            assertTrue(colors.size()<=16);
        }
    }
    @Test void cacheUsesContentAndConverterVersionAndUnreadableIconsFallBack() throws Exception {
        Path source=directory.resolve("icon.png"),pack=directory.resolve("pack");
        Files.copy(getClass().getResourceAsStream("/icons/compass.png"),source);
        var app=new AppDefinition("fixture","Fixture",List.of("fixture.exe"),"minecraft:book",false,"command",null,source.toString());
        var converter=new PixelIconConverter();
        var first_=IconPack.generate(pack,List.of(app),converter); assertEquals(Set.of("fixture"),first_.generated()); assertTrue(first_.changed());
        Path texture=pack.resolve("assets/aresos/textures/item/apps/fixture.png");
        byte[] first=Files.readAllBytes(texture); var time=Files.getLastModifiedTime(texture);
        assertFalse(IconPack.generate(pack,List.of(app),converter).changed(),"An unchanged icon must not ask for a reload"); assertEquals(time,Files.getLastModifiedTime(texture));
        Files.copy(getClass().getResourceAsStream("/icons/sunset.png"),source,StandardCopyOption.REPLACE_EXISTING);
        assertTrue(IconPack.generate(pack,List.of(app),converter).changed()); assertFalse(Arrays.equals(first,Files.readAllBytes(texture)));
        var replacement=new IconConverter() {
            public String version(){return "fixture-style-2";}
            public java.awt.image.BufferedImage convert(java.awt.image.BufferedImage input){return new java.awt.image.BufferedImage(16,16,2);}
        };
        IconPack.generate(pack,List.of(app),replacement); assertEquals(0,ImageIO.read(texture.toFile()).getRGB(8,8));
        Files.delete(source); var gone=IconPack.generate(pack,List.of(app),converter);
        assertTrue(gone.generated().isEmpty()); assertTrue(gone.changed(),"A picture that went away must ask for a reload"); assertFalse(Files.exists(texture));
        assertFalse(IconPack.generate(pack,List.of(app),converter).changed(),"Nothing left to change");
    }
}
