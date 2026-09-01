import java.util.ArrayList;
import java.lang.reflect.Field;

public class GrowthDemo {
    public static void main(String[] args) throws Exception {
        Field elementDataField = ArrayList.class.getDeclaredField("elementData");
        elementDataField.setAccessible(true);

        LedgerEntryList<Integer> mine = new LedgerEntryList<>();
        ArrayList<Integer> real = new ArrayList<>();

        StringBuilder mineSeq = new StringBuilder();
        StringBuilder realSeq = new StringBuilder();

        int lastMineCap = mine.capacity();
        int lastRealCap = ((Object[]) elementDataField.get(real)).length;

        for (int i = 0; i < 400; i++) {
            mine.add(i);
            real.add(i);

            int mineCap = mine.capacity();
            int realCap = ((Object[]) elementDataField.get(real)).length;

            if (mineCap != lastMineCap) {
                mineSeq.append(mineCap).append(' ');
                lastMineCap = mineCap;
            }
            if (realCap != lastRealCap) {
                realSeq.append(realCap).append(' ');
                lastRealCap = realCap;
            }
        }

        System.out.println("LedgerEntryList capacity sequence: " + mineSeq.toString().trim());
        System.out.println("real ArrayList  capacity sequence: " + realSeq.toString().trim());
        System.out.println("match: " + mineSeq.toString().trim().equals(realSeq.toString().trim()));
    }
}
