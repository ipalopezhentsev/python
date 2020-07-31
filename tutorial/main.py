import sys
print("__name__=", __name__)
print(sys.path)
import tutorial.package1.module1 as module1
import tutorial.package2.module2


def main():
    """this is a docstring"""
    a = []
    a.append(1)
    a.extend([2, 3])
    print(a)
    a.sort(key=lambda c: c, reverse=True)
    b = a.copy()
    b.clear()
    print(a)
    print(b)
    print(module1.q)
    print(tutorial.package2.module2.q)


if __name__ == '__main__':
    main()
