import os
import shutil
from transfiles.transactions import Action


class FileAction(Action):
    def __init__(self, file):
        self.file = file


class MoveAction(FileAction):
    def __init__(self, src_file, trg_file):
        FileAction.__init__(self, src_file)
        self.trg_file = trg_file
        self.done_renaming = None

    def __repr__(self) -> str:
        return f"MoveAction[from: {self.file}; to: {self.trg_file}]"

    def pre_commit(self):
        tmp_name = self.file + ".bak"
        if os.path.exists(tmp_name):
            raise RuntimeError(f"Cannot rename as {tmp_name} already exists")
        print(f"Renaming {self.file} to {tmp_name}")
        os.rename(self.file, tmp_name)
        self.done_renaming = (self.file, tmp_name)
        print("Done renaming")

        # should_fail = input("Simulate exception (Y/N)?")
        # if should_fail.lower() == "y":
        #     raise RuntimeError("Asked to fail")

        print(f"Copying {tmp_name} to {self.trg_file}")
        shutil.copyfile(tmp_name, self.trg_file)
        print("Done copying")

    def commit(self):
        src_file, tmp_renamed_file = self.done_renaming
        print(f"Removing {tmp_renamed_file}")
        os.remove(tmp_renamed_file)
        print("Done removing")

    def rollback(self):
        if self.done_renaming:
            src_file, tmp_renamed_file = self.done_renaming
            print(f"Renaming {tmp_renamed_file} to {src_file}")
            os.rename(tmp_renamed_file, src_file)
            try:
                print(f"Removing {self.trg_file}")
                os.remove(self.trg_file)
            except:
                pass
