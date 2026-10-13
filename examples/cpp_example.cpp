// C++ example: Selection sort — O(n^2) time, O(1) space
#include <iostream>
#include <vector>

/**
 * Sort a vector using selection sort.
 *
 * Time Complexity: O(n^2) — nested loops, each traversing O(n) elements.
 * Space Complexity: O(1) — in-place sorting, no additional allocation.
 */
void selectionSort(std::vector<int>& arr) {
    int n = arr.size();
    for (int i = 0; i < n - 1; i++) {
        int minIdx = i;
        for (int j = i + 1; j < n; j++) {
            if (arr[j] < arr[minIdx]) {
                minIdx = j;
            }
        }
        if (minIdx != i) {
            std::swap(arr[i], arr[minIdx]);
        }
    }
}

int main() {
    std::vector<int> data = {64, 25, 12, 22, 11};
    selectionSort(data);
    for (int x : data) std::cout << x << " ";
    std::cout << std::endl;
    return 0;
}
