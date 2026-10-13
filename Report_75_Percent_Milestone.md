# Case Study Progress Report: SLR(1) Parser Implementation
**Milestone Review: Phase 3 (75% Completion)**  
*Project: Design and Implementation of an SLR Parser for a Custom Imperative Programming Language*  
**Authors:** Anweshika Mehta (24BCE0790), Yuvraj Gupta (24BCE0797), Ajay Kumar Yadav (24BCE0805)

---

## 1. Executive Summary

This report documents the achievement of the **75% Completion Milestone** for the design and implementation of a Simple LR (SLR(1)) parser for a custom imperative programming language. 

In the initial **Phase 1 (25%)** submission, the project established the problem context, context-free grammar formulation, manual derivations of FIRST and FOLLOW sets, and the initial LR(0) item states ($I_0$ to $I_3$). 

Since Phase 1, the project has successfully completed:
1. **Phase 2 (50% Milestone - Automaton & Table Construction)**: Algorithmically discovering the complete 21-state LR(0) deterministic finite automaton (DFA) via iterative closure and goto transitions, and constructing the conflict-free SLR(1) ACTION and GOTO parsing tables.
2. **Phase 3 (75% Milestone - Parser Engine & Syntax Tree Generation)**: Implementing the full pushdown automaton shift-reduce driver engine, a semantic stack constructing hierarchical **Parse Trees**, an interactive CLI with table export capabilities, and an automated regression test suite comprising 14 unit tests.

The engine currently parses valid multi-statement assignments and expressions in linear $\mathcal{O}(n)$ time, guarantees zero shift/reduce or reduce/reduce conflicts, and accurately diagnoses syntax errors.

---

## 2. Updated Project Roadmap & Milestone Tracker

| Phase | Milestone Target | Scope & Deliverables | Status | Completion % |
| :---: | :--- | :--- | :---: | :---: |
| **Phase 1** | **Foundational Setup** | Problem formulation, CFG design, manual FIRST/FOLLOW sets, initial LR(0) items | Completed | **25%** |
| **Phase 2** | **Table & DFA Construction** | Automated closure/goto, 21-state LR(0) DFA generation, SLR(1) ACTION/GOTO table builder, conflict-free proof | Completed | **50%** |
| **Phase 3** | **Shift-Reduce Engine & AST** | Pushdown automaton driver, dual-stack engine, Parse Tree generator, table visualizer, automated test suite | **Completed (Current)** | **75%** |
| **Phase 4** | **Final Presentation & Packaging** | Final slide deck, presentation walkthrough, evaluator documentation | Scheduled | 100% |

---

## 3. Formal Language Grammar Specification

To model a realistic programming language rather than a simple mathematical expression evaluator, the grammar models statement sequencing, state mutation, and output:

### Production Rules
- **0**: `P' -> Program` (Augmented start production)
- **1**: `Program -> StmtList`
- **2**: `StmtList -> StmtList Stmt`
- **3**: `StmtList -> Stmt`
- **4**: `Stmt -> let id = Expr ;` (Variable declaration and assignment)
- **5**: `Stmt -> print Expr ;` (Console output statement)
- **6**: `Expr -> Expr + Term` (Addition, left-associative)
- **7**: `Expr -> Term`
- **8**: `Term -> Term * Factor` (Multiplication, higher precedence)
- **9**: `Term -> Factor`
- **10**: `Factor -> id` (Identifier)
- **11**: `Factor -> num` (Integer literal)

### Vocabulary
- **Terminals ($V_T$)**: `{ let, print, id, num, =, ;, +, *, $ }`
- **Non-Terminals ($V_N$)**: `{ P', Program, StmtList, Stmt, Expr, Term, Factor }`

---

## 4. Phase 2 Deliverables: Mathematical Automaton & Parsing Tables (50% Milestone)

### 4.1 Automated FIRST and FOLLOW Sets

The sets are computed using iterative fixed-point algorithms:

