from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional, Tuple


EOF = "$"
TERMINALS = {"NUM", "ID", "+", "-", "*", "/", "(", ")", EOF}

DISPLAY_SYMBOL = {
    "E": "E",
    "E1": "E'",
    "T": "T",
    "T1": "T'",
    "F": "F",
    "NUM": "num",
    "ID": "id",
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "(": "(",
    ")": ")",
    EOF: "$",
    "ε": "ε",
}

TABLE: Dict[str, Dict[str, List[str]]] = {
    "E": {"NUM": ["T", "E1"], "ID": ["T", "E1"], "(": ["T", "E1"]},
    "E1": {
        "+": ["+", "T", "E1"],
        "-": ["-", "T", "E1"],
        ")": ["ε"],
        EOF: ["ε"],
    },
    "T": {"NUM": ["F", "T1"], "ID": ["F", "T1"], "(": ["F", "T1"]},
    "T1": {
        "*": ["*", "F", "T1"],
        "/": ["/", "F", "T1"],
        "+": ["ε"],
        "-": ["ε"],
        ")": ["ε"],
        EOF: ["ε"],
    },
    "F": {"NUM": ["NUM"], "ID": ["ID"], "(": ["(", "E", ")"]},
}


@dataclass
class Token:
    type: str
    lexeme: str
    position: int

    def display(self) -> str:
        if self.type in {"NUM", "ID"}:
            return self.lexeme
        return self.type


@dataclass
class Node:
    symbol: str
    token: Optional[Token] = None
    children: List["Node"] = field(default_factory=list)
    production: Optional[List[str]] = None


@dataclass
class ParseStep:
    step: int
    stack: str
    remaining: str
    action: str


@dataclass
class AnalysisResult:
    expression: str
    status: str
    syntax_message: str
    parse_steps: List[ParseStep] = field(default_factory=list)
    parse_tree: Optional[Node] = None
    tree_text: str = ""
    value_text: str = ""
    evaluation_trace: List[str] = field(default_factory=list)
    tree_image_path: Optional[str] = None
    process_image_path: Optional[str] = None


class ParseError(Exception):
    def __init__(self, message: str, position: Optional[int] = None, steps: Optional[List[ParseStep]] = None):
        super().__init__(message)
        self.message = message
        self.position = position
        self.steps = steps or []


class ExpressionLexer:
    @staticmethod
    def normalize_text(text: str) -> str:
        return (
            text.replace("（", "(")
            .replace("）", ")")
            .replace("；", ";")
            .replace("＋", "+")
            .replace("－", "-")
            .replace("×", "*")
            .replace("÷", "/")
        )

    def tokenize(self, expression: str) -> List[Token]:
        tokens: List[Token] = []
        index = 0
        while index < len(expression):
            char = expression[index]
            if char.isspace():
                index += 1
                continue
            if char.isdigit():
                start = index
                while index < len(expression) and expression[index].isdigit():
                    index += 1
                tokens.append(Token("NUM", expression[start:index], start))
                continue
            if char.isalpha() or char == "_":
                start = index
                while index < len(expression) and (expression[index].isalnum() or expression[index] == "_"):
                    index += 1
                tokens.append(Token("ID", expression[start:index], start))
                continue
            if char in "+-*/()":
                tokens.append(Token(char, char, index))
                index += 1
                continue
            raise ParseError(f"无法识别的字符 '{char}'", index)
        return tokens


