"""
Split large handlers into sub-packages.
Run once from O:/baraholka: python scripts/_split_handlers.py
"""
import os, sys, shutil

BASE = 'O:/baraholka/handlers'

def read(path):
    return open(path, encoding='utf-8').read()

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(content)
    n = content.count('\n')
    print(f"  {path}  ({n} lines)")

def lines_range(src_lines, start, end):
    """1-based inclusive"""
    return ''.join(src_lines[start-1:end])

def imports_block(src_lines):
    """All lines before the first top-level async/def/class"""
    import re
    for i, l in enumerate(src_lines):
        if re.match(r'^(async def |def |class )', l):
            return ''.join(src_lines[:i])
    return ''

# ══════════════════════════════════════════════════════════════════
# 1.  my_ads  (3710 lines)
# ══════════════════════════════════════════════════════════════════
def split_my_ads():
    src = read(f'{BASE}/my_ads.py')
    L = src.splitlines(keepends=True)
    imp = imports_block(L)
    common_import = 'from ._common import *\n\n'
    D = f'{BASE}/my_ads'
    os.makedirs(D, exist_ok=True)

    # _common.py  — shared utilities
    write(f'{D}/_common.py', imp +
          lines_range(L, 39, 113) +    # _show_my_ads_page, needs_size
          lines_range(L, 167, 178) +   # delete_my_ad_info_message
          lines_range(L, 853, 878) +   # _build_edit_other_menu
          lines_range(L, 2000, 2031) + # update_channel_message
          lines_range(L, 2032, 2159) + # return_to_edit_menu
          lines_range(L, 2160, 2249))  # show_edit_preview

    # list.py
    write(f'{D}/list.py', imp + common_import +
          lines_range(L, 115, 166))    # my_ads_handler, my_ads_page_callback

    # details.py
    write(f'{D}/details.py', imp + common_import +
          lines_range(L, 179, 366) +   # my_ad_details_callback, back_from_ad_details
          lines_range(L, 3139, 3207))  # my_ad_edit_rejected_callback

    # edit.py  (text-field editing)
    write(f'{D}/edit.py', imp + common_import +
          lines_range(L, 367, 851) +   # edit_callback … field_handler (skip 853 block already in _common)
          lines_range(L, 879, 1999) +  # contact … size_back
          lines_range(L, 2250, 2397))  # confirm_edit, back_after_moderation

    # edit_photos.py
    write(f'{D}/edit_photos.py', imp + common_import +
          lines_range(L, 2529, 3138))  # cover + additional photo handlers

    # status.py  (sold / unpublish / republish / delete)
    write(f'{D}/status.py', imp + common_import +
          lines_range(L, 2398, 2528) + # my_ad_republish_callback
          lines_range(L, 3208, 3621))  # sold/unpublish/cancel/delete

    # _register.py
    reg_head = (imp +
                'from .list import *\n'
                'from .details import *\n'
                'from .edit import *\n'
                'from .edit_photos import *\n'
                'from .status import *\n'
                'from ._common import *\n\n')
    write(f'{D}/_register.py', reg_head + lines_range(L, 3622, len(L)))

    # __init__.py
    write(f'{D}/__init__.py',
          '"""handlers/my_ads — "Мои объявления" handlers."""\n'
          'from ._common import *\n'
          'from .list import *\n'
          'from .details import *\n'
          'from .edit import *\n'
          'from .edit_photos import *\n'
          'from .status import *\n'
          'from ._register import register_my_ads_handlers\n\n'
          '__all__ = ["register_my_ads_handlers"]\n')

    print("  [OK] my_ads split done")

