from pycparser import c_ast, c_generator


# May be better to have outer translator object instead of
# creating instance of this in main
class TranslationVisitor(c_ast.NodeVisitor):
    level_of_indentation: int = 0

    def __init__(self):
        pass

    def visit_FileAST(self, node: c_ast.Node) -> str:
        return self.visit(node.ext[0])

    def visit_FuncDef(self, node: c_ast.Node) -> str:
        output: str = ""
        whitespace: str = "    " * self.level_of_indentation
        func_name: str = node.decl.name
        func_type: str = node.decl.type.type.type.names[0]

        output += whitespace + "__kernel " + func_type + " " + func_name + "("

        output += ", ".join([
            self.visit(param.type) + " " + param.name
            for param in node.decl.type.args
        ]) + ") {\n"

        for_loop = node.body.block_items[0]
        output += self.visit(for_loop)
        output += "}\n"

        return output

    def visit_PtrDecl(self, node: c_ast.Node) -> str:
        qualifiers = " " + " ".join(node.quals) if node.quals else ""
        return "__global " + self.visit(node.type) + "*" + qualifiers

    def visit_TypeDecl(self, node: c_ast.Node) -> str:
        qualifiers = " ".join(node.quals) + " " if node.quals else ""
        return qualifiers + " ".join(node.type.names)

    def visit_For(self, node: c_ast.Node) -> str:
        self.level_of_indentation += 1
        output = ""
        whitespace = "    " * self.level_of_indentation
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

        self.level_of_indentation -= 1
        return output
