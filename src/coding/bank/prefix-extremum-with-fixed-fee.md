# One Trade, Flat Commission

You are given an integer array `quotes` and an integer `fee`.

You may perform at most one buy followed by one later sell. Buying on day `i`
and selling on day `j` (with `i < j`) nets `quotes[j] - quotes[i] - fee`; the
commission is charged once per completed trade. You may also decline to trade,
which nets `0`.

Return the maximum amount you can net.

**Constraints**
- `1 <= quotes.length <= 10^5`
- `0 <= quotes[i] <= 10^4`
- `0 <= fee <= 10^4`
- Target `O(n)` time and `O(1)` extra space.

**Examples**

```
Input: quotes = [7, 1, 5, 3, 6, 4], fee = 2
Output: 3
Explanation: Buy at 1, sell at 6, pay 2. Net 3.
```

```
Input: quotes = [4, 5, 6], fee = 10
Output: 0
Explanation: The best gross gain is 2, less than the commission, so decline.
```

```
Input: quotes = [1, 1, 1], fee = 0
Output: 0
```

---
_Hint: similar to LC121_BTBSaBTSS_