| Non-Terminal | FIRST Set | FOLLOW Set | Mathematical Rationale |
| :--- | :--- | :--- | :--- |
| `P'` | `{ let, print }` | `{ $ }` | Augmented start symbol terminates at EOF (`$`). |
| `Program` | `{ let, print }` | `{ $ }` | Root program body followed only by `$`. |
| `StmtList` | `{ let, print }` | `{ $, let, print }` | Followed by EOF or the start of the next statement. |
| `Stmt` | `{ let, print }` | `{ $, let, print }` | Statement end can precede another statement or `$`. |
| `Expr` | `{ id, num }` | `{ +, ; }` | Followed by operator `+` or statement terminator `;`. |
| `Term` | `{ id, num }` | `{ *, +, ; }` | Inherits `FOLLOW(Expr)` and includes multiplication `*`. |
| `Factor` | `{ id, num }` | `{ *, +, ; }` | Inherits `FOLLOW(Term)`. |

---

### 4.2 LR(0) Canonical States (Complete 21 States)

The closure of the augmented start item $[P' \to \cdot \text{Program}]$ under the BFS transition algorithm yields exactly 21 canonical states:

- **State 0**: $[P' \to \cdot \text{Program}]$, $[\text{Program} \to \cdot \text{StmtList}]$, $[\text{StmtList} \to \cdot \text{StmtList } \text{Stmt}]$, $[\text{StmtList} \to \cdot \text{Stmt}]$, $[\text{Stmt} \to \cdot \texttt{let } \mathbf{id} = \text{Expr} ;]$, $[\text{Stmt} \to \cdot \texttt{print } \text{Expr} ;]$
- **State 1**: $[\text{StmtList} \to \text{Stmt} \cdot]$
- **State 2**: $[\text{Stmt} \to \texttt{let } \cdot \mathbf{id} = \text{Expr} ;]$
- **State 3**: $[\text{Program} \to \text{StmtList} \cdot]$, $[\text{StmtList} \to \text{StmtList } \cdot \text{Stmt}]$, $[\text{Stmt} \to \cdot \texttt{let } \mathbf{id} = \text{Expr} ;]$, $[\text{Stmt} \to \cdot \texttt{print } \text{Expr} ;]$
- **State 4**: $[P' \to \text{Program} \cdot]$ *(Accepting State on `$`).*
- **State 5**: $[\text{Stmt} \to \texttt{print } \cdot \text{Expr} ;]$, $[\text{Expr} \to \cdot \text{Expr} + \text{Term}]$, $[\text{Expr} \to \cdot \text{Term}]$, $[\text{Term} \to \cdot \text{Term} * \text{Factor}]$, $[\text{Term} \to \cdot \text{Factor}]$, $[\text{Factor} \to \cdot \mathbf{id}]$, $[\text{Factor} \to \cdot \mathbf{num}]$
- **State 6**: $[\text{Stmt} \to \texttt{let } \mathbf{id} \cdot = \text{Expr} ;]$
- **State 7**: $[\text{StmtList} \to \text{StmtList } \text{Stmt} \cdot]$
- **State 8**: $[\text{Factor} \to \mathbf{num} \cdot]$
- **State 9**: $[\text{Term} \to \text{Factor} \cdot]$
- **State 10**: $[\text{Factor} \to \mathbf{id} \cdot]$
- **State 11**: $[\text{Stmt} \to \texttt{print } \text{Expr} \cdot ;]$, $[\text{Expr} \to \text{Expr } \cdot + \text{Term}]$
- **State 12**: $[\text{Expr} \to \text{Term} \cdot]$, $[\text{Term} \to \text{Term } \cdot * \text{Factor}]$
- **State 13**: $[\text{Stmt} \to \texttt{let } \mathbf{id} = \cdot \text{Expr} ;]$, $[\text{Expr} \to \cdot \text{Expr} + \text{Term}]$, $[\text{Expr} \to \cdot \text{Term}]$, $[\text{Term} \to \cdot \text{Term} * \text{Factor}]$, $[\text{Term} \to \cdot \text{Factor}]$, $[\text{Factor} \to \cdot \mathbf{id}]$, $[\text{Factor} \to \cdot \mathbf{num}]$
- **State 14**: $[\text{Stmt} \to \texttt{print } \text{Expr} ; \cdot]$
- **State 15**: $[\text{Expr} \to \text{Expr } + \cdot \text{Term}]$, $[\text{Term} \to \cdot \text{Term} * \text{Factor}]$, $[\text{Term} \to \cdot \text{Factor}]$, $[\text{Factor} \to \cdot \mathbf{id}]$, $[\text{Factor} \to \cdot \mathbf{num}]$
- **State 16**: $[\text{Term} \to \text{Term } * \cdot \text{Factor}]$, $[\text{Factor} \to \cdot \mathbf{id}]$, $[\text{Factor} \to \cdot \mathbf{num}]$
- **State 17**: $[\text{Stmt} \to \texttt{let } \mathbf{id} = \text{Expr} \cdot ;]$, $[\text{Expr} \to \text{Expr } \cdot + \text{Term}]$
- **State 18**: $[\text{Expr} \to \text{Expr } + \text{Term} \cdot]$, $[\text{Term} \to \text{Term } \cdot * \text{Factor}]$
- **State 19**: $[\text{Term} \to \text{Term } * \text{Factor} \cdot]$
- **State 20**: $[\text{Stmt} \to \texttt{let } \mathbf{id} = \text{Expr} ; \cdot]$

---

### 4.3 SLR(1) ACTION & GOTO Parsing Table Matrix

`sN` denotes Shift to State $N$; `rK` denotes Reduce by Production $K$; `acc` denotes Accept.

| State | let | print | id | num | = | ; | + | * | $ | Program | StmtList | Stmt | Expr | Term | Factor |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0** | s2 | s5 | | | | | | | | 4 | 3 | 1 | | | |
| **1** | r3 | r3 | | | | | | | r3 | | | | | | |
| **2** | | | s6 | | | | | | | | | | | | |
| **3** | s2 | s5 | | | | | | | r1 | | | 7 | | | |
| **4** | | | | | | | | | acc | | | | | | |
| **5** | | | s10 | s8 | | | | | | | | | 11 | 12 | 9 |
| **6** | | | | | s13 | | | | | | | | | | |
| **7** | r2 | r2 | | | | | | | r2 | | | | | | |
| **8** | | | | | | r11 | r11 | r11 | | | | | | | |
| **9** | | | | | | r9 | r9 | r9 | | | | | | | |
| **10** | | | | | | r10 | r10 | r10 | | | | | | | |
| **11** | | | | | | s14 | s15 | | | | | | | | |
| **12** | | | | | | r7 | r7 | s16 | | | | | | | |
| **13** | | | s10 | s8 | | | | | | | | | 17 | 12 | 9 |
| **14** | r5 | r5 | | | | | | | r5 | | | | | | |
| **15** | | | s10 | s8 | | | | | | | | | | 18 | 9 |
| **16** | | | s10 | s8 | | | | | | | | | | | 19 |
| **17** | | | | | | s20 | s15 | | | | | | | | |
| **18** | | | | | | r6 | r6 | s16 | | | | | | | |
| **19** | | | | | | r8 | r8 | r8 | | | | | | | |
| **20** | r4 | r4 | | | | | | | r4 | | | | | | |

#### Conflict-Free Proof
Programmatic validation confirms that **every entry in the ACTION and GOTO tables contains at most one action**:
- Total Shift/Reduce Conflicts: **0**
- Total Reduce/Reduce Conflicts: **0**
The grammar is strictly and deterministically **SLR(1)**.

---

## 5. Phase 3 Deliverables: Parser Engine & Parse Tree (75% Milestone)

### 5.1 Dual-Stack Pushdown Automaton Architecture
The parser implements a dual-stack pushdown automaton:
1. **State & Grammar Symbol Stack**: Stores alternating integer states and grammar symbols:
   ```text
   State Stack = [ 0, StmtList, 3, let, 2, id, 6, =, 13, Expr, 17, ;, 20 ]
   ```
2. **Semantic / Node Stack**: Holds instantiated `ParseTreeNode` objects. 
   - On **Shift**: A terminal token is wrapped in a leaf node: `ParseTreeNode(token_type, value=token_val)`.
   - On **Reduce** $A \to X_1 X_2 \dots X_k$: Exactly $k$ nodes are popped from the node stack, assigned as children of a new parent node `ParseTreeNode(A, children=[...])`, and pushed back onto the stack.
   - On **Accept**: The single root node remaining on the stack represents the complete syntax tree.

### 5.2 Parse Tree Visualization
Executing `python3 slr_parser.py "let x = 5 + 10 * y ;" --tree --quiet` generates the concrete parse tree:

```text
└── Program
    └── StmtList
        └── Stmt
            ├── let
            ├── id (x)
            ├── =
            ├── Expr
            │   ├── Expr
            │   │   └── Term
            │   │       └── Factor
            │   │           └── num (5)
            │   ├── +
            │   └── Term
            │       ├── Term
            │       │   └── Factor
            │       │       └── num (10)
            │       ├── *
            │       └── Factor
            │           └── id (y)
            └── ;
```

*Key Insight*: In the tree above, `10 * y` is grouped under `Term -> Term * Factor`, while addition `+` joins the outer `Expr`. This structurally proves that multiplication has higher precedence than addition without ambiguities.

---

## 6. Verification & Automated Testing Suite

An automated test suite (`test_parser.py`) containing 14 unit test cases validates the parser implementation:

```bash
$ python3 -m unittest -v test_parser.py
test_automaton_states_count (test_parser.TestSLRParser.test_automaton_states_count) ... ok
test_conflict_free_slr_table (test_parser.TestSLRParser.test_conflict_free_slr_table) ... ok
test_first_sets (test_parser.TestSLRParser.test_first_sets) ... ok
test_follow_sets (test_parser.TestSLRParser.test_follow_sets) ... ok
test_grammar_symbols (test_parser.TestSLRParser.test_grammar_symbols) ... ok
test_invalid_syntax_missing_expression (test_parser.TestSLRParser.test_invalid_syntax_missing_expression) ... ok
test_invalid_syntax_missing_semicolon (test_parser.TestSLRParser.test_invalid_syntax_missing_semicolon) ... ok
test_invalid_syntax_unbalanced_operator (test_parser.TestSLRParser.test_invalid_syntax_unbalanced_operator) ... ok
test_parse_tree_display (test_parser.TestSLRParser.test_parse_tree_display) ... ok
test_tokenizer (test_parser.TestSLRParser.test_tokenizer) ... ok
test_valid_multi_statement_program (test_parser.TestSLRParser.test_valid_multi_statement_program) ... ok
test_valid_operator_precedence (test_parser.TestSLRParser.test_valid_operator_precedence) ... ok
test_valid_print_statement (test_parser.TestSLRParser.test_valid_print_statement) ... ok
test_valid_single_assignment (test_parser.TestSLRParser.test_valid_single_assignment) ... ok

----------------------------------------------------------------------
Ran 14 tests in 0.003s

OK
```

---

## 7. Remaining Work for 100% Final Review

With the 75% milestone achieved, the remaining 25% to reach the 100% final project sign-off comprises:
1. **Final Presentation & Slide Deck**: Preparing visual presentation slides covering the problem context, grammar trade-offs, and demo walkthrough.
2. **Interactive Demonstration Packaging**: Packaging sample script test vectors for rapid live demonstration during evaluation.
3. **Optional Semantic Interpreter Extension**: Optionally adding symbol evaluation to execute parsed statements directly if requested for bonus credit.
