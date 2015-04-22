'''
Created on Apr 22, 2015

@author: Johnson Earls
'''

import ast
import re
import sys

__all__ = ('ASTFormatter',)

########################################################################
# The ASTFormatter class walks an AST and produces properly formatted
# python code for that AST.

class ASTFormatter(ast.NodeVisitor):
    def __init__(self):
        self.context = [ast.Module]
        self.indent = 0

    ####################################################################
    # helper methods

    def visit(self, node):
        self.context.insert(0, node.__class__)
        retval = super(ASTFormatter, self).visit(node)
        self.context.pop(0)
        return retval

    def process_body(self, stmtlist, indent=""):
        self.indent = len(indent)
        content = []
        for stmt in stmtlist:
            stmts = self.visit(stmt)
            if not isinstance(stmts, list):
                stmts = [stmts]
            content += ["%s%s" % (indent, stmt) for stmt in stmts]
        return content

    def process_child(self, nodelist):
        if not isinstance(nodelist, (list, tuple)):
            nodelist = [nodelist]
        return [self.visit(node) for node in nodelist]

    def flatten_one(self, deeplist):
        retval = []
        for item in deeplist:
            if isinstance(item, list):
                retval.extend(item)
            else:
                retval.append(item)
        return retval

    seenTypes = set()

    def generic_visit(self, node):
        if type(node) not in self.seenTypes:
            print >> sys.stderr, repr(node)
            self.seenTypes.add(type(node))
        try:
            children = "(%s)" % (",".join(self.flatten_one([self.process_child(getattr(node, field)) for field in node._fields])),)
        except AttributeError:
            children = ""
        if isinstance(node, ast.stmt):
            return "#%s#%s\n" % (node.__class__.__name__, children)
        # should be an expr at this point?
        return "#%s#%s" % (node.__class__.__name__, children)

    ####################################################################
    # precedence of expression operators/nodes.
    # each precedence is an integer, with higher values for
    # higher precedence operators.
    
    _precedence_list = (
        (ast.Lambda,),
        (ast.IfExp,),
        (ast.Or,),
        (ast.And,),
        (ast.Not,),
        (ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.NotEq, ast.Eq, ast.Compare, ),
        (ast.BitOr,),
        (ast.BitXor,),
        (ast.BitAnd,),
        (ast.LShift, ast.RShift,),
        (ast.Add, ast.Sub,),
        (ast.Mult, ast.Div, ast.Mod, ast.FloorDiv,),
        (ast.UAdd, ast.USub, ast.Invert,),
        (ast.Pow,),
        (ast.Subscript, ast.Slice, ast.Call, ast.Attribute,),
        (ast.Tuple, ast.List, ast.Dict, ast.Repr,),
    )
    _precedence = dict([(j, i) for i in xrange(len(_precedence_list)) for j in _precedence_list[i]]);

    def _parens(self, operand, operator):
        operand_str = self.visit(operand)
        if isinstance(operand, ast.BinOp):
            operand = operand.op
        elif isinstance(operand, ast.BoolOp):
            operand = operand.op
        operand = type(operand)
        operator = type(operator)
        if operand in self._precedence and operator in self._precedence:
            if self._precedence[operand] < self._precedence[operator]:
                operand_str = "(%s)" % (operand_str,)
        return operand_str

    ####################################################################
    # expression methods - these return a single string with no newline

    def visit_alias(self, node):
        if node.asname is None:
            return node.name
        else:
            return "%s as %s" % (node.name, node.asname)

    def visit_Add(self, node):
        return "+"

    def visit_And(self, node):
        return "and"

    def visit_arguments(self, node):
        args = ["%s" % (self.visit(arg),) for arg in node.args[:len(node.args) - len(node.defaults)]]
        defargs = ["%s=%s" % (self.visit(arg), self.visit(default)) for (arg, default) in zip(node.args[-len(node.defaults):], node.defaults)]
        if node.vararg:
            vararg = ["*" + self.visit(node.vararg)]
        else:
            vararg = []
        if node.kwarg:
            kwarg = ["**" + self.visit(node.kwarg)]
        else:
            kwarg = []
        return "(%s)" % (",".join(args + defargs + vararg + kwarg),)

    def visit_Attribute(self, node):
        return "%s.%s" % (self._parens(node.value, node), node.attr)

    def visit_BinOp(self, node):
        return (" %s " % (self.visit(node.op),)).join([self._parens(operand, node.op) for operand in (node.left, node.right)])

    def visit_BitAnd(self, node):
        return "&"

    def visit_BitOr(self, node):
        return "|"

    def visit_BitXor(self, node):
        return "^"

    def visit_BoolOp(self, node):
        return (" %s " % (self.visit(node.op),)).join([self._parens(operand, node.op) for operand in node.values])

    def visit_Call(self, node):
        args = [self.visit(arg) for arg in node.args]
        keywords = [self.visit(keyword) for keyword in node.keywords]
        if node.starargs:
            starargs = ["*%s" % (self.visit(node.starargs),)]
        else:
            starargs = []
        if node.kwargs:
            kwargs = ["**%s" % (self.visit(node.kwargs),)]
        else:
            kwargs = []
        return "%s(%s)" % (self.visit(node.func), ", ".join(args + keywords + starargs + kwargs))

    def visit_Compare(self, node):
        return "%s %s" % (self.visit(node.left), " ".join(["%s %s" % (self.visit(op), self.visit(right)) for (op, right) in zip(node.ops, node.comparators)]))

    def visit_comprehension(self, node):
        ifs = "".join([" if %s" % (self.visit(ifpart),) for ifpart in node.ifs])
        return "for %s in %s%s" % (self.visit(node.target), self.visit(node.iter), ifs)

    def visit_Dict(self, node):
        return "{%s}" % (", ".join(["%s:%s" % (self.visit(key), self.visit(value)) for (key, value) in zip(node.keys, node.values)]),)

    def visit_Div(self, node):
        return "/"

    def visit_Ellipsis(self, node):
        return "..."

    def visit_Eq(self, node):
        return "=="

    def visit_ExtSlice(self, node):
        return ", ".join([self.visit(dim) for dim in node.dims])

    def visit_FloorDiv(self, node):
        return "//"

    def visit_GeneratorExp(self, node):
        if node.generators:
            return "(%s %s)" % (self.visit(node.elt), " ".join(self.visit(generator) for generator in node.generators),)
        return "(%s)" % (self.visit(node.elt),)

    def visit_Gt(self, node):
        return ">"

    def visit_GtE(self, node):
        return ">="

    def visit_IfExp(self, node):
        return "%s if %s else %s" % (self.visit(node.body), self.visit(node.test), self.visit(node.orelse))

    def visit_In(self, node):
        return "in"

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Invert(self, node):
        return "~"

    def visit_Is(self, node):
        return "is"

    def visit_IsNot(self, node):
        return "is not"

    def visit_keyword(self, node):
        return "%s=%s" % (node.arg, self.visit(node.value))

    def visit_Lambda(self, node):
        return "lambda %s:%s" % (self.visit(node.args), self.visit(node.body))

    def visit_List(self, node):
        return "[%s]" % (", ".join([self.visit(elt) for elt in node.elts]),)

    def visit_ListComp(self, node):
        if node.generators:
            return "[%s %s]" % (self.visit(node.elt), " ".join(self.visit(generator) for generator in node.generators),)
        return "[%s]" % (self.visit(node.elt),)

    def visit_Lt(self, node):
        return "<"

    def visit_LtE(self, node):
        return "<="

    def Visit_LShift(self, node):
        return "<<"

    def visit_Mod(self, node):
        return "%"

    def visit_Mult(self, node):
        return "*"

    def visit_Name(self, node):
        return node.id

    def visit_Not(self, node):
        return "not"

    def visit_NotEq(self, node):
        return "!="

    def visit_NotIn(self, node):
        return "not in"

    def visit_Num(self, node):
        return repr(node.n)

    def visit_Or(self, node):
        return "or"

    def visit_Pow(self, node):
        return "**"

    def visit_Repr(self, node):
        return "repr(%s)" % (self.visit(node.value),)

    def visit_RShift(self, node):
        return ">>"

    def visit_Slice(self, node):
        if node.lower:
            lower = self.visit(node.lower)
        else:
            lower = ""
        if node.upper:
            upper = self.visit(node.upper)
        else:
            upper = ""
        if node.step:
            return ":".join([lower, upper, self.visit(node.step)])
        else:
            return ":".join([lower, upper])

    re_docstr_escape = re.compile(r'([\\"])')
    re_docstr_remove_blank_front = re.compile(r'^[ \n]*')
    re_docstr_remove_blank_back = re.compile(r'[ \n]*$')
    re_docstr_indent = re.compile(r'^( *).*')
    def visit_Str(self, node):
        if self.context[1] == ast.Expr:
            # process docstring
            docstring = self.re_docstr_remove_blank_front.sub('',
                    self.re_docstr_remove_blank_back.sub('',
                            self.re_docstr_escape.sub(r'\\\1', node.s))).split('\n')
            if len(docstring) > 1:
                docstr_indents = [
                    len(self.re_docstr_indent.sub(r'\1', ds)) for ds in [
                        ds.rstrip() for ds in docstring[1:]
                    ] if ds
                ]
                docstr_indent = min(docstr_indents)
                docstring = docstring[0:1] + ["%*s%s" % (self.indent, "", ds[docstr_indent:]) for ds in docstring[1:]]
            return '"""%s\n"""' % ("\n".join(docstring),)
        else:
            return repr(node.s)

    def visit_Sub(self, node):
        return "-"

    def visit_Subscript(self, node):
        return "%s[%s]" % (self.visit(node.value), self.visit(node.slice))

    def visit_Tuple(self, node):
        if len(node.elts) == 1:
            return "(%s,)" % (self.visit(node.elts[0]),)
        return "(%s)" % (", ".join([self.visit(elt) for elt in node.elts]),)

    def visit_UAdd(self, node):
        return "+"

    def visit_USub(self, node):
        return "-"

    def visit_UnaryOp(self, node):
        return "%s %s" % (self.visit(node.op), self.visit(node.operand))

    def visit_Yield(self, node):
        if node.value:
            return "yield %s" % (self.visit(node.value),)
        return "yield"

    ####################################################################
    # statement methods - these return either a single string or a list
    # of strings, all terminated with a `\n` newline.

    def visit_Assert(self, node):
        if node.msg is None:
            msg = ""
        else:
            msg = "," + self.visit(node.msg)
        return "assert %s%s\n" % (self.visit(node.test), msg)

    def visit_Assign(self, node):
        return "%s = %s\n" % (",".join([self.visit(target) for target in node.targets]), self.visit(node.value))

    def visit_AugAssign(self, node):
        return "%s %s= %s\n" % (self.visit(node.target), self.visit(node.op), self.visit(node.value))

    def visit_Break(self, node):
        return "break\n"

    def visit_ClassDef(self, node):
        decorators = [self.visit(dec) for dec in node.decorator_list]
        supers = node.bases
        if supers is None or len(supers) == 0:
            supers = ""
        else:
            supers = "(%s)" % (", ".join([self.visit(super_) for super_ in supers]))
        classdef = ["class %s%s:\n" % (node.name, supers)]
        classbody = self.process_body(node.body, "    ")
        return decorators + classdef + classbody

    def visit_Continue(self, node):
        return "continue\n"

    def visit_Delete(self, node):
        return "del %s\n" % (",".join([self.visit(target) for target in node.targets]),)

    def visit_ExceptHandler(self, node):
        if not node.type:
            return ["except:\n"] + self.process_body(node.body, "    ")
        if node.name:
            return ["except %s,%s:\n" % (self.visit(node.type), self.visit(node.name))] + self.process_body(node.body, "    ")
        return ["except %s:\n" % (self.visit(node.type),)] + self.process_body(node.body, "    ")

    def visit_Exec(self, node):
        inglobals, inlocals = "", ""
        if self.inglobals is not None:
            inglobals = " in %s" % (self.visit(node.globals),)
            if self.inlocals is not None:
                inlocals = ", %s" % (self.visit(node.locals),)
        return "exec %s%s%s\n" % (self.visit(node.body), inglobals, inlocals)

    def visit_Expr(self, node):
        return self.visit(node.value) + "\n"

    def visit_For(self, node):
        if node.orelse is None or len(node.orelse) == 0:
            orelse = []
        else:
            orelse = ["else:\n"] + self.process_body(node.orelse, "    ")
        return [
            "for %s in %s:\n" % (
                self.visit(node.target),
                self.visit(node.iter),
            )
        ] + self.process_body(node.body, "    ") + orelse

    def visit_FunctionDef(self, node):
        decorators = [self.visit(dec) for dec in node.decorator_list]
        funcdef = ["def %s%s:\n" % (node.name, self.visit(node.args))]
        funcbody = self.process_body(node.body, "    ")
        return decorators + funcdef + funcbody

    def visit_Global(self, node):
        return "global %s\n" % (",".join([self.visit(name) for name in node.names]),)

    def visit_If(self, node):
        content = ["if %s:\n" % (self.visit(node.test),)] + self.process_body(node.body, "    ")
        if node.orelse is not None and len(node.orelse) > 0:
            if isinstance(node.orelse[0], ast.If):
                orelse = self.process_body(node.orelse, "")
                orelse[0] = "el" + orelse[0]
            else:
                orelse = ["else:\n"] + self.process_body(node.orelse, "    ")
            content.extend(orelse)
        return content

    def visit_Import(self, node):
        return "import %s\n" % (self.visit(node.names),)
    
    def visit_ImportFrom(self, node):
        return "from %s import %s\n" % (node.module, ", ".join([self.visit(name) for name in node.names]),) 

    def visit_Module(self, node):
        return self.process_body(node.body)

    def visit_Pass(self, node):
        return "pass\n"

    def visit_Print(self, node):
        if node.dest is None:
            dest = ""
        else:
            dest = ">> %s, " % (self.visit(node.dest),)
        if node.nl:
            nl = ""
        else:
            nl = ","
        return "print %s%s%s\n" % (dest, ", ".join([self.visit(value) for value in node.values]), nl)

    def visit_Raise(self, node):
        if node.tback is not None:
            params = (node.type, node.inst, node.tback)
        elif node.inst is not None:
            params = (node.type, node.inst)
        elif node.type is not None:
            params = (node.type,)
        else:
            params = ""
        if len(params):
            params = " " + ",".join([self.visit(param) for param in params])
        return "raise%s\n" % (params,)

    def visit_Return(self, node):
        if node.value is not None:
            return "return %s\n" % (self.visit(node.value),)
        return "return\n"

    def visit_TryExcept(self, node):
        retval = ["try:\n"] + self.process_body(node.body, "    ")
        for handler in node.handlers:
            retval.extend(self.visit(handler))
        if node.orelse is not None and len(node.orelse) > 0:
            retval.extend(["else:\n"] + self.process_body(node.orelse, "    "))
        return retval

    def visit_TryFinally(self, node):
        return ["try:\n"] + self.process_body(node.body, "    ") + ["finally:\n"] + self.process_body(node.finalbody, "    ")

    def visit_While(self, node):
        if node.orelse is None or len(node.orelse) == 0:
            orelse = []
        else:
            orelse = ["else:\n"] + self.process_body(node.orelse, "    ")
        return [
            "while %s:\n" % (
                self.visit(node.test),
            )
        ] + self.process_body(node.body, "    ") + orelse

    def visit_With(self, node):
        if node.optional_vars is None:
            asvars = ""
        else:
            asvars = " as %s" % (self.visit(node.optional_vars),)
        return [
            "with %s%s:\n" % (self.visit(node.context_expr), asvars)
        ] + self.process_body(node.body, "    ")
