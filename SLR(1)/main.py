from __future__ import annotations

import argparse
from pathlib import Path

from slr_core import ReportFormatter, SLRParser, analyze_expression_line, read_expressions
from svg_exporter import SVGExporter


def main() -> None:
    parser = argparse.ArgumentParser(description="SLR(1) parser for the expression grammar")
    parser.add_argument("-i", "--input", default="input.txt", help="input file path")
    parser.add_argument("-o", "--output", default="output.txt", help="output report path")
    parser.add_argument("--table", default="slr_table.txt", help="output table path")
    parser.add_argument("--img-dir", default="images", help="directory for SVG outputs")
    parser.add_argument("--max-visual-steps", type=int, default=80, help="max steps per SVG")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    table_path = Path(args.table)
    img_dir = Path(args.img_dir)

    parser_core = SLRParser()
    expressions = read_expressions(input_path)
    results = [analyze_expression_line(expr, parser_core) for expr in expressions]

    exporter = SVGExporter()
    exporter.export_all(results, img_dir, max_visual_steps=args.max_visual_steps)

    formatter = ReportFormatter()
    report = formatter.format(parser_core, results)
    output_path.write_text(report, encoding="utf-8")

    table_report = formatter.format_table_only(parser_core)
    table_path.write_text(table_report, encoding="utf-8")

    print(report)


if __name__ == "__main__":
    main()
