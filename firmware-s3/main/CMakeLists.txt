option(PRO_MATRIX_DIAGNOSTIC "Build the opt-in 16x16 wiring test instead of the full application" OFF)
option(PRO_HAIR_CALIBRATION "Build the opt-in hair color comparison instead of the full application" OFF)
option(PRO_MATRIX_SERPENTINE "Reverse odd rows for serpentine panels (current tested panel uses straight rows)" OFF)
if(PRO_MATRIX_DIAGNOSTIC AND PRO_HAIR_CALIBRATION)
    message(FATAL_ERROR "Select only one diagnostic application")
endif()
set(PRO_APP_MAIN "main.cc")
if(PRO_MATRIX_DIAGNOSTIC)
    set(PRO_APP_MAIN "../diagnostics/matrix_layout_main.cc")
endif()
if(PRO_HAIR_CALIBRATION)
    set(PRO_APP_MAIN "../diagnostics/hair_palette_main.cc")
endif()

idf_component_register(
    SRCS
        "${PRO_APP_MAIN}"
        "display/display_hal.cc"
        "display/effect_engine.cc"
        "display/game_engine.cc"
        "display/spectrum_engine.cc"
        "display/fingertip_tracker.cc"
        "display/interaction_engine.cc"
        "display/display_manager.cc"
        "display/board_led.cc"
        "display/mario_game.cpp"
        "display/arcade/arcade_manager.cpp"
        "display/arcade/arcade_result_screen.cpp"
        "display/arcade/arcade_score_store.cpp"
        "display/arcade/game_001_mario.cpp"
        "display/arcade/game_009_flappy_bird.cpp"
        "display/arcade/game_010_stack.cpp"
        "display/arcade/game_020_pong.cpp"
        "display/arcade/game_021_breakout.cpp"
        "display/arcade/game_026_space_invaders.cpp"
        "display/arcade/game_033_snake.cpp"
        "display/arcade/game_034_pacman.cpp"
        "display/arcade/game_038_bomberman.cpp"
        "display/arcade/game_041_tetris.cpp"
        "display/arcade/game_054_sokoban.cpp"
        "display/arcade/game_074_highway_racer.cpp"
        "display/arcade/game_097_frogger.cpp"
        "protocol/command_dispatcher.cc"
        "protocol/interaction_commands.cc"
        "protocol/network_audio.cc"
        "protocol/network_auth.cc"
        "protocol/wifi_manager.cc"
        "audio/audio_hal.cc"
    INCLUDE_DIRS
        "."
        "display"
        "display/arcade"
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
        mbedtls
        bootloader_support
    )

target_compile_definitions(${COMPONENT_LIB} PUBLIC
    PRO_MATRIX_SERPENTINE=$<BOOL:${PRO_MATRIX_SERPENTINE}>
)
