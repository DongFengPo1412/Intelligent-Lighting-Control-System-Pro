const fs = require('fs');
const vm = require('vm');
const path = require('path');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..');
const codeTransport = fs.readFileSync(path.join(ROOT, 'pc-agent-vision/web_app/arcade_transport.js'), 'utf8');
const codePaired = fs.readFileSync(path.join(ROOT, 'pc-agent-vision/web_app/paired_http.js'), 'utf8');
const codeApp = fs.readFileSync(path.join(ROOT, 'pc-agent-vision/web_app/app.js'), 'utf8');

function createEnvironment(options = {}) {
  const elements = {};
  const capturedRequests = [];
  const eventListeners = {};
  const envObj = { elements, capturedRequests, eventListeners, fetchHook: options.fetchHook || null };

  function getEl(id) {
    if (!elements[id]) {
      elements[id] = {
        id,
        value: id === 'cameraSource' ? (options.cameraSource || 'phone') : (id === 'visionMode' ? 'pet' : '0'),
        style: { setProperty: () => {} },
        getContext: () => ({
          fillRect: () => {},
          clearRect: () => {},
          beginPath: () => {},
          arc: () => {},
          fill: () => {},
          stroke: () => {},
          drawImage: () => {},
          getImageData: () => ({ data: new Uint8Array(256 * 4) }),
          putImageData: () => {},
        }),
        appendChild: () => {},
        append: () => {},
        replaceChildren: () => {},
        querySelectorAll: () => [],
        querySelector: () => null,
        classList: { add: () => {}, remove: () => {}, toggle: () => {}, contains: () => false },
        setAttribute: () => {},
        removeAttribute: () => {},
        hasAttribute: () => false,
        dataset: {},
        textContent: '',
        disabled: false,
        play: () => Promise.resolve(),
        pause: () => {},
        addEventListener: (event, fn) => {
          eventListeners[id + ':' + event] = (e = {}) => fn({ currentTarget: elements[id], preventDefault: () => {}, ...e });
        },
        removeEventListener: () => {},
      };
    }
    return elements[id];
  }

  const mockWindow = {
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
    scrollTo: () => {},
    location: { hash: '', protocol: 'http:', host: 'localhost:8080', pathname: '/' },
    history: { replaceState: () => {}, pushState: () => {} },
    localStorage: { getItem: () => 'test_token', setItem: () => {} },
    sessionStorage: { getItem: () => 'test_token', setItem: () => {} },
    setTimeout: (fn, ms) => 1,
    clearTimeout: () => {},
    setInterval: (fn, ms) => 1,
    clearInterval: () => {},
    fetch: async (url, opts = {}) => {
      const body = opts.body ? JSON.parse(opts.body) : {};
      capturedRequests.push({ url, method: opts.method || 'GET', body });
      if (envObj.fetchHook) {
        const hookRes = await envObj.fetchHook(url, opts, body);
        if (hookRes !== undefined) return hookRes;
      }
      if (url.includes('/api/pro/vision')) {
        if (body.enabled === true) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              running: true,
              source: body.source,
              mode: body.mode,
              session_id: options.nextSessionId || 'remote_sess_999'
            })
          };
        } else {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              running: false,
              source: 'none',
              session_id: null
            })
          };
        }
      }
      return { ok: true, status: 200, json: async () => ({ status: 'ok' }), text: async () => 'ok' };
    },
    navigator: {
      userAgent: 'test-agent',
      mediaDevices: options.mediaDevices !== undefined ? options.mediaDevices : {
        getUserMedia: async () => {
          if (options.userMediaThrows) throw new Error(options.userMediaThrows);
          return {
            getTracks: () => [{ stop: () => {} }],
          };
        }
      }
    },
    AmadeusNative: options.AmadeusNative !== undefined ? options.AmadeusNative : null,
    console: console,
  };

  const mockDoc = {
    body: getEl('body'),
    getElementById: (id) => getEl(id),
    addEventListener: () => {},
    removeEventListener: () => {},
    createElement: () => getEl('canvas'),
    querySelectorAll: () => [],
    querySelector: () => null,
    hidden: false,
  };

  mockWindow.document = mockDoc;
  mockWindow.window = mockWindow;

  const context = {
    ...mockWindow,
    AbortController: global.AbortController,
    Event: class Event { constructor(type) { this.type = type; } },
    CustomEvent: class CustomEvent { constructor(type, detail) { this.type = type; this.detail = detail; } },
  };

  vm.runInNewContext(codeTransport, context);
  if (context.window.ArcadeTransport) context.ArcadeTransport = context.window.ArcadeTransport;
  if (context.window.DeviceHealth) context.DeviceHealth = context.window.DeviceHealth;
  vm.runInNewContext(codePaired, context);
  vm.runInNewContext(codeApp, context);

  envObj.context = context;
  return envObj;
}

