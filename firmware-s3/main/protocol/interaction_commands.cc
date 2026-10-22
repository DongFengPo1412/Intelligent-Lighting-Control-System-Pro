#include "interaction_commands.h"
#include "display_manager.h"
#include <math.h>
#include <string.h>

namespace {
bool number(cJSON* r,const char* key,double lo,double hi,double& out,bool integer=false) {
    auto* v=cJSON_GetObjectItemCaseSensitive(r,key);
    if(!cJSON_IsNumber(v)||!isfinite(v->valuedouble)||v->valuedouble<lo||v->valuedouble>hi)return false;
    out=v->valuedouble;return !integer||floor(out)==out;
}
bool boolean(cJSON* r,const char* key,bool& out) {
    auto* v=cJSON_GetObjectItemCaseSensitive(r,key);if(!cJSON_IsBool(v))return false;
    out=cJSON_IsTrue(v);return true;
}
int digit(char c) { if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1; }
}
int HandleInteractionCommand(const char* cmd,cJSON* root,DisplayManager& dm) {
    double x=0,y=0,z=0,a=0,b=0,c=0;bool first=false,second=false;
    if(!strcmp(cmd,"frame"))return 1;
    if(!strcmp(cmd,"celebrate")) { dm.Celebrate();return 1; }
    if(!strcmp(cmd,"track_cal")) {
        x=y=0;a=b=1;
        if((cJSON_GetObjectItem(root,"x0")&&!number(root,"x0",0,1,x))||
           (cJSON_GetObjectItem(root,"y0")&&!number(root,"y0",0,1,y))||
           (cJSON_GetObjectItem(root,"x1")&&!number(root,"x1",0,1,a))||
           (cJSON_GetObjectItem(root,"y1")&&!number(root,"y1",0,1,b))||
           (cJSON_GetObjectItem(root,"invert_x")&&!boolean(root,"invert_x",first))||
           (cJSON_GetObjectItem(root,"invert_y")&&!boolean(root,"invert_y",second))||a-x<.0001||b-y<.0001)return 0;
        dm.ConfigureFingertip(x,y,a,b,first,second);return 1;
    }
    if(!strcmp(cmd,"track")) {
        if(!number(root,"x",0,1,x)||!number(root,"y",0,1,y)||!boolean(root,"visible",first))return 0;
        c=1;if(cJSON_GetObjectItem(root,"conf")&&!number(root,"conf",0,1,c))return 0;
        dm.FeedFingertip(x,y,first,c);return 1;
    }
    if(!strcmp(cmd,"hand")) {
        if(!number(root,"x",0,1,x)||!number(root,"y",0,1,y)||!number(root,"z",-2,2,z)||
           !boolean(root,"pinch",first)||!boolean(root,"visible",second))return 0;
        dm.FeedHand(x,y,z,first,second);return 1;
    }
    if(!strcmp(cmd,"mir")) {
        if(!number(root,"energy",0,1,a)||!number(root,"flux",0,1,b)||!number(root,"tempo",30,240,c)||!boolean(root,"onset",first))return 0;
        double phase=0;
        if(cJSON_GetObjectItemCaseSensitive(root,"phase")&&!number(root,"phase",0,1,phase))return 0;
        dm.FeedMusic(a,b,first,c,phase);return 1;
    }
    if(!strcmp(cmd,"pixel")) {
        if(!number(root,"x",0,15,x,true)||!number(root,"y",0,15,y,true)||!number(root,"r",0,255,a,true)||
           !number(root,"g",0,255,b,true)||!number(root,"b",0,255,c,true))return 0;
        dm.SetCanvasPixel(x,y,ColorRGB(a,b,c));return 1;
    }
    if(!strcmp(cmd,"canvas")) {
        auto* hex=cJSON_GetObjectItemCaseSensitive(root,"hex");
        if(!cJSON_IsString(hex)||strlen(hex->valuestring)!=1536)return 0;
        for(int i=0;i<1536;i++)if(digit(hex->valuestring[i])<0)return 0;
        ColorRGB colors[256];
        for(int i=0;i<256;i++) {
            auto* s=hex->valuestring+i*6;
            colors[i]=ColorRGB(digit(s[0])*16+digit(s[1]),digit(s[2])*16+digit(s[3]),digit(s[4])*16+digit(s[5]));
        }
        dm.SetCanvasFrame(colors);
        return 1;
    }
    if(!strcmp(cmd,"gamma")) { if(!boolean(root,"enable",first))return 0;dm.SetGamma(first);return 1; }
    if(!strcmp(cmd,"difficulty")) {
        if(!number(root,"level",0,1,a)||!boolean(root,"adaptive",first))return 0;
        dm.ConfigureDifficulty(a,first);return 1;
    }
    if(!strcmp(cmd,"performance")) {
        if(!number(root,"reaction_ms",0,10000,a)||!number(root,"frustration",0,1,b)||!boolean(root,"success",first))return 0;
        dm.FeedPerformance(a,b,first);return 1;
    }
    if(!strcmp(cmd,"pet_context")) {
        if(!number(root,"hour",0,23,a,true)||!number(root,"gaze",-1,1,b)||!boolean(root,"present",first)||!boolean(root,"tired",second))return 0;
        dm.FeedPet(a,b,first,second);return 1;
    }
    return -1;
}
