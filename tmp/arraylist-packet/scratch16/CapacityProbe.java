import java.util.ArrayList;
import java.lang.reflect.Field;

public class CapacityProbe {

    static int realCapacity(ArrayList<?> list) throws Exception {
        Field f = ArrayList.class.getDeclaredField("elementData");
        f.setAccessible(true);
        return ((Object[]) f.get(list)).length;
    }

    public static void main(String[] args) throws Exception {
        ArrayList<Integer> a = new ArrayList<>();
        System.out.println("new ArrayList<>() capacity right after construction: " + realCapacity(a));

        a.add(1);
        System.out.println("new ArrayList<>() capacity after one add: " + realCapacity(a));

        ArrayList<Integer> b = new ArrayList<>(0);
        b.add(1);
        System.out.println("new ArrayList<>(0) capacity after one add: " + realCapacity(b));

        ArrayList<Integer> c = new ArrayList<>(4);
        for (int i = 0; i < 5; i++) c.add(i);
        System.out.println("new ArrayList<>(4) capacity after five adds: " + realCapacity(c));

        ArrayList<Integer> d = new ArrayList<>();
        for (int i = 0; i < 100; i++) d.add(i);
        System.out.println("default-constructed capacity at size 100: " + realCapacity(d));

        d.trimToSize();
        System.out.println("capacity after trimToSize(): " + realCapacity(d));

        d.clear();
        System.out.println("capacity after clear(): " + realCapacity(d));
    }
}
