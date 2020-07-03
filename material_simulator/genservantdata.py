#!/usr/bin/env python3

import argparse
import csv
import json
import sys


def get_target_skill_level(current: int, threshold: int) -> int:
    if current <= threshold:
        return threshold
    else:
        return current


def main(args):
    reader = csv.reader(args.source, delimiter=args.delimiter)
    items = []

    for line in reader:
        # input format:
        #   no, mno, 略称, 正式名称, クラス, レアリティ, SP, 再臨, スキル1, スキル2, スキル3
        #
        # output format:
        #   mno, 再臨段階, 再臨目標, スキル1, スキル1目標, スキル2, スキル2目標, スキル3, スキル3目標, 1, 0
        #
        # mno は FGO material simulater における管理番号。FGO 本体の管理番号とは異なる。
        #
        # スキル9以下の場合は目標値9に、スキル10の場合は10に設定する。
        #

        # 再臨段階が未設定の行は未所持とみなし無視する
        if line[7] == '':
            continue

        mno = int(line[1])
        current_rank = int(line[7])
        target_rank = 4
        skill1 = int(line[8])
        skill2 = int(line[9])
        skill3 = int(line[10])

        items.append([
            mno, current_rank, target_rank,
            skill1, get_target_skill_level(skill1, args.threshold),
            skill2, get_target_skill_level(skill2, args.threshold),
            skill3, get_target_skill_level(skill3, args.threshold),
            1, 0,
        ])

    json.dump(items, args.dest)
    print('', file=args.dest)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('-d', '--dest', type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('--delimiter', default='\t')
    parser.add_argument('--threshold', type=int, default=9)
    return parser.parse_args()


if __name__ == '__main__':
    main(parse_args())
