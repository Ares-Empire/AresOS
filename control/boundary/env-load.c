#include <stdio.h>
__attribute__((constructor)) static void planted_preload(void) {
    FILE *out = fopen("/home/assistant/work/preload-ran", "w");
    if (out) {
        fputs("LD_PRELOAD code executed\n", out);
        fclose(out);
    }
}
