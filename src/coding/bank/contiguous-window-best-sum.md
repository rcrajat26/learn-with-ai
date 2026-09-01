# The Best Consecutive Stretch

You are given an integer array `deltas`, which may contain negative numbers.

Return the largest sum obtainable from a **non-empty contiguous** block of
`deltas`. The block must be a run of adjacent entries; you may not skip
elements, and you may not reorder them.

**Constraints**
- `1 <= deltas.length <= 10^5`
- `-10^4 <= deltas[i] <= 10^4`
- Target `O(n)` time and `O(1)` extra space.
- The block must contain at least one element, so a negative answer is possible.

**Examples**

```
Input: deltas = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
Output: 6
Explanation: The block [4, -1, 2, 1] sums to 6.
```

```
Input: deltas = [-7, -3, -9]
Output: -3
Explanation: Every block is negative. The single element -3 is the least bad.
```

```
Input: deltas = [5, 4, -1, 7, 8]
Output: 23
Explanation: The whole array.
```

---
_Hint: similar to LC121_BTBSaBTSS_
