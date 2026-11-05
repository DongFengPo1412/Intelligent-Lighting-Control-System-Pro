#pragma once
#include <cJSON.h>
#include <string.h>

namespace usb_json_reply {
inline bool ValidId(const cJSON* request) {
    const cJSON* id=cJSON_GetObjectItemCaseSensitive(request,"request_id");
    return !id || (cJSON_IsString(id) && strlen(id->valuestring)>0 && strlen(id->valuestring)<=64 &&
        strspn(id->valuestring,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")==strlen(id->valuestring));
}
// Request correlation and one complete line, written through one physical sink.
inline bool Send(cJSON* response,const cJSON* request,void (*write)(const char*)) {
    if(!response || !write)return false;
    const cJSON* id=cJSON_GetObjectItemCaseSensitive(request,"request_id");
    if(cJSON_IsString(id) && strlen(id->valuestring)>0 && strlen(id->valuestring)<=64 &&
       strspn(id->valuestring,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")==strlen(id->valuestring))
        cJSON_AddStringToObject(response,"request_id",id->valuestring);
    char text[512];
    if(!cJSON_PrintPreallocated(response,text,sizeof(text)-3,false))return false;
    strcat(text,"\r\n");write(text);return true;
}
}
