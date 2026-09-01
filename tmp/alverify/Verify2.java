import java.util.*;
import java.util.function.*;

public class Verify2 {
    static void t(String name, Runnable r) {
        try { r.run(); System.out.println(name + " -> OK (no throw)"); }
        catch (Throwable e) { System.out.println(name + " -> " + e.getClass().getName()
            + (e.getMessage()==null?"":": "+e.getMessage())); }
    }
    public static void main(String[] a) {
        // 1. classic CME
        t("remove during for-each", () -> {
            List<String> l = new ArrayList<>(List.of("AO-100","AO-400","AA-700"));
            for (String s : l) if (s.equals("AO-400")) l.remove(s);
        });
        // 2. the famous second-to-last removal that does NOT throw
        t("remove SECOND-TO-LAST during for-each", () -> {
            List<String> l = new ArrayList<>(List.of("AO-100","AO-400","AA-700"));
            for (String s : l) if (s.equals("AO-400")) l.remove(s);
            System.out.print("   (list now " + l + ") ");
        });
        // 3. remove last element during for-each
        t("remove LAST during for-each", () -> {
            List<String> l = new ArrayList<>(List.of("AO-100","AO-400","AA-700"));
            for (String s : l) if (s.equals("AA-700")) l.remove(s);
        });
        // 4. Iterator.remove is legal
        t("Iterator.remove", () -> {
            List<String> l = new ArrayList<>(List.of("AO-100","AO-400","AA-700"));
            for (Iterator<String> it = l.iterator(); it.hasNext();)
                if (it.next().equals("AO-400")) it.remove();
            System.out.print("   (list now " + l + ") ");
        });
        // 5. forEach detects mutation
        t("mutate inside forEach", () -> {
            List<String> l = new ArrayList<>(List.of("AO-100","AO-400","AA-700"));
            l.forEach(s -> { if (s.equals("AO-100")) l.add("AA-800"); });
        });
        // 6. subList aliasing
        List<String> base = new ArrayList<>(List.of("DEP-301","DEP-400","BDP-100","BDP-200","BDP-300"));
        List<String> sub = base.subList(1, 4);
        System.out.println("subList(1,4) = " + sub + " class=" + sub.getClass().getName());
        sub.set(0, "DEP-999");
        System.out.println("after sub.set -> base = " + base + "  (write-through)");
        t("structural change to base then read sub", () -> {
            base.add("BDP-400");
            System.out.print("   sub.size()=" + sub.size() + " ");
        });
        t("sub.clear() removes from base", () -> {
            List<String> b2 = new ArrayList<>(List.of("DEP-301","DEP-400","BDP-100","BDP-200","BDP-300"));
            b2.subList(1,4).clear();
            System.out.print("   base now " + b2 + " ");
        });
        // 7. Arrays.asList fixed size
        t("Arrays.asList().add", () -> Arrays.asList("DEP-301","DEP-400").add("BDP-100"));
        t("Arrays.asList().set", () -> { List<String> l = Arrays.asList("DEP-301","DEP-400"); l.set(0,"X"); System.out.print("   -> "+l+" "); });
        t("List.of().set", () -> List.of("DEP-301","DEP-400").set(0,"X"));
        // 8. remove(int) vs remove(Object) overload trap
        List<Integer> nums = new ArrayList<>(List.of(10, 20, 30));
        nums.remove(1);
        System.out.println("List<Integer>.remove(1) -> " + nums + "  (removed INDEX 1)");
        List<Integer> nums2 = new ArrayList<>(List.of(10, 20, 30));
        nums2.remove(Integer.valueOf(20));
        System.out.println("remove(Integer.valueOf(20)) -> " + nums2 + "  (removed VALUE)");
        // 9. toArray covariance trap
        t("toArray(new String[0]) on List<Object> holding non-String", () -> {
            List<Object> l = new ArrayList<>(List.of("DEP-301", 42));
            String[] arr = l.toArray(new String[0]);
            System.out.print(Arrays.toString(arr));
        });
        // 10. Arrays.asList(array).toArray().getClass()
        List<String> asl = Arrays.asList("DEP-301");
        System.out.println("Arrays.asList(..).toArray() class = " + asl.toArray().getClass().getName());
        System.out.println("new ArrayList<>(asl).toArray() class = " + new ArrayList<>(asl).toArray().getClass().getName());
        // 11. removeIf on restrictions
        List<String> restr = new ArrayList<>(List.of("CASH_OUT_BLOCKED","STAKE_BLOCKED","DEPOSIT_BLOCKED","LOGIN_BLOCKED"));
        restr.removeIf(s -> s.endsWith("_BLOCKED") && s.startsWith("D"));
        System.out.println("after removeIf -> " + restr);
    }
}
