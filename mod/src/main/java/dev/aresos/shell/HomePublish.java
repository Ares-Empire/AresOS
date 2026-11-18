package dev.aresos.shell;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import dev.aresos.zone.GatePalette;
import dev.aresos.zone.LogoPixels;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

final class HomePublish {
    private static final System.Logger LOG = System.getLogger("aresos");
    private static final Pattern ID = Pattern.compile("[a-z0-9_-]{1,64}");
    private static final Pattern GROUP = Pattern.compile("[a-z0-9_]{1,64}");
    private static final Pattern PLACE = Pattern.compile("[A-Za-z0-9_-]{1,32}");
    private static final String KEYS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    private static final int MAX_APPS = 200;
    private static final int MAX_PARTS = 16;
    private static final Comparator<HomeState.App> PRIORITY = Comparator
            .comparingInt((HomeState.App app) -> hasPlace(app) ? 0 : hasSlot(app) ? 1 : 2)
            .thenComparing(HomeState.App::name, String.CASE_INSENSITIVE_ORDER)
            .thenComparing(HomeState.App::id);
    private static final Map<String, Integer> GATE_COLOURS = GatePalette.BLOCKS.stream()
            .collect(Collectors.toUnmodifiableMap(LogoPixels.Color::block, LogoPixels.Color::rgb));

    private final Map<String, Integer> colours;
    private final Set<String> warnedIds = new HashSet<>();
    private boolean warnedApps, warnedColours;

    HomePublish() { this(GATE_COLOURS); }

    HomePublish(Map<String, Integer> colours) { this.colours = Map.copyOf(colours); }

    /** Writer only. Reserve the real envelope and newline before adding each UTF-8 row. */
    List<JsonObject> messages(HomeState home, String revision, Supplier<JsonObject> request, int byteLimit) {
        var apps = select(home);
        var used = new HashMap<String, Integer>();
        for (var app : apps) for (var block : app.front())
            if (colours.containsKey(block)) used.merge(block, 1, Integer::sum);
        var kept = used.keySet().stream().sorted(Comparator.<String>comparingInt(used::get).reversed()
                .thenComparing(Comparator.naturalOrder())).limit(KEYS.length()).toList();
        var keys = new HashMap<String, Character>();
        var palette = new JsonObject();
        for (int i = 0; i < kept.size(); i++) {
            String block = kept.get(i);
            char key = KEYS.charAt(i);
            keys.put(block, key);
            palette.addProperty(String.valueOf(key), "#" + HexFormat.of().toHexDigits(colours.get(block), 6));
        }
        if (used.size() > kept.size()) {
            if (!warnedColours) {
                warnedColours = true;
                LOG.log(System.Logger.Level.WARNING, "AresOS home has more than 62 block colours; using the nearest retained colours");
            }
            for (String block : used.keySet()) if (!keys.containsKey(block)) {
                int rgb = colours.get(block);
                var nearest = kept.stream().min(Comparator.comparingInt(other -> distance(rgb, colours.get(other)))).orElseThrow();
                keys.put(block, keys.get(nearest));
            }
        }

        var parts = new ArrayList<JsonObject>();
        var rows = new JsonArray();
        var part = part(request, revision, 0, rows);
        part.add("palette", palette);
        int bytes = ShellClient.wireBytes(part).length;
        for (var app : apps) {
            var row = row(app, keys);
            int rowBytes = ShellClient.wireBytes(row).length - 1;
            if (!rows.isEmpty() && bytes + 1 + rowBytes >= byteLimit) {
                parts.add(part);
                rows = new JsonArray();
                part = part(request, revision, parts.size(), rows);
                bytes = ShellClient.wireBytes(part).length;
            }
            bytes += rowBytes + (rows.isEmpty() ? 0 : 1);
            if (parts.size() >= MAX_PARTS || bytes >= byteLimit)
                throw new IllegalArgumentException("AresOS home exceeds its message budget");
            rows.add(row);
        }
        part.addProperty("last", true);
        parts.add(part);
        return parts;
    }

    private List<HomeState.App> select(HomeState home) {
        var seen = new HashSet<String>();
        var apps = home.apps().stream().filter(this::valid).filter(app -> seen.add(app.id())).sorted(PRIORITY).toList();
        if (apps.size() > MAX_APPS && !warnedApps) {
            warnedApps = true;
            LOG.log(System.Logger.Level.WARNING, "AresOS home has more than 200 apps; publishing the first 200");
        }
        return apps.stream().limit(MAX_APPS).sorted(Comparator.comparing(HomeState.App::id)).toList();
    }

    private boolean valid(HomeState.App app) {
        if (!ID.matcher(app.id()).matches()) {
            if (warnedIds.add(app.id()))
                LOG.log(System.Logger.Level.WARNING, "AresOS home skipped an app whose ID does not fit the protocol: " + app.id());
            return false;
        }
        String name = app.shortName();
        return !name.isEmpty() && name.codePointCount(0, name.length()) <= 64
                && name.codePoints().noneMatch(Character::isISOControl)
                && GROUP.matcher(app.group()).matches() && app.front().size() == 144;
    }

    private static boolean hasPlace(HomeState.App app) {
        return app.place() != null && PLACE.matcher(app.place()).matches();
    }

    private static boolean hasSlot(HomeState.App app) {
        return app.slot() != null && app.slot() >= 0 && app.slot() < 9;
    }

    private static JsonObject part(Supplier<JsonObject> request, String revision, int number, JsonArray rows) {
        var message = request.get();
        message.addProperty("revision", revision);
        message.addProperty("part", number);
        // false takes one extra byte. Reserve it for every part.
        message.addProperty("last", false);
        message.add("apps", rows);
        return message;
    }

    private static JsonObject row(HomeState.App app, Map<String, Character> keys) {
        var row = new JsonObject();
        row.addProperty("id", app.id());
        row.addProperty("short", app.shortName());
        row.addProperty("group", app.group());
        if (hasPlace(app)) row.addProperty("place", app.place());
        if (hasSlot(app)) row.addProperty("slot", app.slot());
        var cells = new StringBuilder(144);
        for (var block : app.front()) cells.append(keys.getOrDefault(block, '.').charValue());
        row.addProperty("cells", cells.toString());
        return row;
    }

    private static int distance(int first, int second) {
        int red = (first >> 16 & 255) - (second >> 16 & 255);
        int green = (first >> 8 & 255) - (second >> 8 & 255);
        int blue = (first & 255) - (second & 255);
        return red * red + green * green + blue * blue;
    }
}
