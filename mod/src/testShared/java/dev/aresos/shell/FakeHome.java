package dev.aresos.shell;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;

import java.util.LinkedHashMap;

final class FakeHome {
    private final String revision;
    private final JsonObject palette;
    private final LinkedHashMap<String, JsonObject> apps = new LinkedHashMap<>();
    private int nextPart;

    private FakeHome(String revision, JsonObject palette) {
        this.revision = revision;
        this.palette = palette;
    }

    static FakeHome receive(FakeHome pending, JsonObject message, int bytes) {
        require(bytes < 64 * 1024, "home message is too large");
        String revision = text(message, "revision");
        int part = integer(message, "part");
        require(line(revision, 128) && part >= 0 && part < 16
                && message.get("last") instanceof JsonPrimitive last && last.isBoolean()
                && (part < 15 || last.getAsBoolean()), "invalid home revision, part or last flag");
        if (pending == null) {
            require(part == 0, "a home publish must start with part 0");
            require(message.get("palette") instanceof JsonObject, "invalid home palette");
            var palette = message.getAsJsonObject("palette");
            require(palette.size() <= 64, "invalid home palette");
            for (var entry : palette.entrySet())
                require(entry.getKey().matches("[A-Za-z0-9]") && matches(text(palette, entry.getKey()), "#[0-9A-Fa-f]{6}"),
                        "invalid home palette");
            pending = new FakeHome(revision, palette);
        } else {
            require(revision.equals(pending.revision) && part == pending.nextPart && !message.has("palette"),
                    "home parts must be consecutive within one revision, with palette in part 0");
        }
        require(message.get("apps") instanceof JsonArray, "home apps must be an array");
        var rows = message.getAsJsonArray("apps");
        require(pending.apps.size() + rows.size() <= 200, "a home publish can contain at most 200 apps");
        var palette = pending.palette;
        for (var value : rows) {
            require(value instanceof JsonObject, "home apps must be objects");
            var row = value.getAsJsonObject();
            String id = text(row, "id"), cells = text(row, "cells");
            require(matches(id, "[a-z0-9_-]{1,64}"), "invalid home app ID");
            require(line(text(row, "short"), 64) && matches(text(row, "group"), "[a-z0-9_]{1,64}"),
                    "invalid home app short name or group");
            require(cells != null && cells.length() == 144 && cells.chars()
                    .allMatch(c -> c == '.' || palette.has(String.valueOf((char) c))), "invalid home app cells");
            require(!row.has("place") || matches(text(row, "place"), "[A-Za-z0-9_-]{1,32}"), "invalid home app place");
            int slot = integer(row, "slot");
            require(!row.has("slot") || slot >= 0 && slot <= 8, "invalid home app slot");
            require(pending.apps.putIfAbsent(id, row) == null, "duplicate home app ID");
        }
        pending.nextPart++;
        return pending;
    }

    FakeHelper.PublishedHome published() { return new FakeHelper.PublishedHome(revision, palette, apps); }

    private static String text(JsonObject object, String key) {
        return object.get(key) instanceof JsonPrimitive value && value.isString() ? value.getAsString() : null;
    }

    private static int integer(JsonObject object, String key) {
        if (!(object.get(key) instanceof JsonPrimitive value) || !value.isNumber()) return -1;
        try { return Integer.parseInt(value.getAsString()); }
        catch (NumberFormatException invalid) { return -1; }
    }

    private static boolean matches(String value, String pattern) { return value != null && value.matches(pattern); }

    private static boolean line(String value, int limit) {
        return value != null && !value.isEmpty() && value.codePointCount(0, value.length()) <= limit
                && value.codePoints().noneMatch(Character::isISOControl);
    }

    private static void require(boolean valid, String reason) {
        if (!valid) throw new IllegalArgumentException(reason);
    }
}
