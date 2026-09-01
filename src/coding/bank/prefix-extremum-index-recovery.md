# Report the Winning Pair, Not Just the Score

You are given an integer array `values`. Among all index pairs `(i, j)` with
`i < j`, consider the quantity `values[j] - values[i]`.

Return an `int[]` of length 2 containing the indices `{i, j}` that maximise that
quantity. If the maximum achievable quantity is less than or equal to `0`,
return an empty array `{}`.

If several pairs tie for the maximum, return the one with the smallest `j`; if
there is still a tie, return the one with the smallest `i`.

**Constraints**
- `1 <= values.length <= 10^5`
- `0 <= values[i] <= 10^4`
- Single pass over the array. `O(1)` extra space beyond the returned array.

**Examples**

```
Input: values = [7, 1, 5, 3, 6, 4]
Output: [1, 4]
Explanation: values[4] - values[1] = 6 - 1 = 5, the maximum. No pair beats it.
```

```
Input: values = [2, 4, 1, 3]
Output: [0, 1]
Explanation: Both (0,1) and (2,3) give 2. The tie-break prefers the smaller j,
             which is 1.
```

```
Input: values = [9, 9, 9]
Output: []
Explanation: The best quantity is 0, which is not greater than 0.
```

---
_Hint: similar to LC121_BTBSaBTSS_
