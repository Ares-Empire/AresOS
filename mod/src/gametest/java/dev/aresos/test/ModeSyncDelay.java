package dev.aresos.test;

import java.util.UUID;

/** Holds the complete inventory sync, without blocking either game thread. */
public final class ModeSyncDelay {
    public static volatile UUID player;
    public static volatile boolean dropAcknowledgements;
    private ModeSyncDelay() { }
}
