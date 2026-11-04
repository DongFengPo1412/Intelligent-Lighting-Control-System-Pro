#include "phase_b3_probe.h"
static double b3_number(cJSON *item) {
    return cJSON_IsBool(item) ? double(cJSON_IsTrue(item)) : cJSON_GetNumberValue(item);
}
static void test_b3_rounds() {
    using namespace arcade;
    constexpr float dt = 16667.f / 1000000.f;
    auto path =
        std::filesystem::path(__FILE__).parent_path() / "fixtures/phase_b3_input_paths.json";
    std::ifstream input(path);
    assert(input);
    std::stringstream text;
    text << input.rdbuf();
    auto *root = cJSON_Parse(text.str().c_str());
    assert(root);
    auto *cases = cJSON_GetObjectItemCaseSensitive(root, "cases");
    int total = 0;
    auto &manager = ArcadeManager::GetInstance();
    cJSON *row = nullptr;
    cJSON_ArrayForEach(row, cases) {
        int id = cJSON_GetObjectItemCaseSensitive(row, "id")->valueint,
            level = cJSON_GetObjectItemCaseSensitive(row, "difficulty")->valueint;
        bool won =
            std::string(cJSON_GetObjectItemCaseSensitive(row, "outcome")->valuestring) == "win";
        assert(manager.SelectGame(id));
        auto *game = manager.current_game_;
        assert(game->SetDifficulty(level));
        game->Init();
        game->Start();
        game->Pause();
        game->Update(dt, KEY_A | KEY_RIGHT, KEY_A | KEY_RIGHT);
        assert(game->GetStatus().state == STATE_PAUSED);
        game->Resume();
        auto *checks = cJSON_GetObjectItemCaseSensitive(row, "checkpoints");
        int next = 0, step = 0;
        auto *check = cJSON_GetArrayItem(checks, next);
        cJSON *action = nullptr;
        auto *actions = cJSON_GetObjectItemCaseSensitive(row, "inputs");
        cJSON_ArrayForEach(action, actions) {
            int n = cJSON_GetArrayItem(action, 0)->valueint,
                down = cJSON_GetArrayItem(action, 1)->valueint,
                pressed = cJSON_GetArrayItem(action, 2)->valueint;
            for (int i = 0; i < n; ++i) {
                ++step;
                sound_now += 17;
                game->Update(dt, down, pressed);
                SoundEvent e;
                while (Sounds().Pop(e)) {
                }
                if (check && step == cJSON_GetArrayItem(check, 0)->valueint) {
                    auto st = game->GetStatus();
                    auto values = B3Probe::Read(game);
                    std::vector<double> actual = {double(st.state), double(st.score),
                                                  double(st.lives), double(st.progress)};
                    actual.insert(actual.end(), values.begin(), values.end());
                    assert(int(actual.size()) == cJSON_GetArraySize(check) - 1);
                    for (unsigned k = 0; k < actual.size(); ++k) {
                        auto *expected = cJSON_GetArrayItem(check, k + 1);
                        double goal = b3_number(expected);
                        double error = std::abs(actual[k] - goal);
                        double tolerance = k == 3 ? 1.0 : k < 3 ? 0 : 0.03;
                        // Circular target angle can wrap by one full revolution.
                        if (id == 12 && k == 4)
                            error = std::min(error, std::abs(error - 6.28318530718));
                        if (error > tolerance)
                            std::cerr << "B3 mismatch id=" << id << " tier=" << level
                                      << " step=" << step << " field=" << k
                                      << " actual=" << actual[k] << " expected=" << goal << "\n";
                        assert(error <= tolerance);
                    }
                    std::vector<uint8_t> frame(800, 0xa5);
                    game->Render(frame.data() + 16);
                    for (int b = 0; b < 16; ++b)
                        assert(frame[b] == 0xa5 && frame[784 + b] == 0xa5);
                    check = cJSON_GetArrayItem(checks, ++next);
                }
            }
        }
        assert(!check);
        assert(game->GetStatus().state == (won ? STATE_VICTORY : STATE_GAMEOVER));
        game->Reset();
        assert(game->GetStatus().state == STATE_TITLE);
        game->Start();
        assert(game->GetStatus().state == STATE_PLAYING);
        ++total;
    }
    cJSON_Delete(root);
    std::cout << "B3 production input-only wins/losses, three difficulties and cross-language "
                 "state checkpoints passed: "
              << total << " rounds\n";
}
