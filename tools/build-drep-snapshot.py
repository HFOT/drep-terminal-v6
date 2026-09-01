#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DRep Terminal 用スナップショット生成。

Koios の無料エンドポイントだけを使って public/drep-snapshot.json を書き出す。
GitHub Actions から 1 日 1 回まわす想定。stdlib のみ (pip 不要)。

使うエンドポイント (いずれも無料・APIキー不要):
  GET  /tip                          現在の epoch
  GET  /drep_list?limit=&offset=     登録 DRep の id 一覧
  POST /drep_info {_drep_ids:[...]}  VP・active・meta_url
  GET  /drep_history?_drep_id=       epoch ごとの VP 系列
  GET  /drep_delegators?_drep_id=    委任者数 (Range ヘッダで件数だけ取る)
  GET  meta_url (CIP-119 JSON-LD)    表示名・画像

name_ja と category は Koios から取れない手作業の値なので
tools/drep-curated.json から id で引き継ぐ。
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

KOIOS = 'https://api.koios.rest/api/v1'
TOP_N = int(os.environ.get('DREP_TOP_N', '50'))
EPOCH_WINDOW = int(os.environ.get('DREP_EPOCH_WINDOW', '75'))
PAUSE = float(os.environ.get('DREP_PAUSE', '0.15'))
UA = 'cignal-drep-snapshot/1.0 (+https://github.com/HFOT)'

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CURATED = os.path.join(HERE, 'drep-curated.json')
# 出力先。public/ を持たないリポジトリ (公開用の単体リポジトリ等) では
# 環境変数 DREP_OUT でルート直下などに切り替える。
OUT = os.environ.get('DREP_OUT') or os.path.join(ROOT, 'public', 'drep-snapshot.json')


def log(msg):
    sys.stderr.write(msg + os.linesep)
    sys.stderr.flush()


def _open(url, data=None, headers=None, timeout=90):
    h = {'Accept': 'application/json', 'User-Agent': UA}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=h)
    return urllib.request.urlopen(req, timeout=timeout)


