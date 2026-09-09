import datetime
import re
import logging
import asyncio
import random
import string
import io
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler
from supabase import create_client, Client

# ========== КОНФИГ ==========
BOT_TOKEN = "8913797082:AAE-AJSs1GyJ6JzMojYiVxrOiNUJXAiYo-k"
ADMIN_ID = 8736990603
PROVIDER_TOKEN = ""
PHOTO_PATH = "photo.jpg"
TON_WALLET = "UQBZtQCKRxk6UnEA_8G8sA99J3JxhA6F-ODCM5aLdAfdECfC"

# ========== SUPABASE ==========
SUPABASE_URL = "https://ckjfruhisdnmfulkcjrz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNramZydWhpc2RubWZ1bGtjanJ6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg5NzgzNTIsImV4cCI6MjEwNDU1NDM1Mn0.2071Yig1Gk_CFUEwt1vTNcUyZxQE_F74q0u44Lpdkdc"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== ПРЕМИУМ ЭМОДЗИ ==========
EMOJI_WELCOME = '<tg-emoji emoji-id="5343833386681148365">👋</tg-emoji>'
EMOJI_SEND = '<tg-emoji emoji-id="5343766642889367448">📤</tg-emoji>'
EMOJI_PROFILE = '<tg-emoji emoji-id="5417955880735906834">👤</tg-emoji>'

logging.basicConfig(level=logging.INFO)

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С БД ==========

def normalize_username(username):
    if username:
        return username.replace("@", "").strip().lower()
    return None

# ===== USERS =====
def get_user(user_id):
    try:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        data = result.data
        if data:
            return (data[0]["user_id"], data[0].get("username"), data[0].get("subscription_end"))
        return None
    except Exception as e:
        logging.error(f"get_user error: {e}")
        return None

def get_user_by_username(username):
    username = normalize_username(username)
    if not username:
        return None
    try:
        result = supabase.table("users").select("*").eq("username", username).execute()
        data = result.data
        if data:
            return (data[0]["user_id"], data[0].get("username"), data[0].get("subscription_end"))
        return None
    except Exception as e:
        logging.error(f"get_user_by_username error: {e}")
        return None

def get_all_users():
    try:
        result = supabase.table("users").select("*").execute()
        return [(u["user_id"], u.get("username"), u.get("subscription_end")) for u in result.data]
    except Exception as e:
        logging.error(f"get_all_users error: {e}")
        return []

def set_subscription(user_id, end_date):
    try:
        existing = get_user(user_id)
        if existing:
            supabase.table("users").update({"subscription_end": end_date}).eq("user_id", user_id).execute()
        else:
            supabase.table("users").insert({"user_id": user_id, "subscription_end": end_date}).execute()
    except Exception as e:
        logging.error(f"set_subscription error: {e}")

def remove_subscription(user_id):
    try:
        supabase.table("users").update({"subscription_end": None}).eq("user_id", user_id).execute()
    except Exception as e:
        logging.error(f"remove_subscription error: {e}")

def has_subscription(user_id):
    data = get_user(user_id)
    if data and data[2]:
        if data[2] == "forever":
            return True
        try:
            end_date = datetime.datetime.fromisoformat(data[2])
            return end_date > datetime.datetime.now()
        except:
            return False
    return False

def add_user(user_id, username):
    try:
        existing = get_user(user_id)
        if not existing:
            supabase.table("users").insert({"user_id": user_id, "username": normalize_username(username)}).execute()
    except Exception as e:
        logging.error(f"add_user error: {e}")

# ===== WHITELIST =====
def add_to_whitelist(username):
    username = normalize_username(username)
    try:
        existing = supabase.table("whitelist").select("*").eq("username", username).execute()
        if not existing.data:
            supabase.table("whitelist").insert({"username": username, "added_at": datetime.datetime.now().isoformat()}).execute()
    except Exception as e:
        logging.error(f"add_to_whitelist error: {e}")

def remove_from_whitelist(username):
    try:
        supabase.table("whitelist").delete().eq("username", normalize_username(username)).execute()
    except Exception as e:
        logging.error(f"remove_from_whitelist error: {e}")

def is_whitelisted(username):
    try:
        result = supabase.table("whitelist").select("*").eq("username", normalize_username(username)).execute()
        return len(result.data) > 0
    except Exception as e:
        logging.error(f"is_whitelisted error: {e}")
        return False

def get_whitelist():
    try:
        result = supabase.table("whitelist").select("*").execute()
        return [(u["username"], u["added_at"]) for u in result.data]
    except Exception as e:
        logging.error(f"get_whitelist error: {e}")
        return []

# ===== PROMOCODES =====
def create_promocode(name, max_activations, subscription_days, expiry_date):
    try:
        result = supabase.table("promocodes").insert({
            "name": name,
            "max_activations": max_activations,
            "subscription_days": subscription_days,
            "expiry_date": expiry_date,
            "created_at": datetime.datetime.now().isoformat(),
            "active": 1
        }).execute()
        return result.data[0]["id"]
    except Exception as e:
        logging.error(f"create_promocode error: {e}")
        return None

def get_all_promocodes():
    try:
        result = supabase.table("promocodes").select("*").order("id", desc=True).execute()
        return [(u["id"], u["name"], u["max_activations"], u["used_activations"], u["subscription_days"], u["expiry_date"], u["created_at"], u["active"]) for u in result.data]
    except Exception as e:
        logging.error(f"get_all_promocodes error: {e}")
        return []

def get_promocode_by_id(promo_id):
    try:
        result = supabase.table("promocodes").select("*").eq("id", promo_id).execute()
        if result.data:
            u = result.data[0]
            return (u["id"], u["name"], u["max_activations"], u["used_activations"], u["subscription_days"], u["expiry_date"], u["created_at"], u["active"])
        return None
    except Exception as e:
        logging.error(f"get_promocode_by_id error: {e}")
        return None

def get_promocode_by_name(name):
    try:
        result = supabase.table("promocodes").select("*").eq("name", name).execute()
        if result.data:
            u = result.data[0]
            return (u["id"], u["name"], u["max_activations"], u["used_activations"], u["subscription_days"], u["expiry_date"], u["created_at"], u["active"])
        return None
    except Exception as e:
        logging.error(f"get_promocode_by_name error: {e}")
        return None

def delete_promocode(promo_id):
    try:
        supabase.table("promocodes").delete().eq("id", promo_id).execute()
    except Exception as e:
        logging.error(f"delete_promocode error: {e}")

def update_promocode(promo_id, field, value):
    try:
        supabase.table("promocodes").update({field: value}).eq("id", promo_id).execute()
    except Exception as e:
        logging.error(f"update_promocode error: {e}")

