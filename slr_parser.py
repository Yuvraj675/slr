import re
import sys
import argparse

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

    def parse(self, tokens):
        stack = [0]
        token_idx = 0
        
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
                print(f"{stack_disp:<40} | {input_str:<40} | Error: Unexpected token '{token_val}' at state {state}")
                return False
                
            action, val = self.action_table[(state, token_type)]
            
            if action == "Shift":
                print(f"{stack_disp:<40} | {input_str:<40} | Shift to state {val}")
                stack.append(token_type)
                stack.append(val)
                token_idx += 1
            elif action == "Reduce":
                lhs, rhs = self.grammar[val]
                print(f"{stack_disp:<40} | {input_str:<40} | Reduce by {val}: {lhs} -> {' '.join(rhs)}")
                for _ in range(2 * len(rhs)):
                    stack.pop()
                
                top_state = stack[-1]
                if (top_state, lhs) not in self.goto_table:
                    print(f"Error: Missing goto transition for state {top_state} and non-terminal {lhs}")
                    return False
                    
                next_state = self.goto_table[(top_state, lhs)]
                stack.append(lhs)
                stack.append(next_state)
            elif action == "Accept":
                print(f"{stack_disp:<40} | {input_str:<40} | Accept!")
                return True

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
    parser_arg = argparse.ArgumentParser(description="SLR Parser for a custom simple language")
    parser_arg.add_argument("code", nargs="?", help="Code string to parse")
    args = parser_arg.parse_args()

    if args.code:
        input_str = args.code
    else:
        print("Enter code to parse (e.g., 'let x = 5 + 10 * y ; print x ;'):")
        try:
            input_str = input()
        except EOFError:
            input_str = ""

    if not input_str.strip():
        print("No input provided.")
        sys.exit(1)

    parser = SLRParser()
    print(f"Tokenizing input: '{input_str}'")
    tokens = tokenize(input_str)
    print("Tokens:", tokens)
    print("\nStarting Parsing:")
    parser.parse(tokens)
