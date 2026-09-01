# A Minimum Holding Period

You are given an integer array `rates` and an integer `k`. `rates[i]` is the
exchange rate on day `i`.

You may buy on one day and sell on a later day, but the position must be held
for at least `k` days: if you buy on day `i` and sell on day `j`, then
`j - i >= k` is required.

Return the maximum profit `rates[j] - rates[i]` achievable under that rule, or
`0` if no legal pair produces a positive profit.

**Constraints**
- `1 <= rates.length <= 10^5`
- `0 <= rates[i] <= 10^4`
- `1 <= k <= 10^5` — note `k` may exceed the array length, in which case no
  legal pair exists.
- Target `O(n)` time and `O(1)` extra space.

**Examples**

```
Input: rates = [7, 1, 5, 3, 6, 4], k = 3
Output: 5
Explanation: Buy at index 1 (rate 1), sell at index 4 (rate 6): the gap is 3,
             which is allowed. Profit 5.
```

```
Input: rates = [7, 1, 5, 3, 6, 4], k = 4
Output: 3
Explanation: Legal pairs must span at least 4 days. Buy index 1 (rate 1),
             sell index 5 (rate 4): profit 3. Buying at index 1 and selling at
             index 4 is now illegal.
```

```
Input: rates = [3, 8], k = 5
Output: 0
Explanation: No pair is far enough apart.
```

---
_Hint: similar to LC121_BTBSaBTSS_
