import os
import shutil
import logging
from transfiles.transactions import Action
import transfiles.logsetup

logger = logging.getLogger(__name__)


class FileAction(Action):
    def __init__(self, file: str):
        self.file = file


class MoveAction(FileAction):
    def __init__(self, src_file: str, trg_file: str):
        super().__init__(src_file)
        self.trg_file = trg_file
        self.__done_renaming = None

    def __repr__(self) -> str:
        return f"MoveAction[from: {self.file}; to: {self.trg_file}]"

    def __eq__(self, other: object) -> bool:
        if id(self) == id(os):
            return True
        if not isinstance(other, MoveAction):
            return False
        else:
            return self.file == other.file and self.trg_file == other.trg_file

    def pre_commit(self):
        tmp_name = self.file + ".bak"
        if os.path.exists(tmp_name):
            raise FileExistsError(f"Cannot rename as {tmp_name} already exists")
        logger.info(f"Renaming {self.file} to {tmp_name}")
        os.rename(self.file, tmp_name)
        self.__done_renaming = (self.file, tmp_name)
        logger.info("Done renaming")

        logger.info(f"Copying {tmp_name} to {self.trg_file}")
        if os.path.exists(self.trg_file):
            # otherwise shutil.copyfile() will just silently replace it
            raise FileExistsError("File {0} already exists".format(self.trg_file))
        os.makedirs(os.path.dirname(self.trg_file), exist_ok=True)
        shutil.copyfile(tmp_name, self.trg_file)
        logger.info("Done copying")

    def commit(self):
        src_file, tmp_renamed_file = self.__done_renaming
        logger.info(f"Removing {tmp_renamed_file}")
        os.remove(tmp_renamed_file)
        logger.info("Done removing")

    def rollback(self):
        if self.__done_renaming:
            src_file, tmp_renamed_file = self.__done_renaming
            logger.info(f"Renaming {tmp_renamed_file} to {src_file}")
            os.rename(tmp_renamed_file, src_file)
            try:
                logger.info(f"Removing {self.trg_file}")
                os.remove(self.trg_file)
            except Exception as e:
                logger.error(f"Error while removing {self.trg_file}", exc_info=e)


class CopyAction(FileAction):
    def __init__(self, src_file, trg_file):
        super().__init__(src_file)
        self.trg_file = trg_file

    def __repr__(self) -> str:
        return f"CopyAction[from: {self.file}; to: {self.trg_file}]"

    def pre_commit(self):
        if os.path.exists(self.trg_file):
            raise FileExistsError(f"Cannot copy as {self.trg_file} already exists")
        logger.info(f"Copying {self.file} to {self.trg_file}")
        os.makedirs(os.path.dirname(self.trg_file), exist_ok=True)
        shutil.copyfile(self.file, self.trg_file)
        logger.info("Done copying")

    def commit(self):
        pass

    def rollback(self):
        try:
            logger.info(f"Removing {self.trg_file}")
            os.remove(self.trg_file)
        except Exception as e:
            logger.error(f"Error while removing {self.trg_file}", exc_info=e)
