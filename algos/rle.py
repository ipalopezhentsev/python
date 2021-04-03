def rle(s: str) -> str:
    cnt = 0
    prev_c = None
    out = ""
    for c in s:
        if c == prev_c or prev_c is None:
            cnt += 1
        else:
            out += prev_c
            out += str(cnt)
            cnt = 1
        prev_c = c
    if cnt >= 1:
        out += prev_c
        out += str(cnt)
    return out


def main():
    s = "AAAAAABBBCCCCCCCCD"
    s_rle = rle(s)
    print(s_rle)
    assert s_rle == "A6B3C8D1"
    assert rle("") == ""
    assert rle("A") == "A1"
    assert rle("AB") == "A1B1"


if __name__ == "__main__":
    main()
