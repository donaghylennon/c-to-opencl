__kernel void AddArrays(__global int *a, __global int *b, __global int *c, int num_elements) {
    int i = get_global_id(0);

    if (i >= num_elements)
        return;

    a[i] = b[i] + c[i];
}
