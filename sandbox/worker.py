# sandbox/worker.py
import os
import json
import time
import traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL = os.environ.get("TARGET_URL")
JOB_ID = os.environ.get("JOB_ID", "job-local")
ARTIFACT_DIR = Path("/artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

def write_bytes(name: str, b: bytes):
    p = ARTIFACT_DIR / name
    p.write_bytes(b)
    print(f"[worker] wrote {p}")

def write_text(name: str, s: str):
    p = ARTIFACT_DIR / name
    p.write_text(s, encoding="utf-8")
    print(f"[worker] wrote {p}")

def main():
    start = time.time()
    result = {
        "verdict": "unknown",
        "risk_score": 0,
        "summary": "",
        "evidence": []
    }
    try:
        if not TARGET_URL:
            raise ValueError("TARGET_URL env not set")
        print("[worker] target:", TARGET_URL)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            network_events = []
            console_events = []
            downloads = []

            def on_request(route):
                pass

            def on_request_event(req):
                network_events.append({
                    "url": req.url,
                    "method": req.method,
                    "resource_type": req.resource_type,
                    "headers": dict(req.headers)
                })

            page.on("request", on_request_event)
            page.on("console", lambda msg: console_events.append({"type": msg.type, "text": msg.text}))
            page.on("download", lambda d: downloads.append({"suggested_filename": d.suggested_filename, "url": d.url}))

            # inject JS hooks before navigation to detect getUserMedia and eval usage
            hook_js = """
            // Hook getUserMedia
            (function(){
              try {
                const orig = navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
                if (orig) {
                  navigator.mediaDevices.getUserMedia = function() {
                    window.__detected_getUserMedia = true;
                    return orig.apply(this, arguments);
                  };
                }
              } catch(e){}
              // Hook eval
              window.__orig_eval = window.eval;
              window.eval = function(s) {
                window.__detected_eval = (window.__detected_eval || 0) + 1;
                return window.__orig_eval(s);
              };
              // Hook document.write
              const origDocWrite = document.write;
              document.write = function(s) {
                window.__detected_document_write = true;
                return origDocWrite.apply(this, arguments);
              };
            })();
            """
            page.add_init_script(hook_js)

            # navigate
            page.goto(TARGET_URL, timeout=30000)
            # wait some time to let JS execute (POC)
            time.sleep(3)

            # capture artifacts
            html = page.content()
            write_text("dom.html", html)

            # screenshot
            try:
                screenshot_path = ARTIFACT_DIR / "screenshot.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception as e:
                print("screenshot failed:", e)

            # save network and consoles
            write_text("network.json", json.dumps(network_events, indent=2))
            write_text("console.json", json.dumps(console_events, indent=2))
            write_text("downloads.json", json.dumps(downloads, indent=2))

            # read detection flags from page
            try:
                detected_getUser = page.evaluate("() => !!window.__detected_getUserMedia")
                detected_eval = page.evaluate("() => window.__detected_eval || 0")
                detected_docwrite = page.evaluate("() => !!window.__detected_document_write")
            except Exception:
                detected_getUser = False
                detected_eval = 0
                detected_docwrite = False

            evidence = []
            if detected_getUser:
                evidence.append("Requested media devices (getUserMedia)")
            if detected_eval and detected_eval > 0:
                evidence.append(f"eval() called {detected_eval} times")
            if detected_docwrite:
                evidence.append("document.write used")

            # look for suspicious resource types or file extensions in network events
            suspicious_downloads = []
            for r in network_events:
                u = r.get("url","")
                if u.endswith(".exe") or u.endswith(".zip") or u.endswith(".apk") or u.endswith(".dll"):
                    suspicious_downloads.append(u)
            if suspicious_downloads:
                evidence.append("Detected direct download links: " + ", ".join(suspicious_downloads))

            # finalize risk scoring (very simple rules)
            score = 0
            if detected_getUser: score += 30
            if detected_eval and detected_eval > 0: score += 20
            if suspicious_downloads: score += 40
            # short page time as a small penalty
            if len(network_events) > 50: score += 5

            result["verdict"] = "malicious" if score >= 70 else ("suspicious" if score >=40 else "benign")
            result["risk_score"] = score
            result["summary"] = "; ".join(evidence) or "no suspicious behavior observed in dynamic run"
            result["evidence"] = evidence

            # write result
            write_text("result.json", json.dumps(result, indent=2))
            print("[worker] result written")
            browser.close()

    except Exception as e:
        tb = traceback.format_exc()
        write_text("worker.log", tb)
        print("[worker] exception:", e)
        result["verdict"] = "failed"
        result["summary"] = f"worker exception: {e}"
        write_text("result.json", json.dumps(result))
    finally:
        # sleep small time to ensure logs flushed
        time.sleep(0.5)

if __name__ == "__main__":
    main()