package org.fglab.kurisu;

import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.json.JSONObject;

/** Actual production UDP client over localhost sockets, not an Android/device test. */
public final class DeviceUdpClientTest {
    static final String KEY="a".repeat(64), BOOT="b".repeat(32);
    static void check(boolean value) {if(!value)throw new AssertionError();}
    static JSONObject envelope(String id,String command) {return new JSONObject().put("request_id",id).put("command",command);}
    public static void main(String[] args) throws Exception {
        final DatagramSocket server=new DatagramSocket(new InetSocketAddress("127.0.0.1",8888));
        final DatagramSocket stranger=new DatagramSocket(new InetSocketAddress("127.0.0.1",0));
        final AtomicBoolean running=new AtomicBoolean(true), mute=new AtomicBoolean(false);
        final AtomicInteger executions=new AtomicInteger();
        final AtomicBoolean dropFrames=new AtomicBoolean(false);
        final CountDownLatch frameStarted=new CountDownLatch(1);
        final List<String> wires=Collections.synchronizedList(new ArrayList<>());
        final Map<String,String> cache=new HashMap<>();
        final CountDownLatch mutedRequest=new CountDownLatch(1);
        Thread board=new Thread(()->{
            try {
                while(running.get()) {
                    byte[] buffer=new byte[4096];DatagramPacket packet=new DatagramPacket(buffer,buffer.length);server.receive(packet);
                    if(mute.get()){mutedRequest.countDown();continue;}
                    String raw=new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8);
                    JSONObject request=new JSONObject(raw);String id=request.getString("request_id");
                    JSONObject reply;
                    if(!request.has("command"))reply=new JSONObject().put("request_id",id).put("status","error").put("error","pairing_required").put("boot_id",BOOT);
                    else if(!KEY.equals(request.optString("token")))reply=new JSONObject().put("request_id",id).put("status","error").put("error","pairing_required");
                    else {
                        wires.add(raw);check(id.startsWith(request.getLong("seq")+"_"));check(BOOT.equals(request.getString("boot_id")));
                        if(dropFrames.get() && "frame".equals(new JSONObject(request.getString("command")).optString("cmd"))) {
                            frameStarted.countDown();continue;
                        }
                        if(!cache.containsKey(id)) {
                            executions.incrementAndGet();
                            reply=new JSONObject().put("request_id",id).put("status","ok").put("arcade",new JSONObject().put("game_id",1).put("state",1).put("score",0));
                            cache.put(id,reply.toString());
                            // Correct ID from a wrong port must not finish this connected socket.
                            byte[] forged=new JSONObject(reply.toString()).put("arcade",new JSONObject().put("score",999)).toString().getBytes(StandardCharsets.UTF_8);
                            stranger.send(new DatagramPacket(forged,forged.length,packet.getSocketAddress()));
                            byte[] wrong=new JSONObject().put("request_id","wrong").put("status","ok").toString().getBytes(StandardCharsets.UTF_8);
                            server.send(new DatagramPacket(wrong,wrong.length,packet.getSocketAddress()));
                            continue; // Lose the first genuine ACK, after executing the action once.
                        }
                        reply=new JSONObject(cache.get(id));
                    }
                    byte[] tx=reply.toString().getBytes(StandardCharsets.UTF_8);
                    server.send(new DatagramPacket(tx,tx.length,packet.getSocketAddress()));
                }
            } catch(Exception error) {if(running.get())throw new RuntimeException(error);}
        },"phase-a-fake-board");
        board.start();
        try {
            DeviceUdpClient client=new DeviceUdpClient();String id="java_request";
            String command="{\"cmd\":\"arcade\",\"action\":\"input\",\"down\":18,\"pressed\":16}";
            JSONObject result=new JSONObject(client.request("127.0.0.1",KEY,"jvm_client",envelope(id,command).toString(),150,1,id));
            check("ok".equals(result.getString("status")));check(id.equals(result.getString("request_id")));
            check(result.getJSONObject("arcade").getInt("score")==0);check(executions.get()==1);
            check(wires.size()==2 && wires.get(0).equals(wires.get(1)));
            int before=wires.size();
            result=new JSONObject(client.request("127.0.0.1",KEY,"jvm_client",envelope("bad","{\"cmd\":\"pair\"}").toString(),100,0,"bad"));
            check("forbidden_command".equals(result.getString("error")));check(wires.size()==before);
            result=new JSONObject(client.request("127.0.0.1",KEY,"jvm_client",envelope("bad_mask","{\"cmd\":\"arcade\",\"action\":\"input\",\"down\":\"18\",\"pressed\":16}").toString(),100,0,"bad_mask"));
            check("invalid_input".equals(result.getString("error")));check(wires.size()==before);
            check(DeviceUdpClient.isReadOnly(envelope("f","{\"cmd\":\"frame\"}").toString()));
            check(!DeviceUdpClient.isReadOnly(envelope("i",command).toString()));
            dropFrames.set(true);
            DeviceUdpClient readClient=new DeviceUdpClient();AtomicReference<String> dropped=new AtomicReference<>();
            Thread read=new Thread(()->dropped.set(readClient.request("127.0.0.1",KEY,"jvm_read_client",envelope("frame","{\"cmd\":\"frame\"}").toString(),1000,0,"frame")));
            read.start();check(frameStarted.await(1,TimeUnit.SECONDS));
            result=new JSONObject(client.request("127.0.0.1",KEY,"jvm_client",envelope("control",command).toString(),100,1,"control"));
            check("ok".equals(result.getString("status")));check(read.isAlive());read.join(1500);
            check("ack_timeout".equals(new JSONObject(dropped.get()).getString("error")));
            mute.set(true);AtomicReference<String> cancelled=new AtomicReference<>();
            Thread request=new Thread(()->cancelled.set(client.request("127.0.0.1",KEY,"jvm_client",envelope("cancel",command).toString(),1000,2,"cancel")));
            request.start();check(mutedRequest.await(1,TimeUnit.SECONDS));client.interrupt();request.join(1500);
            check(!request.isAlive());check("error".equals(new JSONObject(cancelled.get()).getString("status")));
            System.out.println("JVM production UDP: pairing, correlated/peer-filtered ACK, identical retry, command/type validation and lifecycle interrupt passed (loopback)");
        } finally {running.set(false);server.close();stranger.close();board.join(1500);check(!board.isAlive());}
    }
}
