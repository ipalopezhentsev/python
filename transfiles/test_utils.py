from unittest.case import TestCase

from transfiles.utils import group_by, get_fname_wo_extension, get_extension


class TestGroupBy(TestCase):
    def test_group_by(self):
        items = ["a.NEF", "a.xmp", "b.NEF", "b.xmp"]
        proj = lambda fname: fname[:len(fname) - 4]
        res = group_by(items, proj)
        self.assertDictEqual(res, {"a": ["a.NEF", "a.xmp"], "b": ["b.NEF", "b.xmp"]})

    def test_empty_input(self):
        items = []
        proj = lambda x: x
        res = group_by(items, proj)
        self.assertDictEqual(res, {})


class TestGetFnameWoExtension(TestCase):
    def test_get_fname_wo_extension(self):
        f1 = "/Volumes/IlyaHDD/tmp/play/DSC_8670.NEF"
        f2 = "/Volumes/IlyaHDD/tmp/play/DSC_8670.xmp"
        f1_proj = get_fname_wo_extension(f1)
        f2_proj = get_fname_wo_extension(f2)
        self.assertEqual(f1_proj, f2_proj)
        self.assertEqual(f1_proj, "/Volumes/IlyaHDD/tmp/play/DSC_8670")

    def test_multiple_extensions(self):
        f = "/home/user/a.tar.gz"
        f_proj = get_fname_wo_extension(f)
        # okay, it's a bit artificial, but on the other hand it allows names with points...
        self.assertEqual(f_proj, "/home/user/a.tar")

    def test_no_extension(self):
        f = "abc"
        f_proj = get_fname_wo_extension(f)
        self.assertEqual(f, f_proj)


class TestGetExtension(TestCase):
    def test_simple(self):
        f = "abc.raw"
        ext = get_extension(f)
        self.assertEqual(ext, "raw")

    def test_no_extension(self):
        f = "abc"
        ext = get_extension(f)
        self.assertEqual(ext, "")
