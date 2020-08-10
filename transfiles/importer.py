import datetime
import os
from typing import Sequence
import argparse
import logging

import piexif

from transfiles import utils
from transfiles.actions import MoveAction, CopyAction
from transfiles.transactions import process_actions_atomically, Action
from transfiles.utils import get_fname_wo_extension
import transfiles.logsetup

raw_extensions = {"nef", "dng"}
logger = logging.getLogger(__name__)


class FolderActionsGenerator:
    def generate(self, root, dirs, files) -> Sequence[Action]:
        raise NotImplementedError


def err_processor(exception: OSError):
    logger.error("Skipping traversing file {0} due to error".format(exception.filename), exc_info=exception)


def process_tree(path_to_process, *,
                 generator: FolderActionsGenerator,
                 process_actions=process_actions_atomically):
    if not os.path.isdir(path_to_process):
        raise NotADirectoryError(f"path {path_to_process} is not a directory")
    actions = []
    for root, dirs, files in os.walk(path_to_process, onerror=err_processor):
        print(f'Collecting actions for directory {root}:')
        actions_for_dir = generator.generate(root, dirs, files)
        actions.extend(actions_for_dir)
    if len(actions) == 0:
        print("No actions to perform")
        return
    print("Going to process actions:\n", "\n".join(map(repr, actions)), sep="")
    answer = input("Proceed (Y/N)?")
    if answer.lower() == "y":
        print("Processing:")
        process_actions(actions)
        print("Done")


def parse_exif_date(binary_str_datetime) -> datetime.datetime:
    """parses exif date time in binary ascii string in format b'2020:03:22 15:35:59'"""
    # str_dt = binary_str_datetime.decode("utf-8")
    str_dt = str(binary_str_datetime, encoding="utf-8")
    return datetime.datetime.strptime(str_dt, "%Y:%m:%d %H:%M:%S")


def find_date_taken_from_exif(abs_raw_file: str) -> datetime.datetime:
    exif_dict = piexif.load(abs_raw_file)
    str_date_taken = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal]
    return parse_exif_date(str_date_taken)


class ImportRawsActionsGenerator(FolderActionsGenerator):
    def __init__(self, target_dir, find_date_taken=find_date_taken_from_exif,
                 delete_src=False):
        self.target_dir = target_dir
        self.find_date_taken = find_date_taken
        self.delete_src = delete_src

    def generate(self, root, dirs, files) -> Sequence[MoveAction]:
        actions = []

        # let's group by filename as there could be several files with common name,
        # e.g raw file itself and its Lightroom sidecar: DSC_8670.NEF and DSC_8670.xmp
        photos_grouped_by_fname = utils.group_by(files, get_fname_wo_extension)
        # print(photos_grouped_by_fname)
        for base_fname, files_with_fname in photos_grouped_by_fname.items():
            print(f"Processing {base_fname}: {files_with_fname}")
            is_raw_file = lambda fname: utils.get_extension(fname).lower() in raw_extensions
            raw_files = list(filter(is_raw_file, files_with_fname))
            num_raw_files_found = len(raw_files)
            if num_raw_files_found == 0:
                print("Group doesn't have raw file, skipping it:", files_with_fname)
                continue
            elif num_raw_files_found > 1:
                print("Group has more than 1 raw file, taking date from first of them: ", raw_files[0])
            raw_file = raw_files[0]

            try:
                date_taken = self.find_date_taken(os.path.join(root, raw_file))
            except Exception as e:
                print("Cannot find date taken from EXIF of file {0} due to error {1}. Skipping it"
                      .format(raw_file, repr(e)))
                continue

            trg_path = os.path.join(self.target_dir, str(date_taken.year),
                                    "{0.year}-{0.month:02}-{0.day:02}".format(date_taken))
            for file in files_with_fname:
                src = os.path.join(root, file)
                trg = os.path.join(trg_path, file)
                action = MoveAction(src, trg) if self.delete_src else CopyAction(src, trg)
                actions.append(action)

        return actions


def main():
    parser = argparse.ArgumentParser(
        description="Takes photos (jpg, tiff, tiff-based raws (NEF, DNG, ...) from source dir "
                    "and moves them to target dir into folders corresponding to date each "
                    "picture was taken (obtained from EXIF data). If something goes wrong, "
                    "rolls back all changes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("src_dir", help="source directory (with or without trailing slash)")
    parser.add_argument("trg_dir", help="target directory (with or without trailing slash)")
    parser.add_argument("-d", "--delete-src", action="store_true", help="remove source file after successful copying")
    args = parser.parse_args()

    dir_actions_generator = ImportRawsActionsGenerator(args.trg_dir, delete_src=args.delete_src)
    process_tree(args.src_dir, generator=dir_actions_generator)


if __name__ == "__main__":
    main()
