# Leetcode problem 347. Top K Frequent Elements
# https://leetcode.com/problems/top-k-frequent-elements/description/
# (find k most frequent elements in integer array nums (max size 100k), elements of
# this array are in -10k..10k.
# Solution should be better than O(n log n).
from typing import List


def top_k_frequent(nums: List[int], k: int) -> List[int]:
    # since the array elems fit small int, let's use two passes of kind of 'counting sort' (takes O(n)):
    #   first pass collects frequencies (idx - number in nums, value - number of occurrences).
    #   second 'pseudo counting sort' pass collects arrays of most frequent elems (idx - number of occurrences,
    #   value - array of original elems from nums that have such number of occurrences).
    # the third pass then collects first top k original elems in terms of frequency.

    abs_min_num = 10000
    max_num = 10000
    counts = [0] * (abs_min_num + max_num + 1)
    min_idx = 10000000
    max_idx = -1000000
    max_freq = -1
    for i in range(0, len(nums)):
        idx = nums[i] + abs_min_num
        new_freq = counts[idx] + 1
        counts[idx] = new_freq
        if idx > max_idx:
            max_idx = idx
        if idx < min_idx:
            min_idx = idx
        if new_freq > max_freq:
            max_freq = new_freq

    counts2 = [None] * (max_freq + 1)
    min_idx2 = 10000000
    max_idx2 = -1000000
    for j in range(min_idx, max_idx + 1):
        freq = counts[j]
        if freq == 0:
            continue
        existing_arr = counts2[freq]
        if existing_arr is None:
            existing_arr = [j - abs_min_num]
            counts2[freq] = existing_arr
        else:
            existing_arr.append(j - abs_min_num)
        if freq > max_idx2:
            max_idx2 = freq
        if freq < min_idx2:
            min_idx2 = freq

    res = []
    for l in range(max_idx2, min_idx2 - 1, -1):
        elems = counts2[l]
        if elems is None:
            continue
        for m in range(0, len(elems)):
            res.append(elems[m])
            k = k - 1
            if k == 0:
                break
        if k == 0:
            break

    return res


def main():
    res = top_k_frequent([-10000, 0, 0, 10000, 10000], 2)
    assert set(res) == {10000, 0}


if __name__ == '__main__':
    main()
