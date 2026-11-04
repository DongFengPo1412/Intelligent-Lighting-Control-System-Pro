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
    if (!strcmp(a->valuestring,"config")) {
        auto enabled=cJSON_GetObjectItemCaseSensitive(root,"sound_enabled");
        auto volume=cJSON_GetObjectItemCaseSensitive(root,"sound_volume");
        auto difficulty=cJSON_GetObjectItemCaseSensitive(root,"difficulty");
        return cJSON_IsBool(enabled) && Integer(volume,0,100) && (!difficulty || Integer(difficulty,0,2));
    }
    if (!strcmp(a->valuestring, "players"))
        return Integer(cJSON_GetObjectItemCaseSensitive(root, "count"), 1, 2);
    if (!strcmp(a->valuestring, "select")) {
        cJSON* id = cJSON_GetObjectItemCaseSensitive(root, "game_id");
        return Integer(id, 1, 100) && (id->valueint == 1 || id->valueint == 2 || id->valueint == 3 || id->valueint == 4 || id->valueint == 5 || id->valueint == 6 || id->valueint == 7 || id->valueint == 8 || id->valueint == 9 || id->valueint == 10 || id->valueint == 11 || id->valueint == 12 || id->valueint == 13 || id->valueint == 14 || id->valueint == 15 || id->valueint == 16 || id->valueint == 17 || id->valueint == 18 || id->valueint == 19 || id->valueint == 20 || id->valueint == 21 || id->valueint == 22 || id->valueint == 23 || id->valueint == 24 || id->valueint == 25 || id->valueint == 26 || id->valueint == 27 || id->valueint == 28 || id->valueint == 29 || id->valueint == 30 || id->valueint == 31 || id->valueint == 32 || id->valueint == 33 || id->valueint == 34 || id->valueint == 35 || id->valueint == 36 || id->valueint == 37 || id->valueint == 38 || id->valueint == 39 || id->valueint == 40 || id->valueint == 41 || id->valueint == 42 || id->valueint == 43 || id->valueint == 44 || id->valueint == 45 || id->valueint == 46 || id->valueint == 47 || id->valueint == 48 || id->valueint == 49 || id->valueint == 50 || id->valueint == 51 || id->valueint == 52 || id->valueint == 53 || id->valueint == 54 || id->valueint == 55 || id->valueint == 56 || id->valueint == 57 || id->valueint == 58 || id->valueint == 62 || id->valueint == 63 || id->valueint == 64 || id->valueint == 65 || id->valueint == 66 || id->valueint == 67 || id->valueint == 72 || id->valueint == 73 || id->valueint == 74 || id->valueint == 75 || id->valueint == 76 || id->valueint == 81 || id->valueint == 83 || id->valueint == 84 || id->valueint == 85 || id->valueint == 86 || id->valueint == 87 || id->valueint == 88 || id->valueint == 92 || id->valueint == 93 || id->valueint == 94 || id->valueint == 95 || id->valueint == 97 || id->valueint == 98);
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
