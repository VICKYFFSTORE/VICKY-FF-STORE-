import asyncio
import base64
import sqlite3
import random
import logging
import time
import aiohttp
import hmac
import hashlib
import urllib.parse
import html
import os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, Dice, BufferedInputFile
)

# ==============================================================================
# 1. BOT CONFIGURATION & CONSTANTS
# ==============================================================================
BOT_TOKEN = "8737610592:AAFIbedNDZ8zRRFPBlJX9_YrG0cvVRhe9B8"  # Paste your Telegram bot token between the quotes.
BOT_USERNAME = "@VickyXmodestor_bot"
ADMIN_ID = 8700582148
ADMIN_CONTACT = "@Vickyffstore1"


USDT_TO_INR = 90.0
VIP_DISCOUNT_PERCENTAGE = 15.0
VIP_PRICE_INR = 299.0

WELCOME_STICKER_ID = "CAACAgIAAxkBAAEU-WZmH_..."  # Replace with your sticker ID
SPIN_DELAY_SECONDS = 2.5

FIXED_CATEGORIES = [
    "ANDROID NON ROOT PANEL",
    "ANDROID ROOT PANEL",
    "IPHONE PANEL",
    "PC PANEL"
]

# ==============================================================================
# YOUR PREMIUM EMOJIS – all required emoji IDs (updated with new premium ones)
# ==============================================================================
DEFAULT_EMOJIS = {
    'product_store': '6163205892834598715',          # already premium
    'profile': '6161068493769810928',                # new premium
    'add_balance': '5429651785352501917',            # new premium
    'history': '6032594876506312598',                # new premium
    'referral': '5350452584119279096',               # new premium
    'support': '6210671723906342799',                # new premium
    'ludo_spin': '5382194935057372936',              # new premium
    'back': '5409357944619802453',                   # new premium
    'upi': '6161041877857475666',                    # new premium
    'binance': '6161089551994462716',                # new premium
    'reseller': '5447410659077661506',               # new premium
    'tutorial': '5260293700088511294',               # new premium
    'download': '6161336001512874965',               # already premium
    'telegram': '5456140674028019486',               # new premium
    'whatsapp': '5251203410396458957',               # new premium
    'welcome': '5397782960512444700',                # new premium
    'vip': '5206607081334906820',                    # new premium
    'category_android_non_root': '6161172706856282588',
    'category_android_root': '6161449831031118974',
    'category_iphone': '6161399700172840408',
    'category_pc': '5350554349074391003',
    'grid_id': '5474625972751837256',
    'name': '5215399540814781035',
    'account_level': '6129584162992034014',
    'regular_user': '5904630315946611415',
    'wallet': '6210859306602995217',
    'current_balance': '5316711376876485361',
    'global_stats': '6161437856662298090',
    'total_orders': '6160968017304888311',
    'total_spent': '5197503331215361533',
    'total_referrals': '5938196735200333756',
    'joined_grid': '5433614043006903194',
    'info_icon': '6037421444789440735',
    'check_icon': '6161241250239356403',
    'checkbox_icon': '6161437856662298090',
    'shield_icon': '6086672466132865380',
    'money_icon': '5890848474563352982',
    'redeem_icon': '5377624166436445368',
    'wallet_left': '6210859306602995217',
    'wallet_right': '5305699699204837855',
    'point_down': '6161302621027049305',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_activity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def fmt_curr(amount: float) -> str:
    return f"₹{amount:,.2f}"

def safe_float(val, default=0.0):
    """Safely convert a value to float, return default if fails."""
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# ==============================================================================
# 2. DATABASE FUNCTIONS
# ==============================================================================
def db_query(query: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False, commit: bool = True) -> Any:
    conn = sqlite3.connect('yp_shop.db')
    c = conn.cursor()
    try:
        c.execute(query, params)
        if fetchone:
            res = c.fetchone()
        elif fetchall:
            res = c.fetchall()
        else:
            res = None
        if commit: conn.commit()
        return res
    except Exception as e:
        logger.error(f"DB Error: {e} | Query: {query} | Params: {params}")
        if commit: conn.rollback()
        return None
    finally:
        conn.close()

def get_setting(key: str, default: str = "") -> str:
    val = db_query("SELECT value FROM settings WHERE key=?", (key,), fetchone=True)
    return val[0] if val and val[0] else default

def set_setting(key: str, value: str) -> None:
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

def log_activity(user_id: int, action: str, details: str = "") -> None:
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_query(
            "INSERT INTO activity_logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, action, details, timestamp)
        )
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")

def get_emoji(slot: str, default_id: str = None) -> str:
    stored = get_setting(f"emoji_{slot}", "")
    emoji_id = stored if stored and stored.isdigit() else (default_id or DEFAULT_EMOJIS.get(slot, ""))
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">✨</tg-emoji>'
    return "✨"

def get_emoji_icon(slot: str, default_id: str = None) -> str:
    # Use the requested custom emoji consistently for every Back/Cancel button.
    if str(slot).lower() == "back":
        return "5253997076169115797"
    stored = get_setting(f"emoji_{slot}", "")
    emoji_id = stored if stored and stored.isdigit() else (default_id or DEFAULT_EMOJIS.get(slot, ""))
    return emoji_id

# ==============================================================================
# 3. STRING RESOURCES – using placeholders for premium emojis
# ==============================================================================
UI_TEXTS = {
    "start_menu": (
        "✨ <b>𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗧𝗛𝗘 𝗦𝗛𝗢𝗣</b>\n\n"
        "{product_store} 𝗣𝗥𝗢𝗗𝗨𝗖𝗧 𝗦𝘁𝗼𝗿𝗲 : 𝗮𝗹𝗹 𝗸𝗲𝘆𝘀 𝗣𝘂𝗿𝗰𝗵𝗮𝘀𝗲  & 𝗶𝗻𝘀𝘁𝗮𝗻𝘁𝗹𝘆 𝗱𝗲𝗹𝗶𝘃𝗲𝗿𝘆\n"
        "{profile} 𝗠𝘆 𝗽𝗿𝗼𝗳𝗶𝗹𝗲 : 𝗰𝗵𝗲𝗰𝗸 𝘆𝗼𝘂𝗿 𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝗶𝗻𝗳𝗼𝗿𝗺𝗮𝘁𝗶𝗼𝗻\n"
        "{add_balance} 𝗔𝗱𝗱 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 : 𝗱𝗲𝗽𝗼𝘀𝗶𝘁𝗲 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 & 𝘀𝗲𝗰𝘂𝗿𝗲 𝘀𝗲𝗿𝘃𝗶𝗰𝗲\n"
        "{history} 𝗔𝗹𝗹 𝗵𝗶𝘀𝘁𝗼𝗿𝘆 : 𝗰𝗵𝗲𝗰𝗸 𝗮𝗹𝗹 𝗽𝘂𝗿𝗰𝗵𝗮𝘀𝗲 𝗵𝗶𝘀𝘁𝗼𝗿𝘆\n"
        "{referral} 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 : 𝗶𝗻𝘃𝗶𝘁𝗲 𝗳𝗿𝗶𝗲𝗻𝗱𝘀 & 𝗲𝗮𝗿𝗻 𝗿𝗲𝘄𝗮𝗿𝗱𝘀\n"
        "{tutorial} 𝗧𝘂𝘁𝗼𝗿𝗶𝗮𝗹 : 𝘃𝗶𝗲𝘄 𝘁𝘂𝘁𝗼𝗿𝗶𝗮𝗹 & 𝘄𝗼𝗿𝗸 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁\n"
        "{support} 𝗦𝘂𝗽𝗽𝗼𝗿𝘁 : 𝗯𝗼𝘁 𝗽𝗿𝗼𝗯𝗹𝗲𝗺 𝘀𝗼𝗹𝘃𝗲𝗱 𝗳𝗼𝗿 𝘀𝘂𝗽𝗽𝗼𝗿𝘁 𝗮𝗱𝗺𝗶𝗻\n"
        "{ludo_spin} 𝗟𝘂𝗱𝗼 𝗦𝗽𝗶𝗻 :𝗽𝗹𝗮𝘆 𝗴𝗮𝗺𝗲 𝗮𝗻𝗱 𝘄𝗶𝗻 𝗯𝗮𝗹𝗮𝗻𝗰𝗲\n"
        "{download} 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗙𝗶𝗹𝗲 : 𝗱𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗹𝗮𝘁𝗲𝘀𝘁 𝗮𝗽𝗸 𝗳𝗼𝗿 𝘀𝗮𝗳𝗲𝘁𝘆."
    ),
    "download_files": (
        "🗂 <b><u>DOWNLOAD PREMIUM APK & FILES 📊</u></b>\n\n"
        "🌐 All our highly secured, premium, and updated files\n"
        "are securely hosted on our private channel! ⚠️⛔️\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📱 <b>WHAT YOU GET:</b> 📌\n\n"
        "✔️ Latest APK Updates 🔔\n"
        "✔️ 100% Virus Free & Secure ‼️\n"
        "✔️ All Configs & Scripts 🌸\n"
        "✔️ Complete Installation Guides 🔺\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⌨️ Tap the button below to access the Download Channel! 📝"
    ),
    "lucky_dice_result": (
        "{ludo_spin} <b><u>LUCKY DICE RESULT 🔨 💯</u></b>\n\n"
        "🎲 <b>Dice Value:</b> {dice_value}\n\n"
        "💸 <b>You Won:</b> {won_amount}\n"
        "💰 <b>Total Balance:</b> {new_balance}\n\n"
        "Congratulations! Come back after 24 hours."
    ),
    "vip_menu": (
        "🌟 <b><u>VIP MEMBERSHIP CLUB</u></b> 🌟\n\n"
        "Unlock premium benefits and permanent discounts!\n\n"
        "💎 <b>VIP Benefits:</b>\n"
        "• Flat 15% off on ALL products (Stacks with Reseller!)\n"
        "• Priority Support\n"
        "• Exclusive VIP-only giveaways\n\n"
        "💳 <b>VIP Price:</b> ₹299.00 (Lifetime)\n"
        "👤 <b>Your Status:</b> {vip_status}"
    ),
    "add_balance_menu": (
        "{add_balance} <b>ADD BALANCE</b> {info_icon}\n\n"
        "{info_icon} Select your preferred payment method. {check_icon}\n\n"
        "┣ {upi} UPI — Fast Indian payments {checkbox_icon}\n"
        "┣ {binance} Binance — Crypto payments {checkbox_icon}\n\n"
        "{shield_icon} Payments are verified securely. {check_icon}"
    )
}

def get_ui_text(key: str, **kwargs) -> str:
    val = db_query("SELECT value FROM settings WHERE key=?", (f"ui_{key}",), fetchone=True)
    template = val[0] if val and val[0] else UI_TEXTS.get(key, "")

    emoji_map = {
        '{product_store}': get_emoji('product_store'),
        '{profile}': get_emoji('profile'),
        '{add_balance}': get_emoji('add_balance'),
        '{history}': get_emoji('history'),
        '{referral}': get_emoji('referral'),
        '{tutorial}': get_emoji('tutorial'),
        '{support}': get_emoji('support'),
        '{ludo_spin}': get_emoji('ludo_spin'),
        '{download}': get_emoji('download'),
        '{telegram}': get_emoji('telegram'),
        '{whatsapp}': get_emoji('whatsapp'),
        '{upi}': get_emoji('upi'),
        '{binance}': get_emoji('binance'),
        '{info_icon}': get_emoji('info_icon'),
        '{check_icon}': get_emoji('check_icon'),
        '{checkbox_icon}': get_emoji('checkbox_icon'),
        '{shield_icon}': get_emoji('shield_icon'),
        '{money_icon}': get_emoji('money_icon'),
        '{redeem_icon}': get_emoji('redeem_icon'),
        '{wallet_left}': get_emoji('wallet_left'),
        '{wallet_right}': get_emoji('wallet_right'),
        '{point_down}': get_emoji('point_down'),
    }
    for placeholder, emoji_tag in emoji_map.items():
        template = template.replace(placeholder, emoji_tag)

    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing formatting key for template {key}: {e}")
    return template

# ==============================================================================
# 4. DATABASE INITIALISATION & MIGRATION
# ==============================================================================
def init_db() -> None:
    conn = sqlite3.connect('yp_shop.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            phone TEXT, 
            first_name TEXT, 
            username TEXT,
            balance REAL DEFAULT 0.0, 
            account_type TEXT DEFAULT 'Regular', 
            orders_count INTEGER DEFAULT 0, 
            spent REAL DEFAULT 0.0, 
            referrals_count INTEGER DEFAULT 0, 
            referral_earned REAL DEFAULT 0.0, 
            referred_by INTEGER, 
            last_spin TEXT, 
            joined_date TEXT,
            is_reseller INTEGER DEFAULT 0,
            reseller_since TEXT,
            total_saved REAL DEFAULT 0.0,
            is_banned INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            vip_since TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            category TEXT, 
            panel_name TEXT DEFAULT '',
            name TEXT, 
            price_inr REAL, 
            reseller_price REAL DEFAULT 0.0,
            stock INTEGER, 
            apk_link TEXT, 
            validity TEXT DEFAULT 'Lifetime', 
            device_limit TEXT DEFAULT '1 Device',
            is_active INTEGER DEFAULT 1,
            is_maintenance INTEGER DEFAULT 0,
            api_pid INTEGER DEFAULT 0,
            custom_emoji_id TEXT DEFAULT ''
        )
    ''')
    
    # Backward-compatible migration for existing databases.
    product_columns = [row[1] for row in c.execute("PRAGMA table_info(products)").fetchall()]
    if 'is_maintenance' not in product_columns:
        c.execute("ALTER TABLE products ADD COLUMN is_maintenance INTEGER DEFAULT 0")
    if 'api_pid' not in product_columns:
        c.execute("ALTER TABLE products ADD COLUMN api_pid INTEGER DEFAULT 0")
    if 'custom_emoji_id' not in product_columns:
        c.execute("ALTER TABLE products ADD COLUMN custom_emoji_id TEXT DEFAULT ''")

    c.execute('''
        CREATE TABLE IF NOT EXISTS product_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            product_id INTEGER, 
            key_text TEXT, 
            is_used INTEGER DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            product_name TEXT, 
            price_paid REAL, 
            delivered_key TEXT, 
            purchase_date TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            message TEXT, 
            status TEXT DEFAULT 'Open',
            created_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, 
            value TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS store_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            emoji_id TEXT DEFAULT ''
        )
    ''')
    for _cat in ('ANDROID NON ROOT PANEL', 'ANDROID ROOT PANEL', 'IPHONE PANEL', 'PC PANEL'):
        c.execute('INSERT OR IGNORE INTO store_categories (name, emoji_id) VALUES (?, ?)', (_cat, ''))

    c.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY, 
            amount REAL, 
            uses_left INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS redeemed (
            user_id INTEGER, 
            code TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS order_coupons (
            code TEXT PRIMARY KEY,
            amount REAL NOT NULL DEFAULT 0,
            uses_left INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_coupon_redemptions (
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            order_id TEXT NOT NULL,
            PRIMARY KEY(user_id, code, order_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS product_payment_orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            amount_due REAL NOT NULL,
            wallet_used REAL NOT NULL DEFAULT 0,
            coupon_code TEXT,
            coupon_discount REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            order_id TEXT PRIMARY KEY, 
            user_id INTEGER, 
            amount_inr REAL, 
            status TEXT, 
            timestamp INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS crypto_txns (
            txid TEXT PRIMARY KEY, 
            user_id INTEGER, 
            amount_usdt REAL, 
            timestamp INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS spin_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            amount REAL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TEXT
        )
    ''')

    migrations = [
        "ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN vip_since TEXT",
        "ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1",
        "ALTER TABLE tickets ADD COLUMN created_at TEXT",
        "ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN warnings INTEGER DEFAULT 0",
        "ALTER TABLE products ADD COLUMN panel_name TEXT DEFAULT ''"
    ]
    for mig in migrations:
        try: c.execute(mig)
        except sqlite3.OperationalError: pass
    
    c.execute("SELECT COUNT(*) FROM spin_rewards")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO spin_rewards (amount) VALUES (?)", [(0.0,), (1.0,), (2.0,), (5.0,), (10.0,)])

    default_settings = [
        ('spin_status', 'ON'),
        ('daily_spin_limit', '50.0'),
        ('reseller_system_status', 'ON'),
        ('bot_status', 'ON'),
        ('how_to_video', 'None'),
        ('all_files_link', 'None'),
        ('fampay_api_key', ''),
        ('fampay_upi_id', ''),
        ('binance_api', ''),
        ('binance_secret', ''),
        ('binance_address', ''),
        ('vip_status', 'OFF'),
        ('reseller_setup_fee', '200.0'),
        ('reseller_min_balance', '500.0'),
        ('migration_done', '0'),
        ('support_telegram', 'https://t.me/YourSupport'),
        ('support_whatsapp', 'https://wa.me/YourNumber'),
        ('ui_start_menu', UI_TEXTS['start_menu']),
        ('ui_download_files', UI_TEXTS['download_files']),
        ('ui_lucky_dice_result', UI_TEXTS['lucky_dice_result']),
        ('ui_vip_menu', UI_TEXTS['vip_menu']),
        ('ui_add_balance_menu', UI_TEXTS['add_balance_menu']),
    ]
    for slot, emoji_id in DEFAULT_EMOJIS.items():
        default_settings.append((f"emoji_{slot}", emoji_id))
    
    for key, val in default_settings:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    conn.commit()
    conn.close()

def migrate_categories() -> None:
    done = get_setting("migration_done", "0")
    
    # ALWAYS force update emojis and UI texts regardless of migration status
    logger.info("Forcing emoji and UI text updates...")
    
    # Update all emoji settings
    for slot, emoji_id in DEFAULT_EMOJIS.items():
        set_setting(f"emoji_{slot}", emoji_id)
    
    # Force update UI texts
    set_setting("ui_start_menu", UI_TEXTS['start_menu'])
    set_setting("ui_add_balance_menu", UI_TEXTS['add_balance_menu'])
    set_setting("ui_download_files", UI_TEXTS['download_files'])
    set_setting("ui_lucky_dice_result", UI_TEXTS['lucky_dice_result'])
    set_setting("ui_vip_menu", UI_TEXTS['vip_menu'])
    logger.info("UI texts and emojis updated with new placeholders and IDs.")
    
    # Fix any corrupted price columns (one-time cleanup)
    conn = sqlite3.connect('yp_shop.db')
    c = conn.cursor()
    products = c.execute("SELECT id, price_inr, reseller_price FROM products").fetchall()
    for prod in products:
        pid = prod[0]
        for col in ['price_inr', 'reseller_price']:
            val = prod[1] if col == 'price_inr' else prod[2]
            if val is None or val == "":
                new_val = 0.0
            else:
                try:
                    new_val = float(val)
                except (ValueError, TypeError):
                    new_val = 0.0
            c.execute(f"UPDATE products SET {col}=? WHERE id=?", (new_val, pid))
    conn.commit()
    conn.close()
    logger.info("Fixed any non-numeric price columns.")
    
    if done == "1":
        return
    
    logger.info("Running category migration...")
    
    mapping = {
        "android non root panel": "ANDROID NON ROOT PANEL",
        "android root panel": "ANDROID ROOT PANEL",
        "iphone panel": "IPHONE PANEL",
        "pc panel": "PC PANEL",
    }
    for old, new in mapping.items():
        db_query("UPDATE products SET category = ? WHERE LOWER(category) = ?", (new, old))
    
    db_query("UPDATE products SET category = 'ANDROID NON ROOT PANEL' WHERE LOWER(category) NOT IN (?, ?, ?, ?)",
             ("android non root panel", "android root panel", "iphone panel", "pc panel"))
    
    set_setting("migration_done", "1")
    logger.info("Category migration complete.")

# ==============================================================================
# 5. MIDDLEWARES & SECURITY
# ==============================================================================
async def hacker_loading(message: Message, text: str = "Decrypting Data") -> Message:
    msg = await message.answer(f"⚡ {text}\n[□□□] 0%")
    await asyncio.sleep(0.3)
    await msg.edit_text(f"⚡ {text}\n[■□□] 33%", parse_mode='HTML')
    await asyncio.sleep(0.3)
    await msg.edit_text(f"⚡ {text}\n[■■□] 66%", parse_mode='HTML')
    await asyncio.sleep(0.3)
    await msg.edit_text(f"⚡ {text}\n[■■■] 100%", parse_mode='HTML')
    return msg

class GlobalSecurityMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.last_action_times = {}

    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        now = time.time()
        if user_id in self.last_action_times:
            if now - self.last_action_times[user_id] < 0.3:
                return
        self.last_action_times[user_id] = now

        if user_id != ADMIN_ID:
            user_info = db_query("SELECT is_banned FROM users WHERE user_id=?", (user_id,), fetchone=True)
            if user_info and user_info[0] == 1:
                msg = "🚫 <b>ACCESS DENIED</b>\nYou have been banned from using this bot.\nContact support if you think this is a mistake."
                if isinstance(event, Message): await event.answer(msg)
                elif isinstance(event, CallbackQuery): await event.answer(msg, show_alert=True)
                return
                
            status_check = db_query("SELECT value FROM settings WHERE key='bot_status'", fetchone=True)
            status = status_check[0] if status_check else 'ON'
            if status == 'OFF':
                msg = "⚠️ <b>Store Maintenance</b>\n\nThe store is currently offline for updates. Please check back later!"
                if isinstance(event, Message): await event.answer(msg)
                elif isinstance(event, CallbackQuery): await event.answer("⚠️ Bot is currently OFF for Maintenance.", show_alert=True)
                return
                
        return await handler(event, data)

dp.message.middleware(GlobalSecurityMiddleware())
dp.callback_query.middleware(GlobalSecurityMiddleware())

# ==============================================================================
# 6. FSM STATES
# ==============================================================================
class UserStates(StatesGroup):
    wait_for_ticket = State()
    wait_for_redeem = State()
    wait_for_order_coupon = State()
    wait_for_crypto_txid = State()
    custom_amount_input = State()

class AdminStates(StatesGroup):
    add_prod_category = State()
    add_prod_panel_name = State()
    add_prod_name = State()
    add_prod_validity = State()
    add_prod_device_limit = State()
    add_prod_price = State()
    add_prod_reseller_price = State()
    add_prod_apk = State()
    add_prod_keys = State()
    bulk_product_names = State()
    add_product_category = State()
    add_category_name = State()
    add_category_emoji = State()
    bulk_product_emoji = State()
    bulk_product_plans = State()
    add_plan_for_product = State()
    wait_for_product_emoji = State()
    wait_for_fampay_api_only = State()
    wait_for_fampay_upi_only = State()
    wait_for_payment_proof_group = State()
    
    edit_prod_field = State()
    wait_for_new_value = State()
    wait_for_add_keys = State()
    wait_for_delete_key = State()
    
    broadcast_msg = State()
    add_coupon_code = State()
    add_coupon_amount = State()
    add_coupon_uses = State()
    
    wait_for_fampay_api_key = State()
    wait_for_fampay_upi = State()
    wait_for_binance_api = State()
    wait_for_binance_secret = State()
    wait_for_binance_address = State()
    
    ticket_reply_msg = State()
    reseller_manage_id = State()
    manage_target_user = State()
    wait_for_add_money = State()
    wait_for_minus_money = State()
    wait_for_warning = State()
    
    spin_add_reward = State()
    spin_set_limit = State()
    wait_for_howto_video = State()
    wait_for_all_files_link = State()
    
    edit_ui_text = State()
    edit_reseller_price = State()
    wait_for_reseller_setup_fee = State()
    wait_for_reseller_min_balance = State()
    confirm_ban = State()
    
    wait_for_support_telegram = State()
    wait_for_support_whatsapp = State()
    wait_for_category_emoji = State()
    wait_for_panel_emoji_id = State()
    wait_for_emoji_slot = State()

