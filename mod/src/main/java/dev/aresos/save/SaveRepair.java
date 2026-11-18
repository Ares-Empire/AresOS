package dev.aresos.save;

/** Server-thread access to retained data whose dirty bits vanilla clears before a write succeeds. */
public interface SaveRepair {
    void aresos$rewrite();
    default void aresos$flush() { }
}
