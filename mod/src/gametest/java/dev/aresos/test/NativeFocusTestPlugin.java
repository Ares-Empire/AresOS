package dev.aresos.test;

import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.List;
import java.util.Set;

/** Allows real GLFW focus events through Fabric's input suppression only during the native pointer test. */
public final class NativeFocusTestPlugin implements IMixinConfigPlugin {
    private static final String CALLBACK_INFO = "org/spongepowered/asm/mixin/injection/callback/CallbackInfo";
    private static boolean nativeFocus;

    static void nativeFocus(boolean enabled) {
        nativeFocus = enabled;
    }

    public static boolean cancelFabricFocus(CallbackInfo info) {
        return !nativeFocus && info.isCancelled();
    }

    @Override
    public void postApply(String targetClass, ClassNode node, String mixinClass, IMixinInfo info) {
        if (!Boolean.getBoolean("aresos.pointerSession")
                || !mixinClass.equals("dev.aresos.test.mixin.WindowTestAccess")) return;

        var focus = node.methods.stream().filter(method -> method.name.equals("onFocus") && method.desc.equals("(JZ)V"))
                .findFirst().orElseThrow();
        // Fabric cancels onFocus at HEAD, which can also stop AresOS's HEAD injection. Lift only that cancellation.
        // Identifying its handler keeps the mod's cancellation and Fabric's other window callbacks in effect.
        MethodInsnNode fabricHandler = null;
        for (var instruction : focus.instructions) {
            if (instruction instanceof MethodInsnNode call && call.owner.equals(node.name)
                    && call.name.contains("$fabric-client-gametest-api-v1$") && call.name.endsWith("$cancelEvents")) {
                fabricHandler = call;
                break;
            }
        }
        if (fabricHandler == null) throw new IllegalStateException("Fabric's focus handler changed");
        for (var next = fabricHandler.getNext(); next != null; next = next.getNext()) {
            if (next instanceof MethodInsnNode call) {
                if (!call.owner.equals(CALLBACK_INFO) || !call.name.equals("isCancelled")) break;
                focus.instructions.set(call, new MethodInsnNode(Opcodes.INVOKESTATIC,
                        "dev/aresos/test/NativeFocusTestPlugin", "cancelFabricFocus", "(L" + CALLBACK_INFO + ";)Z", false));
                return;
            }
        }
        throw new IllegalStateException("Fabric's focus cancellation changed");
    }

    @Override public void onLoad(String mixinPackage) { }
    @Override public String getRefMapperConfig() { return null; }
    @Override public boolean shouldApplyMixin(String targetClass, String mixinClass) { return true; }
    @Override public void acceptTargets(Set<String> myTargets, Set<String> otherTargets) { }
    @Override public List<String> getMixins() { return null; }
    @Override public void preApply(String targetClass, ClassNode node, String mixinClass, IMixinInfo info) { }
}
