#!/usr/bin/env python3

import argparse
import logging
import io
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_QUALITY = 90


def convert(
        f: io.FileIO,
        prefix: str = '',
        quality: int = DEFAULT_QUALITY,
        shrink_ratio: int = 100,
        dryrun: bool = False,
    ) -> None:

    logger.info(f.name)
    im = Image.open(f)
    logger.debug('%s %s %s', im.format, im.mode, im.size)

    if im.format == 'JPEG':
        logger.warning('skip converting JPEG image: %s', f.name)
        return

    p = Path(f.name)
    jpeg_path = p.with_suffix('.jpg')
    if prefix:
        jpeg_path = jpeg_path.parent / f'{prefix}_{jpeg_path.name}'

    logger.info(' -> %s', jpeg_path)

    if dryrun:
        return

    im_rgb = im.convert('RGB')
    if shrink_ratio < 100:
        w = im.width * shrink_ratio // 100
        h = im.height * shrink_ratio // 100
        logger.debug('resize: %s -> %s', im.size, (w, h))
        im_rgb = im_rgb.resize((w, h), Image.BICUBIC)
    im_rgb.save(jpeg_path, 'JPEG', quality=quality)


def main(args: argparse.Namespace) -> None:
    for f in args.file:
        convert(f, args.prefix, args.quality, args.shrink_ratio, args.dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='+', type=argparse.FileType('rb'))
    parser.add_argument('-p', '--prefix')
    parser.add_argument('-q', '--quality', type=int, default=DEFAULT_QUALITY)
    parser.add_argument('-s', '--shrink-ratio', type=int, default=100)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('-l', '--loglevel', choices=('debug', 'info'), default='info')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )
    logger.setLevel(args.loglevel.upper())
    main(args)
