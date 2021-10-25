from pycparser import c_ast, c_generator

def translate_function(ast):
    output = ""
    func_def = ast.ext[0]
    func_name = func_def.decl.name
    func_type = func_def.decl.type.type.type.names[0]

    output += "__kernel " + func_type + " " + func_name + "("

    for i, param in enumerate(func_def.decl.type.args):
        if i != 0: output += ", "
        output += translate_declaration(param.type) + " " + param.name
    output += ") {\n"

    for_loop = func_def.body.block_items[0]
    output += translate_for(for_loop)
    output += "}\n"

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

def translate_for(node):
    output = ""
    indexes = []
    for decl in node.init:
        indexes.append(decl.name)

    for i, index in enumerate(indexes):
        output += f"int {index} = get_global_id({i});\n"

    cond = node.cond
    output += "if(!("
    output += cond.left.name + " " + cond.op + " " + cond.right.name + "))\n"
    output += "return;\n"

    generator = c_generator.CGenerator()
    for stmt in node.stmt:
        output += generator.visit(stmt) + ";\n"

    return output
