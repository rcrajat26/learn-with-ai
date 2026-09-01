# Absorb One Sorted Array Into Another's Spare Capacity

You are given two integer arrays `first` and `second`, both sorted in
non-decreasing order, along with two integers `m` and `n` giving the number of
meaningful elements in `first` and `second` respectively.

`first` has length exactly `m + n`. Its first `m` positions hold its real
elements; the final `n` positions are padding and should be treated as empty.
`second` has length exactly `n` and all of its positions are meaningful.

Merge `second` into `first` so that, when your function returns, `first` holds
all `m + n` elements in non-decreasing order. Your function returns nothing —
the result is read directly out of `first`.

The merge must be done **in place**, using O(1) extra space. You may not
allocate an array of size `m + n` (or `m`, or `n`) and copy the result back.

**Constraints**
- `first.length == m + n`
- `second.length == n`
- `0 <= m, n <= 200`
- `1 <= m + n <= 200`
- `-10^9 <= first[i], second[j] <= 10^9`
- Both arrays are sorted in non-decreasing order.
- Either `m` or `n` may be 0.

**Examples**

```
Input:  first = [1,2,3,0,0,0], m = 3, second = [2,5,6], n = 3
Output: first = [1,2,2,3,5,6]
Explanation: The arrays being merged are [1,2,3] and [2,5,6]. The three trailing
zeros in first were padding, not data.
```

```
Input:  first = [1], m = 1, second = [], n = 0
Output: first = [1]
```

```
Input:  first = [0], m = 0, second = [1], n = 1
Output: first = [1]
Explanation: first has no meaningful elements; its single position is padding.
```

```
Input:  first = [4,5,6,0,0,0], m = 3, second = [1,2,3], n = 3
Output: first = [1,2,3,4,5,6]
```

**Follow-up**

The last example is the adversarial one: every element of `second` belongs before
every element of `first`. Explain precisely why a left-to-right merge that writes
into `first[0]`, `first[1]`, … fails on it, and state the property your solution
maintains that makes the failure impossible.

---
_Hint: similar to LC26_RDfSA_