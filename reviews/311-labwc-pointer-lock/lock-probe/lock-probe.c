// Package 311's behaviour proof: a Wayland client that asks a headless labwc for
// pointer locks and confinement, on a layer-shell surface or on a normal window.
//
//   lock-probe layer|window
//
// It drives the pointer itself through zwlr_virtual_pointer_v1 and prints one
// line per check. Exit 0 when every check passed, 1 when one failed, 2 when the
// compositor could not be used at all (nothing was tested).
#define _GNU_SOURCE
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>
#include "pointer-constraints-unstable-v1-client-protocol.h"
#include "relative-pointer-unstable-v1-client-protocol.h"
#include "wlr-layer-shell-unstable-v1-client-protocol.h"
#include "wlr-virtual-pointer-unstable-v1-client-protocol.h"
#include "xdg-shell-client-protocol.h"

#define WINDOW_WIDTH 400
#define WINDOW_HEIGHT 300
#define OUTPUT_WIDTH 1280
#define OUTPUT_HEIGHT 720
#define NEAR(a, b) (fabs((a) - (b)) < 0.01)

static struct wl_display *display;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct wl_seat *seat;
static struct wl_pointer *pointer;
static struct zwlr_layer_shell_v1 *layer_shell;
static struct xdg_wm_base *wm_base;
static struct zwp_pointer_constraints_v1 *constraints;
static struct zwp_relative_pointer_manager_v1 *relative_manager;
static struct zwlr_virtual_pointer_manager_v1 *virtual_manager;
static struct zwlr_virtual_pointer_v1 *virtual_pointer;
static struct wl_surface *surface;

static bool has_pointer, configured, entered, locked, unlocked, confined;
static uint32_t surface_width, surface_height;
static double pointer_x, pointer_y;
static int motion_events, relative_events;
static double relative_dx, relative_dy;
static uint32_t clock_ms = 1;
static int failures;

static void check(bool ok, const char *what)
{
	printf("%s %s\n", ok ? "PASS" : "FAIL", what);
	fflush(stdout);
	if (!ok) {
		failures++;
	}
}

static void give_up(const char *why)
{
	printf("UNUSABLE %s\n", why);
	exit(2);
}

static void sync_with_compositor(void)
{
	// Two trips: the first lets labwc handle our requests, the second delivers
	// whatever it sent back while handling them.
	if (wl_display_roundtrip(display) < 0 || wl_display_roundtrip(display) < 0) {
		// Not a lock result: a run that ends here proves nothing either way.
		printf("UNUSABLE the compositor closed the connection (error %d)\n", wl_display_get_error(display));
		exit(2);
	}
}

static void wait_for(const bool *flag)
{
	for (int i = 0; i < 50 && !*flag; i++) {
		sync_with_compositor();
		if (!*flag) {
			usleep(20000);
		}
	}
}

static void move_by(double dx, double dy)
{
	zwlr_virtual_pointer_v1_motion(virtual_pointer, clock_ms++, wl_fixed_from_double(dx), wl_fixed_from_double(dy));
	zwlr_virtual_pointer_v1_frame(virtual_pointer);
	sync_with_compositor();
}

static void move_to(uint32_t x, uint32_t y)
{
	zwlr_virtual_pointer_v1_motion_absolute(virtual_pointer, clock_ms++, x, y, OUTPUT_WIDTH, OUTPUT_HEIGHT);
	zwlr_virtual_pointer_v1_frame(virtual_pointer);
	sync_with_compositor();
}

static void pointer_enter(void *data, struct wl_pointer *p, uint32_t serial, struct wl_surface *s, wl_fixed_t x,
		wl_fixed_t y)
{
	entered = s == surface;
	pointer_x = wl_fixed_to_double(x);
	pointer_y = wl_fixed_to_double(y);
}

static void pointer_leave(void *data, struct wl_pointer *p, uint32_t serial, struct wl_surface *s)
{
	entered = false;
}

static void pointer_motion(void *data, struct wl_pointer *p, uint32_t time, wl_fixed_t x, wl_fixed_t y)
{
	motion_events++;
	pointer_x = wl_fixed_to_double(x);
	pointer_y = wl_fixed_to_double(y);
}

static void pointer_button(void *d, struct wl_pointer *p, uint32_t s, uint32_t t, uint32_t b, uint32_t st) {}
static void pointer_axis(void *d, struct wl_pointer *p, uint32_t t, uint32_t a, wl_fixed_t v) {}
static void pointer_frame(void *d, struct wl_pointer *p) {}
static void pointer_axis_source(void *d, struct wl_pointer *p, uint32_t s) {}
static void pointer_axis_stop(void *d, struct wl_pointer *p, uint32_t t, uint32_t a) {}
static void pointer_axis_discrete(void *d, struct wl_pointer *p, uint32_t a, int32_t v) {}

