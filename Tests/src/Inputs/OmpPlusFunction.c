#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <string.h>

int add(int a, int b);

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
    int *a = malloc(size*sizeof(int));
    int *b = malloc(size*sizeof(int));
    int *c = malloc(size*sizeof(int));
    for (int i = 0; i < size; i++) {
        a[i] = 1;
        b[i] = 2;
    }

    gettimeofday(&start, NULL);

    #pragma omp parallel for
    for (int i = 0; i < size; i++) {
        c[i] = add(a[i], b[i]);
    }

    gettimeofday(&end, NULL);

    if (print_or_time) {
        for (int i = 0; i < size; i++) {
            printf("%i: %i\n", i, c[i]);
        }
    } else {
        long long total_time = (end.tv_sec-start.tv_sec)*1000000 + end.tv_usec-start.tv_usec;
        printf("%lli\n", total_time);
    }
}

int add(int a, int b) {
    return a + b;
}