def activate_promocode(promo_id, user_id):
    try:
        promo = get_promocode_by_id(promo_id)
        if not promo:
            return False, "Промокод не найден"
        if promo[7] == 0:
            return False, "Промокод не активен"
        if promo[2] <= promo[3]:
            return False, "Лимит активаций исчерпан"
        
        supabase.table("promocode_activations").insert({
            "promo_id": promo_id,
            "user_id": user_id,
            "activated_at": datetime.datetime.now().isoformat()
        }).execute()
        supabase.table("promocodes").update({"used_activations": promo[3] + 1}).eq("id", promo_id).execute()
        return True, "Промокод активирован"
    except Exception as e:
        logging.error(f"activate_promocode error: {e}")
        return False, f"Ошибка: {e}"

# ===== REPORTS LOG =====
def add_report_log(user_id, username, target, method, reports_count):
    try:
        supabase.table("reports_log").insert({
            "user_id": user_id,
            "username": normalize_username(username),
            "target": target,
            "method": method,
            "reports_count": reports_count,
            "date": datetime.datetime.now().isoformat()
        }).execute()
    except Exception as e:
        logging.error(f"add_report_log error: {e}")

def get_all_report_logs():
    try:
        result = supabase.table("reports_log").select("*").order("id", desc=True).execute()
        users = {}
        for log in result.data:
            uid = log["user_id"]
            if uid not in users:
                users[uid] = log.get("username")
        return [(uid, users[uid]) for uid in users]
    except Exception as e:
        logging.error(f"get_all_report_logs error: {e}")
        return []

def get_report_logs_by_user(user_id):
    try:
        result = supabase.table("reports_log").select("*").eq("user_id", user_id).order("id", desc=True).execute()
        return [(u["id"], u["user_id"], u.get("username"), u["target"], u["method"], u["reports_count"], u["date"]) for u in result.data]
    except Exception as e:
        logging.error(f"get_report_logs_by_user error: {e}")
        return []

def get_report_log_by_id(log_id):
    try:
        result = supabase.table("reports_log").select("*").eq("id", log_id).execute()
        if result.data:
            u = result.data[0]
            return (u["id"], u["user_id"], u.get("username"), u["target"], u["method"], u["reports_count"], u["date"])
        return None
    except Exception as e:
        logging.error(f"get_report_log_by_id error: {e}")
        return None

# ========== ГЕНЕРАЦИЯ ==========
COUNTRY_CODES = {
    'BY': {'prefix': '+375', 'operators': ['25', '29', '33', '44']},
    'RU': {'prefix': '+7', 'operators': ['900', '901', '902', '903', '904', '905', '906', '909', '910', '911', '912', '913', '914', '915', '916', '917', '918', '919', '920', '921', '922', '923', '924', '925', '926', '927', '928', '929', '930', '931', '932', '933', '934', '935', '936', '937', '938', '939', '950', '951', '952', '953', '954', '955', '956', '957', '958', '959', '960', '961', '962', '963', '964', '965', '966', '967', '968', '969', '980', '981', '982', '983', '984', '985', '986', '987', '988', '989']},
    'UA': {'prefix': '+380', 'operators': ['50', '63', '66', '67', '68', '73', '93', '95', '96', '97', '98', '99']},
    'PL': {'prefix': '+48', 'operators': ['50', '51', '53', '57', '60', '66', '69', '72', '73', '78', '79', '88']},
    'US': {'prefix': '+1', 'operators': ['201', '202', '203', '205', '206', '207', '208', '209', '210', '212', '213', '214', '215', '216', '217', '218', '219', '220', '223', '224', '225', '226', '227', '228', '229', '230', '231', '234', '239', '240', '241', '242', '243', '244', '245', '246', '247', '248', '249', '250', '251', '252', '253', '254', '256', '260', '262', '267', '269', '270', '272', '273', '274', '275', '276', '277', '278', '279', '280', '281', '283', '284', '289', '301', '302', '303', '304', '305', '306', '307', '308', '309', '310', '312', '313', '314', '315', '316', '317', '318', '319', '320', '321', '323', '325', '327', '329', '330', '331', '332', '334', '336', '337', '339', '340', '341', '342', '343', '345', '346', '347', '348', '351', '352', '353', '354', '356', '357', '358', '359', '360', '361', '362', '363', '364', '365', '366', '367', '368', '369', '370', '371', '372', '373', '374', '375', '376', '377', '378', '379', '380', '381', '382', '383', '384', '385', '386', '387', '388', '389', '401', '402', '404', '405', '406', '407', '408', '409', '410', '411', '412', '413', '414', '415', '416', '417', '419', '420', '421', '423', '424', '425', '426', '427', '428', '429', '430', '431', '432', '433', '434', '435', '436', '437', '438', '439', '440', '441', '442', '443', '444', '445', '447', '448', '449', '450', '451', '452', '453', '454', '455', '456', '457', '458', '459', '460', '461', '462', '463', '464', '465', '466', '467', '468', '469', '470', '471', '472', '473', '474', '475', '476', '478', '479', '480', '481', '482', '483', '484', '485', '486', '487', '488', '489', '490', '491', '492', '493', '494', '495', '496', '497', '498', '500', '501', '502', '503', '504', '505', '506', '507', '508', '509']},
    'GB': {'prefix': '+44', 'operators': ['20', '30', '70', '71', '73', '74', '75', '77', '78', '79']}
}

def generate_real_number():
    country = random.choice(list(COUNTRY_CODES.keys()))
    country_data = COUNTRY_CODES[country]
    prefix = country_data['prefix']
    operator = random.choice(country_data['operators'])
    number = f"{prefix}{operator}{random.randint(1000000, 9999999)}"
    return number

def generate_snos_log(target, reports_count):
    numbers = []
    for i in range(reports_count):
        number = generate_real_number()
        if random.random() < 0.7:
            status = random.choice([' - валид ✅', ' - валид ✅', ' - валид ✅', ' - не валид ❌'])
        else:
            status = ' - не валид ❌'
        numbers.append(f"{number}{status}")
    
    log_content = (
        f"=== SNOS LOG ===\n"
        f"Цель: {target}\n"
        f"Всего проверок: {reports_count}\n"
        f"Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"{'='*30}\n\n"
        + "\n".join(numbers)
    )
    return log_content

def parse_time(time_str):
    seconds = 0
    time_str = time_str.lower().strip()
    parts = re.findall(r'(\d+)([dhm])', time_str)
    for value, unit in parts:
        value = int(value)
        if unit == 'd':
            seconds += value * 86400
        elif unit == 'h':
            seconds += value * 3600
        elif unit == 'm':
            seconds += value * 60
    return seconds

def generate_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

