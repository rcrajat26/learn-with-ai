# The Largest Drop From a Peak

You are given an integer array `readings`, where `readings[i]` is a sensor
reading taken at time `i`. Readings arrive in chronological order.

A *drop* is the amount a reading falls from some earlier peak: for indices
`i < j`, the drop is `readings[i] - readings[j]`.

Return the largest drop that occurs anywhere in the array. If no reading is ever
lower than an earlier one, return `0`.

**Constraints**
- `1 <= readings.length <= 10^5`
- `0 <= readings[i] <= 10^4`
- You must use `O(1)` extra space.
- The two indices must satisfy `i < j` strictly; a reading cannot drop from
  itself.

**Examples**

```
Input: readings = [8, 3, 9, 2, 7]
Output: 7
Explanation: The peak 9 at index 2 falls to 2 at index 3, a drop of 7.
             The pair (8, 2) gives only 6.
```

```
Input: readings = [1, 2, 3, 4]
Output: 0
Explanation: Readings never fall. No drop exists, so return 0.
```

```
Input: readings = [5]
Output: 0
```

---
_Hint: similar to LC121_BTBSaBTSS_
