# Retain Only the Values That Occur Exactly Once

Given an integer array `nums` sorted in non-decreasing order, keep only those
values that appear **exactly once** in the array, discarding every value that
appears two or more times. Any value that is duplicated must be removed
completely — not reduced to a single copy, but removed entirely.

The work must be done **in place** in O(1) extra space, and the surviving values
must remain in ascending order.

Let `k` be the number of values that appear exactly once. Your function must:

- place those `k` values, in ascending order, in the first `k` positions of
  `nums`, and
- return `k`.

Anything left in `nums` beyond index `k - 1` will not be inspected.

**Constraints**
- `1 <= nums.length <= 3 * 10^4`
- `-10^4 <= nums[i] <= 10^4`
- `nums` is sorted in non-decreasing order.
- It is possible that no value appears exactly once, in which case `k` is 0.

**Examples**

```
Input:  nums = [1,1,2,3,3,4]
Output: 2, nums = [2,4,_,_,_,_]
Explanation: 1 appears twice and 3 appears twice, so both are dropped entirely.
Only 2 and 4 occur exactly once. Return k = 2.
```

```
Input:  nums = [1,2,2,3,3,3,4,5,5]
Output: 2, nums = [1,4,_,_,_,_,_,_,_]
Explanation: 2 appears twice, 3 appears three times, 5 appears twice — all are
removed. 1 and 4 survive. Return k = 2.
```

```
Input:  nums = [7,7]
Output: 0, nums = [_,_]
Explanation: The only value present is duplicated, so nothing survives.
```

```
Input:  nums = [-5,0,0,0,9]
Output: 2, nums = [-5,9,_,_,_]
```

**Follow-up**

Suppose the array is delivered to you as a stream: you receive the elements one
at a time in ascending order, you may hold only a constant number of them in
memory, and you must emit each surviving value as soon as you can be certain it
survives. What is the maximum number of elements you must buffer before you can
emit, and why?

---
_Hint: similar to LC26_RDfSA_