"""Further split handlers/my_ads/edit.py into smaller files."""
import os

src_lines = open('O:/baraholka/handlers/my_ads.py.bak', encoding='utf-8').readlines()
imp = ''.join(src_lines[:37])
ci = 'from ._common import *\n\n'
D = 'O:/baraholka/handlers/my_ads'

def R(start, end):
    return ''.join(src_lines[start-1:end])

def W(name, body):
    path = f'{D}/{name}'
    content = imp + ci + body
    open(path, 'w', encoding='utf-8').write(content)
    print(f'  {name}: {content.count(chr(10))} lines')

# edit_menu.py — edit mode selection (approved/rejected/other)
W('edit_menu.py',
  R(367, 451) +   # my_ad_edit_callback
  R(566, 621))    # my_ad_edit_other_callback

# edit_price.py — price-only editing
W('edit_price.py',
  R(452, 565))    # my_ad_edit_price_callback, my_ad_edit_price_handler

# edit_fields.py — title/description/contact/size editing
W('edit_fields.py',
  R(622, 878))    # my_ad_edit_field_callback, field_handler, _build_edit_other_menu, contact

# edit_city.py — city/country selection
W('edit_city.py',
  R(987, 1425))   # city_callback, country_callback, custom handlers, city_back

# edit_category.py — category/subcategory/size selection
W('edit_category.py',
  R(1426, 1999))  # category/bike_group/subcategory/size callbacks + backs

# edit_confirm.py — confirm & send to moderation
W('edit_confirm.py',
  R(2250, 2397))  # my_ad_confirm_edit_callback, back_after_moderation

# Remove the monolithic edit.py
os.remove(f'{D}/edit.py')
print('Removed edit.py')

# Update __init__.py to include new modules
init = (
    '"""handlers/my_ads package."""\n'
    'from ._common import *\n'
    'from .list import *\n'
    'from .details import *\n'
    'from .edit_menu import *\n'
    'from .edit_price import *\n'
    'from .edit_fields import *\n'
    'from .edit_city import *\n'
    'from .edit_category import *\n'
    'from .edit_confirm import *\n'
    'from .edit_photos import *\n'
    'from .status import *\n'
    'from ._register import register_my_ads_handlers\n\n'
    '__all__ = ["register_my_ads_handlers"]\n'
)
open(f'{D}/__init__.py', 'w', encoding='utf-8').write(init)

# Update _register.py imports
reg_src = open(f'{D}/_register.py', encoding='utf-8').read()
reg_src = reg_src.replace(
    'from .edit import *\n',
    ('from .edit_menu import *\n'
     'from .edit_price import *\n'
     'from .edit_fields import *\n'
     'from .edit_city import *\n'
     'from .edit_category import *\n'
     'from .edit_confirm import *\n')
)
open(f'{D}/_register.py', 'w', encoding='utf-8').write(reg_src)
print('Updated _register.py imports')
print('Done.')