# ══════════════════════════════════════════════════════════════════
# 2.  catalog  (4114 lines)
# ══════════════════════════════════════════════════════════════════
def split_catalog():
    src = read(f'{BASE}/catalog.py')
    L = src.splitlines(keepends=True)
    imp = imports_block(L)
    common_import = 'from ._common import *\n\n'
    D = f'{BASE}/catalog'
    os.makedirs(D, exist_ok=True)

    # _common.py  — page-rendering helpers
    write(f'{D}/_common.py', imp +
          lines_range(L, 36, 66) +      # _build_category_path
          lines_range(L, 815, 1044) +   # show_catalog_page
          lines_range(L, 1047, 1314) +  # show_category_items, _by_subcategories
          lines_range(L, 1315, 1410))   # show_ad_card

    # browse.py  — catalog navigation
    write(f'{D}/browse.py', imp + common_import +
          lines_range(L, 69, 814) +     # catalog_handler … back navigation
          lines_range(L, 786, 814))     # catalog_page_callback (overlapping, but fine)

    # details.py  — ad details + contact
    write(f'{D}/details.py', imp + common_import +
          lines_range(L, 1411, 1744) +  # ad_details_callback, ad_details_command, show_ad_details
          lines_range(L, 1747, 1756) +  # unpublished_ad_callback, sold_ad_callback
          lines_range(L, 1759, 1855) +  # contact_seller_callback
          lines_range(L, 3834, 3870))   # noop_callback, close_ad_details_callback

    # seller.py  — seller profile + ads
    write(f'{D}/seller.py', imp + common_import +
          lines_range(L, 1858, 2022) +  # seller_profile_callback, show_seller_profile
          lines_range(L, 2023, 2042) +  # seller_profile_page_callback
          lines_range(L, 2044, 2156))   # seller_ads_callback, show_seller_ads_page

    # reviews.py  — reviews + complaints
    write(f'{D}/reviews.py', imp + common_import +
          lines_range(L, 2568, 3100))   # reviews + complaint callbacks

    # search.py  — search functionality
    write(f'{D}/search.py', imp + common_import +
          lines_range(L, 3101, 3351))   # search handlers

    # filter.py  — catalog filters (city/country/type)
    write(f'{D}/filter.py', imp + common_import +
          lines_range(L, 3354, 3833))   # catalog_filter, city/country callbacks

    # back.py  — back navigation + main menu from catalog
    write(f'{D}/back.py', imp + common_import +
          lines_range(L, 2157, 2567) +  # catalog_back_callback (large section)
          lines_range(L, 3867, 4044))   # main_menu_callback from catalog

    # _register.py
    reg_head = (imp +
                'from .browse import *\n'
                'from .details import *\n'
                'from .seller import *\n'
                'from .reviews import *\n'
                'from .search import *\n'
                'from .filter import *\n'
                'from .back import *\n'
                'from ._common import *\n\n')
    write(f'{D}/_register.py', reg_head + lines_range(L, 4046, len(L)))

    # __init__.py
    write(f'{D}/__init__.py',
          '"""handlers/catalog — catalog & search handlers."""\n'
          'from ._common import *\n'
          'from .browse import *\n'
          'from .details import *\n'
          'from .seller import *\n'
          'from .reviews import *\n'
          'from .search import *\n'
          'from .filter import *\n'
          'from .back import *\n'
          'from ._register import register_catalog_handlers\n\n'
          '__all__ = ["register_catalog_handlers"]\n')

    print("  [OK] catalog split done")

