import datetime
import os.path

from transfiles.actions import MoveAction
from transfiles.importer import parse_exif_date, ImportRawsActionsGenerator


class TestParseDate:
    def test_parse_good_exif_date(self):
        str_dt = b"2020:03:22 15:35:59"
        dt = parse_exif_date(str_dt)
        assert dt == datetime.datetime(2020, 3, 22, 15, 35, 59)


class TestImportRawsActionsGenerator:
    def test_generate(self):
        trg_dir = "/target"
        find_date_taken = lambda fname: datetime.datetime(2020, 3, 2)
        subj = ImportRawsActionsGenerator(trg_dir, find_date_taken, delete_src=True)
        root = "/src"
        files = ["a.NEF", "a.xmp", "b.NEF", "b.xmp", "c.NEF", "q.txt"]
        actions = subj.generate(root, [], files)
        # q.txt will be skipped as not raw
        assert actions == [
            MoveAction(os.path.join(root, "a.NEF"), os.path.join(trg_dir, "2020", "2020-03-02", "a.NEF")),
            MoveAction(os.path.join(root, "a.xmp"), os.path.join(trg_dir, "2020", "2020-03-02", "a.xmp")),
            MoveAction(os.path.join(root, "b.NEF"), os.path.join(trg_dir, "2020", "2020-03-02", "b.NEF")),
            MoveAction(os.path.join(root, "b.xmp"), os.path.join(trg_dir, "2020", "2020-03-02", "b.xmp")),
            MoveAction(os.path.join(root, "c.NEF"), os.path.join(trg_dir, "2020", "2020-03-02", "c.NEF"))
        ]
