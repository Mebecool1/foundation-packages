#!/usr/bin/env python3
#please remove the .lb prefix so that you can run it with python3!
import sys, os, subprocess

class TokenType:
    NUMBER = "NUMBER"; STRING = "STRING"; IDENTIFIER = "IDENTIFIER"
    IF = "IF"; THEN = "THEN"; ELSE = "ELSE"; END = "END"
    WHILE = "WHILE"; DO = "DO"; FUNCTION = "FUNCTION"; RETURN = "RETURN"
    PRINT = "PRINT"; SCANF = "SCANF"; INT = "INT"; STR = "STR"; FLOAT = "FLOAT"
    FOPEN = "FOPEN"; FWRITE = "FWRITE"; FCLOSE = "FCLOSE"; HLT = "HLT"
    ASSIGN = "ASSIGN"; PLUS = "PLUS"; MINUS = "MINUS"; MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"; EQ = "EQ"; NE = "NE"; LT = "LT"; GT = "GT"; MOD = "MOD"
    LPAREN = "LPAREN"; RPAREN = "RPAREN"; LBRACE = "LBRACE"; RBRACE = "RBRACE"
    COMMA = "COMMA"; EOF = "EOF"

class Token:
    def __init__(self, ttype, value): self.type = ttype; self.value = value

class Lexer:
    def __init__(self, source):
        self.source = source; self.pos = 0
        self.keywords = {
            'if': TokenType.IF, 'then': TokenType.THEN, 'else': TokenType.ELSE,
            'end': TokenType.END, 'while': TokenType.WHILE, 'do': TokenType.DO,
            'function': TokenType.FUNCTION, 'return': TokenType.RETURN,
            'print': TokenType.PRINT, 'scanf': TokenType.SCANF,
            'int': TokenType.INT, 'str': TokenType.STR, 'float': TokenType.FLOAT,
            'fopen': TokenType.FOPEN, 'fwrite': TokenType.FWRITE, 'fclose': TokenType.FCLOSE,
            'hlt': TokenType.HLT
        }

    def tokenize(self):
        tokens = []
        while self.pos < len(self.source):
            char = self.source[self.pos]
            if char.isspace(): self.pos += 1; continue
            if char == '#':
                while self.pos < len(self.source) and self.source[self.pos] != '\n': self.pos += 1
                continue
            if char.isalpha() or char == '_':
                start = self.pos
                while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'): self.pos += 1
                val = self.source[start:self.pos]
                tokens.append(Token(self.keywords.get(val, TokenType.IDENTIFIER), val))
            elif char.isdigit():
                start = self.pos
                while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'): self.pos += 1
                tokens.append(Token(TokenType.NUMBER, self.source[start:self.pos]))
            elif char in ('"', "'"):
                q = char; self.pos += 1; start = self.pos
                while self.pos < len(self.source) and self.source[self.pos] != q: self.pos += 1
                val = self.source[start:self.pos]; self.pos += 1
                tokens.append(Token(TokenType.STRING, val))
            else:
                double = self.source[self.pos:self.pos+2]
                ops2 = {'==': TokenType.EQ, '!=': TokenType.NE, '<=': TokenType.LT, '>=': TokenType.GT}
                if double in ops2:
                    tokens.append(Token(ops2[double], double)); self.pos += 2
                else:
                    ops1 = {'+': TokenType.PLUS, '-': TokenType.MINUS, '*': TokenType.MULTIPLY, '/': TokenType.DIVIDE,
                           '%': TokenType.MOD, '=': TokenType.ASSIGN, '(': TokenType.LPAREN, ')': TokenType.RPAREN,
                           '{': TokenType.LBRACE, '}': TokenType.RBRACE, ',': TokenType.COMMA, '<': TokenType.LT, '>': TokenType.GT}
                    if char in ops1: tokens.append(Token(ops1[char], char))
                    self.pos += 1
        tokens.append(Token(TokenType.EOF, None))
        return tokens

