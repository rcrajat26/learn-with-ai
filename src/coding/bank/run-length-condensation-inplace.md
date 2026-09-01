# Condense Repeated Runs Into Counted Form, Writing Over the Input

You are given an array of characters `chars`. Rewrite it, in place, into a
condensed form built as follows.

Walk the array left to right and break it into maximal groups of consecutive
repeating characters. For each group:

- if the group has length 1, append just that character;
- if the group has length `L > 1`, append that character followed by the decimal
  digits of `L`.

Each digit of a length greater than 9 occupies its own position in the array —
so a group of 12 identical characters condenses to three positions: the
character, `'1'`, and `'2'`.

Let `k` be the length of the condensed form. Your function must:

- write the condensed form into the first `k` positions of `chars`, and
- return `k`.

Anything left in `chars` beyond index `k - 1` will not be inspected. You must use
only O(1) extra space; in particular you may not build the answer in a separate
buffer, list, or string and then copy it back.

**Constraints**
- `1 <= chars.length <= 2000`
- Each `chars[i]` is a lowercase English letter, an uppercase English letter, or
  a digit character.
- The input is **not** sorted, and groups are determined purely by adjacency.

**Examples**

```
Input:  chars = ['a','a','b','b','c','c','c']
Output: 6, chars = ['a','2','b','2','c','3',_]
Explanation: The groups are "aa", "bb", "ccc", condensing to "a2b2c3".
```

```
Input:  chars = ['a']
Output: 1, chars = ['a']
Explanation: A single group of length 1 contributes just "a" — no count is
appended.
```

```
Input:  chars = ['a','b','b','b','b','b','b','b','b','b','b','b','b']
Output: 4, chars = ['a','b','1','2',_,_,_,_,_,_,_,_,_]
Explanation: The groups are "a" and twelve b's, condensing to "ab12". The count
12 occupies two positions.
```

```
Input:  chars = ['x','y','z']
Output: 3, chars = ['x','y','z']
Explanation: Three groups of length 1. The condensed form is no shorter than the
input.
```

**Follow-up**

Notice that a group of length 1 condenses to 1 position, while a group of length
2 also condenses to 2 positions. Prove that the position you are about to write
to is never a position you have not yet read. State the inequality your solution
maintains and identify the input family where it is tight.

---
_Hint: similar to LC26_RDfSA_