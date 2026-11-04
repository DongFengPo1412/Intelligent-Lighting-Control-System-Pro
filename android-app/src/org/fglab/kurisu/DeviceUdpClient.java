package org.fglab.kurisu;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.json.JSONObject;

/** Used only on the bounded single-worker executor. Retries reuse the same wire request. */
final class DeviceUdpClient {
    static boolean isReadOnly(String message) {
        try {
            JSONObject cmd=new JSONObject(new JSONObject(message).getString("command"));
            String name=cmd.getString("cmd");
            return "frame".equals(name)||"status".equals(name)||
                ("arcade".equals(name)&&"status".equals(cmd.optString("action")));
        } catch(Exception invalid) {return false;}
    }
    private String bootId="";
    private String peerIdentity="";
    private long sequence=System.currentTimeMillis()*1000L;
    private volatile DatagramSocket activeSocket;
    void interrupt() { DatagramSocket socket=activeSocket; if(socket!=null)socket.close(); }
    static String error(String id,String code) {
        JSONObject result=new JSONObject();
        try { result.put("request_id",id);result.put("status","error");result.put("error",code); } catch(Exception ignored) {}
        return result.toString();
    }
    private JSONObject roundTrip(DatagramSocket socket, JSONObject envelope,int timeout,int retries) throws Exception {
        byte[] tx=envelope.toString().getBytes(StandardCharsets.UTF_8);
        if(tx.length>=4096)throw new IllegalArgumentException();
        String rid=envelope.getString("request_id");
        for(int attempt=0;attempt<=retries;attempt++) {
            socket.send(new DatagramPacket(tx,tx.length));
            long deadline=System.nanoTime()+timeout*1000000L;
            while(System.nanoTime()<deadline) {
                socket.setSoTimeout(Math.max(1,(int)((deadline-System.nanoTime())/1000000L)));
                byte[] rx=new byte[4096];DatagramPacket packet=new DatagramPacket(rx,rx.length);
                try { socket.receive(packet); } catch(java.net.SocketTimeoutException timeoutError) { break; }
                if(packet.getLength()>=rx.length)continue;
                try {
                    JSONObject reply=new JSONObject(new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8));
                    if(rid.equals(reply.optString("request_id")) &&
                        ("ok".equals(reply.optString("status")) || "error".equals(reply.optString("status"))))return reply;
                } catch(org.json.JSONException malformed) { /* Ignore unsolicited/malformed packets until deadline. */ }
            }
        }
        throw new java.net.SocketTimeoutException();
    }
    String request(String host,String token,String clientId,String message,int timeout,int retries,String callback) {
        try {
            String identity=host+"|"+token;
            if(!identity.equals(peerIdentity)){bootId="";peerIdentity=identity;}
            JSONObject envelope=new JSONObject(message);
            if(!callback.equals(envelope.getString("request_id")) || message.length()>2500)return error(callback,"invalid_request");
            String command=envelope.getString("command");
            if(command.getBytes(StandardCharsets.UTF_8).length>2048)return error(callback,"command_too_large");
            JSONObject cmd=new JSONObject(command);
            String name=cmd.getString("cmd");
            if(!("arcade".equals(name)||"frame".equals(name)||"status".equals(name)))return error(callback,"forbidden_command");
            if("arcade".equals(name)) {
                String action=cmd.getString("action");
                if(!action.matches("select|start|pause|resume|reset|exit|input|heartbeat|status|players|config"))return error(callback,"invalid_action");
                if("config".equals(action)) {
                    if(!(cmd.get("sound_enabled") instanceof Boolean) || !(cmd.get("sound_volume") instanceof Number))return error(callback,"invalid_config");
                    double volume=cmd.getDouble("sound_volume");
                    if(volume!=Math.floor(volume)||volume<0||volume>100)return error(callback,"invalid_config");
                    if(cmd.has("difficulty")) {
                        if(!(cmd.get("difficulty") instanceof Number))return error(callback,"invalid_config");
                        double level=cmd.getDouble("difficulty");
                        if(level!=Math.floor(level)||level<0||level>2)return error(callback,"invalid_config");
                    }
                }
                if("players".equals(action) && (!(cmd.get("count") instanceof Number) ||
                    (cmd.getDouble("count")!=1 && cmd.getDouble("count")!=2)))return error(callback,"invalid_player_count");
                if("select".equals(action)) {
                    if(!(cmd.get("game_id") instanceof Number))return error(callback,"invalid_game_id");
                    double id=cmd.getDouble("game_id");
                    if(id!=Math.floor(id)||!(id==1||id==2||id==3||id==4||id==5||id==6||id==9||id==10||id==14||id==15||id==16||id==17||id==18||id==19||id==20||id==21||id==22||id==26||id==27||id==28||id==29||id==30||id==31||id==33||id==34||id==38||id==40||id==41||id==42||id==43||id==44||id==45||id==51||id==52||id==53||id==54||id==55||id==62||id==63||id==64||id==65||id==66||id==67||id==72||id==73||id==74||id==75||id==76||id==83||id==84||id==85||id==86||id==87||id==88||id==92||id==93||id==94||id==95||id==97))return error(callback,"invalid_game_id");
                }
                if("input".equals(action)) for(String key:new String[]{"down","pressed"}) {
                    if(!(cmd.get(key) instanceof Number))return error(callback,"invalid_input");
                    double value=cmd.getDouble(key);
                    if(value!=Math.floor(value)||value<0||value>255)return error(callback,"invalid_input");
                }
            }
            try(DatagramSocket socket=new DatagramSocket()) {
                activeSocket=socket;
                // Connected UDP filters replies by the configured device IP AND port.
                socket.connect(InetAddress.getByName(host),8888);
                if(bootId.isEmpty()) {
                    JSONObject probe=new JSONObject();probe.put("request_id","probe_"+UUID.randomUUID().toString().replace("-",""));
                    JSONObject challenge=roundTrip(socket,probe,400,1);
                    bootId=challenge.optString("boot_id");
                    if(!bootId.matches("[0-9a-f]{32}")){bootId="";return error(callback,"invalid_boot_id");}
                }
                envelope.put("token",token);envelope.put("boot_id",bootId);
                envelope.put("client_id",clientId);envelope.put("seq",++sequence);
                String wireId=sequence+"_"+callback;
                if(!BridgePolicy.requestId(wireId))return error(callback,"invalid_request_id");
                envelope.put("request_id",wireId);
                JSONObject reply=roundTrip(socket,envelope,Math.max(100,Math.min(timeout,1000)),Math.max(0,Math.min(retries,2)));
                if("boot_changed".equals(reply.optString("error")))bootId="";
                // roundTrip matched the exact wire ID; now restore this page's callback ID.
                reply.put("request_id",callback);
                return reply.toString();
            } finally { activeSocket=null; }
        } catch(java.net.SocketTimeoutException offline) { return error(callback,"ack_timeout"); }
          catch(Exception invalid) { return error(callback,"udp_failed"); }
    }
}
