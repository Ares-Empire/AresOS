#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>

/* Static linking matters: a dynamic launcher loads LD_PRELOAD before main().
 * This is an ordinary executable, never setuid; it keeps the caller's uid. */
int main(int argc, char **argv) {
    (void)argv;
    if (argc != 1 || getuid() != 10001 || geteuid() != 10001) {
        fputs("REFUSE: assistant uid 10001 and no command-line options required\n", stderr);
        return 78;
    }
    char *const env[] = {
        "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/home/assistant",
        "USER=assistant", "LOGNAME=assistant", "LANG=C.UTF-8",
        "TERM=xterm-256color", "DISABLE_AUTOUPDATER=1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1",
        "CLAUDE_CODE_AUTO_CONNECT_IDE=false", NULL
    };
    char *const args[] = {
        "/usr/bin/python3", "-I", "/opt/aresos-control/launch.py", NULL
    };
    /* No caller-supplied descriptor may carry an already-connected socket. */
    if (close_range(3, ~0U, 0) != 0) {
        perror("REFUSE: close_range");
        return 78;
    }
    execve(args[0], args, env);
    perror("REFUSE: execve");
    return 78;
}
