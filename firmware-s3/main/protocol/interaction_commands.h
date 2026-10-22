#pragma once
#include <cJSON.h>
class DisplayManager;
// -1: not this module; 0: malformed; 1: accepted. Validate before mutation.
int HandleInteractionCommand(const char* cmd,cJSON* root,DisplayManager& display);
