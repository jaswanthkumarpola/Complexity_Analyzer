"""
Binary search — O(log n) time, O(1) auxiliary space.
An iterative implementation on a sorted array.
"""


def binary_search(arr: list, target: int) -> int:
    """
    Search for target in a sorted array.

    Time Complexity: O(log n) — the search space halves on each iteration.
    Space Complexity: O(1) — no additional memory allocated beyond variables.

    Assumptions:
    - arr is sorted in non-decreasing order.
    - Elements support the < and == operators.
    """
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = left + (right - left) // 2   # Safe midpoint: avoids overflow
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1   # Target not found


if __name__ == "__main__":
    data = list(range(0, 100, 2))   # [0, 2, 4, ..., 98]
    print(binary_search(data, 42))  # 21
    print(binary_search(data, 7))   # -1
