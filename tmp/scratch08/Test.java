import java.util.*;

public class Test {
    public static void main(String[] args) {
        List<String> l1 = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
        try {
            for (String s : l1) {
                if (s.equals("AA-700")) l1.remove(s);
            }
            System.out.println("remove-last: no exception, list=" + l1);
        } catch (ConcurrentModificationException e) {
            System.out.println("remove-last: " + e);
        }

        List<String> l2 = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
        try {
            for (String s : l2) {
                if (s.equals("AO-400")) l2.remove(s);
            }
            System.out.println("remove-second-to-last: no exception, list=" + l2);
        } catch (ConcurrentModificationException e) {
            System.out.println("remove-second-to-last: " + e);
        }

        List<String> l3 = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
        Iterator<String> it = l3.iterator();
        while (it.hasNext()) {
            String s = it.next();
            if (s.equals("AO-400")) it.remove();
        }
        System.out.println("iterator-remove: list=" + l3);

        List<String> l4 = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
        try {
            l4.forEach(s -> { if (s.equals("AO-400")) l4.add("EXTRA"); });
            System.out.println("forEach-add: no exception, list=" + l4);
        } catch (ConcurrentModificationException e) {
            System.out.println("forEach-add: " + e);
        }
    }
}
