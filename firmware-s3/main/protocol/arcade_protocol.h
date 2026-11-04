#pragma once
#include <cJSON.h>
#include <string.h>
#include <stdint.h>

namespace arcade_protocol {
inline bool Integer(cJSON* value, int minimum, int maximum) {
    return cJSON_IsNumber(value) && value->valuedouble == value->valueint &&
        value->valueint >= minimum && value->valueint <= maximum;
}
inline bool Valid(cJSON* root) {
    cJSON* a = cJSON_GetObjectItemCaseSensitive(root, "action");
    if (!cJSON_IsString(a)) return false;
    if (!strcmp(a->valuestring, "select")) {
        cJSON* id = cJSON_GetObjectItemCaseSensitive(root, "game_id");
        if (!Integer(id, 1, 255)) return false;
        const int ids[] = {1,9,10,20,21,26,33,34,38,41,54,74,97};
        for (int registered : ids) if (id->valueint == registered) return true;
        return false;
    }
    if (!strcmp(a->valuestring, "input")) {
        return Integer(cJSON_GetObjectItemCaseSensitive(root, "down"), 0, 255) &&
               Integer(cJSON_GetObjectItemCaseSensitive(root, "pressed"), 0, 255);
    }
    const char* actions[] = {"start","pause","resume","reset","exit","heartbeat","status"};
    for (const char* action : actions) if (!strcmp(action, a->valuestring)) return true;
    return false;
}
}
