from typing import Optional
from pycparser import c_ast


class TranslationVisitor(c_ast.NodeVisitor):
    level_of_indentation: int
    omp_mode: bool
    omp_parallel_for: bool
    expand_structs: bool
    declared_in_omp: set[str]
    undeclared_in_omp: set[str]
    function_calls: set[str]
    structs: set[str]
    new_typedefs: set[str]
    typedefs_used: set[str]
    renamed_variables: dict[str, str]

    builtin_types = {"bool", "char", "unsigned", "char", "short", "int", "long", "float", "double", "size_t",
                     "ptrdiff_t", "intptr_t", "uintptr_t", "void"}
    reserved_words = {"global", "local", "constant", "private", "generic", "kernel", "read_only", "write_only",
                      "read_write", "uniform", "pipe", "__global", "__local", "__constant", "__private", "__generic",
                      "__kernel", "__read_only", "__write_only", "__read_write", "__uniform", "__pipe"}

    def translate_omp_parallel(self, node: c_ast.Node) -> str:
        self.omp_mode = True
        self.omp_parallel_for = False
        self.expand_structs = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        self.new_typedefs = set()
        self.typedefs_used = set()
        self.renamed_variables = {}
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
        self.new_typedefs = set()
        self.typedefs_used = set()
        self.renamed_variables = {}
        return self.visit(node)

    def translate_function(self, node: c_ast.Node, renamed: dict[str, str]) -> str:
        self.omp_mode = False
        self.omp_parallel_for = False
        self.expand_structs = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        self.new_typedefs = set()
        self.typedefs_used = set()
        self.renamed_variables = renamed
        return self.visit(node)

    def get_omp_kernel_args(self) -> set[str]:
        return self.undeclared_in_omp

    def get_function_calls(self) -> set[str]:
        return self.function_calls

    def get_structs(self) -> set[str]:
        return self.structs

    def get_typedefs_used(self) -> set[str]:
        return self.typedefs_used

    def get_renamed_variables(self) -> dict[str, str]:
        return self.renamed_variables

    def generate_struct_def(self, node: c_ast.Node) -> str:
        self.omp_mode = False
        self.omp_parallel_for = False
        self.level_of_indentation = 0
        self.declared_in_omp = set()
        self.undeclared_in_omp = set()
        self.function_calls = set()
        self.structs = set()
        self.new_typedefs = set()
        self.typedefs_used = set()
        self.renamed_variables = {}
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
        self.new_typedefs = set()
        self.typedefs_used = set()
        self.renamed_variables = {}
        self.expand_structs = True
        return self.visit(node)

    def generate_argument_type(self, node: c_ast.Node) -> str:
        if type(node) is c_ast.PtrDecl or type(node) is c_ast.ArrayDecl:
            return "__global " + self.visit(node)
        else:
            return self.visit(node)

    def visit_FuncDef(self, node: c_ast.Node) -> str:
        output: str = ""
        whitespace: str = "    " * self.level_of_indentation

        renamed = self.renamed_variables.get(node.decl.name)
        func_name: str = renamed if renamed else node.decl.name
        func_type: str = self.visit(node.decl.type.type)

        output += whitespace + func_type + " " + func_name + "("

        output += ", ".join([
            self.generate_argument_type(param.type) + " " +
            (self.renamed_variables[param.name] if self.renamed_variables.get(param.name) else param.name)
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
        renamed = self.renamed_variables.get(node.name)
        name = renamed if renamed else node.name
        if self.omp_mode and node.name not in self.declared_in_omp:
            self.undeclared_in_omp.add(node.name)
        if not renamed and node.name in self.reserved_words:
            renamed = node.name + "$"
            self.renamed_variables[node.name] = renamed
            return renamed
        return name

    def visit_PtrDecl(self, node: c_ast.Node) -> str:
        qualifiers = " " + " ".join(node.quals) if node.quals else ""
        return self.visit(node.type) + "*" + qualifiers

    def visit_ArrayDecl(self, node: c_ast.Node) -> str:
        return self.visit(node.type) + "*"

    def visit_TypeDecl(self, node: c_ast.Node) -> str:
        qualifiers = " ".join(node.quals) + " " if node.quals else ""
        return qualifiers + self.visit(node.type)

    def visit_Typedef(self, node: c_ast.Node) -> str:
        self.new_typedefs.add(node.name)
        return "typedef " + self.visit(node.type) + " " + node.name

    def visit_Typename(self, node: c_ast.Node) -> str:
        qualifiers = " ".join(node.quals) + " " if node.quals else ""
        name = " " + node.name if node.name else ""
        return qualifiers + self.visit(node.type) + name

    def visit_IdentifierType(self, node: c_ast.Node):
        for name in node.names:
            if name not in self.builtin_types and name not in self.new_typedefs:
                self.typedefs_used.add(name)
        return " ".join(node.names)

    def visit_For(self, node: c_ast.Node) -> str:
        if self.omp_parallel_for:
            self.omp_parallel_for = False
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

            if type(node.stmt) is c_ast.Compound:
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
            if type(node.stmt) is c_ast.Compound:
                output += self.visit(node.stmt)
            else:
                output += (self.level_of_indentation + 1) * "    " + self.visit(node.stmt) + ";\n"
            output += whitespace + "}"
        return output

    def visit_While(self, node: c_ast.Node) -> str:
        whitespace = self.level_of_indentation * "    "
        output = "while ("
        cond = self.visit(node.cond) if node.cond else ""
        output += cond + ") {\n"
        if type(node.stmt) is c_ast.Compound:
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
            if type(child) is c_ast.If or type(child) is c_ast.For or type(child) is c_ast.While or \
                    type(child) is c_ast.DoWhile or type(child) is c_ast.Switch or type(child) is c_ast.Case:
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
        elif node.name.name in self.reserved_words:
            renamed = node.name.name + "$"
            self.renamed_variables[node.name.name] = renamed
            self.function_calls.add(node.name.name)
            return renamed + "(" + args + ")"
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

    def visit_TernaryOp(self, node: c_ast.Node) -> str:
        return "(" + self.visit(node.cond) + " ? " + self.visit(node.iftrue) + " : " + self.visit(node.iffalse) + ")"

    def visit_Constant(self, node: c_ast.Node) -> str:
        return node.value

    def visit_If(self, node: c_ast.Node) -> str:
        whitespace = self.level_of_indentation * "    "
        output = "if (" + self.visit(node.cond) + ") {\n"
        if type(node.iftrue) == c_ast.Compound:
            output += self.visit(node.iftrue)
        else:
            output += (self.level_of_indentation + 1) * "    " + self.visit(node.iftrue) + ";\n"
        if node.iffalse:
            if type(node.iffalse) == c_ast.If:
                output += whitespace + "} else " + self.visit(node.iffalse)
            elif type(node.iffalse) == c_ast.Compound:
                output += whitespace + "} else {\n" + self.visit(node.iffalse)
                output += whitespace + "}"
            else:
                output += whitespace + "} else {\n" + (self.level_of_indentation + 1) * "    " + \
                          self.visit(node.iffalse) + ";"
                output += "\n" + whitespace + "}"
        else:
            output += whitespace + "}"
        return output

    def visit_Switch(self, node: c_ast.Node) -> str:
        whitespace = self.level_of_indentation * "    "
        output = "switch (" + self.visit(node.cond) + ") {\n"
        output += self.visit(node.stmt)
        output += whitespace + "}"
        return output

    def visit_Case(self, node: c_ast.Node) -> str:
        self.level_of_indentation += 1
        whitespace = self.level_of_indentation * "    "
        output = "case " + self.visit(node.expr) + ":\n"
        for stmt in node.stmts:
            seperator = (";\n" if type(stmt) not in (c_ast.If, c_ast.For, c_ast.While, c_ast.DoWhile,
                                                     c_ast.Switch, c_ast.Case) else "\n")
            output += whitespace + self.visit(stmt) + seperator
        self.level_of_indentation -= 1
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
        if node.name:
            self.structs.add(node.name)

        output = "struct " + (node.name + " " if node.name else "")
        if self.expand_structs or node.name is None:
            output += "{\n"
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

    def visit_Break(self, node: c_ast.Node) -> str:
        return "break"

    def visit_Pragma(self, node: c_ast.Node) -> str:
        return ""


class Translator(c_ast.NodeVisitor):
    var_types: dict[str, c_ast.Node] = {}
    struct_defs: dict[str, c_ast.Node] = {}
    typedef_defs: dict[str, c_ast.Node] = {}
    next_omp_kernel_id: int = 0
    kernels: list[str] = []
    structs: dict[str, str] = {}
    typedefs: dict[str, str] = {}
    file_ast: c_ast.Node
    within_typedef: bool = False

    def visit_FileAST(self, node: c_ast.Node) -> str:
        self.file_ast = node
        for child in node:
            self.visit(child)
        return (";\n\n".join(reversed(self.structs.values())) + ";\n\n" if self.structs else "") + \
               (";\n\n".join(reversed(self.typedefs.values())) + ";\n\n" if self.typedefs else "") + \
               "\n".join(self.kernels)

    def visit_Decl(self, node: c_ast.Node) -> None:
        self.var_types[node.name] = node.type
        for child in node:
            self.visit(child)

    def visit_Typedef(self, node: c_ast.Node) -> None:
        self.within_typedef = True
        self.typedef_defs[node.name] = node
        for child in node:
            self.visit(child)
        self.within_typedef = False

    def visit_Struct(self, node: c_ast.Node) -> None:
        must_reset_within_typedef = False
        if not self.within_typedef and node.decls and node.name:
            self.struct_defs[node.name] = node

        if self.within_typedef:
            must_reset_within_typedef = True
            self.within_typedef = False
        for child in node:
            self.visit(child)
        if must_reset_within_typedef:
            self.within_typedef = True

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
                if child.string.startswith("omp parallel for"):
                    omp_parallel_for = True
                elif child.string.startswith("omp parallel"):
                    omp_parallel = True
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
        renamed_variables = trans_visitor.get_renamed_variables()

        output += ", ".join([
            trans_visitor.generate_argument_type(self.var_types[param]) + " " +
            (renamed_variables[param] if renamed_variables.get(param) else param)
            for param in args
        ]) + ") {\n"
        output += function_body + "}\n"
        self.kernels.append(output)

        structs = trans_visitor.get_structs()
        typedefs = trans_visitor.get_typedefs_used()

        self.retrieve_types(structs, typedefs, trans_visitor)

        while function_calls:
            new_calls = set()
            for call in function_calls:
                function_def = self.find_function_def(call)
                if function_def is not None:
                    self.kernels.append(trans_visitor.translate_function(function_def, renamed_variables))
                    new_calls.update(trans_visitor.get_function_calls())
            function_calls = new_calls

    def find_function_def(self, name: str) -> Optional[c_ast.Node]:
        for child in self.file_ast:
            if type(child) is c_ast.FuncDef and child.decl.name == name:
                return child

    def retrieve_types(self, structs: set[str], typedefs: set[str], visitor: TranslationVisitor) -> None:
        structs_found: set[str] = set()
        typedefs_found: set[str] = set()
        for struct_name in structs:
            struct_node = self.struct_defs[struct_name]
            struct_code = visitor.generate_struct_def(struct_node)
            if self.structs.get(struct_name) is None:
                self.structs[struct_name] = struct_code

                structs_inside = visitor.get_structs()
                structs_inside.discard(struct_name)
                structs_found.update(structs_inside)
                typedefs_inside = visitor.get_typedefs_used()
                typedefs_found.update(typedefs_inside)

        for typedef_name in typedefs:
            typedef_node = self.typedef_defs[typedef_name]
            typedef_code = visitor.generate_typedefs(typedef_node)
            if self.typedefs.get(typedef_name) is None:
                self.typedefs[typedef_name] = typedef_code

                if type(typedef_node.type) is c_ast.TypeDecl and type(typedef_node.type.type) is c_ast.Struct:
                    struct = typedef_node.type.type
                    if struct.name and struct.decls is None:
                        structs_found.add(struct.name)
                    else:
                        structs_inside = visitor.get_structs()
                        if struct.name: structs_inside.discard(struct.name)
                        structs_found.update(structs_inside)
                        typedefs_inside = visitor.get_typedefs_used()
                        typedefs_found.update(typedefs_inside)

        if structs_found or typedefs_found:
            self.retrieve_types(structs_found, typedefs_found, visitor)
