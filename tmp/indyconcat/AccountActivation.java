public final class AccountActivation {
    public String activationLog(String clientId, String statusCode) {
        return "client " + clientId + " -> " + statusCode;
    }
}
