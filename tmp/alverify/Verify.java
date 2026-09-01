import java.lang.reflect.*;
import java.util.*;

public class Verify {
    static int cap(ArrayList<?> l) throws Exception {
        Field f = ArrayList.class.getDeclaredField("elementData");
        f.setAccessible(true);
        return ((Object[]) f.get(l)).length;
    }
    public static void main(String[] a) throws Exception {
        System.out.println("java.version = " + System.getProperty("java.version"));

        // 1. growth sequence from default ctor
        ArrayList<Integer> l = new ArrayList<>();
        System.out.println("cap after ctor (lazy) = " + cap(l));
        int last = -1; StringBuilder sb = new StringBuilder();
        for (int i = 1; i <= 400; i++) {
            l.add(i);
            int c = cap(l);
            if (c != last) { sb.append(c).append(" "); last = c; }
        }
        System.out.println("growth sequence = " + sb);

        // 2. new ArrayList<>(0) vs new ArrayList<>()  -- EMPTY vs DEFAULTCAPACITY_EMPTY
        ArrayList<Integer> zero = new ArrayList<>(0);
        zero.add(1);
        System.out.println("cap of new ArrayList<>(0) after 1 add = " + cap(zero));
        ArrayList<Integer> def = new ArrayList<>();
        def.add(1);
        System.out.println("cap of new ArrayList<>() after 1 add  = " + cap(def));

        // 3. new ArrayList<>(4) -- the Movement.entries case
        ArrayList<Integer> four = new ArrayList<>(4);
        System.out.println("cap of new ArrayList<>(4) = " + cap(four));
        for (int i=0;i<5;i++) four.add(i);
        System.out.println("cap of new ArrayList<>(4) after 5 adds = " + cap(four));

        // 4. equals/hashCode across List impls
        List<Integer> al = new ArrayList<>(List.of(1,2,3));
        List<Integer> ll = new LinkedList<>(List.of(1,2,3));
        List<Integer> im = List.of(1,2,3);
        System.out.println("ArrayList.equals(LinkedList) = " + al.equals(ll)
            + " ; hash equal = " + (al.hashCode()==ll.hashCode())
            + " ; equals(List.of) = " + al.equals(im));

        // 5. Java 21 SequencedCollection
        ArrayList<String> sc = new ArrayList<>(List.of("AO-100","AO-400","AA-700"));
        System.out.println("getFirst=" + sc.getFirst() + " getLast=" + sc.getLast());
        List<String> rev = sc.reversed();
        System.out.println("reversed=" + rev + " reversed class=" + rev.getClass().getName());
        rev.set(0, "AA-800");
        System.out.println("after rev.set(0,..) original=" + sc + "  -> reversed() is a VIEW");
        try { new ArrayList<String>().getFirst(); }
        catch (Exception e) { System.out.println("empty getFirst throws " + e.getClass().getName()); }

        // 6. trimToSize
        ArrayList<Integer> t = new ArrayList<>();
        for (int i=0;i<100;i++) t.add(i);
        System.out.println("cap at size 100 = " + cap(t));
        t.trimToSize();
        System.out.println("cap after trimToSize = " + cap(t));

        // 7. clear() does NOT shrink capacity
        t.clear();
        System.out.println("cap after clear() = " + cap(t) + " size=" + t.size());
    }
}