# ========== ОТПРАВКА СООБЩЕНИЙ ==========
async def send_with_photo(context, chat_id, text, reply_markup=None, parse_mode="HTML", reply_to_message_id=None):
    caption = f"<blockquote>{text}</blockquote>"
    try:
        with open(PHOTO_PATH, 'rb') as photo:
            msg = await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(photo),
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id
            )
            return msg
    except FileNotFoundError:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id
        )
        logging.warning(f"Файл {PHOTO_PATH} не найден.")
        return msg

async def send_without_quote(context, chat_id, text, reply_markup=None, parse_mode="HTML"):
    try:
        with open(PHOTO_PATH, 'rb') as photo:
            msg = await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(photo),
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return msg
    except FileNotFoundError:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        return msg

# ========== УДАЛЕНИЕ СООБЩЕНИЙ ==========
async def delete_previous_messages(context, chat_id, user_id, keep_first=True):
    if "messages_to_delete" not in context.user_data:
        context.user_data["messages_to_delete"] = {}
    if user_id not in context.user_data["messages_to_delete"]:
        context.user_data["messages_to_delete"][user_id] = []
    
    messages = context.user_data["messages_to_delete"][user_id]
    if keep_first and len(messages) > 0:
        messages_to_delete = messages[1:]
    else:
        messages_to_delete = messages
    
    for msg_id in messages_to_delete:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass
    
    if keep_first and len(messages) > 0:
        context.user_data["messages_to_delete"][user_id] = [messages[0]]
    else:
        context.user_data["messages_to_delete"][user_id] = []

async def add_message_to_delete(context, chat_id, user_id, message):
    if "messages_to_delete" not in context.user_data:
        context.user_data["messages_to_delete"] = {}
    if user_id not in context.user_data["messages_to_delete"]:
        context.user_data["messages_to_delete"][user_id] = []
    context.user_data["messages_to_delete"][user_id].append(message.message_id)

# ========== УВЕДОМЛЕНИЕ О ПОДПИСКЕ ==========
async def send_subscription_notification(context, user_id, days, source="purchase"):
    user_data = get_user(user_id)
    if not user_data:
        return
    if source == "purchase":
        text = f"🎉 Вы приобрели подписку в боте на {days} ⭐️"
    else:
        text = f"🎉 Вам выдали подписку на {days} ⭐️"
    await send_with_photo(context, user_id, text, main_menu(user_id))

# ========== ФИКТИВНЫЙ ОТЧЁТ ==========
async def schedule_fake_report(context, chat_id, target, reports_count):
    delay = random.randint(1800, 86400)
    
    async def send_fake_report():
        await asyncio.sleep(delay)
        fake_target = "MaksGoldKlad24"
        target_link = f"https://t.me/{fake_target}"
        report_text = (
            f"📊 **Уведомление о блокировке**\n\n"
            f"🎯 Аккаунт <a href='{target_link}'>{target}</a> был заморожен ✅\n"
            f"📤 Всего жалоб: {reports_count}\n"
            f"📅 Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Статус: Аккаунт заблокирован за нарушение правил."
        )
        msg = await send_without_quote(context, chat_id, report_text, parse_mode="HTML")
        await add_message_to_delete(context, chat_id, chat_id, msg)
    
    asyncio.create_task(send_fake_report())

# ========== ПРОГРЕСС-БАР ==========
async def send_progress_message(context, chat_id, target, reports_count, method_name):
    await send_without_quote(context, chat_id, f"🚀 Запущен процесс отправки репортов на {target}\n📋 Метод: {method_name}\n\n🔄 Подготовка...")
    await asyncio.sleep(2)
    
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🚀 Отправка репортов на {target}\n📋 Метод: {method_name}\n\n🔄 Инициализация..."
    )
    
    for i in range(1, reports_count + 1):
        percent = int((i / reports_count) * 100)
        bar_length = 25
        filled = int(bar_length * i / reports_count)
        bar = "▓" * filled + "░" * (bar_length - filled)
        progress_text = (
            f"🚀 Отправка репортов на {target}\n"
            f"📋 Метод: {method_name}\n"
            f"📊 Прогресс: {percent}% | {i}/{reports_count}\n\n"
            f"{bar}\n\n"
            f"⏳ Осталось ~{random.randint(5, 30)} сек."
        )
        try:
            await msg.edit_text(text=progress_text)
        except:
            pass
        await asyncio.sleep(random.uniform(0.03, 0.08))
    
    log_content = generate_snos_log(target, reports_count)
    log_file = io.BytesIO(log_content.encode('utf-8'))
    log_file.name = f"Snos_{target.replace('@', '')}_Logs.txt"
    await context.bot.send_document(
        chat_id=chat_id,
        document=InputFile(log_file, filename=log_file.name),
        caption=f"📄 Лог сноса для {target}"
    )
    
    # ========== ИСПРАВЛЕНИЕ БАГА 1: СОХРАНЯЕМ ЮЗЕРНЕЙМ ==========
    user_data = get_user(chat_id)
    username = user_data[1] if user_data else None
    add_report_log(chat_id, username, target, method_name, reports_count)
    # =============================================================
    
    final_text = (
        f"✅ Успешно!\n\n"
        f"🎯 Цель: {target}\n"
        f"📋 Метод: {method_name}\n"
        f"📤 Отправлено репортов: {reports_count}\n\n"
        f"⏳ Принятие репортов может занять до 24-48 часов.\n"
        f"📄 Отчёт сохранён в файле выше."
    )
    await send_with_photo(context, chat_id, final_text, main_menu(chat_id))
    await schedule_fake_report(context, chat_id, target, reports_count)
    return reports_count

# ========== КЛАВИАТУРЫ ==========
def main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("📤 Отправка", callback_data="send"),
         InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📞 Поддержка", url="https://t.me/Intornational"),
         InlineKeyboardButton("📢 Наш канал", url="https://t.me/baikallShop")],
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🔐 Админка", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def profile_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 Промокод", callback_data="promo")],
        [InlineKeyboardButton("💳 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])

def buy_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Звёздами", callback_data="stars")],
        [InlineKeyboardButton("💎 TON", callback_data="ton_pay")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ])

def stars_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 1 день - 75 ⭐ (TEST)", callback_data="pay_test")],
        [InlineKeyboardButton("1 день - 500 ⭐", callback_data="pay_1")],
        [InlineKeyboardButton("3 дня - 1000 ⭐", callback_data="pay_3")],
        [InlineKeyboardButton("7 дней - 2000 ⭐", callback_data="pay_7")],
        [InlineKeyboardButton("30 дней - 5000 ⭐", callback_data="pay_30")],
        [InlineKeyboardButton("🔙 Назад", callback_data="buy")]
    ])

