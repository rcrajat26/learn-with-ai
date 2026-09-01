# The Distinct Union of Two Sorted Arrays, Built In Place

You are given two integer arrays `first` and `second`, both sorted in
non-decreasing order and both possibly containing duplicates within themselves,
along with two integers `m` and `n`.

`first` has length exactly `m + n`. Its first `m` positions hold its real
elements; the final `n` positions are padding. `second` has length exactly `n`
and every position is meaningful.

Rewrite `first` so that its leading positions hold, in ascending order, each
value that appears in **either** input array, with every value appearing exactly
once — the sorted set union of the two inputs.

Let `k` be the number of distinct values across both arrays. Your function must:

- place those `k` values, in ascending order, in the first `k` positions of
  `first`, and
- return `k`.

Anything left in `first` beyond index `k - 1` will not be inspected.

The work must be done **in place** in O(1) extra space, in O(m + n) time. You may
not allocate any array, list, or set of size dependent on the input, and you may
not sort. Note in particular that you may not first merge into a scratch buffer
and then deduplicate.

**Constraints**
- `first.length == m + n`
- `second.length == n`
- `0 <= m, n <= 10^4`
- `1 <= m + n <= 2 * 10^4`
- `-10^9 <= first[i], second[j] <= 10^9`
- Both arrays are sorted in non-decreasing order.
- Duplicates may occur within `first`, within `second`, and across the two.
- Either `m` or `n` may be 0.

**Examples**

```
Input:  first = [1,2,2,0,0,0], m = 3, second = [2,3,3], n = 3
Output: 3, first = [1,2,3,_,_,_]
Explanation: The arrays being combined are [1,2,2] and [2,3,3]. The distinct
union is {1,2,3}. Return k = 3.
```

```
Input:  first = [1,1,1,0,0], m = 3, second = [1,1], n = 2
Output: 1, first = [1,_,_,_,_]
Explanation: Every element in both arrays is 1, so the union has one member.
```

```
Input:  first = [5,6,7,0,0,0], m = 3, second = [1,2,3], n = 3
Output: 6, first = [1,2,3,5,6,7]
Explanation: Disjoint, and every element of second precedes every element of
first. No compaction is possible — the output fills the array exactly.
```

```
Input:  first = [0,0], m = 0, second = [4,4], n = 2
Output: 1, first = [4,_]
Explanation: first has no meaningful elements. The two padding positions are not
data.
```

**Follow-up**

Two pressures act in opposite directions here. Deduplication shortens the output,
which invites writing forward from index 0. The merge can require every element
of `second` to precede every element of `first`, which forbids it. Resolve the
conflict: state a single cursor-ordering inequality that holds for all inputs,
prove it, and identify the input family where it is tight.

---
_Hint: similar to LC26_RDfSA_