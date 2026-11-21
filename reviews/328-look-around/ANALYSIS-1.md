# 328a: a capture that can't race

**Recommendation: do A now and B later.** A is one more builder step, because the capture half already works in the rig and only the release needs a redesign. B is worth a time-boxed spike after the owner has picked a look mode, not as the fix for this bug.

**Nothing here was compiled or run.** I had read-only tools, so every diff below is untested.

## 1. What this rests on

- **Read:** the brief, `reviews/328-look-around/PROGRESS.md`, `REVIEW-1.md`, `RECHECK-1.md`, both traces, and the rig's `GlfwProbe.java`, `trial.py`, `state.sh`, `vinput.py`, `rig.sh`. In `mod/`: `WorldCapture`, the mixins, `ShellFocusClient`, `HomePointer`, `HomeScreen`, `PointerRules`, the native test and its test mixin. In `os/`: `rc.xml`, `aresos-desktop-java`, the first 1,150 lines of `aresos-desktop`, and the window-tracking parts of `aresos-shell`.
- **GLFW:** I could not open GLFW 3.5.1. I reason from memory of 3.4 and master's `src/x11_window.c` and `src/input.c`. That memory agrees with RECHECK-1 and with what `GlfwProbe.java` showed. The builder confirms five facts first (section 2.6).
- **From memory, not checked:** Xlib's `XPutBackEvent`, Xwayland's warp emulation, wlroots' X window manager.
- **Minecraft 26.2:** I know only what the mod's mixins show: `Window.onFocus(long, boolean)`, a `focused` field, `RenderSystem.pollEvents`, and `createGlfwWindow` taking a `GpuBackend`.

## 2. A: the X11 path, made race-free

### 2.1 Why two reviews found the same kind of bug

GLFW on X11 undoes a capture in two places, and they behave differently.

| Way | Asks the X server | If the focus is elsewhere at that instant |
| --- | --- | --- |
| `glfwSetInputMode(NORMAL)` | "Is my window the focus?" (`XGetInputFocus`) | Records NORMAL and skips the X work. The grab, raw motion and the disabled-cursor window stay. Later calls with NORMAL return early. |
| Its handling of a FocusOut in DISABLED mode | Nothing | Nothing is left. It ungrabs, turns raw motion off and clears the disabled-cursor window. |

Its handling of a FocusIn in DISABLED mode captures again, also without asking.

The current code asks the server first (`Xlib.focused`) and then picks a way. The focus can move between the mod's question and GLFW's own, which is RECHECK-1's finding. Any design that asks first has this hole. The current `XSendEvent` also puts the mod's FocusOut behind real events already on the wire, so the callback cannot tell which FocusOut is its own.

### 2.2 The design: one owner, one way out

**Who owns what:**
- **GLFW** owns the X cursor state: grab, raw motion, disabled-cursor window, warps. The mod never asks about it and never mirrors it.
- **The mod** owns two facts: `hiddenInX` (its XFixes hide is in force) and `letGo` (a release is due).
- **Minecraft** owns `mouseGrabbed`.
- **The cursor mode** changes in two places only: DISABLED in Minecraft's capture call (wrapped by `grab`), and NORMAL inside the mod's own FocusOut callback.

**Every release takes the FocusOut way**, whatever asked for it and wherever the focus is:

1. **A release is asked for.** Esc, an app taking focus, `HomeScreen.frame`, helper loss, leaving the world and the free-pointer rule all end in `MouseHandler.releaseMouse`, so in `WorldCapture.release`. It only sets `letGo = window`. Nothing native runs, inside a callback or outside.
2. **At the head of the next `RenderSystem.pollEvents`** the mod puts a FocusOut at the head of Xlib's queue with `XPutBackEvent`. Nothing goes to the server and nothing is waited for. It is the next event GLFW reads, ahead of every real event.
3. **GLFW handles it** and lets go completely.
4. **GLFW calls the focus callback.** Inside that same event the mod sets NORMAL, shows the cursor again, and cancels `Window.onFocus`, so Minecraft never sees the event.
5. **If Minecraft's own record says the window has the focus,** the mod puts a FocusIn at the head the same way. GLFW's FocusOut handling also took the focus from its input context. If my memory of Xlib is right, that breaks dead keys until the next FocusIn. Minecraft does not see this event either.

The capture half does not change: XFixes hide first, then Minecraft's call, under `PointerRules.mayCapture`.

### 2.3 Why no ordering can break it

**(2) The disabled-cursor window set while the mode is normal.**
- The mode turns NORMAL at one point: right after GLFW's own letting go, in the same event dispatch. No other event can come between.
- At that point the disabled-cursor window is already cleared, so GLFW's focus test in `glfwSetInputMode` has nothing left to skip. Both branches end the same.
- In NORMAL mode nothing sets it again. A FocusIn captures only in DISABLED mode.
- Real events before the mod's FocusOut can only toggle GLFW between captured and let go. The mod's FocusOut ends in "let go" from either.
- `beforePollEvents` first puts the mode back to DISABLED if something changed it behind the mod. So the sequence ends the same from any state GLFW is in.