def ton_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 день - 7.5 TON", callback_data="ton_1")],
        [InlineKeyboardButton("3 дня - 12.5 TON", callback_data="ton_3")],
        [InlineKeyboardButton("7 дней - 15 TON", callback_data="ton_7")],
        [InlineKeyboardButton("30 дней - 20 TON", callback_data="ton_30")],
        [InlineKeyboardButton("🔙 Назад", callback_data="buy")]
    ])

def ton_confirm_menu(code, days, username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="ton_cancel")],
        [InlineKeyboardButton("🔍 Проверить", callback_data=f"ton_check_{code}_{days}_{username}")]
    ])

def ton_admin_menu(code, days, username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Принять", callback_data=f"ton_confirm_{code}_{days}_{username}"),
         InlineKeyboardButton("❌ Отменить", callback_data=f"ton_cancel_admin_{code}_{days}_{username}")]
    ])

def ton_cancel_confirm_menu(code, days, username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Точно отменить", callback_data=f"ton_cancel_final_{code}_{days}_{username}"),
         InlineKeyboardButton("🔙 Назад", callback_data=f"ton_back_{code}_{days}_{username}")]
    ])

def admin_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Выдать подписку", callback_data="admin_give"),
         InlineKeyboardButton("❌ Забрать подписку", callback_data="admin_remove")],
        [InlineKeyboardButton("🎟 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton("📋 Промокоды", callback_data="admin_list_promo")],
        [InlineKeyboardButton("📄 Выдать лог", callback_data="admin_send_log")],
        [InlineKeyboardButton("⬜ Вайт-лист", callback_data="admin_whitelist")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])

def admin_back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ])

def admin_whitelist_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить", callback_data="whitelist_add")],
        [InlineKeyboardButton("🗑 Удалить", callback_data="whitelist_remove")],
        [InlineKeyboardButton("📋 Список", callback_data="whitelist_list")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ])

def admin_days_menu(username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 day", callback_data=f"admin_day_{username}_1"),
         InlineKeyboardButton("3 day", callback_data=f"admin_day_{username}_3")],
        [InlineKeyboardButton("7 day", callback_data=f"admin_day_{username}_7"),
         InlineKeyboardButton("30 day", callback_data=f"admin_day_{username}_30")],
        [InlineKeyboardButton("∞ day", callback_data=f"admin_day_{username}_forever"),
         InlineKeyboardButton("⏱ Своё время", callback_data=f"admin_custom_{username}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_give")]
    ])

def send_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Снос аккаунта", callback_data="snos_acc")],
        [InlineKeyboardButton("🤖 Снос бота", callback_data="snos_bot")],
        [InlineKeyboardButton("👥 Снос группы", callback_data="snos_group")],
        [InlineKeyboardButton("📢 Снос канала", callback_data="snos_channel")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ])

def method_menu(action):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Универсальный", callback_data=f"method_{action}_universal")],
        [InlineKeyboardButton("📨 Спам", callback_data=f"method_{action}_spam")],
        [InlineKeyboardButton("🔞 Порнография", callback_data=f"method_{action}_porno")],
        [InlineKeyboardButton("📱 Физ. номер", callback_data=f"method_{action}_phone")],
        [InlineKeyboardButton("🔙 Назад", callback_data="send")]
    ])

def confirm_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да", callback_data="confirm_yes"),
         InlineKeyboardButton("❌ Нет", callback_data="confirm_no")]
    ])

# ========== ОПЛАТА ЗВЁЗДАМИ ==========
def create_invoice(days, price):
    return {
        "title": f"Подписка Baikall на {days} дней",
        "description": f"Доступ к функции сноса на {days} дней",
        "currency": "XTR",
        "prices": [LabeledPrice(label=f"{days} дней", amount=price)],
        "start_parameter": f"sub_{days}",
        "payload": f"sub_{days}_{price}"
    }

