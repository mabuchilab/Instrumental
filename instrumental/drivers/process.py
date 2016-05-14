# -*- coding: utf-8 -*-
# Copyright 2016 Nate Bogdanowicz
import re
import warnings
import platform
import logging as log
from enum import Enum
from collections import OrderedDict, namedtuple, defaultdict
import ast
from cStringIO import StringIO
from pycparser import c_parser, c_ast

'__cplusplus', '__linux__', '__APPLE__', '__CVI__', '__TPC__'

TokenType = Enum('TokenType', 'DEFINED IDENTIFIER NUMBER STRING_CONST CHAR_CONST HEADER_NAME '
                 'PUNCTUATOR NEWLINE WHITESPACE LINE_COMMENT BLOCK_COMMENT')
Position = namedtuple('Position', ['row', 'col'])


# For converting from c_ast to Python ast
UNARY_OPS = {'-': ast.USub, '+': ast.UAdd, '!': ast.Not, '~': ast.Invert}
BINARY_OPS = {
    '+': ast.Add, '-': ast.Sub, '*': ast.Mult, '/': ast.Div, '%': ast.Mod, '<<': ast.LShift,
    '>>': ast.RShift, '|': ast.BitOr, '^': ast.BitXor, '&': ast.BitAnd
}
CMP_OPS = {'==': ast.Eq, '!=': ast.NotEq, '<': ast.Lt, '<=': ast.LtE, '>': ast.Gt, '>=': ast.GtE}
BOOL_OPS = {'&&': ast.And, '||': ast.Or}


# For converting from c_ast to Python source str
UNARY_OP_STR = {'+': '+', '-': '-', '!': ' not ', '~': '~'}
BINARY_OP_STR = {
    '+': '+', '-': '-', '*': '*', '/': '/', '<<': '<<', '>>': '>>', '|': '|', '^': '^', '&': '&'
}
CMP_OP_STR = {'==': '==', '!=': '!=', '<': '<', '<=': '<=', '>': '>', '<=': '<='}
BOOL_OP_STR = {'&&': ' and ', '||': ' or '}
ALL_BINOP_STRS = dict(BINARY_OP_STR.items() + CMP_OP_STR.items() + BOOL_OP_STR.items())


class EndOfStreamError(Exception):
    pass


class LexError(Exception):
    pass


class ConvertError(Exception):
    pass


class ParseError(Exception):
    def __init__(self, token, msg):
        msg = "({}:{}) {}".format(token.line, token.col, msg)
        super(ParseError, self).__init__(msg)


class Token(object):
    def __init__(self, type, string, line=0, col=0):
        self.type = type
        self.string = string
        self.line = line
        self.col = col

    def matches(self, other_type, other_string):
        return self.type is other_type and self.string == other_string

    def __str__(self):
        return '{}({})'.format(self.type.name, self.string)

    def __repr__(self):
        return str(self)

for ttype in TokenType:
    setattr(Token, ttype.name, ttype)


class Lexer(object):
    def __init__(self):
        self.regexes = OrderedDict()
        self.ignored = []
        self.line = 1
        self.col = 1
        self.esc_newlines = defaultdict(int)

    def add(self, name, regex_str, ignore=False):
        self.regexes[name] = re.compile(regex_str)
        if ignore:
            self.ignored.append(name)

    def lex(self, f):
        lines = f.read().splitlines()
        joined_lines = []
        continued_line = ''
        c_lineno = 1
        for line in lines:
            if line.endswith("\\"):
                continued_line = continued_line + line[:-1]
                self.esc_newlines[c_lineno] += 1
            else:
                joined_lines.append(continued_line + line)
                continued_line = ''
                c_lineno += 1
        text = '\n'.join(joined_lines)
        return lexer._lex_text(text)

    def _lex_text(self, text):
        tokens = []
        pos = 0
        while pos < len(text):
            token = self.read_token(text, pos)
            if token is None:
                raise LexError("No acceptable token found!")
            if token.type not in self.ignored:
                tokens.append(token)
            pos = pos + len(token.string)

            self.line += token.string.count('\n') + self.esc_newlines.get(self.line, 0)
            self.col = len(token.string.rsplit('\n', 1)[-1]) + 1

        return tokens

    def read_token(self, text, pos):
        """Read the next token from text, starting at pos"""
        best_token = None
        best_size = 0
        for token_type, regex in self.regexes.items():
            match = regex.match(text, pos)
            if match:
                size = match.end() - match.start()
                if size > best_size:
                    best_token = Token(token_type, match.group(0), self.line, self.col)
                    best_size = size
        return best_token


