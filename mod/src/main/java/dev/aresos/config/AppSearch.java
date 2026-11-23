package dev.aresos.config;

import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/**
 * The search box of the Apps screen (docs/design/HUB.md 2.4): it looks in a program's name and in what the system
 * said its generic name and keywords are, so "mail" or "pdf" finds the right program.
 */
public final class AppSearch {
    /** By name as he reads it; the ID settles two programs with the same name. */
    public static final Comparator<AppDefinition> BY_NAME = Comparator
            .comparing((AppDefinition app) -> app.name().toLowerCase(Locale.ROOT)).thenComparing(AppDefinition::id);

    private AppSearch() { }

    /** The programs the query finds, by name. An empty query finds every program. */
    public static List<AppDefinition> find(List<AppDefinition> apps, String query) {
        return apps.stream().filter(app -> matches(app, query)).sorted(BY_NAME).toList();
    }

    /**
     * The programs the query finds, the best hit first. This is the order of the search over the world (package 53d),
     * and the rule the Apps screen can share later: My apps before other programs; then a match at the start of the
     * name or of a word before a match inside a word; then by name. A blank query finds every program, in this order.
     *
     * <p>"At the start" is read on what he calls the program: its name and its short names. A program found only
     * inside a word, or only through its generic name or a keyword, comes after one whose name begins with what he
     * typed, so "pdf" puts "PDF Arranger" before a viewer that merely lists pdf as a keyword.
     */
    public static List<AppDefinition> ranked(List<AppDefinition> apps, String query) {
        var words = words(query);
        return apps.stream().filter(app -> matches(app, query))
                .sorted(Comparator.comparing((AppDefinition app) -> !app.mine())
                        .thenComparing(app -> !startsWords(app, words)).thenComparing(BY_NAME)).toList();
    }

    /** The program Enter opens in the search over the world: the first of {@link #ranked}. Null for a blank query or no hit. */
    public static AppDefinition best(List<AppDefinition> apps, String query) {
        if (query.isBlank()) return null;
        var found = ranked(apps, query);
        return found.isEmpty() ? null : found.getFirst();
    }

    /** Whether every word of the query begins the name, a word of the name, or a short name. */
    private static boolean startsWords(AppDefinition app, List<String> words) {
        var called = new StringBuilder(app.name());
        for (String name : app.names()) called.append('\n').append(name);
        String text = called.toString().toLowerCase(Locale.ROOT);
        for (String word : words) if (!startsWord(text, word)) return false;
        return true;
    }

    private static boolean startsWord(String text, String word) {
        for (int at = text.indexOf(word); at >= 0; at = text.indexOf(word, at + 1))
            if (at == 0 || !Character.isLetterOrDigit(text.charAt(at - 1))) return true;
        return false;
    }

    private static List<String> words(String query) {
        return java.util.Arrays.stream(query.toLowerCase(Locale.ROOT).split("\\s+")).filter(word -> !word.isEmpty()).toList();
    }

    /** Every word of the query must be part of the name, the generic name or a keyword; upper and lower case are one. */
    public static boolean matches(AppDefinition app, String query) {
        String text = text(app);
        for (String word : words(query)) if (!text.contains(word)) return false;
        return true;
    }

    private static String text(AppDefinition app) {
        var text = new StringBuilder(app.name());
        for (String name : app.names()) text.append('\n').append(name);
        var system = app.system();
        if (system != null) {
            if (system.genericName() != null) text.append('\n').append(system.genericName());
            // One line each, so a word never matches across two fields.
            if (system.keywords() != null) for (String keyword : system.keywords()) text.append('\n').append(keyword);
        }
        return text.toString().toLowerCase(Locale.ROOT);
    }
}
