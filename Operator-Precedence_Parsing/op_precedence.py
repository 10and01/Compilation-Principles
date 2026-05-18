from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple


@dataclass
class ParseStep:
    step: int
    stack: str
    remaining: str
    action: str


@dataclass
class ParseResult:
    expression: str
    accepted: bool
    message: str
    steps: List[ParseStep]
    parse_tree: Optional["Node"] = None


@dataclass
class Node:
    symbol: str
    children: List["Node"]
    order: Optional[int] = None


@dataclass
class StackItem:
    symbol: str
    node: Optional[Node] = None


class OperatorPrecedenceGrammar:
    def __init__(self) -> None:
        self.start_symbol = "E"
        self.productions: Dict[str, List[List[str]]] = {
            "E": [["E", "+", "T"], ["T"]],
            "T": [["T", "*", "F"], ["F"]],
            "F": [["(", "E", ")"], ["i"]],
        }
        self.nonterminals = set(self.productions.keys())
        self.terminals = self._collect_terminals()
        self.terminals.add("#")
# productions 存储了文法 G[E] 的各个产生式，用列表的列表表示，便于遍历。
# terminals 通过扫描产生式右部，收集所有不在左部出现的符号，并人工加入界符 #。
# is_terminal(symbol) 和 is_nonterminal(symbol) 用于判断符号类型，贯穿整个算法。

    def _collect_terminals(self) -> Set[str]:
        terms: Set[str] = set()
        for rhs_list in self.productions.values():
            for rhs in rhs_list:
                for symbol in rhs:
                    if symbol not in self.productions:
                        terms.add(symbol)
        return terms

    def is_terminal(self, symbol: str) -> bool:
        return symbol in self.terminals

    def is_nonterminal(self, symbol: str) -> bool:
        return symbol in self.nonterminals


