import argparse
import pycparser

import translate, host

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('filepath', help='path to c file to translate')
    args = argparser.parse_args()

    ast = pycparser.parse_file(args.filepath, use_cpp=True)
    cl_output = translate.translate_function(ast)
    print(cl_output)


if __name__ == "__main__":
    main()