# SLR(1) Parsing Lab

## Goal
Build an SLR(1) parser for the grammar below, generate the ACTION/GOTO table, analyze input strings, and visualize the parsing process.

Grammar:
```
S -> E
E -> E + T | T
T -> T * F | F
F -> ( E ) | i
```

Terminals: `i`, `+`, `*`, `(`, `)`, `$`

## What the program does
1. Builds the canonical LR(0) item sets.
2. Computes FOLLOW sets and constructs the SLR(1) ACTION/GOTO tables.
3. Uses a symbol stack and a state stack to parse input strings.
4. Exports SVG visualizations of the parsing steps and parse tree.
5. Writes a detailed report to `output.txt` and a table summary to `slr_table.txt`.

## Files
- main.py: driver program
- slr_core.py: grammar, SLR(1) table construction, parsing logic, report formatter
- svg_exporter.py: SVG export for parsing steps and parse trees
- input.txt: sample input strings (one per line)
- output.txt: generated report
- slr_table.txt: generated ACTION/GOTO table
- images/: SVG outputs (created at runtime)

## Run
From the `SLR(1)` folder:
```
python main.py
```

Custom paths:
```
python main.py -i input.txt -o output.txt --table slr_table.txt --img-dir images
```

## Input format
- One expression per line.
- Valid symbols: `i`, `+`, `*`, `(`, `)`.
- Optional trailing `;`, `$`, or `#` are ignored.
- Identifiers like `x` or `id` are treated as `i`.

## Output
The report contains:
- Grammar and numbered productions
- FOLLOW sets
- ACTION and GOTO tables
- Parsing steps for each input string
- Parse tree (text form) when accepted

SVG files are written to `images/`:
- `expression_XX_tree.svg`: parse tree
- `expression_XX_process.svg`: parsing steps
	- Stack view shows the state stack (left) and symbol stack (right) per step.

## SLR(1) analysis table

ACTION:
```
					 i      +      *      (      )      $
		 0     s2                   s1
		 1     s2                   s1
		 2            r7     r7            r7     r7
		 3            s8                          r1
		 4            r5     r5            r5     r5
		 5                                       acc
		 6            r3     s9            r3     r3
		 7            s8                  s10
		 8     s2                   s1
		 9     s2                   s1
		10            r6     r6            r6     r6
		11            r2     s9            r2     r2
		12            r4     r4            r4     r4
```

GOTO:
```
					 S      E      T      F
		 0      5      3      6      4
		 1             7      6      4
		 2
		 3
		 4
		 5
		 6
		 7
		 8                   11      4
		 9                          12
		10
		11
		12
```

## State transition rules

The parser follows the SLR(1) ACTION/GOTO tables derived from the LR(0) item sets and FOLLOW sets.

- shift (sX): push the input symbol and move to state X
- reduce (rK): pop |rhs| symbols, push lhs, then use GOTO to move to the next state
- accept (acc): input is accepted
- error: no ACTION for (state, lookahead)

Result interpretation:
- ACCEPT means the input string belongs to the grammar
- REJECT means the input string is not recognized by the grammar
