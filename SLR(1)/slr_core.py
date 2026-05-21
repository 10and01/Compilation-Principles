from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

EOF = "$"
EPS = "EPS"


@dataclass(frozen=True)
class Item:
    prod_index: int
    dot: int


@dataclass
class Production:
    lhs: str
    rhs: List[str]


@dataclass
class Token:
    type: str
    lexeme: str
    position: int

    def display(self) -> str:
        if self.type == "i" and self.lexeme != "i":
            return f"i({self.lexeme})"
        return self.type


@dataclass
class Node:
    symbol: str
    children: List["Node"] = field(default_factory=list)
    token: Optional[Token] = None


@dataclass
class ParseStep:
    step: int
    stack: str
    remaining: str
    action: str
    rule: str
    state_stack: List[int] = field(default_factory=list)
    symbol_stack: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    expression: str
    status: str
    message: str
    parse_steps: List[ParseStep] = field(default_factory=list)
    parse_tree: Optional[Node] = None
    tree_text: str = ""
    tree_image_path: Optional[str] = None
    process_image_path: Optional[str] = None


@dataclass
class StackSymbol:
    symbol: str
    node: Optional[Node] = None


@dataclass(frozen=True)
class Action:
    kind: str
    value: Optional[int] = None

    def format(self) -> str:
        if self.kind == "shift":
            return f"s{self.value}"
        if self.kind == "reduce":
            return f"r{self.value}"
        if self.kind == "accept":
            return "acc"
        return ""


class SLRGrammar:
    def __init__(self) -> None:
        self.augmented_start = "S'"
        self.start_symbol = "S"
        self.productions: List[Production] = [
            Production("S'", ["S"]),
            Production("S", ["E"]),
            Production("E", ["E", "+", "T"]),
            Production("E", ["T"]),
            Production("T", ["T", "*", "F"]),
            Production("T", ["F"]),
            Production("F", ["(", "E", ")"]),
            Production("F", ["i"]),
        ]
        self.nonterminals: Set[str] = {prod.lhs for prod in self.productions}
        self.terminals: Set[str] = self._collect_terminals()
        self.terminals.add(EOF)
        self.productions_by_lhs: Dict[str, List[int]] = {}
        for idx, prod in enumerate(self.productions):
            self.productions_by_lhs.setdefault(prod.lhs, []).append(idx)

    def _collect_terminals(self) -> Set[str]:
        terms: Set[str] = set()
        for prod in self.productions:
            for sym in prod.rhs:
                if sym not in self.nonterminals:
                    terms.add(sym)
        return terms

    def is_terminal(self, symbol: str) -> bool:
        return symbol in self.terminals

    def is_nonterminal(self, symbol: str) -> bool:
        return symbol in self.nonterminals


