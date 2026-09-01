import java.time.Instant;

public class PresizeBenchmark {

    static Result run(int n, int presize) {
        LedgerEntryList<LedgerEntry> list = presize > 0 ? new LedgerEntryList<>(presize) : new LedgerEntryList<>();
        int grows = 0;
        long copies = 0;
        int lastCapacity = list.capacity();

        long start = System.nanoTime();
        for (int i = 0; i < n; i++) {
            int capBefore = list.capacity();
            list.add(new LedgerEntry(
                    "E" + i, "M" + (i / 3),
                    (i % 2 == 0) ? LedgerEntry.Direction.DEBIT : LedgerEntry.Direction.CREDIT,
                    new LedgerEntry.Money(1000 + i, "GBP"),
                    Instant.EPOCH));
            int capAfter = list.capacity();
            if (capAfter != capBefore) {
                grows++;
                // a grow copies every element that existed before this add
                copies += capBefore;
            }
        }
        long elapsedNanos = System.nanoTime() - start;
        return new Result(grows, copies, elapsedNanos);
    }

    record Result(int grows, long copies, long elapsedNanos) {}

    public static void main(String[] args) {
        for (int n : new int[]{1800, 40000}) {
            Result withoutPresize = run(n, 0);
            Result withPresize = run(n, n);

            System.out.println("N = " + n);
            System.out.println("  without presizing: grows=" + withoutPresize.grows()
                    + " copies=" + withoutPresize.copies()
                    + " time=" + (withoutPresize.elapsedNanos() / 1_000_000.0) + " ms");
            System.out.println("  with presizing:    grows=" + withPresize.grows()
                    + " copies=" + withPresize.copies()
                    + " time=" + (withPresize.elapsedNanos() / 1_000_000.0) + " ms");
        }
    }
}
