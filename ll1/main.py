from __future__ import annotations

import argparse
from pathlib import Path

from ll1_core import ReportFormatter, analyze_expression_line, read_expressions
from svg_exporter import SVGExporter


def main() -> None:
    parser = argparse.ArgumentParser(description="LL(1) 预测分析法判断并计算算术表达式")
    parser.add_argument("-i", "--input", default="input.txt", help="输入表达式文件，默认 input.txt")
    parser.add_argument("-o", "--output", default="output.txt", help="结果输出文件，默认 output.txt")
    parser.add_argument("--img-dir", default="images", help="语法树和分析过程图片输出目录，默认 images")
    parser.add_argument("--max-visual-steps", type=int, default=80, help="分析过程图片中最多展示的步骤数，默认 80")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    img_dir = Path(args.img_dir)

    expressions = read_expressions(input_path)
    results = [analyze_expression_line(expression) for expression in expressions]

    svg_exporter = SVGExporter()
    svg_exporter.export_all(results, img_dir, max_visual_steps=args.max_visual_steps)

    formatter = ReportFormatter()
    report = formatter.format(results)
    output_path.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()