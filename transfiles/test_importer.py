import datetime
import os.path
from unittest import TestCase

from transfiles.actions import MoveAction
from transfiles.importer import parse_exif_date, ImportRawsActionsGenerator


class TestParseDate(TestCase):
    def test_parse_good_exif_date(self):
        str_dt = b"2020:03:22 15:35:59"
        dt = parse_exif_date(str_dt)
        self.assertEqual(dt.year, 2020)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 22)
        self.assertEqual(dt.hour, 15)
        self.assertEqual(dt.minute, 35)
        self.assertEqual(dt.second, 59)


class TestImportRawsActionsGenerator(TestCase):
    def test_generate(self):
        trg_dir = "/target"
        find_date_taken = lambda fname: datetime.datetime(2020, 3, 2)
        subj = ImportRawsActionsGenerator(trg_dir, find_date_taken, delete_src=True)
        root = "/src"
        files = ["a.NEF", "a.xmp", "b.NEF", "b.xmp", "c.NEF", "q.txt"]
        actions = subj.generate(root, [], files)
        # q.txt will be skipped as not raw
        self.assertEqual(len(actions), 5)

        act1 = actions[0]
        self.assertTrue(isinstance(act1, MoveAction))
        self.assertEqual(act1.file, os.path.join(root, "a.NEF"))
        self.assertEqual(act1.trg_file, os.path.join(trg_dir, "2020", "2020-03-02", "a.NEF"))

        act1 = actions[1]
        self.assertTrue(isinstance(act1, MoveAction))
        self.assertEqual(act1.file, os.path.join(root, "a.xmp"))
        self.assertEqual(act1.trg_file, os.path.join(trg_dir, "2020", "2020-03-02", "a.xmp"))

        act1 = actions[2]
        self.assertTrue(isinstance(act1, MoveAction))
        self.assertEqual(act1.file, os.path.join(root, "b.NEF"))
        self.assertEqual(act1.trg_file, os.path.join(trg_dir, "2020", "2020-03-02", "b.NEF"))

        act1 = actions[3]
        self.assertTrue(isinstance(act1, MoveAction))
        self.assertEqual(act1.file, os.path.join(root, "b.xmp"))
        self.assertEqual(act1.trg_file, os.path.join(trg_dir, "2020", "2020-03-02", "b.xmp"))

        act1 = actions[4]
        self.assertTrue(isinstance(act1, MoveAction))
        self.assertEqual(act1.file, os.path.join(root, "c.NEF"))
        self.assertEqual(act1.trg_file, os.path.join(trg_dir, "2020", "2020-03-02", "c.NEF"))
