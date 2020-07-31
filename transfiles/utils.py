import collections

from typing import Iterable, Callable, TypeVar, Mapping

T = TypeVar("T")
P = TypeVar("P")


def group_by(iterable: Iterable[T], projection: Callable[[T], P]) -> Mapping[P, Iterable[T]]:
    """Groups iterable by values of projection function applied to its elements"""
    res = collections.defaultdict(list)
    for elem in iterable:
        proj_key = projection(elem)
        res[proj_key].append(elem)
    return res


def get_fname_wo_extension(fname: str) -> str:
    last_dot_idx = fname.rfind(".")
    return fname if last_dot_idx == -1 else fname[:last_dot_idx]


def get_extension(fname: str) -> str:
    last_dot_idx = fname.rfind(".")
    return "" if last_dot_idx == -1 else fname[last_dot_idx + 1:]
