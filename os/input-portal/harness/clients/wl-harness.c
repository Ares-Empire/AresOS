// Package 316's harness: the two Wayland test clients, in one program.
//
//   wl-harness window [--lock]
//                       a full-screen window that prints every input event it receives, one per line
//                       --lock adds relative motion and a pointer lock; "release" on stdin destroys the lock
//   wl-harness input pointer|keyboard
//                       a virtual pointer or a virtual keyboard, driven by lines on stdin:
//                         abs X Y W H    put the pointer at X,Y of a W by H layout
//                         rel DX DY      move it by DX,DY
//                         btn CODE 0|1   release or press a button (evdev code)
//                         axis STEPS     turn the wheel by STEPS clicks
//                         key CODE 0|1   release or press a key (evdev code), with the modifier state that follows
//                       It answers each line with OK once the compositor has taken it.
//   wl-harness outputs  a client that binds zwlr_output_manager_v1 and only listens, until it is stopped
//
// A virtual device lives as long as its process: labwc's seat has a pointer and a keyboard only while a
// device of that kind exists, and a client that holds a pointer lock loses it with the seat's pointer. So
// each kind is its own process, and stopping the pointer's takes the seat's pointer away and nothing else.
#define _GNU_SOURCE
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include <xkbcommon/xkbcommon.h>
#include "pointer-constraints-unstable-v1-client-protocol.h"
#include "relative-pointer-unstable-v1-client-protocol.h"
#include "virtual-keyboard-unstable-v1-client-protocol.h"
#include "wlr-output-management-unstable-v1-client-protocol.h"
#include "wlr-virtual-pointer-unstable-v1-client-protocol.h"
#include "xdg-shell-client-protocol.h"

static struct wl_display *display;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct wl_seat *seat;
static struct xdg_wm_base *wm_base;
static struct zwlr_virtual_pointer_manager_v1 *pointer_manager;
static struct zwp_virtual_keyboard_manager_v1 *keyboard_manager;
static struct zwlr_output_manager_v1 *output_manager;
static struct zwp_pointer_constraints_v1 *constraints;
static struct zwp_relative_pointer_manager_v1 *relative_manager;
static bool wants_lock;
static bool wants_outputs;

static void die(const char *why)
{
	fprintf(stderr, "wl-harness: %s\n", why);
	exit(2);
}