def api(url, data=None, headers=None, tries=3, timeout=90):
    """JSON を返す。失敗したら指数バックオフで再試行し、最後は None。"""
    last = None
    for i in range(tries):
        try:
            with _open(url, data, headers, timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(1.5 * (2 ** i))
    log('  ! failed: ' + url[:90] + ' -> ' + repr(last))
    return None


def count_only(url):
    """PostgREST の Content-Range から件数だけ取る (本体は 1 行しか転送しない)。"""
    cr = ''
    try:
        with _open(url, headers={'Prefer': 'count=exact', 'Range': '0-0'}, timeout=90) as r:
            cr = r.headers.get('Content-Range') or ''
    except urllib.error.HTTPError as e:
        if e.headers:
            cr = e.headers.get('Content-Range') or ''
    except Exception:
        return None
    if '/' in cr:
        tail = cr.split('/')[-1].strip()
        if tail.isdigit():
            return int(tail)
    return None


def lovelace_to_m(v):
    """lovelace -> M ADA (百万 ADA)。"""
    try:
        return round(float(v) / 1e12, 3)
    except Exception:
        return None


def pick_name(meta):
    body = (meta or {}).get('body') or {}
    gn = body.get('givenName')
    if isinstance(gn, str):
        return gn.strip()
    if isinstance(gn, dict):
        v = gn.get('@value')
        if v:
            return str(v).strip()
    return ''


def pick_image(meta):
    body = (meta or {}).get('body') or {}
    img = body.get('image')
    url = ''
    if isinstance(img, str):
        url = img
    elif isinstance(img, dict):
        url = img.get('contentUrl') or img.get('@value') or ''
    url = str(url)
    return url if url[:4] == 'http' else ''


def make_ticker(name):
    keep = ''.join(c if (c.isalnum() and ord(c) < 128) else ' ' for c in name)
    words = keep.split()
    if not words:
        return ''
    if len(words) == 1:
        return words[0].upper()[:8]
    return ''.join(w[0] for w in words).upper()[:6]


def main():
    curated = {}
    if os.path.exists(CURATED):
        with open(CURATED, 'r', encoding='utf-8') as f:
            curated = json.load(f)
    log('curated entries: %d' % len(curated))

    tip = api(KOIOS + '/tip')
    if not tip:
        log('FATAL: /tip failed')
        return 1
    epoch = int(tip[0]['epoch_no'])
    log('current epoch: %d' % epoch)

    # ── DRep id 一覧 (ページング) ──
    ids = []
    off = 0
    while True:
        page = api(KOIOS + '/drep_list?limit=1000&offset=%d' % off)
        if not page:
            break
        ids.extend([d['drep_id'] for d in page if d.get('drep_id')])
        if len(page) < 1000:
            break
        off += 1000
        time.sleep(PAUSE)
    log('registered dreps: %d' % len(ids))
    if not ids:
        log('FATAL: drep_list empty')
        return 1

    # ── VP / active / meta_url ──
    info = []
    for i in range(0, len(ids), 50):
        chunk = api(KOIOS + '/drep_info', data={'_drep_ids': ids[i:i + 50]})
        if chunk:
            info.extend(chunk)
        time.sleep(PAUSE)
    log('drep_info rows: %d' % len(info))

    active = []
    for d in info:
        if not d.get('active'):
            continue
        vp = lovelace_to_m(d.get('amount') or 0)
        if not vp or vp <= 0:
            continue
        active.append({'id': d['drep_id'], 'vp': vp, 'meta_url': d.get('meta_url') or ''})
    active.sort(key=lambda x: -x['vp'])
    top = active[:TOP_N]
    log('active dreps: %d  -> top %d' % (len(active), len(top)))

    epochs = [str(e) for e in range(epoch - EPOCH_WINDOW + 1, epoch + 1)]
    want = set(epochs)
    dreps = []

    for n, d in enumerate(top, 1):
        did = d['id']

        hist = api(KOIOS + '/drep_history?_drep_id=' + did) or []
        series = {}
        for row in hist:
            ep = str(row.get('epoch_no'))
            if ep in want:
                series[ep] = lovelace_to_m(row.get('amount') or 0)
        full = {}
        for ep in epochs:
            full[ep] = series.get(ep)

        latest = full.get(epochs[-1])
        if latest is None:
            latest = d['vp']
        prev = full.get(epochs[-2]) if len(epochs) > 1 else None
        chg = None
        if prev and latest is not None and prev > 0:
            chg = round((latest - prev) / prev * 100, 2)

        cnt = count_only(KOIOS + '/drep_delegators?_drep_id=' + did)
        time.sleep(PAUSE)

        name, image = '', ''
        if d['meta_url']:
            meta = api(d['meta_url'], tries=2, timeout=25)
            if meta:
                name = pick_name(meta)
                image = pick_image(meta)

        cur = curated.get(did) or {}
        if not name:
            name = cur.get('name') or (did[:12] + '...')

        rec = {
            'rank': n,
            'id': did,
            'name': name,
            'name_ja': cur.get('name_ja') or '',
            'category': cur.get('category') or '不明',
            'latest_vp': latest,
            'change_pct': chg,
            'series': full,
            'delegators': cnt,
            # Koios は epoch 粒度 (1 epoch = 5 日) なので本当の 24h 変化は取れない。
            # 前 epoch 比を入れ、UI 側のラベルも「前EP比」にしてある。
            'chg_24h': chg,
            'ticker': cur.get('ticker') or make_ticker(name),
        }
        if image:
            rec['image'] = image
        dreps.append(rec)
        log('  [%2d/%d] %-28s vp=%-10s del=%s' % (n, len(top), name[:28], latest, cnt))

    out = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'epoch': epoch,
        'source': 'koios',
        'epochs': epochs,
        'dreps': dreps,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    log('wrote %s (%d bytes, epoch %d, %d dreps)'
        % (OUT, os.path.getsize(OUT), epoch, len(dreps)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
