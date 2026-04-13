#!/usr/bin/env python3
"""Fix garbled unicode replacement characters in a file."""
import sys

path = sys.argv[1]
t = open(path, encoding='utf-8').read()

replacements = [
    ('\ufffd\ufffd\u8def\u9019\u4ef6\u4e8b', '\u8d70\u8def\u9019\u4ef6\u4e8b'),
    ('\u6c92\ufffd\ufffd\u8aaa\u904e', '\u6c92\u6709\u8aaa\u904e'),
    ('\u98a8\u8755\ufffd\ufffd\u6709\u4e9b', '\u98a8\u8755\u5f97\u6709\u4e9b'),
    ('\ufffd\ufffd\u5fb7\u62ac\u982d', '\u51f1\u5fb7\u62ac\u982d'),
    ('\u99ac\ufffd\ufffd\u4e00\u8f1b', '\u99ac\u548c\u4e00\u8f1b'),
    ('\u62f3\u3002\ufffd\ufffd\ufffd\u6307', '\u62f3\u3002\u624b\u6307'),
    ('\u53bb\u4e86\ufffd\ufffd\u4ed6\u5728', '\u53bb\u4e86\u3002\u4ed6\u5728'),
    ('\u5427\u3002\ufffd\ufffd\u5403\u7684', '\u5427\u3002\u6709\u5403\u7684'),
    ('\u9577\ufffd\ufffd\ufffd\u4e0a', '\u9577\u51f3\u4e0a'),
    ('\u7d1a\u4e86\ufffd\ufffd\ufffd', '\u7d1a\u4e86\u3002'),
]

for old, new in replacements:
    t = t.replace(old, new)

open(path, 'w', encoding='utf-8').write(t)

has_garbled = '\ufffd' in t
if has_garbled:
    print('WARNING: Still has garbled characters')
    for i, line in enumerate(t.split('\n'), 1):
        if '\ufffd' in line:
            print(f'  Line {i}')
else:
    print('All garbled characters fixed')