**(1) The cursor hidden.**
- Three things hide it: the XFixes hide, GLFW's hidden image, and Xwayland's lock.
- The hide is paired by `hiddenInX`: one hide in `grab`, one show in `finish`.
- GLFW's image is hidden only in DISABLED mode.
- `finish` runs at the next poll after any request, at most one frame later.
- Helper loss sets `letGo` even if Minecraft thought the mouse was free.
- Quitting closes the X connection, which drops hides and grabs.

**(3) A game that refuses the next click.**
- Minecraft's focus record now holds only real events, in order. The mod's two events are cancelled before Minecraft sees them. There is no focus query to go stale.
- `allowed()` refuses only while `letGo` is set. That ends inside the callback, before any later event of the same poll, so a click read in that poll after the mod's FocusOut captures normally.

### 2.4 What I rejected

- **`XGrabServer` around a focus query and the mode change.** It makes the query atomic, but a game frozen inside the grab freezes every X client. The sleeping-world study freezes the game on purpose.
- **Setting the X focus to the game first.** It steals focus from other X11 apps, and labwc's X window manager may fight it.
- **Keeping `XSendEvent`.** The event lands behind real events and cannot be identified in the callback.
- **The mod doing its own capture** without GLFW's disabled mode. That means rebuilding GLFW's raw-motion path.
- **A patched GLFW in the image.** It is the real fix: `_glfwSetCursorModeX11` should let go without the focus test. But it is a pin change in `os/`, and worth an upstream report rather than a local fork.

### 2.5 Code changes

Apply with `git apply --recount`, or by content if a count is off. No change to `PointerRules.java`, `RenderSystemCaptureMixin.java`, `MouseAppInputMixin.java`, `ShellFocusClient.java`, `HomePointer.java` or `HomeScreen.java`.

The test mixin must change in the same commit: its target `Xlib.focusOut` is gone, and `defaultRequire` is 1.

**`mod/src/client/java/dev/aresos/client/WorldCapture.java`**

