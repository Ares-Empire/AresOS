package dev.aresos.names;

import com.google.common.collect.MapMaker;
import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.tree.CommandNode;
import dev.aresos.mixin.CommandNodeAccess;

import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.Iterator;
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
    /** One node as installed. It names its children but not the node itself: see {@link #INSTALLED}. */
    private record Shape(Command<?> command, Predicate<?> requirement, List<CommandNode<?>> children) {
        static Shape of(CommandNode<?> node) {
            return new Shape(node.getCommand(), node.getRequirement(), List.copyOf(node.getChildren()));
        }
        boolean fits(CommandNode<?> node) {
            if (node.getCommand() != command || node.getRequirement() != requirement) return false;
            var now = node.getChildren();
            if (now.size() != children.size()) return false;
            var iterator = now.iterator();
            for (var child : children) if (iterator.next() != child) return false;
            return true;
        }
    }
    /** The parent we installed under, and the subtree in pre-order: the node first, then each child's subtree. */
    private record Installed(WeakReference<CommandNode<?>> parent, List<Shape> subtree) { }

    // Weak keys compare by identity, which is what we need: CommandNode.equals looks at its changeable content.
    // A record holds neither its node nor its parent strongly (children never point back), so a tree nobody uses
    // any more takes its records with it, also one the server never adopted (a cancelled Create World screen builds
    // one). The server's own trees go at once with {@link #forget}. Concurrent: the hook also runs on the client's tree.
    private static final Map<CommandNode<?>, Installed> INSTALLED = new MapMaker().weakKeys().makeMap();

    private OwnedNodes() { }

    /** Registers the command only if the tree has nothing of that name, so it never merges into another; else null. */
    public static <S> CommandNode<S> install(CommandDispatcher<S> dispatcher, LiteralArgumentBuilder<S> command) {
        var root = dispatcher.getRoot();
        if (root.getChild(command.getLiteral()) != null) return null;
        CommandNode<S> node = dispatcher.register(command);
        var subtree = new ArrayList<Shape>();
        snapshot(node, subtree);
        INSTALLED.put(node, new Installed(new WeakReference<>(root), List.copyOf(subtree)));
        return node;
    }

    private static void snapshot(CommandNode<?> node, List<Shape> into) {
        var shape = Shape.of(node);
        into.add(shape);
        for (var child : shape.children()) snapshot(child, into);
    }

    /** Walks the subtree in the order {@link #snapshot} recorded it. */
    private static boolean unchanged(CommandNode<?> node, Iterator<Shape> shapes) {
        var shape = shapes.next();
        if (!shape.fits(node)) return false;
        for (var child : shape.children()) if (!unchanged(child, shapes)) return false;
        return true;
    }

    /** True while the node is on its tree exactly as installed. A node that changed is forgotten: foreign from now on. */
    public static boolean ours(CommandNode<?> node) {
        var installed = node == null ? null : INSTALLED.get(node);
        if (installed == null) return false;
        var parent = installed.parent().get();
        if (parent != null && parent.getChild(node.getName()) == node && unchanged(node, installed.subtree().iterator()))
            return true;
        INSTALLED.remove(node);
        return false;
    }

    /** Drops every record on this dispatcher's tree, once the server no longer uses it (/reload, the world closed). */
    public static void forget(CommandDispatcher<?> dispatcher) {
        var root = dispatcher.getRoot();
        INSTALLED.values().removeIf(installed -> installed.parent().get() == root);
    }

    /** For tests: whether a record is kept for this node. */
    public static boolean recorded(CommandNode<?> node) {
        return INSTALLED.containsKey(node);
    }

    /** Takes one of our nodes off its tree. Brigadier has no removal; a node that is no longer ours stays. */
    @SuppressWarnings("unchecked")
    public static boolean remove(CommandNode<?> node) {
        if (!ours(node)) return false;
        var parent = INSTALLED.remove(node).parent().get();
        if (parent == null) return false;
        var access = (CommandNodeAccess<Object>)(Object)parent;
        access.aresos$children().remove(node.getName());
        access.aresos$literals().remove(node.getName());
        access.aresos$arguments().remove(node.getName());
        return true;
    }

    /**
     * Called (mixin/CommandNodeMergeMixin) before Brigadier adds {@code incoming} under {@code parent}. If it would
     * merge into a node of ours where we installed it, ours goes first and the newcomer is added whole. Anything else
     * is left to Brigadier: a mod that hung our node under a parent of its own merges into it there, and our node
     * stays where we put it (the merge changes it, so it is foreign from then on).
     */
    public static void beforeAdd(CommandNode<?> parent, CommandNode<?> incoming) {
        var existing = parent.getChild(incoming.getName());
        if (existing == null || existing == incoming) return;
        var installed = INSTALLED.get(existing);
        if (installed != null && installed.parent().get() == parent) remove(existing);
    }
}
