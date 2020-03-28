#!/usr/bin/env python3

"""
    fgosscnt.py が出力した CSV を FGO 周回カウンタの報告形式に変換します。
    CSV の3行目以降を編集（追加、削除含む）した場合には、それらを集計しな
    おします。

    missing行がある場合、不完全なデータが混入している可能性があるため周回
    カウンタ書式の出力を行いません。missing行および、不完全なデータがあれ
    ばそれも取り除いてください。たいていの場合はmissing行の直前にある行を
    疑うとよいでしょう。
    また、無名アイテム (item000001 のような名前) がある場合も同様です。
    アイテムに名前を付けてから再実行してください。

    WARNING ログについては、CSVのサマリ行(2行目)と3行目以降の個別集計値を
    実際に列単位で合計した値が一致しない場合に出ます。これはmissing行の問
    題を解決するためにCSV行を手で編集した場合には起こりうることです。です
    ので、手で編集した場合は WARNING が出るのはおかしなことではありません。
    内容を一読し、問題なければ無視してかまいません。
"""

import argparse
import csv
import logging
import re
import sys

logger = logging.getLogger(__name__)

FGO_COUNTER_FORMAT = """
【{place}】{rounds}周
{report}
#FGO周回カウンタ http://aoshirobo.net/fatego/rc/
"""

piece_pattern = re.compile('([剣弓槍騎術殺狂][ピモ][0-9]+-)+', re.MULTILINE)
stone_pattern = re.compile('([剣弓槍騎術殺狂][秘魔輝][0-9]+-)+', re.MULTILINE)
qp_pattern = re.compile('(QP\(\+[0-9]+\)[0-9]+-)+', re.MULTILINE)

patterns = [
    piece_pattern,
    stone_pattern,
    qp_pattern,
]


def main(args):
    r = csv.reader(args.input)

    # 1行目はヘッダ、2行目はサマリ
    header = next(r)
    summary = next(r)

    unnamed_items = [name for name in header if name.startswith('item0')]
    if unnamed_items:
        logger.error('処理を中断します。無名のアイテムに名前を付けてください。')
        logger.error(unnamed_items)
        return

    # 明細行 (2行目以降) を手で編集した場合には summary と一致しなくなる。
    # 検証のため明細行を再計算する。
    actual_summary = [0] * len(header)
    rounds = 0
    has_migging_rows = False

    for i, row in enumerate(r):
        if row[0] == 'missing':
            logger.error(f'行{i+1}: missing')
            has_migging_rows = True
            continue

        if row[1] == '20+':
            pass
        else:
            rounds += 1

        for j, col in enumerate(row[2:], 2):
            if len(col) == 0:
                continue
            actual_summary[j] += int(col)

    # 再計算の結果が summary と異なる場合、ログに出力する
    for i in range(2, len(summary[2:])):
        if summary[i] != str(actual_summary[i]):
            logger.warning(f'列{i+1}: <{header[i]}> 報告値(2行目) {summary[i]} != 再集計値 {actual_summary[i]}')

    if has_migging_rows:
        logger.error('処理を中断します。missing行の問題を解決してください。')
        return

    # 再計算後の値を FGO 周回カウンタ報告書式の表示にする
    # 2列目は報告対象ではないことに注意
    report = '-'.join([f'{t[0]}{t[1]}' for t in zip(header[3:], actual_summary[3:])])

    for pattern in patterns:
        m = pattern.search(report)
        if m:
            logger.debug(f'pattern: {pattern}')
            logger.debug(f'match: {m}')
            spos = m.start()
            epos = m.end()
            logger.debug(f'spos-1: {report[spos-1]}')
            logger.debug(f'epos-1: {report[epos-1]}')

            if report[spos-1] == '-':
                report = report[:spos-1] + "\n" + report[spos:]
            if report[epos-1] == '-':
                report = report[:epos-1] + "\n" + report[epos:]

    args.output.write(FGO_COUNTER_FORMAT.format(place=args.place, rounds=rounds, report=report))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--output', type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('--loglevel', choices=('DEBUG', 'INFO'), default='INFO')
    parser.add_argument('--place', default='周回場所')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=args.loglevel, format='[%(levelname)s] %(message)s')
    main(args)