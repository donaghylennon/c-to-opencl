import argparse
import pycparser

from . import translate
from . import host


def main():
    argparser = argparse.ArgumentParser(prog="tricl")
    argparser.add_argument('-I', help='c include path', action="append")
    argparser.add_argument('input_file', help='path to c file to translate')
    argparser.add_argument('output_file', help='path to write c file containing host code')
    argparser.add_argument('kernel_file', help='path to write cl file containing kernel code')
    args = argparser.parse_args()

    cpp_args = ["-Iutils/fake_libc_include"]
    if args.I:
        cpp_args += ["-I" + path for path in args.I]

    ast = pycparser.parse_file(args.input_file, use_cpp=True, cpp_args=cpp_args)
    visitor = translate.Translator()
    cl_output = visitor.visit(ast)
    with open(args.kernel_file, 'w') as f:
        f.write(cl_output)
    host_details = host.HostDetails.from_ast(ast)
    host_code = host_details.generate_code(args.kernel_file)
    with open(args.output_file, 'w') as f:
        f.write(host_code)


if __name__ == "__main__":
    main()
