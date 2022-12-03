#!/usr/bin/env python3

import argparse
import csv
import io
import json
import logging
import pathlib
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union

import tweepy  # type: ignore

import settings


RE_RUNCOUNT = re.compile(r'[0-9]+')
RE_ITEMCOUNT = re.compile(r'^(?P<item>.*[^0-9０-９]+)(?P<count>[0-9０-９]+)$')

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


def parse_header(header: str) -> Tuple[str, str]:
    # ex. ほうじ茶100回
    index = header.find("茶") + 1
    if index == 0:
        raise ParseError(f"invalid format: {header}")

    title = header[:index].strip()
    mo = RE_RUNCOUNT.search(header[index:len(header)].strip())
    if not mo:
        return title, ""
    count = mo.group()
    logger.info("%s %s", title, count)
    return title, count


def parse_text(text: str) -> Tuple[str, str, Dict[str, str]]:
    lines = text.strip().split("\n")
    title, count = parse_header(lines[0])
    item_dict: Dict[str, str] = {}

    for line in lines[1:]:
        cleaned = line.strip()
        if cleaned == "":
            continue
        if "#FGO開封カウンタ" in cleaned:
            return title, count, item_dict

        if "-" in cleaned:
            tokens = cleaned.split("-")
        else:
            tokens = [cleaned]
        
        for token in tokens:
            mo = RE_ITEMCOUNT.match(token)
            if not mo:
                logger.warning("could not parse the token: %s", token)
                continue
            d = mo.groupdict()
            item_dict[d['item'].strip()] = d['count'].strip()

    raise ParseError(f"hashtag not found: {text}")


class Report:
    def __init__(self, tweet_id: Union[int, str], screen_name: str, text: str, timestamp: Union[str, datetime]):
        self.tweet_id = str(tweet_id)
        self.screen_name = screen_name
        self.text = text
        if isinstance(timestamp, datetime):
            self.timestamp = timestamp.isoformat()
        else:
            self.timestamp = timestamp

    def __str__(self) -> str:
        return f"<{self.tweet_id} {self.screen_name} {self.timestamp}>"

    @property
    def permalink(self) -> str:
        return f"https://twitter.com/{self.screen_name}/status/{self.tweet_id}"

    def analyze(self) -> List[str]:
        normalized_text = unicodedata.normalize("NFKC", self.text)
        title, count, item_dict = parse_text(normalized_text)
        # 強制的に読み替える
        if title == "甘い茶":
            title = "甘いお茶"
        if title == "新撰茶":
            title = "新選茶"
        # 投稿ミスの訂正
        if self.tweet_id in ("1573092582099656705", "1573325796294656000"):
            title = "沢庵茶"
        if self.tweet_id == "1574581029586993152":
            title = "新選茶"
        if self.tweet_id == "1573330663859982336":
            count = "1000"
        obj = [
            self.timestamp,
            title,
            count,
            item_dict.get("牙", ""),
            item_dict.get("鎖", ""),
            item_dict.get("髄液", ""),
            item_dict.get("種", ""),
            item_dict.get("勾玉", ""),
            item_dict.get("勲章", ""),
            item_dict.get("ランタン", ""),
            item_dict.get("羽根", ""),
            item_dict.get("鬼灯", item_dict.get("鬼炎鬼灯", "")),
            item_dict.get("脂", item_dict.get("黒獣脂", item_dict.get("油", ""))),
            item_dict.get("心臓", item_dict.get("蛮神の心臓", "")),
            self.permalink,
        ]

        return obj

    def header_line(self) -> List[str]:
        return [
            "timestamp",
            "お茶",
            "回数",
            "牙",
            "鎖",
            "髄液",
            "種",
            "勾玉",
            "勲章",
            "ランタン",
            "羽根",
            "鬼灯",
            "脂",
            "心臓",
            "tweet",
        ]

    def to_dict(self) -> Dict[str, str]:
        return {
            "tweet_id": self.tweet_id,
            "screen_name": self.screen_name,
            "text": self.text,
            "timestamp": self.timestamp,
        }


class Agent:
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
    ):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)

    def collect(
        self,
        fetch_count: int = 100,
        since_id: Optional[int] = None,
    ) -> List[Report]:

        objects: List[Report] = []

        q = '#FGO開封カウンタ -filter:retweets'
        kwargs = {
            'q': q,
            'count': fetch_count,
            'tweet_mode': 'extended',
        }
        if since_id:
            kwargs['since_id'] = since_id
        tweets = self.api.search_tweets(**kwargs)

        for tweet in tweets:
            r = Report(tweet.id, tweet.user.screen_name, tweet.full_text, tweet.created_at)
            logger.info(r)
            objects.append(r)

        return objects


def retrieve_saved_reports(report_path: str) -> Dict[str, Report]:
    if not pathlib.Path(report_path).exists():
        return {}

    logger.info(f"load reports from file: {report_path}")
    with open(report_path) as fp:
        data = json.load(fp)

    reports: Dict[str, Report] = {}

    for d in data:
        r: Report = Report(**d)
        reports[r.tweet_id] = r

    return reports


def merge_and_sort(saved_reports: Dict[str, Report], new_reports: List[Report]) -> List[Report]:
    merged = list(saved_reports.values())

    for r in new_reports:
        if r.tweet_id not in saved_reports:
            merged.append(r)

    merged.sort(key=lambda r: r.tweet_id)
    return merged


def backup_prev_reportfile(report_path: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destdir = pathlib.Path("backup")
    destdir.mkdir(exist_ok=True)
    dest = destdir / f"{ts}.json"
    logger.info(f"copy previous report file for backup: {report_path} -> {dest}")
    shutil.copyfile(report_path, dest)


def output_reports(reports: List[Report], out: io.TextIOBase):
    w = csv.writer(out)
    w.writerow(reports[0].header_line())

    for r in reports:
        try:
            result = r.analyze()
        except ParseError as e:
            logger.error(e)
            logger.error(f"cannot parse {r.permalink}")
            continue
        w.writerow(result)


def save_reports(reports: List[Report], dest: str):
    serialized = [r.to_dict() for r in reports]
    logger.info(f"save reports to file: {dest}")
    with open(dest, "w") as fp:
        json.dump(serialized, fp)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=argparse.FileType("w"), default=sys.stdout)
    parser.add_argument("-s", "--since-id", type=int)
    parser.add_argument("-r", "--report-file", default="report.json")
    return parser.parse_args()


def main(args):
    saved_reports = retrieve_saved_reports(args.report_file)

    agent = Agent(
        settings.TwitterConsumerKey,
        settings.TwitterConsumerSecret,
        settings.TwitterAccessToken,
        settings.TwitterAccessTokenSecret,
    )
    new_reports = agent.collect(since_id=args.since_id)
    merged_reports = merge_and_sort(saved_reports, new_reports)

    if saved_reports:
        backup_prev_reportfile(args.report_file)

    output_reports(merged_reports, args.output)
    save_reports(merged_reports, args.report_file)


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main(args)