```diff
--- a/mod/src/client/java/dev/aresos/client/WorldCapture.java
+++ b/mod/src/client/java/dev/aresos/client/WorldCapture.java
@@ -31,13 +31,15 @@
  * only where the lock works: the compositor has given it the focus and the pointer is over its window
  * ({@link PointerRules#mayCapture}, the brief's safe fallback).
  *
- * <p><b>Letting go after an app took the focus.</b> GLFW 3.5 changes its X state for a cursor mode only while its window
- * has the X focus. When an app takes the focus with a click, X first takes the focus away from the game and then hands it
- * a pointer focus, on which GLFW captures once more; the mod's release comes after that, without the X focus, and GLFW
- * skips it. GLFW then keeps its X grab and warps the pointer to the window's centre after every move over the world, and
- * once the world is clicked again labwc follows one of those warps before the capture starts (rig/GlfwProbe.java shows
- * it with GLFW alone). So such a release first gives GLFW a focus-out event of its own: GLFW's handling of it lets go
- * completely, as it does when the focus leaves for good.
+ * <p><b>Letting go.</b> GLFW 3.5 on X11 undoes a capture in two places. {@code glfwSetInputMode} does it only if the X
+ * server says, at that instant, that the window has the focus; otherwise it records the normal mode but keeps its grab,
+ * its raw motion and its disabled-cursor window, and then warps the pointer to the window's centre after every poll. Its
+ * handling of a FocusOut does it always. No question to the server can make the first way safe: the focus can move
+ * between the question and GLFW's own. So every release takes the second way, whatever asked for it and wherever the
+ * focus is: at the next event poll the mod puts a FocusOut of its own at the head of Xlib's queue, GLFW lets go
+ * completely, and inside that same event the mode turns normal. A FocusIn follows the same way where the window really
+ * has the focus, for GLFW's input context. Minecraft sees neither event (rig/GlfwProbe.java shows the steps with GLFW
+ * alone).
  */
 public final class WorldCapture {
     /** {@code InputConstants.grabOrReleaseMouse}: a cursor position first, then GLFW's cursor mode. */
@@ -53,8 +55,10 @@
     private static boolean hiddenInX;
     // Client thread only: where the pointer was when the capture began, in window coordinates.
     private static double startX, startY;
-    private record Release(Window window, double x, double y) { }
-    private static Release pendingRelease;
-    private static boolean pollingEvents, sentFocusOut;
+    // Client thread only: the window whose capture is being let go; the next event poll does it. Null: nothing to do.
+    private static Window letGo;
+    // Client thread only: the mod's own X focus event that GLFW reads next (0: none). The numbers are X's event types.
+    private static final int FOCUS_IN = 9, FOCUS_OUT = 10;
+    private static int own;
     private static Boolean pointerOverWorldForTests;
     private static boolean directForTests;
@@ -66,10 +70,13 @@
         worldFocused = focused;
     }
 
-    /** The helper went away: its next connection reports the focus again. */
+    /** The helper went away: its next connection reports the focus again. What the mod hid is let go at once. */
     static void helperLost(Minecraft client) {
         worldFocused = true;
-        if (ownsCapture()) client.mouseHandler.releaseMouse();
+        if (!ownsCapture()) return;
+        client.mouseHandler.releaseMouse();
+        // Whatever Minecraft believed about the mouse, what the mod hid comes back at the next event poll.
+        if (letGo == null) letGo = client.getWindow();
     }
 
     public static boolean ownsCapture() {
@@ -79,5 +86,5 @@
     /** Whether the world may take the mouse now (Minecraft's own check for its window's focus follows). */
     public static boolean allowed(Minecraft client) {
-        if (pendingRelease != null) return false;
+        if (letGo != null) return false;
         boolean desktop = HomeScreen.active(client);
         return PointerRules.mayCapture(desktop, worldFocused, desktop && worldFocused && pointerOverWorld(client));
@@ -105,68 +112,88 @@
         (directForTests ? (CursorMode) WorldCapture::direct : minecraft).set(window, GLFW.GLFW_CURSOR_DISABLED, x, y);
     }
 
     /** Replaces Minecraft's release call in {@code MouseHandler.releaseMouse}. */
     public static void release(Window window, double x, double y, CursorMode minecraft) {
-        if (!ownsCapture()) {
+        if (letGo != null) return;
+        if (!ownsCapture() && !capturedInX(window)) {
             (directForTests ? (CursorMode) WorldCapture::direct : minecraft).set(window, GLFW.GLFW_CURSOR_NORMAL, x, y);
             return;
         }
-        var release = new Release(window, x, y);
-        if (pollingEvents || !Xlib.focused(window.handle())) {
-            // Minecraft has already cleared mouseGrabbed. The next normal poll handles the native release.
-            pendingRelease = release;
-        } else {
-            finishRelease(release);
-        }
-    }
-
-    public static void beforePollEvents() {
-        if (pendingRelease != null) {
-            long handle = pendingRelease.window().handle();
-            if (Xlib.focused(handle)) {
-                finishRelease(pendingRelease);
-                pendingRelease = null;
-            } else {
-                sentFocusOut = true;
-                Xlib.focusOut(GLFWNativeX11.glfwGetX11Display(), GLFWNativeX11.glfwGetX11Window(handle));
-            }
-        }
-        pollingEvents = true;
-    }
-
-    public static void afterPollEvents() {
-        pollingEvents = false;
-        if (!sentFocusOut) return;
-        finishRelease(pendingRelease);
-        pendingRelease = null;
-        sentFocusOut = false;
-    }
-
-    private static void finishRelease(Release release) {
-        var window = release.window();
-        long display = GLFWNativeX11.glfwGetX11Display();
-        long xwindow = GLFWNativeX11.glfwGetX11Window(window.handle());
-        direct(window, GLFW.GLFW_CURSOR_NORMAL, release.x(), release.y());
-        // Give Xwayland the original pointer position before showing the cursor drops its lock.
-        GLFW.glfwSetCursorPos(window.handle(), startX, startY);
-        JNI.invokePJI(display, 0L /* CurrentTime */, Xlib.UNGRAB_POINTER);
-        JNI.invokePJV(display, xwindow, Xlib.SHOW_CURSOR);
-        JNI.invokePI(display, Xlib.FLUSH);
-        hiddenInX = false;
-    }
-
-    /**
-     * GLFW's focus callback ({@code Window.onFocus}). GLFW calls it at the end of its focus-out handling, right after it let
-     * go of the capture. For the release's own FocusOut the cursor mode turns normal here, at once: the ungrab and the
-     * warp of that letting go can make X send a pointer focus-in that the same poll reads, and a focus-in in the
-     * disabled mode makes GLFW capture again.
-     */
-    public static boolean focusChanged(long handle, boolean focused) {
-        if (focused || !sentFocusOut || pendingRelease.window().handle() != handle) return focused;
-        GLFW.glfwSetInputMode(handle, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_NORMAL);
-        // A real FocusIn can already have run ahead of our FocusOut. Use the server's focus during this poll.
-        return Xlib.focused(handle);
-    }
+        // Minecraft has already cleared mouseGrabbed. The next event poll lets go, the same way whatever asked for it.
+        letGo = window;
+    }
+
+    /** A session's game on X11 with GLFW's cursor disabled, also when Minecraft did it before the helper was there. */
+    private static boolean capturedInX(Window window) {
+        return HomeScreen.session() && Xlib.ready()
+                && GLFW.glfwGetInputMode(window.handle(), GLFW.GLFW_CURSOR) == GLFW.GLFW_CURSOR_DISABLED;
+    }
+
+    /** Head of {@code RenderSystem.pollEvents}, outside every GLFW callback: GLFW's next event is the mod's FocusOut. */
+    public static void beforePollEvents() {
+        if (letGo == null) return;
+        long handle = letGo.handle();
+        // GLFW's FocusOut handling lets go only in the disabled mode. It is that mode here unless something changed it
+        // behind the mod; then this puts it back first, so that what follows ends the same from any state.
+        if (GLFW.glfwGetInputMode(handle, GLFW.GLFW_CURSOR) != GLFW.GLFW_CURSOR_DISABLED)
+            GLFW.glfwSetInputMode(handle, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_DISABLED);
+        own = FOCUS_OUT;
+        Xlib.putBack(handle, FOCUS_OUT);
+    }
+
+    /** Return of {@code RenderSystem.pollEvents}. GLFW has handed the event back by now; if it ever has not, say so. */
+    public static void afterPollEvents() {
+        if (own == 0) return;
+        AresOs.LOGGER.error("AresOS: GLFW did not hand back the release's own focus event ({}); forcing the normal cursor", own);
+        own = 0;
+        if (letGo == null) return;
+        GLFW.glfwSetInputMode(letGo.handle(), GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_NORMAL);
+        finish();
+    }
+
+    /**
+     * GLFW's focus callback ({@code Window.onFocus}), inside GLFW's event handling. True: the event was the mod's own
+     * and Minecraft must not see it, so its record of the focus holds only what the real events said.
+     *
+     * <p>At the mod's FocusOut, GLFW has just let go completely: its handling of a FocusOut in the disabled mode asks
+     * the server nothing. The mode turns normal here, inside the same event, so nothing can come between. A FocusIn
+     * after it finds the normal mode and captures nothing, and whichever way GLFW's own focus test falls in
+     * {@code glfwSetInputMode}, there is nothing left for it to skip.
+     */
+    public static boolean ownFocusEvent(long handle, boolean focused) {
+        if (own == FOCUS_OUT && !focused && letGo != null && letGo.handle() == handle) {
+            GLFW.glfwSetInputMode(handle, GLFW.GLFW_CURSOR, GLFW.GLFW_CURSOR_NORMAL);
+            finish();
+            // GLFW also took the focus from its input context (dead keys). Where the real events say the window has
+            // the focus, it gets a FocusIn the same way, as the very next event.
+            own = Minecraft.getInstance().getWindow().isFocused() ? FOCUS_IN : 0;
+            if (own == FOCUS_IN) Xlib.putBack(handle, FOCUS_IN);
+            return true;
+        }
+        if (own == FOCUS_IN && focused) {
+            own = 0;
+            return true;
+        }
+        return false;
+    }
+
+    private static void finish() {
+        long handle = letGo.handle();
+        long display = GLFWNativeX11.glfwGetX11Display();
+        // Give Xwayland the original pointer position before showing the cursor drops its lock. GLFW moves the pointer
+        // only for a window with the X focus; without it the pointer shows where labwc left it.
+        if (hiddenInX) GLFW.glfwSetCursorPos(handle, startX, startY);
+        JNI.invokePJI(display, 0L /* CurrentTime */, Xlib.UNGRAB_POINTER);
+        if (hiddenInX) JNI.invokePJV(display, GLFWNativeX11.glfwGetX11Window(handle), Xlib.SHOW_CURSOR);
+        JNI.invokePI(display, Xlib.FLUSH);
+        hiddenInX = false;
+        letGo = null;
+    }
+
+    /** Client game tests: no release is under way and none of the mod's own events waits in Xlib's queue. */
+    public static boolean settled() {
+        return letGo == null && own == 0;
+    }
 
     private static void direct(Window window, int mode, double x, double y) {
         GLFW.glfwSetCursorPos(window.handle(), x, y);
@@ -178,45 +205,32 @@
         private static final SharedLibrary X11 = load("libX11.so.6"), XFIXES = load("libXfixes.so.3");
         static final long HIDE_CURSOR = address(XFIXES, "XFixesHideCursor"), SHOW_CURSOR = address(XFIXES, "XFixesShowCursor"),
-                UNGRAB_POINTER = address(X11, "XUngrabPointer"), GET_INPUT_FOCUS = address(X11, "XGetInputFocus"),
-                SEND_EVENT = address(X11, "XSendEvent"), SYNC = address(X11, "XSync"), FLUSH = address(X11, "XFlush");
+                UNGRAB_POINTER = address(X11, "XUngrabPointer"), PUT_BACK_EVENT = address(X11, "XPutBackEvent"),
+                FLUSH = address(X11, "XFlush");
 
         static boolean ready() {
-            return HIDE_CURSOR != 0 && SHOW_CURSOR != 0 && UNGRAB_POINTER != 0 && GET_INPUT_FOCUS != 0
-                    && SEND_EVENT != 0 && SYNC != 0 && FLUSH != 0
+            return HIDE_CURSOR != 0 && SHOW_CURSOR != 0 && UNGRAB_POINTER != 0 && PUT_BACK_EVENT != 0 && FLUSH != 0
                     && GLFW.glfwGetPlatform() == GLFW.GLFW_PLATFORM_X11 && GLFWNativeX11.glfwGetX11Display() != 0;
         }
 
-        /**
-         * Sends the window the FocusOut X sends when the focus leaves it (NotifyNormal, NotifyNonlinear), and waits until
-         * the server has handled it: the event is then in Xlib's queue, and the next poll hands it to GLFW. (Without the
-         * round trip a poll could come first, and GLFW would see the event only after the mode was normal again.)
-         */
-        static void focusOut(long display, long xwindow) {
-            try (var stack = MemoryStack.stackPush()) {
-                // XFocusChangeEvent on x86-64: type, serial, send_event, display, window, mode, detail; XEvent is 192 bytes.
-                var event = stack.calloc(192);
-                event.putInt(0, 10 /* FocusOut */);
-                event.putInt(16, 1 /* send_event */);
-                event.putLong(24, display);
-                event.putLong(32, xwindow);
-                event.putInt(40, 0 /* NotifyNormal */);
-                event.putInt(44, 3 /* NotifyNonlinear */);
-                // XSendEvent(display, window, propagate False, FocusChangeMask, event)
-                JNI.invokePPPPI(display, xwindow, 0, 1L << 21, MemoryUtil.memAddress(event), SEND_EVENT);
-                JNI.invokePI(display, 0 /* keep the queued events */, SYNC);
-            }
-        }
-
-        /** GLFW's own test for its window's focus: the X input focus is that window. */
-        static boolean focused(long handle) {
-            try (var stack = MemoryStack.stackPush()) {
-                var focus = stack.callocLong(1);
-                var revert = stack.callocInt(1);
-                JNI.invokePPPI(GLFWNativeX11.glfwGetX11Display(), MemoryUtil.memAddress(focus),
-                        MemoryUtil.memAddress(revert), GET_INPUT_FOCUS);
-                return focus.get(0) == GLFWNativeX11.glfwGetX11Window(handle);
-            }
-        }
+        /**
+         * Puts a focus event for the window (NotifyNormal, NotifyNonlinear, as X sends one) at the head of Xlib's event
+         * queue: XPutBackEvent. It is the next event GLFW reads, ahead of everything the server has sent. Nothing goes to
+         * the server and nothing is waited for, so no real focus change can get between this and GLFW's handling of it.
+         */
+        static void putBack(long handle, int type) {
+            long display = GLFWNativeX11.glfwGetX11Display();
+            try (var stack = MemoryStack.stackPush()) {
+                // XFocusChangeEvent on x86-64: type, serial, send_event, display, window, mode, detail; XEvent is 192 bytes.
+                var event = stack.calloc(192);
+                event.putInt(0, type);
+                event.putInt(16, 1 /* send_event: not from the server */);
+                event.putLong(24, display);
+                event.putLong(32, GLFWNativeX11.glfwGetX11Window(handle));
+                event.putInt(40, 0 /* NotifyNormal */);
+                event.putInt(44, 3 /* NotifyNonlinear */);
+                JNI.invokePPI(display, MemoryUtil.memAddress(event), PUT_BACK_EVENT);
+            }
+        }
 
         private static SharedLibrary load(String name) {
             try {
```