class SLRParser:
    def __init__(self, grammar: Optional[SLRGrammar] = None) -> None:
        self.grammar = grammar or SLRGrammar()
        self.first = self._compute_first()
        self.follow = self._compute_follow()
        self.states, self.transitions = self._build_canonical_collection()
        self.action, self.goto, self.conflicts = self._build_tables()

    @property
    def state_count(self) -> int:
        return len(self.states)

    @property
    def terminals(self) -> List[str]:
        ordered = ["i", "+", "*", "(", ")", EOF]
        return [t for t in ordered if t in self.grammar.terminals]

    @property
    def nonterminals(self) -> List[str]:
        ordered = ["S", "E", "T", "F"]
        return [nt for nt in ordered if nt in self.grammar.nonterminals and nt != self.grammar.augmented_start]

    def parse(self, expression: str) -> AnalysisResult:
        tokens, error = tokenize_expression(expression)
        result = AnalysisResult(expression=expression.rstrip("\n"), status="REJECT", message="")
        if error:
            result.message = error
            return result

        tokens.append(Token(EOF, EOF, len(expression)))
        state_stack: List[int] = [0]
        symbol_stack: List[StackSymbol] = [StackSymbol(EOF, None)]
        steps: List[ParseStep] = []
        index = 0
        step_no = 1

        while True:
            state = state_stack[-1]
            lookahead = tokens[index].type
            action = self.action.get(state, {}).get(lookahead)

            if action is None:
                message = f"error: no action for state {state} on symbol {lookahead}"
                rule_text = f"ACTION[{state}, {lookahead}] = error"
                states_snapshot, symbols_snapshot = self._snapshot_stacks(state_stack, symbol_stack)
                steps.append(
                    ParseStep(
                        step_no,
                        self._stack_display(state_stack, symbol_stack),
                        self._remaining_display(tokens, index),
                        message,
                        rule_text,
                        states_snapshot,
                        symbols_snapshot,
                    )
                )
                result.message = message
                result.parse_steps = steps
                return result

            if action.kind == "shift":
                symbol = tokens[index]
                node = Node(symbol.type, token=symbol)
                symbol_stack.append(StackSymbol(symbol.type, node))
                state_stack.append(action.value if action.value is not None else -1)
                index += 1
                rule_text = f"ACTION[{state}, {lookahead}] = s{action.value}"
                states_snapshot, symbols_snapshot = self._snapshot_stacks(state_stack, symbol_stack)
                steps.append(
                    ParseStep(
                        step_no,
                        self._stack_display(state_stack, symbol_stack),
                        self._remaining_display(tokens, index),
                        f"shift {symbol.display()} -> s{action.value}",
                        rule_text,
                        states_snapshot,
                        symbols_snapshot,
                    )
                )
                step_no += 1
                continue

            if action.kind == "reduce":
                prod = self.grammar.productions[action.value if action.value is not None else 0]
                rhs_len = len(prod.rhs)
                popped: List[StackSymbol] = []
                for _ in range(rhs_len):
                    popped.append(symbol_stack.pop())
                    state_stack.pop()

                children = [item.node or Node(item.symbol) for item in reversed(popped)]
                node = Node(prod.lhs, children=children)
                symbol_stack.append(StackSymbol(prod.lhs, node))

                goto_state = self.goto.get(state_stack[-1], {}).get(prod.lhs)
                if goto_state is None:
                    message = f"error: no goto for state {state_stack[-1]} on {prod.lhs}"
                    rule_text = f"ACTION[{state}, {lookahead}] = r{action.value}, GOTO[{state_stack[-1]}, {prod.lhs}] = ?"
                    states_snapshot, symbols_snapshot = self._snapshot_stacks(state_stack, symbol_stack)
                    steps.append(
                        ParseStep(
                            step_no,
                            self._stack_display(state_stack, symbol_stack),
                            self._remaining_display(tokens, index),
                            message,
                            rule_text,
                            states_snapshot,
                            symbols_snapshot,
                        )
                    )
                    result.message = message
                    result.parse_steps = steps
                    return result

                state_stack.append(goto_state)
                rhs_text = " ".join(prod.rhs) if prod.rhs else EPS
                rule_text = f"ACTION[{state}, {lookahead}] = r{action.value}, GOTO[{state_stack[-2]}, {prod.lhs}] = {goto_state}"
                states_snapshot, symbols_snapshot = self._snapshot_stacks(state_stack, symbol_stack)
                steps.append(
                    ParseStep(
                        step_no,
                        self._stack_display(state_stack, symbol_stack),
                        self._remaining_display(tokens, index),
                        f"reduce r{action.value}: {prod.lhs} -> {rhs_text}",
                        rule_text,
                        states_snapshot,
                        symbols_snapshot,
                    )
                )
                step_no += 1
                continue

            if action.kind == "accept":
                rule_text = f"ACTION[{state}, {lookahead}] = acc"
                states_snapshot, symbols_snapshot = self._snapshot_stacks(state_stack, symbol_stack)
                steps.append(
                    ParseStep(
                        step_no,
                        self._stack_display(state_stack, symbol_stack),
                        self._remaining_display(tokens, index),
                        "accept",
                        rule_text,
                        states_snapshot,
                        symbols_snapshot,
                    )
                )
                result.status = "ACCEPT"
                result.message = "accepted"
                result.parse_steps = steps
                result.parse_tree = symbol_stack[-1].node
                if result.parse_tree is not None:
                    renderer = TreeTextRenderer()
                    result.tree_text = "\n".join(renderer.render(result.parse_tree))
                return result

    def _build_canonical_collection(self) -> Tuple[List[Set[Item]], Dict[Tuple[int, str], int]]:
        start_items = self._closure({Item(0, 0)})
        states: List[Set[Item]] = [start_items]
        state_map: Dict[frozenset[Item], int] = {frozenset(start_items): 0}
        transitions: Dict[Tuple[int, str], int] = {}
        queue: List[int] = [0]

        symbols = sorted(self.grammar.terminals - {EOF}) + sorted(self.grammar.nonterminals)

        while queue:
            state_idx = queue.pop(0)
            items = states[state_idx]
            for sym in symbols:
                goto_set = self._goto(items, sym)
                if not goto_set:
                    continue
                key = frozenset(goto_set)
                if key not in state_map:
                    state_map[key] = len(states)
                    states.append(goto_set)
                    queue.append(state_map[key])
                transitions[(state_idx, sym)] = state_map[key]

        return states, transitions

    def _closure(self, items: Set[Item]) -> Set[Item]:
        closure_set = set(items)
        changed = True
        while changed:
            changed = False
            for item in list(closure_set):
                prod = self.grammar.productions[item.prod_index]
                if item.dot >= len(prod.rhs):
                    continue
                symbol = prod.rhs[item.dot]
                if self.grammar.is_nonterminal(symbol):
                    for prod_idx in self.grammar.productions_by_lhs.get(symbol, []):
                        new_item = Item(prod_idx, 0)
                        if new_item not in closure_set:
                            closure_set.add(new_item)
                            changed = True
        return closure_set

    def _goto(self, items: Set[Item], symbol: str) -> Set[Item]:
        moved: Set[Item] = set()
        for item in items:
            prod = self.grammar.productions[item.prod_index]
            if item.dot < len(prod.rhs) and prod.rhs[item.dot] == symbol:
                moved.add(Item(item.prod_index, item.dot + 1))
        if not moved:
            return set()
        return self._closure(moved)

    def _build_tables(self) -> Tuple[Dict[int, Dict[str, Action]], Dict[int, Dict[str, int]], List[str]]:
        action_table: Dict[int, Dict[str, Action]] = {}
        goto_table: Dict[int, Dict[str, int]] = {}
        conflicts: List[str] = []

        def set_action(state: int, terminal: str, action: Action) -> None:
            action_table.setdefault(state, {})
            current = action_table[state].get(terminal)
            if current is None:
                action_table[state][terminal] = action
                return
            if current != action:
                conflicts.append(
                    f"conflict at state {state}, symbol {terminal}: {current.format()} vs {action.format()}"
                )

        for state_idx, items in enumerate(self.states):
            for item in items:
                prod = self.grammar.productions[item.prod_index]
                if item.dot < len(prod.rhs):
                    symbol = prod.rhs[item.dot]
                    if self.grammar.is_terminal(symbol):
                        next_state = self.transitions.get((state_idx, symbol))
                        if next_state is not None:
                            set_action(state_idx, symbol, Action("shift", next_state))
                    else:
                        next_state = self.transitions.get((state_idx, symbol))
                        if next_state is not None:
                            goto_table.setdefault(state_idx, {})[symbol] = next_state
                else:
                    if prod.lhs == self.grammar.augmented_start:
                        set_action(state_idx, EOF, Action("accept"))
                        continue
                    for terminal in self.follow.get(prod.lhs, set()):
                        set_action(state_idx, terminal, Action("reduce", item.prod_index))

        return action_table, goto_table, conflicts

    def _compute_first(self) -> Dict[str, Set[str]]:
        first: Dict[str, Set[str]] = {sym: set() for sym in self.grammar.nonterminals}
        for terminal in self.grammar.terminals:
            first[terminal] = {terminal}

        changed = True
        while changed:
            changed = False
            for prod in self.grammar.productions:
                rhs_first = self._first_of_sequence(prod.rhs, first)
                before = set(first[prod.lhs])
                first[prod.lhs].update(rhs_first)
                if before != first[prod.lhs]:
                    changed = True

        return first

    def _compute_follow(self) -> Dict[str, Set[str]]:
        follow: Dict[str, Set[str]] = {nt: set() for nt in self.grammar.nonterminals}
        follow[self.grammar.start_symbol].add(EOF)

        changed = True
        while changed:
            changed = False
            for prod in self.grammar.productions:
                rhs = prod.rhs
                for idx, symbol in enumerate(rhs):
                    if symbol not in self.grammar.nonterminals:
                        continue
                    beta = rhs[idx + 1 :]
                    first_beta = self._first_of_sequence(beta, self.first)
                    before = set(follow[symbol])
                    follow[symbol].update(first_beta - {EPS})
                    if EPS in first_beta or not beta:
                        follow[symbol].update(follow[prod.lhs])
                    if before != follow[symbol]:
                        changed = True

        return follow

    def _first_of_sequence(self, symbols: Iterable[str], first: Dict[str, Set[str]]) -> Set[str]:
        result: Set[str] = set()
        symbols_list = list(symbols)
        if not symbols_list:
            result.add(EPS)
            return result
        for sym in symbols_list:
            sym_first = first.get(sym, {sym})
            result.update(sym_first - {EPS})
            if EPS not in sym_first:
                return result
        result.add(EPS)
        return result

    @staticmethod
    def _remaining_display(tokens: List[Token], index: int) -> str:
        return " ".join(tok.display() for tok in tokens[index:])

    @staticmethod
    def _stack_display(state_stack: List[int], symbol_stack: List[StackSymbol]) -> str:
        state_text = " ".join(str(state) for state in state_stack)
        symbol_text = " ".join(item.symbol for item in symbol_stack)
        return f"states: {state_text} | symbols: {symbol_text}"

    @staticmethod
    def _snapshot_stacks(state_stack: List[int], symbol_stack: List[StackSymbol]) -> Tuple[List[int], List[str]]:
        return list(state_stack), [item.symbol for item in symbol_stack]