static const struct wl_pointer_listener pointer_listener = {
	.enter = pointer_enter, .leave = pointer_leave, .motion = pointer_motion, .button = pointer_button,
	.axis = pointer_axis, .frame = pointer_frame, .axis_source = pointer_axis_source,
	.axis_stop = pointer_axis_stop, .axis_discrete = pointer_axis_discrete,
};

static void relative_motion(void *data, struct zwp_relative_pointer_v1 *r, uint32_t hi, uint32_t lo, wl_fixed_t dx,
		wl_fixed_t dy, wl_fixed_t dx_unaccel, wl_fixed_t dy_unaccel)
{
	relative_events++;
	relative_dx += wl_fixed_to_double(dx_unaccel);
	relative_dy += wl_fixed_to_double(dy_unaccel);
}

static const struct zwp_relative_pointer_v1_listener relative_listener = {.relative_motion = relative_motion};

static void lock_locked(void *d, struct zwp_locked_pointer_v1 *l) { locked = true; }
static void lock_unlocked(void *d, struct zwp_locked_pointer_v1 *l) { unlocked = true; }
static const struct zwp_locked_pointer_v1_listener lock_listener = {.locked = lock_locked, .unlocked = lock_unlocked};

static void confine_confined(void *d, struct zwp_confined_pointer_v1 *c) { confined = true; }
static void confine_unconfined(void *d, struct zwp_confined_pointer_v1 *c) { confined = false; }
static const struct zwp_confined_pointer_v1_listener confine_listener = {
	.confined = confine_confined, .unconfined = confine_unconfined,
};

static void attach_buffer(uint32_t width, uint32_t height)
{
	uint32_t stride = width * 4, size = stride * height;
	int fd = memfd_create("lock-probe", MFD_CLOEXEC);
	if (fd < 0 || ftruncate(fd, size) < 0) {
		give_up("no shared memory for the buffer");
	}
	void *pixels = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
	if (pixels == MAP_FAILED) {
		give_up("cannot map the buffer");
	}
	memset(pixels, 0x80, size);
	munmap(pixels, size);
	struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
	struct wl_buffer *buffer = wl_shm_pool_create_buffer(pool, 0, width, height, stride, WL_SHM_FORMAT_XRGB8888);
	wl_shm_pool_destroy(pool);
	close(fd);
	wl_surface_attach(surface, buffer, 0, 0);
	wl_surface_damage_buffer(surface, 0, 0, width, height);
	wl_surface_commit(surface);
}

static void layer_configure(void *d, struct zwlr_layer_surface_v1 *l, uint32_t serial, uint32_t width, uint32_t height)
{
	zwlr_layer_surface_v1_ack_configure(l, serial);
	surface_width = width;
	surface_height = height;
	if (!configured) {
		attach_buffer(width, height);
	}
	configured = true;
}

static void layer_closed(void *d, struct zwlr_layer_surface_v1 *l) { give_up("the layer surface was closed"); }
static const struct zwlr_layer_surface_v1_listener layer_listener = {.configure = layer_configure, .closed = layer_closed};

static void wm_ping(void *d, struct xdg_wm_base *b, uint32_t serial) { xdg_wm_base_pong(b, serial); }
static const struct xdg_wm_base_listener wm_listener = {.ping = wm_ping};

static void xdg_configure(void *d, struct xdg_surface *x, uint32_t serial)
{
	xdg_surface_ack_configure(x, serial);
	if (!configured) {
		surface_width = WINDOW_WIDTH;
		surface_height = WINDOW_HEIGHT;
		attach_buffer(WINDOW_WIDTH, WINDOW_HEIGHT);
	}
	configured = true;
}

static const struct xdg_surface_listener xdg_listener = {.configure = xdg_configure};

static void toplevel_configure(void *d, struct xdg_toplevel *t, int32_t w, int32_t h, struct wl_array *s) {}
static void toplevel_close(void *d, struct xdg_toplevel *t) {}
static void toplevel_bounds(void *d, struct xdg_toplevel *t, int32_t w, int32_t h) {}
static void toplevel_caps(void *d, struct xdg_toplevel *t, struct wl_array *c) {}
static const struct xdg_toplevel_listener toplevel_listener = {
	.configure = toplevel_configure, .close = toplevel_close, .configure_bounds = toplevel_bounds,
	.wm_capabilities = toplevel_caps,
};

static void seat_capabilities(void *d, struct wl_seat *s, uint32_t capabilities)
{
	has_pointer = capabilities & WL_SEAT_CAPABILITY_POINTER;
}

static void seat_name(void *d, struct wl_seat *s, const char *name) {}
static const struct wl_seat_listener seat_listener = {.capabilities = seat_capabilities, .name = seat_name};

