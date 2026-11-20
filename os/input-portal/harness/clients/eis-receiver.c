// Package 316's harness: an EIS receiver, the part Deskflow plays.
//
//   eis-receiver <fd>
//
// <fd> is the socket ConnectToEIS handed out. The receiver binds every capability a seat can have, whatever
// the seat offers, and prints one line per event: what a session really receives is what this prints.
#include <errno.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <libei.h>

static const enum ei_device_capability capabilities[] = {
	EI_DEVICE_CAP_POINTER, EI_DEVICE_CAP_POINTER_ABSOLUTE, EI_DEVICE_CAP_KEYBOARD,
	EI_DEVICE_CAP_TOUCH,   EI_DEVICE_CAP_SCROLL,           EI_DEVICE_CAP_BUTTON,
};
static const char *const capability_names[] = {"pointer", "pointer_absolute", "keyboard", "touch", "scroll", "button"};
#define CAPABILITIES (sizeof capabilities / sizeof capabilities[0])

int main(int argc, char **argv)
{
	if (argc != 2) {
		fprintf(stderr, "usage: eis-receiver <fd>\n");
		return 2;
	}
	setvbuf(stdout, NULL, _IOLBF, 0);
	struct ei *ei = ei_new_receiver(NULL);
	ei_configure_name(ei, "aresos-harness-receiver");
	if (ei_setup_backend_fd(ei, atoi(argv[1])) != 0) {
		printf("ERROR the socket was not accepted\n");
		return 2;
	}

	struct pollfd pfd = {.fd = ei_get_fd(ei), .events = POLLIN};
	for (;;) {
		if (poll(&pfd, 1, -1) < 0 && errno != EINTR) {
			printf("ERROR poll\n");
			return 2;
		}
		ei_dispatch(ei);
		struct ei_event *event;
		while ((event = ei_get_event(ei))) {
			struct ei_device *device = ei_event_get_device(event);
			const char *name = device ? ei_device_get_name(device) : "";
			switch (ei_event_get_type(event)) {
			case EI_EVENT_CONNECT:
				printf("CONNECT\n");
				break;
			case EI_EVENT_DISCONNECT:
				printf("DISCONNECT\n");
				return 0;
			case EI_EVENT_SEAT_ADDED: {
				struct ei_seat *seat = ei_event_get_seat(event);
				printf("SEAT name=%s", ei_seat_get_name(seat));
				for (size_t i = 0; i < CAPABILITIES; i++) {
					printf(" %s=%d", capability_names[i], ei_seat_has_capability(seat, capabilities[i]));
				}
				printf("\n");
				// Everything, also what the seat doesn't offer: a receiver that asks for more
				// than its session was granted must get nothing more.
				ei_seat_bind_capabilities(seat, EI_DEVICE_CAP_POINTER, EI_DEVICE_CAP_POINTER_ABSOLUTE,
					EI_DEVICE_CAP_KEYBOARD, EI_DEVICE_CAP_TOUCH, EI_DEVICE_CAP_SCROLL,
					EI_DEVICE_CAP_BUTTON, NULL);
				printf("BOUND everything\n");
				break;
			}
			case EI_EVENT_SEAT_REMOVED:
				printf("SEAT_REMOVED\n");
				break;
			case EI_EVENT_DEVICE_ADDED: {
				printf("DEVICE_ADDED name=%s", name);
				for (size_t i = 0; i < CAPABILITIES; i++) {
					printf(" %s=%d", capability_names[i], ei_device_has_capability(device, capabilities[i]));
				}
				struct ei_region *region;
				for (size_t i = 0; (region = ei_device_get_region(device, i)); i++) {
					printf(" region=%u,%u,%ux%u", ei_region_get_x(region), ei_region_get_y(region),
						ei_region_get_width(region), ei_region_get_height(region));
				}
				printf("\n");
				break;
			}
			case EI_EVENT_DEVICE_REMOVED:
				printf("DEVICE_REMOVED name=%s\n", name);
				break;
			case EI_EVENT_DEVICE_PAUSED:
				printf("DEVICE_PAUSED name=%s\n", name);
				break;
			case EI_EVENT_DEVICE_RESUMED:
				printf("DEVICE_RESUMED name=%s\n", name);
				break;
			case EI_EVENT_DEVICE_START_EMULATING:
				printf("START name=%s sequence=%u\n", name, ei_event_emulating_get_sequence(event));
				break;
			case EI_EVENT_DEVICE_STOP_EMULATING:
				printf("STOP name=%s\n", name);
				break;
			case EI_EVENT_FRAME:
				break;
			case EI_EVENT_POINTER_MOTION:
				printf("MOTION %.2f %.2f\n", ei_event_pointer_get_dx(event), ei_event_pointer_get_dy(event));
				break;
			case EI_EVENT_BUTTON_BUTTON:
				printf("BUTTON %u %d\n", ei_event_button_get_button(event), ei_event_button_get_is_press(event));
				break;
			case EI_EVENT_SCROLL_DELTA:
				printf("SCROLL %.2f %.2f\n", ei_event_scroll_get_dx(event), ei_event_scroll_get_dy(event));
				break;
			case EI_EVENT_SCROLL_DISCRETE:
				printf("SCROLL_DISCRETE %d %d\n", ei_event_scroll_get_discrete_dx(event),
					ei_event_scroll_get_discrete_dy(event));
				break;
			case EI_EVENT_SCROLL_STOP:
			case EI_EVENT_SCROLL_CANCEL:
				printf("SCROLL_STOP\n");
				break;
			case EI_EVENT_KEYBOARD_KEY:
				printf("KEY %u %d\n", ei_event_keyboard_get_key(event), ei_event_keyboard_get_key_is_press(event));
				break;
			case EI_EVENT_KEYBOARD_MODIFIERS:
				printf("MODIFIERS\n");
				break;
			default:
				printf("OTHER %d\n", (int)ei_event_get_type(event));
				break;
			}
			ei_event_unref(event);
		}
	}
}
