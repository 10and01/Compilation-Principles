from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from op_precedence import Node, ParseStep


@dataclass
class _LayoutState:
    next_leaf_index: int = 0


class SVGExporter:
    def __init__(self, font_family: str = "Arial") -> None:
        self.font_family = font_family

    def save_tree_svg(self, root: Node, output_path: Path, title: str = "Parse Tree") -> None:
        positions: Dict[int, Tuple[float, float]] = {}
        state = _LayoutState()

        leaf_gap = 150.0
        level_gap = 110.0
        margin_x = 90.0
        margin_y = 90.0

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

        order_values = self._collect_orders(root)
        min_order = min(order_values) if order_values else None
        max_order = max(order_values) if order_values else None

        lines: List[str] = []
        lines.append(self._svg_header(width, height))
        lines.append(self._draw_title(width / 2, 48, title))

        self._draw_tree_edges(root, positions, lines)
        self._draw_tree_nodes(root, positions, lines, min_order, max_order)

        lines.append("</svg>")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def export_steps(
        self,
        expression: str,
        steps: List[ParseStep],
        output_path: Path,
        max_visual_steps: int = 80,
    ) -> None:
        width = 1700.0
        margin_x = 70.0
        margin_y = 90.0
        gap_x = 32.0
        gap_y = 60.0
        cell_w = 52.0
        cell_h = 32.0
        stack_w = cell_w
        min_text_w = 280.0

        visible_steps = self._select_steps(steps, max_visual_steps)
        max_stack = max((len(self._split_stack(step.stack)) for step in visible_steps if step), default=1)
        row_h = max_stack * cell_h + 110.0
        max_cols = max(1, int((width - 2 * margin_x + gap_x) // (stack_w + min_text_w + gap_x)))
        available_w = width - 2 * margin_x - gap_x * (max_cols - 1)
        card_w = available_w / max_cols
        text_w = max(min_text_w, card_w - stack_w)

        layout: List[Tuple[Optional[ParseStep], int, int, bool]] = []
        row = 0
        col = 0
        for step in visible_steps:
            if step is None:
                if col != 0:
                    row += 1
                    col = 0
                layout.append((None, row, 0, True))
                row += 1
                col = 0
                continue

            layout.append((step, row, col, False))
            col += 1
            if col >= max_cols:
                row += 1
                col = 0

        total_rows = row + (1 if col > 0 else 0)
        height = margin_y * 2 + total_rows * row_h + max(0, total_rows - 1) * gap_y + 50.0

        lines: List[str] = []
        lines.append(self._svg_header(width, height))
        lines.append(self._draw_title(width / 2, 48, "Operator-Precedence Parsing Steps (Stack View)"))
        lines.append(
            f"<text x='{width / 2:.1f}' y='74' font-family='{self.font_family}' font-size='16' text-anchor='middle' fill='#34495e'>Expression: {escape(expression)}</text>"
        )

        prev_stack_center: Optional[float] = None
        prev_stack_bottom: Optional[float] = None

        for step, row_idx, col_idx, is_full_row in layout:
            y = margin_y + row_idx * (row_h + gap_y)
            if step is None:
                y += 24
                lines.append(
                    f"<text x='{width / 2:.1f}' y='{y:.1f}' font-family='{self.font_family}' font-size='18' text-anchor='middle' fill='#7f8c8d'>... steps omitted ...</text>"
                )
                prev_stack_center = None
                prev_stack_bottom = None
                continue

            stack_items = self._split_stack(step.stack)
            x = margin_x + col_idx * (card_w + gap_x)
            label_y = y + 24
            action_y = y + 44
            stack_top = y + 60
            stack_base = stack_top + max_stack * cell_h
            stack_center = x + stack_w / 2

            if prev_stack_center is not None and prev_stack_bottom is not None:
                if col_idx == 0:
                    lines.append(
                        f"<line x1='{prev_stack_center:.1f}' y1='{prev_stack_bottom + 6:.1f}' x2='{stack_center:.1f}' y2='{stack_top - 10:.1f}' stroke='#7f8c8d' stroke-width='2' marker-end='url(#arrow)' />"
                    )
                else:
                    lines.append(
                        f"<line x1='{prev_stack_center:.1f}' y1='{stack_top - 14:.1f}' x2='{stack_center - stack_w / 2 - 10:.1f}' y2='{stack_top - 14:.1f}' stroke='#7f8c8d' stroke-width='2' marker-end='url(#arrow)' />"
                    )

            lines.append(self._text(stack_center, label_y, f"Step {step.step}", 14, "#2c3e50"))
            action_text = self._truncate(step.action, 60)
            lines.append(self._text(x + stack_w + 24, action_y, f"Action: {action_text}", 14, "#2c3e50", anchor="start"))

            lines.append(
                f"<rect x='{x - 6:.1f}' y='{stack_top - 6:.1f}' width='{stack_w + 12:.1f}' height='{max_stack * cell_h + 12:.1f}' rx='10' ry='10' fill='#f8fbff' stroke='#bdc3c7' stroke-width='1.5' />"
            )

            for idx, symbol in enumerate(stack_items):
                cell_y = stack_base - (idx + 1) * cell_h
                lines.append(
                    f"<rect x='{x:.1f}' y='{cell_y:.1f}' width='{cell_w:.1f}' height='{cell_h:.1f}' fill='#ffffff' stroke='#2c3e50' stroke-width='1.4' />"
                )
                lines.append(self._text(stack_center, cell_y + cell_h / 2 + 5, symbol, 12, "#2c3e50"))

            input_text = self._truncate(step.remaining, 120)
            lines.append(
                self._text(
                    x + stack_w + 24,
                    stack_top + 18,
                    f"Input: {input_text}",
                    13,
                    "#34495e",
                    anchor="start",
                )
            )

            prev_stack_center = stack_center
            prev_stack_bottom = stack_base

        lines.append("</svg>")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _select_steps(self, steps: List[ParseStep], limit: int) -> List[Optional[ParseStep]]:
        if limit <= 0 or len(steps) <= limit:
            return list(steps)

        head = limit // 2
        tail = limit - head
        return list(steps[:head]) + [None] + list(steps[-tail:])

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

    def _draw_tree_edges(self, node: Node, positions: Dict[int, Tuple[float, float]], lines: List[str]) -> None:
        x1, y1 = positions[id(node)]
        for child in node.children:
            x2, y2 = positions[id(child)]
            lines.append(
                f"<line x1='{x1:.1f}' y1='{y1 + 24:.1f}' x2='{x2:.1f}' y2='{y2 - 24:.1f}' stroke='#7f8c8d' stroke-width='2' />"
            )
            self._draw_tree_edges(child, positions, lines)

    def _draw_tree_nodes(
        self,
        node: Node,
        positions: Dict[int, Tuple[float, float]],
        lines: List[str],
        min_order: Optional[int],
        max_order: Optional[int],
    ) -> None:
        x, y = positions[id(node)]
        node_w = 120.0
        node_h = 46.0
        fill = self._color_for_order(node.order, min_order, max_order)
        lines.append(
            f"<rect x='{x - node_w / 2:.1f}' y='{y - node_h / 2:.1f}' width='{node_w:.1f}' height='{node_h:.1f}' rx='10' ry='10' fill='{fill}' stroke='#2c3e50' stroke-width='1.8' />"
        )
        lines.append(self._text(x, y + 5, node.symbol, 14, "#2c3e50"))
        if node.order is not None:
            lines.append(self._text(x + node_w / 2 - 8, y - node_h / 2 + 14, str(node.order), 10, "#34495e", anchor="end"))
        for child in node.children:
            self._draw_tree_nodes(child, positions, lines, min_order, max_order)

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

    def _collect_orders(self, node: Node) -> List[int]:
        orders: List[int] = []
        if node.order is not None:
            orders.append(node.order)
        for child in node.children:
            orders.extend(self._collect_orders(child))
        return orders

    def _color_for_order(self, order: Optional[int], min_order: Optional[int], max_order: Optional[int]) -> str:
        if order is None or min_order is None or max_order is None:
            return "#ffffff"
        if max_order == min_order:
            return "#d6eaf8"
        t = (order - min_order) / (max_order - min_order)
        light = (214, 234, 248)
        dark = (46, 134, 193)
        r = round(light[0] + (dark[0] - light[0]) * t)
        g = round(light[1] + (dark[1] - light[1]) * t)
        b = round(light[2] + (dark[2] - light[2]) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _split_stack(stack_text: str) -> List[str]:
        return [item for item in stack_text.split() if item]

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."
