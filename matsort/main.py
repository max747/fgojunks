#!/usr/bin/env python3

import argparse
import json
import sys


def setup_item_dict(data):
    item_dict = {}

    for item in data:
        if "shortname" not in item:
            continue
        item_dict[item["shortname"]] = item["dropPriority"]

    return item_dict


def clean_targets(targets):
    tokens = targets.split(",")
    cleaned_targets = []
    for t in tokens:
        token = t.strip()
        if token[0] == "'" and token[-1] == "'":
            cleaned_targets.append(token[1:-1])
        elif token[0] == '"' and token[-1] == '"':
            cleaned_targets.append(token[1:-1])
        else:
            cleaned_targets.append(token)

    return cleaned_targets


def main(args):
    data = json.load(args.json)
    item_dict = setup_item_dict(data)
    targets = clean_targets(args.targets.strip())
    print(" input: ", targets)
    targets.sort(key=lambda s: item_dict[s], reverse=True)
    print("sorted: ", targets)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--json", type=argparse.FileType("r"), default=sys.stdin)
    parser.add_argument("-t", "--targets", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)