If LWJGL has no `JNI.invokePPI(long, long, long)` overload, the build says so. Then call `XPutBackEvent` through Java's foreign-function API, as the test fixture already does for `XSetErrorHandler`.

**`mod/src/client/java/dev/aresos/client/mixin/WindowHomeScreenMixin.java`**

```diff
--- a/mod/src/client/java/dev/aresos/client/mixin/WindowHomeScreenMixin.java
+++ b/mod/src/client/java/dev/aresos/client/mixin/WindowHomeScreenMixin.java
@@ -7,7 +7,6 @@
 import org.spongepowered.asm.mixin.Mixin;
 import org.spongepowered.asm.mixin.injection.At;
 import org.spongepowered.asm.mixin.injection.Inject;
-import org.spongepowered.asm.mixin.injection.ModifyVariable;
 import org.spongepowered.asm.mixin.injection.Redirect;
 import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
 
@@ -30,9 +29,10 @@
         if (HomeScreen.session()) ci.cancel();
     }
 
-    // Package 328a: GLFW's focus callback, inside its event handling (WorldCapture.focusChanged says why).
-    @ModifyVariable(method = "onFocus", at = @At("HEAD"), argsOnly = true)
-    private boolean aresos$focusChanged(boolean focused, long handle) {
-        return WorldCapture.focusChanged(handle, focused);
+    // Package 328a: GLFW's focus callback, inside its event handling. The release's own focus events stop here, so
+    // Minecraft's record of the focus holds only what the real events said (WorldCapture.ownFocusEvent says why).
+    @Inject(method = "onFocus", at = @At("HEAD"), cancellable = true)
+    private void aresos$ownFocusEvent(long handle, boolean focused, CallbackInfo ci) {
+        if (WorldCapture.ownFocusEvent(handle, focused)) ci.cancel();
     }
 }
```