class CTranspiler:
    def __init__(self, tokens):
        self.tokens = tokens; self.pos = 0
        self.headers = [
    "#include <stdio.h>\n", 
    "#include <stdbool.h>\n", 
    "#include <stdlib.h>\n", 
    "#include <unistd.h>\n", 
    "#include <math.h>\n",
    "#include <time.h>\n"
    "#include <string.h>\n"
    "char _lb_buf[64];\n", 
    "static inline char* _lb_f(float x) { sprintf(_lb_buf, \"%g\", (double)x); return _lb_buf; }\n", 
    "static inline char* _lb_s(char* x) { return x; }\n",
    "#define TO_STR(x) _Generic((x), char*: _lb_s, const char*: _lb_s, default: _lb_f)(x)\n"
]
        self.functions = []; self.main_body = []; self.var_types = {}

    def current(self): return self.tokens[self.pos]
    def advance(self): t = self.current(); self.pos += 1; return t
    def expect(self, ttype, shut):
        if self.current().type == ttype: return self.advance()
        if not shut:
            raise Exception(f"Syntax Error: Expected {ttype}")
        return None

    def safe_name(self, name):
        c_keywords = {'double', 'int', 'float', 'char', 'while', 'if', 'return', 'break', 'FILE'}
        return f"var_{name}" if name in c_keywords else name

    def transpile(self):
        while self.current().type != TokenType.EOF:
            if self.current().type == TokenType.FUNCTION: self.functions.append(self.parse_function())
            else:
                stmt = self.parse_statement()
                if stmt: self.main_body.append(stmt)
        res = "\n".join(self.headers) + "\n" + "\n".join(self.functions) + "\n"
        res += "int main(int argc, char** argv) {\n    " + "\n    ".join(self.main_body) + "\n    return 0;\n}"
        return res

    def parse_statement(self):
        t = self.current()
        # --- HLT (Wait ms) ---
        if t.type == TokenType.HLT:
            self.advance(); self.expect(TokenType.LPAREN, False)
            ms = self.parse_expr()
            self.expect(TokenType.RPAREN, False)
            # usleep takes microseconds, so we multiply ms * 1000
            return f"usleep(({ms}) * 1000);"

        # --- File I/O (Safe Mode) ---
        if t.type == TokenType.FOPEN:
            self.advance(); self.expect(TokenType.LPAREN, False)
            fname = self.parse_expr(); self.expect(TokenType.COMMA, False); mode = self.parse_expr(); self.expect(TokenType.RPAREN, False)
            return f'FILE* handle = fopen({fname}, {mode});\n    if (handle == NULL) {{ printf("FAIL: %s\\n", {fname}); exit(1); }}'

        if t.type == TokenType.FWRITE:
            self.advance(); self.expect(TokenType.LPAREN, False); content = self.parse_expr(); self.expect(TokenType.RPAREN, False)
            fmt = '"%s"' if '"' in str(content) else '"%g"'
            return f'if(handle) {{ fprintf(handle, {fmt}, {content}); fflush(handle); }}'

        if t.type == TokenType.FCLOSE:
            self.advance(); self.expect(TokenType.LPAREN, False); self.expect(TokenType.RPAREN, False)
            return "if(handle) fclose(handle);"

        # --- Standard Logic ---
        if t.type in (TokenType.INT, TokenType.FLOAT, TokenType.STR):
            vtype_raw = self.advance().value
            vtype = "char*" if vtype_raw == "str" else vtype_raw
            name = self.safe_name(self.expect(TokenType.IDENTIFIER, False).value)
            self.var_types[name] = vtype_raw
            val = ""
            if self.current().type == TokenType.ASSIGN:
                self.advance(); val = f" = {self.parse_expr()}"
            return f"{vtype} {name}{val};"

        if t.type == TokenType.PRINT:
            self.advance(); self.expect(TokenType.LPAREN, False)
            exprs = []
            while self.current().type != TokenType.RPAREN:
                exprs.append(self.parse_expr())
                if self.current().type == TokenType.COMMA: self.advance()
            self.expect(TokenType.RPAREN, False)
            calls = [f'printf("%s", TO_STR({e}))' for e in exprs]
            return "; ".join(calls) + ";"

        if t.type == TokenType.IF:
            self.advance(); cond = self.parse_expr(); self.expect(TokenType.THEN, False)
            body = []
            while self.current().type not in (TokenType.ELSE, TokenType.END, TokenType.EOF):
                s = self.parse_statement()
                if s: body.append("    " + s)
            else_part = ""
            if self.current().type == TokenType.ELSE:
                self.advance(); e_body = []
                while self.current().type not in (TokenType.END, TokenType.EOF):
                    s = self.parse_statement()
                    if s: e_body.append("    " + s)
                else_part = " else {\n    " + "\n    ".join(e_body) + "\n}"
            self.expect(TokenType.END, False)
            return f"if ({cond}) {{\n    " + "\n    ".join(body) + "\n}" + else_part

        if t.type == TokenType.WHILE:
            self.advance(); cond = self.parse_expr(); self.expect(TokenType.DO, False)
            body = []
            while self.current().type not in (TokenType.END, TokenType.EOF):
                s = self.parse_statement()
                if s: body.append("    " + s)
            self.expect(TokenType.END, False)
            return f"while ({cond}) {{\n    " + "\n    ".join(body) + "\n}"

        if t.type == TokenType.IDENTIFIER:
            name = self.safe_name(self.advance().value)
            if self.current().type == TokenType.ASSIGN:
                self.advance(); return f"{name} = {self.parse_expr()};"
            if self.current().type == TokenType.LPAREN:
                self.advance(); args = []
                while self.current().type != TokenType.RPAREN:
                    args.append(self.parse_expr()); 
                    if self.current().type == TokenType.COMMA: self.advance()
                self.expect(TokenType.RPAREN, False); return f"{name}({', '.join(args)});"

        if t.type == TokenType.SCANF:
            self.advance(); self.expect(TokenType.LPAREN, False); name = self.safe_name(self.expect(TokenType.IDENTIFIER, False).value); self.expect(TokenType.RPAREN, False)
            fmt = "%d" if self.var_types.get(name) == "int" else "%f"
            return f'scanf("{fmt}", &{name});'

        if t.type == TokenType.RETURN: self.advance(); return f"return {self.parse_expr()};"
        self.advance(); return ""

    def parse_expr(self):
        left = self.parse_primary()
        ops = (TokenType.PLUS, TokenType.MINUS, TokenType.EQ, TokenType.LT, TokenType.GT, TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MOD)
        while self.current().type in ops:
            op = self.advance().value; right = self.parse_primary()
            left = f"({left} {op} {right})"
        return left

    def parse_primary(self):
        t = self.advance()
        if t.type == TokenType.NUMBER: return t.value
        if t.type == TokenType.STRING: return f'"{t.value}"'
        if t.type == TokenType.IDENTIFIER:
            name = self.safe_name(t.value)
            if self.current().type == TokenType.LPAREN:
                self.advance(); args = []
                while self.current().type != TokenType.RPAREN:
                    args.append(self.parse_expr()); 
                    if self.current().type == TokenType.COMMA: self.advance()
                self.expect(TokenType.RPAREN, False); return f"{name}({', '.join(args)})"
            return name
        return "0"

    def parse_function(self):
        abc = self.advance(); name = self.safe_name(self.expect(TokenType.IDENTIFIER, False).value); self.expect(TokenType.LPAREN, False); params = []
        while self.current().type != TokenType.RPAREN:               
            p_name = self.safe_name(self.expect(TokenType.IDENTIFIER, False).value); params.append(f"int {p_name}")
            if self.current().type == TokenType.COMMA: self.advance()
        self.expect(TokenType.RPAREN, False); self.expect(TokenType.LBRACE, False)
        body = []
        while self.current().type not in (TokenType.RBRACE, TokenType.EOF):
            s = self.parse_statement(); 
            if s: body.append("    " + s)
        self.expect(TokenType.RBRACE, False)
        return f"int {name}({', '.join(params)}) {{\n" + "\n".join(body) + "\n}\n"

if __name__ == "__main__":
    
    if len(sys.argv) < 3: print("Wrong usage buddy. \nUsage: python3 compiles.py file.lb output");sys.exit(1)
    inf = sys.argv[1]; base = os.path.splitext(inf)[0]
    with open(inf, 'r') as f: source = f.read()
    print("[*] Tokenizing...")
    tokens = Lexer(source).tokenize()
    print("[*] Compiling...")
    try:
        c_code = CTranspiler(tokens).transpile()
    except Exception as e:
        print(f"[-] Unhandled exception in compiling luaBase. Error: {e}")
        sys.exit(-1)
    print("[*] Writing to C file...")
    with open(base + ".c", 'w') as f: f.write(c_code)
    print("[*] Compiling C code...")
    try:
        subprocess.run(["clang", base + ".c", "-o", sys.argv[2], "-ffast-math", "-march=native", "-flto", "-lm", "-w"], check=True)
    except Exception as e:
        print(f"[-] Unhandled exception in compiling C. Error: {e}")
        sys.exit(-2)
    print(f"[*] Compiled: ./{base}")
