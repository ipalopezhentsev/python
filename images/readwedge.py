#!/usr/local/bin/python3
import sys
from PIL import Image, ImageDraw, ImageColor


def main():
    h = 500
    w = int(h * 1.5)
    # filename = 'wedge.png'
    filename = 'wedge_after_ps.png'

    im = Image.open(filename)
    w1 = w / 5
    p1 = im.getpixel((1, 0))
    p2 = im.getpixel((w1 + 1, 0))
    p3 = im.getpixel((2 * w1 + 1, 0))
    p4 = im.getpixel((3 * w1 + 1, 0))
    p5 = im.getpixel((4 * w1, 0))
    print(p1, p2, p3, p4, p5)
    im.close()


if __name__ == '__main__':
    main()
