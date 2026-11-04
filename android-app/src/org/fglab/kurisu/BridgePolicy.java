package org.fglab.kurisu;

/** Pure validation shared by the activity and host-side JVM tests. No DNS lookup. */
public final class BridgePolicy {
    private BridgePolicy() {}
    public static boolean privateIpv4(String host) {
        if (host == null || !host.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}")) return false;
        String[] parts=host.split("\\."); int[] octets=new int[4];
        for (int i=0;i<4;i++) {
            octets[i]=Integer.parseInt(parts[i]);
            if (octets[i]>255 || !parts[i].equals(Integer.toString(octets[i]))) return false;
        }
        if (octets[3]==0 || octets[3]==255) return false;
        return octets[0]==10 || (octets[0]==172 && octets[1]>=16 && octets[1]<=31) ||
            (octets[0]==192 && octets[1]==168);
    }
    public static boolean requestId(String id) { return id!=null && id.matches("[a-zA-Z0-9_-]{1,64}"); }
    public static boolean token(String token) { return token!=null && token.matches("[0-9a-f]{64}"); }
}