class LL1Parser:
    def __init__(self, table: Dict[str, Dict[str, List[str]]] | None = None, lexer: Optional[ExpressionLexer] = None):
        self.table = table or TABLE
        self.lexer = lexer or ExpressionLexer()

    def parse(self, expression: str) -> Tuple[Node, List[ParseStep]]:
        cleaned = self.lexer.normalize_text(expression.strip())
        if not cleaned:
            raise ParseError("空表达式。")
        if not cleaned.endswith(";"):
            raise ParseError("表达式缺少结束分号 ';'。")

        body = cleaned[:-1].rstrip()
        if not body:
            raise ParseError("分号前没有有效表达式。")

        tokens = self.lexer.tokenize(body)
        tokens.append(Token(EOF, EOF, len(body)))

        root = Node("E")
        stack: List[Tuple[str, Node]] = [(EOF, Node(EOF)), ("E", root)]
        steps: List[ParseStep] = []

        index = 0
        step_no = 1

        while stack:
            top_symbol, top_node = stack.pop()
            current = tokens[index]

            if top_symbol == "ε":
                continue

            if top_symbol in TERMINALS:
                if top_symbol == current.type:
                    if top_symbol != EOF:
                        top_node.token = current
                        index += 1
                    steps.append(
                        ParseStep(
                            step_no,
                            self._stack_display(stack),
                            self._token_display_sequence(tokens, index),
                            f"匹配终结符 {DISPLAY_SYMBOL.get(top_symbol, top_symbol)}",
                        )
                    )
                    step_no += 1
                    continue

                expected = DISPLAY_SYMBOL.get(top_symbol, top_symbol)
                found = current.display()
                self._raise_parse_error(
                    f"在位置 {current.position + 1} 处，期望 {expected}，但读到 {found}。",
                    current.position,
                    steps,
                )

            production = self.table.get(top_symbol, {}).get(current.type)
            if production is None:
                expected = ", ".join(DISPLAY_SYMBOL.get(item, item) for item in self._expected_tokens(top_symbol))
                found = current.display()
                hint = self._select_error_hint(top_symbol)
                self._raise_parse_error(
                    f"在位置 {current.position + 1} 处，栈顶符号 {DISPLAY_SYMBOL[top_symbol]} 遇到 {found}，无法使用预测分析表展开。期望符号：{expected}。{hint}",
                    current.position,
                    steps,
                )

            top_node.production = production
            if production == ["ε"]:
                steps.append(
                    ParseStep(
                        step_no,
                        self._stack_display(stack),
                        self._token_display_sequence(tokens, index),
                        f"{DISPLAY_SYMBOL[top_symbol]} -> ε",
                    )
                )
                step_no += 1
                continue

            children = [Node(symbol) for symbol in production]
            top_node.children = children
            for symbol, child in zip(reversed(production), reversed(children)):
                stack.append((symbol, child))

            production_text = " ".join(DISPLAY_SYMBOL.get(symbol, symbol) for symbol in production)
            steps.append(
                ParseStep(
                    step_no,
                    self._stack_display(stack),
                    self._token_display_sequence(tokens, index),
                    f"{DISPLAY_SYMBOL[top_symbol]} -> {production_text}",
                )
            )
            step_no += 1

        if index != len(tokens) - 1:
            current = tokens[index]
            raise ParseError(
                f"在位置 {current.position + 1} 处，表达式末尾存在多余输入 {current.display()}。",
                current.position,
                steps,
            )

        return root, steps

    @staticmethod
    def _token_display_sequence(tokens: List[Token], start_index: int) -> str:
        if start_index >= len(tokens):
            return EOF
        return " ".join(token.display() for token in tokens[start_index:])

    @staticmethod
    def _stack_display(stack: List[Tuple[str, Node]]) -> str:
        symbols = [DISPLAY_SYMBOL.get(symbol, symbol) for symbol, _ in stack]
        return " ".join(symbols) if symbols else "<empty>"

    def _expected_tokens(self, nonterminal: str) -> List[str]:
        return list(self.table.get(nonterminal, {}).keys())

    @staticmethod
    def _select_error_hint(nonterminal: str) -> str:
        hints = {
            "E": "表达式必须以操作数或左括号开始。",
            "E1": "这里应当是 +、-、右括号或表达式结束。",
            "T": "项必须以操作数或左括号开始。",
            "T1": "这里应当是 *、/、+、-、右括号或表达式结束。",
            "F": "因子必须是操作数或括号表达式。",
        }
        return hints.get(nonterminal, "表达式结构不合法。")

    @staticmethod
    def _raise_parse_error(message: str, position: Optional[int], steps: List[ParseStep]) -> None:
        raise ParseError(message, position, steps.copy())


class ExpressionEvaluator:
    def evaluate_with_trace(self, root: Node) -> Tuple[Fraction, List[str]]:
        trace: List[str] = []
        value = self._evaluate_tree(root, trace)
        return value, trace

    def _evaluate_tree(self, node: Node, trace: List[str]) -> Fraction:
        if node.symbol == "E":
            left = self._evaluate_tree(node.children[0], trace)
            return self._evaluate_e1(node.children[1], left, trace)
        if node.symbol == "T":
            left = self._evaluate_tree(node.children[0], trace)
            return self._evaluate_t1(node.children[1], left, trace)
        if node.symbol == "F":
            first = node.children[0]
            if first.symbol == "(":
                trace.append("F -> ( E )")
                return self._evaluate_tree(node.children[1], trace)
            if first.symbol == "NUM":
                value = Fraction(int(first.token.lexeme), 1)
                trace.append(f"F -> num({first.token.lexeme}) = {format_fraction(value)}")
                return value
            if first.symbol == "ID":
                value = Fraction(1, 1)
                trace.append(f"F -> id({first.token.lexeme}) = 1 (默认值)")
                return value
        raise ParseError(f"无法对语法树节点 {node.symbol} 求值。")

    def _evaluate_e1(self, node: Node, inherited: Fraction, trace: List[str]) -> Fraction:
        if not node.children:
            trace.append(f"E' -> ε, 继承值保持 {format_fraction(inherited)}")
            return inherited

        op = node.children[0].token.lexeme
        right = self._evaluate_tree(node.children[1], trace)
        if op == "+":
            result = inherited + right
        else:
            result = inherited - right
        trace.append(f"E' -> {op} T E', {format_fraction(inherited)} {op} {format_fraction(right)} = {format_fraction(result)}")
        return self._evaluate_e1(node.children[2], result, trace)

    def _evaluate_t1(self, node: Node, inherited: Fraction, trace: List[str]) -> Fraction:
        if not node.children:
            trace.append(f"T' -> ε, 继承值保持 {format_fraction(inherited)}")
            return inherited

        op = node.children[0].token.lexeme
        right = self._evaluate_tree(node.children[1], trace)
        if op == "*":
            result = inherited * right
        else:
            if right == 0:
                raise ParseError("运行时除零错误。")
            result = inherited / right
        trace.append(f"T' -> {op} F T', {format_fraction(inherited)} {op} {format_fraction(right)} = {format_fraction(result)}")
        return self._evaluate_t1(node.children[2], result, trace)