# ==============================================================================
# 7. KEYBOARDS
# ==============================================================================
def get_category_emoji(category: str) -> str:
    slot_map = {
        "ANDROID NON ROOT PANEL": "category_android_non_root",
        "ANDROID ROOT PANEL": "category_android_root",
        "IPHONE PANEL": "category_iphone",
        "PC PANEL": "category_pc",
    }
    slot = slot_map.get(category)
    if slot:
        return get_emoji_icon(slot, DEFAULT_EMOJIS.get(slot, ""))
    return ""

def get_panel_emoji(panel_name: str) -> str:
    stored = get_setting(f"panel_emoji_{panel_name}", "")
    if stored and stored.isdigit():
        return stored
    return get_emoji_icon("product_store")

def contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Verify Contact", request_contact=True)]], 
        resize_keyboard=True, 
        one_time_keyboard=True
    )

def main_menu_kb(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    status_check = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    sys_status = status_check[0] if status_check else 'ON'
    vip_sys_check = db_query("SELECT value FROM settings WHERE key='vip_status'", fetchone=True)
    vip_system = vip_sys_check[0] if vip_sys_check else 'OFF'
    
    is_reseller = False
    if user_id:
        user_check = db_query("SELECT is_reseller FROM users WHERE user_id=?", (user_id,), fetchone=True)
        if user_check:
            is_reseller = bool(user_check[0])

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="Product Store", callback_data="menu_shop",
            icon_custom_emoji_id=get_emoji_icon("product_store"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="My Profile", callback_data="menu_profile",
            icon_custom_emoji_id=get_emoji_icon("profile"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Add Balance", callback_data="menu_add_balance",
            icon_custom_emoji_id=get_emoji_icon("add_balance"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="All History", callback_data="menu_orders",
            icon_custom_emoji_id=get_emoji_icon("history"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Referral", callback_data="menu_referral",
            icon_custom_emoji_id=get_emoji_icon("referral"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="Tutorials", callback_data="menu_how_to",
            icon_custom_emoji_id=get_emoji_icon("tutorial"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Support", callback_data="menu_support",
            icon_custom_emoji_id=get_emoji_icon("support"),
            style="success"
        )
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🧾 Check Proof", url="https://t.me/+nykJy-FjkGpjNTBl", style="primary")
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="Ludo Spin", callback_data="menu_spin_landing",
            icon_custom_emoji_id=get_emoji_icon("ludo_spin"),
            style="success"
        ),
        InlineKeyboardButton(
            text="Download Files", callback_data="menu_all_files",
            icon_custom_emoji_id=get_emoji_icon("download"),
            style="success"
        )
    ])
    
    extras_row = []
    if sys_status == 'ON' or is_reseller:
        extras_row.append(InlineKeyboardButton(
            text="Reseller Panel", callback_data="menu_reseller_dash",
            icon_custom_emoji_id=get_emoji_icon("reseller"),
            style="success"
        ))
    if vip_system == 'ON':
        extras_row.append(InlineKeyboardButton(
            text="VIP Club", callback_data="menu_vip_dash",
            style="success"
        ))
    if extras_row:
        kb.inline_keyboard.append(extras_row)
        
    return kb

def back_kb(callback: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="BACK", callback_data=callback,
                icon_custom_emoji_id=get_emoji_icon("back"),
                style="danger"
            )
        ]]
    )

def admin_kb() -> InlineKeyboardMarkup:
    status = db_query("SELECT value FROM settings WHERE key='bot_status'", fetchone=True)
    status_val = status[0] if status else 'ON'
    vip_status = db_query("SELECT value FROM settings WHERE key='vip_status'", fetchone=True)
    vip_val = vip_status[0] if vip_status else 'OFF'
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Bot Statistics", callback_data="admin_view_stats", style="success")],
        [InlineKeyboardButton(text="👥 User Control Panel", callback_data="admin_user_control_start", style="success")],
        [
            InlineKeyboardButton(text="➕ Add Product", callback_data="admin_add_prod", style="success"),
            InlineKeyboardButton(text="📦 Manage Products", callback_data="admin_manage_prods", style="success")
        ],
        [
            InlineKeyboardButton(text="📂 Add Category", callback_data="admin_add_category", style="success"),
            InlineKeyboardButton(text="🗂 Manage Categories", callback_data="admin_manage_categories", style="primary")
        ],
        [
            InlineKeyboardButton(text="👑 Reseller Mgmt", callback_data="admin_reseller_menu", style="success"),
            InlineKeyboardButton(text="🎰 Spin Settings", callback_data="admin_spin_menu", style="success")
        ],
        [
            InlineKeyboardButton(text="🎟 Create Coupon", callback_data="admin_create_coupon", style="success"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast_btn", style="success")
        ],
        [
            InlineKeyboardButton(text="🎫 View Tickets", callback_data="admin_view_tickets", style="success"),
            InlineKeyboardButton(text="📹 Tutorial Video", callback_data="admin_set_video", style="success")
        ],
        [
            InlineKeyboardButton(text="🔗 All Files Link", callback_data="admin_set_all_files", style="success"),
            InlineKeyboardButton(text="🎨 Edit All Emojis", callback_data="admin_edit_emojis", style="success")
        ],
        [
            InlineKeyboardButton(text="🔑 Set FamGateway API Token", callback_data="admin_set_fampay_token", style="success"),
            InlineKeyboardButton(text="💳 Set Merchant UPI ID", callback_data="admin_set_fampay_upi", style="success")
        ],
        [
            InlineKeyboardButton(text="🧾 Set Payment Proof Group", callback_data="admin_set_payment_proof_group", style="success"),
            InlineKeyboardButton(text="🧪 Test Proof", callback_data="admin_test_payment_proof_group", style="primary")
        ],
        [
            InlineKeyboardButton(text="✏️ Edit UI Texts", callback_data="admin_edit_ui_menu", style="success"),
            InlineKeyboardButton(text="📝 Edit Reseller Price", callback_data="admin_edit_reseller_price", style="success")
        ],
        [
            InlineKeyboardButton(text="💰 Reseller Fee", callback_data="admin_set_reseller_fee", style="success"),
            InlineKeyboardButton(text="💳 Min Balance", callback_data="admin_set_reseller_min", style="success")
        ],
        [
            InlineKeyboardButton(text="📞 Set Support Links", callback_data="admin_set_support_links", style="success"),
            InlineKeyboardButton(text="🎨 Set Category Emojis", callback_data="admin_set_category_emojis", style="success")
        ],
        [
            InlineKeyboardButton(text="🖼 Set Panel Emojis", callback_data="admin_set_panel_emojis", style="success")
        ],
        [
            InlineKeyboardButton(
                text=f"Bot Status: {status_val} {'🟢' if status_val == 'ON' else '🔴'}",
                callback_data="admin_toggle_bot",
                style="success" if status_val == 'ON' else "danger"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"VIP System: {vip_val} {'🟢' if vip_val == 'ON' else '🔴'}",
                callback_data="admin_toggle_vip_sys",
                style="success" if vip_val == 'ON' else "danger"
            )
        ]
    ])
    return kb

def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Back to Admin", callback_data="admin_panel_back",
            icon_custom_emoji_id=get_emoji_icon("back"),
            style="danger"
        )
    ]])

# ==============================================================================
# 8. NOTIFICATIONS
# ==============================================================================
async def send_advanced_notification(user_id: int, notif_type: str, amount: float, product: str = None, key: str = None, gateway: str = "FamGateway") -> None:
    user_info = db_query("SELECT first_name, phone, username, is_reseller, is_vip FROM users WHERE user_id=?", (user_id,), fetchone=True)
    
    name = user_info[0] if user_info else "Unknown"
    phone = user_info[1] if user_info and user_info[1] else "Not Provided"
    username = f"@{user_info[2]}" if user_info and user_info[2] else "None"
    
    tags = []
    if user_info and user_info[3]: tags.append("👑 Reseller")
    if user_info and user_info[4]: tags.append("🌟 VIP")
    tag_str = " | ".join(tags) if tags else "👤 Regular"
        
    time_now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    
    if notif_type == "ORDER":
        title = "🛒 <b>NEW ORDER PROCESSED!</b> 🛒"
        details = (f"📦 <b>Product:</b> {product}\n🔑 <b>Key:</b> <code>{key}</code>\n💰 <b>Amount Paid:</b> ₹{amount:.2f}\n📅 <b>Time:</b> {time_now}")
    else:
        title = "💰 <b>NEW WALLET DEPOSIT!</b> 💰"
        details = (f"💵 <b>Amount Added:</b> ₹{amount:.2f}\n🧾 <b>Gateway:</b> {gateway}\n🆔 <b>Reference:</b> <code>{product}</code>\n📅 <b>Time:</b> {time_now}")

    msg = f"{title}\n━━━━━━━━━━━━━━━━━━\n👤 <b>Name:</b> {name}\n🆔 <b>User ID:</b> <code>{user_id}</code>\n📱 <b>Phone:</b> {phone}\n🔗 <b>Username:</b> {username}\n🏷 <b>Status:</b> {tag_str}\n━━━━━━━━━━━━━━━━━━\n{details}"
    try: 
        await bot.send_message(ADMIN_ID, msg, parse_mode='HTML')
    except Exception as e: 
        logger.error(f"Failed to send admin notification: {e}")

# ==============================================================================
# 9. PAYMENT VERIFIER
# ==============================================================================
async def run_payment_verification(user_id: int, order_id: str, reply_target: Any) -> None:
    txn = db_query('SELECT amount_inr, status, timestamp FROM transactions WHERE order_id=? AND user_id=?', (order_id, user_id), fetchone=True)
    if not txn:
        msg = '❌ Invalid payment order.'
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
        return
    if txn[1] == 'paid':
        msg = '✅ This payment has already been credited.'
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
        return
    try:
        verification = await verify_fampay_order(order_id)
    except Exception as e:
        logger.warning('FamGateway wallet verification failed: %s', e)
        msg = '⚠️ Could not verify with FamGateway right now. Try again shortly.'
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
        return
    status = str(verification.get('status', '')).lower()
    data = verification.get('data') if isinstance(verification.get('data'), dict) else verification
    paid_amount = safe_float(data.get('amount', data.get('payable_amount', 0)))
    if status != 'success' or paid_amount + 0.009 < safe_float(txn[0]):
        msg = '⏳ Payment is still pending or the verified amount does not match. Please try again after payment.'
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
        return
    conn = sqlite3.connect('yp_shop.db', timeout=10)
    try:
        conn.execute('BEGIN IMMEDIATE')
        changed = conn.execute("UPDATE transactions SET status='paid' WHERE order_id=? AND user_id=? AND status='pending'", (order_id, user_id)).rowcount
        if not changed:
            conn.rollback()
            msg = 'This payment has already been processed.'
            if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
            else: await reply_target.answer(msg)
            return
        conn.execute('UPDATE users SET balance=balance+? WHERE user_id=?', (txn[0], user_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()
    success_msg = f'🎉 <b>VERIFICATION SUCCESSFUL!</b>\n\n✅ {fmt_curr(txn[0])} has been added to your wallet securely.'
    if isinstance(reply_target, CallbackQuery): await reply_target.message.edit_text(success_msg, reply_markup=back_kb(), parse_mode='HTML')
    else: await reply_target.answer(success_msg, reply_markup=back_kb(), parse_mode='HTML')
    await send_advanced_notification(user_id, 'DEPOSIT', txn[0], product=order_id, gateway='FamGateway')
    log_activity(user_id, 'DEPOSIT_SUCCESS', f'Amount: {txn[0]}, Gateway: FamGateway, Order: {order_id}')


async def auto_verify_task() -> None:
    while True:
        await asyncio.sleep(20)
        pending_txns = db_query("SELECT order_id, user_id FROM transactions WHERE status='pending'", fetchall=True)
        if not pending_txns: continue
        for order_id, user_id in pending_txns:
            try:
                await run_payment_verification(user_id, order_id, _SilentReplyTarget(user_id))
            except Exception as e:
                logger.debug('FamGateway auto-verification retry: %s', e)


class _SilentReplyTarget:
    def __init__(self, user_id): self.user_id = user_id
    async def answer(self, *args, **kwargs): return None


# ==============================================================================
# 10. ONBOARDING & START
# ==============================================================================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    try: await message.answer_sticker(WELCOME_STICKER_ID)
    except: pass 
    
    args = message.text.split()
    # Shared product links open the selected product's complete plan list.
    shared_product_id = None
    if len(args) > 1 and args[1].startswith("product_"):
        try:
            shared_product_id = int(args[1].split("_", 1)[1])
        except (ValueError, IndexError):
            shared_product_id = None
    if len(args) > 1 and args[1].startswith("v_"):
        order_id = args[1].split("v_")[1]
        msg = await message.answer("🔄 <b>Verifying your payment securely...</b>\n<i>Connecting to gateway...</i>", parse_mode='HTML')
        await run_payment_verification(message.from_user.id, order_id, msg)
        return

    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try: referred_by = int(args[1].split("_")[1])
        except: pass

    user = db_query("SELECT phone FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)
    current_username = message.from_user.username or ""
    db_query("UPDATE users SET username=? WHERE user_id=?", (current_username, message.from_user.id))

    if not user or not user[0]:
        db_query("INSERT OR IGNORE INTO users (user_id, first_name, username, referred_by, joined_date) VALUES (?, ?, ?, ?, ?)", 
                 (message.from_user.id, message.from_user.first_name, current_username, referred_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        log_activity(message.from_user.id, "ACCOUNT_CREATED")
        await message.answer("<b>🛡 VERIFICATION REQUIRED</b>\n\nTo safeguard your orders and account, we need to verify you.\n👇 <b>Tap the button below:</b>", parse_mode='HTML', reply_markup=contact_kb())
    else:
        log_activity(message.from_user.id, "CMD_START")
        if len(args) > 1 and args[1] == "shop":
            shop_kb = InlineKeyboardMarkup(inline_keyboard=[])
            category_rows = db_query("SELECT id, name, emoji_id FROM store_categories ORDER BY id", fetchall=True) or []
            for cid, cat, saved_emoji in category_rows:
                if get_setting(f'category_enabled_{cid}', 'ON') == 'OFF':
                    continue
                emoji_id = str(saved_emoji or '').strip() or get_category_emoji(cat)
                shop_kb.inline_keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"cat_{cat[:30]}", icon_custom_emoji_id=emoji_id, style="primary")])
            shop_kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
            shop_text = f"<blockquote>{get_emoji('product_store')} <b>SELECT PRODUCT PANEL</b></blockquote>\n\n{get_emoji('point_down')} <b>Choose a panel to view its packages:</b>"
            await message.answer(shop_text, reply_markup=shop_kb, parse_mode="HTML")
            return
        if shared_product_id is not None:
            selected = db_query(
                "SELECT category, panel_name FROM products WHERE id=? AND is_active=1 AND is_maintenance=0",
                (shared_product_id,), fetchone=True
            )
            if selected:
                category, panel_name = selected
                plans = db_query(
                    "SELECT id, name, price_inr, stock, reseller_price, validity, device_limit, panel_name, custom_emoji_id "
                    "FROM products WHERE category=? AND panel_name=? AND is_active=1 AND is_maintenance=0 ORDER BY id",
                    (category, panel_name), fetchall=True
                )
                if plans:
                    # Send the direct plan page as a new message, keeping the normal menu available.
                    await show_products_for_panel_from_message(message, plans, str(panel_name or category))
                    return
            await message.answer("⚠️ This product is currently unavailable.")
        await send_main_menu(message)

@dp.message(F.contact)
async def handle_contact(message: Message):
    if message.contact.user_id == message.from_user.id:
        db_query("UPDATE users SET phone=? WHERE user_id=?", (message.contact.phone_number, message.from_user.id))
        referrer = db_query("SELECT referred_by FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)
        if referrer and referrer[0]:
            db_query("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id=?", (referrer[0],))
            try: await bot.send_message(referrer[0], f"🎉 <b>Referral Success!</b>\nUser <b>{message.from_user.first_name}</b> joined using your link!", parse_mode='HTML')
            except: pass
        log_activity(message.from_user.id, "CONTACT_VERIFIED")
        await message.answer("✅ Verification successful! Welcome to the system.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
    else:
        await message.answer("❌ Security Alert: Please share your OWN contact using the provided button.")

async def send_main_menu(ctx: Any):
    text = get_ui_text("start_menu")
    kb = main_menu_kb(ctx.from_user.id)
    if isinstance(ctx, Message): 
        await ctx.answer(text, reply_markup=kb, parse_mode='HTML')
    else: 
        await ctx.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    log_activity(call.from_user.id, "RETURN_MAIN_MENU")
    await send_main_menu(call)

# ==============================================================================
# 11. ADD BALANCE
# ==============================================================================
@dp.callback_query(F.data == "menu_add_balance")
async def select_gateway_menu(call: CallbackQuery):
    log_activity(call.from_user.id, "VIEW_ADD_BALANCE")
    text = get_ui_text("add_balance_menu")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="UPI PAY", callback_data="gateway_inr", icon_custom_emoji_id=get_emoji_icon("upi"), style="primary"),
            InlineKeyboardButton(text="BINANCE PAY", callback_data="gateway_crypto", icon_custom_emoji_id=get_emoji_icon("binance"), style="primary")
        ],
        [
            InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")
        ]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

# ==============================================================================
# 12. UPI & CRYPTO PAYMENT FLOWS
# ==============================================================================
@dp.callback_query(F.data == "gateway_inr")
async def add_balance_inr(call: CallbackQuery):
    text = f"💵 <b>— FAMGATEWAY DEPOSIT —</b> 💵\n\nSelect amount to deposit:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₹50", callback_data="pay_50", style="primary"), InlineKeyboardButton(text="₹100", callback_data="pay_100", style="primary")],
        [InlineKeyboardButton(text="₹200", callback_data="pay_200", style="primary"), InlineKeyboardButton(text="₹500", callback_data="pay_500", style="primary")],
        [InlineKeyboardButton(text="✏️ Custom Amount", callback_data="custom_deposit_keypad", style="primary")],
        [InlineKeyboardButton(text="Back", callback_data="menu_add_balance", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "custom_deposit_keypad")
async def show_custom_keypad(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.custom_amount_input)
    await state.update_data(amount_str="0")
    await show_keypad(call.message)

async def show_keypad(message: Message, amount_str: str = "0"):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="      1      ", callback_data="kp_1", style="primary"), InlineKeyboardButton(text="      2      ", callback_data="kp_2", style="primary"), InlineKeyboardButton(text="      3      ", callback_data="kp_3", style="primary")],
        [InlineKeyboardButton(text="      4      ", callback_data="kp_4", style="primary"), InlineKeyboardButton(text="      5      ", callback_data="kp_5", style="primary"), InlineKeyboardButton(text="      6      ", callback_data="kp_6", style="primary")],
        [InlineKeyboardButton(text="      7      ", callback_data="kp_7", style="primary"), InlineKeyboardButton(text="      8      ", callback_data="kp_8", style="primary"), InlineKeyboardButton(text="      9      ", callback_data="kp_9", style="primary")],
        [InlineKeyboardButton(text="    ⌫    ", callback_data="kp_backspace", style="danger"), InlineKeyboardButton(text="      0      ", callback_data="kp_0", style="primary"), InlineKeyboardButton(text="    C    ", callback_data="kp_clear", style="danger")],
        [InlineKeyboardButton(text=f"✅ Confirm (₹{amount_str})", callback_data="kp_confirm", style="success")],
        [InlineKeyboardButton(text="Cancel", callback_data="gateway_inr", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    text = f"💵 <b>Enter Amount (₹):</b>\n\nCurrent: ₹{amount_str}"
    await message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("kp_"), UserStates.custom_amount_input)
async def keypad_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_str = data.get("amount_str", "0")
    action = call.data.split("_")[1]
    if action == "confirm":
        if amount_str == "0":
            await call.answer("Amount cannot be zero.", show_alert=True)
            return
        try:
            amount = float(amount_str)
            if amount < 10:
                await call.answer("Minimum deposit is ₹10.", show_alert=True)
                return
            await state.clear()
            await call.message.edit_text("⏳ <b>Creating FamGateway payment order...</b>", parse_mode='HTML')
            await generate_fampay_wallet_order(call.from_user.id, amount, call.message)
        except ValueError:
            await call.answer("Invalid amount.", show_alert=True)
        return
    if action == "backspace":
        if len(amount_str) > 1: amount_str = amount_str[:-1]
        else: amount_str = "0"
    elif action == "clear":
        amount_str = "0"
    else:
        if amount_str == "0": amount_str = action
        else: amount_str += action
        if len(amount_str) > 6: amount_str = amount_str[:6]
    await state.update_data(amount_str=amount_str)
    await show_keypad(call.message, amount_str)
    await call.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def process_fampay_payment_callback(call: CallbackQuery):
    inr_amount = float(call.data.split("_")[1])
    await call.message.edit_text("⏳ <b>Creating FamGateway payment order...</b>", parse_mode='HTML')
    await generate_fampay_wallet_order(call.from_user.id, inr_amount, call.message)

async def generate_fampay_wallet_order(user_id: int, inr_amount: float, message_obj: Message) -> None:
    if not get_setting('fampay_api_key', '').strip():
        return await message_obj.edit_text('⚠️ FamGateway is not configured. Admin must add the API key.', reply_markup=back_kb('gateway_inr'), parse_mode='HTML')
    if inr_amount < 10:
        return await message_obj.edit_text('❌ Minimum deposit is ₹10.', reply_markup=back_kb('gateway_inr'), parse_mode='HTML')
    try:
        order = await create_fampay_order(inr_amount, user_id)
        order_id = str(order.get('order_id') or '')
        checkout_url = str(order.get('checkout_url') or '')
        qr_url = str(order.get('qr_url') or '')
        if not order_id: raise RuntimeError('FamGateway response did not include order ID.')
        db_query('INSERT INTO transactions (order_id, user_id, amount_inr, status, timestamp) VALUES (?, ?, ?, \'pending\', ?)', (order_id, user_id, inr_amount, int(time.time())))
    except Exception as e:
        logger.warning('FamGateway deposit creation failed: %s', e)
        return await message_obj.edit_text('❌ Could not create a FamGateway order. Please check the API key and try again.', reply_markup=back_kb('gateway_inr'), parse_mode='HTML')
    buttons = []
    if checkout_url: buttons.append([InlineKeyboardButton(text='OPEN UPI CHECKOUT', url=checkout_url, style='success')])
    buttons.append([InlineKeyboardButton(text='VERIFY PAYMENT', callback_data=f'verify_{order_id}', style='primary')])
    buttons.append([InlineKeyboardButton(text='CANCEL', callback_data='menu_add_balance', icon_custom_emoji_id=get_emoji_icon('back'), style='danger')])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    upi_id = get_setting('fampay_upi_id', '').strip()
    upi_line = f'\nMerchant UPI: <code>{html.escape(upi_id)}</code>' if upi_id else ''
    text = f'🧾 <b>FAMGATEWAY INVOICE</b>\n\nAmount: <b>{fmt_curr(inr_amount)}</b>\nOrder ID: <code>{html.escape(order_id)}</code>{upi_line}\n\nComplete the UPI payment, then tap VERIFY PAYMENT. Payment is credited only after server-side verification.'
    log_activity(user_id, 'GENERATE_INVOICE', f'Amount: {inr_amount}, Order ID: {order_id}')
    if qr_url:
        try:
            await message_obj.delete()
            await bot.send_photo(user_id, qr_url, caption=text, reply_markup=kb, parse_mode='HTML')
        except Exception:
            await message_obj.answer(text, reply_markup=kb, parse_mode='HTML')
    else:
        await message_obj.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("verify_"))
