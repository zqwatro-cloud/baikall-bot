import datetime
import re
import logging
import asyncio
import random
import string
import io
import os
import json
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, InputFile, LinkPreviewOptions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler
from supabase import create_client
from dotenv import load_dotenv

# ========== КОНФИГ ==========
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8752748803:AAFjS-NPp5Tard5EORpZm0u-eZYxHstIswI")
ADMIN_ID = 8919925477
PROVIDER_TOKEN = ""
PHOTO_URL = "https://files.catbox.moe/7t9fe7.png"
TON_WALLET = "UQBZtQCKRxk6UnEA_8G8sA99J3JxhA6F-ODCM5aLdAfdECfC"
SUPPORT_URL = "https://t.me/Intornational"
REPORT_LINK = "https://t.me/UPG24"
COOLDOWN_SECONDS = 600

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL и SUPABASE_KEY должны быть в .env!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== СТАРЫЕ ЭМОДЗИ ДЛЯ ТЕКСТА ==========
EMOJI_WELCOME = '<tg-emoji emoji-id="5343833386681148365">👋</tg-emoji>'
EMOJI_SEND = '<tg-emoji emoji-id="5341398363562613784">📤</tg-emoji>'
EMOJI_PROFILE = '<tg-emoji emoji-id="5420190552220018466">👤</tg-emoji>'

# ========== ПРЕМИУМ ЭМОДЗИ (ID) ДЛЯ КНОПОК ==========
CE_WELCOME = "5343833386681148365"
CE_SEND = "5341398363562613784"
CE_PROFILE = "5420190552220018466"
CE_SUPPORT = "5345957870779275438"
CE_CHANNEL = "5343685300503746875"
CE_ADMIN = "5341483949375920400"
CE_PROMO = "5422534908578933102"
CE_BUY = "5346312166926492985"
CE_STARS = "5343982937442390726"
CE_TON = "5420281734375707356"
CE_TON_EMOJI = "5420281734375707356"
CE_STARS_EMOJI = "5346330154249525539"
CE_OWN_SUB = "5424591515013915727"
CE_BACK = "5417978510918589566"
CE_CARD = "5346098281850112009"
CE_USER_CARD = "5422394647831948544"
CE_USER = "5420190552220018466"
CE_ID = "5420609912826794716"
CE_SHIELD = "5343571376496221357"
CE_CALENDAR = "5417897151353104327"
CE_BROADCAST = "5343908497069217137"
CE_DATABASE = "5341361744671448944"
CE_WHITELIST = "5341662856238638762"
CE_LOG = "5418273373308362070"
CE_GIVE_SUB = "5422707922746516794"
CE_TAKE_SUB = "5420365696691379451"
CE_NEXT = "5343926295413692748"
CE_CROSS = "5341290156156558003"
CE_CHECK = "5341684618837924738"
CE_WARN = "5341793857036132809"
CE_EXCL = "5344054710640872335"

# ========== ЛОГИ ==========
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%d.%m.%Y %H:%M:%S"))

file_handler = logging.FileHandler("bot.log", encoding="utf-8")
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%d.%m.%Y %H:%M:%S"))

logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

log = logging.getLogger("Baikall")
def log_event(msg): log.info(msg)
def log_warn(msg): log.warning(msg)
def log_err(msg): log.error(msg)

log_event("✅ Supabase подключён")

# ========== ФУНКЦИИ БД ==========
def normalize_username(username):
    return username.replace("@", "").strip().lower() if username else None

# ===== USERS =====
def get_all_users():
    try:
        res = supabase.table("users").select("*").execute()
        return [(u["user_id"], u["username"] or "NULL", u["end_date"] or "NULL") for u in res.data]
    except Exception as e:
        log_err(f"❌ get_all_users: {e}")
        return []

def get_user(user_id):
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if res.data:
            u = res.data[0]
            return (u["user_id"], u["username"] or "NULL", u["end_date"] or "NULL")
    except Exception as e:
        log_err(f"❌ get_user: {e}")
    return None

def get_user_by_username(username):
    username = normalize_username(username)
    if not username: return None
    try:
        res = supabase.table("users").select("*").eq("username", username).execute()
        if res.data:
            u = res.data[0]
            return (u["user_id"], u["username"] or "NULL", u["end_date"] or "NULL")
    except Exception as e:
        log_err(f"❌ get_user_by_username: {e}")
    return None

def add_user(user_id, username):
    username = normalize_username(username) or "NULL"
    existing = get_user(user_id)
    if existing:
        try:
            supabase.table("users").update({"username": username}).eq("user_id", user_id).execute()
        except Exception as e:
            log_err(f"❌ add_user update: {e}")
        return False
    try:
        supabase.table("users").insert({"user_id": user_id, "username": username, "end_date": "NULL"}).execute()
        log_event(f"👤 Новый юзер: {user_id} (@{username})")
    except Exception as e:
        log_err(f"❌ add_user insert: {e}")
    return True

def set_subscription(user_id, end_date):
    try:
        existing = get_user(user_id)
        if existing:
            supabase.table("users").update({"end_date": end_date}).eq("user_id", user_id).execute()
        else:
            supabase.table("users").insert({"user_id": user_id, "username": "NULL", "end_date": end_date}).execute()
        log_event(f"🛡 Подписка выдана {user_id} до {end_date}")
    except Exception as e:
        log_err(f"❌ set_subscription: {e}")

def remove_subscription(user_id):
    try:
        supabase.table("users").update({"end_date": "NULL"}).eq("user_id", user_id).execute()
        log_event(f"❌ Подписка забрана у {user_id}")
    except Exception as e:
        log_err(f"❌ remove_subscription: {e}")

def has_subscription(user_id):
    data = get_user(user_id)
    if data and data[2] and data[2] != "NULL":
        if data[2] == "forever": return True
        try: return datetime.datetime.fromisoformat(data[2]) > datetime.datetime.now()
        except: return False
    return False

# ===== COOLDOWN =====
def get_cooldown_end(user_id):
    try:
        res = supabase.table("cooldowns").select("*").eq("user_id", user_id).execute()
        if res.data:
            return datetime.datetime.fromisoformat(res.data[0]["end_time"])
    except Exception as e:
        log_err(f"❌ get_cooldown_end: {e}")
    return None

def set_cooldown(user_id, seconds):
    end = (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).isoformat()
    try:
        existing = get_cooldown_end(user_id)
        if existing:
            supabase.table("cooldowns").update({"end_time": end}).eq("user_id", user_id).execute()
        else:
            supabase.table("cooldowns").insert({"user_id": user_id, "end_time": end}).execute()
        log_event(f"⏳ Кулдаун поставлен юзеру {user_id}")
    except Exception as e:
        log_err(f"❌ set_cooldown: {e}")

def clear_cooldown(user_id):
    try:
        supabase.table("cooldowns").delete().eq("user_id", user_id).execute()
    except Exception as e:
        log_err(f"❌ clear_cooldown: {e}")

def get_all_active_cooldowns():
    try:
        res = supabase.table("cooldowns").select("*").execute()
        return [(c["user_id"], datetime.datetime.fromisoformat(c["end_time"])) for c in res.data]
    except Exception as e:
        log_err(f"❌ get_all_active_cooldowns: {e}")
        return []

def is_cooldown_off(user_id):
    try:
        res = supabase.table("cooldown_off").select("*").eq("user_id", user_id).execute()
        return len(res.data) > 0
    except Exception as e:
        log_err(f"❌ is_cooldown_off: {e}")
    return False

def set_cooldown_off(user_id, off):
    try:
        if off:
            existing = is_cooldown_off(user_id)
            if not existing:
                supabase.table("cooldown_off").insert({"user_id": user_id}).execute()
        else:
            supabase.table("cooldown_off").delete().eq("user_id", user_id).execute()
        log_event(f"⏳ Кулдаун {'ВЫКЛ' if off else 'ВКЛ'} для {user_id}")
    except Exception as e:
        log_err(f"❌ set_cooldown_off: {e}")

def cooldown_remaining_text(user_id):
    end = get_cooldown_end(user_id)
    if not end: return None, None
    now = datetime.datetime.now()
    if end <= now:
        return None, end
    delta = end - now
    total_sec = int(delta.total_seconds())
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins} мин {secs} сек", end

# ===== PAYMENTS =====
def add_payment(user_id, username, days, price, custom=False):
    username_display = f"@{username}" if username and username != "NULL" else f"id{user_id}"
    date = datetime.datetime.now().strftime("%d.%m.%Y")
    try:
        supabase.table("payments_stars").insert({
            "user_id": user_id, "username": username_display,
            "days": str(days), "price": int(price), "date": date,
            "is_custom": 1 if custom else 0
        }).execute()
        log_event(f"💰 Stars payment: {user_id} - {days} - {price}⭐")
    except Exception as e:
        log_err(f"❌ add_payment: {e}")

def add_ton_record(user_id, username, ton_amount, status="ожидает проверки", custom=False):
    username_display = f"@{username}" if username and username != "NULL" else f"id{user_id}"
    date = datetime.datetime.now().strftime("%d.%m.%Y")
    try:
        supabase.table("payments_ton").insert({
            "user_id": user_id, "username": username_display,
            "ton_amount": str(ton_amount), "date": date, "status": status,
            "is_custom": 1 if custom else 0
        }).execute()
        log_event(f"💎 TON record: {user_id} - {ton_amount} TON - {status}")
    except Exception as e:
        log_err(f"❌ add_ton_record: {e}")

def update_ton_status(user_id, ton_amount, new_status):
    try:
        res = supabase.table("payments_ton").select("*").eq("user_id", user_id).eq("ton_amount", str(ton_amount)).order("id", desc=True).limit(1).execute()
        if res.data:
            supabase.table("payments_ton").update({"status": new_status}).eq("id", res.data[0]["id"]).execute()
        log_event(f"💎 TON статус: {user_id} - {ton_amount} TON - {new_status}")
    except Exception as e:
        log_err(f"❌ update_ton_status: {e}")

def save_ton_pending(code, user_id, days_or_sec, price, term_text, is_custom=False):
    try:
        supabase.table("ton_pending").insert({
            "code": code, "user_id": user_id, "days_or_sec": str(days_or_sec),
            "price": str(price), "term_text": term_text, "is_custom": 1 if is_custom else 0
        }).execute()
        log_event(f"💎 TON pending: code={code}, user={user_id}")
    except Exception as e:
        log_err(f"❌ save_ton_pending: {e}")

def get_ton_pending(code):
    try:
        res = supabase.table("ton_pending").select("*").eq("code", code).execute()
        if res.data:
            p = res.data[0]
            return {
                "code": p["code"], "user_id": p["user_id"],
                "days_or_sec": p["days_or_sec"], "price": p["price"],
                "term_text": p["term_text"], "is_custom": p["is_custom"] == 1
            }
    except Exception as e:
        log_err(f"❌ get_ton_pending: {e}")
    return None

