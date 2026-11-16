#pragma once
#include <stdint.h>
using esp_err_t = int;
using nvs_handle_t = unsigned;
#ifndef ESP_OK
#define ESP_OK 0
#endif
#ifndef ESP_FAIL
#define ESP_FAIL -1
#endif
constexpr int ESP_ERR_NVS_NOT_FOUND = 1;
constexpr int NVS_READONLY=0, NVS_READWRITE=1;
int nvs_open(const char*,int,nvs_handle_t*);
int nvs_get_u32(nvs_handle_t,const char*,uint32_t*);
int nvs_get_i32(nvs_handle_t,const char*,int32_t*);
int nvs_set_i32(nvs_handle_t,const char*,int32_t);
int nvs_set_u32(nvs_handle_t,const char*,uint32_t);
int nvs_commit(nvs_handle_t);
void nvs_close(nvs_handle_t);
inline const char* esp_err_to_name(int) { return "host injected error"; }
