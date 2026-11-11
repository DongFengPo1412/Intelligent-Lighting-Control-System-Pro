#include "interaction_commands.h"
#include "display_manager.h"
#include "canvas_protocol.h"
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
int HandleInteractionCommand(const char* cmd,cJSON* root,DisplayManager& dm,DisplayManager::CanvasSource source) {
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
        float bands[16];const float* spectrum=nullptr;
        auto* item=cJSON_GetObjectItemCaseSensitive(root,"bands");
        if(item) {
            if(!cJSON_IsArray(item)||cJSON_GetArraySize(item)!=16)return 0;
            for(int i=0;i<16;i++) {
                auto* value=cJSON_GetArrayItem(item,i);
                if(!cJSON_IsNumber(value)||!isfinite(value->valuedouble)||value->valuedouble<0||
                   value->valuedouble>15||floor(value->valuedouble)!=value->valuedouble)return 0;
                bands[i]=value->valuedouble/15.f;
            }
            spectrum=bands;
        }
        dm.FeedMusic(a,b,first,c,phase,spectrum);return 1;
    }
    if(!strcmp(cmd,"pixel")) {
        if(!number(root,"x",0,15,x,true)||!number(root,"y",0,15,y,true)||!number(root,"r",0,255,a,true)||
           !number(root,"g",0,255,b,true)||!number(root,"b",0,255,c,true))return 0;
        bool manual_active = dm.IsManualOverrideActive();
        if (source == DisplayManager::CanvasSource::JETSON && manual_active) {
            // Under manual override by PC/phone, Jetson pixel writes are suppressed from modifying the active canvas.
            return 1;
        }
        if (source == DisplayManager::CanvasSource::MANUAL_USER) {
            dm.SetManualOverride(true);
        }
        auto* auto_item = cJSON_GetObjectItemCaseSensitive(root, "auto_mode");
        if (auto_item && cJSON_IsTrue(auto_item) && (!manual_active || source == DisplayManager::CanvasSource::MANUAL_USER) && dm.GetMode() != DisplayMode::PIXEL_CANVAS) {
            dm.SetMode(static_cast<uint8_t>(DisplayMode::PIXEL_CANVAS));
        }
        dm.SetCanvasSource(source);
        dm.SetCanvasPixel((int)x,(int)y,ColorRGB((uint8_t)a,(uint8_t)b,(uint8_t)c));
        return 1;
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
        bool manual_active = dm.IsManualOverrideActive();
        if (source == DisplayManager::CanvasSource::JETSON && manual_active) {
            // Under manual override by PC/phone, Jetson canvas frames are suppressed from modifying the active canvas.
            return 1;
        }
        if (source == DisplayManager::CanvasSource::MANUAL_USER) {
            dm.SetManualOverride(true);
        }
        auto* auto_item = cJSON_GetObjectItemCaseSensitive(root, "auto_mode");
        if (auto_item && cJSON_IsTrue(auto_item) && (!manual_active || source == DisplayManager::CanvasSource::MANUAL_USER) && dm.GetMode() != DisplayMode::PIXEL_CANVAS) {
            dm.SetMode(static_cast<uint8_t>(DisplayMode::PIXEL_CANVAS));
        }
        dm.SetCanvasSource(source);
        dm.SetCanvasFrame(colors);
        return 1;
    }
    if (!strcmp(cmd, "canvas_chunk")) {
        auto* frame_item = cJSON_GetObjectItemCaseSensitive(root, "frame_id");
        if (!frame_item) frame_item = cJSON_GetObjectItemCaseSensitive(root, "frame");
        auto* chunk_item = cJSON_GetObjectItemCaseSensitive(root, "chunk_idx");
        if (!chunk_item) chunk_item = cJSON_GetObjectItemCaseSensitive(root, "chunk");
        auto* total_item = cJSON_GetObjectItemCaseSensitive(root, "total_chunks");
        if (!total_item) total_item = cJSON_GetObjectItemCaseSensitive(root, "total");
        auto* offset_item = cJSON_GetObjectItemCaseSensitive(root, "offset");
        auto* hex_item = cJSON_GetObjectItemCaseSensitive(root, "hex");
        auto* crc_item = cJSON_GetObjectItemCaseSensitive(root, "crc");
        auto* commit_item = cJSON_GetObjectItemCaseSensitive(root, "commit");
        auto* auto_item = cJSON_GetObjectItemCaseSensitive(root, "auto_mode");

        if (!frame_item || !cJSON_IsNumber(frame_item) ||
            !offset_item || !cJSON_IsNumber(offset_item) ||
            !hex_item || !cJSON_IsString(hex_item)) {
            return 0;
        }

        uint16_t frame_id = (uint16_t)frame_item->valueint;
        uint16_t chunk_idx = chunk_item ? (uint16_t)chunk_item->valueint : 0;
        uint16_t total_chunks = total_item ? (uint16_t)total_item->valueint : 1;
        uint16_t offset = (uint16_t)offset_item->valueint;
        const char* hex_str = hex_item->valuestring;
        size_t hex_len = strlen(hex_str);
        if (hex_len == 0 || (hex_len % 2) != 0 || (hex_len / 2 > 384) || (hex_len / 2 + offset > 768)) {
            return 0;
        }
        if (total_chunks == 0 || total_chunks > 16 || chunk_idx >= total_chunks) {
            return 0;
        }

        size_t byte_len = hex_len / 2;
        uint8_t chunk_bytes[384];
        if (byte_len > sizeof(chunk_bytes)) return 0;

        for (size_t i = 0; i < byte_len; ++i) {
            int h1 = digit(hex_str[i * 2]);
            int h2 = digit(hex_str[i * 2 + 1]);
            if (h1 < 0 || h2 < 0) return 0;
            chunk_bytes[i] = (uint8_t)(h1 * 16 + h2);
        }

        uint16_t expected_crc = (crc_item && cJSON_IsNumber(crc_item)) ? (uint16_t)crc_item->valueint : 0;
        bool commit_now = commit_item ? cJSON_IsTrue(commit_item) : false;
        bool auto_mode = auto_item ? cJSON_IsTrue(auto_item) : true;

        auto res = canvas::CanvasAssembler::GetInstance().FeedChunk(
            frame_id, chunk_idx, total_chunks, offset, chunk_bytes, byte_len,
            expected_crc, commit_now, auto_mode
        );
        return res.success ? 1 : 0;
    }
    if (!strcmp(cmd, "clear_canvas") || !strcmp(cmd, "canvas_clear")) {
        bool manual_active = dm.IsManualOverrideActive();
        if (source == DisplayManager::CanvasSource::JETSON && manual_active) {
            // Jetson clear suppressed when manual override active
            return 1;
        }
        if (source == DisplayManager::CanvasSource::MANUAL_USER) {
            dm.SetManualOverride(true);
        }
        auto* auto_item = cJSON_GetObjectItemCaseSensitive(root, "auto_mode");
        bool auto_mode = auto_item ? cJSON_IsTrue(auto_item) : false;
        canvas::CanvasAssembler::GetInstance().Clear(0, 0, 0, auto_mode);
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
