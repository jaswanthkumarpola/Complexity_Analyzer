"""
Merge sort — O(n log n) time, O(n) auxiliary space.
Classic divide-and-conquer sorting algorithm.
"""
from typing import List


def merge_sort(arr: List[int]) -> List[int]:
    """
    Sort an array using merge sort.

    Time Complexity: O(n log n)
      - The array is divided log n times.
      - Each level of division does O(n) work in the merge step.
    Space Complexity: O(n) auxiliary
      - New arrays are allocated at each merge step.
      - Recursion stack depth is O(log n).
    """
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)


def _merge(left: List[int], right: List[int]) -> List[int]:
    """Merge two sorted arrays. Time: O(n), Space: O(n)."""
    result: List[int] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


if __name__ == "__main__":
    data = [38, 27, 43, 3, 9, 82, 10, 1]
    print("Input: ", data)
    print("Sorted:", merge_sort(data))
