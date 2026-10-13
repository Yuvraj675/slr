import unittest
from slr_parser import SLRParser, tokenize, ParseTreeNode, ParseResult

class TestSLRParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = SLRParser()

    def test_grammar_symbols(self):
        expected_terminals = {"let", "print", "id", "num", "=", ";", "+", "*", "$"}
        expected_non_terminals = {"P'", "Program", "StmtList", "Stmt", "Expr", "Term", "Factor"}
        self.assertEqual(self.parser.terminals, expected_terminals)
        self.assertEqual(self.parser.non_terminals, expected_non_terminals)

    def test_first_sets(self):
        first = self.parser.first
        self.assertEqual(first["Expr"], {"id", "num"})
        self.assertEqual(first["Term"], {"id", "num"})
        self.assertEqual(first["Factor"], {"id", "num"})
        self.assertEqual(first["Stmt"], {"let", "print"})
        self.assertEqual(first["StmtList"], {"let", "print"})
        self.assertEqual(first["Program"], {"let", "print"})
        self.assertEqual(first["P'"], {"let", "print"})

    def test_follow_sets(self):
        follow = self.parser.follow
        self.assertEqual(follow["P'"], {"$"})
        self.assertEqual(follow["Program"], {"$"})
        self.assertEqual(follow["StmtList"], {"$", "let", "print"})
        self.assertEqual(follow["Stmt"], {"$", "let", "print"})
        self.assertEqual(follow["Expr"], {"+", ";"})
        self.assertEqual(follow["Term"], {"*", "+", ";"})
        self.assertEqual(follow["Factor"], {"*", "+", ";"})

    def test_automaton_states_count(self):
        self.assertEqual(len(self.parser.states), 21)

    def test_conflict_free_slr_table(self):
        # Verify no overlapping actions in LR(0) states using FOLLOW lookahead
        action_counts = {}
        for i, state in enumerate(self.parser.states):
            for prod_idx, dot_pos in state:
                lhs, rhs = self.parser.grammar[prod_idx]
                if dot_pos == len(rhs):
                    if prod_idx == 0:
                        action_counts[(i, "$")] = action_counts.get((i, "$"), 0) + 1
                    else:
                        for terminal in self.parser.follow[lhs]:
                            action_counts[(i, terminal)] = action_counts.get((i, terminal), 0) + 1
            for symbol in self.parser.terminals:
                if (i, symbol) in self.parser.transitions:
                    action_counts[(i, symbol)] = action_counts.get((i, symbol), 0) + 1

        conflicts = [k for k, count in action_counts.items() if count > 1]
        self.assertEqual(conflicts, [], f"SLR(1) conflicts detected: {conflicts}")

    def test_tokenizer(self):
        code = "let x = 42 + y * 7 ;"
        tokens = tokenize(code)
        expected = [
            ("let", "let"),
            ("id", "x"),
            ("=", "="),
            ("num", "42"),
            ("+", "+"),
            ("id", "y"),
            ("*", "*"),
            ("num", "7"),
            (";", ";"),
            ("$", "$")
        ]
        self.assertEqual(tokens, expected)

    def test_valid_single_assignment(self):
        tokens = tokenize("let a = 100 ;")
        result = self.parser.parse(tokens, verbose=False)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.tree)
        self.assertEqual(result.tree.symbol, "Program")

    def test_valid_print_statement(self):
        tokens = tokenize("print x + 5 ;")
        result = self.parser.parse(tokens, verbose=False)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.tree)

    def test_valid_operator_precedence(self):
        tokens = tokenize("let z = 2 + 3 * 4 ;")
        result = self.parser.parse(tokens, verbose=False)
        self.assertTrue(result.success)
        
        # Verify structure: Expr -> Expr + Term, where Term -> Term * Factor
        stmt_node = result.tree.children[0].children[0]
        expr_node = [c for c in stmt_node.children if c.symbol == "Expr"][0]
        
        # Left operand is Expr, operator is '+', right operand is Term
        self.assertEqual(expr_node.children[1].value, "+")
        right_term = expr_node.children[2]
        self.assertEqual(right_term.symbol, "Term")
        # Inside right_term, we must find '*' operator
        self.assertEqual(right_term.children[1].value, "*")

    def test_valid_multi_statement_program(self):
        code = "let a = 10 ; let b = 20 ; print a + b ;"
        tokens = tokenize(code)
        result = self.parser.parse(tokens, verbose=False)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.tree)

    def test_invalid_syntax_missing_expression(self):
        tokens = tokenize("let x = ;")
        result = self.parser.parse(tokens, verbose=False)
        self.assertFalse(result.success)
        self.assertIn("Unexpected token ';'", result.error_msg)

    def test_invalid_syntax_missing_semicolon(self):
        tokens = tokenize("let x = 10")
        result = self.parser.parse(tokens, verbose=False)
        self.assertFalse(result.success)
        self.assertIn("Unexpected token '$'", result.error_msg)

    def test_invalid_syntax_unbalanced_operator(self):
        tokens = tokenize("print 5 + ;")
        result = self.parser.parse(tokens, verbose=False)
        self.assertFalse(result.success)

    def test_parse_tree_display(self):
        tokens = tokenize("print 5 ;")
        result = self.parser.parse(tokens, verbose=False)
        tree_str = result.tree.display()
        self.assertIn("Program", tree_str)
        self.assertIn("StmtList", tree_str)
        self.assertIn("print", tree_str)
        self.assertIn("num (5)", tree_str)

if __name__ == "__main__":
    unittest.main()
