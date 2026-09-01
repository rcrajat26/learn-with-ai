# Every Position Expires

You are given an integer array `marks` and an integer `w`.

You may open a position on one day and close it on a strictly later day, but the
position expires after `w` days: if you open on day `i` and close on day `j`,
then `1 <= j - i <= w` is required.

Return the maximum value of `marks[j] - marks[i]` over all legal pairs, or `0`
if no legal pair is profitable.

**Constraints**
- `2 <= marks.length <= 10^5`
- `0 <= marks[i] <= 10^4`
- `1 <= w <= marks.length`
- Target `O(n)` total time. A solution that is `O(n * w)` will not pass.
- Extra space may be `O(w)`.

**Examples**

```
Input: marks = [9, 1, 2, 8, 0, 7], w = 2
Output: 7
Explanation: Open at index 4 (0), close at index 5 (7). Gap 1, legal.
             Opening at index 1 (1) and closing at index 3 (8) would give 7 as
             well, and its gap of 2 is also legal.
```

```
Input: marks = [1, 9, 2, 3], w = 1
Output: 8
Explanation: Only adjacent pairs are legal. The best is 9 - 1 = 8.
```

```
Input: marks = [5, 4, 3, 2, 1], w = 4
Output: 0
Explanation: Nothing is ever profitable.
```

---
_Hint: similar to LC121_BTBSaBTSS_