async def manual_verify_callback(call: CallbackQuery):
    order_id = call.data.split("_", 1)[1]
    await run_payment_verification(call.from_user.id, order_id, call)

@dp.callback_query(F.data == "gateway_crypto")
async def add_balance_crypto(call: CallbackQuery, state: FSMContext):
    address_check = db_query("SELECT value FROM settings WHERE key='binance_address'", fetchone=True)
    if not address_check or not address_check[0]:
        return await call.message.edit_text("⚠️ Binance Gateway is currently offline. Admin has not set a deposit address.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
    deposit_address = address_check[0]
    msg = (f"🪙 <b>— BINANCE USDT DEPOSIT —</b> 🪙\n\n💵 <b>Exchange Rate:</b> 1 USDT = ₹{USDT_TO_INR}\n⚠️ <b>Network:</b> Please send via <b>TRC20</b> or <b>BEP20</b>.\n\n👇 <b>Send your USDT to this exact address:</b>\n<code>{deposit_address}</code>\n\n━━━━━━━━━━━━━━━━━━\n✅ <b>After sending the USDT, reply to this message with your exact TxID (Transaction Hash) to instantly claim your balance.</b>")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="menu_add_balance", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])
    await call.message.edit_text(msg, reply_markup=kb, parse_mode='HTML')
    await state.set_state(UserStates.wait_for_crypto_txid)

@dp.message(UserStates.wait_for_crypto_txid)
async def process_crypto_txid(m: Message, state: FSMContext):
    txid = m.text.strip()
    user_id = m.from_user.id
    if len(txid) < 10: return await m.answer("❌ That doesn't look like a valid TxID. Please try again.")
    if db_query("SELECT txid FROM crypto_txns WHERE txid=?", (txid,), fetchone=True):
        return await m.answer("⚠️ This Transaction ID has already been claimed in the system!", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
    api_key_check = db_query("SELECT value FROM settings WHERE key='binance_api'", fetchone=True)
    secret_key_check = db_query("SELECT value FROM settings WHERE key='binance_secret'", fetchone=True)
    if not api_key_check or not secret_key_check:
        return await m.answer("⚠️ Binance API is missing on the server. Contact Support.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
    await m.answer("🔄 <b>Verifying your TxID with Binance Blockchain...</b>\n<i>This may take up to 30 seconds...</i>", parse_mode='HTML')
    api_key = api_key_check[0]; secret_key = secret_key_check[0]
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'X-MBX-APIKEY': api_key}
    url = f"https://api.binance.com/sapi/v1/capital/deposit/hisrec?{query_string}&signature={signature}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    try: history = await resp.json(content_type=None)
                    except: history = []
                    found = False
                    for deposit in history:
                        if deposit.get("txId") == txid and deposit.get("status") == 1:
                            found = True
                            usdt_amount = float(deposit.get("amount"))
                            inr_amount = usdt_amount * USDT_TO_INR
                            db_query("INSERT INTO crypto_txns (txid, user_id, amount_usdt, timestamp) VALUES (?, ?, ?, ?)", (txid, user_id, usdt_amount, int(time.time())))
                            db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (inr_amount, user_id))
                            await m.answer(f"🎉 <b>CRYPTO DEPOSIT SUCCESSFUL!</b>\n\n✅ We safely received <b>{usdt_amount} USDT</b>.\n💰 <b>{fmt_curr(inr_amount)}</b> has been added to your balance!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
                            await send_advanced_notification(user_id, "DEPOSIT", inr_amount, product=txid, gateway="Binance Crypto")
                            log_activity(user_id, "CRYPTO_DEPOSIT", f"TxID: {txid}, Amount: {inr_amount}")
                            await state.clear()
                            break
                    if not found: await m.answer("❌ <b>TxID Not Found or Still Pending!</b>\nMake sure the transaction is fully confirmed. Try again in 5 mins.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
                else: await m.answer(f"⚠️ <b>Binance Server Error:</b> HTTP {resp.status}.", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')
        except Exception as e: await m.answer(f"⚠️ <b>Connection Error:</b> {str(e)}", reply_markup=back_kb("menu_add_balance"), parse_mode='HTML')

# ==============================================================================
# 13. SHOP – with uppercase categories and new point_down emoji
# ==============================================================================
@dp.callback_query(F.data == "menu_shop")
async def view_shop_panels(call: CallbackQuery):
    log_activity(call.from_user.id, "VIEW_SHOP")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"<blockquote>{get_emoji('product_store')} <b>SELECT PRODUCT PANEL</b></blockquote>\n\n{get_emoji('point_down')} <b>Choose a panel to view its packages:</b>"
    category_rows = db_query("SELECT name, emoji_id FROM store_categories ORDER BY id", fetchall=True) or []
    known = {str(row[0]).upper() for row in category_rows}
    for cat in FIXED_CATEGORIES:
        if cat.upper() not in known:
            category_rows.append((cat, ''))
    for cat, saved_emoji in category_rows:
        emoji_id = str(saved_emoji or '').strip() or get_category_emoji(cat) or get_emoji_icon("product_store")
        kb.inline_keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"cat_{cat[:40]}", icon_custom_emoji_id=emoji_id, style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("cat_"))
async def view_panel_names(call: CallbackQuery):
    category = call.data.split("cat_", 1)[1]
    panel_names = db_query("SELECT DISTINCT panel_name FROM products WHERE category LIKE ? AND is_active=1 AND panel_name != ''", (category + '%',), fetchall=True)
    if not panel_names:
        prods = db_query("SELECT id, name, price_inr, stock, reseller_price, validity, device_limit, panel_name, custom_emoji_id FROM products WHERE category LIKE ? AND is_active=1 AND is_maintenance=0", (category + '%',), fetchall=True)
        if not prods: return await call.answer("❌ No products available in this category yet.", show_alert=True)
        await show_products_for_panel(call, prods, category)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"<blockquote>{get_emoji('product_store')} <b>{html.escape(category.upper())} PANELS</b></blockquote>\n\n{get_emoji('point_down')} <b>Choose a product:</b>"
    for pn in panel_names:
        panel = pn[0]
        state_row = db_query("SELECT MAX(is_maintenance), MAX(is_active), custom_emoji_id FROM products WHERE category LIKE ? AND panel_name=? ORDER BY id LIMIT 1", (category + '%', panel), fetchone=True)
        maintenance = bool(state_row[0]) if state_row else False
        saved_emoji = str(state_row[2] or '').strip() if state_row else ''
        emoji_id = saved_emoji if saved_emoji.isdigit() else (get_panel_emoji(panel) or get_emoji_icon("product_store"))
        label = f"{panel} · 🛠️ MAINTENANCE" if maintenance else panel
        kb.inline_keyboard.append([InlineKeyboardButton(text=label, callback_data="pnlx_" + base64.urlsafe_b64encode((category + "\n" + panel).encode()).decode().rstrip("="), icon_custom_emoji_id=emoji_id, style="danger" if maintenance else "primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK TO PANELS", callback_data="menu_shop", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("pnlx_"))
async def view_products_for_panel(call: CallbackQuery):
    try:
        raw = call.data.split("pnlx_", 1)[1]
        raw += "=" * (-len(raw) % 4)
        category, panel_name = base64.urlsafe_b64decode(raw.encode()).decode().split("\n", 1)
    except Exception:
        return await call.answer("Invalid selection.", show_alert=True)
    maintenance_row = db_query("SELECT MAX(is_maintenance) FROM products WHERE category LIKE ? AND panel_name LIKE ? AND is_active=1", (category + '%', panel_name + '%'), fetchone=True)
    if maintenance_row and maintenance_row[0]:
        return await call.answer("🛠️ This product is currently under maintenance. Please try again later.", show_alert=True)
    prods = db_query("SELECT id, name, price_inr, stock, reseller_price, validity, device_limit, panel_name, custom_emoji_id FROM products WHERE category LIKE ? AND panel_name LIKE ? AND is_active=1 AND is_maintenance=0", (category + '%', panel_name + '%'), fetchall=True)
    if not prods: return await call.answer("No products found for this panel.", show_alert=True)
    await show_products_for_panel(call, prods, f"{category} - {panel_name}")

async def show_products_for_panel_from_message(message: Message, prods: List[Tuple], header: str):
    """Render a shared product's plan page when opened from /start product_ID."""
    user = db_query("SELECT is_reseller, is_vip FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)
    is_reseller = bool(user[0]) if user else False
    is_vip = bool(user[1]) if user else False
    saved_emoji = str(prods[0][8] or '').strip() if len(prods[0]) > 8 else ''
    product_emoji = '5312361253610475399'
    role_emoji = '6057728771719435723'
    plan_heading_emoji = '5451937962629544243'
    price_emoji = '5431750735870050726'
    validity_emoji = '5287231198098117669'
    def ce(eid, fallback):
        eid = str(eid or '').strip()
        return f'<tg-emoji emoji-id="{html.escape(eid)}">{fallback}</tg-emoji>' if eid.isdigit() else fallback
    text = (
        f'<blockquote><b>{ce(product_emoji, "🎮")} {html.escape(str(header).upper())} {ce(product_emoji, "🎮")}</b></blockquote>\n'
        f'<blockquote><b>{ce(role_emoji, "👤")} Your Account Tier: {"RESELLER" if is_reseller else "USER"}</b></blockquote>\n'
        f'<blockquote><b>{ce(plan_heading_emoji, "🛒")} Choose your access plan:</b></blockquote>\n\n'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for index, p in enumerate(prods):
        prod_id, package_name, normal_price, stock, reseller_price, validity = p[:6]
        normal_price = safe_float(normal_price)
        reseller_price = safe_float(reseller_price)
        base_price = reseller_price if is_reseller and reseller_price > 0 else normal_price
        display_price = base_price * (1 - VIP_DISCOUNT_PERCENTAGE / 100) if is_vip else base_price
        validity_label = str(validity or package_name or 'Access').upper()
        branch = '└─' if index == len(prods) - 1 else '├─'
        text += f'{branch} {ce(price_emoji, "💲")} {fmt_curr(display_price)} — {ce(validity_emoji, "⏱")} {html.escape(validity_label)}\n'
        if (stock or 0) > 0:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f'{package_name} · {fmt_curr(display_price)}', callback_data=f'buy_{prod_id}', icon_custom_emoji_id='5440841102871517055', style='success')])
        else:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f'{package_name} · Out of Stock', callback_data='ignore_stock_click', style='danger')])
    kb.inline_keyboard.append([InlineKeyboardButton(text='🏪 OPEN STORE', callback_data='menu_shop', style='primary')])
    await message.answer(text, reply_markup=kb, parse_mode='HTML')


async def show_products_for_panel(call: CallbackQuery, prods: List[Tuple], header: str):
    user = db_query("SELECT is_reseller, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    is_reseller = bool(user[0]) if user else False
    is_vip = bool(user[1]) if user else False

    # Product-specific emoji is taken from the selected product record.
    saved_product_emoji = str(prods[0][8] or '').strip() if len(prods[0]) > 8 else ''
    product_emoji = '5312361253610475399'
    title_emoji = '5312361253610475399'
    role_emoji = '6057728771719435723'
    plan_heading_emoji = '5451937962629544243'
    price_emoji = '5431750735870050726'
    validity_emoji = '5287231198098117669'
    product_name = str(prods[0][7] or header).strip().upper()

    def ce(eid, fallback):
        eid = str(eid or '').strip()
        return f'<tg-emoji emoji-id="{html.escape(eid)}">{fallback}</tg-emoji>' if eid.isdigit() else fallback

    # Keep exactly the three requested quoted headings and simple wave separators.
    separator = f'{ce("6334784630809435068", "〰️")}' + ('〰️' * 16)
    text = (
        f'<blockquote><b>{ce(title_emoji, "🎮")} {html.escape(product_name)} {ce(title_emoji, "🎮")}</b></blockquote>\n'
        f'{separator}\n'
        f'<blockquote><b>{ce(role_emoji, "👤")} Your Account Tier: {"RESELLER" if is_reseller else "USER"}</b></blockquote>\n'
        f'{separator}\n'
        f'<blockquote><b>{ce(plan_heading_emoji, "🛒")} Choose your access plan:</b></blockquote>\n\n'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for index, p in enumerate(prods):
        prod_id, package_name, normal_price, stock, reseller_price, validity, device = p[:7]
        normal_price = safe_float(normal_price)
        reseller_price = safe_float(reseller_price)
        base_price = reseller_price if is_reseller and reseller_price > 0 else normal_price
        display_price = base_price * (1 - VIP_DISCOUNT_PERCENTAGE / 100) if is_vip else base_price
        validity_label = str(validity or package_name or 'Access').upper()
        branch = '└─' if index == len(prods) - 1 else '├─'
        text += (f'{branch} {ce(price_emoji, "💲")} {fmt_curr(display_price)} — '
                 f'{ce(validity_emoji, "⏱")} {html.escape(validity_label)}\n')
        if (stock or 0) > 0:
            kb.inline_keyboard.append([InlineKeyboardButton(
                text=f'{package_name} · {fmt_curr(display_price)}', callback_data=f'buy_{prod_id}',
                icon_custom_emoji_id='5440841102871517055', style='success')])
        else:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f'{package_name} · Out of Stock', callback_data='ignore_stock_click', style='danger')])
    # Share link opens this product/panel directly at its plans, not the shop home.
    share_product_id = prods[0][0]
    bot_username = BOT_USERNAME.lstrip('@')
    direct_link = f"https://t.me/{bot_username}?start=product_{share_product_id}"
    share_url = "https://t.me/share/url?" + urllib.parse.urlencode({"url": direct_link, "text": f"{product_name} — choose your plan"})
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔗 SHARE PRODUCT", url=share_url, style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="menu_shop", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')


def get_product_price(prod, user_row):
    normal_price = safe_float(prod[1])
    reseller_price = safe_float(prod[7])
    is_reseller = bool(user_row[2]) if user_row else False
    is_vip = bool(user_row[4]) if user_row else False
    base_price = reseller_price if is_reseller and reseller_price > 0 else normal_price
    return max(0.0, base_price * (1 - VIP_DISCOUNT_PERCENTAGE / 100)) if is_vip else max(0.0, base_price)


def checkout_keyboard(prod_id: int, total: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Pay with wallet', callback_data=f'checkout_wallet_{prod_id}', icon_custom_emoji_id='5769403330761593044', style='success')],
        [InlineKeyboardButton(text='Pay with UPI', callback_data=f'checkout_upi_{prod_id}', icon_custom_emoji_id='5807750375033278838', style='primary')],
        [InlineKeyboardButton(text='Apply for coupon code', callback_data=f'checkout_coupon_{prod_id}', icon_custom_emoji_id='5294492660650744591', style='primary')],
        [InlineKeyboardButton(text='BACK', callback_data='menu_shop', icon_custom_emoji_id=get_emoji_icon('back'), style='danger')]
    ])


async def show_checkout(call: CallbackQuery, prod_id: int, coupon_code: str = '', coupon_discount: float = 0.0):
    prod = db_query("SELECT name, price_inr, stock, apk_link, validity, device_limit, category, reseller_price, panel_name FROM products WHERE id=? AND is_active=1 AND is_maintenance=0", (prod_id,), fetchone=True)
    user = db_query("SELECT balance, referred_by, is_reseller, total_saved, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if not prod or not user:
        return await call.answer('Product or user record not found.', show_alert=True)
    if safe_float(prod[2]) <= 0:
        return await call.answer('This plan is out of stock.', show_alert=True)
    price = get_product_price(prod, user)
    discount = max(0.0, min(float(coupon_discount), price))
    total = max(0.0, price - discount)
    balance = max(0.0, safe_float(user[0]))
    wallet_applied = min(balance, total)
    remaining = max(0.0, total - wallet_applied)
    name = html.escape(str(prod[0] or 'Product'))
    plan = html.escape(str(prod[4] or prod[0] or 'Plan'))
    text = (
        '<tg-emoji emoji-id="5197269100878907942">🧾</tg-emoji> <b>ORDER SUMMARY</b>\n'
        '━━━━━━━━━━━━━━━\n'
        f'<tg-emoji emoji-id="6219586456810166628">📦</tg-emoji> <b>Product:</b> {name}\n'
        f'<tg-emoji emoji-id="6055108502366461567">🗓</tg-emoji> <b>Plan:</b> {plan}\n'
        f'<tg-emoji emoji-id="6055453744722614569">💰</tg-emoji> <b>Price:</b> {fmt_curr(price)}\n'
    )
    if coupon_code and discount > 0:
        text += f'🎟 <b>Coupon:</b> {html.escape(coupon_code)} (-{fmt_curr(discount)})\n'
    text += (
        '━━━━━━━━━━━━━━━\n'
        f'<tg-emoji emoji-id="6129797816140179747">💳</tg-emoji> <b>Final Total:</b> {fmt_curr(total)}\n'
        f'👛 <b>Wallet available:</b> {fmt_curr(balance)}\n'
        f'💸 <b>Wallet applied to UPI:</b> {fmt_curr(wallet_applied)}\n'
        f'📲 <b>Remaining UPI amount:</b> {fmt_curr(remaining)}'
    )
    await call.message.edit_text(text, reply_markup=checkout_keyboard(prod_id, total), parse_mode='HTML')
    # Keep coupon data in FSM context for this user's next checkout action.
    # A later callback revalidates the code/discount against the DB.


@dp.callback_query(F.data.startswith('buy_'))
async def process_buy(call: CallbackQuery, state: FSMContext):
    try:
        prod_id = int(call.data.split('_', 1)[1])
    except (ValueError, IndexError):
        return await call.answer('Invalid product selection.', show_alert=True)
    await state.update_data(checkout_product_id=prod_id, checkout_coupon_code='', checkout_coupon_discount=0.0)
    await show_checkout(call, prod_id)


async def finalize_wallet_purchase(user_id: int, prod_id: int, coupon_code: str = ''):
    """Atomically validate, charge, reserve one key and create one order."""
    conn = sqlite3.connect('yp_shop.db', timeout=10)
    try:
        conn.execute('BEGIN IMMEDIATE')
        user = conn.execute('SELECT balance, referred_by, is_reseller, total_saved, is_vip FROM users WHERE user_id=?', (user_id,)).fetchone()
        prod = conn.execute('SELECT name, price_inr, stock, apk_link, validity, device_limit, category, reseller_price, panel_name FROM products WHERE id=? AND is_active=1 AND is_maintenance=0', (prod_id,)).fetchone()
        if not user or not prod:
            conn.rollback(); return (False, 'Product or user not found.', None)
        if not prod[2] or int(prod[2]) <= 0:
            conn.rollback(); return (False, 'This plan is out of stock.', None)
        price = get_product_price(prod, user)
        discount = 0.0
        if coupon_code:
            cpn = conn.execute('SELECT amount, uses_left FROM order_coupons WHERE code=?', (coupon_code,)).fetchone()
            used = conn.execute('SELECT 1 FROM order_coupon_redemptions WHERE user_id=? AND code=? LIMIT 1', (user_id, coupon_code)).fetchone()
            if not cpn or cpn[1] <= 0 or used:
                conn.rollback(); return (False, 'Coupon is invalid, expired, exhausted, or already used by you.', None)
            discount = min(price, max(0.0, safe_float(cpn[0])))
        total = max(0.0, price - discount)
        balance = max(0.0, safe_float(user[0]))
        if balance + 1e-9 < total:
            conn.rollback(); return (False, f'Insufficient wallet balance. Total due: {fmt_curr(total)}.', None)
        key_row = conn.execute('SELECT id, key_text FROM product_keys WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1', (prod_id,)).fetchone()
        if not key_row:
            conn.rollback(); return (False, 'No unused key is available for this plan. Admin must add stock.', None)
        delivered_key = key_row[1]
        new_balance = balance - total
        savings = max(0.0, safe_float(prod[1]) - total)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('UPDATE users SET balance=?, spent=spent+?, orders_count=orders_count+1, total_saved=total_saved+? WHERE user_id=?', (new_balance, total, savings, user_id))
        conn.execute('UPDATE product_keys SET is_used=1 WHERE id=? AND is_used=0', (key_row[0],))
        if conn.total_changes < 2:
            conn.rollback(); return (False, 'Could not reserve the key. Please try again.', None)
        conn.execute('UPDATE products SET stock=CASE WHEN stock>0 THEN stock-1 ELSE 0 END WHERE id=?', (prod_id,))
        product_full_name = f'{prod[6]} - {prod[8]} ({prod[0]})'
        conn.execute('INSERT INTO orders (user_id, product_name, price_paid, delivered_key, purchase_date) VALUES (?, ?, ?, ?, ?)', (user_id, product_full_name, total, delivered_key, now))
        if coupon_code:
            conn.execute('UPDATE order_coupons SET uses_left=uses_left-1 WHERE code=? AND uses_left>0', (coupon_code,))
            conn.execute('INSERT INTO order_coupon_redemptions (user_id, code, order_id) VALUES (?, ?, ?)', (user_id, coupon_code, f'wallet-{int(time.time())}-{user_id}'))
        if user[1]:
            commission = total * 0.15
            conn.execute('UPDATE users SET balance=balance+?, referral_earned=referral_earned+? WHERE user_id=?', (commission, commission, user[1]))
        conn.commit()
        return (True, delivered_key, {'prod': prod, 'total': total, 'new_balance': new_balance, 'product_full_name': product_full_name, 'savings': savings, 'coupon_code': coupon_code})
    except Exception as e:
        conn.rollback()
        logger.exception('Wallet checkout transaction failed: %s', e)
        return (False, 'Purchase could not be completed safely. Please retry.', None)
    finally:
        conn.close()


async def send_product_purchase_success(call: CallbackQuery, result):
    prod = result['prod']; delivered_key = result['delivered_key']
    try:
        callback_parts = (call.data or '').split('_')
        result['product_id'] = int(callback_parts[-1]) if callback_parts[-1].isdigit() else None
    except Exception:
        result['product_id'] = None
    try:
        await send_purchase_proof_group(call.from_user, result, mode='WALLET' if result.get('new_balance') is not None else 'UPI')
    except Exception:
        logger.exception('Payment proof group notification failed')
    try:
        await send_advanced_notification(call.from_user.id, 'ORDER', result['total'], product=result['product_full_name'], key=delivered_key, gateway='Wallet')
    except Exception:
        logger.exception('Purchase notification failed')
    if 'OUT_OF_STOCK' in str(delivered_key):
        return await call.message.edit_text('Purchase was not delivered because stock was unavailable. Please contact admin; do not pay again.', reply_markup=back_kb('menu_shop'), parse_mode='HTML')
    msg = (
        '✅ <b>PURCHASE SUCCESSFUL!</b>\n━━━━━━━━━━━━━━━━━━\n'
        f'📦 <b>Panel:</b> {html.escape(str(prod[6] or ""))}\n'
        f'📁 <b>Panel Name:</b> {html.escape(str(prod[8] or ""))}\n'
        f'⏱ <b>Package:</b> {html.escape(str(prod[0] or ""))}\n'
        f'💰 <b>Amount Deducted:</b> {fmt_curr(result["total"])}\n'
        f'👛 <b>Remaining Wallet:</b> {fmt_curr(result["new_balance"])}\n'
        f'📱 <b>Device Limit:</b> {html.escape(str(prod[5] or "1 Device"))}\n━━━━━━━━━━━━━━━━━━\n'
    )
    if prod[3] and str(prod[3]).startswith('http'):
        msg += f'📥 <b>APK Link:</b> <a href="{html.escape(str(prod[3]), quote=True)}">Click Here to Download</a>\n\n'
    msg += f'🔑 <b>Your Exclusive Key:</b>\n<code>{html.escape(str(delivered_key))}</code>\n\n<i>Support: {html.escape(ADMIN_CONTACT)}</i>'
    await call.message.edit_text(msg, reply_markup=back_kb('menu_shop'), disable_web_page_preview=True, parse_mode='HTML')


@dp.callback_query(F.data.startswith('checkout_wallet_'))
async def checkout_pay_wallet(call: CallbackQuery, state: FSMContext):
    try: prod_id = int(call.data.rsplit('_', 1)[1])
    except ValueError: return await call.answer('Invalid product.', show_alert=True)
    data = await state.get_data()
    coupon_code = str(data.get('checkout_coupon_code') or '').upper()
    ok, value, extra = await asyncio.to_thread(finalize_wallet_purchase, call.from_user.id, prod_id, coupon_code)
    if not ok:
        return await call.answer(value, show_alert=True)
    result = {'delivered_key': value, **extra}
    log_activity(call.from_user.id, 'PURCHASE_SUCCESS', f'Product: {extra["product_full_name"]}, Paid: {extra["total"]}')
    await state.clear()
    await send_product_purchase_success(call, result)


@dp.callback_query(F.data.startswith('checkout_coupon_'))
async def checkout_coupon_start(call: CallbackQuery, state: FSMContext):
    try: prod_id = int(call.data.rsplit('_', 1)[1])
    except ValueError: return await call.answer('Invalid product.', show_alert=True)
    await state.update_data(checkout_product_id=prod_id)
    await state.set_state(UserStates.wait_for_order_coupon)
    await call.message.edit_text('🎟️ <b>Apply Coupon Code</b>\n\nSend your coupon code now.\nSend /cancel to stop.', reply_markup=back_kb('menu_shop'), parse_mode='HTML')


@dp.message(UserStates.wait_for_order_coupon)
async def checkout_coupon_apply(message: Message, state: FSMContext):
    code = (message.text or '').strip().upper()
    if code == '/CANCEL':
        await state.clear()
        return await message.answer('Coupon entry cancelled.', reply_markup=main_menu_kb(message.from_user.id))
    data = await state.get_data()
    try: prod_id = int(data.get('checkout_product_id'))
    except (TypeError, ValueError):
        await state.clear(); return await message.answer('Checkout expired. Open the product again.', reply_markup=main_menu_kb(message.from_user.id))
    coupon = db_query('SELECT amount, uses_left FROM order_coupons WHERE code=?', (code,), fetchone=True)
    already = db_query('SELECT 1 FROM order_coupon_redemptions WHERE user_id=? AND code=? LIMIT 1', (message.from_user.id, code), fetchone=True)
    if not coupon or safe_float(coupon[0]) <= 0 or int(coupon[1]) <= 0 or already:
        return await message.answer('❌ Invalid, expired, exhausted, or already-used coupon. Try another code or send /cancel.')
    prod = db_query('SELECT name, price_inr, stock, apk_link, validity, device_limit, category, reseller_price, panel_name FROM products WHERE id=? AND is_active=1 AND is_maintenance=0', (prod_id,), fetchone=True)
    user = db_query('SELECT balance, referred_by, is_reseller, total_saved, is_vip FROM users WHERE user_id=?', (message.from_user.id,), fetchone=True)
    if not prod or not user:
        await state.clear(); return await message.answer('Product unavailable. Please open the shop again.')
    discount = min(get_product_price(prod, user), safe_float(coupon[0]))
    await state.update_data(checkout_coupon_code=code, checkout_coupon_discount=discount)
    # Return to the same checkout message flow with the coupon applied.
    text = ('🎟️ <b>Coupon applied</b>\n'
            f'Code: <code>{html.escape(code)}</code>\nDiscount: <b>{fmt_curr(discount)}</b>\n\n'
            'Tap the button below to reopen checkout and continue.')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='CONTINUE TO CHECKOUT', callback_data=f'checkout_show_{prod_id}', style='success')],
        [InlineKeyboardButton(text='CANCEL', callback_data='menu_shop', style='danger')]
    ])
    await message.answer(text, reply_markup=kb, parse_mode='HTML')
    await state.set_state(None)