lexer = Lexer()
lexer.add(Token.DEFINED, r"defined")
lexer.add(Token.IDENTIFIER, r"[a-zA-Z_][a-zA-Z0-9_]*")
lexer.add(Token.NUMBER, r'\.?[0-9]([0-9a-zA-Z_.]|([eEpP][+-]))*')
lexer.add(Token.STRING_CONST, r'"([^"\\\n]|\\.)*"')
lexer.add(Token.CHAR_CONST, r"'([^'\\\n]|\\.)*'")
lexer.add(Token.HEADER_NAME, r"<[^>\n]*>")
lexer.add(Token.PUNCTUATOR,
          r"[<>=*/*%&^|+-]=|<<==|>>==|\.\.\.|->|\+\+|--|<<|>>|&&|[|]{2}|##|"
          r"[{}\[\]()<>.&*+-~!/%^|=;:,?#]")
lexer.add(Token.NEWLINE, r"\n", ignore=False)
lexer.add(Token.WHITESPACE, r"[ \t]+", ignore=False)
lexer.add(Token.LINE_COMMENT, r"//.*($|(?=\n))", ignore=False)
lexer.add(Token.BLOCK_COMMENT, r"/\*(.|\n)*?\*/", ignore=False)




class Macro(object):
    def __init__(self, name_token, body):
        self.name = name_token.string
        self.line = name_token.line
        self.col = name_token.col
        self.body = body
        self.py_src = None
        self.depends_on = ()

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, tokens):
        self._body = tokens
        self.depends_on = tuple(t.string for t in tokens if t.type is Token.IDENTIFIER)


class FuncMacro(Macro):
    def __init__(self, name_token, body, args):
        super(FuncMacro, self).__init__(name_token, body)
        self.args = args