static void registry_global(void *d, struct wl_registry *r, uint32_t name, const char *interface, uint32_t version)
{
	if (!strcmp(interface, wl_compositor_interface.name)) {
		compositor = wl_registry_bind(r, name, &wl_compositor_interface, 4);
	} else if (!strcmp(interface, wl_shm_interface.name)) {
		shm = wl_registry_bind(r, name, &wl_shm_interface, 1);
	} else if (!strcmp(interface, wl_seat_interface.name)) {
		seat = wl_registry_bind(r, name, &wl_seat_interface, 5);
	} else if (!strcmp(interface, zwlr_layer_shell_v1_interface.name)) {
		layer_shell = wl_registry_bind(r, name, &zwlr_layer_shell_v1_interface, 1);
	} else if (!strcmp(interface, xdg_wm_base_interface.name)) {
		wm_base = wl_registry_bind(r, name, &xdg_wm_base_interface, 1);
	} else if (!strcmp(interface, zwp_pointer_constraints_v1_interface.name)) {
		constraints = wl_registry_bind(r, name, &zwp_pointer_constraints_v1_interface, 1);
	} else if (!strcmp(interface, zwp_relative_pointer_manager_v1_interface.name)) {
		relative_manager = wl_registry_bind(r, name, &zwp_relative_pointer_manager_v1_interface, 1);
	} else if (!strcmp(interface, zwlr_virtual_pointer_manager_v1_interface.name)) {
		virtual_manager = wl_registry_bind(r, name, &zwlr_virtual_pointer_manager_v1_interface, 1);
	}
}

static void registry_remove(void *d, struct wl_registry *r, uint32_t name) {}
static const struct wl_registry_listener registry_listener = {.global = registry_global, .global_remove = registry_remove};

static void make_surface(bool layer)
{
	surface = wl_compositor_create_surface(compositor);
	if (layer) {
		struct zwlr_layer_surface_v1 *l = zwlr_layer_shell_v1_get_layer_surface(layer_shell, surface, NULL,
			ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, "lock-probe");
		zwlr_layer_surface_v1_add_listener(l, &layer_listener, NULL);
		zwlr_layer_surface_v1_set_anchor(l, ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM
			| ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT | ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);
		zwlr_layer_surface_v1_set_size(l, 0, 0);
		// Input capture takes the keyboard too: this is what gives the surface focus.
		zwlr_layer_surface_v1_set_keyboard_interactivity(l, ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_EXCLUSIVE);
	} else {
		xdg_wm_base_add_listener(wm_base, &wm_listener, NULL);
		struct xdg_surface *x = xdg_wm_base_get_xdg_surface(wm_base, surface);
		xdg_surface_add_listener(x, &xdg_listener, NULL);
		struct xdg_toplevel *t = xdg_surface_get_toplevel(x);
		xdg_toplevel_add_listener(t, &toplevel_listener, NULL);
		xdg_toplevel_set_title(t, "lock-probe");
	}
	wl_surface_commit(surface);
	wait_for(&configured);
	if (!configured) {
		give_up("the surface was never configured");
	}
}

// Finds the surface with the pointer, then centres the pointer on it.
static void enter_surface(void)
{
	for (uint32_t y = 20; y < OUTPUT_HEIGHT && !entered; y += 40) {
		for (uint32_t x = 20; x < OUTPUT_WIDTH && !entered; x += 40) {
			move_to(x, y);
		}
	}
	if (!entered) {
		give_up("the pointer never entered the surface");
	}
	move_by(surface_width / 2.0 - pointer_x, surface_height / 2.0 - pointer_y);
}

