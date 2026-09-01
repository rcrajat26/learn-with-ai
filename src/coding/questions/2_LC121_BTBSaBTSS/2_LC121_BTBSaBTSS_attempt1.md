- I will try running two pointers one from left and another from right
- The left pointer will check if the current element is less than the previous element if yes it updates absolute-min
- The right pointer will check if the current element is greater than the previous element if yes it updates absolute-max
- we break the loop if left-pointer cross the right pointer
- if (abs_max) - (abs_min) > 0 return that as a value, else return 0

Edge cases:
- Array size is 0, return 0
- Array size is 1, return 0
- Array has all elements with same value, then the same logic works and we return 0

```java
class Solution {
    public int maxProfit(int[] prices) {
        int n = prices.length;
        int i=0,j=n-1;
        int abs_min=Integer.MAX_VALUE, abs_max=Integer.MIN_VALUE;
        while (i<n || j>=0) {
            if (prices[i]<abs_min) {
                abs_min= prices[i];
                i++;
            }
            if (prices[j]>abs_max) {
                abs_max=prices[j];
                j--;
            }
            if (i>j) {
                break;
            }
        }
        return abs_max-abs_min > 0 ? abs_max-abs_min : 0; 
    }
}
```
- I failed initially with placing i++ and j-- condition within if block and the time ran out
fixed in:
```java
class Solution {
    public int maxProfit(int[] prices) {
        int n = prices.length;
        int i=0,j=n-1;
        int abs_min=Integer.MAX_VALUE, abs_max=Integer.MIN_VALUE;
        while (i<n || j>=0) {
            if (prices[i]<abs_min) {
                abs_min= prices[i];
            }
            if (prices[j]>abs_max) {
                abs_max=prices[j];
            }
            i++;j--;
            if (i>j) {
                break;
            }
        }
        return abs_max-abs_min > 0 ? abs_max-abs_min : 0; 
    }
}
```

After submitting code the flow broke for following input: [3,2,6,5,0,3]
- i=0,j=5 -> abs_min=3, abs_max=3
- i=1,j=4 -> abs_min=2, abs_max=3
- i=2,j=3 -> abs_min=2, abs_max=5
- i=3,j=2 -> break
- The J never got to reach 2nd index
- We must allow i and j both look through all the values

---
Approach 2:
- I can run 2 loops one after the other, but it may so happen that i>j so the buy trade happens after sell trade
- I need hints on this.