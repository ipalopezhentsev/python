import unittest


class TestTransactions(unittest.TestCase):
    def test_oop_basic(self):
        class A:
            def __init__(self):
                self.pub = 1
                self.__priv = 2

        ai = A()
        self.assertTrue("pub" in dir(ai))
        self.assertFalse("__priv" in dir(ai))
        self.assertTrue("_A__priv" in dir(ai))

    def test_oop_inheritance(self):
        class Base:
            def __init__(self):
                self.q = 1
                self.__w = 2

            def f(self): return 1

        class Derived(Base):
            def __init__(self):
                super().__init__()

            def f(self): return 2

        d = Derived()
        self.assertTrue("q" in dir(d))
        self.assertFalse("__w" in dir(d))
        self.assertEqual(d.f(), 2)

    def test_oop_static(self):
        q = 1

        class A:
            @staticmethod
            def static_fun():
                nonlocal q
                q = 2
                A.w = 3

        self.assertEqual(q, 1)
        A.static_fun()
        self.assertEqual(q, 2)
        a = A()
        self.assertEqual(a.__class__.w, 3)

    def test_oop_classmethod(self):
        class A:
            @staticmethod
            def f(): return 1

            @classmethod
            def static_fun(cls): return cls.f()

        self.assertEqual(A.static_fun(), 1)

    def test_property(self):
        class A:
            def __init__(self):
                self.__a = 0

            @property
            def computed_prop(self):
                return 1

            @property
            def field_backed_prop(self):
                return self.__a

            @field_backed_prop.setter
            def field_backed_prop(self, val):
                self.__a = val

        a = A()
        self.assertEqual(a.computed_prop, 1)
        self.assertEqual(a.field_backed_prop, 0)
        a.field_backed_prop = 2
        self.assertEqual(a.field_backed_prop, 2)