async function runTests() {
  console.log("=== Running Phone Camera Request Lifecycle Tests ===");

  // 1. Phone Camera Normal Start -> Stop Button Click
  {
    console.log("Test 1: Normal Phone Camera Start and Stop Button Click...");
    const env = createEnvironment({
      cameraSource: 'phone',
      nextSessionId: 'sess_phone_001',
    });

    const visionStartBtn = env.eventListeners['visionStart:click'];
    const visionStopBtn = env.eventListeners['visionStop:click'];
    assert(visionStartBtn, "visionStart:click listener must exist");
    assert(visionStopBtn, "visionStop:click listener must exist");

    await visionStartBtn({ preventDefault: () => {} });
    const startReqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(startReqs.length, 1, "Only 1 start request to /api/pro/vision");
    assert.strictEqual(startReqs[0].body.enabled, true);
    assert.strictEqual(startReqs[0].body.source, 'remote');

    // Click stop button
    env.capturedRequests.length = 0; // reset capture
    await visionStopBtn({ preventDefault: () => {} });
    const stopReqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));

    // MUST send exactly 1 stop request with session_id, and MUST NOT send global stop!
    assert.strictEqual(stopReqs.length, 1, "Stopping phone camera must send exactly 1 request to /api/pro/vision");
    assert.strictEqual(stopReqs[0].body.enabled, false);
    assert.strictEqual(stopReqs[0].body.source, 'remote');
    assert.strictEqual(stopReqs[0].body.session_id, 'sess_phone_001', "Must specify session_id");

    const globalStops = stopReqs.filter(r => r.body.enabled === false && !r.body.session_id);
    assert.strictEqual(globalStops.length, 0, "No global stop request must be sent!");
    assert.strictEqual(env.elements['visionBadge'].textContent, '未启用', "Badge must show '未启用' on successful stop");
    console.log("  -> PASS: Exactly 1 stop request with session_id sent; 0 global stops.");
  }

  // 2. Native Camera Start Failure (Permission Denied / Failure)
  {
    console.log("Test 2: Native Android Camera startFrontCamera returns false...");
    const env = createEnvironment({
      cameraSource: 'phone',
      nextSessionId: 'sess_phone_native_fail',
      AmadeusNative: {
        hasNativeCamera: () => true,
        startFrontCamera: () => false, // fails
        stopFrontCamera: () => {},
      }
    });

    const visionStartBtn = env.eventListeners['visionStart:click'];
    await visionStartBtn({ preventDefault: () => {} });

    const reqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(reqs.length, 2, "Must have 1 start request and 1 rollback stop request");
    assert.strictEqual(reqs[0].body.enabled, true);
    assert.strictEqual(reqs[1].body.enabled, false);
    assert.strictEqual(reqs[1].body.source, 'remote');
    assert.strictEqual(reqs[1].body.session_id, 'sess_phone_native_fail');

    const globalStops = reqs.filter(r => r.body.enabled === false && !r.body.session_id);
    assert.strictEqual(globalStops.length, 0, "No global stop request sent during native failure rollback");
    console.log("  -> PASS: Session safely revoked on native camera failure without global stop.");
  }

  // 3. WebRTC Permission Denied (NotAllowedError)
  {
    console.log("Test 3: WebRTC getUserMedia permission denied...");
    const env = createEnvironment({
      cameraSource: 'phone',
      nextSessionId: 'sess_phone_webrtc_denied',
      userMediaThrows: 'NotAllowedError: Permission denied',
    });

    const visionStartBtn = env.eventListeners['visionStart:click'];
    await visionStartBtn({ preventDefault: () => {} });

    const reqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(reqs.length, 2, "Must have 1 start request and 1 rollback stop request");
    assert.strictEqual(reqs[0].body.enabled, true);
    assert.strictEqual(reqs[1].body.enabled, false);
    assert.strictEqual(reqs[1].body.source, 'remote');
    assert.strictEqual(reqs[1].body.session_id, 'sess_phone_webrtc_denied');

    const globalStops = reqs.filter(r => r.body.enabled === false && !r.body.session_id);
    assert.strictEqual(globalStops.length, 0, "No global stop request sent during permission denial");
    console.log("  -> PASS: Session safely revoked on getUserMedia denial without global stop.");
  }

  // 4. Missing WebRTC Environment
  {
    console.log("Test 4: Missing WebRTC environment (navigator.mediaDevices missing)...");
    const env = createEnvironment({
      cameraSource: 'phone',
      nextSessionId: 'sess_phone_missing_webrtc',
      mediaDevices: null,
    });

    const visionStartBtn = env.eventListeners['visionStart:click'];
    await visionStartBtn({ preventDefault: () => {} });

    const reqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(reqs.length, 2, "Must have 1 start request and 1 rollback stop request");
    assert.strictEqual(reqs[0].body.enabled, true);
    assert.strictEqual(reqs[1].body.enabled, false);
    assert.strictEqual(reqs[1].body.source, 'remote');
    assert.strictEqual(reqs[1].body.session_id, 'sess_phone_missing_webrtc');

    const globalStops = reqs.filter(r => r.body.enabled === false && !r.body.session_id);
    assert.strictEqual(globalStops.length, 0, "No global stop request sent when WebRTC is missing");
    console.log("  -> PASS: Session safely revoked when WebRTC is missing without global stop.");
  }

  // 5. PC Camera Started -> Dropdown changed to phone -> Stop Button Click
  {
    console.log("Test 5: PC Camera Started -> cameraSource changed to phone -> Stop Button Click...");
    const env = createEnvironment({
      cameraSource: 'pc',
    });

    const visionStartBtn = env.eventListeners['visionStart:click'];
    const visionStopBtn = env.eventListeners['visionStop:click'];
    assert(visionStartBtn, "visionStart:click listener must exist");
    assert(visionStopBtn, "visionStop:click listener must exist");

    // 1) Start PC Camera
    await visionStartBtn({ preventDefault: () => {} });
    const startReqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(startReqs.length, 1, "Must send 1 start request for PC camera");
    assert.strictEqual(startReqs[0].body.enabled, true);
    assert.strictEqual(startReqs[0].body.source, 'camera');
    assert.strictEqual(env.elements['visionBadge'].textContent, '运行中', "Badge must show '运行中'");

    // 2) Change dropdown selection to phone
    env.elements['cameraSource'].value = 'phone';

    // 3) Click stop button
    env.capturedRequests.length = 0; // reset capture
    await visionStopBtn({ preventDefault: () => {} });

    // 4) Assert PC stop request is sent and UI updated to '未启用'
    const stopReqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(stopReqs.length, 1, "Must send exactly 1 stop request for PC camera");
    assert.strictEqual(stopReqs[0].body.enabled, false);
    assert.strictEqual(stopReqs[0].body.source, 'camera', "Must send source: camera");
    assert.strictEqual(stopReqs[0].body.session_id, undefined, "PC stop must not send remote session_id");

    assert.strictEqual(env.elements['visionBadge'].textContent, '未启用', "Badge must be updated to '未启用' after backend confirmation");
    console.log("  -> PASS: Changing dropdown to phone did not misroute stop request; PC camera stopped cleanly and badge shows '未启用'.");
  }

  // 6. Network error during phone stop -> notice "停止未确认" -> retry retains session_id without falling back to PC
  {
    console.log("Test 6: Phone stop network outage -> notice '停止未确认' -> retry retains session_id without falling back to PC...");
    const env = createEnvironment({
      cameraSource: 'phone',
      nextSessionId: 'sess_phone_net_outage',
    });

    const visionStartBtn = env.eventListeners['visionStart:click'];
    const visionStopBtn = env.eventListeners['visionStop:click'];

    // Start phone camera
    await visionStartBtn({ preventDefault: () => {} });
    assert.strictEqual(env.elements['visionBadge'].textContent, '运行中');

    // Simulate network error on stop
    env.capturedRequests.length = 0;
    env.fetchHook = async (url, opts, body) => {
      if (url.includes('/api/pro/vision') && body.enabled === false) {
        throw new TypeError('Failed to fetch (network down)');
      }
    };

    // Click stop button during network outage
    await visionStopBtn({ preventDefault: () => {} });

    // Assert: Notice displays "停止未确认", badge shows "停止未确认"
    assert(env.elements['toast'].textContent.includes('停止未确认'), "Toast must indicate '停止未确认'");
    assert.strictEqual(env.elements['visionBadge'].textContent, '停止未确认', "Badge must show '停止未确认'");

    // Network recovers
    env.fetchHook = null;
    env.capturedRequests.length = 0;

    // Click stop button again (Retry)
    await visionStopBtn({ preventDefault: () => {} });

    // Assert: Retry request MUST be targeted remote stop with original session_id!
    const retryReqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(retryReqs.length, 1, "Must send exactly 1 stop request on retry");
    assert.strictEqual(retryReqs[0].body.enabled, false);
    assert.strictEqual(retryReqs[0].body.source, 'remote', "Retry MUST NOT fall back to source: camera");
    assert.strictEqual(retryReqs[0].body.session_id, 'sess_phone_net_outage', "Retry MUST use preserved session_id");
    assert.strictEqual(env.elements['visionBadge'].textContent, '未启用', "Badge must update to '未启用' upon backend confirmation");
    console.log("  -> PASS: Network outage properly handled: notice shown, session_id preserved, retry remained remote stop.");
  }

  // 7. Backend returns HTTP 200 with running: true on stop -> retry retains session_id
  {
    console.log("Test 7: Phone stop returns HTTP 200 running: true -> badge shows '运行中' -> retry retains session_id without falling back to PC...");
    const env = createEnvironment({
      cameraSource: 'phone',
      nextSessionId: 'sess_phone_still_running',
    });

    const visionStartBtn = env.eventListeners['visionStart:click'];
    const visionStopBtn = env.eventListeners['visionStop:click'];

    // Start phone camera
    await visionStartBtn({ preventDefault: () => {} });
    assert.strictEqual(env.elements['visionBadge'].textContent, '运行中');

    // Backend returns running: true on stop
    env.capturedRequests.length = 0;
    env.fetchHook = async (url, opts, body) => {
      if (url.includes('/api/pro/vision') && body.enabled === false) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            running: true,
            source: 'remote',
            mode: 'pet',
            session_id: 'sess_phone_still_running'
          })
        };
      }
    };

    // Click stop button
    await visionStopBtn({ preventDefault: () => {} });

    // Assert: Badge shows actual state '运行中', notice indicates '停止未确认'
    assert.strictEqual(env.elements['visionBadge'].textContent, '运行中', "Badge must show actual state '运行中'");
    assert(env.elements['toast'].textContent.includes('停止未确认'), "Toast must indicate '停止未确认'");

    // Backend stop now succeeds (running: false)
    env.fetchHook = null;
    env.capturedRequests.length = 0;

    // Click stop button again (Retry)
    await visionStopBtn({ preventDefault: () => {} });

    // Assert: Retry request MUST be targeted remote stop with original session_id!
    const retryReqs = env.capturedRequests.filter(r => r.url.includes('/api/pro/vision'));
    assert.strictEqual(retryReqs.length, 1, "Must send exactly 1 stop request on retry");
    assert.strictEqual(retryReqs[0].body.enabled, false);
    assert.strictEqual(retryReqs[0].body.source, 'remote', "Retry MUST NOT fall back to source: camera");
    assert.strictEqual(retryReqs[0].body.session_id, 'sess_phone_still_running', "Retry MUST use preserved session_id");
    assert.strictEqual(env.elements['visionBadge'].textContent, '未启用', "Badge must update to '未启用' upon backend confirmation");
    console.log("  -> PASS: Backend still running properly handled: actual state displayed, session_id preserved, retry remained remote stop.");
  }

  console.log("ALL 7 JS VISION CAMERA LIFECYCLE TESTS PASSED!");
}

runTests().catch(err => {
  console.error("Test failed:", err);
  process.exit(1);
});
