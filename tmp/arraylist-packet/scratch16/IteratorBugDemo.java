import java.util.ConcurrentModificationException;

public class IteratorBugDemo {
    public static void main(String[] args) {
        System.out.println("--- Case A: remove the LAST element during a for-each ---");
        LedgerEntryList<String> a = new LedgerEntryList<>();
        a.add("AO-100");
        a.add("AO-400");
        a.add("AA-700");
        try {
            for (String s : a) {
                System.out.println("visiting " + s);
                if (s.equals("AA-700")) {
                    a.remove("AA-700");
                }
            }
        } catch (ConcurrentModificationException e) {
            System.out.println("threw " + e.getClass().getName());
        }
        System.out.println("surviving list: " + a);

        System.out.println();
        System.out.println("--- Case B: remove the SECOND-TO-LAST element during a for-each ---");
        LedgerEntryList<String> b = new LedgerEntryList<>();
        b.add("AO-100");
        b.add("AO-400");
        b.add("AA-700");
        try {
            for (String s : b) {
                System.out.println("visiting " + s);
                if (s.equals("AO-400")) {
                    b.remove("AO-400");
                }
            }
            System.out.println("no exception thrown");
        } catch (ConcurrentModificationException e) {
            System.out.println("threw " + e.getClass().getName());
        }
        System.out.println("surviving list: " + b);
    }
}