def remove_ton_pending(code):
    try:
        supabase.table("ton_pending").delete().eq("code", code).execute()
    except Exception as e:
        log_err(f"❌ remove_ton_pending: {e}")

# ===== WHITELIST =====
def get_whitelist():
    try:
        res = supabase.table("whitelist").select("*").execute()
        return [(w["username"], w["added_at"] or "") for w in res.data]
    except Exception as e:
        log_err(f"❌ get_whitelist: {e}")
        return []

def add_to_whitelist(username):
    username = normalize_username(username)
    if not username: return
    try:
        existing = supabase.table("whitelist").select("*").eq("username", username).execute()
        if not existing.data:
            supabase.table("whitelist").insert({"username": username, "added_at": datetime.datetime.now().isoformat()}).execute()
        log_event(f"⬜ В вайт-лист добавлен @{username}")
    except Exception as e:
        log_err(f"❌ add_to_whitelist: {e}")

def remove_from_whitelist(username):
    username = normalize_username(username)
    try:
        supabase.table("whitelist").delete().eq("username", username).execute()
        log_event(f"⬜ Из вайт-листа удалён @{username}")
    except Exception as e:
        log_err(f"❌ remove_from_whitelist: {e}")

def is_whitelisted(username):
    username = normalize_username(username)
    if not username: return False
    try:
        res = supabase.table("whitelist").select("*").eq("username", username).execute()
        return len(res.data) > 0
    except Exception as e:
        log_err(f"❌ is_whitelisted: {e}")
    return False

# ===== PROMOCODES =====
def get_all_promocodes():
    try:
        res = supabase.table("promocodes").select("*").execute()
        return [(p["promo_id"], p["name"], p["max_activations"], p["used_activations"],
                 p["subscription_days"], p["expiry_date"], p["is_active"]) for p in res.data]
    except Exception as e:
        log_err(f"❌ get_all_promocodes: {e}")
        return []

def get_promocode_by_id(promo_id):
    for p in get_all_promocodes():
        if p[0] == promo_id: return p
    return None

def get_promocode_by_name(name):
    for p in get_all_promocodes():
        if p[1] == name and p[6] == 1: return p
    return None

def create_promocode(name, max_activations, subscription_days, expiry_date):
    try:
        res = supabase.table("promocodes").select("promo_id").order("promo_id", desc=True).limit(1).execute()
        new_id = (res.data[0]["promo_id"] + 1) if res.data else 1
        supabase.table("promocodes").insert({
            "promo_id": new_id, "name": name, "max_activations": int(max_activations),
            "used_activations": 0, "subscription_days": int(subscription_days),
            "expiry_date": expiry_date, "is_active": 1
        }).execute()
        log_event(f"🎟 Промокод создан: {name} (ID {new_id})")
        return new_id
    except Exception as e:
        log_err(f"❌ create_promocode: {e}")
    return None

def delete_promocode(promo_id):
    try:
        supabase.table("promocodes").delete().eq("promo_id", promo_id).execute()
        log_event(f"🗑 Промокод удалён: ID {promo_id}")
    except Exception as e:
        log_err(f"❌ delete_promocode: {e}")

def update_promocode(promo_id, field, value):
    try:
        supabase.table("promocodes").update({field: value}).eq("promo_id", promo_id).execute()
    except Exception as e:
        log_err(f"❌ update_promocode: {e}")

def activate_promocode(promo_id, user_id):
    promo = get_promocode_by_id(promo_id)
    if not promo: return False, "Промокод не найден"
    if promo[6] == 0: return False, "Промокод не активен"
    if promo[2] <= promo[3]: return False, "Лимит активаций исчерпан"
    try:
        supabase.table("promo_activations").insert({
            "promo_id": promo_id, "user_id": user_id,
            "activated_at": datetime.datetime.now().isoformat()
        }).execute()
        supabase.table("promocodes").update({"used_activations": promo[3] + 1}).eq("promo_id", promo_id).execute()
        log_event(f"🎟 Промокод {promo[1]} активирован юзером {user_id}")
        return True, "Промокод активирован"
    except Exception as e:
        log_err(f"❌ activate_promocode: {e}")
    return False, "Ошибка БД"

# ===== REPORTS LOG =====
def add_report_log(user_id, username, target, method, reports_count):
    try:
        supabase.table("reports_log").insert({
            "user_id": user_id, "username": normalize_username(username) or "NULL",
            "target": target, "method": method, "reports_count": int(reports_count),
            "created_at": datetime.datetime.now().isoformat()
        }).execute()
        log_event(f"📄 Лог сноса: {user_id} → {target} ({method}, {reports_count})")
    except Exception as e:
        log_err(f"❌ add_report_log: {e}")

def get_all_report_logs():
    try:
        res = supabase.table("reports_log").select("*").order("log_id", desc=False).execute()
        seen = {}
        logs = []
        for r in res.data:
            uid = r["user_id"]
            if uid not in seen:
                seen[uid] = r["username"]
                logs.append((uid, r["username"]))
        return logs
    except Exception as e:
        log_err(f"❌ get_all_report_logs: {e}")
        return []

def get_report_logs_by_user(user_id):
    try:
        res = supabase.table("reports_log").select("*").eq("user_id", user_id).order("log_id", desc=False).execute()
        logs = []
        for r in res.data:
            logs.append((r["log_id"], r["user_id"], r["username"], r["target"], r["method"], r["reports_count"], r["created_at"]))
        return logs
    except Exception as e:
        log_err(f"❌ get_report_logs_by_user: {e}")
        return []

def get_report_log_by_id(log_id):
    try:
        res = supabase.table("reports_log").select("*").eq("log_id", log_id).execute()
        if res.data:
            r = res.data[0]
            return (r["log_id"], r["user_id"], r["username"], r["target"], r["method"], r["reports_count"], r["created_at"])
    except Exception as e:
        log_err(f"❌ get_report_log_by_id: {e}")
    return None

# ========== ГЕНЕРАЦИЯ ==========
COUNTRY_CODES = {
    'BY': {'prefix': '+375', 'operators': ['25','29','33','44']},
    'RU': {'prefix': '+7', 'operators': ['900','901','902','903','904','905','906','909','910','911','912','913','914','915','916','917','918','919','920','921','922','923','924','925','926','927','928','929','930','931','932','933','934','935','936','937','938','939','950','951','952','953','954','955','956','957','958','959','960','961','962','963','964','965','966','967','968','969','980','981','982','983','984','985','986','987','988','989']},
    'UA': {'prefix': '+380', 'operators': ['50','63','66','67','68','73','93','95','96','97','98','99']},
    'PL': {'prefix': '+48', 'operators': ['50','51','53','57','60','66','69','72','73','78','79','88']},
    'GB': {'prefix': '+44', 'operators': ['20','30','70','71','73','74','75','77','78','79']}
}

def generate_real_number():
    country = random.choice(list(COUNTRY_CODES.keys()))
    cd = COUNTRY_CODES[country]
    return f"{cd['prefix']}{random.choice(cd['operators'])}{random.randint(1000000, 9999999)}"

def generate_snos_log(target, reports_count):
    numbers = []
    for _ in range(reports_count):
        number = generate_real_number()
        status = random.choice([' - валид ✅',' - валид ✅',' - валид ✅',' - не валид ❌']) if random.random() < 0.7 else ' - не валид ❌'
        numbers.append(f"{number}{status}")
    return f"=== SNOS LOG ===\nЦель: {target}\nВсего проверок: {reports_count}\nДата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n{'='*30}\n\n" + "\n".join(numbers)

def parse_time(time_str):
    seconds = 0
    for value, unit in re.findall(r'(\d+)([dhm])', time_str.lower().strip()):
        value = int(value)
        if unit == 'd': seconds += value * 86400
        elif unit == 'h': seconds += value * 3600
        elif unit == 'm': seconds += value * 60
    return seconds

