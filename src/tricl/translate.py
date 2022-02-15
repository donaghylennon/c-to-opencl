from typing import Optional
from pycparser import c_ast


class TranslationVisitor(c_ast.NodeVisitor):
    level_of_indentation: int
    omp_mode: bool
    omp_parallel_for: bool
    expand_structs: bool
    declared_in_omp: set
    undeclared_in_omp: set
    function_calls: set
    structs: set

    def translate_omp_parallel(self, node: c_ast.Node) -> str:
        self.omp_mode = True
        self.omp_parallel_for = False
        self.expand_structs = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        return self.visit(node)

    def translate_omp_parallel_for(self, node: c_ast.Node) -> str:
        self.omp_mode = True
        self.omp_parallel_for = True
        self.expand_structs = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        return self.visit(node)

    def translate_function(self, node: c_ast.Node) -> str:
        self.omp_mode = False
        self.omp_parallel_for = False
        self.expand_structs = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        return self.visit(node)

    def get_omp_kernel_args(self) -> set:
        return self.undeclared_in_omp

    def get_function_calls(self) -> set:
        return self.function_calls

    def get_structs(self) -> set:
        return self.structs

    def generate_struct_def(self, node: c_ast.Node) -> str:
        self.omp_mode = False
        self.omp_parallel_for = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        self.expand_structs = True
        return self.visit(node)

    def generate_typedefs(self, node: c_ast.Node) -> str:
        self.omp_mode = False
        self.omp_parallel_for = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        self.expand_structs = False
        return self.visit(node)

    def generate_argument_type(self, node: c_ast.Node) -> str:
        if type(node) is c_ast.PtrDecl or type(node) is c_ast.ArrayDecl:
            return "__global " + self.visit(node)
        else:
            return self.visit(node)

    def visit_FuncDef(self, node: c_ast.Node) -> str:
        output: str = ""
        whitespace: str = "    " * self.level_of_indentation
        func_name: str = node.decl.name
        func_type: str = node.decl.type.type.type.names[0]

        output += whitespace + func_type + " " + func_name + "("

        output += ", ".join([
            self.generate_argument_type(param.type) + " " + param.name
            for param in node.decl.type.args
        ]) + ") {\n"

        if type(node.body) is c_ast.Compound:
            output += self.visit(node.body)
        else:
            output += (self.level_of_indentation + 1) * "    " + self.visit(node.body)

        output += whitespace + "}\n"

        return output

    def visit_Decl(self, node: c_ast.Node) -> str:
        if self.omp_mode and node.name:
            self.declared_in_omp.add(node.name)
        funcspec = " " + " ".join(node.funcspec) if node.funcspec else ""
        storage = " " + " ".join(node.storage) if node.storage else ""
        qualifiers = " " + " ".join(node.quals) if node.quals else ""
        init = " = " + self.visit(node.init) if node.init else ""
        name = " " + node.name if node.name else ""
        return funcspec + storage + qualifiers + self.visit(node.type) + name + init

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
        return qualifiers + self.visit(node.type)

    def visit_Typedef(self, node: c_ast.Node) -> str:
        return "typedef " + self.visit(node.type) + " " + node.name

    def visit_Typename(self, node: c_ast.Node) -> str:
        qualifiers = " ".join(node.quals) + " " if node.quals else ""
        name = " " + node.name if node.name else ""
        return qualifiers + self.visit(node.type) + name

    def visit_IdentifierType(self, node: c_ast.Node):
        return " ".join(node.names)

    def visit_For(self, node: c_ast.Node) -> str:
        if self.omp_parallel_for:
            self.level_of_indentation += 1
            output = ""
            whitespace = "    " * self.level_of_indentation
            indexes = []

            if type(node.init) is c_ast.Assignment:
                indexes.append(node.init.lvalue.name)
                self.declared_in_omp.add(node.init.lvalue.name)
            elif type(node.init) is c_ast.Decl:
                if self.omp_mode:
                    self.declared_in_omp.add(node.init.name)
                indexes.append(node.init.name)
            elif type(node.init) is c_ast.DeclList:
                for init in node.init:
                    if self.omp_mode:
                        self.declared_in_omp.add(init.name)
                    indexes.append(init.name)

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
        args = ", ".join([self.visit(arg) for arg in node.args]) if node.args else ""
        if node.name.name == "omp_get_num_threads":
            return "get_global_size(0)"
        elif node.name.name == "omp_get_thread_num":
            return "get_global_id(0)"
        elif node.name.name == "sqrt":
            pass
        else:
            self.function_calls.add(node.name.name)
        return node.name.name + "(" + args + ")"

    def visit_BinaryOp(self, node: c_ast.Node) -> str:
        return self.visit(node.left) + f" {node.op} " + self.visit(node.right)

    def visit_UnaryOp(self, node: c_ast.Node) -> str:
        op = node.op
        if op == "sizeof":
            return op + "(" + self.visit(node.expr) + ")"
        elif op[0] == "p":
            return node.op.replace("p", self.visit(node.expr))
        else:
            return node.op + self.visit(node.expr)

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

    def visit_Return(self, node: c_ast.Node) -> str:
        if node.expr is not None:
            return "return " + self.visit(node.expr)
        else:
            return "return"

    def visit_StructRef(self, node: c_ast.Node) -> str:
        return self.visit(node.name) + node.type + node.field.name

    def visit_Struct(self, node: c_ast.Node) -> str:
        if node.decls:
            self.structs.add(node)
        output = "struct " + node.name
        if self.expand_structs:
            output += " {\n"
            self.level_of_indentation += 1
            whitespace = "    " * self.level_of_indentation
            for decl in node.decls:
                output += whitespace + self.visit(decl) + ";\n"
            self.level_of_indentation -= 1
            whitespace = "    " * self.level_of_indentation
            output += whitespace + "}"
        return output

    def visit_InitList(self, node: c_ast.Node) -> str:
        return "{ " + ", ".join([self.visit(expr) for expr in node.exprs]) + " }"

    def visit_ExprList(self, node: c_ast.Node) -> str:
        return ", ".join([self.visit(expr) for expr in node.exprs])

    def visit_Cast(self, node: c_ast.Node) -> str:
        return "(" + self.visit(node.to_type) + ")" + self.visit(node.expr)


