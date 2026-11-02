"""Real qualification20 handoff records; exercise the reviewer's actual AST."""
import ast, copy, json, pathlib, re, unittest

ROOT = pathlib.Path.cwd()
SOURCE = ROOT / '.work/14/14zzb-qualification-proof.py'
REAL = ROOT / '.work/14/run-41324240079/evidence/two-disk'
nodes = ast.parse(SOURCE.read_text(encoding='utf-8')).body
index, = [i for i, n in enumerate(nodes) if isinstance(n, ast.Assign)
          and any(isinstance(t, ast.Name) and t.id == 'handoffs' for t in n.targets)]
selection = compile(ast.Module(body=[nodes[index]], type_ignores=[]), str(SOURCE), 'exec')
assert isinstance(nodes[index + 1], ast.Assert)
validation = compile(ast.Module(body=[nodes[index + 1]], type_ignores=[]), str(SOURCE), 'exec')
records = {p.name: json.loads(p.read_text()) for p in REAL.glob('*-handoff-*.json')}

class Files:
    def __init__(self, values): self.values = values
    def __truediv__(self, child):
        assert child == 'two-disk'
        return self
    def glob(self, pattern):
        assert pattern == '*-handoff-*.json'
        return [pathlib.Path(p) for p in self.values]

def review(values):
    env = dict(e=Files(values), read=lambda p: copy.deepcopy(values[p.name]), re=re)
    exec(selection, env)
    exec(validation, env)
    return env['handoffs']

class ReceiptTest(unittest.TestCase):
    def test_only_handoff_selector_changes(self):
        old = ast.parse((ROOT / '.work/14/14zzb/qualification-proof-at-dispatch.py').read_text(encoding='utf-8'))
        new = ast.parse(SOURCE.read_text(encoding='utf-8'))
        old.body[index] = new.body[index]
        self.assertEqual(ast.dump(old), ast.dump(new))
    def test_real_twelve_files_select_exact_three_receipts(self):
        self.assertEqual(len(records), 12)
        self.assertEqual(len(review(records)), 3)
    def test_missing_receipt_refuses(self):
        v = copy.deepcopy(records)
        del v[next(p for p in v if re.search(r'-handoff-[0-9]+\.json$', p))]
        with self.assertRaises(AssertionError): review(v)
    def test_extra_receipt_refuses(self):
        v = copy.deepcopy(records)
        v['unexpected-handoff-1.json'] = next(x for x in v.values() if x.get('handoff_ready'))
        with self.assertRaises(AssertionError): review(v)
    def test_wrong_ready_refuses(self):
        v = copy.deepcopy(records)
        next(x for x in v.values() if x.get('handoff_ready'))['ready'] = True
        with self.assertRaises(AssertionError): review(v)
    def test_echo_based_completion_refuses(self):
        v = copy.deepcopy(records)
        next(x for x in v.values() if x.get('handoff_ready'))['completion_uses_echo'] = True
        with self.assertRaises(AssertionError): review(v)

if __name__ == '__main__': unittest.main(verbosity=2)
