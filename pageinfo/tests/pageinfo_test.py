import os
import unittest
from logging import getLogger

import cv2

import pageinfo

logger = getLogger(__name__)
here = os.path.dirname(os.path.abspath(__file__))


def get_images_absdir(dirname):
    return os.path.join(here, 'images', dirname)


class PageinfoTest(unittest.TestCase):
    def _test_guess_pageinfo(self, images_dir, expected):
        for entry in os.listdir(images_dir):
            if os.path.splitext(entry)[1] not in ('.png', '.jpg'):
                continue
            impath = os.path.join(images_dir, entry)
            with self.subTest(image=impath):
                im = cv2.imread(impath)
                logger.debug(impath)
                try:
                    actual = pageinfo.guess_pageinfo(im)
                    self.assertEqual(actual, expected[entry])
                except pageinfo.CannotGuessError as e:
                    self.fail(f'{impath}: {e}')

    def test_guess_pageinfo_000(self):
        images_dir = get_images_absdir('000')
        expected = {
            '000.png': (1, 1, 0),
            '001.png': (1, 1, 0),
            '002.png': (1, 1, 3),
            '003.png': (1, 1, 3),
            '004.png': (1, 2, 4),
            '005.png': (2, 2, 4),
            '006.png': (1, 2, 6),
            '007.png': (2, 2, 6),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_001(self):
        """
            いわゆる「イシュタル弓問題」のテスト。
            背景領域のオブジェクトをスクロールバーと誤認する問題
        """
        images_dir = get_images_absdir('001')
        expected = {
            '000.png': (1, 1, 3),
            '001.png': (1, 2, 4),
            '002.png': (2, 2, 4),
            '003.png': (1, 1, 3),
            '004.png': (1, 2, 4),
            '005.png': (2, 2, 4),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_002(self):
        images_dir = get_images_absdir('002')
        expected = {
            '000.png': (2, 2, 5),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_003(self):
        """
            2ページ目なのに3ページ目と判定される不具合を修正。
        """
        images_dir = get_images_absdir('003')
        expected = {
            '000.png': (2, 2, 6),
            '001.png': (1, 3, 7),
            '002.png': (2, 3, 7),
            '003.png': (3, 3, 7),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_004(self):
        """
            スクロールバーの誤検出により認識エラーになる件について、
            スクロール可能領域を検出できない場合はスクロールバー
            なしと判定するようにした。
            https://github.com/max747/fgojunks/issues/1
        """
        images_dir = get_images_absdir('004')
        expected = {
            '000.png': (1, 1, 0),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_005(self):
        """
            png だと正常に通るが jpg だと NG なケースについて、
            パラメータを修正して対応した。
            https://github.com/max747/fgojunks/issues/2
        """
        images_dir = get_images_absdir('005')
        expected = {
            '000.png': (2, 2, 4),
            '000.jpg': (2, 2, 4),
            '001.png': (2, 2, 4),
            '001.jpg': (2, 2, 4),
            '002.jpg': (1, 2, 4),
            '003.png': (1, 2, 4),
            '003.jpg': (1, 2, 4),
            '004.png': (1, 2, 4),
            '004.jpg': (1, 2, 4),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_006(self):
        """
            閾値の設定が 26 以下ではスクロール可能領域の
            下端にヒゲが出てしまい矩形幅が広がってしまう jpg 画像。
        """
        images_dir = get_images_absdir('006')
        expected = {
            '000.jpg': (1, 2, 4),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_007(self):
        """
            jpg 画像でイシュタル弓問題を含むスクロールバー誤検出が
            発生するケース。
            000 イシュタル弓問題
                スクロールバー判定の閾値を 60 -> 61 に上げると解決する。
            001 スクロール可能領域をスクロールバーと誤検出
                スクロールバー判定の閾値を 64 以上に上げると解決する。
        """
        images_dir = get_images_absdir('007')
        expected = {
            '000.jpg': (1, 1, 3),
            '001.jpg': (1, 2, 5),
        }
        self._test_guess_pageinfo(images_dir, expected)
