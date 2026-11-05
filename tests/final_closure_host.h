#include "frame_encoding.h"
#include "usb_json_reply.h"
#include <assert.h>
#include <string>
static int closure_writes=0;
static std::string closure_wire;
static void ClosureWrite(const char* text){++closure_writes;closure_wire=text;}
static void TestFinalClosure() {
    char hex[1537],out[1025];
    const char* digits="0123456789abcdef";
    for(int i=0;i<768;++i){hex[i*2]=digits[(i%256)>>4];hex[i*2+1]=digits[i%16];}hex[1536]=0;
    assert(frame_encoding::HexToBase64(hex,out,sizeof(out)));
    assert(strlen(out)==1024 && !strncmp(out,"AAECAwQFBgcICQoL",16));
    assert(!frame_encoding::HexToBase64(hex,out,1024));
    hex[0]='z';assert(!frame_encoding::HexToBase64(hex,out,sizeof(out)));
    auto request=cJSON_Parse("{\"cmd\":\"pair\",\"request_id\":\"physical_123\"}");
    auto response=cJSON_Parse("{\"status\":\"ok\",\"control_token\":\"test-only\"}");
    assert(usb_json_reply::Send(response,request,ClosureWrite));
    assert(closure_writes==1 && closure_wire.substr(closure_wire.size()-2)=="\r\n");
    auto parsed=cJSON_ParseWithOpts(closure_wire.c_str(),nullptr,true);
    assert(parsed && !strcmp(cJSON_GetObjectItem(parsed,"request_id")->valuestring,"physical_123"));
    cJSON_Delete(parsed);cJSON_Delete(response);cJSON_Delete(request);
    request=cJSON_Parse("{\"request_id\":\"unsafe\\nline\"}");
    assert(!usb_json_reply::ValidId(request));cJSON_Delete(request);
}
