# Discard Every Copy of a Given Value

You are given an integer array `nums` and an integer `val`. Remove every
occurrence of `val` from `nums` **in place**. The order of the elements that
remain does not matter.

Let `k` be the number of elements in `nums` that are not equal to `val`. Your
function must:

- place all of those `k` remaining elements within the first `k` positions of
  `nums`, and
- return `k`.

Whatever is left in `nums` beyond index `k - 1` is irrelevant and will not be
inspected.

You must use only O(1) extra space. Allocating a second array of size
proportional to the input is not acceptable, even if you copy the result back
into `nums` afterwards.

**Constraints**
- `0 <= nums.length <= 100`
- `0 <= nums[i] <= 50`
- `0 <= val <= 100`
- Note that `nums` may be empty, and that `val` need not appear in `nums` at all.

**Examples**

```
Input:  nums = [3,2,2,3], val = 3
Output: 2, nums = [2,2,_,_]
Explanation: Return k = 2, with the first two elements of nums being 2 and 2.
Any arrangement of the surviving elements is accepted, and the trailing two
positions may hold anything.
```

```
Input:  nums = [0,1,2,2,3,0,4,2], val = 2
Output: 5, nums = [0,1,3,0,4,_,_,_]
Explanation: Return k = 5. The five surviving elements are 0, 1, 3, 0 and 4.
They could appear in any order in the first five positions — for instance
[0,1,4,0,3] would also be accepted.
```

```
Input:  nums = [1], val = 1
Output: 0, nums = [_]
```

---
_Hint: similar to LC26_RDfSA_