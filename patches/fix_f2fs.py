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

    # Clean up any corrupted line from previous unescaped sed if present
    content = re.sub(
        r'inc_valid_block_count\([^\)]*&reserved\)[^\)]*\)',
        r'inc_valid_block_count(sbi, dn->inode, &reserved, false)',
        content
    )

    # Standard 3-arg call to 4-arg call conversion
    content = re.sub(
        r'inc_valid_block_count\((sbi,\s*dn->inode,\s*&reserved)(?:,\s*false)?\)',
        r'inc_valid_block_count(\1, false)',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Successfully fixed inc_valid_block_count in {file_path}")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    fix_f2fs(target)
