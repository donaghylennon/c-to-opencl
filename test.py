import os
import subprocess
import sys
import matplotlib.pyplot as plt


def main(do_compile, run, translate):
    inputs_path = "Tests/src/Inputs/"
    outputs_path = "Tests/src/Outputs/"
    bin_inputs_path = "Tests/bin/Inputs/"
    bin_outputs_path = "Tests/bin/Outputs/"
    files = os.listdir(inputs_path)
    in_paths = []
    bin_in_paths = []
    out_paths = []
    bin_out_paths = []

    for file in files:
        in_path = inputs_path + file
        in_paths.append(in_path)
        bin_in_paths.append(bin_inputs_path + file[:-2])
        out_path = outputs_path + file
        out_paths.append(out_path)
        bin_out_paths.append(bin_outputs_path + file[:-2])
        cl_path = out_path + "l"
        if translate:
            #p = subprocess.run(["python", "src/c-to-opencl/__main__.py",  in_path, out_path, cl_path])
            p = subprocess.run(["python", "-m", "c-to-opencl",  in_path, out_path, cl_path])

    if do_compile:
        for in_path, bin_in_path in zip(in_paths, bin_in_paths):
            p = subprocess.run(["gcc", "-fopenmp", in_path, "-o", bin_in_path])

        for out_path, bin_out_path in zip(out_paths, bin_out_paths):
            p = subprocess.run(["gcc", "-fopenmp", "-lOpenCL", out_path, "-o", bin_out_path])

    if run:
        failed = False
        for bin_in_path, bin_out_path in zip(bin_in_paths, bin_out_paths):
            in_p = subprocess.run([bin_in_path, "10", "print"], capture_output=True)
            out_p = subprocess.run([bin_out_path, "10", "print"], capture_output=True)

            if in_p.stdout != out_p.stdout:
                failed = True
                print(f"Failed test:\n{bin_in_path}:\n{in_p.stdout}\n\n{bin_out_path}:\n{out_p.stdout}\n\n")
            else:
                print(f"Passed test:\n{bin_in_path}\n{bin_out_path}\n")
                print(in_p.stdout)
        if not failed:
            print("\n\nPassed all tests")
        else:
            print("\n\nFailed one or more tests")

        averages_in = {}
        averages_out = {}
        for bin_in_path, bin_out_path, file in zip(bin_in_paths, bin_out_paths, files):
            averages_in[file] = {}
            averages_out[file] = {}
            for size in ["10", "100", "1000", "10000", "100000"]:
            # for time in ["10", "1000", "100000", "10000000"]:
                in_times = []
                out_times = []
                for _ in range(100):
                    in_p = subprocess.run([bin_in_path, size, "time"], capture_output=True)
                    out_p = subprocess.run([bin_out_path, size, "time"], capture_output=True)

                    in_times.append(int(in_p.stdout.decode('utf-8')))
                    out_times.append(int(out_p.stdout.decode('utf-8')))
                averages_in[file][size] = sum(in_times) / len(in_times)
                averages_out[file][size] = sum(out_times) / len(out_times)

        print(f"{averages_in=}")
        print(f"{averages_out=}")
        for file in files:
            sizes_in = averages_in[file].keys()
            sizes_out = averages_out[file].keys()
            times_in = [averages_in[file][k] for k in sizes_in]
            times_out = [averages_out[file][k] for k in sizes_out]

            fig, ax = plt.subplots()
            ax.plot(sizes_in, times_in, 'blue', marker='o', label='input version')
            ax.plot(sizes_out, times_out, 'red', marker='o', label='translated version')
            ax.legend()
            ax.set_ylabel("Execution time (microseconds)")
            ax.set_xlabel("Array size")
            fig.savefig(f"{file[:-2]}.pdf")


if __name__ == "__main__":
    translate = False
    do_compile = False
    run = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "compile":
            do_compile = True
        elif sys.argv[1] == "run":
            run = True
        elif sys.argv[1] == "translate":
            translate = True
    main(do_compile, run, translate)
