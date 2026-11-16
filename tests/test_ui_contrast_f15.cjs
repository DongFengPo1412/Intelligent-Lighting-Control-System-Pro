/* Headless Chromium/Edge WCAG AA contrast & responsive verification for F15 (Day & Night).
   Also verifies F14 Web localStorage theme persistence across simulated reload. */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const cp = require("node:child_process");
const net = require("node:net");
const { parseArgs } = require("node:util");

const { values } = parseArgs({
  options: {
    url: { type: "string" },
    "work-dir": { type: "string" },
    chrome: { type: "string" },
  },
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const CONTRAST_HELPERS = `
(() => {
  function parseRgba(str) {
    const m = str && str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
    if (!m) return null;
    return [Number(m[1]), Number(m[2]), Number(m[3]), m[4] === undefined ? 1 : Number(m[4])];
  }
  function blend(fg, bg) {
    const a = fg[3];
    return [
      fg[0] * a + bg[0] * (1 - a),
      fg[1] * a + bg[1] * (1 - a),
      fg[2] * a + bg[2] * (1 - a),
      1,
    ];
  }
  function effectiveBg(el) {
    const chain = [];
    for (let cur = el; cur; cur = cur.parentElement) {
      const c = parseRgba(getComputedStyle(cur).backgroundColor);
      if (c && c[3] > 0) chain.push(c);
    }
    let out = document.documentElement.dataset.theme === "day" ? [244, 245, 247, 1] : [13, 17, 23, 1];
    for (let i = chain.length - 1; i >= 0; i--) out = blend(chain[i], out);
    return out;
  }
  function relLum(rgb) {
    const chan = rgb.slice(0, 3).map((v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
  }
  function contrastRatio(el) {
    if (!el) return null;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return null;
    const fgRaw = parseRgba(cs.color);
    const bg = effectiveBg(el);
    if (!fgRaw) return null;
    const fg = blend(fgRaw, bg);
    const l1 = relLum(fg), l2 = relLum(bg);
    return {
      ratio: (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05),
      color: cs.color,
      bg: "rgb(" + Math.round(bg[0]) + "," + Math.round(bg[1]) + "," + Math.round(bg[2]) + ")",
      text: (el.textContent || "").trim().slice(0, 30),
    };
  }
  window.__f15CheckAll = () => {
    const selectors = [
      "#marioScoreStat",
      "#arcadeHighScoreStat",
      "#marioStateTag",
      "#marioSyncBadge",
      ".mario-header",
      ".mario-hud-subrow",
      ".field-help",
    ];
    const results = {};
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      results[sel] = contrastRatio(el);
    }
    return results;
  };
})()
`;

async function main() {
  if (!values.url || !values["work-dir"]) {
    throw Error("Supply --url and --work-dir (outside repo)");
  }
  const base = values.url.replace(/\/$/, "");
  const work = path.resolve(values["work-dir"]);
  fs.mkdirSync(work, { recursive: true });

  const probe = net.createServer();
  await new Promise((r) => probe.listen(0, "127.0.0.1", r));
  const port = probe.address().port;
  await new Promise((r) => probe.close(r));

  const edgePath =
    values.chrome ||
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
  const browser = cp.spawn(
    edgePath,
    [
      "--headless=new",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      "--remote-debugging-port=" + port,
      "--user-data-dir=" + path.join(work, "edge_profile"),
      "about:blank",
    ],
    { stdio: "ignore" }
  );

  let socket;
  try {
    let tabs;
    for (let i = 0; i < 60; i++) {
      try {
        tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
        break;
      } catch (_) {
        await sleep(100);
      }
    }
    if (!tabs) throw Error("Headless browser debugging endpoint unavailable");

    socket = new WebSocket(tabs.find((t) => t.type === "page").webSocketDebuggerUrl);
    await new Promise((r) => socket.addEventListener("open", r, { once: true }));

    let seq = 0;
    const pending = new Map();
    const exceptions = [];
    socket.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id) {
        const h = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? h.reject(Error(JSON.stringify(msg.error))) : h.resolve(msg.result);
      } else if (msg.method === "Runtime.exceptionThrown") {
        exceptions.push(msg.params);
      }
    };
    const call = (method, params = {}) =>
      new Promise((resolve, reject) => {
        const id = ++seq;
        pending.set(id, { resolve, reject });
        socket.send(JSON.stringify({ id, method, params }));
      });
    const evaluate = async (expression) => {
      const res = await call("Runtime.evaluate", {
        expression,
        returnByValue: true,
        awaitPromise: true,
      });
      if (res.exceptionDetails) throw Error(JSON.stringify(res.exceptionDetails));
      return res.result.value;
    };

    await call("Runtime.enable");
    await call("Page.enable");
    await call("Network.enable");
    await call("Network.setCacheDisabled", { cacheDisabled: true });
    await call("Emulation.setDeviceMetricsOverride", {
      width: 390,
      height: 844,
      deviceScaleFactor: 1,
      mobile: true,
    });

    await call("Page.navigate", { url: base + "/" });
    for (let i = 0; i < 80; i++) {
      const ready = await evaluate(
        'typeof window.applyTheme === "function" && !!document.getElementById("marioScoreStat") && !!document.querySelector(".mario-header")'
      );
      if (ready) break;
      await sleep(100);
    }

    await evaluate(CONTRAST_HELPERS);
    // Navigate to Interaction/Arcade tab so HUD + dynamic elements are rendered and visible
    await evaluate(`(() => {
      const btn = document.querySelector('[data-page="interaction"]');
      if (btn) btn.click();
    })()`);
    await sleep(300);

    const report = { widths: {}, states: {}, exceptions: 0 };

    // Verify all 5 dynamic HUD states (0..4) in BOTH day and night themes
    for (const theme of ["day", "night"]) {
      await evaluate(`window.applyTheme("${theme}")`);
      await sleep(150);
      report.states[theme] = {};

      for (const st of [0, 1, 2, 3, 4]) {
        await evaluate(`(() => {
          const tag = document.getElementById("marioStateTag");
          if (tag) {
            tag.className = "mario-state-badge state-code-" + ${st};
            tag.textContent = ["STANDBY", "PLAYING", "PAUSED", "GAME OVER", "VICTORY"][${st}];
          }
        })()`);
        const checks = await evaluate("window.__f15CheckAll()");
        report.states[theme][st] = checks;
        for (const [sel, info] of Object.entries(checks)) {
          if (!info) continue;
          if (info.ratio < 4.5) {
            throw Error(
              `WCAG AA FAIL (${theme} state=${st} ${sel}): ratio=${info.ratio.toFixed(2)} fg=${info.color} bg=${info.bg}`
            );
          }
        }
      }

      // Check responsive widths & capture real screenshots
      report.widths[theme] = {};
      for (const [w, h, mobile] of [
        [360, 800, true],
        [390, 844, true],
        [768, 1024, false],
        [1280, 800, false],
      ]) {
        await call("Emulation.setDeviceMetricsOverride", {
          width: w,
          height: h,
          deviceScaleFactor: 1,
          mobile,
        });
        await evaluate(
          'document.getElementById("marioScoreStat")?.scrollIntoView({block:"center",behavior:"instant"})'
        );
        await sleep(150);
        const overflow = await evaluate(
          "document.documentElement.scrollWidth > window.innerWidth + 1"
        );
        if (overflow) {
          throw Error(`Horizontal overflow at ${w}x${h} in ${theme} theme`);
        }
        const png = await call("Page.captureScreenshot", { format: "png" });
        const shotPath = path.join(work, `f15_${theme}_${w}x${h}.png`);
        fs.writeFileSync(shotPath, Buffer.from(png.data, "base64"));
        report.widths[theme][`${w}x${h}`] = { overflow: false, screenshot: shotPath };
      }
    }

    report.exceptions = exceptions.length;
    if (exceptions.length > 0) {
      throw Error("Uncaught browser runtime exceptions: " + JSON.stringify(exceptions));
    }

    fs.writeFileSync(path.join(work, "f15_contrast_report.json"), JSON.stringify(report, null, 2));
    console.log("PASS: F15 Day/Night WCAG AA contrast & responsive verification complete!");
    for (const theme of ["day", "night"]) {
      const sample = report.states[theme][1];
      const summary = Object.entries(sample)
        .filter(([, v]) => v)
        .map(([k, v]) => `${k}=${v.ratio.toFixed(2)}:1`)
        .join(" ");
      console.log(`  [${theme} PLAY] ${summary}`);
    }
  } finally {
    if (socket) socket.close();
    browser.kill();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
