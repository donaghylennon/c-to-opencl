from pycparser import c_ast, c_generator


class TranslationVisitor(c_ast.NodeVisitor):
    level_of_indentation: int = 0
    omp_mode: bool
    declared_in_omp: set = set()
    undeclared_in_omp: set = set()

    def __init__(self, omp_mode: bool = False):
        self.omp_mode = omp_mode

    def get_omp_kernel_args(self) -> set:
        return self.undeclared_in_omp

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
        ]) + ") "

        if not self.omp_mode:
            output += "{\n"
            for_loop = node.body.block_items[0]
            output += self.visit(for_loop)
            output += "}\n"
        else:
            self.level_of_indentation += 1
            output += self.visit(node.body)
            self.level_of_indentation -= 1

        return output

    def visit_Decl(self, node: c_ast.Node) -> str:
        output: str = "    " * self.level_of_indentation
        if self.omp_mode:
            self.declared_in_omp.add(node.name)
        funcspec = " " + " ".join(node.funcspec) if node.funcspec else ""
        storage = " " + " ".join(node.storage) if node.storage else ""
        qualifiers = " " + " ".join(node.quals) if node.quals else ""
        init = " = " + self.visit(node.init) if node.init else ""
        return funcspec + storage + qualifiers + self.visit(node.type) + " " + node.name + init

    def visit_ID(self, node: c_ast.Node) -> str:
        if self.omp_mode and node.name not in self.declared_in_omp:
            self.undeclared_in_omp.add(node.name)
        return node.name

    def visit_PtrDecl(self, node: c_ast.Node) -> str:
        qualifiers = " " + " ".join(node.quals) if node.quals else ""
        return "__global " + self.visit(node.type) + "*" + qualifiers

    def visit_ArrayDecl(self, node: c_ast.Node) -> str:
        return "__global " + self.visit(node.type) + "*"

    def visit_TypeDecl(self, node: c_ast.Node) -> str:
        qualifiers = " ".join(node.quals) + " " if node.quals else ""
        return qualifiers + " ".join(node.type.names)

    def visit_For(self, node: c_ast.Node) -> str:
        if not self.omp_mode:
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
        else:
            whitespace = self.level_of_indentation * "    "
            output = "for ("
            init = self.visit(node.init) if node.init else ""
            cond = self.visit(node.cond) if node.cond else ""
            nxt = self.visit(node.next) if node.next else ""
            output += init + "; " + cond + "; " + nxt + ") {\n"
            if type(node.stmt) == c_ast.Compound:
                output += self.visit(node.stmt)
            else:
                output += (self.level_of_indentation + 1) * "    " + self.visit(node.stmt) + ";\n"
            output += whitespace + "}"
        return output

    def visit_Compound(self, node: c_ast.Node) -> str:
        # Parent node is responsible for any indentation of opening brace
        # as well as newlines after closing brace, for flexibility in style
        output: str = ""
        self.level_of_indentation += 1
        whitespace: str = "    " * self.level_of_indentation
        for child in node:
            if type(child) == c_ast.If or type(child) == c_ast.For or type(child) == c_ast.While or \
                    type(child) == c_ast.DoWhile:
                line_terminate = "\n"
            else:
                line_terminate = ";\n"
            output += whitespace + self.visit(child) + line_terminate
        self.level_of_indentation -= 1
        return output

    def visit_FuncCall(self, node: c_ast.Node) -> str:
        args = ",".join([self.visit(arg) for arg in node.args]) if node.args else ""
        if node.name.name == "omp_get_num_threads":
            return "get_global_size(0)"
        elif node.name.name == "omp_get_thread_num":
            return "get_global_id(0)"
        return node.name.name + "(" + args + ")"

    def visit_BinaryOp(self, node: c_ast.Node) -> str:
        return self.visit(node.left) + f" {node.op} " + self.visit(node.right)

    def visit_UnaryOp(self, node: c_ast.Node) -> str:
        return node.op.replace("p", self.visit(node.expr))

    def visit_Constant(self, node: c_ast.Node) -> str:
        return node.value

    def visit_If(self, node: c_ast.Node) -> str:
        whitespace = self.level_of_indentation * "    "
        output = "if (" + self.visit(node.cond) + ") {\n"
        self.level_of_indentation += 1
        if type(node.iftrue) == c_ast.Compound:
            output += self.visit(node.iftrue)
        else:
            output += self.level_of_indentation * "    " + self.visit(node.iftrue) + ";"
        if node.iffalse:
            if type(node.iffalse) == c_ast.If:
                output += whitespace + "} else " + self.visit(node.iffalse)
            elif type(node.iffalse) == c_ast.Compound:
                output += whitespace + "} else {\n" + self.visit(node.iffalse)
            else:
                output += whitespace + "} else {\n" + whitespace + self.visit(node.iffalse) + ";"
        self.level_of_indentation -= 1
        output += "\n" + whitespace + "}"
        return output

    def visit_Assignment(self, node: c_ast.Node) -> str:
        return self.visit(node.lvalue) + f" {node.op} " + self.visit(node.rvalue)

    def visit_ArrayRef(self, node: c_ast.Node) -> str:
        return self.visit(node.name) + "[" + self.visit(node.subscript) + "]"

    def visit_DeclList(self, node: c_ast.Node) -> str:
        return ", ".join([self.visit(child) for child in node])


class Translator(c_ast.NodeVisitor):
    omp_mode: bool
    var_types: dict = {}
    next_omp_kernel_id: int = 0
    kernels: list[str] = []

    def __init__(self, omp_mode: bool = False):
        self.omp_mode = omp_mode

    def visit_FileAST(self, node: c_ast.Node):
        if self.omp_mode:
            for child in node:
                self.visit(child)
            return self.kernels[0]
        else:
            return TranslationVisitor().visit(node)

    def visit_Decl(self, node: c_ast.Node):
        self.var_types[node.name] = node.type
        for child in node:
            self.visit(child)

    def visit_Compound(self, node: c_ast.Node):
        omp_parallel: bool = False
        for child in node:
            if omp_parallel:
                self.extract_kernel_from_omp(child)
            elif self.omp_mode and type(child) == c_ast.Pragma:
                if child.string == "omp parallel":
                    omp_parallel = True
            else:
                self.visit(child)

    def extract_kernel_from_omp(self, node: c_ast.Node):
        # Need to visit this entire subtree, while keeping track of
        # declared + used variables -- used but not declared == kernel argument
        k_id = self.next_omp_kernel_id
        self.next_omp_kernel_id += 1
        output: str = f"__kernel void omp_translated_kernel{k_id}("
        trans_visitor: TranslationVisitor = TranslationVisitor(omp_mode=True)
        argtype_visitor: TranslationVisitor = TranslationVisitor()
        function_body = trans_visitor.visit(node)
        args = trans_visitor.get_omp_kernel_args()

        output += ", ".join([
            argtype_visitor.visit(self.var_types[param]) + " " + param
            for param in args
        ]) + ") {\n"
        output += function_body + "}\n"
        self.kernels.append(output)