**`mod/src/gametest/java/dev/aresos/test/mixin/WorldCaptureReleaseTestMixin.java`** (five named points of a release)

```diff
--- a/mod/src/gametest/java/dev/aresos/test/mixin/WorldCaptureReleaseTestMixin.java
+++ b/mod/src/gametest/java/dev/aresos/test/mixin/WorldCaptureReleaseTestMixin.java
@@ -1,17 +1,42 @@
 package dev.aresos.test.mixin;
 
+import com.mojang.blaze3d.platform.Window;
 import dev.aresos.client.WorldCapture;
 import dev.aresos.test.WorldKeepsPointerClientGameTest;
 import org.spongepowered.asm.mixin.Mixin;
 import org.spongepowered.asm.mixin.injection.At;
 import org.spongepowered.asm.mixin.injection.Inject;
 import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
+import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
 
+/** Named points of a release where the native test moves the real X focus (WorldKeepsPointerClientGameTest.races). */
 @Mixin(WorldCapture.class)
 public abstract class WorldCaptureReleaseTestMixin {
+    @Inject(method = "release", at = @At("HEAD"))
+    private static void aresos$asked(Window window, double x, double y, WorldCapture.CursorMode minecraft, CallbackInfo ci) {
+        WorldKeepsPointerClientGameTest.seam("asked");
+    }
+
     @Inject(method = "beforePollEvents", at = @At(value = "INVOKE",
-            target = "Ldev/aresos/client/WorldCapture$Xlib;focusOut(JJ)V"))
-    private static void aresos$raceFocusOut(CallbackInfo ci) {
-        WorldKeepsPointerClientGameTest.beforeSyntheticFocusOut();
+            target = "Ldev/aresos/client/WorldCapture$Xlib;putBack(JI)V"))
+    private static void aresos$queued(CallbackInfo ci) {
+        WorldKeepsPointerClientGameTest.seam("queued");
+    }
+
+    // After GLFW let go, before the mode turns normal: where RECHECK-1's race sat, now inside one event.
+    @Inject(method = "ownFocusEvent", at = @At(value = "INVOKE",
+            target = "Lorg/lwjgl/glfw/GLFW;glfwSetInputMode(JII)V"))
+    private static void aresos$normal(long handle, boolean focused, CallbackInfoReturnable<Boolean> cir) {
+        WorldKeepsPointerClientGameTest.seam("normal");
+    }
+
+    @Inject(method = "finish", at = @At("HEAD"))
+    private static void aresos$show(CallbackInfo ci) {
+        WorldKeepsPointerClientGameTest.seam("show");
+    }
+
+    @Inject(method = "afterPollEvents", at = @At("HEAD"))
+    private static void aresos$polled(CallbackInfo ci) {
+        WorldKeepsPointerClientGameTest.seam("polled");
     }
 }
```

