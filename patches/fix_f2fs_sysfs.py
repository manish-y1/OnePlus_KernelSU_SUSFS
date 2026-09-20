"""
fix_f2fs_sysfs.py  –  Remove duplicate static-function definitions from
fs/f2fs/sysfs.c that were left behind by the 5.10.236 → 5.10.246 ACK merge.

Strategy
--------
For every static function whose signature appears more than once, keep only
the *last* definition and remove all earlier copies.  The function body is
located by brace-matching so partial / multi-line bodies are handled safely.
"""

import re
import os
import sys


def _find_function_end(src: str, start: int) -> int:
    """
    Given an index into src that points at (or before) the opening '{' of a
    C function body, return the index immediately after the matching '}'.
    Returns -1 if no opening brace is found after start.
    """
    i = src.find('{', start)
    if i == -1:
        return -1
    depth = 0
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _remove_earlier_duplicates(content: str, func_name: str) -> tuple[str, int]:
    """
    Find all occurrences of 'static ssize_t <func_name>' (allowing whitespace
    variants), collect their span (start of the keyword up to the end of the
    function body including a trailing newline), then delete all but the last.

    Returns (new_content, number_of_removals).
    """
    # Match: optional newline then 'static' ... function name ... '('
    pattern = re.compile(
        r'static\s+ssize_t\s+' + re.escape(func_name) + r'\s*\('
    )

    spans = []
    for m in pattern.finditer(content):
        func_start = m.start()
        func_end = _find_function_end(content, m.end())
        if func_end == -1:
            continue
        # Consume trailing newline(s) so we don't leave blank lines
        while func_end < len(content) and content[func_end] in ('\n', '\r'):
            func_end += 1
        spans.append((func_start, func_end))

    if len(spans) <= 1:
        return content, 0

    # Remove all spans except the last, in reverse order so indices stay valid
    for start, end in reversed(spans[:-1]):
        content = content[:start] + content[end:]

    return content, len(spans) - 1


def fix_f2fs_sysfs(kernel_folder: str) -> None:
    file_path = os.path.join(kernel_folder, 'fs', 'f2fs', 'sysfs.c')
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as fh:
        content = fh.read()

    total_removed = 0
    # Known duplicates introduced by the 5.10.246 ACK merge
    for func in ('encoding_flags_show',):
        content, n = _remove_earlier_duplicates(content, func)
        if n:
            print(f"  Removed {n} duplicate definition(s) of '{func}'")
            total_removed += n

    if total_removed == 0:
        print("No duplicate definitions found in sysfs.c – nothing to do.")
        return

    with open(file_path, 'w', encoding='utf-8') as fh:
        fh.write(content)

    print(f"Successfully fixed fs/f2fs/sysfs.c ({total_removed} duplicate(s) removed)")


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    fix_f2fs_sysfs(target)
