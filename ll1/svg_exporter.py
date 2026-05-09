from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ll1_core import AnalysisResult, DISPLAY_SYMBOL, Node, ParseStep


@dataclass
class _LayoutState:
    next_leaf_index: int = 0


class SVGExporter:
    def __init__(self, font_family: str = "Arial"):
        self.font_family = font_family

    def export_all(self, results: List[AnalysisResult], output_dir: Path, max_visual_steps: int = 80) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        for index, result in enumerate(results, start=1):
            if result.parse_tree is not None:
                tree_path = output_dir / f"expression_{index:02d}_tree.svg"
                self.save_tree_svg(result.parse_tree, tree_path, title=f"Expression {index} Syntax Tree")
                result.tree_image_path = str(tree_path)

            if result.parse_steps:
                steps_path = output_dir / f"expression_{index:02d}_process.svg"
                self.save_parse_steps_svg(result.expression, result.parse_steps, steps_path, max_visual_steps=max_visual_steps)
                result.process_image_path = str(steps_path)

    def save_tree_svg(self, root: Node, output_path: Path, title: str = "Syntax Tree") -> None:
        positions: Dict[int, Tuple[float, float]] = {}
        state = _LayoutState()

        leaf_gap = 160.0
        level_gap = 120.0
        margin_x = 100.0
        margin_y = 100.0

        max_depth = self._tree_depth(root)
        leaf_count = self._leaf_count(root)

        self._assign_positions(
            root,
            depth=0,
            positions=positions,
            state=state,
            margin_x=margin_x,
            margin_y=margin_y,
            leaf_gap=leaf_gap,
            level_gap=level_gap,
        )

        width = max(900.0, margin_x * 2 + max(1, leaf_count - 1) * leaf_gap + 200.0)
        height = max(420.0, margin_y * 2 + max_depth * level_gap + 200.0)

        lines: List[str] = []
        lines.append(self._svg_header(width, height))
        lines.append(self._draw_title(width / 2, 48, title))

        self._draw_tree_edges(root, positions, lines)
        self._draw_tree_nodes(root, positions, lines)

        lines.append("</svg>")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def save_parse_steps_svg(
        self,
        expression: str,
        steps: List[ParseStep],
        output_path: Path,
        max_visual_steps: int = 80,
    ) -> None:
        width = 1800.0
        margin_x = 70.0
        margin_y = 90.0
        card_w = width - margin_x * 2
        card_h = 126.0
        gap = 26.0

        visible_steps = self._select_steps(steps, max_visual_steps)
        height = margin_y * 2 + len(visible_steps) * (card_h + gap) + 80.0

        lines: List[str] = []
        lines.append(self._svg_header(width, height))
        lines.append(self._draw_title(width / 2, 48, "LL(1) Predictive Parsing Steps"))
        lines.append(
            f"<text x='{width / 2:.1f}' y='74' font-family='{self.font_family}' font-size='16' text-anchor='middle' fill='#34495e'>Expression: {escape(expression)}</text>"
        )

        y = margin_y
        prev_center_x = margin_x + card_w / 2
        prev_bottom_y: Optional[float] = None

        for step in visible_steps:
            if step is None:
                y += 16
                lines.append(
                    f"<text x='{width / 2:.1f}' y='{y:.1f}' font-family='{self.font_family}' font-size='18' text-anchor='middle' fill='#7f8c8d'>... 中间步骤省略 ...</text>"
                )
                y += 34
                prev_bottom_y = None
                continue

            x = margin_x
            top = y
            bottom = y + card_h
            center_x = x + card_w / 2

            if prev_bottom_y is not None:
                lines.append(
                    f"<line x1='{prev_center_x:.1f}' y1='{prev_bottom_y:.1f}' x2='{center_x:.1f}' y2='{top - 8:.1f}' stroke='#7f8c8d' stroke-width='2' marker-end='url(#arrow)' />"
                )

            lines.append(
                f"<rect x='{x:.1f}' y='{top:.1f}' width='{card_w:.1f}' height='{card_h:.1f}' rx='12' ry='12' fill='#f8fbff' stroke='#3498db' stroke-width='2' />"
            )

            line1 = f"Step {step.step}: {step.action}"
            line2 = f"Stack    : {self._truncate(step.stack, 120)}"
            line3 = f"Input    : {self._truncate(step.remaining, 120)}"

            lines.append(self._text(x + 18, top + 34, line1, 16, "#2c3e50", anchor="start"))
            lines.append(self._text(x + 18, top + 64, line2, 14, "#34495e", anchor="start"))
            lines.append(self._text(x + 18, top + 92, line3, 14, "#34495e", anchor="start"))

            prev_center_x = center_x
            prev_bottom_y = bottom
            y += card_h + gap

        lines.append("</svg>")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _select_steps(self, steps: List[ParseStep], limit: int) -> List[Optional[ParseStep]]:
        if limit <= 0 or len(steps) <= limit:
            return list(steps)

        head = limit // 2
        tail = limit - head
        return list(steps[:head]) + [None] + list(steps[-tail:])

    def _draw_tree_edges(self, node: Node, positions: Dict[int, Tuple[float, float]], lines: List[str]) -> None:
        x1, y1 = positions[id(node)]
        for child in node.children:
            x2, y2 = positions[id(child)]
            lines.append(
                f"<line x1='{x1:.1f}' y1='{y1 + 24:.1f}' x2='{x2:.1f}' y2='{y2 - 24:.1f}' stroke='#7f8c8d' stroke-width='2' />"
            )
            self._draw_tree_edges(child, positions, lines)

    def _draw_tree_nodes(self, node: Node, positions: Dict[int, Tuple[float, float]], lines: List[str]) -> None:
        x, y = positions[id(node)]
        node_w = 124.0
        node_h = 48.0

        label = DISPLAY_SYMBOL.get(node.symbol, node.symbol)
        if node.symbol in {"NUM", "ID"} and node.token is not None:
            label = f"{label}({node.token.lexeme})"

        lines.append(
            f"<rect x='{x - node_w / 2:.1f}' y='{y - node_h / 2:.1f}' width='{node_w:.1f}' height='{node_h:.1f}' rx='10' ry='10' fill='#ffffff' stroke='#2c3e50' stroke-width='1.8' />"
        )
        lines.append(self._text(x, y + 5, label, 14, "#2c3e50"))

        for child in node.children:
            self._draw_tree_nodes(child, positions, lines)

    def _assign_positions(
        self,
        node: Node,
        depth: int,
        positions: Dict[int, Tuple[float, float]],
        state: _LayoutState,
        margin_x: float,
        margin_y: float,
        leaf_gap: float,
        level_gap: float,
    ) -> float:
        y = margin_y + depth * level_gap

        if not node.children:
            x = margin_x + state.next_leaf_index * leaf_gap
            state.next_leaf_index += 1
            positions[id(node)] = (x, y)
            return x

        child_xs = [
            self._assign_positions(child, depth + 1, positions, state, margin_x, margin_y, leaf_gap, level_gap)
            for child in node.children
        ]
        x = sum(child_xs) / len(child_xs)
        positions[id(node)] = (x, y)
        return x

    def _leaf_count(self, node: Node) -> int:
        if not node.children:
            return 1
        return sum(self._leaf_count(child) for child in node.children)

    def _tree_depth(self, node: Node) -> int:
        if not node.children:
            return 0
        return 1 + max(self._tree_depth(child) for child in node.children)

    def _svg_header(self, width: float, height: float) -> str:
        return (
            "<svg xmlns='http://www.w3.org/2000/svg' "
            f"width='{width:.0f}' height='{height:.0f}' viewBox='0 0 {width:.0f} {height:.0f}'>"
            "<defs>"
            "<marker id='arrow' markerWidth='10' markerHeight='10' refX='8' refY='5' orient='auto'>"
            "<path d='M0,0 L10,5 L0,10 z' fill='#7f8c8d'/>"
            "</marker>"
            "</defs>"
            "<rect width='100%' height='100%' fill='#f4f7fb'/>"
        )

    def _draw_title(self, x: float, y: float, text: str) -> str:
        return self._text(x, y, text, 24, "#2c3e50")

    def _text(self, x: float, y: float, text: str, size: int, color: str, anchor: str = "middle") -> str:
        return (
            f"<text x='{x:.1f}' y='{y:.1f}' font-family='{self.font_family}' "
            f"font-size='{size}' text-anchor='{anchor}' fill='{color}'>{escape(text)}</text>"
        )

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"
