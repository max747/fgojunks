#!/usr/bin/env python3
#
# MIT License
# Copyright 2020 max747
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the 
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import argparse
import csv
import logging
import os
import sys

import cv2

logger = logging.getLogger('fgo')

NOSCROLL_PAGE_INFO = (1, 1, 0)


class CannotGuessError(Exception):
    pass


class TooManyAreasDetectedError(Exception):
    pass


def filter_contour_qp(contour, im):
    """
        "所持 QP" エリアを拾い、それ以外を除外するフィルター
    """
    im_w, im_h = im.shape[:2]
    # 画像全体に対する検出領域の面積比が一定以上であること。
    # 明らかに小さすぎる領域はここで捨てる。
    if cv2.contourArea(contour) * 25 < im_w * im_h:
        return False
    x, y, w, h = cv2.boundingRect(contour)
    # 横長領域なので、高さに対して十分大きい幅になっていること。
    if w < h * 6:
        return False
    # 横幅が画像サイズに対して長すぎず短すぎないこと。
    # 長すぎる場合は画面下部の端末別表示調整用領域を検出している可能性がある。
    if not (w * 1.2 < im_w < w * 2):
        return False
    logger.debug('qp region: (x, y, width, height) = (%s, %s, %s, %s)', x, y, w, h)
    return True


def filter_contour_scrollbar(contour, im):
    """
        スクロールバー領域を拾い、それ以外を除外するフィルター
    """
    im_w, im_h = im.shape[:2]
    # 画像全体に対する検出領域の面積比が一定以上であること。
    # 明らかに小さすぎる領域はここで捨てる。
    if cv2.contourArea(contour) * 80 < im_w * im_h:
        return False
    x, y, w, h = cv2.boundingRect(contour)
    logger.debug('scrollbar candidate: (x, y, width, height) = (%s, %s, %s, %s)', x, y, w, h)
    # 縦長領域なので、幅に対して十分大きい高さになっていること。
    if h < w * 5:
        return False
    logger.debug('scrollbar region: (x, y, width, height) = (%s, %s, %s, %s)', x, y, w, h)
    return True


def filter_contour_scrollable_area(contour, im):
    """
        スクロール可能領域を拾い、それ以外を除外するフィルター
    """
    im_w, im_h = im.shape[:2]
    # 画像全体に対する検出領域の面積比が一定以上であること。
    # 明らかに小さすぎる領域はここで捨てる。
    if cv2.contourArea(contour) * 50 < im_w * im_h:
        return False
    x, y, w, h = cv2.boundingRect(contour)
    logger.debug('scrollable area candidate: (x, y, width, height) = (%s, %s, %s, %s)', x, y, w, h)
    # 縦長領域なので、幅に対して十分大きい高さになっていること。
    if h < w * 10:
        return False
    logger.debug('scrollable area region: (x, y, width, height) = (%s, %s, %s, %s)', x, y, w, h)
    return True