class TreeTextRenderer:
    def render(self, node: Node, indent: str = "") -> List[str]:
        label = DISPLAY_SYMBOL.get(node.symbol, node.symbol)
        if node.symbol in {"NUM", "ID"} and node.token is not None:
            label = f"{label}({node.token.lexeme})"
        lines = [indent + label]
        next_indent = indent + "  "
        for child in node.children:
            lines.extend(self.render(child, next_indent))
        return lines


class ReportFormatter:
    def format(self, results: List[AnalysisResult]) -> str:
        lines: List[str] = []
        lines.append("算术表达式 LL(1) 预测分析结果")
        lines.append("=" * 60)
        lines.append("")
        lines.append("文法：")
        lines.append("E  -> T E'")
        lines.append("E' -> + T E' | - T E' | ε")
        lines.append("T  -> F T'")
        lines.append("T' -> * F T' | / F T' | ε")
        lines.append("F  -> ( E ) | num | id")
        lines.append("")
        lines.append("预测分析表：")
        lines.append("E  : num/id/( -> T E'")
        lines.append("E' : + -> + T E' ; - -> - T E' ; )/$ -> ε")
        lines.append("T  : num/id/( -> F T'")
        lines.append("T' : * -> * F T' ; / -> / F T' ; +,-,),$ -> ε")
        lines.append("F  : num -> num ; id -> id ; ( -> ( E )")
        lines.append("")

        for index, result in enumerate(results, start=1):
            lines.append(f"表达式 {index}: {result.expression}")
            lines.append(f"判定: {result.status}")

            if result.tree_image_path:
                lines.append(f"语法树图片: {result.tree_image_path}")
            if result.process_image_path:
                lines.append(f"分析过程图片: {result.process_image_path}")

            if result.status == "正确":
                lines.append(f"结果: {result.value_text}")
                lines.append("语法树:")
                lines.append(result.tree_text)
                lines.append("分析过程:")
                lines.append(f"{'步号':<6}{'符号栈':<28}{'剩余输入':<36}动作")
                for step in result.parse_steps:
                    lines.append(f"{step.step:<6}{step.stack:<28}{step.remaining:<36}{step.action}")
                lines.append("计算过程:")
                for item in result.evaluation_trace:
                    lines.append(f"  {item}")
            else:
                lines.append(f"错误信息: {result.syntax_message}")
                if result.parse_steps:
                    lines.append("已完成的分析过程:")
                    lines.append(f"{'步号':<6}{'符号栈':<28}{'剩余输入':<36}动作")
                    for step in result.parse_steps:
                        lines.append(f"{step.step:<6}{step.stack:<28}{step.remaining:<36}{step.action}")
            lines.append("-" * 60)

        return "\n".join(lines)


def format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def analyze_expression_line(
    line: str,
    parser: Optional[LL1Parser] = None,
    evaluator: Optional[ExpressionEvaluator] = None,
    renderer: Optional[TreeTextRenderer] = None,
) -> AnalysisResult:
    parser = parser or LL1Parser()
    evaluator = evaluator or ExpressionEvaluator()
    renderer = renderer or TreeTextRenderer()

    result = AnalysisResult(expression=line.rstrip("\n"), status="错误", syntax_message="")
    try:
        tree, steps = parser.parse(line)
        result.parse_steps = steps
        result.parse_tree = tree
        result.tree_text = "\n".join(renderer.render(tree))

        value, trace = evaluator.evaluate_with_trace(tree)
        result.status = "正确"
        result.syntax_message = "表达式语法正确。"
        result.value_text = format_fraction(value)
        result.evaluation_trace = trace
    except ParseError as exc:
        result.syntax_message = exc.message
        if exc.steps:
            result.parse_steps = exc.steps
    return result


def read_expressions(input_path: Path) -> List[str]:
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    lines: List[str] = []
    for raw_line in input_path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip():
            lines.append(raw_line)
    return lines