class Parser(object):
    def __init__(self, tokens, replacement_map=[]):
        self.tokens = tokens
        self.last_line = tokens[-1].line
        self.replacement_map = replacement_map
        self.out = []
        self.cond_stack = []
        self.cond_done_stack = []
        self.macros = OrderedDict()
        self.func_macros = OrderedDict()
        self.all_macros = OrderedDict()
        self.expand_macros = True
        self.skipping = False
        self.output_defines = False
        self._ignored_tokens = (Token.NEWLINE, Token.WHITESPACE, Token.LINE_COMMENT,
                                Token.BLOCK_COMMENT)

        self.directive_parse_func = {
            'if': self.parse_if,
            'ifdef': self.parse_ifdef,
            'ifndef': self.parse_ifndef,
            'else': self.parse_else,
            'elif': self.parse_elif,
            'endif': self.parse_endif,
            'define': self.parse_define,
            'undef': self.parse_undef,
            'pragma': self.parse_pragma,
            'include': self.parse_include,
        }

    def pop(self, test_type=None, test_string=None, dont_ignore=(), silent=False):
        return self._pop_base(self.tokens, test_type, test_string, dont_ignore, silent,
                              track_lines=True)

    def pop_from(self, tokens, test_type=None, test_string=None, dont_ignore=()):
        return self._pop_base(tokens, test_type, test_string, dont_ignore, silent=True,
                              track_lines=False)

    def _pop_base(self, tokens, test_type=None, test_string=None, dont_ignore=(), silent=True,
                  track_lines=False):
        while True:
            try:
                token = tokens.pop(0)
            except IndexError:
                raise EndOfStreamError

            if not silent and not self.skipping:
                self.out_line.append(token)

            if (token.type in dont_ignore) or (token.type not in self._ignored_tokens):
                break

        log.debug("Popped token {}".format(token))

        if test_type is not None and token.type != test_type:
            raise ParseError(token, "Expected token type {}, got {}".format(test_type, token.type))

        if test_string is not None and token.string != test_string:
            raise ParseError(token, "Expected token string '{}', got '{}'".format(test_string,
                                                                                  token.string))

        return token

    def parse(self, update_cb=None):
        while True:
            try:
                self.parse_next()
            except EndOfStreamError:
                break

            if update_cb:
                update_cb(self.out[-1].line, self.last_line)

        for macro in self.all_macros.values():
            if isinstance(macro, FuncMacro):
                if macro.body:
                    c_src = ''.join(token.string for token in macro.body)
                    try:
                        macro.py_src = c_to_py_src(c_src)
                    except ConvertError as e:
                        raise ParseError(macro, e.message)
            else:
                if self.expand_macros:
                    macro.body = self.macro_expand_2(macro.body)

                macro.dependencies_satisfied = True
                for macro_name in macro.depends_on:
                    if macro_name not in self.macros:
                        macro.dependencies_satisfied = False

                #c_src = ''.join(token.string for token in tokens)
                #val, token = evaluate_c_src(c_src)
                #self.macro_vals[name_token.string] = val

                if macro.body:
                    c_src = ''.join(token.string for token in macro.body)
                    try:
                        macro.py_src = c_to_py_src(c_src)
                    except ConvertError as e:
                        raise ParseError(macro, e.message)

    def parse_next(self):
        self.out_line = []
        token = self.pop(dont_ignore=(Token.NEWLINE,))

        if token.type is Token.NEWLINE:
            if not self.skipping:
                self.out.extend(self.out_line)
        elif token.matches(Token.PUNCTUATOR, '#'):
            dir_token = self.pop()
            parse_directive = self.directive_parse_func[dir_token.string]
            keep_line = parse_directive()

            if keep_line:
                self.out.extend(self.out_line)
        else:
            chunk = [token]
            dont_ignore = (Token.NEWLINE, Token.WHITESPACE, Token.LINE_COMMENT,
                           Token.BLOCK_COMMENT)
            while True:
                if token.type is Token.IDENTIFIER:
                    next_token = self.pop(silent=True, dont_ignore=dont_ignore)
                    chunk.append(next_token)
                    if (next_token.matches(Token.PUNCTUATOR, '(') and
                            token.string in self.func_macros):
                        # Pop tokens until the closing paren
                        arg_lists = [[]]
                        n_parens = 1
                        while n_parens > 0:
                            token = self.pop(silent=True, dont_ignore=dont_ignore)
                            chunk.append(token)
                            if token.string == '(':
                                n_parens += 1
                            elif token.string == ')':
                                n_parens -= 1

                            if token.string == ',' and n_parens == 1:
                                arg_lists.append([])
                            elif n_parens > 0:
                                arg_lists[-1].append(token)
                        token = self.pop(silent=True, dont_ignore=dont_ignore)
                        chunk.append(token)
                    else:
                        token = next_token
                elif token.type is Token.NEWLINE:
                    break  # Done with this line
                else:
                    # Ordinary token
                    token = self.pop(silent=True, dont_ignore=dont_ignore)
                    chunk.append(token)

            # Add to output
            expanded = self.macro_expand_2(chunk)
            if not self.skipping:
                for token in expanded:
                    self.out.append(token)
                    self.perform_replacement()

    def append_to_output(self, token):
        if not self.skipping:
            self.out.append(token)
            self.perform_replacement()

    def perform_replacement(self):
        for test_strings, repl_tokens in self.replacement_map:
            try:
                match = True
                i = 1
                for test_string in reversed(test_strings):
                    token = self.out[-i]
                    while token.type in (Token.WHITESPACE, Token.NEWLINE, Token.BLOCK_COMMENT,
                                         Token.LINE_COMMENT):
                        i += 1
                        token = self.out[-i]

                    if test_string != self.out[-i].string:
                        match = False
                        break
                    i += 1
            except IndexError:
                match = False

            if match:
                for _ in range(i-1):
                    self.out.pop(-1)
                self.out.extend(repl_tokens)
                break  # Only allow a single replacement

    def parse_macro(self):
        token = self.pop()
        return self.macros.get(token.string, None)

    def start_if_clause(self, condition):
        self.cond_stack.append(condition)
        self.cond_done_stack.append(condition)
        self.skipping = not all(self.cond_stack)

    def start_else_clause(self):
        cond_done = self.cond_done_stack[-1]
        self.cond_stack[-1] = not cond_done
        self.cond_done_stack[-1] = True
        self.skipping = not all(self.cond_stack)

    def start_elif_clause(self, elif_cond):
        cond_done = self.cond_done_stack[-1]
        self.cond_stack[-1] = (not cond_done) and elif_cond
        self.cond_done_stack[-1] = cond_done or elif_cond
        self.skipping = not all(self.cond_stack)

    def end_if_clause(self):
        self.cond_stack.pop(-1)
        self.skipping = not all(self.cond_stack)

    def assert_line_empty(self):
        """Pops all tokens up to a newline (or end of stream) and asserts that they're empty
        (either NEWLINE, WHITESPACE, LINE_COMMENT, or BLOCK_COMMENT)
        """
        while True:
            try:
                token = self.pop(dont_ignore=(Token.NEWLINE,))
            except EndOfStreamError:  # End of token stream
                break

            if token.type is Token.NEWLINE:
                break

            if token.type not in (Token.WHITESPACE, Token.LINE_COMMENT, Token.BLOCK_COMMENT):
                raise ParseError(token, "Rest of line should be devoid of any tokens!")

    def pop_until_newline(self, dont_ignore=(), silent=False):
        """Pops all tokens up to a newline (or end of stream) and returns them"""
        tokens = []
        while True:
            try:
                token = self.pop(dont_ignore=(Token.NEWLINE,)+dont_ignore, silent=silent)
            except EndOfStreamError:  # End of token stream
                break

            if token.type is Token.NEWLINE:
                break
            tokens.append(token)
        return tokens

    def parse_if(self):
        value = self.parse_expression(self.pop_until_newline())
        self.start_if_clause(bool(value))
        return False

    def macro_expand_2(self, tokens, blacklist=[], func_blacklist=[]):
        if tokens:
            tokens = tokens[:]  # Copy so we can pop
            token = tokens.pop(0)
        else:
            return []

        expanded = []
        done = False

        while not done:
            if token.type is Token.IDENTIFIER:
                if tokens:
                    next_token = tokens.pop(0)
                else:
                    done = True

                if (not done and next_token.string == '(' and token.string in self.func_macros and
                        token.string not in func_blacklist):
                    # Func-like macro
                    # Pop tokens until the closing paren
                    name_token = token
                    name = token.string
                    macro = self.func_macros[name]
                    arg_lists = [[]]
                    n_parens = 1
                    while n_parens > 0:
                        token = tokens.pop(0)
                        if token.string == '(':
                            n_parens += 1
                        elif token.string == ')':
                            n_parens -= 1

                        if token.string == ',' and n_parens == 1:
                            arg_lists.append([])
                        elif n_parens > 0:
                            arg_lists[-1].append(token)

                    if len(macro.args) != len(arg_lists):
                        raise ParseError(name_token, "Func-like macro needs {} arguments, got "
                                         "{}".format(len(macro.args), len(arg_lists)))

                    # Expand args
                    exp_arg_lists = [self.macro_expand_2(a, blacklist, func_blacklist +
                                                         [token.string]) for a in arg_lists]

                    # Substitute args into body
                    body = []
                    for token in macro.body:
                        if token.type is Token.IDENTIFIER and token.string in macro.args:
                            arg_idx = macro.args.index(token.string)
                            body.extend(exp_arg_lists[arg_idx])
                        else:
                            body.append(token)

                    # Expand body
                    expanded.extend(self.macro_expand_2(body, blacklist, func_blacklist +
                                                        [token.string]))

                    if tokens:
                        token = tokens.pop(0)
                    else:
                        done = True
                else:
                    if token.string in self.macros and token.string not in blacklist:
                        # Object-like macro expand
                        body = self.macros[token.string].body
                        expanded.extend(self.macro_expand_2(body, blacklist + [token.string],
                                                            func_blacklist))
                    else:
                        # Ordinary identifier
                        expanded.append(token)

                    if not done:
                        token = next_token
            else:
                # Ordinary token
                expanded.append(token)
                if tokens:
                    token = tokens.pop(0)
                else:
                    done = True
        return expanded

    def macro_expand_tokens(self, tokens, blacklist=[]):
        expanded = []
        for token in tokens:
            if (token.type is Token.IDENTIFIER and token.string in self.macros and
                    token.string not in blacklist):
                vals = self.macros[token.string].body
                vals = self.macro_expand_tokens(vals, blacklist + [token.string])
                expanded.extend(vals)
            else:
                expanded.append(token)
        return expanded

    def parse_expression(self, tokens):
        tokens = tokens[:]
        expanded = []
        while tokens:
            token = self.pop_from(tokens)
            if token.type is Token.IDENTIFIER:
                if token.string not in self.macros:
                    warnings.warn("Undefined identifier {} in expression, treating as "
                                  "0...".format(token.string))
                    val = [Token(Token.NUMBER, '0')]
                else:
                    val = self.macros[token.string].body
                tokens = val + tokens
            elif token.type is Token.DEFINED:
                token = self.pop_from(tokens)
                if token.matches(Token.PUNCTUATOR, '('):
                    token = self.pop_from(tokens, Token.IDENTIFIER)
                    self.pop_from(tokens, Token.PUNCTUATOR, ')')
                elif token.type != Token.IDENTIFIER:
                    raise ParseError(token, "Need either '(' or identifier after `defined`")
                expanded.append('1' if token.string in self.macros else '0')
            else:
                replacements = {
                    '||': 'or',
                    '&&': 'and',
                    '!': 'not',
                }
                expanded.append(replacements.get(token.string, token.string))

        out = ' '.join(expanded)
        log.debug("Parsed expression is '{}'".format(out))
        return eval(out, {})

    def parse_ifdef(self):
        macro = self.parse_macro()
        self.start_if_clause(macro is not None)
        self.assert_line_empty()
        return False

    def parse_ifndef(self):
        macro = self.parse_macro()
        self.start_if_clause(macro is None)
        self.assert_line_empty()
        return False

    def parse_else(self):
        self.start_else_clause()
        self.assert_line_empty()
        return False

    def parse_elif(self):
        value = self.parse_expression(self.pop_until_newline())
        self.start_elif_clause(bool(value))
        return False

    def parse_endif(self):
        self.end_if_clause()
        self.assert_line_empty()
        return False

    def parse_define(self):
        name_token = self.pop(Token.IDENTIFIER)

        # The VERY NEXT token (including whitespace) must be a paren
        if self.tokens[0].matches(Token.PUNCTUATOR, '('):
            # Func-like macro
            # Param-list is identifiers, separated by commas and optional whitespace
            self.pop()  # '('
            args = []
            needs_comma = False
            while True:
                token = self.pop()
                if token.matches(Token.PUNCTUATOR, ')'):
                    break

                if needs_comma:
                    if token.matches(Token.PUNCTUATOR, ','):
                        needs_comma = False
                    else:
                        raise ParseError(token, "Need comma in arg list")
                elif token.type is Token.IDENTIFIER:
                    args.append(token.string)
                    needs_comma = True
                else:
                    raise ParseError(token, "Invalid token {} in arg list".format(token))

            dont_ignore = (Token.WHITESPACE, Token.BLOCK_COMMENT, Token.LINE_COMMENT)
            tokens = self.pop_until_newline(silent=True, dont_ignore=dont_ignore)

            if not self.skipping:
                preamble, body, postamble = self._split_body(tokens)
                macro = FuncMacro(name_token, body, args)
                self.func_macros[name_token.string] = macro
                self.all_macros[name_token.string] = macro
        else:
            # Object-like macro
            dont_ignore = (Token.WHITESPACE, Token.BLOCK_COMMENT, Token.LINE_COMMENT)
            tokens = self.pop_until_newline(silent=True, dont_ignore=dont_ignore)

            if not self.skipping:
                preamble, body, postamble = self._split_body(tokens)
                macro = Macro(name_token, body)
                self.macros[name_token.string] = macro
                self.all_macros[name_token.string] = macro

        # Output all the tokens we suppressed
        self.out_line.extend(tokens)
        self.out_line.append(Token(Token.NEWLINE, '\n'))
        return self.output_defines

    @staticmethod
    def _split_body(tokens):
        preamble, postamble = [], []
        for token in tokens:
            if token.type in (Token.WHITESPACE, Token.BLOCK_COMMENT, Token.LINE_COMMENT):
                preamble.append(token)
            else:
                break

        for token in reversed(tokens):
            if token.type in (Token.WHITESPACE, Token.BLOCK_COMMENT, Token.LINE_COMMENT):
                postamble.insert(0, token)
            else:
                break

        start = len(preamble)
        if start == len(tokens):
            postamble = []
        stop = len(tokens) - len(postamble)

        return preamble, tokens[start:stop], postamble

    def parse_undef(self):
        name_token = self.pop(Token.IDENTIFIER)
        self.assert_line_empty()

        if not self.skipping:
            try:
                del self.macros[name_token.string]
            except KeyError:
                pass
        return True

    def parse_pragma(self):
        self.pop_until_newline()  # Ignore pragmas
        return False

    def parse_include(self):
        self.pop_until_newline()  # Ignore includes
        return False


