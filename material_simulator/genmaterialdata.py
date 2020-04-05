#!/usr/bin/env python3

import argparse
import csv
import json
import sys


def main(args):
    reader = csv.reader(args.source, delimiter=args.delimiter)
    items = {}

    for line in reader:
        # input format:
        #   no, mno, 名称, 略称, 所持数
        #
        # output format:
        #   mno, 所持数
        #
        # mno は FGO material simulater における管理番号。FGO 本体の管理番号とは異なる。
        #

        mno = line[1]
        # 所持数が未設定の行は所持数0とみなす
        if line[4].strip() == '':
            amount = 0
        else:
            amount = int(line[4])

        items[mno] = amount

    json.dump(items, args.dest)
    print('', file=args.dest)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', type=argparse.FileType, default=sys.stdin)
    parser.add_argument('-d', '--dest', type=argparse.FileType, default=sys.stdout)
    parser.add_argument('--delimiter', default='\t')
    return parser.parse_args()


if __name__ == '__main__':
    main(parse_args())
