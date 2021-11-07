#define BUF_SZ 100

void AddArrays(int *a, int *b, int *c, int num_elements) {
    for (int i = 0; i < num_elements; i++) {
        a[i] = b[i] + c[i];
    }
}

int main() {
    int a[BUF_SZ], b[BUF_SZ], c[BUF_SZ];

    for (int i = 0; i < BUF_SZ; i++) {
        a[i] = i;
        b[i] = BUF_SZ - i;
    }

    AddArrays(a, b, c, BUF_SZ);
}
