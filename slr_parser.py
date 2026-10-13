import re
import sys
import argparse

class ParseTreeNode:
    def __init__(self, symbol, value=None, children=None):
        self.symbol = symbol
        self.value = value
        self.children = children if children is not None else []

    def display(self, indent="", is_last=True):
        branch = "└── " if is_last else "├── "
        val_str = f" ({self.value})" if self.value is not None and self.value != self.symbol else ""
        lines = [indent + branch + self.symbol + val_str]
        next_indent = indent + ("    " if is_last else "│   ")
        for i, child in enumerate(self.children):
            last = (i == len(self.children) - 1)
            lines.append(child.display(next_indent, last))
        return "\n".join(lines)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "value": self.value,
            "children": [c.to_dict() for c in self.children]
        }

    def __repr__(self):
        return f"ParseTreeNode({self.symbol}, value={self.value!r}, children_count={len(self.children)})"

class ParseResult:
    def __init__(self, success, tree=None, error_msg=None):
        self.success = success
        self.tree = tree
        self.error_msg = error_msg

    def __bool__(self):
        return self.success

    def __repr__(self):
        return f"ParseResult(success={self.success}, has_tree={self.tree is not None})"

class SLRParser:
    def __init__(self):
        # Epsilon-free Grammar for the custom language
        self.grammar = [
            ("P'", ["Program"]),
            ("Program", ["StmtList"]),
            ("StmtList", ["StmtList", "Stmt"]),
            ("StmtList", ["Stmt"]),
            ("Stmt", ["let", "id", "=", "Expr", ";"]),
            ("Stmt", ["print", "Expr", ";"]),
            ("Expr", ["Expr", "+", "Term"]),
            ("Expr", ["Term"]),
            ("Term", ["Term", "*", "Factor"]),
            ("Term", ["Factor"]),
            ("Factor", ["id"]),
            ("Factor", ["num"])
        ]
        
        self.non_terminals = {lhs for lhs, _ in self.grammar}
        self.terminals = {"let", "print", "id", "num", "=", ";", "+", "*", "$"}
        self.terminal_order = ["let", "print", "id", "num", "=", ";", "+", "*", "$"]
        self.non_terminal_order = ["Program", "StmtList", "Stmt", "Expr", "Term", "Factor"]
        
        self.first = self.compute_first()
        self.follow = self.compute_follow()
        
        self.states = []
        self.transitions = {}
        self.action_table = {}
        self.goto_table = {}
        
        self.build_automaton()
        self.build_parsing_table()

    def compute_first(self):
        first = {sym: set() for sym in self.non_terminals.union(self.terminals)}
        for t in self.terminals:
            first[t].add(t)
            
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar:
                if not rhs: continue
                sym = rhs[0]
                before_len = len(first[lhs])
                first[lhs].update(first[sym])
                if len(first[lhs]) > before_len:
                    changed = True
        return first

    def compute_follow(self):
        follow = {sym: set() for sym in self.non_terminals}
        follow["P'"].add("$")
        follow["Program"].add("$")
        
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar:
                for i, symbol in enumerate(rhs):
                    if symbol in self.non_terminals:
                        before_len = len(follow[symbol])
                        if i + 1 < len(rhs):
                            next_symbol = rhs[i+1]
                            follow[symbol].update(self.first[next_symbol])
                        else:
                            follow[symbol].update(follow[lhs])
                            
                        if len(follow[symbol]) > before_len:
                            changed = True
        return follow

    def closure(self, items):
        closure_set = set(items)
        changed = True
        while changed:
            new_items = set()
            for prod_idx, dot_pos in closure_set:
                lhs, rhs = self.grammar[prod_idx]
                if dot_pos < len(rhs):
                    symbol_after_dot = rhs[dot_pos]
                    if symbol_after_dot in self.non_terminals:
                        for i, (p_lhs, p_rhs) in enumerate(self.grammar):
                            if p_lhs == symbol_after_dot:
                                new_items.add((i, 0))
            if new_items.issubset(closure_set):
                changed = False
            else:
                closure_set.update(new_items)
        return frozenset(closure_set)

    def goto(self, items, symbol):
        goto_set = set()
        for prod_idx, dot_pos in items:
            lhs, rhs = self.grammar[prod_idx]
            if dot_pos < len(rhs) and rhs[dot_pos] == symbol:
                goto_set.add((prod_idx, dot_pos + 1))
        return self.closure(goto_set)

    def build_automaton(self):
        initial_item = (0, 0)
        initial_state = self.closure({initial_item})
        self.states = [initial_state]
        
        symbols = self.non_terminals.union(self.terminals)
        
        queue = [0]
        while queue:
            state_idx = queue.pop(0)
            state = self.states[state_idx]
            for symbol in symbols:
                next_state = self.goto(state, symbol)
                if not next_state: 
                    continue
                
                if next_state not in self.states:
                    self.states.append(next_state)
                    queue.append(len(self.states) - 1)
                    
                next_state_idx = self.states.index(next_state)
                self.transitions[(state_idx, symbol)] = next_state_idx

    def build_parsing_table(self):
        for i, state in enumerate(self.states):
            for prod_idx, dot_pos in state:
                lhs, rhs = self.grammar[prod_idx]
                if dot_pos == len(rhs):
                    if prod_idx == 0:
                        self.action_table[(i, "$")] = ("Accept", 0)
                    else:
                        for terminal in self.follow[lhs]:
                            self.action_table[(i, terminal)] = ("Reduce", prod_idx)
            
            for symbol in self.terminals.union(self.non_terminals):
                if (i, symbol) in self.transitions:
                    next_state = self.transitions[(i, symbol)]
                    if symbol in self.terminals:
                        self.action_table[(i, symbol)] = ("Shift", next_state)
                    elif symbol in self.non_terminals:
                        self.goto_table[(i, symbol)] = next_state

    def parse(self, tokens, verbose=True):
        stack = [0]
        node_stack = []
        token_idx = 0
        
        if verbose:
            print(f"{'Stack':<40} | {'Input Buffer':<40} | {'Action'}")
            print("-" * 100)
        
        while True:
            state = stack[-1]
            if token_idx < len(tokens):
                token_type, token_val = tokens[token_idx]
            else:
                break
            
            stack_disp = " ".join(map(str, stack))
            if len(stack_disp) > 38:
                stack_disp = "..." + stack_disp[-35:]
                
            input_str = " ".join(t[1] for t in tokens[token_idx:])
            if len(input_str) > 38:
                input_str = input_str[:35] + "..."
            
            if (state, token_type) not in self.action_table:
                err = f"Unexpected token '{token_val}' ({token_type}) at state {state}"
                if verbose:
                    print(f"{stack_disp:<40} | {input_str:<40} | Error: {err}")
                return ParseResult(False, error_msg=err)
                
            action, val = self.action_table[(state, token_type)]
            
            if action == "Shift":
                if verbose:
                    print(f"{stack_disp:<40} | {input_str:<40} | Shift to state {val}")
                stack.append(token_type)
                stack.append(val)
                node_stack.append(ParseTreeNode(token_type, value=token_val))
                token_idx += 1
            elif action == "Reduce":
                lhs, rhs = self.grammar[val]
                rhs_len = len(rhs)
                if verbose:
                    print(f"{stack_disp:<40} | {input_str:<40} | Reduce by {val}: {lhs} -> {' '.join(rhs)}")
                
                children = []
                for _ in range(rhs_len):
                    children.insert(0, node_stack.pop())
                parent_node = ParseTreeNode(lhs, children=children)
                node_stack.append(parent_node)

                for _ in range(2 * rhs_len):
                    stack.pop()
                
                top_state = stack[-1]
                if (top_state, lhs) not in self.goto_table:
                    err = f"Missing goto transition for state {top_state} and non-terminal {lhs}"
                    if verbose:
                        print(f"Error: {err}")
                    return ParseResult(False, error_msg=err)
                    
                next_state = self.goto_table[(top_state, lhs)]
                stack.append(lhs)
                stack.append(next_state)
            elif action == "Accept":
                if verbose:
                    print(f"{stack_disp:<40} | {input_str:<40} | Accept!")
                root_node = node_stack[-1] if node_stack else None
                return ParseResult(True, tree=root_node)

    def print_parsing_table(self):
        print("\n" + "=" * 105)
        print(" " * 38 + "SLR(1) PARSING TABLE")
        print("=" * 105)
        
        # Header line 1
        act_header = "ACTION".center(len(self.terminal_order) * 7)
        goto_header = "GOTO".center(len(self.non_terminal_order) * 7)
        print(f"{'State':<6} | {act_header} | {goto_header}")
        
        # Header line 2 (columns)
        term_cols = " ".join(f"{t:>6}" for t in self.terminal_order)
        non_term_cols = " ".join(f"{nt:>6}" for nt in self.non_terminal_order)
        print(f"{'':<6} | {term_cols} | {non_term_cols}")
        print("-" * 105)
        
        for i in range(len(self.states)):
            act_vals = []
            for t in self.terminal_order:
                if (i, t) in self.action_table:
                    act, val = self.action_table[(i, t)]
                    if act == "Shift":
                        act_vals.append(f"s{val:>4}")
                    elif act == "Reduce":
                        act_vals.append(f"r{val:>4}")
                    elif act == "Accept":
                        act_vals.append("acc".rjust(5))
                else:
                    act_vals.append(" " * 5)
            
            goto_vals = []
            for nt in self.non_terminal_order:
                if (i, nt) in self.goto_table:
                    goto_vals.append(f"{self.goto_table[(i, nt)]:>5}")
                else:
                    goto_vals.append(" " * 5)
            
            row_act = " ".join(f"{v:>6}" for v in act_vals)
            row_goto = " ".join(f"{v:>6}" for v in goto_vals)
            print(f"{i:<6} | {row_act} | {row_goto}")
        print("=" * 105 + "\n")

    def export_parsing_table_markdown(self, filepath="slr_table.md"):
        headers = ["State"] + [f"ACT:{t}" for t in self.terminal_order] + [f"GOTO:{nt}" for nt in self.non_terminal_order]
        lines = [
            "# SLR(1) Parsing Table",
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join([":---:"] * len(headers)) + " |"
        ]
        for i in range(len(self.states)):
            row = [str(i)]
            for t in self.terminal_order:
                if (i, t) in self.action_table:
                    act, val = self.action_table[(i, t)]
                    if act == "Shift": row.append(f"s{val}")
                    elif act == "Reduce": row.append(f"r{val}")
                    elif act == "Accept": row.append("acc")
                else:
                    row.append("")
            for nt in self.non_terminal_order:
                if (i, nt) in self.goto_table:
                    row.append(str(self.goto_table[(i, nt)]))
                else:
                    row.append("")
            lines.append("| " + " | ".join(row) + " |")
        
        with open(filepath, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Exported SLR(1) table to {filepath}")

    def export_parsing_table_csv(self, filepath="slr_table.csv"):
        import csv
        headers = ["State"] + [f"ACT_{t}" for t in self.terminal_order] + [f"GOTO_{nt}" for nt in self.non_terminal_order]
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for i in range(len(self.states)):
                row = [i]
                for t in self.terminal_order:
                    if (i, t) in self.action_table:
                        act, val = self.action_table[(i, t)]
                        if act == "Shift": row.append(f"s{val}")
                        elif act == "Reduce": row.append(f"r{val}")
                        elif act == "Accept": row.append("acc")
                    else:
                        row.append("")
                for nt in self.non_terminal_order:
                    if (i, nt) in self.goto_table:
                        row.append(self.goto_table[(i, nt)])
                    else:
                        row.append("")
                writer.writerow(row)
        print(f"Exported SLR(1) table to {filepath}")

def tokenize(input_string):
    tokens = []
    pattern = r'\s*(?:(let|print)|([a-zA-Z_]\w*)|(\d+)|([=;+*]))\s*'
    for match in re.finditer(pattern, input_string):
        if match.group(1):
            tokens.append((match.group(1), match.group(1)))
        elif match.group(2):
            tokens.append(("id", match.group(2)))
        elif match.group(3):
            tokens.append(("num", match.group(3)))
        elif match.group(4):
            tokens.append((match.group(4), match.group(4)))
    tokens.append(("$", "$"))
    return tokens

if __name__ == "__main__":
    parser_arg = argparse.ArgumentParser(description="SLR(1) Parser for a custom simple language")
    parser_arg.add_argument("code", nargs="?", help="Code string to parse")
    parser_arg.add_argument("--table", action="store_true", help="Display the SLR(1) parsing table (ACTION & GOTO)")
    parser_arg.add_argument("--tree", action="store_true", help="Display the generated Parse Tree")
    parser_arg.add_argument("--export-table", choices=["csv", "md"], help="Export table to file (slr_table.csv or slr_table.md)")
    parser_arg.add_argument("--quiet", action="store_true", help="Suppress trace output")
    args = parser_arg.parse_args()

    parser = SLRParser()

    if args.export_table:
        if args.export_table == "csv":
            parser.export_parsing_table_csv()
        elif args.export_table == "md":
            parser.export_parsing_table_markdown()

    if args.table:
        parser.print_parsing_table()
        if not args.code:
            sys.exit(0)

    if args.code:
        input_str = args.code
    elif not args.table and not args.export_table:
        print("Enter code to parse (e.g., 'let x = 5 + 10 * y ; print x ;'):")
        try:
            input_str = input()
        except EOFError:
            input_str = ""
    else:
        sys.exit(0)

    if not input_str.strip():
        print("No input provided.")
        sys.exit(1)

    tokens = tokenize(input_str)
    if not args.quiet:
        print(f"Tokenizing input: '{input_str}'")
        print("Tokens:", tokens)
        print("\nStarting Parsing:")
    
    result = parser.parse(tokens, verbose=not args.quiet)
    
    if result.success:
        if args.tree and result.tree:
            print("\nGenerated Parse Tree:")
            print("=" * 40)
            print(result.tree.display())
            print("=" * 40)
    else:
        sys.exit(1)
