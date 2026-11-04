#pragma once
#include "game_034_pacman.h"
#include <cstdlib>
#include <filesystem>
#include <set>
namespace arcade {
struct PhaseCProbe {
    static void CheckPelletReachability(const Game034Pacman &g) {
        bool seen[256]{};
        int queue[256], read = 0, write = 0;
        int start = int(std::round(g.pac_y_)) * 16 + int(std::round(g.pac_x_));
        queue[write++] = start;
        seen[start] = true;
        while (read < write) {
            int p = queue[read++], dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, -1};
            for (int d = 0; d < 4; ++d) {
                int x = p % 16 + dx[d], y = p / 16 + dy[d];
                if (y == 7) {
                    if (x < 0)
                        x = 15;
                    if (x > 15)
                        x = 0;
                }
                if (x < 0 || x >= 16 || y < 0 || y >= 16 || g.IsWall(x, y) || seen[y * 16 + x])
                    continue;
                assert(write < 256);
                seen[y * 16 + x] = true;
                queue[write++] = y * 16 + x;
            }
        }
        int pellets = 0;
        for (int y = 0; y < 16; ++y)
            for (int x = 0; x < 16; ++x)
                if (g.grid_[y][x] == 1 || g.grid_[y][x] == 2) {
                    ++pellets;
                    assert(seen[y * 16 + x]);
                }
        assert(pellets == g.total_dots_ && pellets == 119);
    }
};
} // namespace arcade
static void test_phase_c_directed() {
    using namespace arcade;
    auto &manager = ArcadeManager::GetInstance();
    Sounds().Configure(true, 25);
    SoundEvent event;
    while (Sounds().Pop(event)) {
    }
    assert(manager.SelectGame(80));
    auto *g = manager.current_game_;
    g->Init();
    g->Start();
    while (Sounds().Pop(event)) {
    }
    g->Update(.016667f, KEY_RIGHT, KEY_RIGHT);
    for (int i = 0; i < 3; ++i)
        g->Update(.016667f, KEY_RIGHT, 0);
    g->Update(.016667f, KEY_LEFT, KEY_LEFT);
    int turns = 0, collisions = 0;
    while (Sounds().Pop(event)) {
        if (event.kind == Sound::Action && event.game == 80) {
            ++turns;
            assert(event.detail == 1);
        }
    }
    assert(turns == 1);
    for (int i = 0; i < 240 && g->GetStatus().state == STATE_PLAYING; ++i) {
        g->Update(.016667f, KEY_RIGHT, 0);
        while (Sounds().Pop(event))
            collisions += event.game == 80 && event.kind == Sound::Collision;
    }
    assert(g->GetStatus().state == STATE_GAMEOVER && collisions == 1);
    assert(manager.SelectGame(34));
    manager.current_game_->Init();
    manager.current_game_->Start();
    PhaseCProbe::CheckPelletReachability(*static_cast<Game034Pacman *>(manager.current_game_));
    assert(manager.SelectGame(10));
    g = manager.current_game_;
    g->Init();
    g->Start();
    g->Update(.016667f, 0, KEY_A);
    auto stack_status = g->GetStatus();
    assert(stack_status.progress == (stack_status.score >= 25 ? 100 : stack_status.score * 4));
    assert(manager.SelectGame(1));
    g = manager.current_game_;
    g->Init();
    g->Start();
    g->Pause();
    assert(g->GetStatus().state == STATE_PAUSED);
    std::vector<uint8_t> before(768), after(768);
    g->Render(before.data());
    for (int i = 0; i < 150; ++i)
        g->Update(.016667f, KEY_RIGHT, KEY_RIGHT);
    g->Render(after.data());
    assert(before == after);
    g->Resume();
    assert(g->GetStatus().state == STATE_PLAYING);
    for (int i = 0; i < 18000 && g->GetStatus().state != STATE_GAMEOVER; ++i)
        g->Update(.016667f, KEY_RIGHT, 0);
    assert(g->GetStatus().state == STATE_GAMEOVER && g->GetStatus().lives == 0);
    assert(manager.SelectGame(100));
    auto *memory = static_cast<Game100MemoryMatch *>(manager.current_game_);
    memory->UseRandomSeeds();
    std::set<uint32_t> layouts;
    for (int i = 0; i < 20; ++i) {
        memory->Reset();
        layouts.insert(B3Probe::MemoryFingerprint(*memory));
    }
    assert(layouts.size() > 15);
    for (uint32_t seed : {0u, 1u, 42u, 0xffffffffu}) {
        memory->SetReplaySeed(seed);
        memory->Reset();
        auto first = B3Probe::MemoryFingerprint(*memory);
        memory->Start();
        assert(first == B3Probe::MemoryFingerprint(*memory));
    }
    memory->UseRandomSeeds();
    std::cout << "Phase C production directed Tron turn/hold/reverse/collision and fresh/seeded "
                 "Memory Match passed\n";
}
// Optional host-only capture. Paths come from test CLI; no firmware endpoint is added.
static void capture_phase_c() {
    const char *folder = std::getenv("PHASE_C_CAPTURE");
    if (!folder)
        return;
    auto out = std::filesystem::path(folder);
    std::filesystem::create_directories(out);
    std::ofstream csv(out / "frames.csv");
    csv << "id,phase,state,score,progress,file,source,nonzero_channels,control_type\n";
    auto base = std::filesystem::path(__FILE__).parent_path() / "fixtures";
    auto load = [&](const char *name) {
        std::ifstream f(base / name);
        std::stringstream s;
        s << f.rdbuf();
        return cJSON_Parse(s.str().c_str());
    };
    cJSON *b3 = load("phase_b3_input_paths.json"), *b2 = load("phase_b2_input_paths.json");
    auto *extra = load("phase_c_input_paths.json");
    assert(b3 && b2 && extra);
    auto find = [&](int id) {
        cJSON *fallback = nullptr;
        for (auto *root : {b3, b2, extra}) {
            cJSON *row = nullptr;
            cJSON_ArrayForEach(row, cJSON_GetObjectItemCaseSensitive(root, "cases")) {
                auto *outcome = cJSON_GetObjectItemCaseSensitive(row, "outcome");
                if (cJSON_GetObjectItemCaseSensitive(row, "id")->valueint == id &&
                    cJSON_GetObjectItemCaseSensitive(row, "difficulty")->valueint == 1) {
                    if (!outcome || std::string(outcome->valuestring) == "win")
                        return row;
                    if (!fallback)
                        fallback = row;
                }
            }
        }
        return fallback;
    };
    auto &manager = arcade::ArcadeManager::GetInstance();
    for (int id = 1; id <= 100; ++id) {
        assert(manager.SelectGame(id));
        auto *g = manager.current_game_;
        g->SetDifficulty(1);
        if (id == 100)
            static_cast<arcade::Game100MemoryMatch *>(g)->SetReplaySeed(0x100fa);
        g->Init();
        auto save = [&](const char *phase, const char *source) {
            std::vector<uint8_t> buf(800, 0xa5);
            g->Render(buf.data() + 16);
            for (int i = 0; i < 16; ++i)
                assert(buf[i] == 0xa5 && buf[784 + i] == 0xa5);
            char name[40];
            std::snprintf(name, sizeof(name), "%03d_%s.rgb", id, phase);
            std::ofstream f(out / name, std::ios::binary);
            f.write(reinterpret_cast<char *>(buf.data() + 16), 768);
            auto s = g->GetStatus();
            int nonzero = 0;
            for (int i = 16; i < 784; ++i)
                nonzero += buf[i] != 0;
            csv << id << ',' << phase << ',' << int(s.state) << ',' << s.score << ','
                << int(s.progress) << ',' << name << ',' << source << ',' << nonzero << ','
                << int(g->GetControlType()) << '\n';
        };
        save("title", "Reset");
        g->Start();
        save("play", "Start");
        for (int frame = 0; frame < 12; ++frame) {
            g->Update(16667.f / 1000000.f, 0, 0);
            if (frame % 2 == 0) {
                char phase[16];
                std::snprintf(phase, sizeof(phase), "anim%d", frame / 2);
                save(phase, "idle_real_updates");
            }
        }
        g->Init();
        g->Start();

        auto *witness = find(id);
        const char *source = witness ? "legal_input_witness" : "deterministic_exploratory_inputs";
        int step = 0;
        if (witness) {
            auto *inputs = cJSON_GetObjectItemCaseSensitive(witness, "inputs");
            cJSON *row = nullptr;
            cJSON_ArrayForEach(row, inputs) {
                int count = cJSON_GetArrayItem(row, 0)->valueint,
                    down = cJSON_GetArrayItem(row, 1)->valueint,
                    pressed = cJSON_GetArrayItem(row, 2)->valueint;
                for (int n = 0; n < count; ++n) {
                    g->Update(16667.f / 1000000.f, down, pressed);
                    ++step;
                    if (step ==
                            std::max(1,
                                     cJSON_GetObjectItemCaseSensitive(witness, "steps")->valueint /
                                         2) &&
                        g->GetStatus().state == 1)
                        save("play", source);
                    if (g->GetStatus().state >= 3)
                        break;
                }
                if (g->GetStatus().state >= 3)
                    break;
            }
        } else {
            uint32_t random = 0xc0ffeeu ^ unsigned(id);
            unsigned key = 0;
            for (step = 0; step < 18000 && g->GetStatus().state == 1; ++step) {
                if (step % 15 == 0) {
                    random = random * 1664525u + 1013904223u;
                    const unsigned keys[] = {1, 2, 4, 8, 16, 32, 18, 36};
                    key = keys[(random >> 16) % 8];
                }
                g->Update(16667.f / 1000000.f, key, step % 15 == 0 ? key : 0);
                if (step == 90 && g->GetStatus().state == 1)
                    save("play", source);
            }
        }
        auto state = g->GetStatus().state;
        if (state >= 3) {
            for (int n = 0; n < 60; ++n)
                g->Update(16667.f / 1000000.f, 0, 0);
            save("result", source);
        } else
            save("unfinished", source);
        if (id == 100)
            static_cast<arcade::Game100MemoryMatch *>(g)->UseRandomSeeds();
    }
    cJSON_Delete(b3);
    cJSON_Delete(b2);
    cJSON_Delete(extra);
    std::cout << "Phase C actual production renderer capture complete (unobserved terminals remain "
                 "unverified)\n";
}

