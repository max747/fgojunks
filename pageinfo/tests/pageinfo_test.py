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
            impath = os.path.join(images_dir, entry)
            with self.subTest(image=impath):
                im = cv2.imread(impath)
                logger.debug(impath)
                actual = pageinfo.guess_pageinfo(im)
                self.assertEqual(actual, expected[entry])

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
        images_dir = get_images_absdir('003')
        expected = {
            '000.png': (2, 2, 6),
            '001.png': (1, 3, 7),
            '002.png': (2, 3, 7),
            '003.png': (3, 3, 7),
        }
        self._test_guess_pageinfo(images_dir, expected)

    def test_guess_pageinfo_004(self):
        images_dir = get_images_absdir('004')
        expected = {
            '000.png': (1, 1, 0),
        }
        self._test_guess_pageinfo(images_dir, expected)
