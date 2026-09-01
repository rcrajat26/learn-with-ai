- The brute force would be to run two loops and find for every i which is the biggest j
- Get the smallest i and its corresponding biggest j
```java
class Solution {
    public int maxProfit(int[] prices) {
        int n=prices.length;
        int mx=Integer.MIN_VALUE;
        
        for (int i=0; i<n; i++) {
            for (int j=i; j<n;j++) {
                if (prices[j]-prices[i]>mx) {
                    mx=prices[j]-prices[i];
                }
            }
        }
        return Math.max(mx, 0); 
    }
}
```
- In the above code as j>=i always sell time never goes before buy
- It's a triangular matrix not a square matrix

- We track the local minimum and compare it with next numbers till we see next minimum.
- However, I'm not aware what's the pattern
```java
class Solution {
    public int maxProfit(int[] prices) {
        int n = prices.length;
        int min_pr=Integer.MAX_VALUE;
        int mx=Integer.MIN_VALUE;

        for (int price : prices) {
            if (price < min_pr) {
                min_pr = price;
            }
            if (price - min_pr > mx) {
                mx = price - min_pr;
            }
        }
        return mx; 
    }
}
```