@dp.callback_query(F.data.startswith('checkout_show_'))
async def checkout_show_after_coupon(call: CallbackQuery, state: FSMContext):
    try: prod_id = int(call.data.rsplit('_', 1)[1])
    except ValueError: return await call.answer('Invalid product.', show_alert=True)
    data = await state.get_data()
    await show_checkout(call, prod_id, str(data.get('checkout_coupon_code') or ''), safe_float(data.get('checkout_coupon_discount')))


async def create_fampay_order(amount: float, user_id: int, customer_name: str = ''):
    api_key = get_setting('fampay_api_key', '').strip()
    if not api_key:
        raise RuntimeError('FamGateway API key is not configured by admin.')
    payload = {'amount': round(float(amount), 2), 'customer_name': customer_name or str(user_id), 'customer_phone': ''}
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post('https://famgateway.in/api/create-order', json=payload,
                                headers={'X-Api-Key': api_key, 'Content-Type': 'application/json'}) as resp:
            data = await resp.json(content_type=None)
            if resp.status != 200 or data.get('status') != 'success' or not isinstance(data.get('data'), dict):
                raise RuntimeError(f'FamGateway order creation failed (HTTP {resp.status}).')
            return data['data']


async def verify_fampay_order(order_id: str):
    api_key = get_setting('fampay_api_key', '').strip()
    if not api_key:
        raise RuntimeError('FamGateway API key is not configured by admin.')
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get('https://famgateway.in/api/verify-order.php', params={'order_id': order_id},
                               headers={'X-Api-Key': api_key}, timeout=timeout) as resp:
            data = await resp.json(content_type=None)
            if resp.status != 200 or not isinstance(data, dict):
                raise RuntimeError(f'FamGateway verification failed (HTTP {resp.status}).')
            return data


@dp.callback_query(F.data.startswith('checkout_upi_'))
async def checkout_pay_upi(call: CallbackQuery, state: FSMContext):
    try: prod_id = int(call.data.rsplit('_', 1)[1])
    except ValueError: return await call.answer('Invalid product.', show_alert=True)
    data = await state.get_data()
    coupon_code = str(data.get('checkout_coupon_code') or '').upper()
    prod = db_query('SELECT name, price_inr, stock, apk_link, validity, device_limit, category, reseller_price, panel_name FROM products WHERE id=? AND is_active=1 AND is_maintenance=0', (prod_id,), fetchone=True)
    user = db_query('SELECT balance, referred_by, is_reseller, total_saved, is_vip FROM users WHERE user_id=?', (call.from_user.id,), fetchone=True)
    if not prod or not user: return await call.answer('Product or user not found.', show_alert=True)
    if not prod[2] or int(prod[2]) <= 0: return await call.answer('Out of stock.', show_alert=True)
    price = get_product_price(prod, user)
    discount = 0.0
    if coupon_code:
        cpn = db_query('SELECT amount, uses_left FROM order_coupons WHERE code=?', (coupon_code,), fetchone=True)
        used = db_query('SELECT 1 FROM order_coupon_redemptions WHERE user_id=? AND code=? LIMIT 1', (call.from_user.id, coupon_code), fetchone=True)
        if not cpn or int(cpn[1]) <= 0 or used: return await call.answer('Coupon is no longer valid.', show_alert=True)
        discount = min(price, safe_float(cpn[0]))
    total = max(0.0, price - discount)
    # Reserve wallet contribution atomically so the user cannot spend it twice.
    conn = sqlite3.connect('yp_shop.db', timeout=10)
    try:
        conn.execute('BEGIN IMMEDIATE')
        fresh = conn.execute('SELECT balance FROM users WHERE user_id=?', (call.from_user.id,)).fetchone()
        if not fresh: conn.rollback(); return await call.answer('User record not found.', show_alert=True)
        wallet_used = min(max(0.0, safe_float(fresh[0])), total)
        conn.execute('UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?', (wallet_used, call.from_user.id, wallet_used))
        if conn.total_changes < 1:
            conn.rollback(); return await call.answer('Wallet changed. Please reopen checkout.', show_alert=True)
        conn.commit()
    except Exception:
        conn.rollback(); return await call.answer('Could not reserve wallet balance. Try again.', show_alert=True)
    finally: conn.close()
    remaining = round(max(0.0, total - wallet_used), 2)
    if remaining <= 0:
        # All payable value is covered by wallet; restore the reservation and use atomic wallet checkout.
        db_query('UPDATE users SET balance=balance+? WHERE user_id=?', (wallet_used, call.from_user.id))
        ok, value, extra = await asyncio.to_thread(finalize_wallet_purchase, call.from_user.id, prod_id, coupon_code)
        if not ok: return await call.answer(value, show_alert=True)
        await state.clear()
        return await send_product_purchase_success(call, {'delivered_key': value, **extra})
    try:
        order = await create_fampay_order(remaining, call.from_user.id, call.from_user.first_name)
        gateway_order_id = str(order.get('order_id') or '')
        qr_url = str(order.get('qr_url') or '')
        checkout_url = str(order.get('checkout_url') or '')
        if not gateway_order_id:
            raise RuntimeError('FamGateway response did not include an order ID.')
        conn = sqlite3.connect('yp_shop.db', timeout=10)
        try:
            conn.execute('INSERT INTO product_payment_orders (order_id,user_id,product_id,product_name,amount_due,wallet_used,coupon_code,coupon_discount,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                         (gateway_order_id, call.from_user.id, prod_id, str(prod[0]), remaining, wallet_used, coupon_code or None, discount, 'pending', int(time.time())))
            conn.commit()
        finally: conn.close()
    except Exception as e:
        db_query('UPDATE users SET balance=balance+? WHERE user_id=?', (wallet_used, call.from_user.id))
        logger.warning('FamGateway product checkout create failed: %s', e)
        return await call.message.edit_text(f'❌ <b>Could not create UPI order.</b> Your reserved wallet amount {fmt_curr(wallet_used)} was returned. Check FamGateway setup and try again.', reply_markup=back_kb('menu_shop'), parse_mode='HTML')
    buttons = []
    if checkout_url: buttons.append([InlineKeyboardButton(text='OPEN UPI CHECKOUT', url=checkout_url, style='success')])
    buttons.append([InlineKeyboardButton(text='VERIFY PAYMENT', callback_data=f'product_verify_{gateway_order_id}', style='primary')])
    buttons.append([InlineKeyboardButton(text='CANCEL', callback_data=f'product_cancel_{gateway_order_id}', style='danger')])
    text = (f'💳 <b>FAMGATEWAY PAYMENT</b>\n\nProduct: <b>{html.escape(str(prod[0]))}</b>\n'
            f'Order ID: <code>{html.escape(gateway_order_id)}</code>\n'
            f'Wallet applied: <b>{fmt_curr(wallet_used)}</b>\n'
            f'UPI amount: <b>{fmt_curr(remaining)}</b>\n\n'
            'Complete the UPI payment, then tap VERIFY PAYMENT. The product will be delivered only after server-side payment verification.')
    if qr_url:
        try:
            await call.message.delete()
            await bot.send_photo(call.from_user.id, qr_url, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode='HTML')
        except Exception:
            await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode='HTML')
    else:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode='HTML')


@dp.callback_query(F.data.startswith('product_cancel_'))
async def product_payment_cancel(call: CallbackQuery):
    order_id = call.data[len('product_cancel_'):]
    row = db_query('SELECT user_id, wallet_used, status FROM product_payment_orders WHERE order_id=?', (order_id,), fetchone=True)
    if not row or row[0] != call.from_user.id: return await call.answer('Order not found.', show_alert=True)
    if row[2] == 'pending':
        conn = sqlite3.connect('yp_shop.db', timeout=10)
        try:
            conn.execute('BEGIN IMMEDIATE')
            changed = conn.execute("UPDATE product_payment_orders SET status='cancelled' WHERE order_id=? AND user_id=? AND status='pending'", (order_id, call.from_user.id)).rowcount
            if changed:
                conn.execute('UPDATE users SET balance=balance+? WHERE user_id=?', (row[1], call.from_user.id))
            conn.commit()
        except Exception:
            conn.rollback(); return await call.answer('Could not cancel safely. Contact support.', show_alert=True)
        finally: conn.close()
    await call.message.edit_text('Payment order cancelled. Any reserved wallet balance has been returned. If you already paid, verify the payment instead of cancelling.', reply_markup=back_kb('menu_shop'), parse_mode='HTML')


@dp.callback_query(F.data.startswith('product_verify_'))
async def product_payment_verify(call: CallbackQuery):
    order_id = call.data[len('product_verify_'):]
    row = db_query('SELECT user_id, product_id, product_name, amount_due, wallet_used, coupon_code, coupon_discount, status, created_at FROM product_payment_orders WHERE order_id=?', (order_id,), fetchone=True)
    if not row or row[0] != call.from_user.id: return await call.answer('Invalid payment order.', show_alert=True)
    if row[7] == 'paid': return await call.answer('This order has already been fulfilled.', show_alert=True)
    if row[7] != 'pending': return await call.answer('This payment order is no longer pending.', show_alert=True)
    try:
        verification = await verify_fampay_order(order_id)
    except Exception as e:
        logger.warning('FamGateway verify failed: %s', e)
        return await call.answer('Could not verify with FamGateway right now. Try again shortly.', show_alert=True)
    gateway_status = str(verification.get('status', '')).lower()
    data = verification.get('data') if isinstance(verification.get('data'), dict) else verification
    paid_amount = safe_float(data.get('amount', data.get('payable_amount', 0)))
    if gateway_status != 'success' or paid_amount + 0.009 < safe_float(row[3]):
        if gateway_status == 'expired':
            conn = sqlite3.connect('yp_shop.db', timeout=10)
            try:
                conn.execute('BEGIN IMMEDIATE')
                changed = conn.execute("UPDATE product_payment_orders SET status='expired' WHERE order_id=? AND status='pending'", (order_id,)).rowcount
                if changed: conn.execute('UPDATE users SET balance=balance+? WHERE user_id=?', (row[4], call.from_user.id))
                conn.commit()
            except Exception: conn.rollback()
            finally: conn.close()
            return await call.message.edit_text('⌛ Payment expired. Reserved wallet balance was returned. Please start checkout again.', reply_markup=back_kb('menu_shop'), parse_mode='HTML')
        return await call.answer('Payment is not confirmed yet. Please wait and verify again.', show_alert=True)
    # Payment confirmed: atomically reserve stock and mark the gateway order paid once.
    conn = sqlite3.connect('yp_shop.db', timeout=10)
    try:
        conn.execute('BEGIN IMMEDIATE')
        current = conn.execute('SELECT status FROM product_payment_orders WHERE order_id=?', (order_id,)).fetchone()
        if not current or current[0] != 'pending':
            conn.rollback(); return await call.answer('This order has already been processed.', show_alert=True)
        prod = conn.execute('SELECT name, price_inr, stock, apk_link, validity, device_limit, category, reseller_price, panel_name FROM products WHERE id=? AND is_active=1 AND is_maintenance=0', (row[1],)).fetchone()
        user = conn.execute('SELECT balance, referred_by, is_reseller, total_saved, is_vip FROM users WHERE user_id=?', (call.from_user.id,)).fetchone()
        if not prod or not user or not prod[2] or int(prod[2]) <= 0:
            conn.rollback(); return await call.answer('Payment confirmed but stock is unavailable. Contact admin with order ID.', show_alert=True)
        key_row = conn.execute('SELECT id,key_text FROM product_keys WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1', (row[1],)).fetchone()
        if not key_row:
            conn.rollback(); return await call.answer('Payment confirmed but no key is available. Contact admin with order ID.', show_alert=True)
        conn.execute('UPDATE product_keys SET is_used=1 WHERE id=? AND is_used=0', (key_row[0],))
        conn.execute('UPDATE products SET stock=CASE WHEN stock>0 THEN stock-1 ELSE 0 END WHERE id=?', (row[1],))
        total = safe_float(row[3]) + safe_float(row[4])
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        product_full_name = f'{prod[6]} - {prod[8]} ({prod[0]})'
        conn.execute('UPDATE users SET spent=spent+?, orders_count=orders_count+1, total_saved=total_saved+? WHERE user_id=?', (total, max(0.0, safe_float(prod[1])-total), call.from_user.id))
        conn.execute('INSERT INTO orders (user_id, product_name, price_paid, delivered_key, purchase_date) VALUES (?,?,?,?,?)', (call.from_user.id, product_full_name, total, key_row[1], now))
        if row[5]:
            conn.execute('UPDATE order_coupons SET uses_left=uses_left-1 WHERE code=? AND uses_left>0', (row[5],))
            conn.execute('INSERT OR IGNORE INTO order_coupon_redemptions (user_id,code,order_id) VALUES (?,?,?)', (call.from_user.id, row[5], order_id))
        conn.execute("UPDATE product_payment_orders SET status='paid' WHERE order_id=? AND status='pending'", (order_id,))
        conn.commit()
    except Exception as e:
        conn.rollback(); logger.exception('Product payment fulfilment failed: %s', e)
        return await call.answer('Payment is verified but fulfillment needs admin review. Share the order ID with support.', show_alert=True)
    finally: conn.close()
    log_activity(call.from_user.id, 'PURCHASE_SUCCESS_UPI', f'Order: {order_id}, Amount: {total}')
    result = {'delivered_key': key_row[1], 'prod': prod, 'total': total, 'new_balance': safe_float(user[0]), 'product_full_name': product_full_name, 'savings': max(0.0, safe_float(prod[1])-total)}
    await send_product_purchase_success(call, result)

# ==============================================================================
# 14. USER DASHBOARD, FILES, VIP, RESELLER, ORDERS, PROFILE, REFERRAL
# ==============================================================================
@dp.callback_query(F.data == "menu_all_files")
async def all_files_handler(call: CallbackQuery):
    link_q = db_query("SELECT value FROM settings WHERE key='all_files_link'", fetchone=True)
    link = link_q[0] if link_q and link_q[0] != 'None' else None
    if link:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Access Download Channel ↗️", url=link, icon_custom_emoji_id=get_emoji_icon("download"), style="success")],
            [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
        ])
        text = get_ui_text("download_files")
        await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')
    else:
        await call.answer("⚠️ Admin has not configured the private download channel link yet.", show_alert=True)

