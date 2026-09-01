# Push All Zeros to the Back

Given an integer array `nums`, move every `0` to the end of the array while
preserving the relative order of all the non-zero elements.

This must be done **in place** — you may not allocate a second array.

Unlike problems where the tail of the array is left unspecified, here the whole
array is checked: after your function returns, `nums` must consist of the
non-zero elements in their original relative order, followed by exactly as many
zeros as the input contained. Your function returns nothing.

**Constraints**
- `1 <= nums.length <= 10^4`
- `-2^31 <= nums[i] <= 2^31 - 1`
- The array may be all zeros, or contain no zeros at all.

**Examples**

```
Input:  nums = [0,1,0,3,12]
Output: nums = [1,3,12,0,0]
Explanation: The non-zero elements 1, 3 and 12 keep their relative order, and
the two zeros are moved to the end.
```

```
Input:  nums = [0]
Output: nums = [0]
```

```
Input:  nums = [4,0,0,-7,0,2]
Output: nums = [4,-7,2,0,0,0]
```

**Follow-up**

Can you minimise the total number of write operations your solution performs?
State how many writes your solution makes as a function of the input, and
whether that count is optimal.

---
_Hint: similar to LC26_RDfSA_