**`mod/src/gametest/java/dev/aresos/test/WorldKeepsPointerClientGameTest.java`** (the seam replaces the one race hook)

```diff
--- a/mod/src/gametest/java/dev/aresos/test/WorldKeepsPointerClientGameTest.java
+++ b/mod/src/gametest/java/dev/aresos/test/WorldKeepsPointerClientGameTest.java
@@ -49,11 +49,13 @@
 public final class WorldKeepsPointerClientGameTest implements FabricClientGameTest {
-    private static Runnable raceFocusOut;
+    // Client thread only: what runs once at a named point of a release (WorldCaptureReleaseTestMixin).
+    private static String seamName;
+    private static Runnable seamRun;
 
-    public static void beforeSyntheticFocusOut() {
-        if (raceFocusOut == null) return;
-        var race = raceFocusOut;
-        raceFocusOut = null;
-        race.run();
+    public static void seam(String name) {
+        if (seamRun == null || !name.equals(seamName)) return;
+        var run = seamRun;
+        seamRun = null;
+        run.run();
     }
 
     @Override public void runTest(ClientGameTestContext context) {
@@ -463,5 +465,8 @@
             var previous = context.computeOnClient(client -> {
                 long handle = client.getWindow().handle();
-                if (race) raceFocusOut = () -> X11.focus(handle, true);
+                if (race) {
+                    seamName = "queued";
+                    seamRun = () -> X11.focus(handle, true);
+                }
                 var keyboard = (KeyboardTestAccess) (Object) client.keyboardHandler;
                 return GLFW.glfwSetKeyCallback(handle, (window, key, scancode, action, mods) -> {
@@ -483,7 +488,7 @@
                 input("key esc");
                 context.waitFor(client -> client.gui.screen() instanceof AresOsMenuScreen && released(client));
-                context.runOnClient(client -> check(raceFocusOut == null, "The real FocusIn never raced the synthetic event"));
+                context.runOnClient(client -> check(seamRun == null, "The real FocusIn never raced the mod's own FocusOut"));
             } finally {
                 context.runOnClient(client -> {
-                    raceFocusOut = null;
+                    seamRun = null;
                     GLFW.glfwSetKeyCallback(client.getWindow().handle(), previous).free();
```

### 2.6 Order of work for the builder

1. **Confirm five facts in GLFW 3.5.1.** If one is false, stop and report; do not patch around it.
   - **F1:** in `src/x11_window.c`, a FocusOut whose mode is not NotifyGrab or NotifyUngrab, in DISABLED mode, calls `enableCursor` with no focus test. `enableCursor` turns raw motion off, ungrabs and sets `_glfw.x11.disabledCursorWindow = NULL`. The handler does not look at `send_event`.
   - **F2:** `glfwSetInputMode` (`src/input.c`) returns early for an unchanged mode. `_glfwSetCursorModeX11` does its X work only inside `if (_glfwWindowFocusedX11(window))`. With the disabled-cursor window already NULL, a switch to NORMAL only ungrabs (focused) or does nothing.
   - **F3:** a FocusIn captures only in DISABLED or CAPTURED mode. In NORMAL it sets the input context's focus and calls the callback.
   - **F4:** `_glfwPollEventsX11` takes events from Xlib's queue in order, and re-centres only while the disabled-cursor window is set.
   - **F5:** the FocusOut case iconifies only a fullscreen window. The session's window never is one.
2. **Check Minecraft's call sites.** `InputConstants.grabOrReleaseMouse` should be called from `MouseHandler.grabMouse` and `releaseMouse` only. Another caller would change the mode behind the mod.
3. **Prove the lever with GLFW alone,** before touching the mod (section 2.7, level 1).
4. **Apply the diffs,** add the tests of level 2, then two full passes as `AGENTS.md` requires.

### 2.7 Tests that prove each race

