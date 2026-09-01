public final class BootstrapCost {
    static String a(String c, String s) { return "client " + c + " -> " + s; }
    static String b(String c, String s) { return "acct " + c + " :: " + s; }
    public static void main(String[] args) {
        long t0 = System.nanoTime();
        String r1 = a("c1", "AA-801 ACTIVATED");
        long t1 = System.nanoTime();
        String r2 = a("c2", "AA-801 ACTIVATED");
        long t2 = System.nanoTime();
        long t3 = System.nanoTime();
        String r3 = b("c3", "AA-801 ACTIVATED");
        long t4 = System.nanoTime();
        System.out.println("first  call site A (bootstrap+invoke): " + (t1 - t0) / 1000 + " us");
        System.out.println("second call site A (linked)          : " + (t2 - t1) + " ns");
        System.out.println("first  call site B (bootstrap+invoke): " + (t4 - t3) / 1000 + " us");
        System.out.println(r1.length() + r2.length() + r3.length());
    }
}
