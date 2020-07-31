import unittest
import os
import tempfile
from transfiles.actions import MoveAction, CopyAction


class TestMoveAction(unittest.TestCase):
    def test_can_commit(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            try:
                self.assertTrue(os.path.exists(src))
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = MoveAction(src, trg)

                action.pre_commit()
                self.assertFalse(os.path.exists(src))
                self.assertTrue(os.path.exists(trg))
                bak_name = os.path.join(os.path.dirname(src), filename + ".bak")
                self.assertTrue(os.path.exists(bak_name))

                action.commit()
                self.assertTrue(os.path.exists(trg))
                self.assertFalse(os.path.exists(bak_name))
            finally:
                if os.path.exists(src):
                    os.remove(src)
                    self.fail("Didn't cleanup temp src file")

    def test_can_rollback(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            try:
                self.assertTrue(os.path.exists(src))
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = MoveAction(src, trg)

                action.pre_commit()
                self.assertFalse(os.path.exists(src))
                self.assertTrue(os.path.exists(trg))
                bak_name = os.path.join(os.path.dirname(src), filename + ".bak")
                self.assertTrue(os.path.exists(bak_name))

                action.rollback()
                self.assertFalse(os.path.exists(trg))
                self.assertFalse(os.path.exists(bak_name))
                self.assertTrue(os.path.exists(src))
            finally:
                os.remove(src)

    def test_can_create_intermediate_folders(self):
        with tempfile.TemporaryDirectory() as trg_dir_base:
            # add not existing intermediate dir to ensure it will be created
            trg_dir = os.path.join(trg_dir_base, "not_existing_dir")
            src_handle, src = tempfile.mkstemp()
            try:
                self.assertTrue(os.path.exists(src))
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = MoveAction(src, trg)

                action.pre_commit()
                self.assertFalse(os.path.exists(src))
                self.assertTrue(os.path.exists(trg))
                bak_name = os.path.join(os.path.dirname(src), filename + ".bak")
                self.assertTrue(os.path.exists(bak_name))

                action.rollback()
                self.assertFalse(os.path.exists(trg))
                self.assertFalse(os.path.exists(bak_name))
                self.assertTrue(os.path.exists(src))
            finally:
                os.remove(src)


class TestCopyAction(unittest.TestCase):
    def test_can_commit(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            try:
                self.assertTrue(os.path.exists(src))
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = CopyAction(src, trg)

                action.pre_commit()
                self.assertTrue(os.path.exists(src))
                self.assertTrue(os.path.exists(trg))

                action.commit()
                self.assertTrue(os.path.exists(src))
                self.assertTrue(os.path.exists(trg))
            finally:
                os.remove(src)

    def test_can_rollback(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            try:
                self.assertTrue(os.path.exists(src))
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = CopyAction(src, trg)

                action.pre_commit()
                self.assertTrue(os.path.exists(src))
                self.assertTrue(os.path.exists(trg))

                action.rollback()
                self.assertTrue(os.path.exists(src))
                self.assertFalse(os.path.exists(trg))
            finally:
                os.remove(src)


if __name__ == '__main__':
    unittest.main()
