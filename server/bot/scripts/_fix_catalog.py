"""Fix catalog reviews.py and search.py boundary cut issue."""
src_lines = open('O:/baraholka/handlers/catalog.py.bak', encoding='utf-8').readlines()
imp = ''.join(src_lines[:35])
common_import = 'from ._common import *\n\n'

# reviews.py ends at line 3103 (include the 'pass' in try/except)
reviews_body = ''.join(src_lines[2567:3103])
open('O:/baraholka/handlers/catalog/reviews.py', 'w', encoding='utf-8').write(imp + common_import + reviews_body)
print(f"reviews.py: {reviews_body.count(chr(10))} body lines")

# search.py starts at line 3104
search_body = ''.join(src_lines[3103:3351])
open('O:/baraholka/handlers/catalog/search.py', 'w', encoding='utf-8').write(imp + common_import + search_body)
print(f"search.py: {search_body.count(chr(10))} body lines")

print("Fixed.")