# ══════════════════════════════════════════════════════════════════
# 3.  admin_panel  (2587 lines)
# ══════════════════════════════════════════════════════════════════
def split_admin_panel():
    src = read(f'{BASE}/admin_panel.py')
    L = src.splitlines(keepends=True)
    imp = imports_block(L)
    common_import = 'from ._common import *\n\n'
    D = f'{BASE}/admin_panel'
    os.makedirs(D, exist_ok=True)

    # _common.py  — shared admin helpers
    write(f'{D}/_common.py', imp +
          lines_range(L, 103, 177))     # check_admin_rights, _get_admin_main_menu, admin_command, admin_back

    # post.py  — /post_attach command
    write(f'{D}/post.py', imp + common_import +
          lines_range(L, 38, 102))      # post_attach_*

    # trusted.py  — trusted seller management
    write(f'{D}/trusted.py', imp + common_import +
          lines_range(L, 179, 549))     # admin_trusted_* + admin_roles_stub

    # users.py  — user ban/unban/csv
    write(f'{D}/users.py', imp + common_import +
          lines_range(L, 550, 883))     # admin_users_*

    # stats.py  — statistics
    write(f'{D}/stats.py', imp + common_import +
          lines_range(L, 884, 1377))    # admin_stats_*, _parse_*, _build_transitions_excel

    # ads.py  — ad management (delete/edit/view)
    write(f'{D}/ads.py', imp + common_import +
          lines_range(L, 1378, 2126) +  # admin_ads_menu, delete, edit, view
          lines_range(L, 2323, 2349))   # admin_edit_back

    # moderators.py  — moderator management
    write(f'{D}/moderators.py', imp + common_import +
          lines_range(L, 2127, 2281))   # admin_moderators_*

    # logs.py  — logs section
    write(f'{D}/logs.py', imp + common_import +
          lines_range(L, 2281, 2324))   # admin_logs

    # boost_settings.py  — boost settings п.2.4
    write(f'{D}/boost_settings.py', imp + common_import +
          lines_range(L, 2349, 2496))   # admin_boost_*

    # _register.py
    reg_head = (imp +
                'from .post import *\n'
                'from .trusted import *\n'
                'from .users import *\n'
                'from .stats import *\n'
                'from .ads import *\n'
                'from .moderators import *\n'
                'from .logs import *\n'
                'from .boost_settings import *\n'
                'from ._common import *\n\n')
    write(f'{D}/_register.py', reg_head + lines_range(L, 2497, len(L)))

    # __init__.py
    write(f'{D}/__init__.py',
          '"""handlers/admin_panel — admin panel handlers."""\n'
          'from ._common import *\n'
          'from .post import *\n'
          'from .trusted import *\n'
          'from .users import *\n'
          'from .stats import *\n'
          'from .ads import *\n'
          'from .moderators import *\n'
          'from .logs import *\n'
          'from .boost_settings import *\n'
          'from ._register import register_admin_panel_handlers\n\n'
          '__all__ = ["register_admin_panel_handlers"]\n')

    print("  [OK] admin_panel split done")

# ══════════════════════════════════════════════════════════════════
# 4.  moderation  (1011 lines)
# ══════════════════════════════════════════════════════════════════
def split_moderation():
    src = read(f'{BASE}/moderation.py')
    L = src.splitlines(keepends=True)
    imp = imports_block(L)
    common_import = 'from ._common import *\n\n'
    D = f'{BASE}/moderation'
    os.makedirs(D, exist_ok=True)

    # approve.py
    write(f'{D}/approve.py', imp +
          lines_range(L, 27, 465) +    # moderation_comment_*, approve_ad_callback
          lines_range(L, 707, 877) +   # approve_edit_callback
          lines_range(L, 956, 987))    # approve/reject_with_comment_callback

    # reject.py
    write(f'{D}/reject.py', imp +
          lines_range(L, 466, 706) +   # reject_ad_callback … process_rejection
          lines_range(L, 878, 955))    # reject_edit_callback, process_rejection_edit

    # _register.py
    reg_head = (imp +
                'from .approve import *\n'
                'from .reject import *\n\n')
    write(f'{D}/_register.py', reg_head + lines_range(L, 988, len(L)))

    # __init__.py
    write(f'{D}/__init__.py',
          '"""handlers/moderation — moderation handlers."""\n'
          'from .approve import *\n'
          'from .reject import *\n'
          'from ._register import register_moderation_handlers\n\n'
          '__all__ = ["register_moderation_handlers"]\n')

    print("  [OK] moderation split done")

# ══════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════
print("=== Splitting handlers ===")
split_my_ads()
split_catalog()
split_admin_panel()
split_moderation()

print("\n=== Renaming original files to .py.bak ===")
for name in ['my_ads', 'catalog', 'admin_panel', 'moderation']:
    src = f'{BASE}/{name}.py'
    dst = f'{BASE}/{name}.py.bak'
    if os.path.exists(src):
        os.rename(src, dst)
        print(f"  {src} → {dst}")

print("\nDone! Test the bot, then delete .bak files when satisfied.")