def detect_qp_region(im, debug_draw_image=False, debug_image_name=None):
    """
        "所持 QP" 領域を検出する
    """
    # 縦横2分割して4領域に分け、左下の領域だけ使う。
    # QP の領域を調べたいならそれで十分。
    im_h, im_w = im.shape[:2]
    cropped = im[int(im_h/2):im_h, 0:int(im_w/2)]
    cr_h, cr_w = cropped.shape[:2]
    logger.debug('cropped image size (for qp): (width, height) = (%s, %s)', cr_w, cr_h)
    im_gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    binary_threshold = 25
    ret, th1 = cv2.threshold(im_gray, binary_threshold, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(th1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    filtered_contours = [c for c in contours if filter_contour_qp(c, im_gray)]
    if len(filtered_contours) == 1:
        qp_region = filtered_contours[0]
        x, y, w, h = cv2.boundingRect(qp_region)
        # 左右の無駄領域を除外する。
        # 感覚的な値ではあるが 左 12%, 右 7% を除外。
        topleft = (x + int(w*0.12), y)
        bottomright = (topleft[0] + w - int(w*0.12) - int(w*0.07), y + h)

        # TODO 切り出した領域をどう扱うか決めてない

        if debug_draw_image:
            cv2.rectangle(cropped, topleft, bottomright, (0, 0, 255), 3)

    if debug_draw_image:
        cv2.drawContours(cropped, filtered_contours, -1, (0, 255, 0), 3)
        logger.debug('writing debug image: %s', debug_image_name)
        cv2.imwrite(debug_image_name, cropped)


def guess_pages(actual_width, actual_height, entire_width, entire_height):
    """
        スクロールバー領域の高さからドロップ枠が何ページあるか推定する
    """
    if abs(entire_width - actual_width) > 6:
        # 比較しようとしている領域が異なる可能性が高い
        raise CannotGuessError(f'幅の誤差が大きすぎます: entire_width = {entire_width}, actual_width = {actual_width}')

    if actual_height * 1.1 > entire_height:
        return 1
    if actual_height * 2.2 > entire_height:
        return 2
    # 4 ページ以上 (ドロップ枠総数 > 63) になることはないと仮定。
    return 3


def guess_pagenum(actual_x, actual_y, entire_x, entire_y, entire_height):
    """
        スクロールバー領域の y 座標の位置からドロップ画像のページ数を推定する
    """
    if abs(actual_x - entire_x) > 5:
        # 比較しようとしている領域が異なる可能性が高い
        raise CannotGuessError(f'x 座標の誤差が大きすぎます: entire_x = {entire_x}, actual_x = {actual_x}')

    # スクロールバーと上端との空き領域の縦幅 delta と
    # スクロール可能領域の縦幅 entire_height との比率で位置を推定する。
    delta = actual_y - entire_y
    ratio = delta / entire_height
    logger.debug('space above scrollbar: %s, entire_height: %s, ratio: %s', delta, entire_height, ratio)
    if ratio < 0.1:
        return 1
    # 実測では 0.47-0.50 の間くらいになる。
    # 7列3ページの3ページ目の値が 0.55 近辺なので、あまり余裕を持たせて大きくしすぎてもいけない。
    # このあたりから 0.52 くらいが妥当な線ではないか。
    if ratio < 0.52:
        return 2
    # 4 ページ以上になることはないと仮定。
    return 3


def guess_lines(actual_width, actual_height, entire_width, entire_height):
    """
        スクロールバー領域の高さからドロップ枠が何行あるか推定する
        スクロールバーを用いる関係上、原理的に 2 行以下は推定不可
    """
    if abs(entire_width - actual_width) > 6:
        # 比較しようとしている領域が異なる可能性が高い
        raise CannotGuessError(f'幅の誤差が大きすぎます: entire_width = {entire_width}, actual_width = {actual_width}')

    ratio = actual_height / entire_height
    logger.debug('scrollbar ratio: %s', ratio)
    if ratio > 0.90:    # 実測値 0.94
        return 3
    elif ratio > 0.70:  # 実測値 0.72-0.73
        return 4
    elif ratio > 0.57:  # 実測値 0.59-0.60
        return 5
    elif ratio > 0.48:  # 実測値 0.50-0.51
        return 6
    elif ratio > 0.40:  # サンプルなし 参考値 1/2.333 = 0.429, 1/2.5 = 0.4
        return 7
    elif ratio > 0.36:  # サンプルなし 参考値 1/2.666 = 0.375, 1/2.77 = 0.361
        return 8
    else:
        # 10 行以上は考慮しない
        return 9


def _detect_scrollbar_region(im, binary_threshold, filter_func):
    ret, th1 = cv2.threshold(im, binary_threshold, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(th1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return [c for c in contours if filter_func(c, im)]
    

def guess_pageinfo(im, debug_draw_image=False, debug_image_name=None):
    """
        ページ情報を推定する。
        返却値は (現ページ数, 全体ページ数, 全体行数)
        スクロールバーがない場合は全体行数の推定は不可能。その場合は
        NOSCROLL_PAGE_INFO すなわち (1, 1, 0) を返す
    """
    # 縦4分割して4領域に分け、一番右の領域だけ使う。
    # スクロールバーの領域を調べたいならそれで十分。
    im_h, im_w = im.shape[:2]
    cropped = im[0:im_h, int(im_w*3/4):im_w]
    cr_h, cr_w = cropped.shape[:2]
    logger.debug('cropped image size (for scrollbar): (width, height) = (%s, %s)', cr_w, cr_h)
    im_gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

    # 二値化の閾値を高めにするとスクロールバー本体の領域を検出できる。
    # 低めにするとスクロールバー可動域全体の領域を検出できる。
    threshold_for_actual = 60
    threshold_for_entire = 25
    
    actual_scrollbar_contours = _detect_scrollbar_region(
        im_gray, threshold_for_actual, filter_contour_scrollbar)
    if len(actual_scrollbar_contours) == 0:
        # スクロールバーがない場合はページ数1、全体行数は推定不能
        return NOSCROLL_PAGE_INFO

    scrollable_area_contours = _detect_scrollbar_region(
        im_gray, threshold_for_entire, filter_contour_scrollable_area)
    if len(scrollable_area_contours) == 0:
        # スクロール可能領域が検出できない場合、元のスクロールバーが
        # 誤認識の可能性がきわめて高い。よってこのケースはスクロールバー
        # なしとして扱う
        return NOSCROLL_PAGE_INFO

    if debug_draw_image:
        cv2.drawContours(cropped, actual_scrollbar_contours, -1, (0, 255, 0), 3)
        cv2.drawContours(cropped, scrollable_area_contours, -1, (255, 0, 0), 3)
        logger.debug('writing debug image: %s', debug_image_name)
        cv2.imwrite(debug_image_name, cropped)

    if len(actual_scrollbar_contours) > 1:
        n = len(actual_scrollbar_contours)
        raise TooManyAreasDetectedError(f'{n} actual scrollbar areas are detected')
    if len(scrollable_area_contours) > 1:
        n = len(scrollable_area_contours)
        raise TooManyAreasDetectedError(f'{n} scrollable areas are detected')

    actual_scrollbar_region = actual_scrollbar_contours[0]
    asr_x, asr_y, asr_w, asr_h = cv2.boundingRect(actual_scrollbar_region)
    scrollable_area_region = scrollable_area_contours[0]
    esr_x, esr_y, esr_w, esr_h = cv2.boundingRect(scrollable_area_region)

    pages = guess_pages(asr_w, asr_h, esr_w, esr_h)
    pagenum = guess_pagenum(asr_x, asr_y, esr_x, esr_y, esr_h)
    lines = guess_lines(asr_w, asr_h, esr_w, esr_h)
    return (pagenum, pages, lines)


def look_into_file(filename, args):
    logger.debug(f'===== {filename}')

    im = cv2.imread(filename)
    if im is None:
        raise FileNotFoundError(f'Cannot read file: {filename}')

    im_h, im_w = im.shape[:2]
    logger.debug('image size: (width, height) = (%s, %s)', im_w, im_h)

    # TODO QP 領域をどう扱うか未定
    # if args.debug_qp:
    #     debug_qp_dir = os.path.join(args.debug_out_dir, 'qp')
    #     os.makedirs(debug_qp_dir, exist_ok=True)
    #     debug_qp_image = os.path.join(debug_qp_dir, os.path.basename(filename))
    # else:
    #     debug_qp_image = None
    # detect_qp_region(im, args.debug_qp, debug_qp_image)

    if args.debug_sc:
        debug_sc_dir = os.path.join(args.debug_out_dir, 'sc')
        os.makedirs(debug_sc_dir, exist_ok=True)
        debug_sc_image = os.path.join(debug_sc_dir, os.path.basename(filename))
    else:
        debug_sc_image = None
    pagenum, pages, lines = guess_pageinfo(im, args.debug_sc, debug_sc_image)
    logger.debug('pagenum: %s, pages: %s, lines: %s', pagenum, pages, lines)
    return (pagenum, pages, lines)


def main(args):
    csvdata = []

    for filename in args.filename:
        if os.path.isdir(filename):
            for child in os.listdir(filename):
                path = os.path.join(filename, child)
                result = look_into_file(path, args)
                csvdata.append((path, *result))
        else:
            result = look_into_file(filename, args)
            csvdata.append((filename, *result))

    csv_writer = csv.writer(args.output, lineterminator='\n')
    csv_writer.writerows(csvdata)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='+')
    parser.add_argument(
        '-l', '--loglevel',
        choices=('DEBUG', 'INFO', 'WARNING'),
        default='INFO',
        help='set loglevel [default: INFO]',
    )
    # parser.add_argument(
    #     '-dq', '--debug-qp',
    #     action='store_true',
    #     help='enable writing qp image for debug',
    # )
    parser.add_argument(
        '-ds', '--debug-sc',
        action='store_true',
        help='enable writing sc image for debug',
    )
    parser.add_argument(
        '-do', '--debug-out-dir',
        default='debugimages',
        help='output directory for debug images [default: debugimages]',
    )
    parser.add_argument(
        '-o', '--output',
        type=argparse.FileType('w'),
        default=sys.stdout,
        help='output file [default: STDOUT]',
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    logger.setLevel(args.loglevel)
    main(args)