class TreeTextRenderer:
    def render(self, node: Node, indent: str = "") -> List[str]:
        label = node.symbol
        if node.symbol == "i" and node.token is not None:
            label = f"i({node.token.lexeme})"
        lines = [indent + label]
        next_indent = indent + "  "
        for child in node.children:
            lines.extend(self.render(child, next_indent))
        return lines


class ReportFormatter:
    def format(self, parser: SLRParser, results: List[AnalysisResult]) -> str:
        lines = self._build_header(parser)

        for index, result in enumerate(results, start=1):
            lines.append("")
            lines.append(f"Expression {index}: {result.expression}")
            lines.append(f"Result: {result.status} ({result.message})")

            if result.tree_image_path:
                lines.append(f"Parse tree SVG: {result.tree_image_path}")
            if result.process_image_path:
                lines.append(f"Process SVG: {result.process_image_path}")

            if result.parse_tree is not None and result.tree_text:
                lines.append("Parse tree:")
                lines.append(result.tree_text)

            if result.parse_steps:
                lines.append("Steps:")
                lines.append(f"{'Step':<6}{'Stack':<64}{'Input':<32}Action")
                for step in result.parse_steps:
                    lines.append(f"{step.step:<6}{step.stack:<64}{step.remaining:<32}{step.action}")

        return "\n".join(lines)

    def format_table_only(self, parser: SLRParser) -> str:
        return "\n".join(self._build_header(parser))

    def _build_header(self, parser: SLRParser) -> List[str]:
        grammar = parser.grammar
        lines: List[str] = []
        lines.append("SLR(1) Parsing Report")
        lines.append("Grammar:")
        lines.append("  S -> E")
        lines.append("  E -> E + T | T")
        lines.append("  T -> T * F | F")
        lines.append("  F -> ( E ) | i")
        lines.append("")
        lines.append("Productions:")
        for idx, prod in enumerate(grammar.productions):
            rhs = " ".join(prod.rhs) if prod.rhs else EPS
            lines.append(f"  {idx}: {prod.lhs} -> {rhs}")
        lines.append("")
        lines.append("Follow sets:")
        for nt in sorted(grammar.nonterminals):
            if nt == grammar.augmented_start:
                continue
            follow_set = ", ".join(sorted(parser.follow.get(nt, set())))
            lines.append(f"  FOLLOW({nt}) = {{ {follow_set} }}")
        lines.append("")
        lines.append("ACTION table:")
        lines.extend(format_action_table(parser.action, parser.state_count, parser.terminals))
        lines.append("")
        lines.append("GOTO table:")
        lines.extend(format_goto_table(parser.goto, parser.state_count, parser.nonterminals))
        if parser.conflicts:
            lines.append("")
            lines.append("Conflicts:")
            lines.extend(f"  {item}" for item in parser.conflicts)
        return lines