# Ordered by precedence - should usually be longest match first
replacement_maps = {
    'Windows': [
        (['unsigned', '__int8'], [Token(Token.IDENTIFIER, 'uint8_t')]),
        (['__int8'], [Token(Token.IDENTIFIER, 'int8_t')]),
        (['unsigned', '__int16'], [Token(Token.IDENTIFIER, 'uint16_t')]),
        (['__int16'], [Token(Token.IDENTIFIER, 'int16_t')]),
        (['unsigned', '__int32'], [Token(Token.IDENTIFIER, 'uint32_t')]),
        (['__int32'], [Token(Token.IDENTIFIER, 'int32_t')]),
        (['unsigned', '__int64'], [Token(Token.IDENTIFIER, 'uint64_t')]),
        (['__int64'], [Token(Token.IDENTIFIER, 'int64_t')]),
    ],
    'Linux': [],
    'Darwin': [],
}


def write_tokens_simple(file, parser):
    for token in parser.out:
        file.write(token.string)


def write_tokens(file, parser, add_newlines=True):
    needs_space = False
    accept_newline = False
    for token in parser.out:
        if token.type is Token.NEWLINE:
            if accept_newline:
                file.write('\n')
            needs_space = False
            accept_newline = False
        elif token.type not in (Token.WHITESPACE, Token.LINE_COMMENT, Token.BLOCK_COMMENT):
            this_needs_space = not (token.string in '+-#,;{}[]')

            if needs_space and this_needs_space:
                file.write(' ')
            file.write(token.string)

            needs_space = this_needs_space
            if token.string in ';#':
                accept_newline = True


