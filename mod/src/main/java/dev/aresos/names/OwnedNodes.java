package dev.aresos.names;

import com.google.common.collect.MapMaker;
import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.tree.CommandNode;
import dev.aresos.mixin.CommandNodeAccess;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * The command nodes AresOS put on a tree, and whether each is still exactly what it put there.
 *
 * Brigadier merges a later registration of the same name into the node already there: that node and its
 * requirement stay, the newcomer's command and children move in. So the node's identity says nothing about whose it
 * is. A node is ours only while it has our command, our requirement and no child we did not add; once it changed it
 * is foreign for good, and we leave it alone. To keep that from happening at all, {@link #beforeAdd} lets our node
 * step aside before a merge, so the later command lands whole, with its own requirement: later commands win.
 */
public final class OwnedNodes {
    private record Shape(CommandNode<?> node, Command<?> command, Predicate<?> requirement, List<CommandNode<?>> children) {
        static Shape of(CommandNode<?> node) {
            return new Shape(node, node.getCommand(), node.getRequirement(), List.copyOf(node.getChildren()));
        }
        boolean unchanged() {
            if (node.getCommand() != command || node.getRequirement() != requirement) return false;
            var now = node.getChildren();
            if (now.size() != children.size()) return false;
            var iterator = now.iterator();
            for (var child : children) if (iterator.next() != child) return false;
            return true;
        }
    }
    private record Installed(CommandNode<?> parent, List<Shape> subtree) { }

    // Weak keys compare by identity, which is what we need: CommandNode.equals looks at its changeable content.
    // Concurrent, because the hook also runs for the client's own command tree on the render thread.
    private static final Map<CommandNode<?>, Installed> INSTALLED = new MapMaker().weakKeys().makeMap();

    private OwnedNodes() { }

    /** Registers the command only if the tree has nothing of that name, so it never merges into another; else null. */
    public static <S> CommandNode<S> install(CommandDispatcher<S> dispatcher, LiteralArgumentBuilder<S> command) {
        var root = dispatcher.getRoot();
        if (root.getChild(command.getLiteral()) != null) return null;
        CommandNode<S> node = dispatcher.register(command);
        var subtree = new ArrayList<Shape>();
        snapshot(node, subtree);
        INSTALLED.put(node, new Installed(root, List.copyOf(subtree)));
        return node;
    }

    private static void snapshot(CommandNode<?> node, List<Shape> into) {
        into.add(Shape.of(node));
        for (var child : node.getChildren()) snapshot(child, into);
    }

    /** True while the node is on its tree exactly as installed. A node that changed is forgotten: foreign from now on. */
    public static boolean ours(CommandNode<?> node) {
        var installed = node == null ? null : INSTALLED.get(node);
        if (installed == null) return false;
        if (installed.parent().getChild(node.getName()) == node && installed.subtree().stream().allMatch(Shape::unchanged))
            return true;
        INSTALLED.remove(node);
        return false;
    }

    /** Takes one of our nodes off its tree. Brigadier has no removal; a node that is no longer ours stays. */
    @SuppressWarnings("unchecked")
    public static boolean remove(CommandNode<?> node) {
        if (!ours(node)) return false;
        var access = (CommandNodeAccess<Object>)(Object)INSTALLED.remove(node).parent();
        access.aresos$children().remove(node.getName());
        access.aresos$literals().remove(node.getName());
        access.aresos$arguments().remove(node.getName());
        return true;
    }

    /**
     * Called (mixin/CommandNodeMergeMixin) before Brigadier adds {@code incoming} under {@code parent}. If it would
     * merge into a node of ours, ours goes first and the newcomer is added whole. Anything else is left to Brigadier.
     */
    public static void beforeAdd(CommandNode<?> parent, CommandNode<?> incoming) {
        var existing = parent.getChild(incoming.getName());
        if (existing != null && existing != incoming && INSTALLED.containsKey(existing)) remove(existing);
    }
}