**Level 1: GLFW alone (`reviews/328-look-around/rig/GlfwProbe.java`).** Add:
- `away`, `root`, `back`: `XSetInputFocus` to PointerRoot, the root window, or the window, then `XSync`.
- `normal`: `glfwSetInputMode(NORMAL)` only.
- `lever`, `lever away`, `lever root`, `lever back`: put a FocusOut back, poll, and set NORMAL in the focus callback. The optional word moves the real focus inside the callback, before NORMAL.
- Several commands on one line, split at `;`, run with no poll between them.

The instrument: move the virtual pointer to 90,70 and then 140,110 over the window, and read `state`. A stale GLFW pulls the X pointer back to 640,360 each time. `state.sh` must also say "X pointer grab: free".

| Run | Commands | Must show |
| --- | --- | --- |
| Control, RECHECK-1's race | `capture`, then `away;normal` | Stale: pointer pulled to the centre, grab held. |
| Control, PROGRESS's second gap | `capture`, `away`, a poll, `normal` | Stale. |
| Lever, focused | `capture`, `lever` | Clean. Mode 34001. |
| Lever, focus left unseen | `capture`, `away;lever` | Clean. |
| Lever, focus left and seen | `capture`, `away`, a poll, `lever` | Clean. |
| Lever, focus moves inside | `capture`, `lever away`; `capture`, `away;lever back` | Clean. |
| Lever from the stale state | a control run, then `lever` | Clean. The repair works from any state. |

The control runs matter. If they show clean, the instrument cannot see the bug, and nothing after them counts as proof.

**Level 2: the real game (`WorldKeepsPointerClientGameTest`, under `client-test.sh --session`).** The test moves the real X focus synchronously from the game's own X connection, at a named seam. That fixes where the real events sit relative to the mod's FocusOut.

| Ordering | How to force it |
| --- | --- |
| Real focus events GLFW has already handled, pointer FocusIn included | Move the focus to PointerRoot, `XSync`, wait two ticks, then release. Both events are read by one poll, so `HomeScreen.frame` does not release first. |
| Real events queued behind the mod's FocusOut | Move the focus at seam `asked` or `queued`. |
| The focus moves between GLFW's letting go and NORMAL | Seam `normal`. |
| The focus moves before the pointer is put back and shown | Seam `show`. |
| The focus moves right after | Seam `polled`. |

Add `races()`: three start states (focused; away and still queued; away and already handled), five seams, five moves (`away`, `root`, `back`, `away,back`, `back,away`). The "already handled" start uses PointerRoot only. That is 75 cycles, each a capture by a real click, then `releaseMouse()`, then `clean()`. I guess about two minutes in all.

`clean()` checks, after putting the X focus back:
- `released(client)` and `WorldCapture.settled()`;
- no XFixes hide is outstanding (`X11.checkCursorShown`);
- `state.sh` says the grab is free;
- the pointer stays at 90,70 and at 140,110 after three ticks each;
- `client.isWindowActive()` is true;
- the next cycle's click captures. That is condition (3).

Each release cause once, with the focus leaving at seam `normal`:
- real Esc through GLFW (extend `escDuringHandoff`);
- the helper's `shell_focus` background;
- SIGKILL of the helper (the existing block);
- leaving the world while captured, last, on the title screen.

Also assert that the game log never holds "did not hand back".

The rig's X window manager may put the focus back by itself. Assert the intended focus right before each seam runs, as `escDuringHandoff` already does, so a cycle cannot pass on the wrong state.

**Not proven by this suite:** that the FocusIn restores dead keys. The rig's virtual keyboard has a US keymap. One hand check in `GlfwProbe.java` with a keymap that has dead keys would settle it.

### 2.8 Known limits (decision 24)

- **Held keys:** GLFW forgets held keys and buttons at every release, as it does on a real focus loss. After Esc and closing the menu, a key still held walks again only after a new press. Low harm.
- **Held Esc:** GLFW may report its first repeat as a new press. Check once in the rig by holding Esc for 1.5 s, and compare with today's build.
- **One frame:** the cursor stays hidden from the request to the next poll.
- **Same-frame capture:** a capture asked for in the same frame as a release is refused. The next click captures.
- **Pointer position:** when an app took the focus, the pointer still reappears where labwc left it (RECHECK-1, point 5).
- **A silent helper:** if the helper is alive but stuck, and the pointer rests on the world, the hide can outlast an app taking the focus. `HomeScreen.frame` is the only other net. I did not read the shell client's timeout.
- **No `libXfixes` or no X11:** Minecraft's own path, as before.
- **Outside the session:** GLFW's bug remains, as in vanilla.
- **Struct layout:** the event layout is for 64-bit Linux.

### 2.9 Judgment calls for the lead

- **The lever also undoes Minecraft's own captures in the session** (`capturedInX`): ones made before the helper connected, or outside a desktop world. Without it, such a capture released behind an app can still leave GLFW re-centring. REVIEW-1 asked to scope captures to the connected desktop world; this is cleanup, not capture. To narrow it, delete `capturedInX` and its one use.
- **I left out a deferred re-capture** after a refused same-frame capture. It is one more state for a case the brief already accepts.

## 3. B: native Wayland for the game

All of this is from reading the repo and general knowledge of GLFW's Wayland backend. None of it was run. Statements about Minecraft 26.2 and NVIDIA are unverified.