class OperatorPrecedenceParser:
    def __init__(self, grammar: OperatorPrecedenceGrammar) -> None:
        self.grammar = grammar
        self.firstvt = self._compute_firstvt()
        self.lastvt = self._compute_lastvt()
        self.precedence, self.conflicts = self._build_precedence_table()
    #计算 FirstVT 与 LastVT
    def _compute_firstvt(self) -> Dict[str, Set[str]]:
        firstvt: Dict[str, Set[str]] = {nt: set() for nt in self.grammar.nonterminals}
        changed = True
        while changed:
            changed = False
            for lhs, rhs_list in self.grammar.productions.items():
                for rhs in rhs_list:
                    if not rhs:
                        continue
                    first = rhs[0]
                    if self.grammar.is_terminal(first):
                        if first not in firstvt[lhs]:
                            firstvt[lhs].add(first)
                            changed = True
                    if len(rhs) >= 2 and self.grammar.is_nonterminal(first) and self.grammar.is_terminal(rhs[1]):
                        if rhs[1] not in firstvt[lhs]:
                            firstvt[lhs].add(rhs[1])
                            changed = True
                    if self.grammar.is_nonterminal(first):
                        for sym in firstvt[first]:
                            if sym not in firstvt[lhs]:
                                firstvt[lhs].add(sym)
                                changed = True
        return firstvt

    def _compute_lastvt(self) -> Dict[str, Set[str]]:
        lastvt: Dict[str, Set[str]] = {nt: set() for nt in self.grammar.nonterminals}
        changed = True
        while changed:
            changed = False
            for lhs, rhs_list in self.grammar.productions.items():
                for rhs in rhs_list:
                    if not rhs:
                        continue
                    last = rhs[-1]
                    if self.grammar.is_terminal(last):
                        if last not in lastvt[lhs]:
                            lastvt[lhs].add(last)
                            changed = True
                    if len(rhs) >= 2 and self.grammar.is_nonterminal(last) and self.grammar.is_terminal(rhs[-2]):
                        if rhs[-2] not in lastvt[lhs]:
                            lastvt[lhs].add(rhs[-2])
                            changed = True
                    if self.grammar.is_nonterminal(last):
                        for sym in lastvt[last]:
                            if sym not in lastvt[lhs]:
                                lastvt[lhs].add(sym)
                                changed = True
        return lastvt
    #构造算符优先关系表
    def _build_precedence_table(self) -> Tuple[Dict[str, Dict[str, str]], List[str]]: 
        table: Dict[str, Dict[str, str]] = {a: {} for a in self.grammar.terminals}
        conflicts: List[str] = []

        def set_relation(a: str, b: str, rel: str) -> None:
            current = table[a].get(b)
            if current is None:
                table[a][b] = rel
                return
            if current != rel:
                conflicts.append(f"conflict: {a} {current}/{rel} {b}")

        for lhs, rhs_list in self.grammar.productions.items():
            for rhs in rhs_list:
                for i in range(len(rhs) - 1):
                    x = rhs[i]
                    y = rhs[i + 1]
                    if self.grammar.is_terminal(x) and self.grammar.is_terminal(y):
                        set_relation(x, y, "=")   # a b 相邻 => a = b
                    if self.grammar.is_terminal(x) and self.grammar.is_nonterminal(y):
                        for sym in self.firstvt[y]: # a Q => a < FirstVT(Q)
                            set_relation(x, sym, "<")
                    if self.grammar.is_nonterminal(x) and self.grammar.is_terminal(y):
                        for sym in self.lastvt[x]:    # Q a => LastVT(Q) > a
                            set_relation(sym, y, ">")
                    if (
                        i + 2 < len(rhs) and self.grammar.is_terminal(x) and self.grammar.is_nonterminal(y) and self.grammar.is_terminal(rhs[i + 2])
                    ):   # a Q b => a = b
                        set_relation(x, rhs[i + 2], "=")

        start = self.grammar.start_symbol
        for sym in self.firstvt[start]:
            set_relation("#", sym, "<")
        for sym in self.lastvt[start]:
            set_relation(sym, "#", ">")
        set_relation("#", "#", "=")
        # 加入# 与开始符号 FirstVT/LastVT 的关系，以及 # = #，确保句子两端匹配
        return table, conflicts
    #移进-归约主循环
    def parse(self, expression: str) -> ParseResult:
        tokens, error = tokenize_expression(expression)
        if error is not None:
            return ParseResult(
                expression=expression,
                accepted=False,
                message=error,
                steps=[],
                parse_tree=self._build_error_tree(None, [], error),
            )

        tokens.append("#")  
        stack: List[StackItem] = [StackItem("#")]
        steps: List[ParseStep] = []
        step_no = 1
        index = 0

        while True:
            a = self._top_terminal(stack) # 栈顶终结符
            b = tokens[index]  # 当前输入符号
            # 接受条件：栈中只剩 #N，输入为 #
            if a == "#" and b == "#" and self._stack_symbols(stack) == ["#", "N"]:
                steps.append(ParseStep(step_no, self._stack_text(stack), " ".join(tokens[index:]), "accept"))
                root = stack[-1].node
                root = self._normalize_root(root) if root is not None else None
                return ParseResult(
                    expression=expression,
                    accepted=True,
                    message="accepted",
                    steps=steps,
                    parse_tree=root,
                )

            rel = self.precedence.get(a, {}).get(b)
            if rel in ("<", "="):
                # 移进
                stack.append(StackItem(b, Node(b, [])))
                index += 1
                steps.append(ParseStep(step_no, self._stack_text(stack), " ".join(tokens[index:]), f"shift {b}"))
                step_no += 1
                continue

            if rel == ">":
                # 归约
                stack_snapshot = list(stack)
                handle = self._pop_handle(stack) # 弹出最左素短语
                ok, prod_or_error, node = self._reduce_handle(handle, step_no)
                if not ok:
                    # 归约失败，报错
                    steps.append(
                        ParseStep(step_no, self._stack_text(stack), " ".join(tokens[index:]), f"error: {prod_or_error}")
                    )
                    return ParseResult(
                        expression=expression,
                        accepted=False,
                        message=prod_or_error,
                        steps=steps,
                        parse_tree=self._build_error_tree(stack_snapshot, tokens[index:], prod_or_error, handle),
                    )

                stack.append(StackItem("N", node))  # 压入非终结符占位
                steps.append(
                    ParseStep(step_no, self._stack_text(stack), " ".join(tokens[index:]), f"reduce {prod_or_error}")
                )
                step_no += 1
                continue
            # 没有优先关系 -> 错误
            message = f"no precedence relation between {a} and {b}"
            steps.append(ParseStep(step_no, self._stack_text(stack), " ".join(tokens[index:]), f"error: {message}"))
            return ParseResult(
                expression=expression,
                accepted=False,
                message=message,
                steps=steps,
                parse_tree=self._build_error_tree(stack, tokens[index:], message),
            )

    def _reduce_handle(self, handle: Sequence[StackItem], reduce_step: int) -> Tuple[bool, str, Optional[Node]]:
        text = "".join(item.symbol for item in handle)
        #用简单字符串匹配来模拟归约。这里用 N 作为非终结符的占位符，因为算符优先分析实际上不区分具体非终结符，只要终结符序列匹配即可归约。
        if text == "i":
            leaf = handle[0].node or Node("i", [])
            return True, "F -> i", Node("F", [leaf], reduce_step)
        if text == "(N)":
            left = handle[0].node or Node("(", [])
            mid = handle[1].node or Node("N", [])
            right = handle[2].node or Node(")", [])
            return True, "F -> (E)", Node("F", [left, mid, right], reduce_step)
        if text == "N+N":
            left = handle[0].node or Node("N", [])
            op = handle[1].node or Node("+", [])
            right = handle[2].node or Node("N", [])
            return True, "E -> E + T", Node("E", [left, op, right], reduce_step)
        if text == "N*N":
            left = handle[0].node or Node("N", [])
            op = handle[1].node or Node("*", [])
            right = handle[2].node or Node("N", [])
            return True, "T -> T * F", Node("T", [left, op, right], reduce_step)
        return False, f"invalid handle: {text}", None

    def _top_terminal(self, stack: List[StackItem]) -> str:
        for item in reversed(stack):
            if self.grammar.is_terminal(item.symbol):
                return item.symbol
        return "#"
    #栈顶向栈底寻找最上方的终结符作为右边界 right
    def _pop_handle(self, stack: List[StackItem]) -> List[StackItem]:
        right = self._find_terminal_index(stack, len(stack) - 1)
        if right <= 0:
            return []
        #向左找另一个终结符 left，检查它们的关系。只要 left ≥ right（即不是 < 关系），就向左移动边界，直到遇到 left < right 关系为止。
        #这样 stack[left+1 : right+1] 就是被 < 和 > 包围的最左素短语，弹出后交给 _reduce_handle 进行归约。
        left = self._find_terminal_index(stack, right - 1)
        while (
            left >= 0
            and self.precedence.get(stack[left].symbol, {}).get(stack[right].symbol) != "<"
        ):
            right = left
            left = self._find_terminal_index(stack, right - 1)

        start = left + 1 if left >= 0 else 0
        handle = stack[start:]
        del stack[start:]
        return handle

    def _find_terminal_index(self, stack: List[StackItem], start: int) -> int:
        for i in range(start, -1, -1):
            if self.grammar.is_terminal(stack[i].symbol):
                return i
        return -1

    def _stack_text(self, stack: List[StackItem]) -> str:
        return " ".join(item.symbol for item in stack)

    def _stack_symbols(self, stack: List[StackItem]) -> List[str]:
        return [item.symbol for item in stack]

    def _normalize_root(self, node: Node) -> Node:
        if node.symbol == "E":
            return node
        if node.symbol == "T":
            return Node("E", [node])
        if node.symbol == "F":
            return Node("E", [Node("T", [node])])
        return Node("E", [node])

    def _build_error_tree(
        self,
        stack: Optional[List[StackItem]],
        remaining: Sequence[str],
        message: str,
        handle: Optional[Sequence[StackItem]] = None,
    ) -> Node:
        reason = Node(self._compact_reason(message), [])
        reason_node = Node("REASON", [reason])

        stack_nodes: List[Node] = []
        if stack:
            for item in stack:
                if item.node is not None:
                    stack_nodes.append(item.node)
                else:
                    stack_nodes.append(Node(item.symbol, []))

        input_nodes = [Node(tok, []) for tok in remaining]

        children = [reason_node, Node("STACK", stack_nodes), Node("INPUT", input_nodes)]
        if handle:
            handle_nodes = [item.node or Node(item.symbol, []) for item in handle]
            children.insert(1, Node("HANDLE", handle_nodes))

        return Node("ERROR", children)

    def _compact_reason(self, message: str) -> str:
        if message.startswith("no precedence relation between "):
            parts = message.split()
            if len(parts) >= 7:
                return f"no-rel({parts[4]},{parts[6]})"
        if message.startswith("invalid handle: "):
            return "invalid-handle"
        if message.startswith("invalid character: "):
            ch = message.split(":", 1)[1].strip()
            return f"invalid-char({ch})"
        if message == "empty expression":
            return "empty"
        return "error"


def tokenize_expression(expression: str) -> Tuple[List[str], Optional[str]]:
    expr = expression.strip()
    if expr.endswith(";"):
        expr = expr[:-1]

    tokens: List[str] = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if ch in {"+", "*", "(", ")"}:
            tokens.append(ch)
            i += 1
            continue
        if ch == "i":
            tokens.append(ch)
            i += 1
            continue
        return [], f"invalid character: {ch}"

    if not tokens:
        return [], "empty expression"

    return tokens, None


def format_set(values: Set[str]) -> str:
    return "{" + ", ".join(sorted(values)) + "}"


def format_precedence_table(table: Dict[str, Dict[str, str]], terminals: List[str]) -> List[str]:
    col_width = 3
    header = " ".join([" ".rjust(col_width)] + [t.rjust(col_width) for t in terminals])
    lines = [header]
    for a in terminals:
        row = [a.rjust(col_width)]
        for b in terminals:
            rel = table.get(a, {}).get(b, "")
            row.append(rel.rjust(col_width))
        lines.append(" ".join(row))
    return lines
