#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc < 2 || argc > 3) {
        printf("%s: invalid arguments\n", argv[0]);
        exit(1);
    }
    int print_or_time = 0;
    if (argc == 3) {
        if (strcmp(argv[2], "print") == 0)
            print_or_time = 1;
        else if (strcmp(argv[2], "time") == 0)
            print_or_time = 0;
    }
    struct timeval start, end;
    int size = atoi(argv[1]);
    long *a = malloc(size*sizeof(long));

    gettimeofday(&start, NULL);

#pragma omp parallel for
    for (int i = 0; i < size; i++) {
        long acc = 1;
        for (int j = 1; j <= i; j++)
            acc *= j;
        a[i] = acc;
    }

    gettimeofday(&end, NULL);

    if (print_or_time) {
        for (int i = 0; i < size; i++) {
            printf("%i: %li\n", i, a[i]);
        }
    } else {
        long long total_time = (end.tv_sec-start.tv_sec)*1000000 + end.tv_usec-start.tv_usec;
        printf("%lli\n", total_time);
    }
}
