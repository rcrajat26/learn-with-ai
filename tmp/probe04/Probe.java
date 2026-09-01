import java.util.ArrayList;
import java.lang.reflect.Field;

public class Probe {
    static int capacityOf(ArrayList<?> list) throws Exception {
        Field f = ArrayList.class.getDeclaredField("elementData");
        f.setAccessible(true);
        Object[] arr = (Object[]) f.get(list);
        return arr.length;
    }
    public static void main(String[] args) throws Exception {
        ArrayList<String> a = new ArrayList<>();
        a.add("x");
        System.out.println("new ArrayList<>() then one add -> capacity " + capacityOf(a));

        ArrayList<String> b = new ArrayList<>(0);
        b.add("x");
        System.out.println("new ArrayList<>(0) then one add -> capacity " + capacityOf(b));

        ArrayList<String> c = new ArrayList<>(4);
        System.out.println("new ArrayList<>(4) capacity -> " + capacityOf(c));
        for (int i = 0; i < 5; i++) c.add("e" + i);
        System.out.println("after 5 adds -> capacity " + capacityOf(c));

        try {
            new ArrayList<>(-1);
        } catch (IllegalArgumentException e) {
            System.out.println("negative capacity -> " + e);
        }
    }
}
