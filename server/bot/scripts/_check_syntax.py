import ast, os

errors = []
for root, dirs, files in os.walk('O:/baraholka/handlers'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fname in files:
        if fname.endswith('.py') and not fname.endswith('.bak'):
            fpath = os.path.join(root, fname)
            try:
                ast.parse(open(fpath, encoding='utf-8').read())
            except SyntaxError as e:
                errors.append(f'{fpath}:{e.lineno}: {e.msg}')

if errors:
    for e in errors:
        print('SYNTAX ERROR:', e)
else:
    print('All handler files: no syntax errors')