**What it removes:**
- The cause of the leak: one lock, no warps, no hint to jump to. `rig/locker.py` already shows a held lock keeps clicks in the window.
- `WorldCapture`'s whole native half: the XFixes hide, the lever, the Xlib calls, `RenderSystemCaptureMixin`, the `onFocus` hook, and the test seams.
- The "GLFW says focused behind an app" quirk. GLFW's focus becomes the real keyboard focus.

**What stays or changes in the mod (hub):**
- `PointerRules.mayCapture` stays. labwc grants a lock only to the focused window.
- Release order still needs proof. As I remember it, GLFW's Wayland cursor code returns early when the pointer is not over the window, so a NORMAL set then may leave a lock object until the pointer comes back. It is smaller than today's problem, but it has to be tested.
- Minecraft 26.2 asks GLFW for X11 (PROGRESS and `client-test.sh` both say so). A mixin must change that, behind an environment switch from the supervisor.
- Expected GLFW errors to guard:
  - setting the window icon; in older versions this crashed the start;
  - `glfwSetCursorPos` in normal mode; `WorldCapture` already wraps that call;
  - `glfwGetWindowPos`, which package 56's test coordinates and the 328a test use.
- The window needs the undecorated hint. With `serverDecoration="no"`, GLFW would otherwise draw its own title bar.
- Focus code needs a second look: `HomeScreen.frame`, `MinecraftFocusMixin`, the focus-return logic.
- **The biggest unknown is the frame loop.** A Wayland client can block in buffer swap while its window is covered. The client thread then stops, and with it the world save at shutdown. Under Xwayland this cannot happen. It likely needs vsync off in the session, and proof with a maximized app over the world.

**labwc rules (`os/config/usr/share/aresos/labwc/rc.xml`):** I expect no edit. `WindowIdentityMixin` already sets the Wayland app_id to `aresos-desktop`, and Maximize and ToggleAlwaysOnBottom apply to native windows too.

**The helper (`os/config/usr/libexec/aresos-shell`):** I expect no code change. It tracks windows by foreign-toplevel app_id. Its timing assumptions need a re-run with a native window: the restored desktop giving focus back, Super's hand-off, covering and uncover.

**The supervisor (`os/config/usr/libexec/aresos-desktop`, `aresos-desktop-java`):**
- `game_environment` gains the platform switch.
- The NVIDIA set is GLX-only today; EGL needs its own vendor selection.
- The wrapper's `SUPPLIED` allow-list must gain both keys, with their tests.
- Rollback is one value, as long as the mod keeps its X11 path. So A is also B's fallback.

**NVIDIA:** today the game renders through GLX offload under Xwayland. Natively it uses NVIDIA's EGL on Wayland, or Vulkan if 26.2's `GpuBackend` allows it, and shares buffers with a compositor on the Intel GPU. Frame pacing and flicker depend on the driver and labwc versions in the image. Only the laptop can prove this.

**The rigs:**
- `client-test.sh` probes the GPU with `glxinfo`; it needs an EGL probe and an EGL offload set.
- The 328a test's X11 helpers go.
- `probe.py`, `vinput.py`, `tl.py` and `locker.py` stay.
- `GlfwProbe.java` needs two lines for a Wayland variant.
- The 30 client tests' screenshots must come out the same.

**Mouse feel may change** with the backend, and the owner is about to judge feel in 328b to 328d.

**Rough size and owners:**

| Owner | Work | Size |
| --- | --- | --- |
| hub (`mod/`) | A spike first: GLFW alone and the dev client on Wayland in the 328 rig. Then the platform switch, the guards, the focus review and the test port. | 1 step for the spike, then 2 to 3 steps plus reviews |
| desktop | Re-run the helper's rigs with a native window; confirm `rc.xml`. | 1 step |
| aresos | Supervisor and wrapper environment with tests; image check (NVIDIA EGL pieces, labwc version); VM rehearsal; a release; the owner's laptop trial. | 1 to 2 steps plus a release |

That is weeks at one agent at a time, and the spike may say no.

## 4. C: recommendation

**A now, B later.**

- **The owner's harm.** R28 on his laptop sends his clicks into Chrome today. The branch's capture half fixes that and is proven in the rig. What blocks it is the release, where the worst case is a mouse he can't use on the world. A removes that class of bug: no focus query is left to go stale.
- **The cost of more rounds.** Both NOT SAFE verdicts were about asking the server and then acting. The redesign shrinks what the reviewer must check to two questions: are F1 to F5 true of GLFW 3.5.1, and does the matrix pass with its controls failing first? It is one builder step and one review. The handoff says both budgets are over pace.
- **The structure.** B is the better structure in the end, because it deletes native code where A adds a careful workaround. But it touches three owners' files and needs a release. It also has open NVIDIA and frame-loop risks, and it still needs the safe fallback and its own release tests. It also needs A's X11 path as its rollback.

**Two conditions:**
- **Stop rule for A.** If step 1 or step 3 of section 2.6 fails, stop and report. Do not add another patch to the release path. Then the B spike moves up.
- **When to start B's spike.** After the owner picks a look mode in 328d. `edge` never captures, so his pick decides how much capture matters. The backend should also not change under his trial.

Also report the GLFW bug upstream. A fixed `_glfwSetCursorModeX11` would make A's lever unnecessary on any backend that keeps X11.
