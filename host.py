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