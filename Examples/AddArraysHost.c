void AddArrays(int *a, int *b, int *c, int num_elements) {
    for (int i = 0; i < num_elements; i++) {
        a[i] = b[i] + c[i];
    }
}