def format_action_table(
    action_table: Dict[int, Dict[str, Action]],
    state_count: int,
    terminals: List[str],
) -> List[str]:
    col_width = 6
    header = " ".rjust(col_width) + " ".join(term.rjust(col_width) for term in terminals)
    lines = [header]
    for state in range(state_count):
        row = [str(state).rjust(col_width)]
        for term in terminals:
            action = action_table.get(state, {}).get(term)
            cell = action.format() if action else ""
            row.append(cell.rjust(col_width))
        lines.append(" ".join(row))
    return lines


def format_goto_table(
    goto_table: Dict[int, Dict[str, int]],
    state_count: int,
    nonterminals: List[str],
) -> List[str]:
    col_width = 6
    header = " ".rjust(col_width) + " ".join(nt.rjust(col_width) for nt in nonterminals)
    lines = [header]
    for state in range(state_count):
        row = [str(state).rjust(col_width)]
        for nt in nonterminals:
            value = goto_table.get(state, {}).get(nt)
            cell = str(value) if value is not None else ""
            row.append(cell.rjust(col_width))
        lines.append(" ".join(row))
    return lines


def tokenize_expression(expression: str) -> Tuple[List[Token], Optional[str]]:
    cleaned = normalize_text(expression.strip())
    cleaned = _strip_trailing_marker(cleaned)
    if not cleaned:
        return [], "empty expression"

    tokens: List[Token] = []
    idx = 0
    while idx < len(cleaned):
        ch = cleaned[idx]
        if ch.isspace():
            idx += 1
            continue
        if ch in {"+", "*", "(", ")"}:
            tokens.append(Token(ch, ch, idx))
            idx += 1
            continue
        if ch.isalnum() or ch == "_":
            start = idx
            while idx < len(cleaned) and (cleaned[idx].isalnum() or cleaned[idx] == "_"):
                idx += 1
            lexeme = cleaned[start:idx]
            tokens.append(Token("i", lexeme, start))
            continue
        return [], f"invalid character: {ch}"

    return tokens, None


def _strip_trailing_marker(text: str) -> str:
    stripped = text.rstrip()
    if stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()
    if stripped.endswith("$") or stripped.endswith("#"):
        stripped = stripped[:-1].rstrip()
    return stripped


def normalize_text(text: str) -> str:
    return text


def analyze_expression_line(line: str, parser: Optional[SLRParser] = None) -> AnalysisResult:
    parser = parser or SLRParser()
    result = parser.parse(line)
    return result


def read_expressions(input_path: Path) -> List[str]:
    if not input_path.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")

    lines: List[str] = []
    for raw_line in input_path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip():
            lines.append(raw_line)
    return lines


