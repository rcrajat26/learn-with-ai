import java.util.*;

public class SubListCheck {
    public static void main(String[] args) {
        List<String> base = new ArrayList<>(List.of("DEP-301", "DEP-400", "BDP-100", "BDP-200", "BDP-300"));
        List<String> sub = base.subList(1, 4);
        System.out.println("subList(1,4) = " + sub + " class=" + sub.getClass());
        sub.set(0, "DEP-999");
        System.out.println("sub.set(0, DEP-999) -> base = " + base);

        try {
            base.add("BDP-400");
            sub.get(0);
            System.out.println("no exception");
        } catch (ConcurrentModificationException e) {
            System.out.println("base.add then read sub -> " + e);
        }

        List<String> b2 = new ArrayList<>(List.of("DEP-301", "DEP-400", "BDP-100", "BDP-200", "BDP-300"));
        b2.subList(1, 4).clear();
        System.out.println("b2.subList(1,4).clear() -> b2 = " + b2);

        // nested subList root check
        List<String> b3 = new ArrayList<>(List.of("DEP-301", "DEP-400", "BDP-100", "BDP-200", "BDP-300"));
        List<String> outer = b3.subList(0, 5);
        List<String> inner = outer.subList(1, 4);
        inner.set(0, "NESTED");
        System.out.println("nested subList write-through -> b3 = " + b3);

        try {
            b3.subList(2, 1);
        } catch (IllegalArgumentException e) {
            System.out.println("from > to -> " + e);
        }
        try {
            b3.subList(0, 99);
        } catch (IndexOutOfBoundsException e) {
            System.out.println("to > size -> " + e);
        }
        List<String> empty = b3.subList(2, 2);
        System.out.println("from==to -> " + empty + " isEmpty=" + empty.isEmpty());
    }
}