@dp.callback_query(F.data == "menu_vip_dash")
async def vip_dashboard(call: CallbackQuery):
    u = db_query("SELECT balance, is_vip, vip_since FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    is_vip = bool(u[1])
    status_str = "🟢 Active (Lifetime)" if is_vip else "🔴 Not Subscribed"
    text = get_ui_text("vip_menu", vip_status=status_str)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if is_vip:
        text += f"\n📅 <b>Member Since:</b> {u[2]}\n\nEnjoy your permanent 15% discount!"
    else:
        text += f"\n\n💳 <b>Your Current Balance:</b> {fmt_curr(u[0])}\n"
        if u[0] >= VIP_PRICE_INR: kb.inline_keyboard.append([InlineKeyboardButton(text=f"✅ Purchase VIP for {fmt_curr(VIP_PRICE_INR)}", callback_data="execute_vip_upgrade", style="success")])
        else:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ Need {fmt_curr(VIP_PRICE_INR)} to Upgrade", callback_data="ignore_stock_click", style="danger")])
            kb.inline_keyboard.append([InlineKeyboardButton(text="💳 Add Balance Now", callback_data="menu_add_balance", style="success")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "execute_vip_upgrade")
async def execute_vip_upgrade(call: CallbackQuery):
    u = db_query("SELECT balance, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if u[1]: return await call.answer("⚠️ You are already a VIP Member!", show_alert=True)
    if u[0] < VIP_PRICE_INR: return await call.answer(f"❌ Your balance dropped below {VIP_PRICE_INR}.", show_alert=True)
    new_balance = u[0] - VIP_PRICE_INR
    now_date = datetime.now().strftime("%Y-%m-%d")
    db_query("UPDATE users SET balance=?, is_vip=1, vip_since=? WHERE user_id=?", (new_balance, now_date, call.from_user.id))
    log_activity(call.from_user.id, "UPGRADED_VIP")
    try: await bot.send_message(ADMIN_ID, f"🌟 <b>NEW VIP UPGRADE</b>\n👤 User ID: <code>{call.from_user.id}</code>", parse_mode='HTML')
    except: pass
    await call.answer("🎉 Upgrade Successful! You are now a VIP Member.", show_alert=True)
    await vip_dashboard(call)

@dp.callback_query(F.data == "menu_reseller_dash")
async def reseller_dashboard(call: CallbackQuery):
    u = db_query("SELECT balance, is_reseller, reseller_since, total_saved FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    status_check = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    system_status = status_check[0] if status_check else "ON"
    setup_fee = safe_float(get_setting("reseller_setup_fee", "200.0"))
    min_balance = safe_float(get_setting("reseller_min_balance", "500.0"))
    if u[1]: 
        text = (f"{get_emoji('shield_icon')} <b><u>— RESELLER DASHBOARD —</u></b> {get_emoji('shield_icon')}\n\n🟢 <b>Status:</b> Active\n📅 <b>Since:</b> {u[2]}\n{get_emoji('money_icon')} <b>Total Saved:</b> {fmt_curr(u[3])}\n\n🎉 You are enjoying exclusive wholesale prices on all products!")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])
        await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')
        return
    if system_status == "OFF": return await call.answer("⚠️ Wholesale / Reseller registrations are currently closed by Admin.", show_alert=True)
    text = (f"⚡ <b><u>— BECOME A RESELLER —</u></b> ⚡\n\nUpgrade your account to access wholesale <b>Reseller Prices</b>!\n\n📋 <b>Requirements to Upgrade:</b>\n1️⃣ Must have a minimum balance of <b>{fmt_curr(min_balance)}</b>.\n2️⃣ A one-time setup fee of <b>{fmt_curr(setup_fee)}</b> will be deducted.\n\n💳 <b>Your Current Balance:</b> {fmt_curr(u[0])}\n")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if u[0] >= min_balance: kb.inline_keyboard.append([InlineKeyboardButton(text=f"✅ Pay {fmt_curr(setup_fee)} & Become Reseller", callback_data="execute_reseller_upgrade", style="success")])
    else:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ Insufficient Balance (Need {fmt_curr(min_balance)})", callback_data="ignore_stock_click", style="danger")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="💳 Add Balance", callback_data="menu_add_balance", style="success")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "execute_reseller_upgrade")
async def execute_reseller_upgrade(call: CallbackQuery):
    setup_fee = safe_float(get_setting("reseller_setup_fee", "200.0"))
    min_balance = safe_float(get_setting("reseller_min_balance", "500.0"))
    u = db_query("SELECT balance, is_reseller FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if u[1]: return await call.answer("⚠️ You are already a Reseller!", show_alert=True)
    if u[0] < min_balance: return await call.answer(f"❌ Your balance dropped below {fmt_curr(min_balance)}. Please top up.", show_alert=True)
    new_balance = u[0] - setup_fee
    db_query("UPDATE users SET balance=?, is_reseller=1, reseller_since=?, account_type='Reseller' WHERE user_id=?", (new_balance, datetime.now().strftime("%Y-%m-%d"), call.from_user.id))
    log_activity(call.from_user.id, "UPGRADED_RESELLER")
    try: await bot.send_message(ADMIN_ID, f"👑 <b>NEW RESELLER UPGRADE</b>\n👤 User ID: <code>{call.from_user.id}</code>", parse_mode='HTML')
    except: pass
    await call.answer("🎉 Upgrade Successful! Welcome to the Reseller tier.", show_alert=True)
    await reseller_dashboard(call)

@dp.callback_query(F.data == "menu_orders")
async def my_orders(call: CallbackQuery):
    orders = db_query("SELECT product_name, delivered_key, purchase_date, price_paid FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (call.from_user.id,), fetchall=True)
    if not orders: return await call.message.edit_text("🧾 You haven't made any purchases yet. Your vault is empty.", reply_markup=back_kb(), parse_mode='HTML')
    text = "🧾 <b><u>— YOUR RECENT ORDERS (LAST 10) —</u></b> 🧾\n\n"
    for o in orders: text += f"📦 <b>{o[0]}</b> ({fmt_curr(o[3])})\n🔑 <code>{o[1]}</code>\n📅 <i>{o[2]}</i>\n━━━━━━━━━━━━━━━━\n"
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "menu_profile")
async def show_profile(call: CallbackQuery):
    u = db_query("SELECT user_id, first_name, account_type, balance, orders_count, spent, referrals_count, joined_date, is_reseller, reseller_since, total_saved, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    acc_type_display = []
    if u[8]: acc_type_display.append(f"{get_emoji('reseller')} Reseller")
    if u[11]: acc_type_display.append(f"{get_emoji('vip')} VIP")
    type_str = " | ".join(acc_type_display) if acc_type_display else f"{get_emoji('regular_user')} Regular User"
    text = (
        f"{get_emoji('grid_id')} <b><u>— YOUR SECURE PROFILE —</u></b> {get_emoji('grid_id')}\n\n"
        f"{get_emoji('grid_id')} <b>Grid ID:</b> <code>{u[0]}</code>\n"
        f"{get_emoji('name')} <b>Name:</b> {u[1]}\n"
        f"{get_emoji('account_level')} <b>Account Level:</b> {type_str}\n\n"
        f"{get_emoji('wallet_left')} <b>— Wallet —</b> {get_emoji('wallet_right')}\n"
        f"{get_emoji('wallet_left')} <b>Current Balance:</b> {fmt_curr(u[3])} {get_emoji('wallet_right')}\n\n"
        f"{get_emoji('global_stats')} <b>— Global Statistics —</b>\n"
        f"{get_emoji('total_orders')} <b>Total Orders:</b> {u[4]}\n"
        f"{get_emoji('total_spent')} <b>Total Spent:</b> {fmt_curr(u[5])}\n"
        f"{get_emoji('total_referrals')} <b>Total Referrals:</b> {u[6]}\n\n"
    )
    if u[8]:
        text += f"{get_emoji('shield_icon')} <b>— RESELLER METRICS —</b> {get_emoji('shield_icon')}\n{get_emoji('money_icon')} <b>Total Saved via Reseller:</b> {fmt_curr(u[10])}\n\n"
    text += f"{get_emoji('joined_grid')} <b>Joined Grid:</b> {u[7]}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Redeem Promo Code",
            callback_data="redeem_coupon",
            icon_custom_emoji_id=get_emoji_icon('redeem_icon'),
            style="success"
        )],
        [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "redeem_coupon")
async def redeem_coupon_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🎟 <b>Please enter your VIP / Promo redeem code below:</b>", reply_markup=back_kb("menu_profile"), parse_mode='HTML')
    await state.set_state(UserStates.wait_for_redeem)

@dp.message(UserStates.wait_for_redeem)
async def process_redeem(m: Message, state: FSMContext):
    code = m.text.strip().upper()
    user_id = m.from_user.id
    if db_query("SELECT * FROM redeemed WHERE user_id=? AND code=?", (user_id, code), fetchone=True):
        await m.answer("❌ Anti-Fraud Alert: You already redeemed this unique code!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
        await state.clear()
        return
    coupon = db_query("SELECT amount, uses_left FROM coupons WHERE code=?", (code,), fetchone=True)
    if not coupon: await m.answer("❌ Invalid or Expired Code!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
    elif coupon[1] <= 0: await m.answer("❌ This code's usage limit has been fully claimed by other users.", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
    else:
        db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (coupon[0], user_id))
        db_query("UPDATE coupons SET uses_left = uses_left - 1 WHERE code=?", (code,))
        db_query("INSERT INTO redeemed (user_id, code) VALUES (?, ?)", (user_id, code))
        log_activity(user_id, "PROMO_REDEEMED", f"Code: {code}, Amount: {coupon[0]}")
        await m.answer(f"🎉 <b>Success!</b>\nSafely added {fmt_curr(coupon[0])} to your balance!", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
        try:
            user_info = db_query("SELECT first_name FROM users WHERE user_id=?", (user_id,), fetchone=True)
            uname = user_info[0] if user_info else "Unknown User"
            await bot.send_message(ADMIN_ID, f"🎟 <b>PROMO CODE REDEEMED!</b>\n👤 User: {uname} (<code>{user_id}</code>)\n🔖 Code: <b>{code}</b>\n💵 Amount: {fmt_curr(coupon[0])}", parse_mode='HTML')
        except Exception: pass
    await state.clear()

@dp.callback_query(F.data == "menu_referral")
async def show_referral(call: CallbackQuery):
    u = db_query("SELECT referrals_count, referral_earned FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{call.from_user.id}"
    text = (f"{get_emoji('referral')} <b><u>AFFILIATE PROGRAM</u></b> {get_emoji('referral')}\n\n✅ <b>Status:</b> ACTIVE\n💰 Earn <b>15% flat commission</b> on every successful purchase made by your referred friends!\n\n📊 <b>YOUR STATS:</b>\n👥 Total Invited: {u[0]}\n💵 Life-time Earned: {fmt_curr(u[1])}\n\n🔗 <b>Your Invite Link:</b>\n<code>{ref_link}</code>\n\n<i>Simply copy and share this link to start earning!</i>")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

# ==============================================================================
# 15. LUDO / DICE SPIN
# ==============================================================================
@dp.callback_query(F.data == "menu_spin_landing")
async def lucky_spin_landing(call: CallbackQuery):
    status_check = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    spin_status = status_check[0] if status_check else "ON"
    if spin_status == "OFF": return await call.answer("⚠️ Lucky Ludo Spin is currently disabled by Admin.", show_alert=True)
    await call.message.edit_text(f"{get_emoji('ludo_spin')} <b><u>— LUDO SPIN —</u></b> {get_emoji('ludo_spin')}\n\nTest your luck! You can spin once every 24 hours.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Spin Dice Now!", callback_data="execute_spin", style="success")], 
        [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ]), parse_mode='HTML')

@dp.callback_query(F.data == "execute_spin")
async def execute_spin(call: CallbackQuery):
    status_check = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    if status_check and status_check[0] == "OFF": return await call.answer("⚠️ Lucky Spin is disabled.", show_alert=True)
    u = db_query("SELECT last_spin, balance, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    now = datetime.now()
    if u[0] and now < datetime.strptime(u[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        return await call.message.edit_text("❌ <b>Cooldown Active!</b>\nYou already played today. Come back tomorrow.", reply_markup=back_kb(), parse_mode='HTML')
    await call.message.delete()
    dice_msg = await bot.send_dice(chat_id=call.message.chat.id, emoji="🎲")
    await asyncio.sleep(SPIN_DELAY_SECONDS) 
    dice_val = dice_msg.dice.value
    limit_check = db_query("SELECT value FROM settings WHERE key='daily_spin_limit'", fetchone=True)
    limit = safe_float(limit_check[0]) if limit_check else 50.0
    rewards_db = db_query("SELECT amount FROM spin_rewards WHERE amount <= ?", (limit,), fetchall=True)
    rewards_list = [r[0] for r in rewards_db] if rewards_db else [0.0]
    reward = random.choice(rewards_list)
    if bool(u[2]) and reward > 0: reward = reward * 2.0
    new_bal = u[1] + reward
    db_query("UPDATE users SET balance=?, last_spin=? WHERE user_id=?", (new_bal, now.strftime("%Y-%m-%d %H:%M:%S"), call.from_user.id))
    log_activity(call.from_user.id, "PLAYED_SPIN", f"Reward: {reward}, Dice: {dice_val}")
    msg = get_ui_text("lucky_dice_result", dice_value=dice_val, won_amount=fmt_curr(reward), new_balance=fmt_curr(new_bal))
    if bool(u[2]) and reward > 0: msg += "\n\n<i>🌟 VIP Bonus: 2x Multiplier Applied!</i>"
    await dice_msg.reply(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📚 BACK TO MENU", callback_data="back_main", style="success")]]), parse_mode='HTML')

# ==============================================================================
# 16. TUTORIALS & SUPPORT
# ==============================================================================
@dp.callback_query(F.data == "menu_how_to")
async def tutorial_system(call: CallbackQuery):
    video_link_query = db_query("SELECT value FROM settings WHERE key='how_to_video'", fetchone=True)
    video_link = video_link_query[0] if video_link_query and video_link_query[0] != 'None' else None
    text = (f"{get_emoji('tutorial')} <b><u>— TUTORIALS & GUIDE —</u></b> {get_emoji('tutorial')}\n\n1️⃣ Add funds via <b>Add Balance</b>\n2️⃣ Navigate to <b>Product Store</b>\n3️⃣ Choose your desired Panel and Package validity.\n4️⃣ The Key and Installation APK link will be instantly provided.")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if video_link: kb.inline_keyboard.append([InlineKeyboardButton(text="Watch Full Video Tutorial", url=video_link, icon_custom_emoji_id=get_emoji_icon("tutorial"), style="success")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "menu_support")
async def support_center(call: CallbackQuery):
    telegram_link = get_setting("support_telegram", "https://t.me/YourSupport")
    whatsapp_link = get_setting("support_whatsapp", "https://wa.me/YourNumber")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Contact on Telegram", url=telegram_link, icon_custom_emoji_id=get_emoji_icon("telegram"), style="primary")],
        [InlineKeyboardButton(text="Contact on WhatsApp", url=whatsapp_link, icon_custom_emoji_id=get_emoji_icon("whatsapp"), style="primary")],
        [InlineKeyboardButton(text="🎫 Open New Ticket", callback_data="open_ticket", style="success"), InlineKeyboardButton(text="📋 My Open Tickets", callback_data="my_tickets", style="success")], 
        [InlineKeyboardButton(text="BACK", callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(f"{get_emoji('telegram')}{get_emoji('whatsapp')} <b><u>— PREMIUM SUPPORT CENTER —</u></b>\n\nContact us via Telegram or WhatsApp for instant help, or open a support ticket for admin assistance.", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "my_tickets")
async def view_my_tickets(call: CallbackQuery):
    tickets = db_query("SELECT id, message, status, created_at FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT 5", (call.from_user.id,), fetchall=True)
    if not tickets: return await call.message.edit_text("📋 You do not have any active or previous support tickets.", reply_markup=back_kb("menu_support"), parse_mode='HTML')
    text = "📋 <b><u>— Your Recent Tickets —</u></b> 📋\n\n"
    for t in tickets:
        status_icon = "🟢" if t[2] == 'Open' else "🔴"
        text += f"🎫 <b>Ticket #{t[0]}</b> | Status: {status_icon} <b>{t[2]}</b>\n📅 <i>{t[3]}</i>\n📝 <i>{t[1][:80]}...</i>\n\n"
    await call.message.edit_text(text, reply_markup=back_kb("menu_support"), parse_mode='HTML')

@dp.callback_query(F.data == "open_ticket")
async def open_ticket_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("📝 <b>Please type your issue/message below in detail:</b>", reply_markup=back_kb("menu_support"), parse_mode='HTML')
    await state.set_state(UserStates.wait_for_ticket)

@dp.message(UserStates.wait_for_ticket)
async def process_ticket(m: Message, state: FSMContext):
    db_query("INSERT INTO tickets (user_id, message, created_at) VALUES (?, ?, ?)", (m.from_user.id, m.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    await m.answer("✅ <b>Ticket Submitted Successfully!</b> Admins will reply soon.", reply_markup=main_menu_kb(m.from_user.id), parse_mode='HTML')
    try: await bot.send_message(ADMIN_ID, f"🚨 <b>NEW SUPPORT TICKET</b>\nFrom: <code>{m.from_user.id}</code>\nMsg: {m.text}", parse_mode='HTML')
    except: pass
    log_activity(m.from_user.id, "OPENED_TICKET")
    await state.clear()

# ==============================================================================
# 17. ADMIN PANEL
# ==============================================================================
@dp.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    await message.answer("⚙️ <b>Advanced Admin Terminal</b>\n<i>Authorized Access Granted.</i>", reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_panel_back")
async def back_to_admin(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ <b>Advanced Admin Terminal</b>\n<i>Authorized Access Granted.</i>", reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_toggle_vip_sys")
async def toggle_vip_sys(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    res = db_query("SELECT value FROM settings WHERE key='vip_status'", fetchone=True)
    current = res[0] if res else 'OFF'
    new_status = 'ON' if current == 'OFF' else 'OFF'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('vip_status', ?)", (new_status,))
    await call.message.edit_reply_markup(reply_markup=admin_kb())

@dp.callback_query(F.data == "admin_user_control_start")
async def admin_user_control_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Download Full User List", callback_data="admin_download_userlist", style="success")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("💻 <b>User Control Terminal</b>\n\n✏️ Enter the <b>User ID</b> or <b>@Username</b> you want to investigate or manage:\n\n👇 <b>OR</b> download the full user CSV format list:", reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.manage_target_user)

@dp.callback_query(F.data == "admin_download_userlist")
async def admin_download_userlist(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    users = db_query("SELECT username, user_id, phone, balance, orders_count, is_vip, is_reseller FROM users", fetchall=True)
    if not users: return await call.answer("❌ No users found in the database.", show_alert=True)
    file_content = "FULL DATABASE DUMP\n" + "="*100 + "\n"
    for u in users:
        uname = u[0] if u[0] else "No_Username"
        uid = u[1]
        phone = u[2] if u[2] else "No_Phone"
        bal = u[3]
        orders = u[4]
        vip_status = "YES" if u[5] else "NO"
        res_status = "YES" if u[6] else "NO"
        file_content += f"UID: {uid} | UNAME: {uname} | PHONE: {phone} | BAL: ₹{bal:.2f} | BUY: {orders} | VIP: {vip_status} | RES: {res_status}\n"
    doc = BufferedInputFile(file_content.encode('utf-8'), filename=f"DB_{datetime.now().strftime('%Y%m%d')}.txt")
    await call.message.answer_document(document=doc, caption="📋 <b>Database export complete.</b>", parse_mode='HTML')
    await call.answer()

@dp.message(AdminStates.manage_target_user)
async def process_user_lookup(m: Message, state: FSMContext):
    target = m.text.strip()
    if target.startswith('@'): target = target[1:]
    loader_msg = await hacker_loading(m, "Querying User Database")
    user_q = db_query("SELECT user_id, first_name, username, balance, is_reseller, orders_count, spent, joined_date, is_banned, warnings, is_vip FROM users WHERE user_id=? OR username=? COLLATE NOCASE", (target, target), fetchone=True)
    if not user_q: return await loader_msg.edit_text("❌ Target not found in the grid. Check ID/Username syntax.", reply_markup=admin_back_kb(), parse_mode='HTML')
    u_id, u_name, u_user, bal, is_res, orders, spent, joined, is_banned, warnings, is_vip = user_q
    await state.update_data(target_u_id=u_id)
    status_emoji = "🔴 BANNED" if is_banned else "🟢 ACTIVE"
    tags = []
    if is_res: tags.append("👑 Reseller")
    if is_vip: tags.append("🌟 VIP")
    type_str = " | ".join(tags) if tags else "👤 Regular"
    text = (f"🛡 <b><u>USER CONTROL TERMINAL</u></b> 🛡\n━━━━━━━━━━━━━━━━━━\n📛 <b>Name:</b> {u_name} (@{u_user})\n🆔 <b>ID:</b> <code>{u_id}</code>\n📊 <b>Status:</b> {status_emoji}\n🔰 <b>Type:</b> {type_str}\n⚠️ <b>Warnings Issued:</b> {warnings}\n━━━━━━━━━━━━━━━━━━\n💰 <b>Wallet Balance:</b> {fmt_curr(bal)}\n📦 <b>Orders:</b> {orders} | 💸 <b>Total Spent:</b> {fmt_curr(spent)}\n📅 <b>Joined:</b> {joined}")
    ban_btn_text = "Unban ✅" if is_banned else "Ban 🚫"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Add Funds ➕", callback_data=f"usrctrl_add_{u_id}", style="success"), InlineKeyboardButton(text="Minus Funds ➖", callback_data=f"usrctrl_min_{u_id}", style="danger")],
        [InlineKeyboardButton(text=ban_btn_text, callback_data=f"usrctrl_ban_{u_id}", style="danger"), InlineKeyboardButton(text="Warn User ⚠️", callback_data=f"usrctrl_warn_{u_id}", style="danger")],
        [InlineKeyboardButton(text="Give VIP 🌟" if not is_vip else "Remove VIP 🚫", callback_data=f"usrctrl_vip_{u_id}", style="success")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await loader_msg.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("usrctrl_"))
async def handle_user_actions(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    action = call.data.split("_")[1]
    u_id = int(call.data.split("_")[2])
    await state.update_data(target_u_id=u_id)
    if action == "ban":
        current_status = db_query("SELECT is_banned FROM users WHERE user_id=?", (u_id,), fetchone=True)[0]
        if current_status == 0:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Yes, Ban", callback_data=f"confirm_ban_{u_id}", style="danger"), InlineKeyboardButton(text="❌ Cancel", callback_data="admin_user_control_start", style="danger")]
            ])
            await call.message.edit_text(f"⚠️ Are you sure you want to <b>BAN</b> user <code>{u_id}</code>?", reply_markup=kb, parse_mode='HTML')
            await state.set_state(AdminStates.confirm_ban)
        else:
            db_query("UPDATE users SET is_banned=0 WHERE user_id=?", (u_id,))
            await call.answer("✅ User unbanned successfully!", show_alert=True)
            m = call.message; m.text = str(u_id); await process_user_lookup(m, state)
    elif action == "vip":
        current_status = db_query("SELECT is_vip FROM users WHERE user_id=?", (u_id,), fetchone=True)[0]
        if current_status == 1:
            db_query("UPDATE users SET is_vip=0 WHERE user_id=?", (u_id,))
            await call.answer("✅ VIP Removed!", show_alert=True)
        else:
            db_query("UPDATE users SET is_vip=1, vip_since=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d"), u_id))
            await call.answer("✅ VIP Granted!", show_alert=True)
        m = call.message; m.text = str(u_id); await process_user_lookup(m, state)
    elif action == "add":
        await call.message.edit_text("💰 Enter the amount to <b>ADD</b> to this user's wallet:", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_add_money)
    elif action == "min":
        await call.message.edit_text("💸 Enter the amount to <b>DEDUCT</b> from this user's wallet:", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_minus_money)
    elif action == "warn":
        await call.message.edit_text("⚠️ Type the strict warning message you want to send directly to this user:", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_warning)

@dp.callback_query(F.data.startswith("confirm_ban_"))
async def confirm_ban(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    u_id = int(call.data.split("_")[2])
    db_query("UPDATE users SET is_banned=1 WHERE user_id=?", (u_id,))
    await call.answer("🔴 User has been banned!", show_alert=True)
    await state.clear()
    m = call.message; m.text = str(u_id); await process_user_lookup(m, state)

@dp.message(AdminStates.wait_for_add_money)
async def exec_add_money(m: Message, state: FSMContext):
    try:
        amt = float(m.text)
        data = await state.get_data()
        u_id = data['target_u_id']
        db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, u_id))
        await m.answer(f"✅ Successfully added {fmt_curr(amt)} to target <code>{u_id}</code>.", reply_markup=admin_kb(), parse_mode='HTML')
        try: await bot.send_message(u_id, f"💰 <b>Wallet Top-up!</b>\nAdmin has manually added {fmt_curr(amt)} to your wallet.", parse_mode='HTML')
        except: pass
        await state.clear()
    except ValueError: await m.answer("❌ Critical Error: Input must be a valid number.")

@dp.message(AdminStates.wait_for_minus_money)
async def exec_minus_money(m: Message, state: FSMContext):
    try:
        amt = float(m.text)
        data = await state.get_data()
        u_id = data['target_u_id']
        db_query("UPDATE users SET balance = balance - ? WHERE user_id=?", (amt, u_id))
        await m.answer(f"✅ Successfully deducted {fmt_curr(amt)} from target <code>{u_id}</code>.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Critical Error: Input must be a valid number.")

@dp.message(AdminStates.wait_for_warning)
async def exec_warn_user(m: Message, state: FSMContext):
    data = await state.get_data()
    u_id = data['target_u_id']
    warn_text = m.text
    db_query("UPDATE users SET warnings = warnings + 1 WHERE user_id=?", (u_id,))
    await m.answer(f"✅ Official warning dispatched to <code>{u_id}</code>.", reply_markup=admin_kb(), parse_mode='HTML')
    try: await bot.send_message(u_id, f"⚠️ <b>OFFICIAL WARNING FROM SYSTEM ADMIN:</b>\n\n{warn_text}\n\n<i>Subsequent infractions may lead to an automated grid ban.</i>", parse_mode='HTML')
    except: pass
    await state.clear()

# ==============================================================================
# 18. ADMIN STATISTICS
# ==============================================================================
@dp.callback_query(F.data == "admin_view_stats")
async def admin_dashboard_stats(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    t_users = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
    t_resellers = db_query("SELECT COUNT(*) FROM users WHERE is_reseller=1", fetchone=True)[0]
    t_vip = db_query("SELECT COUNT(*) FROM users WHERE is_vip=1", fetchone=True)[0]
    t_prods = db_query("SELECT COUNT(*) FROM products", fetchone=True)[0]
    t_keys = db_query("SELECT COUNT(*) FROM product_keys WHERE is_used=0", fetchone=True)[0]
    t_rev = db_query("SELECT SUM(spent) FROM users", fetchone=True)[0] or 0.0
    today_str = datetime.now().strftime("%Y-%m-%d")
    t_spins = db_query("SELECT COUNT(*) FROM users WHERE last_spin LIKE ?", (f"{today_str}%",), fetchone=True)[0]
    msg = (f"📊 <b><u>GRID INTELLIGENCE DASHBOARD</u></b> 📊\n━━━━━━━━━━━━━━━━━━\n👥 <b>Total Grid Users:</b> {t_users}\n👑 <b>Wholesale Resellers:</b> {t_resellers}\n🌟 <b>Elite VIP Members:</b> {t_vip}\n━━━━━━━━━━━━━━━━━━\n📦 <b>Active Products:</b> {t_prods}\n🔑 <b>Unused Keys in Vault:</b> {t_keys}\n💰 <b>Total Gross Revenue:</b> {fmt_curr(t_rev)}\n🎰 <b>Ludo Spins Today:</b> {t_spins}\n━━━━━━━━━━━━━━━━━━")
    await call.message.edit_text(msg, reply_markup=admin_back_kb(), parse_mode='HTML')

# Payment-proof group configuration. Admin can send a group/channel chat ID or @username.
@dp.callback_query(F.data == "admin_set_payment_proof_group")
async def admin_set_payment_proof_group(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Not authorized", show_alert=True)
    current = get_setting("payment_proof_group_id", "")
    await call.message.edit_text(
        "<b>🧾 Set Payment Proof Group</b>\n\nSend the target group's numeric chat ID (usually starts with -100) or its public @username.\n"
        f"Current: <code>{html.escape(current) if current else 'Not set'}</code>\n\n"
        "Add the bot to that group and give it permission to send messages. Send <code>off</code> to disable.",
        reply_markup=admin_back_kb(), parse_mode="HTML")
    await state.set_state(AdminStates.wait_for_payment_proof_group)

@dp.callback_query(F.data == "admin_test_payment_proof_group")
async def admin_test_payment_proof_group(call: CallbackQuery):
    """Send a clearly marked test receipt to the configured proof group."""
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Not authorized", show_alert=True)
    target = (get_setting("payment_proof_group_id", "") or "").strip()
    if not target:
        return await call.answer("Set Payment Proof Group first.", show_alert=True)
    # Use the same feedback layout as real purchases; keep test data clearly fictional.
    test_text = (
        '┌ 🔔 <b>User Buy Feedback</b>\n'
        '│\n'
        '├ 👤 <b>Name:</b> TEST BUYER\n'
        '├ 🆔 <b>User ID:</b> •••***•••\n'
        '├ ⚙️ <b>Action:</b> Purchased: TEST PRODUCT (TEST PLAN) [Price: ₹0.00]\n'
        '├ 🔑 <b>Key Delivered:</b> <code>TEST — NO KEY</code>\n'
        f'├ 📅 <b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
        '└───────────────────'
    )
    bot_username = str(BOT_USERNAME).lstrip('@')
    test_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='🛍 OPEN SHOP & BUY NOW', url=f'https://t.me/{bot_username}?start=shop', style='success')
    ]])
    try:
        await bot.send_message(chat_id=target, text=test_text, reply_markup=test_kb, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as exc:
        logger.exception("Payment proof test message failed")
        return await call.answer("Test failed. Check group ID and bot permissions.", show_alert=True)
    await call.answer("Test proof sent to the group.", show_alert=True)
    try:
        await call.message.answer("✅ Test proof sent. Check the configured Payment Proof Group.", reply_markup=admin_kb())
    except Exception:
        pass

@dp.message(AdminStates.wait_for_payment_proof_group)
async def save_payment_proof_group(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    value = (message.text or "").strip()
    if value.lower() == "off":
        set_setting("payment_proof_group_id", "")
        await state.clear()
        return await message.answer("✅ Payment proof group disabled.", reply_markup=admin_kb())
    if not (value.startswith("@") and len(value) > 1) and not (value.lstrip("-").isdigit()):
        return await message.answer("❌ Send a numeric chat ID (e.g. -1001234567890) or public @username, or send off.")
    set_setting("payment_proof_group_id", value)
    await state.clear()
    await message.answer("✅ Payment proof group saved. Make sure the bot is a member and can send messages.", reply_markup=admin_kb())

async def send_purchase_proof_group(user, result: dict, mode: str = "MANUAL"):
    """Send the requested masked purchase feedback and a deep-link button to the shop."""
    target = (get_setting("payment_proof_group_id", "") or "").strip()
    if not target:
        return
    try:
        prod = result.get('prod') or ()
        product = str(result.get('product_full_name') or (prod[0] if len(prod) else 'Product'))
        plan = str(prod[8] if len(prod) > 8 else (prod[0] if len(prod) else 'Plan'))
        amount = fmt_curr(result.get('total', 0))
        user_id = str(user.id)
        full_name = html.escape(str(getattr(user, 'full_name', None) or 'User'))
        def mask_id(v):
            v = str(v or '')
            return (v[:3] + '***' + v[-3:]) if len(v) > 6 else '***'
        key = str(result.get('delivered_key') or '')
        masked_key = (key[:4] + '********' + key[-3:]) if len(key) > 9 else '********'
        proof = (
            '┌ 🔔 <b>User Buy Feedback</b>\n'
            '│\n'
            f'├ 👤 <b>Name:</b> {full_name}\n'
            f'├ 🆔 <b>User ID:</b> {html.escape(mask_id(user_id))}\n'
            f'├ ⚙️ <b>Action:</b> Purchased: {html.escape(product)} ({html.escape(plan)}) [Price: {html.escape(amount)}]\n'
            f'├ 🔑 <b>Key Delivered:</b> <code>{html.escape(masked_key)}</code>\n'
            f'├ 📅 <b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            '└───────────────────'
        )
        product_id = result.get('product_id')
        if product_id:
            start_arg = f'product_{int(product_id)}'
        else:
            start_arg = 'shop'
        bot_username = str(BOT_USERNAME).lstrip('@')
        shop_url = f'https://t.me/{bot_username}?start={start_arg}'
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='🛍 OPEN SHOP & BUY NOW', url=shop_url, style='success')
        ]])
        await bot.send_message(chat_id=target, text=proof, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        logger.exception("Could not send purchase proof to configured group")

# ==============================================================================
# ADMIN CATEGORY MANAGEMENT (Add / edit emoji / delete)
# ==============================================================================
@dp.callback_query(F.data == "admin_add_category")
async def admin_add_category_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await state.clear()
    await call.message.edit_text("📂 <b>ADD CATEGORY</b>\n\nSend the category name, e.g. <code>ANDROID EMULATOR PANEL</code>.", reply_markup=admin_back_kb(), parse_mode="HTML")
    await state.set_state(AdminStates.add_category_name)

@dp.message(AdminStates.add_category_name)
async def admin_add_category_name(m: Message, state: FSMContext):
    name = " ".join((m.text or "").strip().split()).upper()
    if not name or len(name) > 64:
        return await m.answer("❌ Send a category name (1–64 characters).")
    existing = db_query("SELECT id FROM store_categories WHERE LOWER(name)=LOWER(?)", (name,), fetchone=True)
    if existing:
        return await m.answer("❌ This category already exists. Send another name.")
    await state.update_data(new_category_name=name)
    await m.answer("🎨 Send the category Custom Emoji ID (numeric), or send <code>0</code> for default.", parse_mode="HTML")
    await state.set_state(AdminStates.add_category_emoji)

@dp.message(AdminStates.add_category_emoji)
async def admin_add_category_emoji(m: Message, state: FSMContext):
    emoji = (m.text or "").strip()
    if emoji != "0" and (not emoji.isdigit() or not (5 <= len(emoji) <= 25)):
        return await m.answer("❌ Send a numeric emoji ID (5–25 digits), or 0.")
    data = await state.get_data(); name = data.get("new_category_name", "")
    try:
        db_query("INSERT INTO store_categories (name, emoji_id) VALUES (?, ?)", (name, "" if emoji == "0" else emoji))
    except Exception:
        return await m.answer("❌ Category could not be saved. It may already exist.")
    await state.clear()
    await m.answer(f"✅ <b>Category added:</b> {html.escape(name)}", reply_markup=admin_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_manage_categories")
async def admin_manage_categories(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    rows = db_query("SELECT id, name, emoji_id FROM store_categories ORDER BY id", fetchall=True) or []
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cid, name, emoji in rows:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{name} · EDIT EMOJI", callback_data=f"category_emoji_{cid}", style="primary")])
        if name not in FIXED_CATEGORIES:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"🗑 Delete {name}", callback_data=f"category_delete_{cid}", style="danger")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="BACK", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("🗂 <b>MANAGE CATEGORIES</b>\nSelect a category to edit its emoji or delete a custom category.", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("category_emoji_"))
async def admin_edit_category_emoji_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    try: cid = int(call.data.rsplit("_", 1)[1])
    except ValueError: return await call.answer("Invalid category.", show_alert=True)
    row = db_query("SELECT name FROM store_categories WHERE id=?", (cid,), fetchone=True)
    if not row: return await call.answer("Category not found.", show_alert=True)
    await state.clear(); await state.update_data(edit_category_id=cid)
    await call.message.edit_text(f"🎨 <b>EDIT CATEGORY EMOJI</b>\nCategory: <b>{html.escape(row[0])}</b>\n\nSend numeric emoji ID or <code>0</code> for default.", reply_markup=admin_back_kb(), parse_mode="HTML")
    await state.set_state(AdminStates.wait_for_category_emoji)

@dp.message(AdminStates.wait_for_category_emoji)
async def admin_edit_category_emoji_save(m: Message, state: FSMContext):
    emoji = (m.text or "").strip()
    if emoji != "0" and (not emoji.isdigit() or not (5 <= len(emoji) <= 25)):
        return await m.answer("❌ Send a numeric emoji ID or 0.")
    data = await state.get_data()
    db_query("UPDATE store_categories SET emoji_id=? WHERE id=?", ("" if emoji == "0" else emoji, data.get("edit_category_id")))
    await state.clear(); await m.answer("✅ Category emoji updated.", reply_markup=admin_kb())

@dp.callback_query(F.data.startswith("category_delete_"))
async def admin_delete_category(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    try: cid = int(call.data.rsplit("_", 1)[1])
    except ValueError: return await call.answer("Invalid category.", show_alert=True)
    row = db_query("SELECT name FROM store_categories WHERE id=?", (cid,), fetchone=True)
    if not row: return await call.answer("Category not found.", show_alert=True)
    if row[0] in FIXED_CATEGORIES: return await call.answer("Built-in categories cannot be deleted.", show_alert=True)
    count = db_query("SELECT COUNT(*) FROM products WHERE category=?", (row[0],), fetchone=True)[0]
    if count: return await call.answer("This category contains products. Move/delete those products first.", show_alert=True)
    db_query("DELETE FROM store_categories WHERE id=?", (cid,))
    await call.answer("Category deleted.", show_alert=True)
    await admin_manage_categories(call)

# ==============================================================================
# 19. ADMIN PRODUCT MANAGEMENT
# ==============================================================================
@dp.callback_query(F.data == "admin_add_prod")
async def add_prod_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await state.clear()
    await call.message.edit_text(
        "➕ <b>ADD PRODUCT</b>\n\nSend ONE product name.\n"
        "Each product has its own custom emoji and its own plans, so add products one at a time.\n"
        "Example: <code>ZREX NON ROOT</code>\n\nDefault category: Android Non Root Panel.",
        reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.bulk_product_names)

@dp.message(AdminStates.bulk_product_names)
async def bulk_product_names(m: Message, state: FSMContext):
    name = (m.text or '').strip()
    if not name: return await m.answer('❌ Send one product name.')
    if '\n' in name: return await m.answer('❌ Add one product at a time so each product can have its own emoji and plans.')
    await state.update_data(bulk_product_names=[name])
    rows = db_query("SELECT name FROM store_categories ORDER BY id", fetchall=True) or []
    names = list(dict.fromkeys([str(r[0]) for r in rows] + list(FIXED_CATEGORIES)))
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in names:
        slug = base64.urlsafe_b64encode(cat.encode()).decode().rstrip('=')
        kb.inline_keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"addprodcat_{slug}", style="primary")])
    await m.answer('📂 <b>Choose the category for this product:</b>', reply_markup=kb, parse_mode='HTML')
    await state.set_state(AdminStates.add_product_category)

@dp.callback_query(F.data.startswith("addprodcat_"))
async def choose_add_product_category(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        raw = call.data.split("addprodcat_", 1)[1]
        raw += "=" * (-len(raw) % 4)
        category = base64.urlsafe_b64decode(raw.encode()).decode()
    except Exception:
        return await call.answer("Invalid category.", show_alert=True)
    await state.update_data(bulk_product_category=category)
    await call.answer()
    await call.message.edit_text('🎨 Send this product’s Custom Emoji ID (numeric Telegram custom emoji ID).\nIf you do not have one, send <code>0</code>.', parse_mode='HTML')
    await state.set_state(AdminStates.bulk_product_emoji)

@dp.message(AdminStates.bulk_product_emoji)
async def bulk_product_emoji(m: Message, state: FSMContext):
    emoji_id=(m.text or '').strip()
    if emoji_id != '0' and not emoji_id.isdigit(): return await m.answer('❌ Emoji ID must be numeric, or send 0.')
    await state.update_data(bulk_product_emoji='' if emoji_id=='0' else emoji_id)
    await m.answer('🧾 Send this product’s plans, one plan per line, in this exact format:\n<code>1 DAYS | PID=1 | USER=60 | RESELLER=45\n3 DAYS | PID=2 | USER=120 | RESELLER=90\n7 DAYS | PID=3 | USER=200 | RESELLER=160</code>\n\nEach line: Plan Name | PID=number | USER=price | RESELLER=price. Only these plans will belong to this product.', parse_mode='HTML')
    await state.set_state(AdminStates.bulk_product_plans)

@dp.message(AdminStates.bulk_product_plans)
async def bulk_product_plans(m: Message, state: FSMContext):
    import re
    lines=[x.strip() for x in (m.text or '').splitlines() if x.strip()]
    plans=[]
    for line in lines:
        parts=[x.strip() for x in line.split('|')]
        if len(parts)!=4:
            return await m.answer(f'❌ Invalid plan line:\n<code>{html.escape(line)}</code>\nUse: Plan Name | PID=1 | USER=40 | RESELLER=30', parse_mode='HTML')
        name=parts[0]
        vals={}
        for part in parts[1:]:
            if '=' not in part: return await m.answer(f'❌ Invalid field: {html.escape(part)}', parse_mode='HTML')
            k,v=part.split('=',1); vals[k.strip().upper()]=v.strip()
        try:
            pid=int(vals['PID']); user_price=float(vals['USER']); reseller_price=float(vals['RESELLER'])
            if pid<1 or user_price<0 or reseller_price<0: raise ValueError()
        except Exception:
            return await m.answer(f'❌ PID and prices must be valid numbers in line: {html.escape(line)}', parse_mode='HTML')
        plans.append((name,pid,user_price,reseller_price))
    if not plans: return await m.answer('❌ Send at least one plan.')
    data=await state.get_data(); names=data.get('bulk_product_names',[]); emoji=data.get('bulk_product_emoji','')
    conn=sqlite3.connect('yp_shop.db')
    try:
        cur=conn.cursor(); created=[]
        for product_name in names:
            for plan_name,pid,user_price,reseller_price in plans:
                cur.execute("INSERT INTO products (category,panel_name,name,price_inr,reseller_price,stock,apk_link,validity,device_limit,is_active,is_maintenance,api_pid,custom_emoji_id) VALUES (?,?,?,?,?,?,?,?,?,1,0,?,?)",
                    (data.get('bulk_product_category', 'ANDROID NON ROOT PANEL'),product_name,plan_name,user_price,reseller_price,999999,'',plan_name,'1 Device',pid,emoji))
                created.append((product_name,plan_name,pid))
        conn.commit()
    except Exception:
        conn.rollback(); logger.exception('Bulk product creation failed')
        return await m.answer('❌ Products could not be saved. Please check the format and retry.')
    finally: conn.close()
    summary='\n'.join(f'• {html.escape(n)} → {html.escape(pl)} (PID {pid})' for n,pl,pid in created[:25])
    if len(created)>25: summary+=f'\n…and {len(created)-25} more plan entries.'
    await m.answer(f'✅ <b>Products and plans saved.</b>\nProducts: {len(names)}\nPlans per product: {len(plans)}\nTotal plan entries: {len(created)}\n\n{summary}\n\n⚠️ API purchase fulfillment must be tested before accepting live orders.', reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_manage_prods")
async def admin_manage_prods(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    products = db_query(
        "SELECT category, panel_name, COUNT(*), MAX(is_maintenance), MIN(is_active) "
        "FROM products GROUP BY category, panel_name ORDER BY category, panel_name",
        fetchall=True,
    ) or []
    categories = db_query("SELECT id, name, emoji_id FROM store_categories ORDER BY id", fetchall=True) or []
    product_count = db_query("SELECT COUNT(DISTINCT category || '::' || panel_name) FROM products", fetchone=True)
    category_count = db_query("SELECT COUNT(*) FROM store_categories", fetchone=True)
    total_products = int(product_count[0] or 0) if product_count else 0
    total_categories = int(category_count[0] or 0) if category_count else 0

    # Telegram custom emoji are supported in message text via tg-emoji HTML tags.
    title = (
        '<tg-emoji emoji-id="6087162775304409688">🧩</tg-emoji> '
        '<b>PRODUCT &amp; CATEGORY EDITOR</b> '
        '<tg-emoji emoji-id="6086730808968614780">❞</tg-emoji>\n\n'
        '<tg-emoji emoji-id="5422439311196834318">💡</tg-emoji> '
        'Manage all available hacks, APKs and products from here '
        '<tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji>\n\n'
        f'<tg-emoji emoji-id="5449449325434266744">🌀</tg-emoji> <b>Total Products:</b> {total_products}\n'
        f'<tg-emoji emoji-id="5271604874419647061">🔗</tg-emoji> <b>Total Categories:</b> {total_categories}\n\n'
        '<i>Select a product or category below to edit its configuration.</i>'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for category, panel_name, plan_count, maintenance, active in products:
        cat = str(category or 'Uncategorized')
        name = str(panel_name or 'Unnamed Product')
        state_icon = '🛠️' if maintenance else ('🟢' if active else '🔴')
        first_id = (db_query(
            "SELECT MIN(id) FROM products WHERE category=? AND panel_name=?", (cat, name), fetchone=True
        ) or [0])[0]
        kb.inline_keyboard.append([InlineKeyboardButton(
            text=f'{state_icon} {name} · {int(plan_count or 0)} PLAN(S)',
            callback_data=f'admin_view_p_{first_id}', style='primary'
        )])
    # Keep the add actions directly in this manager, as requested.
    kb.inline_keyboard.append([
        InlineKeyboardButton(text='➕ Add Product', callback_data='admin_add_prod', style='success'),
        InlineKeyboardButton(text='➕ Add Category', callback_data='admin_add_category', style='success')
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(
        text='🗂 Manage Categories', callback_data='admin_manage_categories', style='primary'
    )])
    for cid, name, emoji_id in categories:
        enabled = get_setting(f'category_enabled_{cid}', 'ON') != 'OFF'
        status = '🟢' if enabled else '🔴'
        kb.inline_keyboard.append([InlineKeyboardButton(
            text=f'{status} {name} · CATEGORY SWITCH',
            callback_data=f'admin_category_switch_{cid}',
            style='success' if enabled else 'danger'
        )])
    mode = get_setting('fulfillment_mode', 'MANUAL').upper()
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=('🔌 API MODE ✓' if mode == 'API' else '🔌 API MODE'), callback_data='admin_fulfillment_api', style='primary'),
        InlineKeyboardButton(text=('🖐 MANUAL MODE ✓' if mode != 'API' else '🖐 MANUAL MODE'), callback_data='admin_fulfillment_manual', style='primary')
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(
        text='🔙 Back', callback_data='admin_panel_back', icon_custom_emoji_id=get_emoji_icon('back'), style='danger'
    )])
    await call.message.edit_text(title, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith('admin_category_switch_'))
async def admin_category_switch(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    try: cid = int(call.data.rsplit('_', 1)[1])
    except ValueError: return await call.answer('Invalid category.', show_alert=True)
    row = db_query('SELECT name FROM store_categories WHERE id=?', (cid,), fetchone=True)
    if not row: return await call.answer('Category not found.', show_alert=True)
    key = f'category_enabled_{cid}'
    enabled = get_setting(key, 'ON') != 'OFF'
    set_setting(key, 'OFF' if enabled else 'ON')
    await call.answer(f"{row[0]} {'disabled' if enabled else 'enabled'}")
    await admin_manage_prods(call)

@dp.callback_query(F.data == 'admin_fulfillment_api')
async def admin_fulfillment_api(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    set_setting('fulfillment_mode', 'API')
    await call.answer('API mode selected. Verify API credentials and each plan PID before live sales.', show_alert=True)
    await admin_manage_prods(call)

@dp.callback_query(F.data == 'admin_fulfillment_manual')
async def admin_fulfillment_manual(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    set_setting('fulfillment_mode', 'MANUAL')
    await call.answer('Manual mode selected.', show_alert=True)
    await admin_manage_prods(call)

@dp.callback_query(F.data.startswith("admin_view_p_"))
async def admin_view_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        p_id = int(call.data.rsplit('_', 1)[1])
    except ValueError:
        return await call.answer('Invalid product.', show_alert=True)
    prod = db_query("SELECT * FROM products WHERE id=?", (p_id,), fetchone=True)
    if not prod:
        return await call.answer("Product not found.", show_alert=True)
    category, panel_name = str(prod[1] or ''), str(prod[2] or '')
    siblings = db_query(
        "SELECT id, name, price_inr, reseller_price, api_pid, is_active, is_maintenance "
        "FROM products WHERE category=? AND panel_name=? ORDER BY id", (category, panel_name), fetchall=True
    ) or []
    title = (
        '<tg-emoji emoji-id="6087162775304409688">🧩</tg-emoji> <b>PRODUCT MANAGER</b>\n\n'
        f'<b>Product:</b> {html.escape(panel_name)}\n'
        f'<b>Category:</b> {html.escape(category)}\n'
        f'<b>Total Plans:</b> {len(siblings)}\n\n'
        '<i>Tap a plan to open Plan Manager:</i>'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for row in siblings:
        plan_id, plan_name, price, reseller, pid, active, maintenance = row
        status = '🛠️' if maintenance else ('🟢' if active else '🔴')
        kb.inline_keyboard.append([InlineKeyboardButton(
            text=f'{status} {plan_name} · {fmt_curr(safe_float(price))} · PID {pid or 0}',
            callback_data=f'admin_plan_{plan_id}', style='primary'
        )])
    mode = get_setting('fulfillment_mode', 'MANUAL').upper()
    kb.inline_keyboard.extend([
        [InlineKeyboardButton(text=('🔌 API MODE ✓' if mode == 'API' else '🔌 API MODE'), callback_data='admin_fulfillment_api', style='primary'),
         InlineKeyboardButton(text=('🖐 MANUAL MODE ✓' if mode != 'API' else '🖐 MANUAL MODE'), callback_data='admin_fulfillment_manual', style='primary')],
        [InlineKeyboardButton(text='➕ ADD PLAN', callback_data=f'add_plan_product_{p_id}', style='success'),
         InlineKeyboardButton(text='✏️ RENAME PRODUCT', callback_data=f'rename_product_{p_id}', style='primary')],
        [InlineKeyboardButton(text='🎨 CHANGE EMOJI ID', callback_data=f'edit_product_emoji_{p_id}', style='primary'),
         InlineKeyboardButton(text=('🟢 Maintenance OFF' if prod[11] else '🛠️ Maintenance ON'), callback_data=f'maintenance_p_{p_id}', style='primary')],
        [InlineKeyboardButton(text='🗑 DELETE PRODUCT', callback_data=f'confirm_delete_p_{p_id}', style='danger')],
        [InlineKeyboardButton(text='🔙 BACK', callback_data='admin_manage_prods', icon_custom_emoji_id=get_emoji_icon('back'), style='danger')]
    ])
    await call.message.edit_text(title, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith('rename_product_'))
async def rename_product_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        p_id = int(call.data.rsplit('_', 1)[1])
    except ValueError:
        return await call.answer('Invalid product.', show_alert=True)
    row = db_query('SELECT category, panel_name FROM products WHERE id=?', (p_id,), fetchone=True)
    if not row:
        return await call.answer('Product not found.', show_alert=True)
    await state.clear()
    await state.update_data(rename_product_id=p_id, rename_product_category=row[0], rename_product_old=row[1])
    await call.message.edit_text(
        f'<b>RENAME PRODUCT</b>\nCurrent name: <code>{html.escape(str(row[1]))}</code>\n\n'
        'Send the new product name. All plans belonging to this product will be renamed together.',
        reply_markup=admin_back_kb(), parse_mode='HTML'
    )
    await state.set_state(AdminStates.wait_for_new_value)
    await state.update_data(edit_field='product_name', edit_p_id=p_id)

@dp.callback_query(F.data.startswith('confirm_delete_p_'))
async def confirm_delete_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        p_id = int(call.data.rsplit('_', 1)[1])
    except ValueError:
        return await call.answer('Invalid product.', show_alert=True)
    row = db_query('SELECT category, panel_name FROM products WHERE id=?', (p_id,), fetchone=True)
    if not row:
        return await call.answer('Product not found.', show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ YES, DELETE PRODUCT + ALL PLANS', callback_data=f'delete_p_{p_id}', style='danger')],
        [InlineKeyboardButton(text='❌ CANCEL', callback_data=f'admin_view_p_{p_id}', style='primary')]
    ])
    await call.message.edit_text(
        f'⚠️ <b>CONFIRM PRODUCT DELETION</b>\n\nProduct: <b>{html.escape(str(row[1]))}</b>\n'
        f'Category: {html.escape(str(row[0]))}\n\n'
        'This permanently deletes every plan and its keys belonging to this product. Continue?',
        reply_markup=kb, parse_mode='HTML'
    )

@dp.callback_query(F.data.startswith('admin_plan_'))
async def admin_plan_manager(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        p_id = int(call.data.rsplit('_', 1)[1])
    except ValueError:
        return await call.answer('Invalid plan.', show_alert=True)
    row = db_query(
        'SELECT id, category, panel_name, name, price_inr, reseller_price, api_pid, stock, is_active, is_maintenance '
        'FROM products WHERE id=?', (p_id,), fetchone=True
    )
    if not row:
        return await call.answer('Plan not found.', show_alert=True)
    pid, category, product_name, plan_name, user_price, reseller_price, api_pid, stock, active, maintenance = row
    title = (
        '<b>PLAN MANAGER</b>\n\n'
        f'<b>Product:</b> {html.escape(str(product_name))}\n'
        f'<b>Plan:</b> {html.escape(str(plan_name))}\n'
        f'<b>User Price:</b> {fmt_curr(safe_float(user_price))}\n'
        f'<b>Reseller Price:</b> {fmt_curr(safe_float(reseller_price))}\n'
        f'<b>API PID:</b> <code>{api_pid or 0}</code>\n'
        f'<b>Stock:</b> {stock}\n'
        f'<b>Visibility:</b> {"Visible" if active else "Hidden"}\n'
        f'<b>Maintenance:</b> {"ON" if maintenance else "OFF"}'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💰 USER PRICE', callback_data=f'edit_p_{pid}_price', style='primary'), InlineKeyboardButton(text='👑 RESELLER PRICE', callback_data=f'edit_p_{pid}_rprice', style='primary')],
        [InlineKeyboardButton(text='🔌 EDIT PID', callback_data=f'edit_p_{pid}_pid', style='primary'), InlineKeyboardButton(text='✏️ RENAME PLAN', callback_data=f'edit_p_{pid}_name', style='primary')],
        [InlineKeyboardButton(text=('👁 UNHIDE PLAN' if not active else '🙈 HIDE PLAN'), callback_data=f'toggle_p_{pid}', style='primary'), InlineKeyboardButton(text=('🟢 MAINTENANCE OFF' if maintenance else '🛠️ MAINTENANCE ON'), callback_data=f'maintenance_p_{pid}', style='primary')],
        [InlineKeyboardButton(text='🔑 ADD KEYS', callback_data=f'edit_p_{pid}_keys', style='success'), InlineKeyboardButton(text='🗑 DELETE PLAN', callback_data=f'confirm_delete_plan_{pid}', style='danger')],
        [InlineKeyboardButton(text='🔙 BACK TO PRODUCT', callback_data=f'admin_view_p_{pid}', style='danger')]
    ])
    await call.message.edit_text(title, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith('confirm_delete_plan_'))
async def confirm_delete_plan(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        p_id = int(call.data.rsplit('_', 1)[1])
    except ValueError:
        return await call.answer('Invalid plan.', show_alert=True)
    row = db_query('SELECT name FROM products WHERE id=?', (p_id,), fetchone=True)
    if not row:
        return await call.answer('Plan not found.', show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='✅ DELETE PLAN', callback_data=f'delete_plan_{p_id}', style='danger'),
        InlineKeyboardButton(text='❌ CANCEL', callback_data=f'admin_plan_{p_id}', style='primary')
    ]])
    await call.message.edit_text(
        f'Confirm deleting plan <b>{html.escape(str(row[0]))}</b>? This also deletes its keys.',
        reply_markup=kb, parse_mode='HTML'
    )

@dp.callback_query(F.data.startswith('delete_plan_'))
async def delete_plan(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        p_id = int(call.data.rsplit('_', 1)[1])
    except ValueError:
        return await call.answer('Invalid plan.', show_alert=True)
    db_query('DELETE FROM product_keys WHERE product_id=?', (p_id,))
    db_query('DELETE FROM products WHERE id=?', (p_id,))
    await call.answer('Plan and its keys deleted.', show_alert=True)
    await admin_manage_prods(call)

@dp.callback_query(F.data.startswith("edit_product_emoji_"))
async def edit_product_emoji_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        product_id = int(call.data.rsplit("_", 1)[1])
    except (ValueError, IndexError):
        return await call.answer("Invalid product.", show_alert=True)
    prod = db_query("SELECT category, panel_name FROM products WHERE id=?", (product_id,), fetchone=True)
    if not prod:
        return await call.answer("Product not found.", show_alert=True)
    await state.update_data(product_emoji_category=prod[0], product_emoji_panel=prod[1], product_emoji_id=product_id)
    await call.message.edit_text(
        "🎨 <b>EDIT PRODUCT EMOJI</b>\n\nSend the numeric Telegram custom emoji ID.\n"
        "Send <code>0</code> to use the default emoji.\n\nExample: <code>5440841102871517055</code>",
        reply_markup=admin_back_kb(), parse_mode="HTML")
    await state.set_state(AdminStates.wait_for_product_emoji)

@dp.message(AdminStates.wait_for_product_emoji)
async def save_product_emoji(m: Message, state: FSMContext):
    emoji_id = (m.text or "").strip()
    if emoji_id != "0" and (not emoji_id.isdigit() or not (5 <= len(emoji_id) <= 25)):
        return await m.answer("❌ Emoji ID must be numeric (5–25 digits), or send 0.")
    data = await state.get_data()
    emoji_value = "" if emoji_id == "0" else emoji_id
    db_query("UPDATE products SET custom_emoji_id=? WHERE category=? AND panel_name=?",
             (emoji_value, data.get("product_emoji_category"), data.get("product_emoji_panel")))
    await m.answer("✅ Product emoji updated for this product and all its plans.", reply_markup=admin_kb(), parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("add_plan_product_"))
async def add_plan_product_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        product_id = int(call.data.rsplit("_", 1)[1])
    except ValueError:
        return await call.answer("Invalid product.", show_alert=True)
    prod = db_query("SELECT category, panel_name, custom_emoji_id FROM products WHERE id=? ORDER BY id LIMIT 1", (product_id,), fetchone=True)
    if not prod:
        return await call.answer("Product not found.", show_alert=True)
    await state.update_data(add_plan_product_id=product_id, add_plan_category=prod[0], add_plan_panel=prod[1], add_plan_emoji=prod[2])
    await call.message.edit_text(
        "➕ <b>Add Plan</b>\nSend one line in this format:\n"
        "<code>12 HOURS | PID=1 | USER=40 | RESELLER=30</code>",
        reply_markup=admin_back_kb(), parse_mode="HTML")
    await state.set_state(AdminStates.add_plan_for_product)

@dp.message(AdminStates.add_plan_for_product)
async def add_plan_product_save(m: Message, state: FSMContext):
    import re
    line = (m.text or "").strip()
    parts = [x.strip() for x in line.split("|")]
    if len(parts) != 4:
        return await m.answer("❌ Format: Plan Name | PID=1 | USER=40 | RESELLER=30")
    vals = {}
    for part in parts[1:]:
        if "=" not in part:
            return await m.answer("❌ Format: Plan Name | PID=1 | USER=40 | RESELLER=30")
        k, v = part.split("=", 1); vals[k.strip().upper()] = v.strip()
    try:
        plan_name = parts[0]; pid = int(vals["PID"]); user_price = float(vals["USER"]); reseller_price = float(vals["RESELLER"])
        if not plan_name or pid < 1 or user_price < 0 or reseller_price < 0: raise ValueError()
    except Exception:
        return await m.answer("❌ Invalid plan name, PID or price. Please retry.")
    data = await state.get_data()
    # New plan is a separate product row, retaining category, panel and product emoji.
    db_query("INSERT INTO products (category,panel_name,name,price_inr,reseller_price,stock,apk_link,validity,device_limit,is_active,is_maintenance,api_pid,custom_emoji_id) VALUES (?,?,?,?,?,?,?,?,?,1,0,?,?)",
             (data["add_plan_category"], data["add_plan_panel"], plan_name, user_price, reseller_price, 999999, "", plan_name, "1 Device", pid, data.get("add_plan_emoji", "")))
    await m.answer(f"✅ Plan <b>{html.escape(plan_name)}</b> added.\nPID: <code>{pid}</code>\nUSER: {fmt_curr(user_price)}\nRESELLER: {fmt_curr(reseller_price)}", reply_markup=admin_kb(), parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("toggle_p_"))
async def admin_toggle_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    p_id = int(call.data.split("_")[2])
    current = db_query("SELECT is_active FROM products WHERE id=?", (p_id,), fetchone=True)[0]
    new_val = 0 if current == 1 else 1
    db_query("UPDATE products SET is_active=? WHERE id=?", (new_val, p_id))
    await call.answer("Visibility updated successfully!", show_alert=True)
    await admin_view_product(call)

@dp.callback_query(F.data.startswith("maintenance_p_"))
async def admin_toggle_product_maintenance(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        p_id = int(call.data.rsplit("_", 1)[1])
        row = db_query("SELECT category, panel_name, is_maintenance FROM products WHERE id=?", (p_id,), fetchone=True)
        if not row:
            return await call.answer("Product not found.", show_alert=True)
        new_value = 0 if int(row[2] or 0) else 1
        db_query("UPDATE products SET is_maintenance=? WHERE category=? AND panel_name=?", (new_value, row[0], row[1]))
        await call.answer("Product maintenance enabled 🛠️" if new_value else "Product maintenance disabled ✅", show_alert=True)
        await admin_view_product(call)
    except Exception as e:
        logger.exception("Could not toggle product maintenance")
        await call.answer("Unable to update maintenance status.", show_alert=True)

# ==============================================================================
# FIX: Edit product field – correctly handle different data types and multi-word fields
# ==============================================================================
@dp.callback_query(F.data.startswith("edit_p_"))
async def start_edit_product(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    # Use split with maxsplit=3 to keep field name intact (may contain underscores)
    parts = call.data.split("_", 3)
    if len(parts) < 4:
        return await call.answer("Invalid callback data.", show_alert=True)
    p_id = int(parts[2])
    field = parts[3]
    await state.update_data(edit_p_id=p_id, edit_field=field)
    if field == 'keys':
        await call.message.edit_text("📥 <b>Vault Injection</b>\nPaste the <b>NEW KEYS</b> to append to the stock (1 key per line):", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_add_keys)
    else:
        field_name_map = {'cat': 'New Panel Group/Category Name', 'panel_name': 'New Panel Name', 'name': 'New Plan Name', 'price': 'New USER Price in ₹', 'rprice': 'New RESELLER Price in ₹', 'pid': 'New API PID', 'validity': 'New Plan Validity', 'device': 'New Device Limit', 'apk': 'New Download/API Link (or send none)'}
        await call.message.edit_text(f"✏️ Input the required data for: <b>{field_name_map.get(field, field)}</b>", reply_markup=admin_back_kb(), parse_mode='HTML')
        await state.set_state(AdminStates.wait_for_new_value)

@dp.message(AdminStates.wait_for_new_value)
async def process_edit_value(m: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['edit_p_id']; field = data['edit_field']; new_val = m.text.strip()
    if field == 'product_name':
        if not new_val or len(new_val) > 80:
            return await m.answer('❌ Product name must be 1–80 characters.')
        old_name = data.get('rename_product_old')
        category = data.get('rename_product_category')
        db_query('UPDATE products SET panel_name=? WHERE category=? AND panel_name=?', (new_val, category, old_name))
        await state.clear()
        await m.answer(f'✅ Product renamed to <b>{html.escape(new_val)}</b>. All its plans were updated.', reply_markup=admin_kb(), parse_mode='HTML')
        return
    # Convert price fields to float, others remain strings
    if field in ['price', 'rprice']:
        try:
            new_val = float(new_val)
            if new_val < 0: raise ValueError()
        except ValueError:
            return await m.answer("❌ Invalid number format. Please enter a valid non-negative price (e.g., 500).")
    elif field == 'pid':
        try:
            new_val = int(new_val)
            if new_val < 1: raise ValueError()
        except ValueError:
            return await m.answer("❌ API PID must be a positive integer.")
    elif field == 'apk':
        new_val = "" if new_val.lower() == 'none' else new_val
    # For panel_name, cat, name, validity, device – keep as string
    
    db_col_map = {'cat': 'category', 'panel_name': 'panel_name', 'name': 'name', 'price': 'price_inr', 'rprice': 'reseller_price', 'pid': 'api_pid', 'validity': 'validity', 'device': 'device_limit', 'apk': 'apk_link'}
    if field not in db_col_map:
        return await m.answer('❌ Unsupported field.')
    db_query(f"UPDATE products SET {db_col_map[field]}=? WHERE id=?", (new_val, p_id))
    await m.answer("✅ <b>Plan updated successfully.</b>", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.message(AdminStates.wait_for_add_keys)
async def process_add_keys(m: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['edit_p_id']
    keys = [k.strip() for k in m.text.strip().split('\n') if k.strip()]
    if len(keys) == 0: return await m.answer("❌ Protocol breach: Zero valid keys found.", reply_markup=admin_kb(), parse_mode='HTML')
    conn = sqlite3.connect('yp_shop.db')
    c = conn.cursor()
    for k in keys: c.execute("INSERT INTO product_keys (product_id, key_text) VALUES (?, ?)", (p_id, k))
    c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (len(keys), p_id))
    conn.commit(); conn.close()
    await m.answer(f"✅ <b>Vault Secure!</b> {len(keys)} new keys appended and encrypted.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data.startswith("delete_p_"))
async def admin_delete_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    try: p_id = int(call.data.rsplit("_", 1)[1])
    except ValueError: return await call.answer("Invalid product.", show_alert=True)
    row = db_query("SELECT category, panel_name FROM products WHERE id=?", (p_id,), fetchone=True)
    if not row: return await call.answer("Product not found.", show_alert=True)
    category, panel_name = row
    ids = db_query("SELECT id FROM products WHERE category=? AND panel_name=?", (category, panel_name), fetchall=True) or []
    for item in ids:
        db_query("DELETE FROM product_keys WHERE product_id=?", (item[0],))
    db_query("DELETE FROM products WHERE category=? AND panel_name=?", (category, panel_name))
    await call.answer("Product and all its plans deleted.", show_alert=True)
    await admin_manage_prods(call)

@dp.callback_query(F.data.startswith("delkey_p_"))
async def admin_delete_key_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    p_id = int(call.data.split("_")[2])
    await state.update_data(del_p_id=p_id)
    await call.message.edit_text("🗑 Send the <b>exact string match</b> of the key you wish to purge from the vault:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_delete_key)

@dp.message(AdminStates.wait_for_delete_key)
async def process_delete_key(m: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['del_p_id']
    key_to_delete = m.text.strip()
    key_data = db_query("SELECT id, is_used FROM product_keys WHERE product_id=? AND key_text=?", (p_id, key_to_delete), fetchone=True)
    if not key_data: return await m.answer("❌ Key not found. Check logs and try again.", reply_markup=admin_back_kb(), parse_mode='HTML')
    if key_data[1] == 1: return await m.answer("⚠️ Action Blocked: This key has already been dispatched to a user.", reply_markup=admin_back_kb(), parse_mode='HTML')
    db_query("DELETE FROM product_keys WHERE id=?", (key_data[0],))
    db_query("UPDATE products SET stock = stock - 1 WHERE id=?", (p_id,))
    await m.answer(f"✅ Key <code>{key_to_delete}</code> securely purged from vault.\n📦 Database indices updated.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

# ==============================================================================
# 20. ADMIN TICKETS, BROADCAST, COUPONS
# ==============================================================================
@dp.callback_query(F.data == "admin_view_tickets")
async def admin_view_tickets(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    tickets = db_query("SELECT id, user_id, message, created_at FROM tickets WHERE status='Open' LIMIT 1", fetchall=True)
    if not tickets: return await call.answer("✅ Zero pending issues. Grid is clean!", show_alert=True)
    t = tickets[0]
    text = (f"🎫 <b><u>ACTIVE TICKET #{t[0]}</u></b>\n👤 <b>Origin UID:</b> <code>{t[1]}</code>\n📅 <b>Timestamp:</b> {t[3]}\n\n📝 <b>Payload:</b>\n{t[2]}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Formulate Reply", callback_data=f"reply_ticket_{t[0]}_{t[1]}", style="primary")],
        [InlineKeyboardButton(text="❌ Force Close Ticket", callback_data=f"close_ticket_{t[0]}", style="danger")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("close_ticket_"))
async def close_ticket(call: CallbackQuery):
    ticket_id = call.data.split("_")[2]
    db_query("UPDATE tickets SET status='Closed' WHERE id=?", (ticket_id,))
    await call.answer("✅ Status set to Closed.", show_alert=True)
    await admin_view_tickets(call) 

@dp.callback_query(F.data.startswith("reply_ticket_"))
async def reply_ticket_start(call: CallbackQuery, state: FSMContext):
    data = call.data.split("_")
    ticket_id, user_id = data[2], data[3]
    await state.update_data(ticket_id=ticket_id, user_id=user_id)
    await call.message.edit_text(f"💬 Formulating reply for node <code>{user_id}</code>.\n\nType your message payload:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.ticket_reply_msg)

@dp.message(AdminStates.ticket_reply_msg)
async def send_ticket_reply(m: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await bot.send_message(data['user_id'], f"📞 <b>Admin Reply (Ref #{data['ticket_id']}):</b>\n\n{m.text}", parse_mode='HTML')
        db_query("UPDATE tickets SET status='Closed' WHERE id=?", (data['ticket_id'],))
        await m.answer("✅ Payload delivered and connection closed successfully.", reply_markup=admin_kb(), parse_mode='HTML')
    except Exception as e: await m.answer(f"❌ Transmission Error: {e}", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_broadcast_btn")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("📢 <b>Mass Broadcast Protocol</b>\n\nSend the rich message payload you wish to transmit globally across the grid:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.broadcast_msg)

@dp.message(AdminStates.broadcast_msg)
async def admin_broadcast_send(message: Message, state: FSMContext):
    users = db_query("SELECT user_id FROM users", fetchall=True)
    sent, failed = 0, 0
    m = await message.answer("⏳ Broadcast protocol initiated... Do not interrupt.", parse_mode='HTML')
    bot_username = str(BOT_USERNAME).lstrip('@')
    broadcast_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛍 SHOP NOW', url=f'https://t.me/{bot_username}?start=shop', style='primary')],
        [InlineKeyboardButton(text='💬 FEEDBACK', url='https://t.me/+nykJy-FjkGpjNTBl', style='success')],
    ])
    for u in users:
        try:
            await message.send_copy(chat_id=u[0], reply_markup=broadcast_kb)
            sent += 1
        except Exception:
            # Some message types may not support a copied-message keyboard; retry with buttons in a follow-up.
            try:
                await message.send_copy(chat_id=u[0])
                await bot.send_message(chat_id=u[0], text='Choose an option:', reply_markup=broadcast_kb)
                sent += 1
            except Exception:
                failed += 1
        await asyncio.sleep(0.06)
    await m.edit_text(f"✅ <b>Global Broadcast Complete!</b>\n\n🟢 Nodes reached: {sent}\n🔴 Nodes failed/blocked: {failed}", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_create_coupon")
async def admin_create_coupon_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text('🎟️ <b>Create checkout discount coupon</b>\nEnter a coupon code (letters/numbers). Type /cancel to stop.', reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.add_coupon_code)

@dp.message(AdminStates.add_coupon_code)
async def admin_coupon_code(m: Message, state: FSMContext):
    code = (m.text or '').strip().upper()
    if code == '/CANCEL':
        await state.clear(); return await m.answer('Coupon creation cancelled.', reply_markup=admin_kb())
    if not code or len(code) > 32 or not code.isalnum():
        return await m.answer('Use only letters and numbers, up to 32 characters, or /cancel.')
    await state.update_data(code=code)
    await m.answer('💰 Enter the fixed discount amount in INR (₹), e.g. 20. Type /cancel to stop.')
    await state.set_state(AdminStates.add_coupon_amount)

@dp.message(AdminStates.add_coupon_amount)
async def admin_coupon_amount(m: Message, state: FSMContext):
    if (m.text or '').strip().lower() == '/cancel':
        await state.clear(); return await m.answer('Coupon creation cancelled.', reply_markup=admin_kb())
    try: amount = float(m.text)
    except (ValueError, TypeError): return await m.answer('Enter a valid number, e.g. 20, or /cancel.')
    if amount <= 0 or amount > 100000: return await m.answer('Discount must be greater than ₹0 and at most ₹100000.')
    await state.update_data(amount=round(amount, 2))
    await m.answer('👥 Enter the maximum number of successful uses (positive whole number). Type /cancel to stop.')
    await state.set_state(AdminStates.add_coupon_uses)

@dp.message(AdminStates.add_coupon_uses)
async def admin_coupon_uses(m: Message, state: FSMContext):
    if (m.text or '').strip().lower() == '/cancel':
        await state.clear(); return await m.answer('Coupon creation cancelled.', reply_markup=admin_kb())
    try: uses = int(m.text)
    except (ValueError, TypeError): return await m.answer('Enter a whole number or /cancel.')
    if uses < 1 or uses > 100000: return await m.answer('Uses must be between 1 and 100000.')
    data = await state.get_data()
    db_query('INSERT OR REPLACE INTO order_coupons (code, amount, uses_left, created_at) VALUES (?, ?, ?, ?)', (data['code'], data['amount'], uses, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    await m.answer(f'✅ <b>Checkout coupon created</b>\nCode: <code>{html.escape(data["code"])}</code>\nDiscount: {fmt_curr(data["amount"])}\nMaximum uses: {uses}', reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

# ==============================================================================
# 21. ADMIN RESELLER & SPIN SETTINGS
# ==============================================================================
@dp.callback_query(F.data == "admin_reseller_menu")
async def admin_reseller_menu(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    status_check = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    sys_status = status_check[0] if status_check else "ON"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Grant Reseller Rights", callback_data="reseller_make", style="success"), InlineKeyboardButton(text="➖ Revoke Reseller", callback_data="reseller_remove", style="danger")],
        [InlineKeyboardButton(text="📋 Audit Active Resellers", callback_data="reseller_view", style="primary")],
        [InlineKeyboardButton(text=f"{'🟢' if sys_status == 'ON' else '🔴'} Auto-Upgrade System: {sys_status}", callback_data="admin_toggle_reseller_sys", style="success" if sys_status == 'ON' else "danger")], 
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("👑 <b>Wholesale Reseller Protocols</b>\nSelect administrative action:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "admin_toggle_reseller_sys")
async def toggle_reseller_sys(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    res = db_query("SELECT value FROM settings WHERE key='reseller_system_status'", fetchone=True)
    current = res[0] if res else 'ON'
    new_status = 'OFF' if current == 'ON' else 'ON'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('reseller_system_status', ?)", (new_status,))
    await admin_reseller_menu(call)

@dp.callback_query(F.data.in_(["reseller_make", "reseller_remove"]))
async def reseller_prompt_id(call: CallbackQuery, state: FSMContext):
    action = call.data
    await state.update_data(reseller_action=action)
    await call.message.edit_text("👤 Identify target node. Input <b>User ID</b> or <b>@username</b>:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.reseller_manage_id)

@dp.message(AdminStates.reseller_manage_id)
async def process_reseller_manage(m: Message, state: FSMContext):
    data = await state.get_data()
    target = m.text.strip()
    if target.startswith('@'): target = target[1:]
    user_q = db_query("SELECT user_id, first_name FROM users WHERE user_id=? OR username=? COLLATE NOCASE", (target, target), fetchone=True)
    if not user_q: return await m.answer("❌ Target completely ghosted. Not in database.", reply_markup=admin_back_kb(), parse_mode='HTML')
    u_id, u_name = user_q[0], user_q[1]
    if data['reseller_action'] == "reseller_make":
        db_query("UPDATE users SET is_reseller=1, reseller_since=?, account_type='Reseller' WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d"), u_id))
        await m.answer(f"✅ Credentials upgraded. <b>{u_name}</b> (<code>{u_id}</code>) has reseller rights.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        db_query("UPDATE users SET is_reseller=0, account_type='Regular' WHERE user_id=?", (u_id,))
        await m.answer(f"✅ Credentials revoked. <b>{u_name}</b> (<code>{u_id}</code>) is back to regular user.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "reseller_view")
async def reseller_view(call: CallbackQuery):
    resellers = db_query("SELECT user_id, first_name, username FROM users WHERE is_reseller=1", fetchall=True)
    if not resellers: return await call.message.edit_text("📋 Zero active resellers found.", reply_markup=admin_back_kb(), parse_mode='HTML')
    text = "👑 <b><u>ACTIVE RESELLER AUDIT LOG</u></b> 👑\n━━━━━━━━━━━━━━━━━━\n"
    for r in resellers:
        uname = f"(@{r[2]})" if r[2] else ""
        text += f"👤 {r[1]} {uname}\n🆔 <code>{r[0]}</code>\n\n"
    await call.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_spin_menu")
async def admin_spin_menu(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    status = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    limit = db_query("SELECT value FROM settings WHERE key='daily_spin_limit'", fetchone=True)
    status_val = status[0] if status else 'ON'
    limit_val = limit[0] if limit else '50.0'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Append Reward Logic", callback_data="spin_add", style="success"), InlineKeyboardButton(text="❌ Drop Reward Logic", callback_data="spin_del", style="danger")],
        [InlineKeyboardButton(text="📋 Audit Configs", callback_data="spin_view", style="primary"), InlineKeyboardButton(text="⚙️ Throttle Limits", callback_data="spin_limit", style="primary")],
        [InlineKeyboardButton(text=f"{'🟢' if status_val == 'ON' else '🔴'} Master Toggle: {status_val}", callback_data="spin_toggle", style="success" if status_val == 'ON' else "danger")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(f"🎰 <b>Advanced Ludo/Spin Algorithms</b>\nCurrent Threshold: ₹{limit_val}", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "spin_toggle")
async def spin_toggle(call: CallbackQuery):
    res = db_query("SELECT value FROM settings WHERE key='spin_status'", fetchone=True)
    current = res[0] if res else 'ON'
    new_status = 'OFF' if current == 'ON' else 'ON'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('spin_status', ?)", (new_status,))
    await admin_spin_menu(call)

@dp.callback_query(F.data == "admin_toggle_bot")
async def toggle_bot(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    res = db_query("SELECT value FROM settings WHERE key='bot_status'", fetchone=True)
    current = res[0] if res else 'ON'
    new_status = 'OFF' if current == 'ON' else 'ON'
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('bot_status', ?)", (new_status,))
    await call.message.edit_reply_markup(reply_markup=admin_kb())

@dp.callback_query(F.data == "spin_add")
async def spin_add_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🎰 Inject new decimal logic limit (e.g. 15.50):", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.spin_add_reward)

@dp.message(AdminStates.spin_add_reward)
async def spin_add_exec(m: Message, state: FSMContext):
    try:
        amt = float(m.text)
        db_query("INSERT INTO spin_rewards (amount) VALUES (?)", (amt,))
        await m.answer(f"✅ Algorithm updated. New vector {fmt_curr(amt)} injected.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Math parsing error.")

@dp.callback_query(F.data == "spin_view")
async def spin_view(call: CallbackQuery):
    rewards = db_query("SELECT amount FROM spin_rewards ORDER BY amount ASC", fetchall=True)
    text = "🎰 <b>Live Ludo Constants</b>\n\n"
    for r in rewards: text += f"🎁 {fmt_curr(r[0])}\n"
    await call.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_set_video")
async def admin_set_video_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("📹 Input direct streaming / YouTube Link for Tutorial system:\n<i>(Or type 'None' to clear registry):</i>", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_howto_video)

@dp.message(AdminStates.wait_for_howto_video)
async def exec_set_video(m: Message, state: FSMContext):
    link = m.text.strip()
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('how_to_video', ?)", (link,))
    await m.answer("✅ Routing complete. Video linked.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_all_files")
async def admin_set_all_files_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🔗 Input the direct Channel / Cloud URL for 'Download Files' button:\n<i>(Or type 'None' to format data):</i>", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_all_files_link)

@dp.message(AdminStates.wait_for_all_files_link)
async def exec_set_all_files(m: Message, state: FSMContext):
    link = m.text.strip()
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('all_files_link', ?)", (link,))
    await m.answer("✅ Global resource variable updated.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_edit_emojis")
async def admin_edit_emojis(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    rows = db_query("SELECT key, value FROM settings WHERE key LIKE 'emoji_%' ORDER BY key", fetchall=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for row in rows:
        key = row[0]
        slot = key.replace("emoji_", "")
        current_id = row[1] if row[1] else "Not set"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{slot} (ID: {current_id})", callback_data=f"edit_emoji_{slot}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("🎨 <b>Edit All Emojis</b>\nChoose an emoji slot to change its ID:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("edit_emoji_"))
async def admin_edit_emoji_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    slot = call.data.split("edit_emoji_", 1)[1]
    await state.update_data(emoji_slot=slot)
    current = get_setting(f"emoji_{slot}", "Not set")
    await call.message.edit_text(f"✏️ Enter new emoji ID for <b>{slot}</b>:\nCurrent: {current}\n(Leave empty to reset to default)", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_emoji_slot)

@dp.message(AdminStates.wait_for_emoji_slot)
async def save_emoji_slot(m: Message, state: FSMContext):
    data = await state.get_data()
    slot = data['emoji_slot']
    new_id = m.text.strip()
    if new_id == "":
        db_query("DELETE FROM settings WHERE key=?", (f"emoji_{slot}",))
        await m.answer(f"✅ Reset emoji for '{slot}' to default.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        if not new_id.isdigit():
            await m.answer("❌ Invalid ID! Must be numeric.", reply_markup=admin_kb(), parse_mode='HTML')
            return
        set_setting(f"emoji_{slot}", new_id)
        await m.answer(f"✅ Emoji for '{slot}' updated to ID {new_id}.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_edit_ui_menu")
async def admin_edit_ui_menu(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Edit Start Menu Text", callback_data="edit_ui_start", style="primary")],
        [InlineKeyboardButton(text="Edit Download Files Text", callback_data="edit_ui_download", style="primary")],
        [InlineKeyboardButton(text="Edit VIP Menu Text", callback_data="edit_ui_vip", style="primary")],
        [InlineKeyboardButton(text="Edit Lucky Dice Text", callback_data="edit_ui_dice", style="primary")],
        [InlineKeyboardButton(text="Edit Add Balance Text", callback_data="edit_ui_add_balance", style="primary")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("✏️ <b>Edit User Interface Texts</b>\nSelect which text you want to modify:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("edit_ui_"))
async def admin_edit_ui_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    ui_key = call.data.split("_")[2]
    await state.update_data(ui_key=ui_key)
    current_text = get_ui_text(ui_key)
    await call.message.edit_text(f"📝 Send the new text for <b>{ui_key.upper()}</b> menu.\n\nCurrent text:\n{current_text}", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.edit_ui_text)

@dp.message(AdminStates.edit_ui_text)
async def admin_save_ui_text(m: Message, state: FSMContext):
    data = await state.get_data()
    ui_key = data['ui_key']
    new_text = m.text
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"ui_{ui_key}", new_text))
    await m.answer(f"✅ UI text <b>{ui_key}</b> updated successfully!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_edit_reseller_price")
async def admin_edit_reseller_price_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    prods = db_query("SELECT id, name, category, panel_name, reseller_price FROM products ORDER BY category, panel_name", fetchall=True)
    if not prods: return await call.message.edit_text("No products to edit.", reply_markup=admin_back_kb(), parse_mode='HTML')
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in prods:
        panel_name = p[3] if p[3] is not None else ""
        r_price = safe_float(p[4])
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{p[2]} - {panel_name} - {p[1]} (₹{r_price:.2f})", callback_data=f"edit_reseller_{p[0]}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("👑 <b>Edit Reseller Price per Product</b>\nSelect a product to change its wholesale price:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("edit_reseller_"))
async def admin_edit_reseller_price_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    prod_id = int(call.data.split("_")[2])
    await state.update_data(edit_reseller_prod_id=prod_id)
    await call.message.edit_text("💰 Enter the new <b>Reseller Price</b> in Rupees (₹) for this product:", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.edit_reseller_price)

@dp.message(AdminStates.edit_reseller_price)
async def admin_save_reseller_price(m: Message, state: FSMContext):
    try:
        new_price = float(m.text)
        data = await state.get_data()
        prod_id = data['edit_reseller_prod_id']
        db_query("UPDATE products SET reseller_price=? WHERE id=?", (new_price, prod_id))
        await m.answer(f"✅ Reseller price updated to {fmt_curr(new_price)} for product ID {prod_id}.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Invalid number. Please enter a valid price.")

@dp.callback_query(F.data == "admin_set_reseller_fee")
async def admin_set_reseller_fee(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("💰 Enter the new <b>Reseller Setup Fee</b> in Rupees (₹):\nCurrent: " + get_setting("reseller_setup_fee", "200.0"), reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_reseller_setup_fee)

@dp.message(AdminStates.wait_for_reseller_setup_fee)
async def admin_save_reseller_fee(m: Message, state: FSMContext):
    try:
        fee = float(m.text)
        set_setting("reseller_setup_fee", str(fee))
        await m.answer(f"✅ Reseller setup fee updated to {fmt_curr(fee)}.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Invalid number. Please enter a valid amount.")

@dp.callback_query(F.data == "admin_set_reseller_min")
async def admin_set_reseller_min(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("💳 Enter the new <b>Minimum Balance</b> required to become reseller (₹):\nCurrent: " + get_setting("reseller_min_balance", "500.0"), reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_reseller_min_balance)

@dp.message(AdminStates.wait_for_reseller_min_balance)
async def admin_save_reseller_min(m: Message, state: FSMContext):
    try:
        min_bal = float(m.text)
        set_setting("reseller_min_balance", str(min_bal))
        await m.answer(f"✅ Minimum reseller balance updated to {fmt_curr(min_bal)}.", reply_markup=admin_kb(), parse_mode='HTML')
        await state.clear()
    except ValueError: await m.answer("❌ Invalid number. Please enter a valid amount.")

@dp.callback_query(F.data == "admin_set_support_links")
async def admin_set_support_links(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Set Telegram Link", callback_data="admin_set_telegram", style="primary")],
        [InlineKeyboardButton(text="📱 Set WhatsApp Link", callback_data="admin_set_whatsapp", style="primary")],
        [InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text("📌 <b>Support Contact Links</b>\nSet the URLs for Telegram and WhatsApp support:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "admin_set_telegram")
async def admin_set_telegram(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("✈️ Enter the Telegram contact URL (e.g., https://t.me/YourSupport):", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_support_telegram)

@dp.message(AdminStates.wait_for_support_telegram)
async def save_telegram_link(m: Message, state: FSMContext):
    link = m.text.strip()
    set_setting("support_telegram", link)
    await m.answer("✅ Telegram support link updated!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_whatsapp")
async def admin_set_whatsapp(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("📱 Enter the WhatsApp contact URL (e.g., https://wa.me/1234567890):", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_support_whatsapp)

@dp.message(AdminStates.wait_for_support_whatsapp)
async def save_whatsapp_link(m: Message, state: FSMContext):
    link = m.text.strip()
    set_setting("support_whatsapp", link)
    await m.answer("✅ WhatsApp support link updated!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_category_emojis")
async def admin_set_category_emojis(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in FIXED_CATEGORIES:
        current = get_setting(f"cat_emoji_{cat}", "Not set")
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{cat} (ID: {current})", callback_data=f"set_cat_emoji_{cat}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("🎨 <b>Set Category Emojis</b>\nChoose a category to set its custom emoji ID:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("set_cat_emoji_"))
async def admin_set_category_emoji_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    category = call.data.split("set_cat_emoji_", 1)[1]
    await state.update_data(cat_emoji_category=category)
    await call.message.edit_text(f"🎨 Enter the emoji ID for <b>{category}</b>:\n(Leave empty to reset to default)", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_category_emoji)

@dp.message(AdminStates.wait_for_category_emoji)
async def save_category_emoji(m: Message, state: FSMContext):
    data = await state.get_data()
    category = data['cat_emoji_category']
    emoji_id = m.text.strip()
    if emoji_id == "":
        db_query("DELETE FROM settings WHERE key=?", (f"cat_emoji_{category}",))
        await m.answer(f"✅ Reset emoji for {category} to default.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        if not emoji_id.isdigit():
            await m.answer("❌ Invalid ID! Must be numeric.", reply_markup=admin_kb(), parse_mode='HTML')
            return
        set_setting(f"cat_emoji_{category}", emoji_id)
        await m.answer(f"✅ Emoji set for {category} successfully!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_panel_emojis")
async def admin_set_panel_emojis(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    panels = db_query("SELECT DISTINCT panel_name FROM products WHERE panel_name != '' ORDER BY panel_name", fetchall=True)
    if not panels:
        await call.message.edit_text("No panel names found in products.", reply_markup=admin_back_kb(), parse_mode='HTML')
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in panels:
        panel = p[0]
        current = get_setting(f"panel_emoji_{panel}", "Not set")
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{panel} (ID: {current})", callback_data=f"set_panel_emoji_{panel}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="Back to Admin", callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text("🖼 <b>Set Panel Emojis</b>\nChoose a panel name to set its custom emoji ID:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("set_panel_emoji_"))
async def admin_set_panel_emoji_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    panel_name = call.data.split("set_panel_emoji_", 1)[1]
    await state.update_data(panel_emoji_name=panel_name)
    await call.message.edit_text(f"🎨 Enter the emoji ID for panel <b>{panel_name}</b>:\n(Leave empty to reset to default)", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_panel_emoji_id)

@dp.message(AdminStates.wait_for_panel_emoji_id)
async def save_panel_emoji(m: Message, state: FSMContext):
    data = await state.get_data()
    panel_name = data['panel_emoji_name']
    emoji_id = m.text.strip()
    if emoji_id == "":
        db_query("DELETE FROM settings WHERE key=?", (f"panel_emoji_{panel_name}",))
        await m.answer(f"✅ Reset emoji for panel '{panel_name}'.", reply_markup=admin_kb(), parse_mode='HTML')
    else:
        if not emoji_id.isdigit():
            await m.answer("❌ Invalid ID! Must be numeric.", reply_markup=admin_kb(), parse_mode='HTML')
            return
        set_setting(f"panel_emoji_{panel_name}", emoji_id)
        await m.answer(f"✅ Emoji set for panel '{panel_name}'!", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_set_fampay_token")
async def set_fampay_token_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text('🔑 <b>SET FAMGATEWAY API TOKEN</b>\nSend the API token. It will be stored in bot settings and masked in the UI. Send /cancel to stop.', reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_fampay_api_only)

@dp.message(AdminStates.wait_for_fampay_api_only)
async def set_fampay_token_value(m: Message, state: FSMContext):
    value=(m.text or '').strip()
    if value.lower()=='/cancel': await state.clear(); return await m.answer('Cancelled.', reply_markup=admin_kb())
    if len(value)<8: return await m.answer('❌ Token looks too short. Send a valid API token or /cancel.')
    set_setting('fampay_api_key', value)
    await state.clear(); await m.answer('✅ FamGateway API token saved securely.', reply_markup=admin_kb())

@dp.callback_query(F.data == "admin_set_fampay_upi")
async def set_fampay_upi_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text('💳 <b>SET MERCHANT UPI ID</b>\nSend the UPI ID associated with FamGateway (example: name@bank). Send /cancel to stop.', reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_fampay_upi_only)

@dp.message(AdminStates.wait_for_fampay_upi_only)
async def set_fampay_upi_value(m: Message, state: FSMContext):
    value=(m.text or '').strip()
    if value.lower()=='/cancel': await state.clear(); return await m.answer('Cancelled.', reply_markup=admin_kb())
    if '@' not in value or len(value)>100: return await m.answer('❌ Enter a valid UPI ID or /cancel.')
    set_setting('fampay_upi_id', value)
    masked=value[:2]+'••••'+value[-3:] if len(value)>7 else '••••'
    await state.clear(); await m.answer(f'✅ Merchant UPI ID saved: <code>{html.escape(masked)}</code>', reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_setup_fampay")
async def setup_fampay_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    current = get_setting('fampay_api_key', '')
    current_upi = get_setting('fampay_upi_id', '')
    masked = (current[:6] + '••••••' + current[-4:]) if len(current) > 12 else ('•••••• configured' if current else 'not configured')
    upi_display = (current_upi[:2] + '••••' + current_upi[-3:]) if len(current_upi) > 7 else (current_upi or 'not configured')
    await call.message.edit_text(f'⚙️ <b>FAMGATEWAY SETUP</b>\nCurrent API key: <code>{masked}</code>\nMerchant UPI: <code>{html.escape(upi_display)}</code>\n\nSend your FamGateway API key, or /cancel to keep the existing key.', reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_fampay_api_key)

@dp.message(AdminStates.wait_for_fampay_api_key)
async def fampay_api_key(m: Message, state: FSMContext):
    value = (m.text or '').strip()
    if value.lower() == '/cancel':
        await state.clear(); return await m.answer('FamGateway setup cancelled.', reply_markup=admin_kb())
    if len(value) < 8:
        return await m.answer('That API key looks too short. Send the valid FamGateway API key or /cancel.')
    set_setting('fampay_api_key', value)
    await m.answer('✅ API key saved. Now send the merchant UPI ID associated with FamGateway (or /cancel to keep the existing UPI ID).')
    await state.set_state(AdminStates.wait_for_fampay_upi)

@dp.message(AdminStates.wait_for_fampay_upi)
async def fampay_upi_id(m: Message, state: FSMContext):
    value = (m.text or '').strip()
    if value.lower() == '/cancel':
        await state.clear()
        return await m.answer('FamGateway settings saved. Existing UPI ID was kept.', reply_markup=admin_kb())
    if '@' not in value or len(value) > 100:
        return await m.answer('Please enter a valid UPI ID (usually name@bank), or /cancel.')
    set_setting('fampay_upi_id', value)
    masked = value[:2] + '••••' + value[-3:] if len(value) > 7 else '••••'
    await m.answer(f'✅ <b>FamGateway configured.</b>\nAPI key: <code>{html.escape(value[:0] or "saved securely")}</code>\nMerchant UPI: <code>{html.escape(masked)}</code>', reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data == "admin_setup_binance")
async def setup_binance_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("🪙 <b>CRYPTO NODE INIT: Step 1/3</b>\nInput Master <b>Binance API Key</b>:\n<i>(Type /cancel to halt protocol)</i>", reply_markup=admin_back_kb(), parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_binance_api)

@dp.message(AdminStates.wait_for_binance_api)
async def setup_binance_api(m: Message, state: FSMContext):
    if m.text == '/cancel':
        await state.clear()
        return await m.answer("Sequence aborted.", reply_markup=admin_kb(), parse_mode='HTML')
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('binance_api', ?)", (m.text.strip(),))
    await m.answer("🪙 <b>CRYPTO NODE INIT: Step 2/3</b>\nNow inject the highly secure <b>Binance Secret Key</b>:", parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_binance_secret)

@dp.message(AdminStates.wait_for_binance_secret)
async def setup_binance_secret(m: Message, state: FSMContext):
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('binance_secret', ?)", (m.text.strip(),))
    await m.answer("🪙 <b>CRYPTO NODE INIT: Step 3/3</b>\nFinal variable: Set the public <b>USDT Deposit Address (TRC20/BEP20)</b>\nUsers will broadcast to this ledger:", parse_mode='HTML')
    await state.set_state(AdminStates.wait_for_binance_address)

@dp.message(AdminStates.wait_for_binance_address)
async def setup_binance_address(m: Message, state: FSMContext):
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('binance_address', ?)", (m.text.strip(),))
    await m.answer("✅ <b>Blockchain node synchronized.</b> Crypto gateway is fully armed.", reply_markup=admin_kb(), parse_mode='HTML')
    await state.clear()

# ==============================================================================
# 22. BOOTSTRAPPING & MAIN
# ==============================================================================
async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Paste your Telegram bot token into the BOT_TOKEN variable near the top of this file.")
    init_db()
    logger.info("Initializing DB structure...")
    migrate_categories()
    asyncio.create_task(auto_verify_task())
    logger.info("FamGateway Auto-Verifier Daemon Running in Background.")
    logger.info("🚀 CORE SYSTEM IS FULLY OPERATIONAL...")
    try:
        await dp.start_polling(bot)
    except Exception as err:
        logger.error(f"Critical System Failure in Polling: {err}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("System shutting down gracefully. Goodbye.")