def seconds_to_text(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days: parts.append(f"{days}д")
    if hours: parts.append(f"{hours}ч")
    if minutes: parts.append(f"{minutes}м")
    return " ".join(parts) if parts else "0м"

def generate_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def make_report_text(target_username, reports_count, success=True):
    target_link = REPORT_LINK
    date_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    if success:
        return (
            f"📊 <b>Уведомление о блокировке</b>\n\n"
            f"🎯 Аккаунт <a href='{target_link}'>{target_username}</a> <b>был заморожен</b> ✅\n"
            f"📤 Всего жалоб: <code>{reports_count}</code>\n"
            f"📅 Дата: <i>{date_str}</i>\n\n"
            f"<b>Статус:</b> <i>Аккаунт заблокирован за нарушение правил.</i>"
        )
    else:
        return (
            f"📊 <b>Уведомление о блокировке</b>\n\n"
            f"🎯 Аккаунт <a href='{target_link}'>{target_username}</a> <b>не был был заморожен</b> ❌️\n"
            f"📤 Всего жалоб: <code>{reports_count}</code>\n"
            f"📅 Дата: <i>{date_str}</i>\n\n"
            f"<b>Статус:</b> <i>жалобы отменены</i>"
        )

# ========== КЛАВИАТУРЫ ==========
def _btn(text, callback_data=None, url=None, style=None, emoji_id=None):
    d = {"text": text}
    if callback_data is not None: d["callback_data"] = callback_data
    if url is not None: d["url"] = url
    if style is not None: d["style"] = style
    if emoji_id is not None: d["icon_custom_emoji_id"] = emoji_id
    return d

def main_menu(user_id):
    rows = [
        [_btn("Отправка", "send", style="primary", emoji_id=CE_SEND), _btn("Профиль", "profile", style="primary", emoji_id=CE_PROFILE)],
        [_btn("Поддержка", url=SUPPORT_URL, style="danger", emoji_id=CE_SUPPORT), _btn("Наш канал", url="https://t.me/baikallShop", style="danger", emoji_id=CE_CHANNEL)],
    ]
    if user_id == ADMIN_ID:
        rows.append([_btn("Админка", "admin", style="success", emoji_id=CE_ADMIN)])
    return rows

def profile_menu():
    return [
        [_btn("Промокод", "promo", style="danger", emoji_id=CE_PROMO)],
        [_btn("Купить подписку", "buy", style="success", emoji_id=CE_BUY)],
        [_btn("Назад", "back_main", style="primary", emoji_id=CE_BACK)],
    ]

def promo_enter_menu():
    return [[_btn("Назад", "profile", style="primary", emoji_id=CE_BACK)]]

def buy_menu():
    return [
        [_btn("Звёздами", "stars", style="success", emoji_id=CE_STARS)],
        [_btn("TON", "ton_pay", style="primary", emoji_id=CE_TON)],
        [_btn("Назад", "profile", style="primary", emoji_id=CE_BACK)],
    ]

def stars_menu():
    return [
        [_btn("1 день - 500 ⭐", "pay_1", style="danger", emoji_id=CE_STARS_EMOJI)],
        [_btn("3 дня - 1000 ⭐", "pay_3", style="danger", emoji_id=CE_STARS_EMOJI)],
        [_btn("7 дней - 2000 ⭐", "pay_7", style="danger", emoji_id=CE_STARS_EMOJI)],
        [_btn("30 дней - 5000 ⭐", "pay_30", style="danger", emoji_id=CE_STARS_EMOJI)],
        [_btn("Своя подписка", "own_sub_stars", style="primary", emoji_id=CE_OWN_SUB)],
        [_btn("Назад", "buy", style="primary", emoji_id=CE_BACK)],
    ]

def ton_menu():
    return [
        [_btn("1 день - 1.5 TON", "ton_1", style="danger", emoji_id=CE_TON_EMOJI)],
        [_btn("3 дня - 2.5 TON", "ton_3", style="danger", emoji_id=CE_TON_EMOJI)],
        [_btn("7 дней - 4 TON", "ton_7", style="danger", emoji_id=CE_TON_EMOJI)],
        [_btn("30 дней - 10 TON", "ton_30", style="danger", emoji_id=CE_TON_EMOJI)],
        [_btn("Своя подписка", "own_sub_ton", style="primary", emoji_id=CE_OWN_SUB)],
        [_btn("Назад", "buy", style="primary", emoji_id=CE_BACK)],
    ]

def own_sub_menu(back_cb):
    return [
        [_btn("Перейти к оформлению", url=SUPPORT_URL, style="success", emoji_id=CE_CARD)],
        [_btn("Назад", back_cb, style="primary", emoji_id=CE_BACK)],
    ]

def ton_confirm_menu(code, days, user_id):
    return [
        [_btn("Отмена", "ton_cancel", style="danger", emoji_id=CE_CROSS)],
        [_btn("Проверить", f"ton_check_{code}_{user_id}", style="primary", emoji_id=CE_CHECK)],
    ]

def ton_admin_menu(code, days, user_id):
    return [
        [_btn("Принять", f"ton_confirm_{code}", style="success", emoji_id=CE_CHECK)],
        [_btn("Отменить", f"ton_cancel_admin_{code}", style="danger", emoji_id=CE_CROSS)],
    ]

def ton_cancel_confirm_menu(code, days, user_id):
    return [
        [_btn("Точно отменить", f"ton_cancel_final_{code}", style="danger", emoji_id=CE_CROSS)],
        [_btn("Назад", f"ton_back_{code}", style="primary", emoji_id=CE_BACK)],
    ]

def admin_main_menu():
    return [
        [_btn("Выдать подписку", "admin_give", style="success", emoji_id=CE_GIVE_SUB), _btn("Забрать подписку", "admin_remove", style="danger", emoji_id=CE_TAKE_SUB)],
        [_btn("Создать промокод", "admin_create_promo", style="danger", emoji_id=CE_PROMO), _btn("Промокоды", "admin_list_promo", style="danger", emoji_id=CE_PROMO)],
        [_btn("Выдать лог", "admin_send_log", style="primary", emoji_id=CE_LOG), _btn("Вайт-лист", "admin_whitelist", style="primary", emoji_id=CE_WHITELIST)],
        [_btn("Рассылка", "admin_broadcast", style="primary", emoji_id=CE_BROADCAST), _btn("Database", "admin_database", style="success", emoji_id=CE_DATABASE)],
        [_btn("Создать оплату", "admin_create_payment", style="success", emoji_id=CE_BUY), _btn("Назад", "back_main", style="danger", emoji_id=CE_BACK)],
    ]

def admin_back_menu():
    return [[_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)]]

def admin_input_back_menu():
    return [
        [_btn("Отмена", "admin_back", style="danger", emoji_id=CE_CROSS)],
        [_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)],
    ]

def admin_whitelist_menu():
    return [
        [_btn("Добавить", "whitelist_add", style="success", emoji_id=CE_CHECK)],
        [_btn("Удалить", "whitelist_remove", style="danger", emoji_id=CE_CROSS)],
        [_btn("Список", "whitelist_list", style="primary", emoji_id=CE_WHITELIST)],
        [_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)],
    ]

def admin_days_menu(user_id):
    return [
        [_btn("1 day", f"admin_day_{user_id}_1")],
        [_btn("3 day", f"admin_day_{user_id}_3")],
        [_btn("7 day", f"admin_day_{user_id}_7")],
        [_btn("30 day", f"admin_day_{user_id}_30")],
        [_btn("∞ day", f"admin_day_{user_id}_forever")],
        [_btn("Своё время", f"admin_custom_{user_id}", style="primary", emoji_id=CE_CALENDAR)],
        [_btn("Назад", "admin_give", style="primary", emoji_id=CE_BACK)],
    ]

def broadcast_preview_menu():
    return [
        [_btn("Отправить", "broadcast_send", style="success", emoji_id=CE_CHECK)],
        [_btn("Отменить", "broadcast_cancel", style="danger", emoji_id=CE_CROSS)],
    ]

def admin_database_menu(page, total_pages, users_on_page):
    rows = [[_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)]]
    row = []
    for u in users_on_page:
        username = u[1] if u[1] != "NULL" else f"id{u[0]}"
        row.append(_btn(f"{username}"[:25], f"db_user_{u[0]}", style="danger", emoji_id=CE_USER))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row: rows.append(row)
    nav = []
    if page > 0: nav.append(_btn("Назад", f"db_page_{page-1}", style="primary", emoji_id=CE_BACK))
    if page < total_pages - 1: nav.append(_btn("Вперёд", f"db_page_{page+1}", style="primary", emoji_id=CE_NEXT))
    if nav: rows.append(nav)
    return rows

def db_user_menu(user_id, current_page, cooldown_active_for_user):
    if cooldown_active_for_user:
        cd_btn = _btn("Кулдаун: ВКЛ", f"db_toggle_cd_{user_id}", style="success", emoji_id=CE_CHECK)
    else:
        cd_btn = _btn("Кулдаун: ВЫКЛ", f"db_toggle_cd_{user_id}", style="danger", emoji_id=CE_CROSS)
    return [
        [cd_btn],
        [_btn("Назад", f"db_page_{current_page}", style="primary", emoji_id=CE_BACK)],
    ]

def send_menu():
    return [
        [_btn("Снос аккаунта", "snos_acc", style="danger", emoji_id=CE_USER)],
        [_btn("Снос бота", "snos_bot", style="danger", emoji_id=CE_PROFILE)],
        [_btn("Снос группы", "snos_group", style="danger", emoji_id=CE_CHANNEL)],
        [_btn("Снос канала", "snos_channel", style="danger", emoji_id=CE_CHANNEL)],
        [_btn("Назад", "back_main", style="primary", emoji_id=CE_BACK)],
    ]

def snos_input_menu():
    return [
        [_btn("Отмена", "back_main", style="danger", emoji_id=CE_CROSS)],
        [_btn("Назад", "send", style="primary", emoji_id=CE_BACK)],
    ]

def method_menu(action):
    return [
        [_btn("Универсальный", f"method_{action}_universal", style="primary", emoji_id=CE_SEND)],
        [_btn("Спам", f"method_{action}_spam", emoji_id=CE_EXCL)],
        [_btn("Порнография", f"method_{action}_porno", emoji_id=CE_WARN)],
        [_btn("Физ. номер", f"method_{action}_phone", emoji_id=CE_ID)],
        [_btn("Назад", "send", style="primary", emoji_id=CE_BACK)],
    ]

def confirm_menu():
    return [
        [_btn("Да", "confirm_yes", style="success", emoji_id=CE_CHECK)],
        [_btn("Нет", "confirm_no", style="danger", emoji_id=CE_CROSS)],
    ]

def admin_create_payment_type_menu():
    return [
        [_btn("Stars", "acp_type_stars", style="success", emoji_id=CE_STARS_EMOJI)],
        [_btn("TON", "acp_type_ton", style="primary", emoji_id=CE_TON_EMOJI)],
        [_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)],
    ]

def admin_create_payment_term_menu():
    return [
        [_btn("1 день", "acp_term_1")],
        [_btn("3 дня", "acp_term_3")],
        [_btn("7 дней", "acp_term_7")],
        [_btn("30 дней", "acp_term_30")],
        [_btn("∞ Навсегда", "acp_term_forever")],
        [_btn("Своё время", "acp_term_custom", style="primary", emoji_id=CE_CALENDAR)],
        [_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)],
    ]

def admin_create_payment_confirm_menu():
    return [
        [_btn("Отправить счёт", "acp_send", style="success", emoji_id=CE_CHECK)],
        [_btn("Отменить", "admin_back", style="danger", emoji_id=CE_CROSS)],
    ]

# ========== ОТПРАВКА ==========
def _build_fallback_markup(keyboard_rows):
    if not keyboard_rows: return None
    rows = []
    for row in keyboard_rows:
        btn_row = []
        for b in row:
            if "url" in b:
                btn_row.append(InlineKeyboardButton(text=b["text"], url=b["url"]))
            else:
                btn_row.append(InlineKeyboardButton(text=b["text"], callback_data=b.get("callback_data", "noop")))
        rows.append(btn_row)
    return InlineKeyboardMarkup(rows)

async def send_message_with_image_quote(context, chat_id, text, keyboard_rows=None, parse_mode="HTML", reply_to_message_id=None, no_quote=False):
    if no_quote:
        body = f"<a href='{PHOTO_URL}'>&#8203;</a>{text}"
    else:
        body = f"<blockquote><a href='{PHOTO_URL}'>&#8203;</a>{text}</blockquote>"

    if keyboard_rows:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": body,
                "parse_mode": parse_mode,
                "reply_markup": {"inline_keyboard": keyboard_rows},
                "link_preview_options": {"is_disabled": False, "prefer_large_media": False, "show_above_text": True},
            }
            if reply_to_message_id:
                payload["reply_to_message_id"] = reply_to_message_id
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    return _MsgWrapper(data["result"])
                else:
                    log_err(f"❌ sendMessage со style/emoji отклонён: {r.status_code}: {r.text}")
        except Exception as e:
            log_err(f"❌ sendMessage со style/emoji упал: {type(e).__name__}: {e}")

    lpo = LinkPreviewOptions(is_disabled=False, prefer_large_media=False, show_above_text=True)
    return await context.bot.send_message(
        chat_id=chat_id, text=body, parse_mode=parse_mode,
        reply_markup=_build_fallback_markup(keyboard_rows),
        reply_to_message_id=reply_to_message_id,
        link_preview_options=lpo,
    )

