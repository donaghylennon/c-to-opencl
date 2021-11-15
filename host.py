from enum import Enum, auto
from pycparser import c_ast


class HostDetails:
    __slots__ = 'global_domain_sz', 'buffers', 'kernel_args'

    def __init__(self, global_domain_sz, buffers, kernel_args):
        self.global_domain_sz = global_domain_sz
        self.buffers = buffers
        self.kernel_args = kernel_args

    @staticmethod
    def from_ast(ast):
        buffers = []
        kernel_args = []

        # Assume first external declaration in file is function to be translated
        func_def = ast.ext[0]
        func_name = func_def.decl.name
        for param in func_def.decl.type.args:
            if is_buffer(param):
                buffers.append(param.name)

        # Assume second external declaration in file is main function
        main_func = ast.ext[1]
        for stmt in main_func.body.block_items:
            if type(stmt) == c_ast.FuncCall and stmt.name.name == func_name:
                func_call = stmt
                break

        for arg in func_call.args.exprs:
            if type(arg) == c_ast.Constant:
                arg_type = ArgType.CONSTANT
                input_var = arg.value
                buffer_size = None
            else:
                input_var = arg.name
                for stmt in main_func.body.block_items:
                    if type(stmt) == c_ast.Decl and stmt.name == arg.name:
                        if type(stmt.type) == c_ast.ArrayDecl:
                            arg_type = ArgType.BUFFER
                            buffer_size = stmt.type.dim.value
                            # can retrieve the type of the buffer here, but assume int for now
                        else:
                            arg_type = ArgType.SCALAR
                            buffer_size = None

            kernel_args.append(KernelArg(arg_type, input_var, buffer_size))

        # assume first buffer's size is domain size for now
        global_domain_sz = kernel_args[0].buffer_size

        return HostDetails(global_domain_sz, buffers, kernel_args)

    def generate_code(self):
        assign_constants = ""
        buffer_decls = ""
        create_buffers = ""
        write_to_buffers = ""
        set_kernel_args = ""
        read_from_buffers = ""
        release_buffers = ""
        constant_index = 0

        with open('opencl_host.template', 'r') as f:
            output = f.read()

        output = output.replace('<GLOBAL DOMAIN SIZE>', self.global_domain_sz)

        for i, arg in enumerate(self.kernel_args):
            if arg.argument_type == ArgType.BUFFER:
                buffer_decls += f"cl_mem {arg.input_var}_clbuffer;\n\t"
                create_buffers += f"{arg.input_var}_clbuffer = clCreateBuffer(context, CL_MEM_READ_WRITE, {arg.buffer_size}*sizeof(int), NULL, &err);\n\t"
                write_to_buffers += f"err = clEnqueueWriteBuffer(command_queue, {arg.input_var}_clbuffer, CL_TRUE, 0, {arg.buffer_size}*sizeof(int), {arg.input_var}, 0, NULL, NULL);\n\t"
                set_kernel_args += f"err = clSetKernelArg(kernel, {i}, sizeof(cl_mem), &{arg.input_var});\n\t"
                read_from_buffers += f"err = clEnqueueReadBuffer(command_queue, {arg.input_var}_clbuffer, CL_TRUE, 0, {arg.buffer_size}*sizeof(int), {arg.input_var}, 0, NULL, NULL);\n\t"
                release_buffers += f"err = clReleaseMemObject({arg.input_var}_clbuffer);\n\t"
            elif arg.argument_type == ArgType.SCALAR:
                set_kernel_args += f"err = clSetKernelArg(kernel, {i}, sizeof(int), &{arg.input_var});\n\t"
            elif arg.argument_type == ArgType.CONSTANT:
                var_name = f"CONSTANT{constant_index}"
                constant_index += 1
                assign_constants += f"int {var_name} = {arg.input_var};\n\t"
                set_kernel_args += f"err = clSetKernelArg(kernel, {i}, sizeof(int), &{var_name});\n\t"

        output = output.replace('<ASSIGN CONSTANTS>', assign_constants)
        output = output.replace('<INPUT BUFFERS>', buffer_decls)
        output = output.replace('<OUTPUT BUFFERS>', '')      # Treat all buffers as both input/output for now
        output = output.replace('<CREATE BUFFERS>', create_buffers)
        output = output.replace('<WRITE TO INPUT BUFFERS>', write_to_buffers)
        output = output.replace('<SET KERNEL ARGUMENTS>', set_kernel_args)
        output = output.replace('<READ FROM OUTPUT BUFFERS>', read_from_buffers)
        output = output.replace('<RELEASE BUFFERS>', release_buffers)

        output = output.replace('<PRE KERNEL HOST CODE>', '')
        output = output.replace('<POST KERNEL HOST CODE>', '')

        return output

class KernelArg:
    __slots__ = 'argument_type', 'input_var', 'buffer_size'

    def __init__(self, argument_type, input_var, buffer_size):
        self.argument_type = argument_type
        self.input_var = input_var
        self.buffer_size = buffer_size

class ArgType(Enum):
    BUFFER = auto()
    SCALAR = auto()
    CONSTANT = auto()

# Unused, may be used later or removed
class BufferDetails:
    __slots__ = 'name', 'size', 'buf_type', 'read_write', 'input_var', 'output_var'

    def __init__(self, name, size, buf_type, read_write, input_var, output_var):
        self.name = name
        self.size = size
        self.buf_type = buf_type
        self.read_write = read_write
        self.input_var = input_var
        self.output_var = output_var

def is_buffer(ast):
    # Assume if ast node is a pointer, it's a device buffer
    if type(ast.type) == c_ast.PtrDecl:
        return True
    return False