class Translator(c_ast.NodeVisitor):
    var_types: dict = {}
    struct_defs: dict[str, c_ast.Node] = {}
    typedef_defs: dict[str, c_ast.Node] = {}
    next_omp_kernel_id: int = 0
    kernels: list[str] = []
    structs: list[str] = []
    typedefs: list[str] = []
    file_ast: c_ast.Node

    def visit_FileAST(self, node: c_ast.Node) -> str:
        self.file_ast = node
        for child in node:
            self.visit(child)
        return (";\n".join(self.structs) + ";\n\n" if self.structs else "") + \
               (";\n".join(self.typedefs) + ";\n\n" if self.typedefs else "") + \
               "\n".join(self.kernels)

    def visit_Decl(self, node: c_ast.Node) -> None:
        self.var_types[node.name] = node.type
        for child in node:
            self.visit(child)

    def visit_Typedef(self, node: c_ast.Node) -> None:
        self.typedef_defs[node.name] = node
        for child in node:
            self.visit(child)

    def visit_Struct(self, node: c_ast.Node) -> None:
        if node.decls:
            self.struct_defs[node.name] = node
        for child in node:
            self.visit(child)

    def visit_Compound(self, node: c_ast.Node) -> None:
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

    def extract_kernel_from_omp(self, node: c_ast.Node, parallel_for: bool = False) -> None:
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
        function_calls = trans_visitor.get_function_calls()
        structs = trans_visitor.get_structs()

        structs_needed = set()
        typedefs_needed = set()
        for param in args:
            tp = self.var_types[param]
            while type(tp) is c_ast.ArrayDecl or type(tp) is c_ast.PtrDecl:
                tp = tp.type
            if type(tp.type) is c_ast.Struct:
                structs_needed.add(tp.type.name)
            elif type(tp.type) is c_ast.IdentifierType:
                typedefs_needed.add(tp.type.names[0])

        output += ", ".join([
            trans_visitor.generate_argument_type(self.var_types[param]) + " " + param
            for param in args
        ]) + ") {\n"
        output += function_body + "}\n"
        self.kernels.append(output)

        while function_calls:
            new_calls = set()
            for call in function_calls:
                function_def = self.find_function_def(call)
                if function_def is not None:
                    self.kernels.append(trans_visitor.translate_function(function_def))
                    new_calls.update(trans_visitor.get_function_calls())
            function_calls = new_calls

        for td in typedefs_needed:
            td_def = self.typedef_defs[td]
            code = trans_visitor.generate_typedefs(td_def)
            self.typedefs.append(code)
            if type(td_def.type) is c_ast.TypeDecl and type(td_def.type.type) is c_ast.Struct:
                structs_needed.add(td_def.type.type.name)

        for struct in structs_needed:
            code = trans_visitor.generate_struct_def(self.struct_defs[struct])
            self.structs.append(code)

    def find_function_def(self, name: str) -> Optional[c_ast.Node]:
        for child in self.file_ast:
            if type(child) is c_ast.FuncDef and child.decl.name == name:
                return child