def c_to_py_ast(c_src):
    """Convert C expression source str to a Python ast.Expression"""
    expr_node = src_to_c_ast(c_src)
    py_node = ast.fix_missing_locations(ast.Expression(to_py_ast(expr_node)))
    codeobj = compile(py_node, '<string>', 'eval')
    return eval(codeobj, {})


def c_to_py_src(c_src):
    """Convert C expression source str to a Python source str"""
    expr_node = src_to_c_ast(c_src)
    return ''.join(to_py_src(expr_node))


def src_to_c_ast(source):
    """Convert C expression source str to a c_ast expression node"""
    if ';' in source:
        raise Exception("C-to-Py supports only expressions, not statements")
    parser = c_parser.CParser()
    tree = parser.parse('int main(void){' + source + ';}')
    expr_node = tree.ext[0].body.block_items[0]
    return expr_node


def evaluate_c_src(src):
    val = c_to_py_ast(src)

    if isinstance(val, bool):
        result = Token(Token.NUMBER, str(int(val)))
    elif isinstance(val, (int, float)):
        result = Token(Token.NUMBER, str(val))
    elif isinstance(val, float):
        result = Token(Token.STRING_CONST, '"{}"'.format(val))
    else:
        raise Exception("Unknown result {}".format(val))

    return val, result


