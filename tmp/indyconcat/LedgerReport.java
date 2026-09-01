public final class LedgerReport {
    public String report(String[] ids) {
        String report = "";
        for (String id : ids) {
            report += id + "\n";
        }
        return report;
    }
}
