#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <logfile>\n", argv[0]);
        return 1;
    }

    // Developer "fix" that over-elevates: sets REAL uid to root too,
    // so the invoked shell no longer sees a privilege mismatch and keeps root.
    setuid(0);

    char command[256];
    // VULNERABILITY: user input concatenated directly into a shell command
    snprintf(command, sizeof(command), "cat /var/log/app/%s", argv[1]);
    system(command);

    return 0;
}
