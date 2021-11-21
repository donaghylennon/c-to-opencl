from pycparser import c_ast, c_generator


def translate_function(ast, lvl_indent=0):
    output = ""
    whitespace = "    " * lvl_indent
    func_def = ast.ext[0]
    func_name = func_def.decl.name
    func_type = func_def.decl.type.type.type.names[0]

    output += whitespace + "__kernel " + func_type + " " + func_name + "("

    for i, param in enumerate(func_def.decl.type.args):
        if i != 0:
            output += ", "
        output += translate_declaration(param.type, lvl_indent+1) + " " + param.name
    output += ") {\n"

    for_loop = func_def.body.block_items[0]
    output += translate_for(for_loop, lvl_indent+1)
    output += "}\n"

    return output


def translate_declaration(node, lvl_indent=0):
    output = ""
    if type(node) == c_ast.PtrDecl:
        output += "__global "
        output += translate_declaration(node.type)
        output += "*"
    elif type(node) == c_ast.TypeDecl:
        output += " ".join(node.type.names)
    return output


def translate_for(node, lvl_indent=0):
    output = ""
    whitespace = "    " * lvl_indent
    indexes = []
    for decl in node.init:
        indexes.append(decl.name)

    for i, index in enumerate(indexes):
        output += whitespace + f"int {index} = get_global_id({i});\n"

    cond = node.cond
    output += whitespace + "if(!("
    output += cond.left.name + " " + cond.op + " " + cond.right.name + "))\n"
    output += whitespace + "    " + "return;\n"

    generator = c_generator.CGenerator()
    for stmt in node.stmt:
        output += whitespace + generator.visit(stmt) + ";\n"

    return output
