def main():
    a = []
    a.append(1)
    a.extend([2, 3])
    a.insert(0, "1")
    print(a)
    a.sort(key=lambda a: a, reverse=True)
    b = a.copy()
    b.clear()
    print(a)
    print(b)


if __name__ == '__main__':
    main()