async def send_invoice(update, context, days, price):
    user = update.effective_user if update.effective_user else update.callback_query.from_user
    invoice_data = create_invoice(days, price)
    try:
        await context.bot.send_invoice(
            chat_id=user.id,
            title=invoice_data["title"],
            description=invoice_data["description"],
            payload=invoice_data["payload"],
            provider_token=PROVIDER_TOKEN,
            currency=invoice_data["currency"],
            prices=invoice_data["prices"],
            start_parameter=invoice_data["start_parameter"],
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка отправки счёта: {e}")
        return False

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = normalize_username(user.username)
    add_user(user.id, username)
    text = f"{EMOJI_WELCOME} Добро пожаловать в Baikall Snos {EMOJI_WELCOME}"
    msg = await send_with_photo(context, user.id, text, main_menu(user.id))
    if "messages_to_delete" not in context.user_data:
        context.user_data["messages_to_delete"] = {}
    if user.id not in context.user_data["messages_to_delete"]:
        context.user_data["messages_to_delete"][user.id] = []
    context.user_data["messages_to_delete"][user.id].append(msg.message_id)

# ===== СОЗДАНИЕ ПРОМОКОДА (ШАГИ) =====
async def create_promo_step1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
    context.user_data["promo_step"] = "activations"
    text = "🎟 Введите количество активаций для промокода:"
    msg = await send_with_photo(context, update.effective_user.id, text, admin_back_menu())
    await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_step2(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    try:
        max_activations = int(text)
        context.user_data["promo_max_activations"] = max_activations
        context.user_data["promo_step"] = "subscription_days"
        await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
        text = "⏱ Введите количество дней подписки (цифрой):"
        msg = await send_with_photo(context, update.effective_user.id, text, admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)
    except:
        text = "❌ Введите число!"
        msg = await send_with_photo(context, update.effective_user.id, text, admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_step3(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    try:
        days = int(text)
        context.user_data["promo_sub_days"] = days
        context.user_data["promo_step"] = "expiry_date"
        await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
        text = "📅 Введите дату окончания (пример: 31.12.2026):"
        msg = await send_with_photo(context, update.effective_user.id, text, admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)
    except:
        text = "❌ Введите число!"
        msg = await send_with_photo(context, update.effective_user.id, text, admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_step4(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    try:
        datetime.datetime.strptime(text, "%d.%m.%Y")
        context.user_data["promo_expiry_date"] = text
        context.user_data["promo_step"] = "name"
        await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
        text = "📝 Введите название промокода:"
        msg = await send_with_photo(context, update.effective_user.id, text, admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)
    except:
        text = "❌ Неверный формат! Используйте ДД.ММ.ГГГГ"
        msg = await send_with_photo(context, update.effective_user.id, text, admin_back_menu())
        await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

async def create_promo_finish(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    name = text
    promo_id = create_promocode(
        name,
        context.user_data["promo_max_activations"],
        context.user_data["promo_sub_days"],
        context.user_data["promo_expiry_date"]
    )
    
    max_activations = context.user_data["promo_max_activations"]
    sub_days = context.user_data["promo_sub_days"]
    expiry_date = context.user_data["promo_expiry_date"]
    
    del context.user_data["promo_step"]
    del context.user_data["promo_max_activations"]
    del context.user_data["promo_sub_days"]
    del context.user_data["promo_expiry_date"]
    
    await delete_previous_messages(context, update.effective_user.id, update.effective_user.id, keep_first=True)
    
    text = (
        f"✅ Промокод создан!\n\n"
        f"📝 Название: {name}\n"
        f"📊 Активаций: {max_activations}\n"
        f"⏱ Дней: {sub_days}\n"
        f"📅 Действует до: {expiry_date}"
    )
    msg = await send_with_photo(context, update.effective_user.id, text, admin_main_menu())
    await add_message_to_delete(context, update.effective_user.id, update.effective_user.id, msg)

# ========== ОБРАБОТЧИК КНОПОК ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    await delete_previous_messages(context, user.id, user.id, keep_first=True)

    # ========== АДМИНКА ==========
    if data == "admin":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        text = "🔐 Админ-панель:"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_back":
        text = "🔐 Админ-панель:"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    # ========== ВАЙТ-ЛИСТ ==========
    if data == "admin_whitelist":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        text = "⬜ Вайт-лист:"
        msg = await send_with_photo(context, user.id, text, admin_whitelist_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "whitelist_add":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        context.user_data["whitelist_action"] = "add"
        text = "➕ Введите @username для добавления в вайт-лист:"
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "whitelist_remove":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        context.user_data["whitelist_action"] = "remove"
        text = "➖ Введите @username для удаления из вайт-листа:"
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "whitelist_list":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        whitelist = get_whitelist()
        if not whitelist:
            text = "⬜ Вайт-лист пуст."
        else:
            text = "⬜ **Вайт-лист:**\n\n"
            for item in whitelist:
                text += f"• @{item[0]} (добавлен: {item[1][:10]})\n"
        msg = await send_with_photo(context, user.id, text, admin_whitelist_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    # ========== ВЫДАТЬ/ЗАБРАТЬ ПОДПИСКУ ==========
    if data == "admin_give":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        context.user_data["admin_action"] = "give"
        text = "👤 Введите @username пользователя:"
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_remove":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        context.user_data["admin_action"] = "remove"
        text = "👤 Введите @username пользователя:"
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("admin_day_"):
        parts = data.split("_")
        username = parts[2]
        days = parts[3]
        
        user_data = get_user_by_username(username)
        
        if not user_data:
            text = "❌ Пользователь не найден."
            msg = await send_with_photo(context, user.id, text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        
        target_id = user_data[0]
        
        if days == "forever":
            end_date = "forever"
            text_days = "навсегда"
        else:
            days_int = int(days)
            end_date = (datetime.datetime.now() + datetime.timedelta(days=days_int)).isoformat()
            text_days = f"{days_int} дней"
        
        set_subscription(target_id, end_date)
        await send_subscription_notification(context, target_id, text_days, source="admin")
        
        text = f"✅ Подписка выдана @{username} на {text_days}"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("admin_custom_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        username = data.replace("admin_custom_", "")
        context.user_data["admin_custom_username"] = username
        context.user_data["admin_action"] = "custom_time"
        text = (
            f"⏱ Введите время в формате:\n"
            f"Примеры:\n"
            f"• 2d 5h 7m — 2 дня 5 часов 7 минут\n"
            f"• 30d — 30 дней\n"
            f"• 1d 12h — 1 день 12 часов\n\n"
            f"Доступные обозначения: d (дни), h (часы), m (минуты)"
        )
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    # ========== ПРОМОКОДЫ ==========
    if data == "admin_create_promo":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        await create_promo_step1(update, context)
        try: await query.message.delete()
        except: pass
        return

    if data == "admin_list_promo":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        promos = get_all_promocodes()
        if not promos:
            text = "📋 Промокодов пока нет."
            msg = await send_with_photo(context, user.id, text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        
        keyboard = []
        for promo in promos:
            status = "✅" if promo[7] == 1 else "❌"
            keyboard.append([InlineKeyboardButton(f"{status} {promo[1]} ({promo[3]}/{promo[2]})", callback_data=f"promo_view_{promo[0]}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        
        msg = await send_with_photo(context, user.id, "📋 Список промокодов:", InlineKeyboardMarkup(keyboard))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_view_"):
        promo_id = int(data.split("_")[2])
        promo = get_promocode_by_id(promo_id)
        if not promo:
            text = "❌ Промокод не найден."
            msg = await send_with_photo(context, user.id, text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        
        text = (
            f"📋 Промокод: {promo[1]}\n"
            f"📊 Активаций: {promo[3]}/{promo[2]}\n"
            f"📅 Дней подписки: {promo[4]}\n"
            f"⏳ Действует до: {promo[5]}\n"
            f"📌 Статус: {'Активен ✅' if promo[7] == 1 else 'Неактивен ❌'}"
        )
        keyboard = [
            [InlineKeyboardButton("🗑 Удалить", callback_data=f"promo_delete_{promo_id}")],
            [InlineKeyboardButton("📅 Продлить", callback_data=f"promo_extend_{promo_id}")],
            [InlineKeyboardButton("➕ Добавить активации", callback_data=f"promo_add_activations_{promo_id}")],
            [InlineKeyboardButton("⏱ Добавить подписку", callback_data=f"promo_add_subscription_{promo_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_list_promo")]
        ]
        msg = await send_with_photo(context, user.id, text, InlineKeyboardMarkup(keyboard))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_delete_"):
        promo_id = int(data.split("_")[2])
        delete_promocode(promo_id)
        text = "✅ Промокод удалён."
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_extend_"):
        promo_id = int(data.split("_")[2])
        context.user_data["promo_extend_id"] = promo_id
        context.user_data["promo_step"] = "extend_date"
        text = "📅 Введите новую дату окончания (пример: 31.12.2026):"
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_add_activations_"):
        promo_id = int(data.split("_")[3])
        context.user_data["promo_add_activations_id"] = promo_id
        context.user_data["promo_step"] = "add_activations"
        text = "➕ Введите количество активаций для добавления:"
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("promo_add_subscription_"):
        promo_id = int(data.split("_")[3])
        context.user_data["promo_add_subscription_id"] = promo_id
        context.user_data["promo_step"] = "add_subscription"
        text = "⏱ Введите количество дней для подписки:"
        msg = await send_with_photo(context, user.id, text, admin_back_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    # ========== ВЫДАТЬ ЛОГ ==========
    if data == "admin_send_log":
        if user.id != ADMIN_ID:
            await query.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        logs = get_all_report_logs()
        if not logs:
            text = "📄 Логов пока нет."
            msg = await send_with_photo(context, user.id, text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        
        keyboard = []
        for log in logs:
            username = log[1] or "Неизвестный"
            keyboard.append([InlineKeyboardButton(f"👤 {username}", callback_data=f"log_user_{log[0]}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        
        msg = await send_with_photo(context, user.id, "📄 Выберите пользователя:", InlineKeyboardMarkup(keyboard))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("log_user_"):
        user_id = int(data.split("_")[2])
        logs = get_report_logs_by_user(user_id)
        user_data = get_user(user_id)
        username = user_data[1] if user_data else "Неизвестный"
        
        keyboard = []
        for log in logs:
            keyboard.append([InlineKeyboardButton(f"🎯 {log[3]} ({log[4]})", callback_data=f"log_target_{log[0]}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_send_log")])
        
        text = f"👤 Пользователь: @{username}\nВыберите цель:"
        msg = await send_with_photo(context, user.id, text, InlineKeyboardMarkup(keyboard))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("log_target_"):
        log_id = int(data.split("_")[2])
        log = get_report_log_by_id(log_id)
        if not log:
            text = "❌ Лог не найден."
            msg = await send_with_photo(context, user.id, text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        
        context.user_data["send_log_id"] = log_id
        keyboard = [
            [InlineKeyboardButton("📤 Отправить лог", callback_data=f"log_send_{log_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"log_user_{log[1]}")]
        ]
        text = (
            f"📄 Лог:\n"
            f"👤 Пользователь: @{log[2]}\n"
            f"🎯 Цель: {log[3]}\n"
            f"📋 Метод: {log[4]}\n"
            f"📊 Репортов: {log[5]}\n"
            f"📅 Дата: {log[6]}"
        )
        msg = await send_with_photo(context, user.id, text, InlineKeyboardMarkup(keyboard))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("log_send_"):
        log_id = int(data.split("_")[2])
        log = get_report_log_by_id(log_id)
        if not log:
            text = "❌ Лог не найден."
            msg = await send_with_photo(context, user.id, text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return
        
        user_id = log[1]
        target = log[3]
        fake_target = "MaksGoldKlad24"
        
        target_display = target
        target_link = f"https://t.me/{fake_target}"
        
        report_text = (
            f"📊 **Уведомление о блокировке**\n\n"
            f"🎯 Аккаунт <a href='{target_link}'>{target_display}</a> был заморожен ✅\n"
            f"📅 Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Статус: Аккаунт заблокирован за нарушение правил."
        )
        
        await send_without_quote(context, user_id, report_text, parse_mode="HTML")
        
        text = f"✅ Лог отправлен пользователю @{log[2]}\n🎯 Аккаунт: {target_display} → {target_link}"
        msg = await send_with_photo(context, user.id, text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    # ========== TON ОПЛАТА ==========
    if data == "ton_pay":
        text = "💎 Выберите тариф TON:"
        msg = await send_with_photo(context, user.id, text, ton_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "ton_cancel":
        text = "💳 Выберите способ оплаты:"
        msg = await send_with_photo(context, user.id, text, buy_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_") and data not in ["ton_pay", "ton_cancel"]:
        days_map = {
            "ton_1": 1,
            "ton_3": 3,
            "ton_7": 7,
            "ton_30": 30
        }
        prices = {
            "ton_1": "7.5",
            "ton_3": "12.5",
            "ton_7": "15",
            "ton_30": "20"
        }
        
        if data in days_map:
            days = days_map[data]
            price = prices[data]
            username = user.username or "пользователь"
            
            code = generate_code()
            context.user_data[f"ton_code_{code}"] = {
                "user_id": user.id,
                "days": days,
                "username": username
            }
            
            text = (
                f"💎 Оплата TON\n\n"
                f"📤 Кошелёк:\n<code>{TON_WALLET}</code>\n\n"
                f"💰 Сумма: {price} TON\n"
                f"📅 Подписка: {days} дней\n\n"
                f"📝 Комментарий к переводу (обязательно):\n<code>{code}</code>\n\n"
                f"⚠️ После перевода нажмите «Проверить»"
            )
            msg = await send_without_quote(context, user.id, text, ton_confirm_menu(code, days, username))
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
            return

    if data.startswith("ton_check_"):
        parts = data.split("_")
        code = parts[2]
        days = int(parts[3])
        username = parts[4]
        
        admin_text = (
            f"🔍 Проверка оплаты TON\n\n"
            f"👤 @{username} купил подписку на {days} дней\n"
            f"📝 Код: <code>{code}</code>"
        )
        msg = await send_without_quote(context, ADMIN_ID, admin_text, ton_admin_menu(code, days, username))
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        
        await query.answer("✅ Запрос отправлен администратору!", show_alert=True)
        try: await query.message.delete()
        except: pass
        
        text = "⏳ Ожидайте подтверждения от администратора."
        msg = await send_with_photo(context, user.id, text, main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    if data.startswith("ton_cancel_admin_"):
        parts = data.split("_")
        code = parts[3]
        days = int(parts[4])
        username = parts[5]
        
        text = "⚠️ Вы уверены, что хотите отменить заказ?"
        msg = await send_without_quote(context, ADMIN_ID, text, ton_cancel_confirm_menu(code, days, username))
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_back_"):
        parts = data.split("_")
        code = parts[2]
        days = int(parts[3])
        username = parts[4]
        
        admin_text = (
            f"🔍 Проверка оплаты TON\n\n"
            f"👤 @{username} купил подписку на {days} дней\n"
            f"📝 Код: <code>{code}</code>"
        )
        msg = await send_without_quote(context, ADMIN_ID, admin_text, ton_admin_menu(code, days, username))
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_cancel_final_"):
        parts = data.split("_")
        code = parts[3]
        days = int(parts[4])
        username = parts[5]
        
        text = f"❌ Заказ отменён для @{username} на {days} дней"
        msg = await send_with_photo(context, ADMIN_ID, text, admin_main_menu())
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("ton_confirm_"):
        parts = data.split("_")
        code = parts[2]
        days = int(parts[3])
        username = parts[4]
        
        user_data = get_user_by_username(username)
        if not user_data:
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        target_id = user_data[0]
        
        end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        set_subscription(target_id, end_date)
        
        await send_subscription_notification(context, target_id, f"{days} дней", source="purchase")
        
        await query.answer("✅ Подписка оформлена!", show_alert=True)
        try: await query.message.delete()
        except: pass
        
        text = f"✅ Подписка на {days} дней выдана @{username}"
        msg = await send_with_photo(context, ADMIN_ID, text, admin_main_menu())
        await add_message_to_delete(context, ADMIN_ID, ADMIN_ID, msg)
        return

    # ========== ОСТАЛЬНЫЕ КНОПКИ ==========
    if data == "back_main":
        text = f"{EMOJI_WELCOME} Добро пожаловать в Baikall Snos {EMOJI_WELCOME}"
        msg = await send_with_photo(context, user.id, text, main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "send":
        if has_subscription(user.id):
            text = f"{EMOJI_SEND} Выберите цель для сноса:"
            msg = await send_with_photo(context, user.id, text, send_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await query.message.delete()
            except: pass
        else:
            await query.answer("❌ У вас не активирована подписка 💎", show_alert=True)
        return

    if data == "profile":
        user_data = get_user(user.id)
        if has_subscription(user.id):
            status = "✅ Активна"
            till = "Навсегда" if user_data[2] == "forever" else datetime.datetime.fromisoformat(user_data[2]).strftime("%d.%m.%Y")
        else:
            status = "❌ Не активна"
            till = "—"
        
        text = (
            f"{EMOJI_PROFILE} Ваш профиль\n\n"
            f"🆔 ID: {user.id}\n"
            f"👤 Юзернейм: @{user.username or 'Не указан'}\n"
            f"🛡 Подписка: {status}\n"
            f"📅 Действует до: {till}"
        )
        msg = await send_with_photo(context, user.id, text, profile_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "promo":
        text = "🎟 Введите подарочный код:"
        msg = await send_with_photo(context, user.id, text, profile_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "buy":
        text = "💳 Выберите способ оплаты:"
        msg = await send_with_photo(context, user.id, text, buy_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "stars":
        text = "⭐ Выберите тариф:"
        msg = await send_with_photo(context, user.id, text, stars_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("pay_"):
        days_map = {
            "pay_test": (1, 75),
            "pay_1": (1, 500),
            "pay_3": (3, 1000),
            "pay_7": (7, 2000),
            "pay_30": (30, 5000)
        }
        
        if data in days_map:
            days, price = days_map[data]
            success = await send_invoice(update, context, days, price)
            if success:
                try: await query.message.delete()
                except: pass
        return

    if data in ["snos_acc", "snos_bot", "snos_group", "snos_channel"]:
        action = data.replace("snos_", "")
        context.user_data["snos_action"] = action
        text = "Введите ссылку или юзернейм цели:"
        msg = await send_with_photo(context, user.id, text, None)
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data.startswith("method_"):
        parts = data.split("_")
        action = parts[1]
        method = parts[2]
        target = context.user_data.get('snos_target')
        
        if not target:
            await query.answer("❌ Цель не найдена. Попробуйте заново.", show_alert=True)
            return
        
        if is_whitelisted(target):
            await query.answer("❌ Отказано, пользователь находится в white list ❌", show_alert=True)
            return
        
        context.user_data["snos_method"] = method
        context.user_data["snos_action"] = action
        
        methods_text = {
            "universal": "🌐 Универсальный",
            "spam": "📨 Спам",
            "porno": "🔞 Порнография",
            "phone": "📱 Физ. номер"
        }
        
        method_name = methods_text.get(method, "🌐 Универсальный")
        text = f"🎯 Цель: {target}\n📋 Метод: {method_name}\n\n🚀 Запустить процесс?"
        msg = await send_with_photo(context, user.id, text, confirm_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

    if data == "confirm_yes":
        target = context.user_data.get('snos_target')
        method = context.user_data.get('snos_method')
        
        if not target or not method:
            await query.answer("❌ Ошибка. Попробуйте заново.", show_alert=True)
            return
        
        if is_whitelisted(target):
            await query.answer("❌ Отказано, пользователь находится в white list ❌", show_alert=True)
            return
        
        try: await query.message.delete()
        except: pass
        
        methods_text = {
            "universal": "🌐 Универсальный",
            "spam": "📨 Спам",
            "porno": "🔞 Порнография",
            "phone": "📱 Физ. номер"
        }
        method_name = methods_text.get(method, "🌐 Универсальный")
        
        reports_count = random.randint(90, 295)
        
        await send_progress_message(context, user.id, target, reports_count, method_name)
        return

    if data == "confirm_no":
        text = f"{EMOJI_WELCOME} Добро пожаловать в Baikall Snos {EMOJI_WELCOME}"
        msg = await send_with_photo(context, user.id, text, main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
        try: await query.message.delete()
        except: pass
        return

# ========== ОБРАБОТЧИК ТЕКСТА ==========
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # ========== ПРОМОКОДЫ (ПОШАГОВО) ==========
    if "promo_step" in context.user_data:
        step = context.user_data["promo_step"]
        
        if step == "activations":
            await create_promo_step2(update, context, text)
            return
        
        elif step == "subscription_days":
            await create_promo_step3(update, context, text)
            return
        
        elif step == "expiry_date":
            await create_promo_step4(update, context, text)
            return
        
        elif step == "name":
            await create_promo_finish(update, context, text)
            return
        
        elif step == "extend_date":
            try:
                datetime.datetime.strptime(text, "%d.%m.%Y")
                promo_id = context.user_data["promo_extend_id"]
                update_promocode(promo_id, "expiry_date", text)
                
                del context.user_data["promo_step"]
                del context.user_data["promo_extend_id"]
                
                await delete_previous_messages(context, user.id, user.id, keep_first=True)
                text = f"✅ Дата продлена до {text}"
                msg = await send_with_photo(context, user.id, text, admin_main_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
                return
            except:
                text = "❌ Неверный формат! Используйте ДД.ММ.ГГГГ"
                msg = await send_with_photo(context, user.id, text, admin_back_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
                return
        
        elif step == "add_activations":
            try:
                count = int(text)
                promo_id = context.user_data["promo_add_activations_id"]
                promo = get_promocode_by_id(promo_id)
                if promo:
                    new_max = promo[2] + count
                    update_promocode(promo_id, "max_activations", new_max)
                
                del context.user_data["promo_step"]
                del context.user_data["promo_add_activations_id"]
                
                await delete_previous_messages(context, user.id, user.id, keep_first=True)
                text = f"✅ Добавлено {count} активаций"
                msg = await send_with_photo(context, user.id, text, admin_main_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
                return
            except:
                text = "❌ Введите число!"
                msg = await send_with_photo(context, user.id, text, admin_back_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
                return
        
        elif step == "add_subscription":
            try:
                days = int(text)
                promo_id = context.user_data["promo_add_subscription_id"]
                update_promocode(promo_id, "subscription_days", days)
                
                del context.user_data["promo_step"]
                del context.user_data["promo_add_subscription_id"]
                
                await delete_previous_messages(context, user.id, user.id, keep_first=True)
                text = f"✅ Подписка обновлена на {days} дней"
                msg = await send_with_photo(context, user.id, text, admin_main_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
                return
            except:
                text = "❌ Введите число!"
                msg = await send_with_photo(context, user.id, text, admin_back_menu())
                await add_message_to_delete(context, user.id, user.id, msg)
                try: await update.message.delete()
                except: pass
                return

    # ========== ВАЙТ-ЛИСТ ==========
    if user.id == ADMIN_ID and "whitelist_action" in context.user_data:
        action = context.user_data["whitelist_action"]
        username = text.strip()
        try: await update.message.delete()
        except: pass
        
        if action == "add":
            add_to_whitelist(username)
            text = f"✅ @{normalize_username(username)} добавлен в вайт-лист."
        elif action == "remove":
            remove_from_whitelist(username)
            text = f"✅ @{normalize_username(username)} удалён из вайт-листа."
        
        del context.user_data["whitelist_action"]
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        msg = await send_with_photo(context, user.id, text, admin_whitelist_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    # ========== АКТИВАЦИЯ ПРОМОКОДА (ИСПРАВЛЕННАЯ) ==========
    if not text.startswith("/") and "admin_action" not in context.user_data and "whitelist_action" not in context.user_data and "snos_action" not in context.user_data:
        # Проверяем, есть ли такой промокод
        promo = get_promocode_by_name(text)
        
        if promo:
            success, message = activate_promocode(promo[0], user.id)
            if success:
                days = promo[4]
                end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
                set_subscription(user.id, end_date)
                reply_text = f"✅ Промокод активирован! Подписка на {days} дней оформлена 🎉"
            else:
                reply_text = f"❌ {message}"
        else:
            reply_text = "❌ Промокод не найден или неактивен."
        
        try: await update.message.delete()
        except: pass
        
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        msg = await send_with_photo(context, user.id, reply_text, main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
        return

    # ========== АДМИН ==========
    if user.id == ADMIN_ID and "admin_action" in context.user_data:
        action = context.user_data["admin_action"]
        username = text.strip()
        try: await update.message.delete()
        except: pass
        
        user_data = get_user_by_username(username)
        
        if not user_data:
            all_users = get_all_users()
            users_list = "\n".join([f"• {u[1]} (ID: {u[0]})" for u in all_users]) if all_users else "пусто"
            reply_text = (
                f"❌ Пользователь не найден.\n"
                f"Вы ввели: {username}\n\n"
                f"📋 Список пользователей в БД:\n{users_list}"
            )
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, reply_text, admin_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        
        if action == "remove":
            remove_subscription(user_data[0])
            clean_username = normalize_username(username)
            reply_text = f"❌ Подписка забрана у @{clean_username}"
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, reply_text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            del context.user_data["admin_action"]
            return
        
        elif action == "give":
            clean_username = normalize_username(username)
            reply_text = f"👤 Выдача подписки для @{clean_username}\nВыберите срок:"
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, reply_text, admin_days_menu(clean_username))
            await add_message_to_delete(context, user.id, user.id, msg)
            del context.user_data["admin_action"]
            return

    if user.id == ADMIN_ID and context.user_data.get("admin_action") == "custom_time":
        username = context.user_data.get("admin_custom_username")
        if not username:
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, "❌ Ошибка. Попробуйте заново.", admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            try: await update.message.delete()
            except: pass
            return
        
        time_str = text.strip()
        seconds = parse_time(time_str)
        try: await update.message.delete()
        except: pass
        
        if seconds == 0:
            reply_text = (
                "❌ Неверный формат. Используйте:\n"
                "• 2d 5h 7m\n"
                "• 30d\n"
                "• 1d 12h\n\n"
                "Доступно: d (дни), h (часы), m (минуты)"
            )
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, reply_text, admin_back_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        
        user_data = get_user_by_username(username)
        if not user_data:
            reply_text = "❌ Пользователь не найден."
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            msg = await send_with_photo(context, user.id, reply_text, admin_main_menu())
            await add_message_to_delete(context, user.id, user.id, msg)
            del context.user_data["admin_action"]
            del context.user_data["admin_custom_username"]
            return
        
        end_date = (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).isoformat()
        set_subscription(user_data[0], end_date)
        
        days = seconds // 86400
        await send_subscription_notification(context, user_data[0], f"{days} дней", source="admin")
        
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        time_text = []
        if days: time_text.append(f"{days}д")
        if hours: time_text.append(f"{hours}ч")
        if minutes: time_text.append(f"{minutes}м")
        time_text = " ".join(time_text) if time_text else "0м"
        
        reply_text = f"✅ Подписка выдана @{username} на {time_text}"
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        msg = await send_with_photo(context, user.id, reply_text, admin_main_menu())
        await add_message_to_delete(context, user.id, user.id, msg)
        
        del context.user_data["admin_action"]
        del context.user_data["admin_custom_username"]
        return

    # ========== СНОС ==========
    if "snos_action" in context.user_data and not text.startswith("/"):
        target = text
        context.user_data["snos_target"] = target
        
        if is_whitelisted(target):
            try: await update.message.delete()
            except: pass
            await delete_previous_messages(context, user.id, user.id, keep_first=True)
            text = "❌ Отказано, пользователь находится в white list ❌"
            msg = await send_with_photo(context, user.id, text, main_menu(user.id))
            await add_message_to_delete(context, user.id, user.id, msg)
            return
        
        try: await update.message.delete()
        except: pass
        await delete_previous_messages(context, user.id, user.id, keep_first=True)
        action = context.user_data["snos_action"]
        reply_text = f"✅ Цель сохранена: {text}\n\nВыберите метод:"
        msg = await send_with_photo(context, user.id, reply_text, method_menu(action))
        await add_message_to_delete(context, user.id, user.id, msg)
        return

# ========== PRE_CHECKOUT ==========
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("sub_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Что-то пошло не так...")

# ========== УСПЕШНАЯ ОПЛАТА ==========
async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = message.from_user
    payload = message.successful_payment.invoice_payload
    
    parts = payload.split("_")
    if len(parts) >= 2:
        days = int(parts[1])
        end_date = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        set_subscription(user.id, end_date)
        await send_subscription_notification(context, user.id, f"{days} дней", source="purchase")
        text = f"✅ Оплата прошла успешно!\n🎉 Подписка на {days} дней активирована ✅"
        msg = await send_with_photo(context, user.id, text, main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)
    else:
        text = "✅ Оплата прошла успешно!"
        msg = await send_with_photo(context, user.id, text, main_menu(user.id))
        await add_message_to_delete(context, user.id, user.id, msg)

# ========== ЗАПУСК ==========
def main():
    time.sleep(3)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Принудительное удаление вебхука
    app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    print("✅ Бот запущен с Supabase!")
    app.run_polling()

if __name__ == "__main__":
    main()