def to_py_ast(node):
    """Convert a c_ast expression into a Python ast object"""
    if isinstance(node, c_ast.UnaryOp):
        py_expr = to_py_ast(node.expr)
        py_node = ast.UnaryOp(UNARY_OPS[node.op](), py_expr)

    elif isinstance(node, c_ast.BinaryOp):
        py_left = to_py_ast(node.left)
        py_right = to_py_ast(node.right)
        if node.op in BINARY_OPS:
            py_node = ast.BinOp(py_left, BINARY_OPS[node.op](), py_right)
        elif node.op in CMP_OPS:
            py_node = ast.Compare(py_left, CMP_OPS[node.op](), py_right)
        elif node.op in BOOL_OPS:
            py_node = ast.BoolOp(py_left, py_right, BOOL_OPS[node.op]())
        else:
            raise ConvertError("Unsupported binary operator '{}'".format(node.op))

    elif isinstance(node, c_ast.Constant):
        if node.type == 'int':
            py_node = ast.Num(int(node.value.rstrip('UuLl'), base=0))
        elif node.type == 'float':
            # Not including the hex stuff from C++17
            py_node = ast.Num(float(node.value.rstrip('FfLl')))
        elif node.type == 'string':
            py_node = ast.Str(node.value.strip('"'))
        else:
            raise ConvertError("Unsupported constant type '{}'".format(node.type))

    elif isinstance(node, c_ast.TernaryOp):
        py_node = ast.IfExp(to_py_ast(node.cond), to_py_ast(node.iftrue), to_py_ast(node.iffalse))

    else:
        raise ConvertError("Unsupported c_ast type {}".format(type(node)))

    return py_node


