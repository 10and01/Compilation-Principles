from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from op_precedence import (
    OperatorPrecedenceGrammar,
    OperatorPrecedenceParser,
    ParseResult,
    format_precedence_table,
    format_set,
)
from svg_exporter import SVGExporter


def build_report_header(parser: OperatorPrecedenceParser) -> List[str]:
    grammar = parser.grammar
    lines: List[str] = []
    lines.append("Operator-Precedence Parser")
    lines.append("Grammar:")
    lines.append("  E -> E + T | T")
    lines.append("  T -> T * F | F")
    lines.append("  F -> ( E ) | i")
    lines.append("")
    lines.append("FirstVT:")
    for nt in sorted(grammar.nonterminals):
        lines.append(f"  FirstVT({nt}) = {format_set(parser.firstvt[nt])}")
    lines.append("")
    lines.append("LastVT:")
    for nt in sorted(grammar.nonterminals):
        lines.append(f"  LastVT({nt}) = {format_set(parser.lastvt[nt])}")
    lines.append("")
    lines.append("Operator-precedence table:")
    terminals = ["+", "*", "(", ")", "i", "#"]
    lines.extend(format_precedence_table(parser.precedence, terminals))
    if parser.conflicts:
        lines.append("")
        lines.append("Conflicts detected:")
        lines.extend(f"  {item}" for item in parser.conflicts)
    return lines


def append_expression_report(lines: List[str], result: ParseResult) -> None:
    lines.append("")
    lines.append(f"Expression: {result.expression}")
    lines.append(f"Result: {'ACCEPT' if result.accepted else 'REJECT'} ({result.message})")
    lines.append("Steps:")
    for step in result.steps:
        lines.append(
            f"  {step.step:>3} | stack: {step.stack:<24} | input: {step.remaining:<20} | {step.action}"
        )


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="Operator-precedence parser demo")
    arg_parser.add_argument("-i", "--input", default="input.txt", help="input file path")
    arg_parser.add_argument("-o", "--output", default="output.txt", help="output report path")
    arg_parser.add_argument(
        "--table", default="precedence_table.txt", help="output file path for precedence table"
    )
    arg_parser.add_argument("--img-dir", default="images", help="directory for SVG outputs")
    arg_parser.add_argument("--max-visual-steps", type=int, default=80, help="max steps per SVG")
    args = arg_parser.parse_args()

    grammar = OperatorPrecedenceGrammar()
    parser = OperatorPrecedenceParser(grammar)

    input_path = Path(args.input)
    output_path = Path(args.output)
    table_path = Path(args.table)
    img_dir = Path(args.img_dir) if args.img_dir else None

    expressions: List[str] = []
    if input_path.exists():
        for line in input_path.read_text(encoding="utf-8").splitlines():
            cleaned = line.strip()
            if cleaned:
                expressions.append(cleaned)

    header_lines = build_report_header(parser)
    report_lines = list(header_lines)

    table_path.write_text("\n".join(header_lines), encoding="utf-8")

    results: List[ParseResult] = []
    for expr in expressions:
        result = parser.parse(expr)
        results.append(result)
        append_expression_report(report_lines, result)

    output_path.write_text("\n".join(report_lines), encoding="utf-8")
    print("\n".join(report_lines))

    if img_dir is not None:
        img_dir.mkdir(parents=True, exist_ok=True)
        exporter = SVGExporter()
        for idx, result in enumerate(results, start=1):
            if result.parse_tree is not None:
                tree_path = img_dir / f"expression_{idx:02d}_tree.svg"
                exporter.save_tree_svg(result.parse_tree, tree_path, title=f"Expression {idx} Parse Tree")
            svg_path = img_dir / f"expression_{idx:02d}_process.svg"
            exporter.export_steps(result.expression, result.steps, svg_path, max_visual_steps=args.max_visual_steps)


if __name__ == "__main__":
    main()
