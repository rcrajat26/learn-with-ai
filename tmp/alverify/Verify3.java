import java.util.*;
import java.util.stream.*;

public class Verify3 {
    record Money(long minor, String currency) {}
    record LedgerEntry(String id, String movementId, String direction, Money amount, long postedAt) {}
    public static void main(String[] args) throws Exception {
        // 1. sorting stability + Comparator chain on LedgerEntry
        List<LedgerEntry> es = new ArrayList<>(List.of(
            new LedgerEntry("E5","M2","CREDIT",new Money(420,"GBP"),300),
            new LedgerEntry("E1","M1","DEBIT", new Money(420,"GBP"),100),
            new LedgerEntry("E3","M1","CREDIT",new Money(180,"GBP"),100),
            new LedgerEntry("E2","M2","DEBIT", new Money(420,"GBP"),300)));
        es.sort(Comparator.comparingLong(LedgerEntry::postedAt)
                .thenComparing(LedgerEntry::direction));
        System.out.println("sorted ids = " + es.stream().map(LedgerEntry::id).toList());

        // 2. sort throws on null comparator with non-Comparable
        try { new ArrayList<>(List.of(new Money(1,"GBP"), new Money(2,"GBP"))).sort(null); }
        catch (Throwable t) { System.out.println("sort(null) on non-Comparable -> " + t.getClass().getName()); }

        // 3. TimSort contract violation is detectable
        try {
            List<Integer> bad = new ArrayList<>();
            for (int i=0;i<40;i++) bad.add(i);
            bad.sort((x,y) -> 1); // inconsistent comparator
            System.out.println("bad comparator (always 1) on 40 elems -> no throw");
        } catch (Throwable t) { System.out.println("bad comparator -> " + t.getClass().getName()+": "+t.getMessage()); }

        // 4. modCount bumped by sort? (sort increments modCount)
        var mf = java.util.AbstractList.class.getDeclaredField("modCount");
        mf.setAccessible(true);
        ArrayList<Integer> l = new ArrayList<>(List.of(3,1,2));
        int before = (int) mf.get(l);
        l.sort(null);
        System.out.println("modCount before sort=" + before + " after sort=" + mf.get(l));
        int b2 = (int) mf.get(l);
        l.set(0, 99);
        System.out.println("modCount after set() = " + mf.get(l) + " (set is NOT structural)");
        b2 = (int) mf.get(l);
        l.add(4);
        System.out.println("modCount after add() = " + mf.get(l) + " (add IS structural)");

        // 5. footprint: 19.8M ledger entries/day, ~180 bytes row
        System.out.println("--- footprint arithmetic ---");
        long refs = 4; // compressed oops
        for (int cap : new int[]{4, 10, 16}) {
            long arrayBytes = 16 + cap*refs; // header 16 + len, padded
            arrayBytes = (arrayBytes + 7) / 8 * 8;
            long alBytes = 16 + 4 + 4 + 4; // header + elementData ref + size + modCount -> padded
            alBytes = (alBytes + 7)/8*8;
            System.out.printf("cap=%2d : ArrayList shell=%d B, Object[]=%d B, total=%d B%n",
                cap, alBytes, arrayBytes, alBytes+arrayBytes);
        }
        // 6. wasted slots for Movement.entries (2..4 entries) at DEFAULT_CAPACITY 10
        System.out.println("Movement.entries with default ctor: 10 slots for 4 entries = "
            + (6*4) + " B wasted per Movement; at 19.8M/day / 4 entries = "
            + (19_800_000L/4) + " Movements/day -> "
            + (19_800_000L/4*24/1024/1024) + " MB/day wasted");
    }
}
