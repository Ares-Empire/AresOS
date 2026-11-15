import java.io.DataOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.zip.GZIPOutputStream;

/**
 * Writes level-modified-utf8.dat: a gzip-compressed NBT level whose strings Java encodes with
 * DataOutput.writeUTF, exactly as Minecraft's StringTag and CompoundTag do (modified UTF-8: NUL as C0 80, a
 * character outside the BMP as two three-byte surrogates). Run: java JavaStrings.java level-modified-utf8.dat
 */
public class JavaStrings {
    public static void main(String[] args) throws IOException {
        try (DataOutputStream out = new DataOutputStream(new GZIPOutputStream(new FileOutputStream(args[0])))) {
            out.writeByte(10);
            out.writeUTF("");
            out.writeByte(10);
            out.writeUTF("Data");
            out.writeByte(8);
            out.writeUTF("LevelName");
            out.writeUTF("AresHub 🔥");
            out.writeByte(8);
            out.writeUTF("Note");
            out.writeUTF("a\u0000b");
            out.writeByte(3);
            out.writeUTF("version");
            out.writeInt(19133);
            out.writeByte(0);
            out.writeByte(0);
        }
    }
}
