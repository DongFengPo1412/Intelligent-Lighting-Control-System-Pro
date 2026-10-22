option(PRO_MATRIX_DIAGNOSTIC "Build the opt-in 16x16 wiring test instead of the full application" OFF)
set(PRO_APP_MAIN "main.cc")
if(PRO_MATRIX_DIAGNOSTIC)
    set(PRO_APP_MAIN "../diagnostics/matrix_layout_main.cc")
endif()

idf_component_register(
    SRCS
        "${PRO_APP_MAIN}"
        "display/display_hal.cc"
        "display/effect_engine.cc"
        "display/game_engine.cc"
        "display/spectrum_engine.cc"
        "display/display_manager.cc"
        "display/board_led.cc"
        "protocol/command_dispatcher.cc"
        "protocol/wifi_manager.cc"
        "audio/audio_hal.cc"
    INCLUDE_DIRS
        "."
        "display"
        "protocol"
        "audio"
    REQUIRES
        esp_driver_gpio
        esp_driver_i2s
        led_strip
        esp_timer
        json
        esp_driver_usb_serial_jtag
        esp_ringbuf
        esp_wifi
        esp_event
        esp_netif
        nvs_flash
        lwip
    )