// Exploratory all-game comparison reports mismatches; it never promotes these to certified wins.
static void audit_phase_c_observations() {
    const char *source = std::getenv("PHASE_C_OBSERVATIONS");
    const char *report = std::getenv("PHASE_C_COMPARISON");
    if (!source || !report)
        return;
    std::ifstream input(source);
    std::stringstream text;
    text << input.rdbuf();
    auto *root = cJSON_Parse(text.str().c_str());
    assert(root);
    std::ofstream csv(report);
    csv << "id,checkpoint_mismatches,first_mismatch_step,cpp_terminal,python_terminal,cpp_score,"
           "python_score,cpp_lives,python_lives,terminal_step_delta\n";
    auto &manager = arcade::ArcadeManager::GetInstance();
    cJSON *row = nullptr;
    int games = 0, divergent = 0;
    cJSON_ArrayForEach(row, cJSON_GetObjectItemCaseSensitive(root, "cases")) {
        int id = cJSON_GetObjectItemCaseSensitive(row, "id")->valueint;
        assert(manager.SelectGame(id));
        auto *g = manager.current_game_;
        g->SetDifficulty(1);
        if (id == 100)
            static_cast<arcade::Game100MemoryMatch *>(g)->SetReplaySeed(
                uint32_t(cJSON_GetObjectItemCaseSensitive(row, "seed")->valuedouble));
        g->Init();
        g->Start();
        auto *checks = cJSON_GetObjectItemCaseSensitive(row, "checkpoints");
        int check_index = 0, step = 0, mismatch = 0, first = -1;
        auto *check = cJSON_GetArrayItem(checks, 0);
        cJSON *action = nullptr;
        bool ended = false;
        cJSON_ArrayForEach(action, cJSON_GetObjectItemCaseSensitive(row, "inputs")) {
            int count = cJSON_GetArrayItem(action, 0)->valueint,
                down = cJSON_GetArrayItem(action, 1)->valueint,
                pressed = cJSON_GetArrayItem(action, 2)->valueint;
            for (int n = 0; n < count; ++n) {
                ++step;
                g->Update(16667.f / 1000000.f, down, pressed);
                auto status = g->GetStatus();
                if (check && cJSON_GetArrayItem(check, 0)->valueint == step) {
                    double actual[] = {double(status.state), double(status.score),
                                       double(status.lives), double(status.progress)};
                    bool different = false;
                    for (int k = 0; k < 4; ++k)
                        different |=
                            actual[k] != cJSON_GetNumberValue(cJSON_GetArrayItem(check, k + 1));
                    if (different) {
                        ++mismatch;
                        if (first < 0)
                            first = step;
                    }
                    check = cJSON_GetArrayItem(checks, ++check_index);
                }
                if (status.state >= 3) {
                    ended = true;
                    break;
                }
            }
            if (ended)
                break;
        }
        auto status = g->GetStatus();
        auto *expected = cJSON_GetObjectItemCaseSensitive(row, "terminal");
        auto number = [&](const char *key) {
            return cJSON_GetObjectItemCaseSensitive(expected, key)->valueint;
        };
        bool same = status.state == number("state") && status.score == unsigned(number("score")) &&
                    status.lives == number("lives");
        divergent += !same;
        ++games;
        csv << id << ',' << mismatch << ',' << first << ',' << int(status.state) << ','
            << number("state") << ',' << status.score << ',' << number("score") << ','
            << int(status.lives) << ',' << number("lives") << ','
            << step - cJSON_GetObjectItemCaseSensitive(row, "steps")->valueint << '\n';
        if (id == 100)
            static_cast<arcade::Game100MemoryMatch *>(g)->UseRandomSeeds();
    }
    cJSON_Delete(root);
    std::cout << "Phase C exploratory comparison: " << games << " games, " << divergent
              << " different terminal/score/lives (diagnostic, not certification)\n";
}