class _MsgWrapper:
    def __init__(self, data):
        self._data = data or {}
        self.message_id = self._data.get("message_id")

async def send_with_photo(context, chat_id, text, keyboard_rows=None, parse_mode="HTML", reply_to_message_id=None):
    return await send_message_with_image_quote(context, chat_id, text, keyboard_rows, parse_mode, reply_to_message_id, no_quote=False)

async def send_without_quote(context, chat_id, text, keyboard_rows=None, parse_mode="HTML"):
    return await send_message_with_image_quote(context, chat_id, text, keyboard_rows, parse_mode, None, no_quote=True)

async def delete_previous_messages(context, chat_id, user_id, keep_first=True):
    if "messages_to_delete" not in context.user_data: context.user_data["messages_to_delete"] = {}
    if user_id not in context.user_data["messages_to_delete"]: context.user_data["messages_to_delete"][user_id] = []
    messages = context.user_data["messages_to_delete"][user_id]
    messages_to_delete = messages[1:] if keep_first and len(messages) > 0 else messages
    for msg_id in messages_to_delete:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except: pass
    if keep_first and len(messages) > 0:
        context.user_data["messages_to_delete"][user_id] = [messages[0]]
    else:
        context.user_data["messages_to_delete"][user_id] = []

async def add_message_to_delete(context, chat_id, user_id, message):
    if "messages_to_delete" not in context.user_data: context.user_data["messages_to_delete"] = {}
    if user_id not in context.user_data["messages_to_delete"]: context.user_data["messages_to_delete"][user_id] = []
    if message is not None and getattr(message, "message_id", None):
        context.user_data["messages_to_delete"][user_id].append(message.message_id)

async def send_subscription_notification(context, user_id, days, source="purchase"):
    user_data = get_user(user_id)
    if not user_data: return
    if source == "purchase":
        text = f"🎉 <b>Вы приобрели подписку</b> в боте на <code>{days}</code> ⭐️"
    else:
        text = f"🎉 <b>Вам выдали подписку</b> на <code>{days}</code> ⭐️"
    await send_with_photo(context, user_id, text, main_menu(user_id))

async def schedule_fake_report(context, chat_id, target, reports_count):
    delay = random.randint(1800, 86400)
    success = random.random() < 0.6
    async def send_fake_report():
        await asyncio.sleep(delay)
        report_text = make_report_text(target, reports_count, success=success)
        msg = await send_without_quote(context, chat_id, report_text, None, parse_mode="HTML")
        await add_message_to_delete(context, chat_id, chat_id, msg)
        log_event(f"📩 Фейк-отчёт {'✅' if success else '❌'} отправлен юзеру {chat_id} по цели {target}")
    asyncio.create_task(send_fake_report())

async def send_progress_message(context, chat_id, target, reports_count, method_name):
    await send_without_quote(context, chat_id, f"🚀 <b>Запущен процесс</b> отправки репортов на <code>{target}</code>\n📋 Метод: <i>{method_name}</i>\n\n<i>🔄 Подготовка...</i>")
    await asyncio.sleep(1)
    msg = await context.bot.send_message(chat_id=chat_id, text=f"🚀 <b>Отправка репортов</b> на <code>{target}</code>\n📋 Метод: <i>{method_name}</i>\n\n<i>🔄 Инициализация...</i>", parse_mode="HTML")
    bar_length = 25
    last_edit = 0
    for i in range(1, reports_count + 1):
        if i - last_edit >= 5 or i == reports_count:
            percent = int((i / reports_count) * 100)
            filled = int(bar_length * i / reports_count)
            bar = "▓" * filled + "░" * (bar_length - filled)
            progress_text = (
                f"🚀 <b>Отправка репортов</b> на <code>{target}</code>\n"
                f"📋 Метод: <i>{method_name}</i>\n"
                f"📊 Прогресс: <b>{percent}%</b> | <code>{i}/{reports_count}</code>\n\n"
                f"<code>{bar}</code>\n\n"
                f"<i>⏳ Осталось ~{random.randint(3, 15)} сек.</i>"
            )
            try: await msg.edit_text(text=progress_text, parse_mode="HTML")
            except: pass
            last_edit = i
        await asyncio.sleep(random.uniform(0.05, 0.12))
    log_content = generate_snos_log(target, reports_count)
    log_file = io.BytesIO(log_content.encode('utf-8'))
    log_file.name = f"Snos_{target.replace('@', '')}_Logs.txt"
    await context.bot.send_document(chat_id=chat_id, document=InputFile(log_file, filename=log_file.name), caption=f"📄 Лог сноса для {target}")
    user_data = get_user(chat_id)
    username = user_data[1] if user_data else None
    add_report_log(chat_id, username, target, method_name, reports_count)
    final_text = (
        f"<b>✅ Успешно!</b>\n\n"
        f"🎯 Цель: <code>{target}</code>\n"
        f"📋 Метод: <i>{method_name}</i>\n"
        f"📤 Отправлено репортов: <code>{reports_count}</code>\n\n"
        f"<i>⏳ Принятие репортов может занять до 24-48 часов.</i>\n"
        f"<i>📄 Отчёт сохранён в файле выше.</i>"
    )
    await send_with_photo(context, chat_id, final_text, main_menu(chat_id))
    await schedule_fake_report(context, chat_id, target, reports_count)
    return reports_count

# ========== ФОНОВЫЙ ТАСК КУЛДАУНА ==========
async def cooldown_watcher(context):
    notified = set()
    while True:
        await asyncio.sleep(30)
        try:
            now = datetime.datetime.now()
            active = get_all_active_cooldowns()
            for uid, end in active:
                if end <= now:
                    if uid in notified:
                        clear_cooldown(uid)
                        continue
                    try:
                        await send_without_quote(context, uid, "⏳ <b>Кулдаун завершен!</b>\n\n<i>Можете снова отправлять жалобы.</i>", None, parse_mode="HTML")
                        log_event(f"⏳ Уведомление об окончании кулдауна отправлено {uid}")
                    except Exception as e:
                        log_warn(f"⚠️ Не удалось уведомить {uid}: {e}")
                    notified.add(uid)
                    clear_cooldown(uid)
        except Exception as e:
            log_err(f"❌ cooldown_watcher: {type(e).__name__}: {e}")

# ========== ОПЛАТА ==========
def create_invoice(days, price, payload=None):
    days_str = str(days)
    safe_param = re.sub(r'[^a-zA-Z0-9_-]', '_', f"sub_{days_str}")[:64]
    title = f"Подписка Baikall на {days_str} дн."[:32]
    return {
        "title": title,
        "description": f"Доступ к функции сноса на {days_str} дней"[:255],
        "currency": "XTR",
        "prices": [LabeledPrice(label=f"{days_str} дн."[:32], amount=int(price))],
        "start_parameter": safe_param,
        "payload": payload or f"sub_{days_str}_{price}"
    }

async def send_invoice(chat_id, context, days, price, payload=None):
    try: price_int = int(price)
    except:
        log_err(f"❌ Неверная сумма: {price}")
        return False
    if price_int < 1 or price_int > 10000:
        log_err(f"❌ Сумма {price_int} вне диапазона 1..10000 (XTR)")
        return False
    inv = create_invoice(days, price_int, payload)
    try:
        await context.bot.send_invoice(
            chat_id=chat_id, title=inv["title"], description=inv["description"], payload=inv["payload"],
            provider_token=PROVIDER_TOKEN, currency=inv["currency"], prices=inv["prices"],
            start_parameter=inv["start_parameter"], need_name=False, need_phone_number=False,
            need_email=False, need_shipping_address=False, is_flexible=False
        )
        log_event(f"📤 Счёт отправлен: chat_id={chat_id}, days={days}, price={price_int}⭐")
        return True
    except Exception as e:
        log_err(f"❌ Ошибка отправки счёта юзеру {chat_id}: {type(e).__name__}: {e}")
        return False

async def show_database_page(context, admin_id, page, query=None):
    all_users = get_all_users()
    per_page = 4
    total_pages = max(1, (len(all_users) + per_page - 1) // per_page)
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    users_on_page = all_users[page * per_page: page * per_page + per_page]
    context.user_data["db_current_page"] = page
    text = f"🗄 <b>База пользователей</b>\n\n📄 Страница <code>{page+1}</code> из <code>{total_pages}</code>\n👥 Всего: <code>{len(all_users)}</code>"
    msg = await send_with_photo(context, admin_id, text, admin_database_menu(page, total_pages, users_on_page))
    await add_message_to_delete(context, admin_id, admin_id, msg)
    if query:
        try: await query.message.delete()
        except: pass

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, normalize_username(user.username))
    text = f"{EMOJI_WELCOME} <b>Добро пожаловать в Baikall Snos</b> {EMOJI_WELCOME}"
    msg = await send_with_photo(context, user.id, text, main_menu(user.id))
    if "messages_to_delete" not in context.user_data: context.user_data["messages_to_delete"] = {}
    if user.id not in context.user_data["messages_to_delete"]: context.user_data["messages_to_delete"][user.id] = []
    context.user_data["messages_to_delete"][user.id].append(msg.message_id)

