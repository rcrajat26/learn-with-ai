# Fuse Overlapping Ranges Without Allocating

You are given a two-dimensional array `ranges` where `ranges[i] = [start_i,
end_i]` describes a closed interval, and the array is already sorted in
non-decreasing order of `start_i`.

Fuse every set of overlapping or touching intervals into a single interval. Two
intervals overlap or touch if the start of the later one is less than or equal to
the end of the earlier one — so `[1,4]` and `[4,7]` fuse into `[1,7]`, and
`[1,4]` and `[5,7]` do not fuse.

The work must be done **in place** in O(1) extra space beyond the input. You may
not build a `List<int[]>` of results, nor allocate a new outer array. You may
mutate the existing `int[]` rows and reassign row references within `ranges`.

Let `k` be the number of intervals after fusing. Your function must:

- place the `k` fused intervals, in ascending order of start, in
  `ranges[0]` through `ranges[k-1]`, and
- return `k`.

Anything left in `ranges` beyond index `k - 1` will not be inspected.

**Constraints**
- `1 <= ranges.length <= 10^4`
- `ranges[i].length == 2`
- `0 <= start_i <= end_i <= 10^4`
- `ranges` is sorted in non-decreasing order of `start_i`.
- Intervals are closed: `[2,2]` is a valid interval containing exactly one point.
- Note that an interval may be entirely contained within an earlier one.

**Examples**

```
Input:  ranges = [[1,3],[2,6],[8,10],[15,18]]
Output: 3, ranges = [[1,6],[8,10],[15,18],_]
Explanation: [1,3] and [2,6] overlap and fuse into [1,6]. The others are
disjoint. Return k = 3.
```

```
Input:  ranges = [[1,4],[4,5]]
Output: 1, ranges = [[1,5],_]
Explanation: The intervals touch at 4, so they fuse.
```

```
Input:  ranges = [[1,10],[2,3],[4,5],[6,7]]
Output: 1, ranges = [[1,10],_,_,_]
Explanation: The last three intervals are all contained within [1,10]. The fused
end must not shrink to 3, 5 or 7.
```

```
Input:  ranges = [[1,2],[3,4]]
Output: 2, ranges = [[1,2],[3,4]]
Explanation: The intervals neither overlap nor touch — 3 is strictly greater
than 2 — so nothing fuses.
```

**Follow-up**

In the simpler members of this family, an element is either kept unchanged or
discarded. Here, keeping an element can also *modify* one that was already kept.
State the loop invariant that remains true under that additional operation, and
say whether it still guarantees that no unread input is destroyed.

---
_Hint: similar to LC26_RDfSA_