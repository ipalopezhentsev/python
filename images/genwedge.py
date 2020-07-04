#!/usr/local/bin/python3
import sys
from PIL import Image, ImageDraw, ImageColor

WIDTH = 2


def gen_wedge(size):
    (w, h) = size
    im = Image.new('RGB', (w, h), ImageColor.getrgb("white"))
    draw = ImageDraw.Draw(im)
    w1 = w/5
    draw.rectangle([(0, 0), (w, h - 1)], fill=ImageColor.getrgb("black"), width=1)
    draw.rectangle([(w1, 0), (2*w1, h - 1)], fill=(60,60,60), width=1)
    draw.rectangle([(2*w1, 0), (3*w1, h - 1)], fill=(120,120,120), width=1)
    draw.rectangle([(3*w1, 0), (4*w1, h - 1)], fill=(200,200,200), width=1)
    draw.rectangle([(4*w1, 0), (5*w1, h - 1)], fill=ImageColor.getrgb("white"), width=1)
    return im


def main():
    h = 500
    w = int(h * 1.5)
    filename = 'wedge.png'

    im = gen_wedge((w, h))
    im.save(filename)
    im.show()
    im.close()


if __name__ == '__main__':
    main()