async def create_promo_step1(update, context):
    await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
    context.user_data["promo_step"] = "activations"
    msg = await send_with_photo(context, update.effective_user.id, "🎟 <b>Введите количество активаций</b> для промокода:", admin_back_menu())
    await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_step2(update, context, text):
    try:
        context.user_data["promo_max_activations"] = int(text)
        context.user_data["promo_step"] = "subscription_days"
        await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
        msg = await send_with_photo(context, update.effective_user.id, "⏱ <b>Введите количество дней подписки</b> (цифрой):", admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)
    except:
        msg = await send_with_photo(context, update.effective_user.id, "❌ <b>Введите число!</b>", admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_step3(update, context, text):
    try:
        context.user_data["promo_sub_days"] = int(text)
        context.user_data["promo_step"] = "expiry_date"
        await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
        msg = await send_with_photo(context, update.effective_user.id, "📅 <b>Введите дату окончания</b> (пример: 31.12.2026):", admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)
    except:
        msg = await send_with_photo(context, update.effective_user.id, "❌ <b>Введите число!</b>", admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_step4(update, context, text):
    try:
        datetime.datetime.strptime(text, "%d.%m.%Y")
        context.user_data["promo_expiry_date"] = text
        context.user_data["promo_step"] = "name"
        await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
        msg = await send_with_photo(context, update.effective_user.id, "📝 <b>Введите название промокода:</b>", admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)
    except:
        msg = await send_with_photo(context, update.effective_user.id, "❌ <b>Неверный формат!</b> Используйте <code>ДД.ММ.ГГГГ</code>", admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_finish(update, context, text):
    name = text
    create_promocode(name, context.user_data["promo_max_activations"], context.user_data["promo_sub_days"], context.user_data["promo_expiry_date"])
    max_activations = context.user_data["promo_max_activations"]
    sub_days = context.user_data["promo_sub_days"]
    expiry_date = context.user_data["promo_expiry_date"]
    for k in ["promo_step", "promo_max_activations", "promo_sub_days", "promo_expiry_date"]:
        context.user_data.pop(k, None)
    await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
    text = f"<b>✅ Промокод создан!</b>\n\n📝 Название: <code>{name}</code>\n📊 Активаций: <code>{max_activations}</code>\n⏱ Дней: <code>{sub_days}</code>\n📅 Действует до: <i>{expiry_date}</i>"
    msg = await send_with_photo(context, update.effective_user.id, text, admin_main_menu())
    await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

# ========== BUTTON HANDLER ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if data == "send":
        if not has_subscription(user.id):
            await query.answer("❌ У вас не активирована подписка", show_alert=True)
            return
        if not is_cooldown_off(user.id):
            remaining_text, end_dt = cooldown_remaining_text(user.id)
            if remaining_text:
                await query.answer(f"⏳ Кулдаун: {remaining_text}", show_alert=True)
                return
            else:
                if end_dt is not None:
                    clear_cooldown(user.id)

    await delete_previous_messages(context, user.id, user.id, keep_first=True)

    if data == "admin":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        msg = await send_with_photo(context, user.id, "🔐 <b>Админ-панель:</b>", admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_back":
        msg = await send_with_photo(context, user.id, "🔐 <b>Админ-панель:</b>", admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_broadcast":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        context.user_data["broadcast_step"] = "waiting_text"
        msg = await send_with_photo(context, user.id, "📢 <b>Введите текст для рассылки:</b>", admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "broadcast_send":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        broadcast_text = context.user_data.get("broadcast_text")
        if not broadcast_text:
            await query.answer("❌ Текст потерян.", show_alert=True); return
        all_users = get_all_users()
        sent, failed = 0, 0
        log_event(f"📢 Начало рассылки на {len(all_users)} юзеров")
        for u in all_users:
            try:
                await context.bot.send_message(chat_id=u[0], text=broadcast_text)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                failed += 1
                log_warn(f"⚠️ Рассылка не дошла до {u[0]}: {e}")
        context.user_data.pop("broadcast_step", None); context.user_data.pop("broadcast_text", None)
        log_event(f"📢 Рассылка завершена: ✅{sent} / ❌{failed}")
        text = f"<b>✅ Рассылка завершена</b>\n\n📤 Отправлено: <code>{sent}</code>\n❌ Ошибок: <code>{failed}</code>"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "broadcast_cancel":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        context.user_data.pop("broadcast_step", None); context.user_data.pop("broadcast_text", None)
        log_event("📢 Рассылка отменена")
        msg = await send_with_photo(context, user.id, "❌ <b>Рассылка отменена</b>", admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_database":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        await show_database_page(context, user.id, page=0, query=query); return

    if data.startswith("db_page_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        await show_database_page(context, user.id, page=int(data.split("_")[2]), query=query); return

    if data.startswith("db_user_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        target_id = int(data.split("_")[2])
        u = get_user(target_id)
        if not u:
            await query.answer("❌ Пользователь не найден", show_alert=True); return
        username = u[1] if u[1] != "NULL" else "—"
        if u[2] and u[2] != "NULL":
            try: sub = "Навсегда" if u[2] == "forever" else datetime.datetime.fromisoformat(u[2]).strftime("%d.%m.%Y %H:%M")
            except: sub = u[2]
        else: sub = "❌ Нет"
        cd_off = is_cooldown_off(target_id)
        cd_status_text = "🔴 Выключен" if cd_off else "🟢 Включён"
        text = f"👤 <b>Пользователь</b>\n\n🆔 ID: <code>{u[0]}</code>\n📛 Юзернейм: <i>@{username}</i>\n🛡 Подписка: <b>{sub}</b>\n⏳ Кулдаун: <b>{cd_status_text}</b>"
        current_page = context.user_data.get("db_current_page", 0)
        kb = db_user_menu(target_id, current_page, cooldown_active_for_user=(not cd_off))
        msg = await send_with_photo(context, user.id, text, kb)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("db_toggle_cd_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        target_id = int(data.split("_")[3])
        u = get_user(target_id)
        if not u:
            await query.answer("❌ Пользователь не найден", show_alert=True); return
        currently_off = is_cooldown_off(target_id)
        set_cooldown_off(target_id, off=(not currently_off))
        username = u[1] if u[1] != "NULL" else "—"
        if u[2] and u[2] != "NULL":
            try: sub = "Навсегда" if u[2] == "forever" else datetime.datetime.fromisoformat(u[2]).strftime("%d.%m.%Y %H:%M")
            except: sub = u[2]
        else: sub = "❌ Нет"
        cd_off = is_cooldown_off(target_id)
        cd_status_text = "🔴 Выключен" if cd_off else "🟢 Включён"
        text = f"👤 <b>Пользователь</b>\n\n🆔 ID: <code>{u[0]}</code>\n📛 Юзернейм: <i>@{username}</i>\n🛡 Подписка: <b>{sub}</b>\n⏳ Кулдаун: <b>{cd_status_text}</b>"
        current_page = context.user_data.get("db_current_page", 0)
        kb = db_user_menu(target_id, current_page, cooldown_active_for_user=(not cd_off))
        msg = await send_with_photo(context, user.id, text, kb)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_whitelist":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        msg = await send_with_photo(context, user.id, "⬜ <b>Вайт-лист:</b>", admin_whitelist_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "whitelist_add":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        context.user_data["whitelist_action"] = "add"
        msg = await send_with_photo(context, user.id, "➕ <b>Введите @username</b> для добавления в вайт-лист:", admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "whitelist_remove":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        context.user_data["whitelist_action"] = "remove"
        msg = await send_with_photo(context, user.id, "➖ <b>Введите @username</b> для удаления из вайт-листа:", admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "whitelist_list":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        wl = get_whitelist()
        text = "⬜ <b>Вайт-лист пуст.</b>" if not wl else "⬜ <b>Вайт-лист:</b>\n\n" + "\n".join(f"• <i>@{i[0]}</i> (добавлен: <code>{i[1][:10]}</code>)" for i in wl)
        msg = await send_with_photo(context, user.id, text, admin_whitelist_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_give":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        all_users = get_all_users()
        users_list = "\n".join([f"• ID: <code>{u[0]}</code> | @{u[1] if u[1] != 'NULL' else 'без юзернейма'}" for u in all_users]) if all_users else "пусто"
        context.user_data["admin_action"] = "give"
        text = f"👤 <b>Введите ID или @username пользователя:</b>\n\n📋 <b>Список в БД:</b>\n{users_list}"
        msg = await send_with_photo(context, user.id, text, admin_input_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_remove":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        all_users = get_all_users()
        users_list = "\n".join([f"• ID: <code>{u[0]}</code> | @{u[1] if u[1] != 'NULL' else 'без юзернейма'}" for u in all_users]) if all_users else "пусто"
        context.user_data["admin_action"] = "remove"
        text = f"👤 <b>Введите ID или @username пользователя:</b>\n\n📋 <b>Список в БД:</b>\n{users_list}"
        msg = await send_with_photo(context, user.id, text, admin_input_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("admin_day_"):
        parts = data.split("_")
        target_id = int(parts[2]); days = parts[3]
        user_data = get_user(target_id)
        username = user_data[1] if user_data and user_data[1] != "NULL" else f"id{target_id}"
        if days == "forever":
            end_date = "forever"; text_days = "навсегда"
        else:
            end_date = (datetime.datetime.now() + datetime.timedelta(days=int(days))).isoformat()
            text_days = f"{days} дней"
        set_subscription(target_id, end_date)
        await send_subscription_notification(context, target_id, text_days, source="admin")
        text = f"✅ <b>Подписка выдана</b> @{username} (ID: <code>{target_id}</code>) на <i>{text_days}</i>"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("admin_custom_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        target_id = data.replace("admin_custom_", "")
        context.user_data["admin_custom_user_id"] = target_id
        context.user_data["admin_action"] = "custom_time"
        text = "⏱ <b>Введите время в формате:</b>\n\n• <code>2d 5h 7m</code> — 2 дня 5 часов 7 минут\n• <code>30d</code> — 30 дней\n• <code>1d 12h</code> — 1 день 12 часов"
        msg = await send_with_photo(context, user.id, text, admin_input_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_create_payment":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        for k in ["acp_type", "acp_price", "acp_term", "acp_term_seconds", "acp_term_text", "acp_username", "acp_target_id"]:
            context.user_data.pop(k, None)
        context.user_data["acp_step"] = "type"
        msg = await send_with_photo(context, user.id, "💳 <b>Создать оплату</b>\n\n<i>Выберите тип оплаты:</i>", admin_create_payment_type_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("acp_type_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        context.user_data["acp_type"] = data.replace("acp_type_", "")
        context.user_data["acp_step"] = "price"
        type_text = "⭐ звёзд" if context.user_data["acp_type"] == "stars" else "💎 TON"
        msg = await send_with_photo(context, user.id, f"💰 <b>Введите количество</b> {type_text} для счёта:", admin_input_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("acp_term_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        term = data.replace("acp_term_", "")
        if term == "custom":
            context.user_data["acp_step"] = "custom_time"
            msg = await send_with_photo(context, user.id, "⏱ <b>Введите время подписки:</b>\n\n• <code>2d 5h 7m</code>\n• <code>30d</code>\n• <code>1d 12h</code>", admin_input_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        if term == "forever":
            context.user_data["acp_term_seconds"] = "forever"
            context.user_data["acp_term_text"] = "навсегда"
        else:
            sec = int(term) * 86400
            context.user_data["acp_term_seconds"] = sec
            context.user_data["acp_term_text"] = f"{term} дней"
        context.user_data["acp_step"] = "username"
        msg = await send_with_photo(context, user.id, "👤 <b>Введите ID или @username получателя:</b>", admin_input_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "acp_send":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        acp_type = context.user_data.get("acp_type")
        acp_price = context.user_data.get("acp_price")
        acp_term_seconds = context.user_data.get("acp_term_seconds")
        acp_term_text = context.user_data.get("acp_term_text")
        target_id = context.user_data.get("acp_target_id")
        if not all([acp_type, acp_price, acp_term_seconds is not None, target_id]):
            await query.answer("❌ Данные потеряны, начните заново.", show_alert=True); return

        if acp_type == "stars":
            if acp_term_seconds == "forever":
                payload = f"custom_f_{acp_price}"
                days_display = 9999
            else:
                payload = f"custom_{acp_term_seconds}_{acp_price}"
                days_display = acp_term_seconds // 86400 if isinstance(acp_term_seconds, int) and acp_term_seconds >= 86400 else 1
            ok = await send_invoice(target_id, context, days_display, int(acp_price), payload=payload)
            if ok:
                log_event(f"💳 Кастомный счёт Stars отправлен {target_id}")
                text = f"✅ <b>Счёт отправлен</b> юзеру <code>{target_id}</code>\n💰 <b>{acp_price}</b> ⭐\n📅 <i>{acp_term_text}</i>"
                msg = await send_with_photo(context, user.id, text, admin_main_menu())
            else:
                msg = await send_with_photo(context, user.id, "❌ <b>Не удалось отправить счёт.</b>", admin_main_menu())
        else:
            code = generate_code()
            save_ton_pending(code, target_id, acp_term_seconds, acp_price, acp_term_text, is_custom=True)
            text = f"💎 <b>Оплата TON</b>\n\n📤 Кошелёк:\n<code>{TON_WALLET}</code>\n\n💰 Сумма: <b>{acp_price} TON</b>\n📅 Подписка: <i>{acp_term_text}</i>\n\n📝 Комментарий к переводу:\n<code>{code}</code>\n\n<i>⚠️ После перевода нажмите «Проверить»</i>"
            try:
                await send_without_quote(context, target_id, text, ton_confirm_menu(code, 0, target_id))
                log_event(f"💳 Кастомный счёт TON отправлен {target_id}")
                text2 = f"✅ <b>TON-реквизиты отправлены</b> юзеру <code>{target_id}</code>\n💎 <b>{acp_price} TON</b>\n📅 <i>{acp_term_text}</i>"
                msg = await send_with_photo(context, user.id, text2, admin_main_menu())
            except Exception as e:
                log_err(f"❌ Ошибка отправки TON: {e}")
                msg = await send_with_photo(context, user.id, "❌ <b>Не удалось отправить реквизиты.</b>", admin_main_menu())

        for k in ["acp_step", "acp_type", "acp_price", "acp_term_seconds", "acp_term_text", "acp_target_id", "acp_username"]:
            context.user_data.pop(k, None)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_create_promo":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        await create_promo_step1(update, context)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_list_promo":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        promos = get_all_promocodes()
        if not promos:
            msg = await send_with_photo(context, user.id, "📋 <b>Промокодов пока нет.</b>", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        rows = []
        for promo in promos:
            status = "✅" if promo[6] == 1 else "❌"
            rows.append([_btn(f"{status} {promo[1]} ({promo[3]}/{promo[2]})", f"promo_view_{promo[0]}")])
        rows.append([_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)])
        msg = await send_with_photo(context, user.id, "📋 <b>Список промокодов:</b>", rows)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_view_"):
        promo_id = int(data.split("_")[2])
        promo = get_promocode_by_id(promo_id)
        if not promo:
            msg = await send_with_photo(context, user.id, "❌ <b>Промокод не найден.</b>", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        text = f"📋 <b>Промокод:</b> <code>{promo[1]}</code>\n📊 Активаций: <b>{promo[3]}/{promo[2]}</b>\n📅 Дней подписки: <code>{promo[4]}</code>\n⏳ Действует до: <i>{promo[5]}</i>\n📌 Статус: <b>{'Активен ✅' if promo[6] == 1 else 'Неактивен ❌'}</b>"
        rows = [
            [_btn("Удалить", f"promo_delete_{promo_id}", style="danger", emoji_id=CE_CROSS)],
            [_btn("Продлить", f"promo_extend_{promo_id}", style="primary", emoji_id=CE_CALENDAR)],
            [_btn("Добавить активации", f"promo_add_activations_{promo_id}", style="primary", emoji_id=CE_CHECK)],
            [_btn("Добавить подписку", f"promo_add_subscription_{promo_id}", style="primary", emoji_id=CE_CALENDAR)],
            [_btn("Назад", "admin_list_promo", style="primary", emoji_id=CE_BACK)],
        ]
        msg = await send_with_photo(context, user.id, text, rows)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_delete_"):
        delete_promocode(int(data.split("_")[2]))
        msg = await send_with_photo(context, user.id, "✅ <b>Промокод удалён.</b>", admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_extend_"):
        context.user_data["promo_extend_id"] = int(data.split("_")[2])
        context.user_data["promo_step"] = "extend_date"
        msg = await send_with_photo(context, user.id, "📅 <b>Введите новую дату окончания</b> (пример: 31.12.2026):", admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_add_activations_"):
        context.user_data["promo_add_activations_id"] = int(data.split("_")[3])
        context.user_data["promo_step"] = "add_activations"
        msg = await send_with_photo(context, user.id, "➕ <b>Введите количество активаций</b> для добавления:", admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_add_subscription_"):
        context.user_data["promo_add_subscription_id"] = int(data.split("_")[3])
        context.user_data["promo_step"] = "add_subscription"
        msg = await send_with_photo(context, user.id, "⏱ <b>Введите количество дней</b> для подписки:", admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_send_log":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True); return
        logs = get_all_report_logs()
        if not logs:
            msg = await send_with_photo(context, user.id, "📄 <b>Логов пока нет.</b>", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        rows = [[_btn(f"{log[1] if log[1] != 'NULL' else f'id{log[0]}'}", f"log_user_{log[0]}", emoji_id=CE_USER)] for log in logs]
        rows.append([_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)])
        msg = await send_with_photo(context, user.id, "📄 <b>Выберите пользователя:</b>", rows)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("log_user_"):
        user_id = int(data.split("_")[2])
        logs = get_report_logs_by_user(user_id)
        user_data = get_user(user_id)
        username = user_data[1] if user_data and user_data[1] != "NULL" else f"id{user_id}"
        rows = [[_btn(f"{log[3]} ({log[4]})", f"log_target_{log[0]}")] for log in logs]
        rows.append([_btn("Назад", "admin_send_log", style="primary", emoji_id=CE_BACK)])
        text = f"👤 Пользователь: <i>@{username}</i>\n<b>Выберите цель:</b>"
        msg = await send_with_photo(context, user.id, text, rows)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("log_target_"):
        log_id = int(data.split("_")[2])
        log = get_report_log_by_id(log_id)
        if not log:
            msg = await send_with_photo(context, user.id, "❌ <b>Лог не найден.</b>", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        context.user_data["send_log_id"] = log_id
        rows = [
            [_btn("Отправить", f"log_send_{log_id}", style="success", emoji_id=CE_CHECK)],
            [_btn("Отменить", f"log_cancel_{log_id}", style="danger", emoji_id=CE_CROSS)],
            [_btn("Назад", "admin_back", style="primary", emoji_id=CE_BACK)],
        ]
        text = f"📄 <b>Лог:</b>\n👤 Пользователь: <i>@{log[2]}</i>\n🎯 Цель: <code>{log[3]}</code>\n📋 Метод: <i>{log[4]}</i>\n📊 Репортов: <code>{log[5]}</code>\n📅 Дата: <i>{log[6]}</i>"
        msg = await send_with_photo(context, user.id, text, rows)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("log_send_"):
        log_id = int(data.split("_")[2])
        log = get_report_log_by_id(log_id)
        if not log:
            msg = await send_with_photo(context, user.id, "❌ <b>Лог не найден.</b>", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        report_text = make_report_text(log[3], log[5], success=True)
        await send_without_quote(context, log[1], report_text, None, parse_mode="HTML")
        log_event(f"📩 Отправлен ✅-отчёт юзеру {log[1]}")
        text = f"✅ <b>Отчёт (успех) отправлен</b> @{log[2]}"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("log_cancel_"):
        log_id = int(data.split("_")[2])
        log = get_report_log_by_id(log_id)
        if not log:
            msg = await send_with_photo(context, user.id, "❌ <b>Лог не найден.</b>", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        report_text = make_report_text(log[3], log[5], success=False)
        await send_without_quote(context, log[1], report_text, None, parse_mode="HTML")
        log_event(f"📩 Отправлен ❌-отчёт юзеру {log[1]}")
        text = f"❌ <b>Отчёт (провал) отправлен</b> @{log[2]}"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "ton_pay":
        msg = await send_with_photo(context, user.id, "💎 <b>Выберите тариф TON:</b>", ton_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "ton_cancel":
        msg = await send_with_photo(context, user.id, "💳 <b>Выберите способ оплаты:</b>", buy_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_") and data not in ["ton_pay", "ton_cancel"] and not data.startswith("ton_check_") and not data.startswith("ton_confirm_") and not data.startswith("ton_cancel_") and not data.startswith("ton_back_"):
        days_map = {"ton_1": 1, "ton_3": 3, "ton_7": 7, "ton_30": 30}
        prices = {"ton_1": "1.5", "ton_3": "2.5", "ton_7": "4", "ton_30": "10"}
        if data in days_map:
            days = days_map[data]; price = prices[data]
            code = generate_code()
            save_ton_pending(code, user.id, days, price, f"{days} дней", is_custom=False)
            text = f"💎 <b>Оплата TON</b>\n\n📤 Кошелёк:\n<code>{TON_WALLET}</code>\n\n💰 Сумма: <b>{price} TON</b>\n📅 Подписка: <i>{days} дней</i>\n\n📝 Комментарий к переводу (обязательно):\n<code>{code}</code>\n\n<i>⚠️ После перевода нажмите «Проверить»</i>"
            msg = await send_without_quote(context, user.id, text, ton_confirm_menu(code, days, user.id))
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return

    if data.startswith("ton_check_"):
        parts = data.split("_")
        code = parts[2]
        pending = get_ton_pending(code)
        if not pending:
            await query.answer("❌ Данные заказа потеряны. Начните заново.", show_alert=True)
            return
        target_user_id = pending["user_id"]
        price = pending["price"]
        term_text = pending["term_text"]
        user_data = get_user(target_user_id)
        username = user_data[1] if user_data and user_data[1] != "NULL" else f"id{target_user_id}"
        add_ton_record(target_user_id, user_data[1] if user_data else None, price, "ожидает проверки")
        admin_text = f"🔍 <b>Проверка оплаты TON</b>\n\n👤 @{username} купил подписку на <i>{term_text}</i>\n💰 Сумма: <b>{price} TON</b>\n📝 Код: <code>{code}</code>"
        msg = await send_without_quote(context, ADMIN_ID, admin_text, ton_admin_menu(code, 0, target_user_id))
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        await query.answer("✅ Запрос отправлен администратору!", show_alert=True)
        try: await query.message.delete()
        except: pass
        msg = await send_with_photo(context, user.id, "⏳ <b>Ожидайте подтверждения</b> от администратора.", main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    if data.startswith("ton_cancel_admin_"):
        code = data.replace("ton_cancel_admin_", "")
        msg = await send_without_quote(context, ADMIN_ID, "⚠️ <b>Вы уверены, что хотите отменить заказ?</b>", ton_cancel_confirm_menu(code, 0, 0))
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_cancel_final_"):
        code = data.replace("ton_cancel_final_", "")
        pending = get_ton_pending(code)
        if pending:
            user_data = get_user(pending["user_id"])
            username = user_data[1] if user_data and user_data[1] != "NULL" else f"id{pending['user_id']}"
            update_ton_status(pending["user_id"], pending["price"], "отменено")
            remove_ton_pending(code)
            log_event(f"💎 TON отменён: code={code}")
            msg = await send_with_photo(context, ADMIN_ID, f"❌ <b>Заказ отменён</b> для @{username}", admin_main_menu())
        else:
            msg = await send_with_photo(context, ADMIN_ID, "❌ <b>Заказ не найден</b>", admin_main_menu())
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_back_"):
        code = data.replace("ton_back_", "")
        pending = get_ton_pending(code)
        if pending:
            user_data = get_user(pending["user_id"])
            username = user_data[1] if user_data and user_data[1] != "NULL" else f"id{pending['user_id']}"
            admin_text = f"🔍 <b>Проверка оплаты TON</b>\n\n👤 @{username} купил подписку на <i>{pending['term_text']}</i>\n💰 Сумма: <b>{pending['price']} TON</b>\n📝 Код: <code>{code}</code>"
            msg = await send_without_quote(context, ADMIN_ID, admin_text, ton_admin_menu(code, 0, pending["user_id"]))
            await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_confirm_"):
        code = data.replace("ton_confirm_", "")
        pending = get_ton_pending(code)
        if not pending:
            await query.answer("❌ Данные заказа потеряны.", show_alert=True)
            return
        target_user_id = pending["user_id"]
        price = pending["price"]
        term_text = pending["term_text"]
        days_or_sec = pending["days_or_sec"]
        user_data = get_user(target_user_id)
        if not user_data:
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return
        username = user_data[1] if user_data[1] != "NULL" else f"id{target_user_id}"
        update_ton_status(target_user_id, price, "подтверждено")
        if days_or_sec == "forever":
            set_subscription(target_user_id, "forever")
            await send_subscription_notification(context, target_user_id, "навсегда", source="purchase")
        elif str(days_or_sec).isdigit():
            sec = int(days_or_sec)
            if sec <= 3650: sec = sec * 86400
            end_date = (datetime.datetime.now() + datetime.timedelta(seconds=sec)).isoformat()
            set_subscription(target_user_id, end_date)
            await send_subscription_notification(context, target_user_id, term_text, source="purchase")
        remove_ton_pending(code)
        await query.answer("✅ Подписка оформлена!", show_alert=True)
        try: await query.message.delete()
        except: pass
        msg = await send_with_photo(context, ADMIN_ID, f"✅ <b>Подписка выдана</b> @{username} на <i>{term_text}</i>", admin_main_menu())
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        return

    if data == "back_main":
        msg = await send_with_photo(context, user.id, f"{EMOJI_WELCOME} <b>Добро пожаловать в Baikall Snos</b> {EMOJI_WELCOME}", main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "send":
        msg = await send_with_photo(context, user.id, f"{EMOJI_SEND} <b>Выберите цель для сноса:</b>", send_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "profile":
        user_data = get_user(user.id)
        if has_subscription(user.id):
            status = "✅ <b>Активна</b>"
            if user_data[2] == "forever": till = "Навсегда"
            else:
                try: till = datetime.datetime.fromisoformat(user_data[2]).strftime("%d.%m.%Y")
                except: till = user_data[2]
        else:
            status = "❌ <b>Не активна</b>"; till = "—"
        text = f"{EMOJI_PROFILE} <b>Ваш профиль</b>\n\n🆔 ID: <code>{user.id}</code>\n👤 Юзернейм: <i>@{user.username or 'Не указан'}</i>\n🛡 Подписка: {status}\n📅 Действует до: <i>{till}</i>"
        msg = await send_with_photo(context, user.id, text, profile_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "promo":
        msg = await send_with_photo(context, user.id, "🎟 <b>Введите подарочный код:</b>", promo_enter_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "buy":
        msg = await send_with_photo(context, user.id, "💳 <b>Выберите способ оплаты:</b>", buy_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "stars":
        msg = await send_with_photo(context, user.id, "⭐ <b>Выберите тариф:</b>", stars_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "own_sub_stars":
        text = "⏱ <b>Своя подписка</b>\n\n<i>Подписку можно покупать не менее 1 дня.</i>\nНапишите в поддержку свой срок и сумму — админ вышлет вам счёт.\n\n📋 <b>Скопируй и отправь в поддержку:</b>\n<i>«Привет хочу купить подписку по своему времени»</i>"
        msg = await send_with_photo(context, user.id, text, own_sub_menu("stars"))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "own_sub_ton":
        text = "⏱ <b>Своя подписка</b>\n\n<i>Подписку можно покупать не менее 1 дня.</i>\nНапишите в поддержку свой срок и сумму — админ вышлет вам счёт.\n\n📋 <b>Скопируй и отправь в поддержку:</b>\n<i>«Привет хочу купить подписку по своему времени»</i>"
        msg = await send_with_photo(context, user.id, text, own_sub_menu("ton_pay"))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("pay_"):
        days_map = {"pay_1": (1, 500), "pay_3": (3, 1000), "pay_7": (7, 2000), "pay_30": (30, 5000)}
        if data in days_map:
            days, price = days_map[data]
            ok = await send_invoice(user.id, context, days, price)
            if ok:
                try: await query.message.delete()
                except: pass
        return

    if data in ["snos_acc", "snos_bot", "snos_group", "snos_channel"]:
        action = data.replace("snos_", "")
        context.user_data["snos_action"] = action
        msg = await send_with_photo(context, user.id, "<b>Введите ссылку или юзернейм цели:</b>", snos_input_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("method_"):
        parts = data.split("_")
        action = parts[1]; method = parts[2]
        target = context.user_data.get('snos_target')
        if not target:
            await query.answer("❌ Цель не найдена.", show_alert=True); return
        if is_whitelisted(target):
            await query.answer("❌ Отказано, пользователь в white list", show_alert=True); return
        context.user_data["snos_method"] = method
        methods_text = {"universal": "🌐 Универсальный", "spam": "📨 Спам", "porno": "🔞 Порнография", "phone": "📱 Физ. номер"}
        method_name = methods_text.get(method, "🌐 Универсальный")
        text = f"🎯 Цель: <code>{target}</code>\n📋 Метод: <i>{method_name}</i>\n\n<b>🚀 Запустить процесс?</b>"
        msg = await send_with_photo(context, user.id, text, confirm_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "confirm_yes":
        target = context.user_data.get('snos_target')
        method = context.user_data.get('snos_method')
        if not target or not method:
            await query.answer("❌ Ошибка.", show_alert=True); return
        if is_whitelisted(target):
            await query.answer("❌ Отказано, white list", show_alert=True); return
        try: await query.message.delete()
        except: pass
        methods_text = {"universal": "🌐 Универсальный", "spam": "📨 Спам", "porno": "🔞 Порнография", "phone": "📱 Физ. номер"}
        method_name = methods_text.get(method, "🌐 Универсальный")
        log_event(f"🚀 Запуск сноса: юзер {user.id} → {target} ({method_name})")
        if not is_cooldown_off(user.id):
            set_cooldown(user.id, COOLDOWN_SECONDS)
        reports_count = random.randint(90, 295)
        await send_progress_message(context, user.id, target, reports_count, method_name)
        return

    if data == "confirm_no":
        msg = await send_with_photo(context, user.id, f"{EMOJI_WELCOME} <b>Добро пожаловать в Baikall Snos</b> {EMOJI_WELCOME}", main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

# ========== TEXT HANDLER ==========
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if user.id == ADMIN_ID and context.user_data.get("whitelist_action"):
        action = context.user_data["whitelist_action"]
        try: await update.message.delete()
        except: pass
        if action == "add":
            add_to_whitelist(text)
            reply = f"✅ <i>@{normalize_username(text)}</i> <b>добавлен в вайт-лист.</b>"
        else:
            remove_from_whitelist(text)
            reply = f"✅ <i>@{normalize_username(text)}</i> <b>удалён из вайт-листа.</b>"
        context.user_data.pop("whitelist_action", None)
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        msg = await send_with_photo(context, user.id, reply, admin_whitelist_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    if user.id == ADMIN_ID and context.user_data.get("broadcast_step") == "waiting_text":
        context.user_data["broadcast_text"] = text
        context.user_data["broadcast_step"] = "preview"
        try: await update.message.delete()
        except: pass
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        text_msg = f"📢 <b>Предпросмотр рассылки:</b>\n\n<i>{text}</i>"
        msg = await send_with_photo(context, user.id, text_msg, broadcast_preview_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    if user.id == ADMIN_ID and context.user_data.get("acp_step") == "price":
        acp_type = context.user_data.get("acp_type")
        try:
            val = float(text)
            if acp_type == "stars": val = int(val)
            context.user_data["acp_price"] = val
            context.user_data["acp_step"] = "term"
            try: await update.message.delete()
            except: pass
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, "📅 <b>Выберите срок подписки:</b>", admin_create_payment_term_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
        except:
            try: await update.message.delete()
            except: pass
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, "❌ <b>Введите число!</b>", admin_input_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
        return

    if user.id == ADMIN_ID and context.user_data.get("acp_step") == "custom_time":
        seconds = parse_time(text)
        try: await update.message.delete()
        except: pass
        if seconds == 0:
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, "❌ <b>Неверный формат.</b>", admin_input_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        context.user_data["acp_term_seconds"] = seconds
        context.user_data["acp_term_text"] = seconds_to_text(seconds)
        context.user_data["acp_step"] = "username"
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        msg = await send_with_photo(context, user.id, "👤 <b>Введите ID или @username получателя:</b>", admin_input_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    if user.id == ADMIN_ID and context.user_data.get("acp_step") == "username":
        try: await update.message.delete()
        except: pass
        target = None
        if text.isdigit(): target = get_user(int(text))
        if not target: target = get_user_by_username(text)
        if not target:
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, f"❌ <b>Пользователь</b> <code>{text}</code> <b>не найден в БД.</b>", admin_input_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        context.user_data["acp_target_id"] = target[0]
        context.user_data["acp_step"] = "confirm"
        acp_type = context.user_data["acp_type"]
        acp_price = context.user_data["acp_price"]
        acp_term_text = context.user_data["acp_term_text"]
        username = target[1] if target[1] != "NULL" else f"id{target[0]}"
        type_label = "⭐ Stars" if acp_type == "stars" else "💎 TON"
        text_msg = f"💳 <b>Проверьте счёт:</b>\n\n👤 Получатель: <i>@{username}</i> (ID <code>{target[0]}</code>)\n💰 Сумма: <b>{acp_price} {type_label}</b>\n📅 Срок: <i>{acp_term_text}</i>"
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        msg = await send_with_photo(context, user.id, text_msg, admin_create_payment_confirm_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    if user.id == ADMIN_ID and context.user_data.get("admin_action") == "custom_time":
        target_id_str = context.user_data.get("admin_custom_user_id")
        if not target_id_str:
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, "❌ <b>Ошибка.</b>", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await update.message.delete()
            except: pass
            return
        target_id = int(target_id_str)
        seconds = parse_time(text.strip())
        try: await update.message.delete()
        except: pass
        if seconds == 0:
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, "❌ <b>Неверный формат.</b>", admin_input_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        user_data = get_user(target_id)
        username = user_data[1] if user_data and user_data[1] != "NULL" else f"id{target_id}"
        end_date = (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).isoformat()
        set_subscription(target_id, end_date)
        await send_subscription_notification(context, target_id, seconds_to_text(seconds), source="admin")
        log_event(f"🛡 Выдана кастомная подписка {target_id}")
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        text_msg = f"✅ <b>Подписка выдана</b> @{username} (ID: <code>{target_id}</code>) на <i>{seconds_to_text(seconds)}</i>"
        msg = await send_with_photo(context, user.id, text_msg, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        context.user_data.pop("admin_action", None)
        context.user_data.pop("admin_custom_user_id", None)
        return

    if user.id == ADMIN_ID and "admin_action" in context.user_data:
        action = context.user_data["admin_action"]
        text_input = text.strip()
        try: await update.message.delete()
        except: pass
        user_data = get_user(int(text_input)) if text_input.isdigit() else None
        if not user_data: user_data = get_user_by_username(text_input)
        if not user_data:
            all_users = get_all_users()
            users_list = "\n".join([f"• ID: <code>{u[0]}</code> | @{u[1] if u[1] != 'NULL' else 'без юзернейма'}" for u in all_users]) if all_users else "пусто"
            text_msg = f"❌ <b>Пользователь не найден.</b>\n<i>Вы ввели:</i> <code>{text_input}</code>\n\n📋 <b>Список в БД:</b>\n{users_list}"
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, text_msg, admin_input_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        target_id = user_data[0]
        clean_username = user_data[1] if user_data[1] != "NULL" else f"id{target_id}"
        if action == "remove":
            remove_subscription(target_id)
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            text_msg = f"❌ <b>Подписка забрана</b> у @{clean_username} (ID: <code>{target_id}</code>)"
            msg = await send_with_photo(context, user.id, text_msg, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            context.user_data.pop("admin_action", None)
            return
        elif action == "give":
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            text_msg = f"👤 <b>Выдача подписки</b> для @{clean_username}\n🆔 ID: <code>{target_id}</code>\n\n<b>Выберите срок:</b>"
            msg = await send_with_photo(context, user.id, text_msg, admin_days_menu(target_id))
            await add_message_to_delete(context, user.id, user.id, msg)
            context.user_data.pop("admin_action", None)
            return

    if "promo_step" in context.user_data:
        step = context.user_data["promo_step"]
        if step == "activations": await create_promo_step2(update, context, text); return
        elif step == "subscription_days": await create_promo_step3(update, context, text); return
        elif step == "expiry_date": await create_promo_step4(update, context, text); return
        elif step == "name": await create_promo_finish(update, context, text); return
        elif step == "extend_date":
            try:
                datetime.datetime.strptime(text, "%d.%m.%Y")
                update_promocode(context.user_data["promo_extend_id"], "expiry_date", text)
                for k in ["promo_step", "promo_extend_id"]: context.user_data.pop(k, None)
                await delete_previous_messages(context, user.id, user.id, keep_first=True)
                msg = await send_with_photo(context, user.id, f"✅ <b>Дата продлена до</b> <i>{text}</i>", admin_main_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
            except:
                msg = await send_with_photo(context, user.id, "❌ <b>Неверный формат!</b>", admin_back_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
            return
        elif step == "add_activations":
            try:
                count = int(text)
                promo = get_promocode_by_id(context.user_data["promo_add_activations_id"])
                if promo: update_promocode(promo[0], "max_activations", promo[2] + count)
                for k in ["promo_step", "promo_add_activations_id"]: context.user_data.pop(k, None)
                await delete_previous_messages(context, user.id, user.id, keep_first=True)
                msg = await send_with_photo(context, user.id, f"✅ <b>Добавлено</b> <code>{count}</code> <b>активаций</b>", admin_main_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
            except:
                msg = await send_with_photo(context, user.id, "❌ <b>Введите число!</b>", admin_back_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
            return
        elif step == "add_subscription":
            try:
                days = int(text)
                update_promocode(context.user_data["promo_add_subscription_id"], "subscription_days", days)
                for k in ["promo_step", "promo_add_subscription_id"]: context.user_data.pop(k, None)
                await delete_previous_messages(context, user.id, user.id, keep_first=True)
                msg = await send_with_photo(context, user.id, f"✅ <b>Подписка обновлена на</b> <code>{days}</code> <b>дней</b>", admin_main_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
            except:
                msg = await send_with_photo(context, user.id, "❌ <b>Введите число!</b>", admin_back_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
            return

    if not text.startswith("/") and "admin_action" not in context.user_data and "whitelist_action" not in context.user_data and "snos_action" not in context.user_data and "acp_step" not in context.user_data and "broadcast_step" not in context.user_data:
        promo = get_promocode_by_name(text)
        if promo:
            success, message = activate_promocode(promo[0], user.id)
            if success:
                days = promo[4]
                end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
                set_subscription(user.id, end_date)
                text_reply = f"✅ <b>Промокод активирован!</b> <i>Подписка на</i> <code>{days}</code> <i>дней оформлена</i> 🎉"
            else:
                text_reply = f"❌ <b>{message}</b>"
        else:
            text_reply = "❌ <b>Промокод не найден или неактивен.</b>"
        try: await update.message.delete()
        except: pass
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        msg = await send_with_photo(context, user.id, text_reply, promo_enter_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    if "snos_action" in context.user_data and not text.startswith("/"):
        target = text
        context.user_data["snos_target"] = target
        if is_whitelisted(target):
            try: await update.message.delete()
            except: pass
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, "❌ <b>Отказано, пользователь находится в white list</b>", main_menu(user.id))
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        try: await update.message.delete()
        except: pass
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        action = context.user_data["snos_action"]
        text_msg = f"✅ <b>Цель сохранена:</b> <code>{text}</code>\n\n<b>Выберите метод:</b>"
        msg = await send_with_photo(context, user.id, text_msg, method_menu(action))
        await add_message_to_delete(context, user.id, user.id, msg)
        return

# ========== PRE_CHECKOUT ==========
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("sub_") or query.invoice_payload.startswith("custom_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Что-то пошло не так...")

# ========== УСПЕШНАЯ ОПЛАТА ==========
async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = message.from_user
    payload = message.successful_payment.invoice_payload
    total_amount = message.successful_payment.total_amount

    if payload.startswith("custom_"):
        parts = payload.split("_")
        if len(parts) >= 3:
            term = parts[1]
            if term == "f":
                set_subscription(user.id, "forever")
                user_data = get_user(user.id)
                username = user_data[1] if user_data and user_data[1] != "NULL" else None
                add_payment(user.id, username, "forever", total_amount, custom=True)
                await send_subscription_notification(context, user.id, "навсегда", source="purchase")
                log_event(f"💰 Кастомная оплата (Stars, навсегда): {user.id}")
            else:
                sec = int(term)
                if sec <= 3650: sec = sec * 86400
                end_date = (datetime.datetime.now() + datetime.timedelta(seconds=sec)).isoformat()
                set_subscription(user.id, end_date)
                user_data = get_user(user.id)
                username = user_data[1] if user_data and user_data[1] != "NULL" else None
                add_payment(user.id, username, seconds_to_text(sec), total_amount, custom=True)
                await send_subscription_notification(context, user.id, seconds_to_text(sec), source="purchase")
                log_event(f"💰 Кастомная оплата (Stars): {user.id} - {seconds_to_text(sec)}")
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"💰 Кастомная оплата звёздами\n👤 ID: {user.id}\n💵 Сумма: {total_amount}⭐")
        except: pass
        return

    if payload.startswith("sub_"):
        parts = payload.split("_")
        if len(parts) >= 2:
            days = int(parts[1])
            end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
            set_subscription(user.id, end_date)
            user_data = get_user(user.id)
            username = user_data[1] if user_data and user_data[1] != "NULL" else None
            add_payment(user.id, username, days, total_amount)
            await send_subscription_notification(context, user.id, f"{days} дней", source="purchase")
            text_msg = f"✅ <b>Оплата прошла успешно!</b>\n🎉 Подписка на <code>{days}</code> дней активирована ✅"
            msg = await send_with_photo(context, user.id, text_msg, main_menu(user.id))
            await add_message_to_delete(context, user.id, user.id, msg)
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"💰 Оплата звёздами\n👤 ID: {user.id}\n📅 {days} дней\n💵 {total_amount}⭐")
            except: pass

# ========== POST INIT ==========
async def post_init(app):
    asyncio.create_task(cooldown_watcher(app))
    log_event("🕒 Фоновый watcher кулдаунов запущен")

# ========== STARTUP ==========
def startup_report():
    log_event("=" * 50)
    log_event("✅ Запуск Baikall Snos")
    log_event(f"📅 Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    log_event(f"👤 Админ ID: {ADMIN_ID}")
    log_event(f"👥 Юзеров: {len(get_all_users())}")
    log_event(f"🎟 Промокодов: {len(get_all_promocodes())}")
    log_event(f"⬜ Вайт-лист: {len(get_whitelist())}")
    log_event(f"📋 Логов сноса: {len(get_all_report_logs())}")
    log_event(f"⏳ Активных кулдаунов: {len(get_all_active_cooldowns())}")
    log_event(f"🖼 PHOTO_URL: {PHOTO_URL}")
    log_event("✅ Бот готов к работе")
    log_event("=" * 50)

def main():
    startup_report()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    log_event("🚀 Polling запущен")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