# TODO: Convert this to using a generator pattern like CGenerator?
def to_py_src(node):
    """Convert a c_ast expression into a Python source code string list"""
    if isinstance(node, c_ast.UnaryOp):
        py_expr = to_py_src(node.expr)

        if node.op == 'sizeof':
            py_src = ['ffi.sizeof('] + py_expr + [')']
        else:
            py_src = ['(', UNARY_OP_STR[node.op]] + py_expr + [')']

    elif isinstance(node, c_ast.BinaryOp):
        py_left = to_py_src(node.left)
        py_right = to_py_src(node.right)

        # TODO: account for the Python/C99 difference of / and %
        if node.op in ALL_BINOP_STRS:
            py_src = ['('] + py_left + [ALL_BINOP_STRS[node.op]] + py_right + [')']
        else:
            raise ConvertError("Unsupported binary operator '{}'".format(node.op))

    elif isinstance(node, c_ast.Constant):
        if node.type == 'int':
            py_src = [node.value.rstrip('UuLl')]
        elif node.type == 'float':
            py_src = [node.value.rstrip('FfLl')]
        elif node.type == 'string':
            py_src = [node.value]
        else:
            raise ConvertError("Unsupported constant type '{}'".format(node.type))

    elif isinstance(node, c_ast.ID):
        py_src = [node.name]

    elif isinstance(node, c_ast.TernaryOp):
        py_src = (['('] + to_py_src(node.iftrue) + [' if '] + to_py_src(node.cond) + [' else '] +
                  to_py_src(node.iffalse) + [')'])

    elif isinstance(node, c_ast.FuncCall):
        args = ', '.join(''.join(to_py_src(e)) for e in node.args.exprs)
        py_src = [node.name.name, '(', args, ')']

    elif isinstance(node, c_ast.Cast):
        py_type_map = {'int': 'int', 'long': 'int', 'float': 'float', 'double': 'float'}
        py_type = py_type_map[''.join(node.to_type.type.type.names)]
        py_src = [py_type, '('] + to_py_src(node.expr) + [')']

    else:
        raise ConvertError("Unsupported c_ast type {}".format(type(node)))

    return py_src


def process_file(in_fname, out_fname, minify):
    with open(in_fname, 'rU') as f:
        tokens = lexer.lex(f)

    parser = Parser(tokens, replacement_maps.get(platform.system()))
    parser.parse()

    with open(out_fname, 'w') as f:
        if minify:
            write_tokens(f, parser)
        else:
            write_tokens_simple(f, parser)

    with open('macros.py', 'w') as f:
        #f.writelines("{} = {}\n".format(name, val) for name, val in parser.macro_vals.items())
        for name, macro in parser.macros.items():
            if not macro.dependencies_satisfied:
                f.write("# ")
            f.write("{} = {}\n".format(name, macro.py_src))


def process_header(in_fname, minify, update_cb=None):
    with open(in_fname, 'rU') as f:
        tokens = lexer.lex(f)

    parser = Parser(tokens, replacement_maps.get(platform.system()))
    parser.parse(update_cb=update_cb)

    header_io = StringIO()
    if minify:
        write_tokens(header_io, parser)
    else:
        write_tokens_simple(header_io, parser)

    macro_io = StringIO()
    macro_io.write("# Generated macro definitions\n")
    for name, macro in parser.all_macros.items():
        if isinstance(macro, FuncMacro):
            arg_list = ', '.join(macro.args)
            #macro_io.write("def {}({}):\n".format(name, arg_list))
            #macro_io.write("    return {}\n".format(macro.py_src))
            #macro_io.write("defs.{} = {}\n".format(name, name))
            macro_io.write("defs.{} = lambda {}: {}\n".format(name, arg_list, macro.py_src))
        else:
            if not macro.dependencies_satisfied:
                macro_io.write("# ")
            macro_io.write("defs.{} = {}\n".format(name, macro.py_src))

    return header_io.getvalue(), macro_io.getvalue()


if __name__ == '__main__':
    process_file('./NIDAQmx.h', './NIDAQmx_clean.h', minify=True)
    #process_file('uc480.h', 'uc480_clean.h', minify=True)



# NOTES
# =====

# - pycparser needs typedefs to be able to parse properly, e.g. "(HCAM)0" won't parse unless HCAM
# has been typedef'd (or already macro expanded to a valid type)