static void lock_phase(void)
{
	double start_x = pointer_x, start_y = pointer_y;
	struct zwp_relative_pointer_v1 *relative =
		zwp_relative_pointer_manager_v1_get_relative_pointer(relative_manager, pointer);
	zwp_relative_pointer_v1_add_listener(relative, &relative_listener, NULL);

	struct zwp_locked_pointer_v1 *lock = zwp_pointer_constraints_v1_lock_pointer(constraints, surface, pointer, NULL,
		ZWP_POINTER_CONSTRAINTS_V1_LIFETIME_PERSISTENT);
	zwp_locked_pointer_v1_add_listener(lock, &lock_listener, NULL);
	wl_surface_commit(surface);
	wait_for(&locked);
	check(locked, "the compositor activated the pointer lock");

	motion_events = relative_events = 0;
	relative_dx = relative_dy = 0;
	for (int i = 0; i < 20; i++) {
		move_by(10, 5);
	}
	printf("INFO while locked: %d relative events (%.2f, %.2f), %d absolute motion events\n", relative_events,
		relative_dx, relative_dy, motion_events);
	check(relative_events == 20 && NEAR(relative_dx, 200) && NEAR(relative_dy, 100),
		"relative motion arrived in full while locked");
	check(motion_events == 0, "no absolute motion reached the surface while locked");

	zwp_locked_pointer_v1_destroy(lock);
	sync_with_compositor();
	move_by(3, 2);
	printf("INFO after unlock: pointer at (%.2f, %.2f), started at (%.2f, %.2f)\n", pointer_x, pointer_y, start_x,
		start_y);
	check(NEAR(pointer_x, start_x + 3) && NEAR(pointer_y, start_y + 2), "the cursor stayed still during the lock");

	// The cursor hint: on unlock the cursor goes where the client asked (warp_cursor_to_constraint_hint).
	double hint_x = pointer_x + 40, hint_y = pointer_y + 30;
	locked = false;
	lock = zwp_pointer_constraints_v1_lock_pointer(constraints, surface, pointer, NULL,
		ZWP_POINTER_CONSTRAINTS_V1_LIFETIME_PERSISTENT);
	zwp_locked_pointer_v1_add_listener(lock, &lock_listener, NULL);
	wl_surface_commit(surface);
	wait_for(&locked);
	check(locked, "a second lock was activated");
	zwp_locked_pointer_v1_set_cursor_position_hint(lock, wl_fixed_from_double(hint_x), wl_fixed_from_double(hint_y));
	wl_surface_commit(surface);
	sync_with_compositor();
	zwp_locked_pointer_v1_destroy(lock);
	sync_with_compositor();
	move_by(1, 1);
	printf("INFO after hinted unlock: pointer at (%.2f, %.2f), hint was (%.2f, %.2f)\n", pointer_x, pointer_y, hint_x,
		hint_y);
	check(NEAR(pointer_x, hint_x + 1) && NEAR(pointer_y, hint_y + 1), "unlocking moved the cursor to the hint");
	zwp_relative_pointer_v1_destroy(relative);
}

static void confine_phase(void)
{
	int left = (int)pointer_x - 20, top = (int)pointer_y - 20;
	struct wl_region *region = wl_compositor_create_region(compositor);
	wl_region_add(region, left, top, 40, 40);
	struct zwp_confined_pointer_v1 *confine = zwp_pointer_constraints_v1_confine_pointer(constraints, surface, pointer,
		region, ZWP_POINTER_CONSTRAINTS_V1_LIFETIME_PERSISTENT);
	zwp_confined_pointer_v1_add_listener(confine, &confine_listener, NULL);
	wl_region_destroy(region);
	wl_surface_commit(surface);
	wait_for(&confined);
	check(confined, "the compositor activated the confinement");
	double before_x = pointer_x;
	for (int i = 0; i < 10; i++) {
		move_by(15, 15);
	}
	printf("INFO while confined: pointer at (%.2f, %.2f), region x %d..%d y %d..%d\n", pointer_x, pointer_y, left,
		left + 40, top, top + 40);
	check(pointer_x > before_x && pointer_x <= left + 40 && pointer_y <= top + 40,
		"the pointer moved inside the region and stopped at its edge");
	zwp_confined_pointer_v1_destroy(confine);
	sync_with_compositor();
}

int main(int argc, char **argv)
{
	if (argc != 2 || (strcmp(argv[1], "layer") && strcmp(argv[1], "window"))) {
		fprintf(stderr, "usage: lock-probe layer|window\n");
		return 2;
	}
	bool layer = !strcmp(argv[1], "layer");
	display = wl_display_connect(NULL);
	if (!display) {
		give_up("no Wayland display");
	}
	struct wl_registry *registry = wl_display_get_registry(display);
	wl_registry_add_listener(registry, &registry_listener, NULL);
	wl_display_roundtrip(display);
	if (!compositor || !shm || !seat || !layer_shell || !wm_base || !constraints || !relative_manager
			|| !virtual_manager) {
		give_up("the compositor lacks a protocol this probe needs");
	}
	// A headless seat has no pointer until the virtual one exists.
	wl_seat_add_listener(seat, &seat_listener, NULL);
	virtual_pointer = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(virtual_manager, seat);
	wait_for(&has_pointer);
	if (!has_pointer) {
		give_up("the seat never gained a pointer");
	}
	pointer = wl_seat_get_pointer(seat);
	wl_pointer_add_listener(pointer, &pointer_listener, NULL);
	sync_with_compositor();

	printf("MODE %s\n", argv[1]);
	make_surface(layer);
	sync_with_compositor();
	enter_surface();
	lock_phase();
	confine_phase();
	printf("RESULT %s %s\n", argv[1], failures ? "FAILED" : "PASSED");
	wl_display_disconnect(display);
	return failures ? 1 : 0;
}
