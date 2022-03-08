from tricl.translate import KernelInfo, TranslationVisitor
from pycparser import c_ast


def generate_host_function(kernel_info: KernelInfo, kernel_path: str) -> str:
    visitor = TranslationVisitor()
    with open("host_function.c.template", "r") as f:
        template = f.read()

    template = template.replace("<KERNEL NAME>", f'"{kernel_info.name}"')
    template = template.replace("<SOURCE FILEPATH>", f'"{kernel_path}"')

    buffer_decls = []
    create_buffers = []
    write_buffers = []
    read_buffers = []
    release_buffers = []
    set_kernel_args = []

    for i, arg in enumerate(kernel_info.args):
        if type(arg.type) is c_ast.PtrDecl:
            tp = visitor.generate_argument_type(arg.type.type)
            buffer_decls.append(f"cl_mem {arg.name}_cl;")
            create_buffers.append(f"{arg.name}_cl = clCreateBuffer(context, CL_MEM_READ_WRITE, "
                                  f"{arg.size}, NULL, &err);\n"
                                  "    if (err != CL_SUCCESS) {\n"
                                  "        fprintf(stderr, \"OpenCL Error: Failed to create buffer. %d\\n\", err);\n"
                                  "        exit(EXIT_FAILURE);\n"
                                  "    }\n")
            write_buffers.append(f"err = clEnqueueWriteBuffer(command_queue, {arg.name}_cl, CL_TRUE,"
                                 f" 0, {arg.size}, {arg.name}, 0, NULL, NULL);\n"
                                 "    if (err != CL_SUCCESS) {\n"
                                 "        fprintf(stderr, \"OpenCL Error: Failed to write to buffer. %d\\n\", err);\n"
                                 "        exit(EXIT_FAILURE);\n"
                                 "    }\n")
            read_buffers.append(f"err = clEnqueueReadBuffer(command_queue, {arg.name}_cl, CL_TRUE, "
                                f"0, {arg.size}, {arg.name}, 0, NULL, NULL);\n"
                                "    if (err != CL_SUCCESS) {\n"
                                "        fprintf(stderr, \"OpenCL Error: Failed to read from buffer. %d\\n\", err);\n"
                                "        exit(EXIT_FAILURE);\n"
                                "    }\n")
            release_buffers.append(f"err = clReleaseMemObject({arg.name}_cl);\n"
                                   "    if (err != CL_SUCCESS) {\n"
                                   "        fprintf(stderr, \"OpenCL Error: Failed to release buffer. %d\\n\", err);\n"
                                   "        exit(EXIT_FAILURE);\n"
                                   "    }\n")
            set_kernel_args.append(f"err = clSetKernelArg(kernel, {i}, sizeof(cl_mem), "
                                   f"&{arg.name}_cl);\n"
                                   "    if (err != CL_SUCCESS) {\n"
                                   "        fprintf(stderr, \"OpenCL Error: Failed to set kernel argument. %d\\n\", "
                                   "err);\n"
                                   "        exit(EXIT_FAILURE);\n"
                                   "    }\n")
        else:
            tp = visitor.generate_argument_type(arg.type)
            set_kernel_args.append(f"err = clSetKernelArg(kernel, {i}, sizeof({tp}), &{arg.name});\n"
                                   "    if (err != CL_SUCCESS) {\n"
                                   "        fprintf(stderr, \"OpenCL Error: Failed to set kernel argument. %d\\n\", "
                                   "err);\n"
                                   "        exit(EXIT_FAILURE);\n"
                                   "    }\n")

    template = template.replace("<INPUT BUFFERS>", "\n    ".join(buffer_decls))
    template = template.replace("<CREATE BUFFERS>", "\n    ".join(create_buffers))
    template = template.replace("<WRITE BUFFERS>", "\n    ".join(write_buffers))
    template = template.replace("<SET KERNEL ARGUMENTS>", "\n    ".join(set_kernel_args))
    template = template.replace("<READ BUFFERS>", "\n    ".join(read_buffers))
    template = template.replace("<RELEASE BUFFERS>", "\n    ".join(release_buffers))

    return template


def generate_host_functions(kernels_info: list[KernelInfo], kernel_path: str) -> (list[str], list[str], list[str]):
    visitor = TranslationVisitor()
    functions = []
    calls = []
    decls = []
    for kernel_info in kernels_info:
        func = f"void {kernel_info.name}(int domain_size, "
        call = f"{kernel_info.name}({kernel_info.domain_size}, "

        pointer_derefs = []
        pointer_writes = []

        first = True
        for arg in kernel_info.args:
            if first:
                sep = ""
                first = False
            else:
                sep = ", "
            if type(arg.type) is c_ast.PtrDecl:
                func += sep + f"{visitor.visit(arg.type)} {arg.name}"
                call += sep + f"{arg.name}"
            else:
                tp = visitor.visit(arg.type)
                func += sep + f"{tp} * p_{arg.name}"
                call += sep + f"&{arg.name}"
                pointer_derefs.append(f"{tp} {arg.name} = *p_{arg.name};")
                pointer_writes.append(f"*p_{arg.name} = {arg.name};")
        decl = func + ");\n"
        func += ") {\n    "
        func += ("\n    ".join(pointer_derefs) + "\n") if pointer_derefs else ""
        func += generate_host_function(kernel_info, kernel_path)
        func += ("\n    " + "\n    ".join(pointer_writes) + "\n") if pointer_writes else ""
        func += "}\n"
        functions.append(func)

        call += ");\n"
        calls.append(call)
        decls.append(decl)

    return functions, calls, decls


def process_original_file(file: str, kernels_info: list[KernelInfo], kernel_path: str) -> str:
    functions, calls, decls = generate_host_functions(kernels_info, kernel_path)
    with open(file, "r") as f:
        lines = f.readlines()
    gaps = []
    included = [False for _ in kernels_info]
    for k, ki in enumerate(kernels_info):
        start = ki.src_start_line + 1
        num_open_braces = 0
        ended = False
        end = -1
        for i, line in enumerate(lines[start:]):
            for char in line:
                if char == "{":
                    num_open_braces += 1
                elif char == "}":
                    num_open_braces -= 1
                if num_open_braces == -1:
                    end = start + i
                    ended = True
                    break
            if ended:
                break
        gaps.append((k, ki.src_start_line-1, end))

    new_lines = []
    for i, line in enumerate(lines):
        if i == 0:
            new_lines.append("#include <CL/cl.h>\n")
        if line.find("main(") >= 0:
            new_lines.append("".join(decls) + "\n")
        ignored = False
        for j, gap in enumerate(gaps):
            k, start, end = gap
            if start-1 <= i <= end:
                ignored = True
                if not included[k]:
                    new_lines.append("    " + calls[k])
                    included[k] = True
        if not ignored:
            new_lines.append(line)

    return "".join(new_lines) + "".join(functions)
