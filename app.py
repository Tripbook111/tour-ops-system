import hashlib
import json
import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

DATA_DIR = Path(os.getenv("APP_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"
WECOM_LOG_FILE = DATA_DIR / "wecom_callbacks.log"

WECOM_CALLBACK_TOKEN = os.getenv("WECOM_CALLBACK_TOKEN", "")
WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "")
WECOM_AGENT_ID = os.getenv("WECOM_AGENT_ID", "")
WECOM_AGENT_SECRET = os.getenv("WECOM_AGENT_SECRET", "")


def default_state():
    return {
        "activeId": "",
        "tours": []
    }


def read_state():
    if not STATE_FILE.exists():
        return default_state()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_state()


def write_state(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=DATA_DIR) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(STATE_FILE)


def wecom_signature_ok(signature, timestamp, nonce, echo_or_body):
    if not WECOM_CALLBACK_TOKEN:
        return True
    pieces = [WECOM_CALLBACK_TOKEN, timestamp or "", nonce or "", echo_or_body or ""]
    digest = hashlib.sha1("".join(sorted(pieces)).encode("utf-8")).hexdigest()
    return digest == signature


def get_wecom_access_token():
    import requests

    if not (WECOM_CORP_ID and WECOM_AGENT_SECRET):
        return None
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    response = requests.get(url, params={"corpid": WECOM_CORP_ID, "corpsecret": WECOM_AGENT_SECRET}, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get("access_token")


def send_wecom_text(content, to_user="@all"):
    import requests

    token = get_wecom_access_token()
    if not token or not WECOM_AGENT_ID:
        return {"ok": False, "error": "WeCom credentials are not configured"}
    url = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
    payload = {
        "touser": to_user,
        "msgtype": "text",
        "agentid": int(WECOM_AGENT_ID),
        "text": {"content": content},
        "safe": 0
    }
    response = requests.post(url, params={"access_token": token}, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


@app.get("/")
def health_check():
    return jsonify({
        "ok": True,
        "service": "tour-ops-system",
        "dashboard": "/dashboard"
    })


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html", initial_state=read_state())


@app.get("/api/state")
def api_get_state():
    return jsonify(read_state())


@app.post("/api/state")
def api_save_state():
    state = request.get_json(silent=True)
    if not isinstance(state, dict) or not isinstance(state.get("tours"), list):
        return jsonify({"ok": False, "error": "Invalid state payload"}), 400
    write_state(state)
    return jsonify({"ok": True})


@app.route("/api/wecom/callback", methods=["GET", "POST"])
def wecom_callback():
    signature = request.args.get("msg_signature") or request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    if request.method == "GET":
        echostr = request.args.get("echostr", "")
        if not wecom_signature_ok(signature, timestamp, nonce, echostr):
            return "invalid signature", 403
        return echostr

    body = request.get_data(as_text=True)
    if not wecom_signature_ok(signature, timestamp, nonce, body):
        return "invalid signature", 403
    WECOM_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with WECOM_LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(json.dumps({
            "timestamp": timestamp,
            "nonce": nonce,
            "query": request.args.to_dict(),
            "body": body
        }, ensure_ascii=False) + "\n")
    return "success"


@app.post("/api/wecom/send-test")
def api_send_test_message():
    payload = request.get_json(silent=True) or {}
    content = payload.get("content") or "报账系统测试消息：企业微信应用已连接。"
    to_user = payload.get("to_user") or "@all"
    try:
        return jsonify(send_wecom_text(content, to_user))
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 502


@app.get("/dashboard/")
def dashboard_slash():
    return redirect("/dashboard")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
