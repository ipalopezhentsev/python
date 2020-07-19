import sys
import os
from typing import Collection
from transfiles.actions import MoveAction, FileAction
from transfiles.transactions import process_actions_atomically


# class ActionsProvider:
#     def generate_actions(self, files) -> Collection[FileAction]:
#         pass


# class ActionsExecutor:
#     def process(self, actions: Sequence[Collection]):
#         """Executes the actions - first it calls process() on each,
#         if anything fails for some action, it doesn't call process() on the remaining ones,
#         but executes rollback() on already processed ones.
#         Then, after it successfully called process() on all items, it starts calling
#         commit() on them. If anything fails, it doesn't commit further and instead"""
#         pass


def process_tree(path_to_process, *,
                 generate_actions,
                 process_actions=process_actions_atomically):
    if not os.path.isdir(path_to_process):
        raise RuntimeError("path is not a directory")
    actions = []
    for root, dirs, files in os.walk(path_to_process):
        print(f'Collecting actions for directory {root}:')
        actions.extend(generate_actions(root, files))
    print("Processing actions:")
    process_actions(actions)
    print("Done")


def generate_actions_for_import_dslr_raws(root, files) -> Collection[FileAction]:
    actions = []
    src = os.path.join(root, "DSC_8670.NEF")
    trg = "/Volumes/IlyaHDD/tmp/trg/DSC_8670.NEF"
    action = MoveAction(src, trg)
    actions.append(action)
    src = os.path.join(root, "DSC_8670.xmp")
    trg = "/Volumes/IlyaHDD/tmp/trg/DSC_8670.xmp"
    action = MoveAction(src, trg)
    actions.append(action)
    return actions


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {os.path.basename(sys.argv[0])} <directory to process>")
        sys.exit(1)
    else:
        process_tree(sys.argv[1],
                     generate_actions=generate_actions_for_import_dslr_raws)


if __name__ == "__main__":
    main()
