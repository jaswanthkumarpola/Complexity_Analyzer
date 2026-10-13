// Java example: Linear search — O(n) time, O(1) space

public class LinearSearch {

    /**
     * Search for a target value in an unsorted array.
     *
     * Time Complexity: O(n) — must inspect up to n elements.
     * Space Complexity: O(1) — no additional storage proportional to input.
     *
     * Best case: O(1) — target is the first element.
     * Worst case: O(n) — target is last or not present.
     */
    public static int linearSearch(int[] arr, int target) {
        for (int i = 0; i < arr.length; i++) {
            if (arr[i] == target) {
                return i;   // Found at index i
            }
        }
        return -1;  // Not found
    }

    public static void main(String[] args) {
        int[] data = {4, 2, 7, 1, 9, 3, 8};
        System.out.println(linearSearch(data, 9));  // 4
        System.out.println(linearSearch(data, 5));  // -1
    }
}
