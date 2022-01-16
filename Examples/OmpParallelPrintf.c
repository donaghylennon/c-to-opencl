#define BUF_SZ 100

int main() {
    int a[BUF_SZ], b[BUF_SZ], c[BUF_SZ];
    for (int i = 0; i < BUF_SZ; i++) {
        a[i] = 1;
        b[i] = 2;
    }

    #pragma omp parallel
    {
        int num_threads = omp_get_num_threads();
        int thread_id = omp_get_thread_num();
        int thread_work = BUF_SZ / num_threads;
        int offset = thread_id * thread_work;
        if (thread_id == num_threads - 1)
            thread_work += BUF_SZ % num_threads;
        for (int i = 0; i < thread_work; i++) {
            c[offset + i] = a[offset + i] + b[offset + i];
        }
    }

//    for (int i = 0; i < BUF_SZ; i++) {
//        printf("%i: %i\n", i, c[i]);
//    }
}