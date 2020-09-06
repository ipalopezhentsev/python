import os
import tempfile

import pytest

from transfiles.actions import MoveAction, CopyAction


# TODO: rewrite temp dirs on pytest fixtures

class TestMoveAction:
    def test_can_commit(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            # if we don't close it now, Windows will fail to remove/rename it,
            # because it will be locked by our process. closing it doesn't remove
            # it so we still have to remove it later.
            os.close(src_handle)
            try:
                assert os.path.exists(src)
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = MoveAction(src, trg)

                action.pre_commit()
                assert not os.path.exists(src)
                assert os.path.exists(trg)
                bak_name = os.path.join(os.path.dirname(src), filename + ".bak")
                assert os.path.exists(bak_name)

                action.commit()
                assert os.path.exists(trg)
                assert not os.path.exists(bak_name)
            finally:
                if os.path.exists(src):
                    os.remove(src)
                    pytest.fail("Didn't cleanup temp src file")

    def test_can_rollback(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            os.close(src_handle)
            try:
                assert os.path.exists(src)
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = MoveAction(src, trg)

                action.pre_commit()
                assert not os.path.exists(src)
                assert os.path.exists(trg)
                bak_name = os.path.join(os.path.dirname(src), filename + ".bak")
                assert os.path.exists(bak_name)

                action.rollback()
                assert not os.path.exists(trg)
                assert not os.path.exists(bak_name)
                assert os.path.exists(src)
            finally:
                os.remove(src)

    def test_can_create_intermediate_folders(self):
        with tempfile.TemporaryDirectory() as trg_dir_base:
            # add not existing intermediate dir to ensure it will be created
            trg_dir = os.path.join(trg_dir_base, "not_existing_dir")
            src_handle, src = tempfile.mkstemp()
            os.close(src_handle)
            try:
                assert os.path.exists(src)
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = MoveAction(src, trg)

                action.pre_commit()
                assert not os.path.exists(src)
                assert os.path.exists(trg)
                bak_name = os.path.join(os.path.dirname(src), filename + ".bak")
                assert os.path.exists(bak_name)

                action.rollback()
                assert not os.path.exists(trg)
                assert not os.path.exists(bak_name)
                assert os.path.exists(src)
            finally:
                os.remove(src)


class TestCopyAction:
    def test_can_commit(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            os.close(src_handle)
            try:
                assert os.path.exists(src)
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = CopyAction(src, trg)

                action.pre_commit()
                assert os.path.exists(src)
                assert os.path.exists(trg)

                action.commit()
                assert os.path.exists(src)
                assert os.path.exists(trg)
            finally:
                os.remove(src)

    def test_can_rollback(self):
        with tempfile.TemporaryDirectory() as trg_dir:
            src_handle, src = tempfile.mkstemp()
            os.close(src_handle)
            try:
                assert os.path.exists(src)
                filename = os.path.basename(src)
                print("trg_dir=", trg_dir)
                trg = os.path.join(trg_dir, filename)
                print("trg=", trg)
                action = CopyAction(src, trg)

                action.pre_commit()
                assert os.path.exists(src)
                assert os.path.exists(trg)

                action.rollback()
                assert os.path.exists(src)
                assert not os.path.exists(trg)
            finally:
                os.remove(src)
