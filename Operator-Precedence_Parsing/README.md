# Operator-Precedence Parsing Lab
## 一、文法产生式
- E → E + T | T
- T → T * F |F
- F → (E) | i

## 二、计算FirstVT和LastVT集合

### FirstVT集合
- **FirstVT(F)** = { `(`, `i` }
- **FirstVT(T)**：由 `T * F` 得 `*`，由 `F` 得 FirstVT(F) = { `(`, `i` }  
  **FirstVT(T)** = { `*`, `(`, `i` }
- **FirstVT(E)**：由 `E + T` 得 `+`，由 `T` 得 FirstVT(T) = { `*`, `(`, `i` }  
  **FirstVT(E)** = { `+`, `*`, `(`, `i` }

### LastVT集合
- **LastVT(F)** = { `)`, `i` }
- **LastVT(T)**：由 `T * F` 得 `*`，由 `F` 得 LastVT(F) = { `)`, `i` }  
  **LastVT(T)** = { `*`, `)`, `i` }
- **LastVT(E)**：由 `E + T` 得 `+`，由 `T` 得 LastVT(T) = { `*`, `)`, `i` }  
  **LastVT(E)** = { `+`, `*`, `)`, `i` }

## 三、构造算符优先关系表

算符优先分析法只关心终结符之间的三种优先关系：
- `a ⋖ b`：a 的优先级低于 b（a 先于 b 被归约）
- `a ≐ b`：a 与 b 优先级相等（同时归约）
- `a ⋗ b`：a 的优先级高于 b（a 后于 b 被归约）

### 构造算法

#### 1. ≐ 关系
对产生式中相邻的终结符或终结符与非终结符紧邻的情况：  
形如 `...ab...` 或 `...aQb...`，则 `a ≐ b`。

**本例**：`F → (E)` 中有 `( E )`，所以 `( ≐ )`。

#### 2. ⋖ 关系
对每个形如 `aQ` 的相邻对（终结符 a 在非终结符 Q 之前），有：  
`a ⋖ b` 对所有 `b ∈ FirstVT(Q)`。

**本例**：
- `E → E + T` 中有 `+ T`，所以 `+ ⋖ FirstVT(T)` → `+ ⋖ *`，`+ ⋖ (`，`+ ⋖ i`
- `F → (E)` 中有 `( E`，所以 `( ⋖ FirstVT(E)` → `( ⋖ +`，`( ⋖ *`，`( ⋖ (`，`( ⋖ i`
- `T → T * F` 中有 `* F`，所以 `* ⋖ FirstVT(F)` → `* ⋖ (`，`* ⋖ i`

#### 3. ⋗ 关系
对每个形如 `Qa` 的相邻对（非终结符 Q 在终结符 a 之前），有：  
`b ⋗ a` 对所有 `b ∈ LastVT(Q)`。

**本例**：
- `E → E + T` 中有 `E +`，所以 LastVT(E) 中的 `+`、`*`、`)`、`i` 都 `⋗ +`
- `T → T * F` 中有 `T *`，所以 LastVT(T) 中的 `*`、`)`、`i` 都 `⋗ *`
- `F → (E)` 中有 `E )`，所以 LastVT(E) 中的 `+`、`*`、`)`、`i` 都 `⋗ )`

#### 4. 特殊处理 #
句子两端加上界符 `#`：
- `# ⋖ FirstVT(E)`
- `LastVT(E) ⋗ #`
- `# ≐ #`（接受状态）

### 完整算符优先关系表

|   | + | * | ( | ) | i | # |
|---|---|---|---|---|---|---|
| + | ⋗ | ⋖ | ⋖ | ⋗ | ⋖ | ⋗ |
| * | ⋗ | ⋗ | ⋖ | ⋗ | ⋖ | ⋗ |
| ( | ⋖ | ⋖ | ⋖ | ≐ | ⋖ |   |
| ) | ⋗ | ⋗ |   | ⋗ |   | ⋗ |
| i | ⋗ | ⋗ |   | ⋗ |   | ⋗ |
| # | ⋖ | ⋖ | ⋖ |   | ⋖ | ≐ |
## Goals

1. Build an operator-precedence parser for the expression grammar.
2. Compute FirstVT and LastVT sets.
3. Construct and output the precedence table.
4. Parse sample expressions and print the reduction process.
5. Export the parsing steps to SVG for visualization.

## Grammar

```
E -> E + T | T
T -> T * F | F
F -> ( E ) | i
```

Terminals: `+`, `*`, `(`, `)`, `i`, `#`

## Files

- main.py: entry point
- op_precedence.py: FirstVT/LastVT, precedence table, parser
- svg_exporter.py: SVG exporter for parse steps and parse tree
- input.txt: sample expressions
- output.txt: generated report
- precedence_table.txt: generated precedence table
- images/: SVG outputs

## Run

```bash
python main.py
```

Custom paths:

```bash
python main.py -i input.txt -o output.txt --table precedence_table.txt --img-dir images
```

## Notes

- The parser accepts expressions built from `i`, `+`, `*`, and parentheses.
- A trailing semicolon in the input is optional and will be ignored.
- The output includes the shift/reduce process for each expression.
- For accepted expressions, the parse tree SVG is exported as expression_XX_tree.svg.
- Parse tree nodes are colored and numbered by reduction order (lighter = earlier, darker = later).
- For rejected expressions, an ERROR tree is exported to show the stack/input state and error reason.
