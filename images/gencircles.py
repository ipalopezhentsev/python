#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageColor

WIDTH = 2


def gen_circles(size, n, step):
    (w, h) = size
    im = Image.new('RGB', (w, h), ImageColor.getrgb("white"))
    center = (w / 2, h / 2)
    cur_radius = step
    draw = ImageDraw.Draw(im)
    draw.line([(0, 0), (w - 1, h - 1)], fill=ImageColor.getrgb("black"), width=2)
    draw.line([(0, h - 1), (w - 1, 0)], fill=ImageColor.getrgb("black"), width=2)
    colors = [ImageColor.getrgb("red"), ImageColor.getrgb("green"), ImageColor.getrgb("blue")]
    for i in range(0, n):
        color = colors[i % len(colors)]
        draw_circle(draw, center, cur_radius, color)
        cur_radius += step
    return im


def draw_circle(draw, center, radius, color):
    (c_x, c_y) = center
    draw.ellipse([(c_x - radius, c_y - radius), (c_x + radius, c_y + radius)],
                 outline=color, width=WIDTH)


def main():
    h = 1000
    w = int(h * 1.5)
    n = 60
    step = 30
    filename = 'circles.png'

    im = gen_circles((w, h), n, step)
    im.save(filename)
    im.show()
    im.close()


if __name__ == '__main__':
    main()
