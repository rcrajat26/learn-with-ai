import java.time.Instant;

public record LedgerEntry(String id, String movementId, Direction direction, Money amount, Instant postedAt) {
    public enum Direction { DEBIT, CREDIT }
    public record Money(long minorUnits, String currency) {}
}