static uint32_t now_ms(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

static void registry_global(void *data, struct wl_registry *registry, uint32_t name, const char *interface,
	uint32_t version)
{
	if (!strcmp(interface, wl_compositor_interface.name)) {
		compositor = wl_registry_bind(registry, name, &wl_compositor_interface, 4);
	} else if (!strcmp(interface, wl_shm_interface.name)) {
		shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
	} else if (!strcmp(interface, wl_seat_interface.name) && !seat) {
		seat = wl_registry_bind(registry, name, &wl_seat_interface, version < 5 ? version : 5);
	} else if (!strcmp(interface, xdg_wm_base_interface.name)) {
		wm_base = wl_registry_bind(registry, name, &xdg_wm_base_interface, 1);
	} else if (!strcmp(interface, zwlr_virtual_pointer_manager_v1_interface.name)) {
		pointer_manager = wl_registry_bind(registry, name, &zwlr_virtual_pointer_manager_v1_interface, 1);
	} else if (!strcmp(interface, zwp_virtual_keyboard_manager_v1_interface.name)) {
		keyboard_manager = wl_registry_bind(registry, name, &zwp_virtual_keyboard_manager_v1_interface, 1);
	} else if (wants_lock && !strcmp(interface, zwp_pointer_constraints_v1_interface.name)) {
		constraints = wl_registry_bind(registry, name, &zwp_pointer_constraints_v1_interface, 1);
	} else if (wants_lock && !strcmp(interface, zwp_relative_pointer_manager_v1_interface.name)) {
		relative_manager = wl_registry_bind(registry, name, &zwp_relative_pointer_manager_v1_interface, 1);
	} else if (wants_outputs && !strcmp(interface, zwlr_output_manager_v1_interface.name)) {
		output_manager = wl_registry_bind(registry, name, &zwlr_output_manager_v1_interface, version < 4 ? version : 4);
	}
}

static void registry_global_remove(void *data, struct wl_registry *registry, uint32_t name) {}

static const struct wl_registry_listener registry_listener = {
	.global = registry_global,
	.global_remove = registry_global_remove,
};

// ---- the window --------------------------------------------------------------------------------------------

static struct wl_surface *surface;
static struct wl_pointer *pointer;
static struct wl_keyboard *keyboard;
static struct zwp_locked_pointer_v1 *lock;
static struct zwp_relative_pointer_v1 *relative;
static int32_t width, height;

// The persistent constraint and unaccelerated deltas used by package 311's lock_phase().
static void relative_motion(void *d, struct zwp_relative_pointer_v1 *r, uint32_t hi, uint32_t lo,
	wl_fixed_t dx, wl_fixed_t dy, wl_fixed_t dx_unaccel, wl_fixed_t dy_unaccel)
{
	printf("REL %.2f %.2f\n", wl_fixed_to_double(dx_unaccel), wl_fixed_to_double(dy_unaccel));
}

static void locked(void *d, struct zwp_locked_pointer_v1 *l) { puts("LOCKED"); }
static void unlocked(void *d, struct zwp_locked_pointer_v1 *l) { puts("UNLOCKED"); }
static const struct zwp_locked_pointer_v1_listener lock_listener = {.locked = locked, .unlocked = unlocked};
static const struct zwp_relative_pointer_v1_listener relative_listener = {.relative_motion = relative_motion};

static void pointer_enter(void *d, struct wl_pointer *p, uint32_t serial, struct wl_surface *s, wl_fixed_t x,
	wl_fixed_t y)
{
	printf("ENTER %.1f %.1f\n", wl_fixed_to_double(x), wl_fixed_to_double(y));
	if (wants_lock) {
		relative = zwp_relative_pointer_manager_v1_get_relative_pointer(relative_manager, p);
		zwp_relative_pointer_v1_add_listener(relative, &relative_listener, NULL);
		lock = zwp_pointer_constraints_v1_lock_pointer(constraints, s, p, NULL,
			ZWP_POINTER_CONSTRAINTS_V1_LIFETIME_PERSISTENT);
		zwp_locked_pointer_v1_add_listener(lock, &lock_listener, NULL);
		wl_surface_commit(s);
		wants_lock = false;
	}
}

static void pointer_leave(void *d, struct wl_pointer *p, uint32_t serial, struct wl_surface *s)
{
	printf("LEAVE\n");
}

static void pointer_motion(void *d, struct wl_pointer *p, uint32_t time, wl_fixed_t x, wl_fixed_t y)
{
	printf("MOTION %.1f %.1f\n", wl_fixed_to_double(x), wl_fixed_to_double(y));
}

static void pointer_button(void *d, struct wl_pointer *p, uint32_t serial, uint32_t time, uint32_t button,
	uint32_t state)
{
	printf("BUTTON %u %u\n", button, state);
}

static void pointer_axis(void *d, struct wl_pointer *p, uint32_t time, uint32_t axis, wl_fixed_t value)
{
	printf("AXIS %u %.1f\n", axis, wl_fixed_to_double(value));
}

static void pointer_frame(void *d, struct wl_pointer *p) {}
static void pointer_axis_source(void *d, struct wl_pointer *p, uint32_t source) {}
static void pointer_axis_stop(void *d, struct wl_pointer *p, uint32_t time, uint32_t axis) {}
static void pointer_axis_discrete(void *d, struct wl_pointer *p, uint32_t axis, int32_t discrete) {}

static const struct wl_pointer_listener pointer_listener = {
	.enter = pointer_enter,
	.leave = pointer_leave,
	.motion = pointer_motion,
	.button = pointer_button,
	.axis = pointer_axis,
	.frame = pointer_frame,
	.axis_source = pointer_axis_source,
	.axis_stop = pointer_axis_stop,
	.axis_discrete = pointer_axis_discrete,
};

static void keyboard_keymap(void *d, struct wl_keyboard *k, uint32_t format, int32_t fd, uint32_t size)
{
	close(fd);
}

static void keyboard_enter(void *d, struct wl_keyboard *k, uint32_t serial, struct wl_surface *s,
	struct wl_array *keys)
{
	printf("KBD_ENTER\n");
}

static void keyboard_leave(void *d, struct wl_keyboard *k, uint32_t serial, struct wl_surface *s)
{
	printf("KBD_LEAVE\n");
}

static void keyboard_key(void *d, struct wl_keyboard *k, uint32_t serial, uint32_t time, uint32_t key,
	uint32_t state)
{
	printf("KEY %u %u\n", key, state);
}

static void keyboard_modifiers(void *d, struct wl_keyboard *k, uint32_t serial, uint32_t depressed,
	uint32_t latched, uint32_t locked, uint32_t group)
{
	printf("MODS %u\n", depressed);
}

static void keyboard_repeat_info(void *d, struct wl_keyboard *k, int32_t rate, int32_t delay) {}

static const struct wl_keyboard_listener keyboard_listener = {
	.keymap = keyboard_keymap,
	.enter = keyboard_enter,
	.leave = keyboard_leave,
	.key = keyboard_key,
	.modifiers = keyboard_modifiers,
	.repeat_info = keyboard_repeat_info,
};

static void seat_capabilities(void *d, struct wl_seat *s, uint32_t caps)
{
	printf("SEAT_CAPS pointer=%d keyboard=%d\n", !!(caps & WL_SEAT_CAPABILITY_POINTER),
		!!(caps & WL_SEAT_CAPABILITY_KEYBOARD));
	if ((caps & WL_SEAT_CAPABILITY_POINTER) && !pointer) {
		pointer = wl_seat_get_pointer(s);
		wl_pointer_add_listener(pointer, &pointer_listener, NULL);
	} else if (!(caps & WL_SEAT_CAPABILITY_POINTER) && pointer) {
		wl_pointer_release(pointer);
		pointer = NULL;
	}
	if ((caps & WL_SEAT_CAPABILITY_KEYBOARD) && !keyboard) {
		keyboard = wl_seat_get_keyboard(s);
		wl_keyboard_add_listener(keyboard, &keyboard_listener, NULL);
	} else if (!(caps & WL_SEAT_CAPABILITY_KEYBOARD) && keyboard) {
		wl_keyboard_release(keyboard);
		keyboard = NULL;
	}
}

static void seat_name(void *d, struct wl_seat *s, const char *name) {}

static const struct wl_seat_listener seat_listener = {
	.capabilities = seat_capabilities,
	.name = seat_name,
};

static void attach_buffer(int32_t w, int32_t h)
{
	int stride = w * 4;
	size_t size = (size_t)stride * h;
	int fd = memfd_create("wl-harness-buffer", MFD_CLOEXEC);
	if (fd < 0 || ftruncate(fd, size) < 0) {
		die("no memory for the window's buffer");
	}
	uint32_t *pixels = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
	if (pixels == MAP_FAILED) {
		die("the window's buffer could not be mapped");
	}
	for (size_t i = 0; i < size / 4; i++) {
		pixels[i] = 0xff204060;
	}
	munmap(pixels, size);
	struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
	struct wl_buffer *buffer = wl_shm_pool_create_buffer(pool, 0, w, h, stride, WL_SHM_FORMAT_XRGB8888);
	wl_shm_pool_destroy(pool);
	close(fd);
	wl_surface_attach(surface, buffer, 0, 0);
	wl_surface_damage_buffer(surface, 0, 0, w, h);
}

static void wm_ping(void *d, struct xdg_wm_base *b, uint32_t serial)
{
	xdg_wm_base_pong(b, serial);
}

static const struct xdg_wm_base_listener wm_listener = {.ping = wm_ping};

static void xdg_configure(void *d, struct xdg_surface *x, uint32_t serial)
{
	int32_t w = width > 0 ? width : 1280, h = height > 0 ? height : 720;
	xdg_surface_ack_configure(x, serial);
	attach_buffer(w, h);
	wl_surface_commit(surface);
	printf("CONFIGURED %d %d\n", w, h);
}

static const struct xdg_surface_listener xdg_listener = {.configure = xdg_configure};

static void toplevel_configure(void *d, struct xdg_toplevel *t, int32_t w, int32_t h, struct wl_array *states)
{
	width = w;
	height = h;
}

static void toplevel_close(void *d, struct xdg_toplevel *t) {}

static const struct xdg_toplevel_listener toplevel_listener = {
	.configure = toplevel_configure,
	.close = toplevel_close,
};

static int dispatch_lock_window(void)
{
	struct pollfd fds[] = {{.fd = wl_display_get_fd(display), .events = POLLIN},
		{.fd = STDIN_FILENO, .events = POLLIN}};

	while (wl_display_dispatch_pending(display) >= 0 && wl_display_flush(display) >= 0
		&& poll(fds, 2, -1) > 0) {
		if (fds[0].revents && wl_display_dispatch(display) < 0) {
			return 0;
		}
		if (fds[1].revents) {
			char line[32];
			if (!fgets(line, sizeof line, stdin)) {
				return 0;
			}
			if (!lock || strcmp(line, "release\n")) {
				die("expected release with a pointer lock");
			}
			zwp_locked_pointer_v1_destroy(lock);
			zwp_relative_pointer_v1_destroy(relative);
			lock = NULL;
			if (wl_display_roundtrip(display) < 0) {
				die("the compositor is gone");
			}
			puts("RELEASED");
		}
	}
	return 0;
}

static int run_window(void)
{
	if (!compositor || !shm || !seat || !wm_base) {
		die("the compositor lacks wl_compositor, wl_shm, wl_seat or xdg_wm_base");
	}
	if (wants_lock && (!constraints || !relative_manager)) {
		die("the compositor lacks pointer constraints or relative pointer");
	}
	setvbuf(stdout, NULL, _IOLBF, 0);
	wl_seat_add_listener(seat, &seat_listener, NULL);
	xdg_wm_base_add_listener(wm_base, &wm_listener, NULL);
	surface = wl_compositor_create_surface(compositor);
	struct xdg_surface *xdg = xdg_wm_base_get_xdg_surface(wm_base, surface);
	xdg_surface_add_listener(xdg, &xdg_listener, NULL);
	struct xdg_toplevel *toplevel = xdg_surface_get_toplevel(xdg);
	xdg_toplevel_add_listener(toplevel, &toplevel_listener, NULL);
	xdg_toplevel_set_title(toplevel, "harness-probe");
	xdg_toplevel_set_app_id(toplevel, "harness-probe");
	xdg_toplevel_set_fullscreen(toplevel, NULL);
	wl_surface_commit(surface);
	if (wants_lock) {
		return dispatch_lock_window();
	}
	while (wl_display_dispatch(display) >= 0) {
	}
	return 0;
}

// ---- the virtual pointer and keyboard ----------------------------------------------------------------------

static int run_input(bool is_keyboard)
{
	if (!seat || !pointer_manager || !keyboard_manager) {
		die("the compositor lacks wl_seat, zwlr_virtual_pointer_manager_v1 or zwp_virtual_keyboard_manager_v1");
	}
	struct zwlr_virtual_pointer_v1 *vp = NULL;
	struct zwp_virtual_keyboard_v1 *vk = NULL;
	struct xkb_state *state = NULL;
	if (is_keyboard) {
		vk = zwp_virtual_keyboard_manager_v1_create_virtual_keyboard(keyboard_manager, seat);
		// The default keymap (evdev, pc105, us): the keys are real evdev codes, as from a real keyboard.
		struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
		struct xkb_keymap *keymap =
			context ? xkb_keymap_new_from_names(context, NULL, XKB_KEYMAP_COMPILE_NO_FLAGS) : NULL;
		char *text = keymap ? xkb_keymap_get_as_string(keymap, XKB_KEYMAP_FORMAT_TEXT_V1) : NULL;
		if (!text) {
			die("no keymap");
		}
		size_t size = strlen(text) + 1;
		int fd = memfd_create("wl-harness-keymap", MFD_CLOEXEC);
		if (fd < 0 || write(fd, text, size) != (ssize_t)size) {
			die("the keymap could not be written");
		}
		zwp_virtual_keyboard_v1_keymap(vk, WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1, fd, size);
		close(fd);
		state = xkb_state_new(keymap);
	} else {
		vp = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(pointer_manager, seat);
	}
	if (wl_display_roundtrip(display) < 0) {
		die("the compositor refused the virtual devices");
	}
	puts("READY");
	fflush(stdout);

	char line[256];
	while (fgets(line, sizeof line, stdin)) {
		unsigned x, y, w, h, code, pressed;
		double dx, dy;
		int steps;
		uint32_t time = now_ms();
		if (vp && sscanf(line, "abs %u %u %u %u", &x, &y, &w, &h) == 4) {
			zwlr_virtual_pointer_v1_motion_absolute(vp, time, x, y, w, h);
			zwlr_virtual_pointer_v1_frame(vp);
		} else if (vp && sscanf(line, "rel %lf %lf", &dx, &dy) == 2) {
			zwlr_virtual_pointer_v1_motion(vp, time, wl_fixed_from_double(dx), wl_fixed_from_double(dy));
			zwlr_virtual_pointer_v1_frame(vp);
		} else if (vp && sscanf(line, "btn %u %u", &code, &pressed) == 2) {
			zwlr_virtual_pointer_v1_button(vp, time, code, pressed);
			zwlr_virtual_pointer_v1_frame(vp);
		} else if (vp && sscanf(line, "axis %d", &steps) == 1) {
			zwlr_virtual_pointer_v1_axis_source(vp, WL_POINTER_AXIS_SOURCE_WHEEL);
			zwlr_virtual_pointer_v1_axis_discrete(vp, time, WL_POINTER_AXIS_VERTICAL_SCROLL,
				wl_fixed_from_int(15 * steps), steps);
			zwlr_virtual_pointer_v1_frame(vp);
		} else if (vk && sscanf(line, "key %u %u", &code, &pressed) == 2) {
			zwp_virtual_keyboard_v1_key(vk, time, code, pressed);
			// wlroots takes a virtual keyboard's modifier state from the client, not from its keys.
			xkb_state_update_key(state, code + 8, pressed ? XKB_KEY_DOWN : XKB_KEY_UP);
			zwp_virtual_keyboard_v1_modifiers(vk, xkb_state_serialize_mods(state, XKB_STATE_MODS_DEPRESSED),
				xkb_state_serialize_mods(state, XKB_STATE_MODS_LATCHED),
				xkb_state_serialize_mods(state, XKB_STATE_MODS_LOCKED),
				xkb_state_serialize_layout(state, XKB_STATE_LAYOUT_EFFECTIVE));
		} else {
			puts("ERR");
			fflush(stdout);
			continue;
		}
		if (wl_display_roundtrip(display) < 0) {
			die("the compositor is gone");
		}
		puts("OK");
		fflush(stdout);
	}
	return 0;
}

// ---- the output listener -----------------------------------------------------------------------------------

// It sends nothing after the bind and releases nothing: libwayland makes the head and mode objects as they
// are announced and drops their events.
static void outputs_head(void *d, struct zwlr_output_manager_v1 *m, struct zwlr_output_head_v1 *head) {}
static void outputs_done(void *d, struct zwlr_output_manager_v1 *m, uint32_t serial) {}
static void outputs_finished(void *d, struct zwlr_output_manager_v1 *m) {}

static const struct zwlr_output_manager_v1_listener outputs_listener = {
	.head = outputs_head,
	.done = outputs_done,
	.finished = outputs_finished,
};

static int run_outputs(void)
{
	if (!output_manager) {
		die("the compositor lacks zwlr_output_manager_v1");
	}
	zwlr_output_manager_v1_add_listener(output_manager, &outputs_listener, NULL);
	while (wl_display_dispatch(display) >= 0) {
	}
	return 0;
}

int main(int argc, char **argv)
{
	wants_lock = argc == 3 && !strcmp(argv[1], "window") && !strcmp(argv[2], "--lock");
	bool is_window = wants_lock || (argc == 2 && !strcmp(argv[1], "window"));
	bool is_input = argc == 3 && !strcmp(argv[1], "input") && (!strcmp(argv[2], "pointer") || !strcmp(argv[2], "keyboard"));
	wants_outputs = argc == 2 && !strcmp(argv[1], "outputs");
	if (!is_window && !is_input && !wants_outputs) {
		fprintf(stderr, "usage: wl-harness window [--lock] | wl-harness input pointer|keyboard | wl-harness outputs\n");
		return 2;
	}
	display = wl_display_connect(NULL);
	if (!display) {
		die("no Wayland display");
	}
	struct wl_registry *registry = wl_display_get_registry(display);
	wl_registry_add_listener(registry, &registry_listener, NULL);
	if (wl_display_roundtrip(display) < 0) {
		die("the registry did not answer");
	}
	if (wants_outputs) {
		return run_outputs();
	}
	return is_window ? run_window() : run_input(!strcmp(argv[2], "keyboard"));
}
