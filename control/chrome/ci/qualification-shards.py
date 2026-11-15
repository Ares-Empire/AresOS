"""Expand each immutable qualification pair into a complete parallel partition."""
import ast
import json
from pathlib import Path
import re
import sys

source=Path(__file__).with_name('shards.mjs').read_text()
browser=ast.literal_eval(re.search(r'BROWSER_SHARDS=(\[[^;]+\]);',source)[1])
plan=json.loads(Path(sys.argv[1]).read_text())
shards=browser+[f'python-{index}' for index in range(4)]+['precedence']
rows=[{**pair,'shard':shard} for pair in plan['include'] for shard in shards]
assert len(rows)<=256
print(json.dumps({'include':rows},separators=(',',':')))
