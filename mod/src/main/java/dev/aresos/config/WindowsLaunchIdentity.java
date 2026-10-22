package dev.aresos.config;

import java.util.*;

/** Discovery metadata; the owner's command remains the only launch instruction. */
public record WindowsLaunchIdentity(String target, List<String> arguments, String workingDirectory, String aumid,
                                    String rawArguments) {
    /** Old metadata and configured argv do not establish a raw Windows command line. */
    public WindowsLaunchIdentity(String target, List<String> arguments, String workingDirectory, String aumid) {
        this(target, arguments, workingDirectory, aumid, null);
    }
    public WindowsLaunchIdentity {
        Objects.requireNonNull(target); Objects.requireNonNull(arguments);
        Objects.requireNonNull(workingDirectory); Objects.requireNonNull(aumid);
        if (target.isBlank() && aumid.isBlank()) throw new IllegalArgumentException("Missing Windows launch target");
        target = path(target); workingDirectory = path(workingDirectory);
        aumid = aumid.toLowerCase(Locale.ROOT); arguments = List.copyOf(arguments);
    }
    public static String path(String value) { return value.replace('\\', '/').toLowerCase(Locale.ROOT); }
}
