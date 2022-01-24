from pycparser import c_ast


class TranslationVisitor(c_ast.NodeVisitor):
    level_of_indentation: int
    omp_mode: bool
    omp_parallel_for: bool
    declared_in_omp: set
    undeclared_in_omp: set

    def translate_omp_parallel(self, node: c_ast.Node) -> str:
        self.omp_mode = True
        self.omp_parallel_for = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        return self.visit(node)

    def translate_omp_parallel_for(self, node: c_ast.Node) -> str:
        self.omp_mode = True
        self.omp_parallel_for = True
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        return self.visit(node)

    def translate_function(self, node: c_ast.Node) -> str:
        self.omp_mode = False
        self.omp_parallel_for = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        return self.visit(node)

    def get_omp_kernel_args(self) -> set:
        return self.undeclared_in_omp

    def generate_argument_type(self, node: c_ast.Node) -> str:
        self.omp_mode = False
        self.omp_parallel_for = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        if type(node) is c_ast.PtrDecl or type(node) is c_ast.ArrayDecl:
            return "__global " + self.visit(node)

    def visit_FuncDef(self, node: c_ast.Node) -> str:
        output: str = ""
        whitespace: str = "    " * self.level_of_indentation
        func_name: str = node.decl.name
        func_type: str = node.decl.type.type.type.names[0]

        output += whitespace + "__kernel " + func_type + " " + func_name + "("

        output += ", ".join([
            self.generate_argument_type(param.type) + " " + param.name
            for param in node.decl.type.args
        ]) + ") "

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
        return self.visit(node.type) + "*" + qualifiers

    def visit_ArrayDecl(self, node: c_ast.Node) -> str:
        return self.visit(node.type) + "*"

    def visit_TypeDecl(self, node: c_ast.Node) -> str:
        qualifiers = " ".join(node.quals) + " " if node.quals else ""
        return qualifiers + " ".join(node.type.names)

    def visit_For(self, node: c_ast.Node) -> str:
        if self.omp_parallel_for:
            self.level_of_indentation += 1
            output = ""
            whitespace = "    " * self.level_of_indentation
            indexes = []
            for decl in node.init:
                if self.omp_mode:
                    self.declared_in_omp.add(decl.name)
                indexes.append(decl.name)

            for i, index in enumerate(indexes):
                output += whitespace + f"int {index} = get_global_id({i});\n"

            output += whitespace + "if(!("
            cond = self.visit(node.cond)
            output += cond + "))\n"
            output += whitespace + "    " + "return;\n"

            if type(node.stmt) == c_ast.Compound:
                self.level_of_indentation -= 1
                output += self.visit(node.stmt)
                self.level_of_indentation += 1
            else:
                output += whitespace + self.visit(node.stmt) + ";\n"

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
    var_types: dict = {}
    next_omp_kernel_id: int = 0
    kernels: list[str] = []

    def visit_FileAST(self, node: c_ast.Node):
        for child in node:
            self.visit(child)
        return self.kernels[0]

    def visit_Decl(self, node: c_ast.Node):
        self.var_types[node.name] = node.type
        for child in node:
            self.visit(child)

    def visit_Compound(self, node: c_ast.Node):
        omp_parallel: bool = False
        omp_parallel_for: bool = False
        for child in node:
            if omp_parallel:
                self.extract_kernel_from_omp(child)
                omp_parallel = False
            elif omp_parallel_for:
                self.extract_kernel_from_omp(child, True)
                omp_parallel_for = False
            elif type(child) == c_ast.Pragma:
                if child.string == "omp parallel":
                    omp_parallel = True
                elif child.string == "omp parallel for":
                    omp_parallel_for = True
            else:
                self.visit(child)

    def extract_kernel_from_omp(self, node: c_ast.Node, parallel_for: bool = False):
        # Need to visit this entire subtree, while keeping track of
        # declared + used variables -- used but not declared == kernel argument
        k_id = self.next_omp_kernel_id
        self.next_omp_kernel_id += 1
        output: str = f"__kernel void omp_translated_kernel{k_id}("
        trans_visitor: TranslationVisitor = TranslationVisitor()

        if parallel_for:
            function_body = trans_visitor.translate_omp_parallel_for(node)
        else:
            function_body = trans_visitor.translate_omp_parallel(node)
        args = trans_visitor.get_omp_kernel_args()

        output += ", ".join([
            trans_visitor.generate_argument_type(self.var_types[param]) + " " + param
            for param in args
        ]) + ") {\n"
        output += function_body + "}\n"
        self.kernels.append(output)
