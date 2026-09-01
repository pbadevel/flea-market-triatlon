import os

packages = ['my_ads', 'catalog', 'admin_panel', 'moderation']
for pkg in packages:
    d = f'O:/baraholka/handlers/{pkg}'
    if not os.path.isdir(d):
        continue
    files = sorted(f for f in os.listdir(d) if f.endswith('.py'))
    total_lines = 0
    print(f'\n  handlers/{pkg}/')
    for f in files:
        path = f'{d}/{f}'
        n = open(path, encoding='utf-8').read().count('\n')
        total_lines += n
        mark = ' *** OVER 1000' if n > 1000 else ''
        print(f'    {f:<30s}  {n:5d} lines{mark}')
    print(f'    {"(total)":<30s}  {total_lines:5d} lines')
