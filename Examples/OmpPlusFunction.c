#define BUF_SZ 100

int add(int a, int b);

int main() {
    int a[BUF_SZ], b[BUF_SZ], c[BUF_SZ];
    for (int i = 0; i < BUF_SZ; i++) {
        a[i] = 1;
        b[i] = 2;
    }

    #pragma omp parallel for
    for (int i = 0; i < BUF_SZ; i++) {
        c[i] = add(a[i], b[i]);
    }

//    for (int i = 0; i < BUF_SZ; i++) {
//        printf("%i: %i\n", i, c[i]);
//    }
}

int add(int a, int b) {
    return a + b;
}
