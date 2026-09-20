import re
import os
import sys

def fix_f2fs(kernel_folder):
    file_path = os.path.join(kernel_folder, 'fs', 'f2fs', 'file.c')
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace the 3-arg form with the 4-arg form required by 5.10.246.
    # Pattern matches: inc_valid_block_count(sbi, dn->inode, &reserved)
    # (with optional surrounding whitespace between tokens).
    # Does NOT touch calls that already have 4 arguments.
    content = re.sub(
        r'inc_valid_block_count\s*\(\s*sbi\s*,\s*dn->inode\s*,\s*&reserved\s*\)',
        r'inc_valid_block_count(sbi, dn->inode, &reserved, false)',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Successfully fixed inc_valid_block_count in {file_path}")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    fix_f2fs(target)
