import argparse
from pycparser import c_parser
import translate

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('filepath', help='path to c file to translate')
    args = argparser.parse_args()

    c_source = ""
    with open(args.filepath) as c_file:
        c_source = c_file.read()

    parser = c_parser.CParser()
    ast = parser.parse(c_source)
    cl_output = translate.translate_function(ast)
    print(cl_output)


if __name__ == "__main__":
    main()