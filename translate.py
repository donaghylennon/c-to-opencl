from pycparser import c_ast

def translate_function(ast):
    output = ""
    func_def = ast.ext[0]
    func_name = func_def.decl.name
    func_type = func_def.decl.type.type.type.names[0]

    output += "__kernel " + func_type + " " + func_name + "("

    for i, param in enumerate(func_def.decl.type.args):
        if i != 0: output += ", "
        output += translate_declaration(param.type) + " " + param.name
    output += ")"

    return output

def translate_declaration(node):
    output = ""
    if type(node) == c_ast.PtrDecl:
        output += "__global "
        output += translate_declaration(node.type)
        output += "*"
    elif type(node) == c_ast.TypeDecl:
        output += " ".join(node.type.names)
    return output
