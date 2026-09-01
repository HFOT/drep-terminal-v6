#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成した drep-snapshot.json の最低限の健全性チェック。

CI で build-drep-snapshot.py の直後に走らせる。
Koios が部分的に落ちていた場合に、空 or 極端に欠けたスナップショットを
コミットしてしまうのを防ぐのが目的。
"""

import json
import os
import sys

# Windows のコンソールは既定が cp932 で、ADA 記号などを print すると落ちる。
# CI (UTF-8) でもローカルでも同じように動くように stdout を UTF-8 に固定する。
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.environ.get('DREP_OUT') or os.path.join(os.path.dirname(HERE), 'public', 'drep-snapshot.json')

MIN_DREPS = int(os.environ.get('DREP_MIN', '10'))


def main():
    if not os.path.exists(SNAP):
        print('FAIL: not found: ' + SNAP)
        return 1
    with open(SNAP, 'r', encoding='utf-8') as f:
        d = json.load(f)

    problems = []
    dreps = d.get('dreps') or []
    epochs = d.get('epochs') or []

    if not epochs:
        problems.append('epochs is empty')
    if len(dreps) < MIN_DREPS:
        problems.append('too few dreps: %d (need >= %d)' % (len(dreps), MIN_DREPS))
    if dreps and not dreps[0].get('latest_vp'):
        problems.append('top drep has no latest_vp')

    # 系列がまるごと欠けている DRep が多すぎないか
    empty = sum(1 for x in dreps
                if not any(v is not None for v in (x.get('series') or {}).values()))
    if dreps and empty > len(dreps) / 2:
        problems.append('%d/%d dreps have an empty series' % (empty, len(dreps)))

    if problems:
        for p in problems:
            print('FAIL: ' + p)
        return 1

    top = dreps[0]
    print('ok: epoch %s, %d dreps, %d epochs, top=%s (%s M), generated %s'
          % (d.get('epoch'), len(dreps), len(epochs),
             top.get('name'), top.get('latest_vp'), d.get('generated_at')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
