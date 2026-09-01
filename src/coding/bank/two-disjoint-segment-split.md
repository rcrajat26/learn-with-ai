# Two Non-Overlapping Rounds

You are given an integer array `levels`, where `levels[i]` is a measured level
at time `i`.

You may pick **at most two** disjoint pairs of times. Each pair is
`(i, j)` with `i < j` and scores `levels[j] - levels[i]`. The two pairs must not
overlap: if the first pair is `(i1, j1)` and the second is `(i2, j2)`, then
`j1 < i2`. Sharing an endpoint is not allowed.

Return the maximum total score. Using one pair, or none at all, is permitted, so
the answer is never negative.

**Constraints**
- `1 <= levels.length <= 10^5`
- `0 <= levels[i] <= 10^4`
- Target `O(n)` time. An `O(n^2)` split-point scan will not pass.

**Examples**

```
Input: levels = [3, 3, 5, 0, 0, 3, 1, 4]
Output: 6
Explanation: Pair (0, 2) scores 2, then pair (3, 7) scores 4. Total 6.
```

```
Input: levels = [1, 2, 3, 4, 5]
Output: 4
Explanation: Splitting the run into two pairs cannot beat taking the whole rise
             once.
```

```
Input: levels = [7, 6, 4, 3, 1]
Output: 0
```

---
_Hint: similar to LC121_BTBSaBTSS_
