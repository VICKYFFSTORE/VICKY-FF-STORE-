import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButtonRequestUser
import requests, sqlite3, re, time, json, threading, html as _html
from datetime import datetime, timedelta, timezone
_IST = timezone(timedelta(hours=5, minutes=30))
def _now_ist(): return datetime.now(_IST).strftime("%d %b %Y %I:%M %p")
import os, random, string, io
import base64

def _safe_err(e):
    """Exception ko HTML-safe string mein convert karo"""
    return str(e).replace('<','&lt;').replace('>','&gt;')

def _strip_tg_emoji(text):
    """<tg-emoji ...>fallback</tg-emoji> → fallback (plain emoji only)"""
    return re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)

def _safe_send(chat_id, text, **kwargs):
    """send_message with auto-fallback: strips tg-emoji if ENTITY_TEXT_INVALID."""
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as _e:
        if 'entity_text_invalid' in str(_e).lower():
            try:
                return bot.send_message(chat_id, _strip_tg_emoji(text), **kwargs)
            except Exception as _e2:
                print(f"[SAFE_SEND] fallback failed: {_e2}")
        else:
            raise


def _send_react(chat_id, text, big=True, **kwargs):
    FREE_REACTIONS = ["👍","👎","❤️","🔥","🥰","👏","😁","🤔","🤯","😱","🤬","😢","🎉","🤩","🤮","💩","🙏","👌","🕊","🤡","🥱","🥴","😍","🐳","❤️‍🔥","🌚","🌭","💯","🤣","⚡","🍌","🏆","💔","🤨","😐","🍓","🍾","💋","🖕","😈","😴","😭","🤓","👻","👨‍💻","👀","🎃","🙈","😇","😨","🤝","✍️","🤗","🫡","🎅","🎄","☃️","💅","🤪","🗿","🆒","💘","🙉","🦄","😘","💊","🙊","😎","👾","🤷‍♂️","🤷","🤷‍♀️","😡"]
    try:
        sent = bot.send_message(chat_id, text, **kwargs)
        try:
            random_emoji = random.choice(FREE_REACTIONS)
            bot.set_message_reaction(
                sent.chat.id,
                sent.message_id,
                [telebot.types.ReactionTypeEmoji(random_emoji)],
                is_big=big
            )
        except Exception as re:
            print(f"[REACTION ERROR] {re}")
        return sent
    except Exception as e:
        print(f"[SEND_REACT] {e}")

BOT_TOKEN = "8987630612:AAFfw7YKxzuT0xI0Bh1BQ1mMNrMxIZ0BsN0"
OWNER_ID = 8700582148
FREE_CREDITS = 3         # Starting credits (new users ko sirf 3 milenge) - DO NOT CHANGE
FREE_CREDITS_BOT = 3    # Bot (private) users ke liye max free usage
FREE_CREDITS_GROUP = 3  # Group users ke liye max free usage
REFERRAL_BONUS = 2       # Har refer pe 2 credits milenge referrer ko
BOT_CLONE_REFERRAL_REQUIRED = 30
LOG_CHANNEL_ID   = -1003891564918  # @databasefelix - all logs go here now
TOKEN_LOG_GROUP  = -1003891564918  # @databasefelix

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ── Auto-fallback patch: strip <tg-emoji> on ENTITY_TEXT_INVALID ──
_orig_send_message = bot.send_message
def _patched_send_message(chat_id, text, **kwargs):
    try:
        return _orig_send_message(chat_id, text, **kwargs)
    except Exception as _e:
        if 'entity_text_invalid' in str(_e).lower():
            try:
                import re as _rp
                _clean = _rp.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', str(text))
                return _orig_send_message(chat_id, _clean, **kwargs)
            except Exception as _e2:
                print(f"[PATCH_SEND] fallback failed: {_e2}")
        raise
bot.send_message = _patched_send_message

_orig_reply_to = bot.reply_to
def _patched_reply_to(message, text, **kwargs):
    try:
        return _orig_reply_to(message, text, **kwargs)
    except Exception as _e:
        if 'entity_text_invalid' in str(_e).lower():
            try:
                import re as _rp
                _clean = _rp.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', str(text))
                return _orig_reply_to(message, _clean, **kwargs)
            except Exception as _e2:
                try:
                    return _orig_send_message(message.chat.id, _clean, **kwargs)
                except Exception as _e3:
                    print(f"[PATCH_REPLY] all fallbacks failed: {_e3}")
        raise
bot.reply_to = _patched_reply_to
_BOT_USERNAME_CACHE = None
_BOT_ID_CACHE = None
def _get_bot_username():
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE: return _BOT_USERNAME_CACHE
    try: _BOT_USERNAME_CACHE = bot.get_me().username
    except: _BOT_USERNAME_CACHE = "felix_modz1"
    return _BOT_USERNAME_CACHE

def _get_bot_id():
    global _BOT_ID_CACHE
    if _BOT_ID_CACHE: return _BOT_ID_CACHE
    try: _BOT_ID_CACHE = bot.get_me().id
    except: _BOT_ID_CACHE = int(BOT_TOKEN.split(':')[0])
    return _BOT_ID_CACHE
_F="━━━━━━━━━━━━━━━━━━━━━━━━━━"  # separator line (replaces fire emoji)

class _StyledKB(KeyboardButton):
    def __init__(self, text, style=None, icon_custom_emoji_id=None, **kwargs):
        super().__init__(text, **kwargs)
        self.__style = style
        self.__icon_emoji = icon_custom_emoji_id
    def to_dict(self):
        d = super().to_dict()
        if self.__style: d['style'] = self.__style
        if self.__icon_emoji: d['icon_custom_emoji_id'] = self.__icon_emoji
        return d

class _StyledIKB(InlineKeyboardButton):
    def __init__(self, text, style=None, icon_custom_emoji_id=None, **kwargs):
        super().__init__(text, **kwargs)
        self.__style = 'success' if style == 'active' else style
        self.__icon_emoji = icon_custom_emoji_id
    def to_dict(self):
        d = super().to_dict()
        try:
            if self.__style: d['style'] = self.__style
        except: pass
        try:
            if self.__icon_emoji: d['icon_custom_emoji_id'] = self.__icon_emoji
        except: pass
        return d

def _KB(text, style=None, icon_custom_emoji_id=None, **kwargs):
    if style == 'active': style = 'success'
    try: return _StyledKB(text, style=style, icon_custom_emoji_id=icon_custom_emoji_id, **kwargs)
    except:
        try: return KeyboardButton(text, **kwargs)
        except: return KeyboardButton(text)

def _IKB(text, style=None, icon_custom_emoji_id=None, **kwargs):
    try: return _StyledIKB(text, style=style, icon_custom_emoji_id=icon_custom_emoji_id, **kwargs)
    except:
        try: return InlineKeyboardButton(text, **kwargs)
        except:
            safe_kw = {k:v for k,v in kwargs.items() if k in ('callback_data','url','switch_inline_query','switch_inline_query_current_chat')}
            return InlineKeyboardButton(text, **safe_kw) if safe_kw else InlineKeyboardButton(text, callback_data='noop')

S_NONE='none'; S_NUM='number'; S_USER='username'; S_TID='tgid'
S_ADH='aadhar'; S_INSTA='instagram'; S_FF='freefire'; S_FFL='freefire_like'
S_VEH='vehicle'; S_REDEEM='redeem_code'; S_CLONE='bot_clone'
S_BOMB='bomber'
S_PREM_REDEEM='premium_redeem'
S_FF_LIKE_UID='ff_like_uid'  # new: waiting for UID input for like

user_state = {}
bomber_jobs = {}
_user_temp_cache = {}  # Temporary cache for un_more callback data

def pbar(pct):
    """Progress bar: ░░░░░░░░░░░░░  0%  →  █████████░░░░  70%  →  █████████████  100%"""
    pct = max(0, min(100, int(pct)))
    total = 13
    filled = int(round(pct / 100 * total))
    empty = total - filled
    bar = '█' * filled + '░' * empty
    return f"{bar}  {pct}%"

# ── Premium emoji for loading animation ──
_ANIM_PE = "<tg-emoji emoji-id='6255767342916045646'>⚡</tg-emoji>"

# Label map — stype string ya custom string pass karo
_ANIM_LABELS = {
    'number':   'ꜰᴇᴛᴄʜɪɴɢ ɴᴜᴍʙᴇʀ ɪɴꜰᴏ',
    'username': 'ꜰᴇᴛᴄʜɪɴɢ ᴜꜱᴇʀɴᴀᴍᴇ ɪɴꜰᴏ',
    'tgid':     'ꜰᴇᴛᴄʜɪɴɢ ᴛɢ ɪᴅ ɪɴꜰᴏ',
    'aadhar':   'ꜰᴇᴛᴄʜɪɴɢ ᴀᴀᴅʜᴀʀ ɪɴꜰᴏ',
    'instagram':'ꜰᴇᴛᴄʜɪɴɢ ɪɴꜱᴛᴀ ɪɴꜰᴏ',
    'freefire': 'ꜰᴇᴛᴄʜɪɴɢ ꜰʀᴇᴇꜰɪʀᴇ ɪɴꜰᴏ',
    'like':     'ꜱᴇɴᴅɪɴɢ ʟɪᴋᴇꜱ',
    'viplike':  'ꜱᴇɴᴅɪɴɢ ᴠɪᴩ ʟɪᴋᴇꜱ',
    'bomber':   'ʟᴀᴜɴᴄʜɪɴɢ ʙᴏᴍʙᴇʀ',
    'vehicle':  'ꜰᴇᴛᴄʜɪɴɢ ᴠᴇʜɪᴄʟᴇ ɪɴꜰᴏ',
    'usernum':  'ꜰᴇᴛᴄʜɪɴɢ ᴜꜱᴇʀ ɪɴꜰᴏ',
}

def _start_anim(chat_id, msg_id, label_key):
    """
    3-phase loading animation.
    Phase 1 (~1s):  ʙʏᴩᴀꜱꜱɪɴɢ ꜱʏꜱᴛᴇᴍ
    Phase 2 (~1.5s): ꜱᴇᴀʀᴄʜɪɴɢ
    Phase 3 (loop): <label>   (jab tak stop_flag[0]=True ho)
    Format:
        ███░░░░░░░  68%
        ꜰᴇᴛᴄʜɪɴɢ ɴᴜᴍʙᴇʀ ɪɴꜰᴏ [premium_emoji]
    Returns stop_flag (list with 1 bool) — caller sets stop_flag[0]=True to stop.
    """
    final_label = _ANIM_LABELS.get(label_key, 'ꜰᴇᴛᴄʜɪɴɢ')
    stop_flag = [False]

    def _run():
        # Phase 1 — ʙʏᴩᴀꜱꜱɪɴɢ ꜱʏꜱᴛᴇᴍ
        for pct in [0, 8, 15]:
            if stop_flag[0]: return
            try:
                bot.edit_message_text(
                    f"<blockquote>{pbar(pct)}\nʙʏᴩᴀꜱꜱɪɴɢ ꜱʏꜱᴛᴇᴍ {_ANIM_PE}</blockquote>",
                    chat_id, msg_id, parse_mode='HTML')
            except: pass
            time.sleep(0.38)
        # Phase 2 — ꜱᴇᴀʀᴄʜɪɴɢ
        for pct in [22, 35, 48, 55]:
            if stop_flag[0]: return
            try:
                bot.edit_message_text(
                    f"<blockquote>{pbar(pct)}\nꜱᴇᴀʀᴄʜɪɴɢ {_ANIM_PE}</blockquote>",
                    chat_id, msg_id, parse_mode='HTML')
            except: pass
            time.sleep(0.42)
        # Phase 3 — final label loop
        _pcts = [60, 68, 75, 82, 88, 92, 95]
        _i = 0
        _max_loops = 33  # ~30 seconds max — prevent infinite stuck (increased for slow APIs)
        while not stop_flag[0] and _i < _max_loops:
            pct = _pcts[min(_i, len(_pcts)-1)]
            try:
                bot.edit_message_text(
                    f"<blockquote>{pbar(pct)}\n{final_label} {_ANIM_PE}</blockquote>",
                    chat_id, msg_id, parse_mode='HTML')
            except: pass
            _i += 1
            time.sleep(0.9)
        # Agar loop timeout ho gaya — "failed" show karo
        if not stop_flag[0]:
            stop_flag[0] = True
            try:
                bot.edit_message_text(
                    f"<blockquote>{pbar(95)}\n❌ ꜰᴀɪʟᴇᴅ — ᴘʟᴇᴀꜱᴇ ʀᴇᴛʀʏ {_ANIM_PE}</blockquote>",
                    chat_id, msg_id, parse_mode='HTML')
            except: pass

    threading.Thread(target=_run, daemon=True).start()
    return stop_flag

LIKE_API_0 = "https://simran-like-r-bot-api.vercel.app/like"  # NEW primary
LIKE_API_1 = "https://freefireautolikeservice.vercel.app/like"
LIKE_API_2 = "https://ff-like-api-azure.vercel.app/like"
LIKE_API_3 = "https://sexty-autolikes.vercel.app/like"
LIKE_API_4 = "https://verma-like-api.vercel.app/like"
LIKE_API_5 = "https://druu-likes-15-day.vercel.app/like"  # 5th API backup
FF_INFO_API = "https://free-fire-info-bice.vercel.app/"
FF_INFO_KEY = "SH4DAW-D4DY"
LIKE_COOLDOWN_HOURS = 12
LIKE_COOLDOWN_SECS  = LIKE_COOLDOWN_HOURS * 3600
LIKE_DAILY_MAX      = 10

uid_like_cooldown = {}   # key = "userid:uid"
like_rate_limits  = {}   # key = "userid:like"

VALID_REGIONS = ["ind","bd","id","th","vn","br","ru","my","sg","ph"]
REGION_NAMES  = {
    "ind":"🇮🇳 INDIA","bd":"🇧🇩 BANGLADESH","id":"🇮🇩 INDONESIA",
    "th":"🇹🇭 THAILAND","vn":"🇻🇳 VIETNAM","br":"🇧🇷 BRAZIL",
    "ru":"🇷🇺 RUSSIA","my":"🇲🇾 MALAYSIA","sg":"🇸🇬 SINGAPORE","ph":"🇵🇭 PHILIPPINES"
}

def _like_check_cooldown(user_id,uid):
    if is_admin(user_id): return True,0,None
    key=f"{user_id}:{uid}"; now=time.time()
    # Memory check first (fast path)
    if key in uid_like_cooldown:
        last=uid_like_cooldown[key].get("last_like",0)
        elapsed=now-last
        if elapsed<LIKE_COOLDOWN_SECS:
            return False,LIKE_COOLDOWN_SECS-elapsed,uid_like_cooldown[key]
    else:
        # DB se load karo (restart ke baad memory empty hoti hai)
        try:
            row=c.execute("SELECT last_like,uid,region,timestamp FROM ff_like_cooldown WHERE key=?",(key,)).fetchone()
            if row:
                last=row[0]; elapsed=now-last
                info={"last_like":last,"uid":row[1],"region":row[2],"timestamp":row[3]}
                uid_like_cooldown[key]=info  # memory mein bhi cache karo
                if elapsed<LIKE_COOLDOWN_SECS:
                    return False,LIKE_COOLDOWN_SECS-elapsed,info
        except: pass
    return True,0,None

def _like_update_cooldown(user_id,uid,region):
    key=f"{user_id}:{uid}"; now=time.time()
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info={"last_like":now,"uid":uid,"region":region,"timestamp":ts}
    uid_like_cooldown[key]=info  # memory update
    # DB mein persist karo
    try:
        c.execute("INSERT OR REPLACE INTO ff_like_cooldown(key,user_id,uid,region,last_like,timestamp) VALUES(?,?,?,?,?,?)",
                  (key,user_id,uid,region,now,ts))
        conn.commit()
    except: pass

def _like_check_ratelimit(user_id):
    if is_admin(user_id): return True
    key=f"{user_id}:like"; now=time.time()
    # Memory se ya DB se timestamps load karo
    if key not in like_rate_limits:
        try:
            row=c.execute("SELECT timestamps FROM ff_like_ratelimit WHERE key=?",(key,)).fetchone()
            if row and row[0]:
                like_rate_limits[key]=[float(t) for t in row[0].split(",") if t.strip()]
            else:
                like_rate_limits[key]=[]
        except:
            like_rate_limits[key]=[]
    like_rate_limits[key]=[t for t in like_rate_limits[key] if now-t<86400]
    return len(like_rate_limits[key])<LIKE_DAILY_MAX

def _like_update_ratelimit(user_id):
    if is_admin(user_id): return
    key=f"{user_id}:like"; now=time.time()
    like_rate_limits.setdefault(key,[]).append(now)
    like_rate_limits[key]=[t for t in like_rate_limits[key] if now-t<86400]
    # DB mein persist karo
    try:
        ts_str=",".join(str(t) for t in like_rate_limits[key])
        c.execute("INSERT OR REPLACE INTO ff_like_ratelimit(key,user_id,timestamps) VALUES(?,?,?)",
                  (key,user_id,ts_str))
        conn.commit()
    except: pass

def _like_remaining_daily(user_id):
    if is_admin(user_id): return LIKE_DAILY_MAX
    key=f"{user_id}:like"; now=time.time()
    if key not in like_rate_limits:
        try:
            row=c.execute("SELECT timestamps FROM ff_like_ratelimit WHERE key=?",(key,)).fetchone()
            if row and row[0]:
                like_rate_limits[key]=[float(t) for t in row[0].split(",") if t.strip()]
            else:
                like_rate_limits[key]=[]
        except:
            like_rate_limits[key]=[]
    used=len([t for t in like_rate_limits.get(key,[]) if now-t<86400])
    return max(0,LIKE_DAILY_MAX-used)

_db_lock=threading.Lock()

# ══════════════════════════════════════════════════════════
# TELEGRAM CHANNEL BACKUP SYSTEM
# Har 30 sec mein database channel pe save hoga
# SIRF apna channel ka latest message use karo — koi bhi
# dusra platform ka purana data kabhi nahi lega
# ══════════════════════════════════════════════════════════
BACKUP_CHANNEL_ID = -1003982551952  # @felixdeta — original + clone dono ka data yahan, alag file names se
BACKUP_INTERVAL   = 30              # har 30 sec mein backup

# Latest backup message ID track karo (pin ke liye)
_last_backup_msg_id = None

def _get_backup_channel():
    return BACKUP_CHANNEL_ID

def _get_backup_filename():
    """
    Har bot ka unique backup file naam:
      Original  → felix_MAIN_db_backup.json
      Clone     → felix_CLONE_<owner_id>_db_backup.json
    Isse ek hi channel mein dono ka data alag-alag rehta hai.
    """
    try:
        is_clone = (OWNER_ID != 8335023642)
    except:
        is_clone = False
    if is_clone:
        return f"felix_CLONE_{OWNER_ID}_db_backup.json"
    return "felix_MAIN_db_backup.json"

def _db_to_json_str():
    """DB ka pura data JSON string mein convert karo"""
    data = {
        "backup_time": _now_ist(),
        "tables": {}
    }
    try:
        con = sqlite3.connect(_DB_FILE)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        for table in tables:
            try:
                cur.execute(f"SELECT * FROM {table}")
                data["tables"][table] = [dict(r) for r in cur.fetchall()]
            except:
                data["tables"][table] = []
        con.close()
    except Exception as e:
        print(f"[TG_BACKUP] DB read error: {e}")
    return json.dumps(data, indent=2, default=str)

def _json_str_to_db(json_str):
    """JSON string se DB restore karo — CREATE TABLE + INSERT OR REPLACE"""
    try:
        data = json.loads(json_str)
        tables = data.get("tables", {})
        if not tables:
            print(f"[TG_RESTORE] ⚠️ Backup JSON mein koi tables nahi — empty backup hai")
            return False
        non_empty = {t: rows for t, rows in tables.items() if rows}
        print(f"[TG_RESTORE] Backup mein {len(tables)} tables, {len(non_empty)} mein data hai")
        if not non_empty:
            print(f"[TG_RESTORE] ⚠️ Saari tables empty hain — fresh start theek hai")
            return True

        con = sqlite3.connect(_DB_FILE)
        cur = con.cursor()
        restored = 0
        skipped = 0

        for table, rows in tables.items():
            if not rows:
                continue
            # Skip internal sqlite tables
            if table.startswith("sqlite_"):
                continue
            try:
                columns = list(rows[0].keys())
                cols_str = ", ".join(f'"{c}"' for c in columns)
                placeholders = ", ".join("?" for _ in columns)

                # ── KEY FIX: Table exist nahi toh pehle create karo ──
                # Column types guess karte hain pehle row se
                col_defs = []
                for c_name in columns:
                    val = rows[0].get(c_name)
                    if c_name in ('id', 'user_id', 'group_id') and columns.index(c_name) == 0:
                        col_defs.append(f'"{c_name}" INTEGER PRIMARY KEY')
                    elif isinstance(val, int):
                        col_defs.append(f'"{c_name}" INTEGER')
                    elif isinstance(val, float):
                        col_defs.append(f'"{c_name}" REAL')
                    else:
                        col_defs.append(f'"{c_name}" TEXT')
                create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
                try:
                    cur.execute(create_sql)
                except:
                    pass  # Already exists — theek hai

                # ── Existing columns check — backup mein extra cols ho sakti hain ──
                cur.execute(f'PRAGMA table_info("{table}")')
                existing_cols = {row[1] for row in cur.fetchall()}
                # Backup mein jo columns hain jo DB mein nahi hain, unhe add karo
                for c_name in columns:
                    if c_name not in existing_cols:
                        val = rows[0].get(c_name)
                        col_type = "INTEGER" if isinstance(val, (int, type(None))) else "TEXT"
                        try:
                            cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{c_name}" {col_type}')
                        except:
                            pass

                sql = f'INSERT OR REPLACE INTO "{table}" ({cols_str}) VALUES ({placeholders})'
                for row in rows:
                    try:
                        cur.execute(sql, [row.get(c) for c in columns])
                        restored += 1
                    except Exception as _re:
                        skipped += 1
                        print(f"[TG_RESTORE] Skip {table} row: {_re}")
            except Exception as te:
                print(f"[TG_RESTORE] Table '{table}' error: {te}")

        con.commit()
        con.close()
        print(f"[TG_RESTORE] ✅ {restored} rows restored, {skipped} skipped")
        return restored > 0
    except json.JSONDecodeError as je:
        print(f"[TG_RESTORE] ❌ JSON parse error: {je}")
        return False
    except Exception as e:
        print(f"[TG_RESTORE] ❌ {e}")
        return False

_last_backup_hash_tg = ""

def _tg_channel_backup(force=False):
    """Database ko Telegram channel pe document ke roop mein bhejo aur pin karo"""
    global _last_backup_hash_tg, _last_backup_msg_id
    backup_ch = _get_backup_channel()
    try:
        json_str = _db_to_json_str()

        # Duplicate backup avoid
        import hashlib as _hl_tg
        curr_hash = _hl_tg.md5(json_str.encode()).hexdigest()
        if not force and curr_hash == _last_backup_hash_tg:
            return  # koi change nahi
        _last_backup_hash_tg = curr_hash

        # JSON file banao aur channel pe bhejo
        import io as _io_tg
        file_bytes = json_str.encode("utf-8")
        bio = _io_tg.BytesIO(file_bytes)
        bot_label = "CLONE" if (OWNER_ID != 8335023642) else "MAIN"
        file_name = _get_backup_filename()
        bio.name = file_name
        bio.seek(0)

        now_str = _now_ist()
        caption = (
            f"<blockquote>📦 <b>DATABASE BACKUP [{bot_label}]</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕒 Time: {now_str}\n"
            f"📊 Tables: {len(json.loads(json_str).get('tables', {}))}\n"
            f"💾 Size: {len(file_bytes)} bytes\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ @Felix_modz1</blockquote>"
        )

        sent_msg = bot.send_document(
            backup_ch,
            bio,
            caption=caption,
            parse_mode="HTML",
            visible_file_name=file_name
        )
        print(f"[TG_BACKUP] ✅ [{bot_label}] Saved to channel {backup_ch} @ {now_str}")

        # ── AUTO-PIN: latest backup pin karo taki restore hamesha latest le ──
        if sent_msg and sent_msg.message_id:
            _last_backup_msg_id = sent_msg.message_id
            try:
                bot.pin_chat_message(backup_ch, sent_msg.message_id, disable_notification=True)
                print(f"[TG_BACKUP] 📌 [{bot_label}] Message {sent_msg.message_id} pinned")
            except Exception as _pin_e:
                print(f"[TG_BACKUP] Pin failed (no admin?): {_pin_e}")
    except Exception as e:
        print(f"[TG_BACKUP] Error: {e}")

def _ensure_missing_tables():
    """
    Restore ke baad missing tables ensure karo.
    Backup JSON mein jo tables nahi hain (empty tha / naya table hai),
    unhe yahan CREATE TABLE IF NOT EXISTS se safely create karo.
    """
    try:
        con = sqlite3.connect(_DB_FILE)
        cur = con.cursor()
        cur.executescript('''
CREATE TABLE IF NOT EXISTS search_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, search_type TEXT,
  query TEXT, search_date TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS admins(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
  added_by INTEGER, added_date TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS welcome_settings(
  id INTEGER PRIMARY KEY CHECK(id=1), welcome_emoji TEXT DEFAULT '👋',
  welcome_caption TEXT DEFAULT 'Welcome!',
  welcome_image TEXT, welcome_video TEXT, bot_dp TEXT, first_time_sticker TEXT);
CREATE TABLE IF NOT EXISTS feature_toggles(
  id INTEGER PRIMARY KEY AUTOINCREMENT, feature_name TEXT UNIQUE,
  is_enabled INTEGER DEFAULT 1, updated_by INTEGER, updated_date TEXT);
CREATE TABLE IF NOT EXISTS groups(
  group_id INTEGER PRIMARY KEY, group_title TEXT, added_date TEXT, added_by INTEGER,
  credits INTEGER DEFAULT 0, unlimited INTEGER DEFAULT 0,
  is_blocked INTEGER DEFAULT 0, searches INTEGER DEFAULT 0, is_muted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS bot_clones(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
  bot_token TEXT, created_date TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS force_join_channels(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, chat_title TEXT,
  chat_url TEXT, added_by INTEGER, added_date TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS group_welcome_settings(
  group_id INTEGER PRIMARY KEY, welcome_on INTEGER DEFAULT 1,
  group_rules TEXT DEFAULT '', updated_date TEXT,
  welcome_image TEXT, welcome_video TEXT, video_list TEXT);
CREATE TABLE IF NOT EXISTS redeem_codes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, credits INTEGER,
  redeem_limit INTEGER, used_count INTEGER DEFAULT 0, created_by INTEGER,
  created_date TEXT, expiry TEXT);
CREATE TABLE IF NOT EXISTS redeemed_users(
  code TEXT, user_id INTEGER, redeem_date TEXT, PRIMARY KEY(code,user_id));
CREATE TABLE IF NOT EXISTS premium_codes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, days INTEGER,
  redeem_limit INTEGER DEFAULT 1, used_count INTEGER DEFAULT 0, created_by INTEGER,
  created_date TEXT, expiry TEXT);
CREATE TABLE IF NOT EXISTS redeemed_premium(
  code TEXT, user_id INTEGER, redeem_date TEXT, PRIMARY KEY(code,user_id));
CREATE TABLE IF NOT EXISTS blocked_identifiers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, identifier TEXT UNIQUE,
  identifier_type TEXT, blocked_by INTEGER, blocked_date TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS clone_admins(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clone_owner_uid INTEGER, admin_uid INTEGER,
  added_by INTEGER, added_date TEXT);
CREATE TABLE IF NOT EXISTS clone_forced_channels(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clone_owner_uid INTEGER, chat_id TEXT, chat_title TEXT,
  chat_url TEXT, added_by INTEGER, added_date TEXT,
  is_active INTEGER DEFAULT 1, is_fake INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS user_fj_attempts(
  user_id INTEGER PRIMARY KEY,
  attempts INTEGER DEFAULT 0, last_attempt TEXT);
CREATE TABLE IF NOT EXISTS protected_users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  identifier TEXT UNIQUE, identifier_type TEXT,
  protected_by INTEGER, protected_date TEXT);
CREATE TABLE IF NOT EXISTS api_keys(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  api_name TEXT UNIQUE, api_url TEXT, api_key TEXT,
  is_active INTEGER DEFAULT 1, added_by INTEGER, added_date TEXT);
CREATE TABLE IF NOT EXISTS admin_btn_toggles(
  btn_name TEXT PRIMARY KEY, is_visible INTEGER DEFAULT 1,
  updated_by INTEGER, updated_date TEXT);
CREATE TABLE IF NOT EXISTS token_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_name TEXT,
  username TEXT, added INTEGER DEFAULT 0, total INTEGER DEFAULT 0,
  source TEXT, bot_name TEXT, log_date TEXT, log_time TEXT);
CREATE TABLE IF NOT EXISTS verify_tokens(
  user_id INTEGER, token TEXT UNIQUE, created_at TEXT);
CREATE TABLE IF NOT EXISTS verify_claims(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
  claim_date TEXT, UNIQUE(user_id, claim_date));
CREATE TABLE IF NOT EXISTS daily_claims(
  user_id INTEGER, claim_date TEXT, PRIMARY KEY(user_id,claim_date));
CREATE TABLE IF NOT EXISTS referrals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, referrer INTEGER, referred INTEGER, date TEXT);
CREATE TABLE IF NOT EXISTS ff_like_cooldown(
  key TEXT PRIMARY KEY, user_id INTEGER, uid TEXT, region TEXT,
  last_like REAL, timestamp TEXT);
CREATE TABLE IF NOT EXISTS ff_like_ratelimit(
  key TEXT PRIMARY KEY, user_id INTEGER, timestamps TEXT);
        ''')
        # welcome_settings default row
        cur.execute("INSERT OR IGNORE INTO welcome_settings(id) VALUES(1)")
        # owner admin row
        try:
            from datetime import datetime as _dt
            cur.execute("INSERT OR IGNORE INTO admins(user_id,added_by,added_date,is_active) VALUES(?,?,?,1)",
                        (8335023642, 8335023642, _dt.now().strftime("%Y-%m-%d %H:%M:%S")))
        except: pass
        con.commit()
        con.close()
        print(f"[DB_REINIT] ✅ All missing tables ensured after restore")
    except Exception as e:
        print(f"[DB_REINIT] Error: {e}")


def _tg_channel_restore():
    """
    Startup pe Telegram channel ke PINNED message se restore karo.
    Backup hone ke baad auto-pin hota hai — isliye pinned = hamesha latest.
    Pehle local DB delete karo taki Termux/Render ka purana data kabhi mix na ho.
    """
    backup_ch = _get_backup_channel()
    bot_label = "CLONE" if (OWNER_ID != 8335023642) else "MAIN"
    print(f"[TG_RESTORE] Restoring [{bot_label}] from channel {backup_ch}...")
    try:
        my_file = _get_backup_filename()
        backup_file_id = None

        # STEP 1: Pinned message se file lo
        try:
            chat_info = bot.get_chat(backup_ch)
            if chat_info.pinned_message and chat_info.pinned_message.document:
                doc = chat_info.pinned_message.document
                if doc.file_name and doc.file_name == my_file:
                    backup_file_id = doc.file_id
                    print(f"[TG_RESTORE] Pinned message se mila: {doc.file_name}")
                else:
                    print(f"[TG_RESTORE] ⚠️ Pinned file '{doc.file_name}' match nahi kiya (chahiye: {my_file})")
                    print(f"[TG_RESTORE] 🔍 Recent messages mein '{my_file}' dhundh raha hoon...")
                    # Fallback: last 20 messages mein dhundo
                    try:
                        msgs = bot.get_chat_history(backup_ch, limit=20) if hasattr(bot, 'get_chat_history') else []
                    except:
                        msgs = []
                    for _m in (msgs or []):
                        if _m.document and _m.document.file_name == my_file:
                            backup_file_id = _m.document.file_id
                            print(f"[TG_RESTORE] ✅ Recent messages mein mila: {_m.document.file_name}")
                            break
                    if not backup_file_id:
                        print(f"[TG_RESTORE] ⚠️ Recent messages mein bhi nahi mila — fresh start")
            else:
                print(f"[TG_RESTORE] Pinned message mein document nahi hai")
        except Exception as _pe:
            print(f"[TG_RESTORE] Pinned check error: {_pe}")

        if not backup_file_id:
            print(f"[TG_RESTORE] [{bot_label}] Channel mein koi backup nahi mila — fresh start.")
            return

        # STEP 2: Pehle local DB wipe karo
        try:
            if os.path.exists(_DB_FILE):
                os.remove(_DB_FILE)
                print(f"[TG_RESTORE] Local DB delete ho gayi — sirf channel ka data use hoga")
        except Exception as _del_e:
            print(f"[TG_RESTORE] DB delete error: {_del_e}")

        # STEP 3: Channel se download aur restore
        print(f"[TG_RESTORE] Downloading backup file...")
        file_info  = bot.get_file(backup_file_id)
        file_bytes = bot.download_file(file_info.file_path)
        json_str   = file_bytes.decode("utf-8")
        print(f"[TG_RESTORE] Downloaded {len(file_bytes)} bytes")

        ok = _json_str_to_db(json_str)
        if ok:
            print(f"[TG_RESTORE] [{bot_label}] Channel ka data restore ho gaya!")
        else:
            print(f"[TG_RESTORE] [{bot_label}] Restore failed!")
        # Restore ke baad missing tables ensure karo (search_history, admins, etc.)
        _ensure_missing_tables()
    except Exception as e:
        print(f"[TG_RESTORE] Error: {e}")


def _tg_backup_loop():
    """Har 30 sec mein backup loop"""
    import time as _t_bk
    while True:
        _t_bk.sleep(BACKUP_INTERVAL)
        _tg_channel_backup()

# Emergency backup on exit
import atexit as _atexit
def _emergency_backup():
    print("[TG_BACKUP] 🚨 Emergency backup on exit...")
    _tg_channel_backup(force=True)
_atexit.register(_emergency_backup)
# ══════════════════════════════════════════════════════════
# TELEGRAM CHANNEL BACKUP END
# ══════════════════════════════════════════════════════════


# ── Persistent DB — same file after every restart ──
# Store in script's own directory so data survives restarts
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BOT_ID = BOT_TOKEN.split(':')[0]
_DB_FILE = os.path.join(_SCRIPT_DIR, f"bot_{_BOT_ID}.db")

conn = sqlite3.connect(_DB_FILE, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.commit()

class _SafeCursor:
    """Thread-safe cursor wrapper - prevents 'Recursive use of cursors not allowed'"""
    def __init__(self, connection):
        self._conn=connection
        self._lock=_db_lock
    def execute(self,sql,params=()):
        with self._lock:
            self._cur=self._conn.cursor()
            self._cur.execute(sql,params)
            return self
    def executescript(self,sql):
        with self._lock:
            self._cur=self._conn.cursor()
            self._cur.executescript(sql)
            return self
    def executemany(self,sql,data):
        with self._lock:
            self._cur=self._conn.cursor()
            self._cur.executemany(sql,data)
            return self
    def fetchone(self):
        return self._cur.fetchone() if hasattr(self,'_cur') else None
    def fetchall(self):
        return self._cur.fetchall() if hasattr(self,'_cur') else []
    @property
    def rowcount(self):
        return self._cur.rowcount if hasattr(self,'_cur') else 0

c = _SafeCursor(conn)

_orig_conn = conn  # raw sqlite3 connection

def _safe_commit():
    with _db_lock:
        try: _orig_conn.commit()
        except: pass

# Wrapper so conn.commit() calls work without monkey-patching (read-only attr fix)
class _ConnWrapper:
    def __init__(self, c): self._c = c
    def __getattr__(self, name):
        if name == 'commit': return _safe_commit
        return getattr(self._c, name)

conn = _ConnWrapper(_orig_conn)
c.executescript('''
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
  join_date TEXT, referrer INTEGER, credits INTEGER DEFAULT 5,
  is_blocked INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0,
  premium_until TEXT, joined_channel INTEGER DEFAULT 0, first_time INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS referrals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, referrer INTEGER, referred INTEGER, date TEXT);
CREATE TABLE IF NOT EXISTS search_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, search_type TEXT,
  query TEXT, search_date TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS daily_claims(
  user_id INTEGER, claim_date TEXT, PRIMARY KEY(user_id,claim_date));
CREATE TABLE IF NOT EXISTS redeem_codes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, credits INTEGER,
  redeem_limit INTEGER, used_count INTEGER DEFAULT 0, created_by INTEGER,
  created_date TEXT, expiry TEXT);
CREATE TABLE IF NOT EXISTS redeemed_users(
  code TEXT, user_id INTEGER, redeem_date TEXT, PRIMARY KEY(code,user_id));
CREATE TABLE IF NOT EXISTS premium_codes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, days INTEGER,
  redeem_limit INTEGER DEFAULT 1, used_count INTEGER DEFAULT 0, created_by INTEGER,
  created_date TEXT, expiry TEXT);
CREATE TABLE IF NOT EXISTS redeemed_premium(
  code TEXT, user_id INTEGER, redeem_date TEXT, PRIMARY KEY(code,user_id));
CREATE TABLE IF NOT EXISTS force_join_channels(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, chat_title TEXT,
  chat_url TEXT, added_by INTEGER, added_date TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS groups(
  group_id INTEGER PRIMARY KEY, group_title TEXT, added_date TEXT, added_by INTEGER,
  credits INTEGER DEFAULT 0, unlimited INTEGER DEFAULT 0,
  is_blocked INTEGER DEFAULT 0, searches INTEGER DEFAULT 0, is_muted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS welcome_settings(
  id INTEGER PRIMARY KEY CHECK(id=1), welcome_emoji TEXT DEFAULT '👋',
  welcome_caption TEXT DEFAULT 'Welcome!',
  welcome_image TEXT, welcome_video TEXT, bot_dp TEXT, first_time_sticker TEXT);
CREATE TABLE IF NOT EXISTS blocked_identifiers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, identifier TEXT UNIQUE,
  identifier_type TEXT, blocked_by INTEGER, blocked_date TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS feature_toggles(
  id INTEGER PRIMARY KEY AUTOINCREMENT, feature_name TEXT UNIQUE,
  is_enabled INTEGER DEFAULT 1, updated_by INTEGER, updated_date TEXT);
CREATE TABLE IF NOT EXISTS admins(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
  added_by INTEGER, added_date TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS bot_clones(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
  bot_token TEXT, created_date TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS token_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_name TEXT,
  username TEXT, added INTEGER DEFAULT 0, total INTEGER DEFAULT 0,
  source TEXT, bot_name TEXT, log_date TEXT, log_time TEXT);
CREATE TABLE IF NOT EXISTS group_welcome_settings(
  group_id INTEGER PRIMARY KEY, welcome_on INTEGER DEFAULT 1,
  group_rules TEXT DEFAULT '', updated_date TEXT,
  welcome_image TEXT, welcome_video TEXT, video_list TEXT);
  CREATE TABLE IF NOT EXISTS verify_tokens(
  user_id INTEGER, token TEXT UNIQUE, created_at TEXT);
CREATE TABLE IF NOT EXISTS verify_claims(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
  claim_date TEXT, UNIQUE(user_id, claim_date));
''')
conn.commit()

def safe_alter(tbl, col, typ, default="0"):
    try: c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ} DEFAULT {default}"); conn.commit()
    except: pass

safe_alter("groups","searches","INTEGER","0")
safe_alter("group_welcome_settings","welcome_image","TEXT","NULL")
safe_alter("group_welcome_settings","welcome_video","TEXT","NULL")
safe_alter("group_welcome_settings","video_list","TEXT","NULL")
safe_alter("group_welcome_settings","group_sticker","TEXT","NULL")
safe_alter("group_welcome_settings","welcome_text","TEXT","NULL")
safe_alter("group_welcome_settings","bye_on","INTEGER","1")
safe_alter("groups","unlimited","INTEGER","0")
safe_alter("groups","is_blocked","INTEGER","0")
safe_alter("groups","credits","INTEGER","0")
safe_alter("groups","is_muted","INTEGER","0")
# Clone admins — original owner jo clone pe admin set kare
try:
    conn._c.execute("""CREATE TABLE IF NOT EXISTS clone_admins(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clone_owner_uid INTEGER, admin_uid INTEGER,
        added_by INTEGER, added_date TEXT)""")
    _orig_conn.commit()
except: pass

# Clone forced channels — original owner jo clone me force join add kare (REMOVE proof)
try:
    conn._c.execute("""CREATE TABLE IF NOT EXISTS clone_forced_channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clone_owner_uid INTEGER, chat_id TEXT, chat_title TEXT,
        chat_url TEXT, added_by INTEGER, added_date TEXT,
        is_active INTEGER DEFAULT 1,
        is_fake INTEGER DEFAULT 0)""")
    _orig_conn.commit()
except: pass
# is_fake column add karo agar purana DB hai
try:
    conn._c.execute("ALTER TABLE clone_forced_channels ADD COLUMN is_fake INTEGER DEFAULT 0")
    _orig_conn.commit()
except: pass

# User verify attempts tracker — fake FJ ke liye (3rd attempt pe auto-pass)
try:
    conn._c.execute("""CREATE TABLE IF NOT EXISTS user_fj_attempts(
        user_id INTEGER PRIMARY KEY,
        attempts INTEGER DEFAULT 0,
        last_attempt TEXT)""")
    _orig_conn.commit()
except: pass

# Protected users table — admin se protected users ka detail search me hide hoga
try:
    conn._c.execute("""CREATE TABLE IF NOT EXISTS protected_users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT UNIQUE,
        identifier_type TEXT,
        protected_by INTEGER,
        protected_date TEXT)""")
    _orig_conn.commit()
except: pass

# API Keys management table
try:
    conn._c.execute("""CREATE TABLE IF NOT EXISTS api_keys(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_name TEXT UNIQUE,
        api_url TEXT,
        api_key TEXT,
        is_active INTEGER DEFAULT 1,
        added_by INTEGER,
        added_date TEXT)""")
    _orig_conn.commit()
except: pass

# Admin panel button toggles table
try:
    conn._c.execute("""CREATE TABLE IF NOT EXISTS admin_btn_toggles(
        btn_name TEXT PRIMARY KEY, is_visible INTEGER DEFAULT 1,
        updated_by INTEGER, updated_date TEXT)""")
    _orig_conn.commit()
except: pass
# Default buttons seeding
_DEFAULT_ADMIN_BTNS = [
    "📊 DASHBOARD","👥 USER LIST","📢 BROADCAST","📜 HISTORY",
    "👋 BOT WELCOME SETTINGS","⚙️ TOGGLE FEATURES","👥 GROUP MANAGEMENT",
    "🌟 GROUP WELCOME SETTINGS","🚫 BLOCK USER (ID)","✅ UNBLOCK USER (ID)",
    "🚫 BLOCK NUMBER","✅ UNBLOCK NUMBER","📋 BLOCKED LIST","💎 ADD PREMIUM",
    "💰 ADD CREDITS","➖ REMOVE CREDITS","👥 ADMIN MGMT","📢 CHANNEL MGMT",
    "🎫 GEN REDEEM CODE","🎁 GEN PREMIUM CODE","💀 REVOKE ALL PREMIUM",
    "🧹 CLEAR HISTORY","🤖 CLONE MGMT","🔗 ADD CLONE CHANNEL","🤖 FORCE ADD CLONE"
]
for _btn in _DEFAULT_ADMIN_BTNS:
    try:
        conn._c.execute("INSERT OR IGNORE INTO admin_btn_toggles(btn_name,is_visible) VALUES(?,1)",(_btn,))
    except: pass
try: _orig_conn.commit()
except: pass

# Group welcome helpers
def get_group_welcome_media(gid):
    """Return (image_path, video_path, video_list_json, sticker_id) for group welcome"""
    try:
        c.execute("SELECT welcome_image,welcome_video,video_list,group_sticker FROM group_welcome_settings WHERE group_id=?",(gid,))
        r=c.fetchone()
        if r: return r[0],r[1],r[2],r[3] if len(r)>3 else None
    except: pass
    return None,None,None,None

def set_group_welcome_image(gid,path):
    c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",(gid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("UPDATE group_welcome_settings SET welcome_image=?,updated_date=? WHERE group_id=?",(path,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),gid)); conn.commit()

def set_group_welcome_video(gid,path):
    c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",(gid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("UPDATE group_welcome_settings SET welcome_video=?,updated_date=? WHERE group_id=?",(path,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),gid)); conn.commit()

def set_group_welcome_video_list(gid,lst_json):
    c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",(gid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("UPDATE group_welcome_settings SET video_list=?,updated_date=? WHERE group_id=?",(lst_json,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),gid)); conn.commit()

def set_group_welcome_sticker(gid,stk_id):
    c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",(gid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("UPDATE group_welcome_settings SET group_sticker=?,updated_date=? WHERE group_id=?",(stk_id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),gid)); conn.commit()

def get_next_group_video(gid):
    """Round-robin se next video file_id return karo from video_list"""
    try:
        c.execute("SELECT video_list FROM group_welcome_settings WHERE group_id=?",(gid,))
        r=c.fetchone()
        if not r or not r[0]: return None
        lst=json.loads(r[0])
        if not lst: return None
        # Use a per-group counter stored in memory
        idx=_grp_video_idx.get(gid,0) % len(lst)
        _grp_video_idx[gid]=idx+1
        return lst[idx]
    except: return None

_grp_video_idx={}  # in-memory round-robin index per group

def get_group_welcome(gid):
    c.execute("SELECT welcome_on, group_rules FROM group_welcome_settings WHERE group_id=?",(gid,))
    r=c.fetchone()
    if r: return r[0], r[1] or ''
    # Default: ON, no rules
    c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",
              (gid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
    return 1, ''

def get_group_bye(gid):
    """Returns bye_on status (1=on, 0=off). Default ON."""
    try:
        c.execute("SELECT bye_on FROM group_welcome_settings WHERE group_id=?",(gid,))
        r=c.fetchone()
        if r: return r[0] if r[0] is not None else 1
    except: pass
    return 1

def set_group_bye_on(gid, val):
    try:
        c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",
                  (gid, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE group_welcome_settings SET bye_on=?,updated_date=? WHERE group_id=?",
                  (val, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gid))
        conn.commit()
    except Exception as e: print(f"[BYE_SET] {e}")

def set_group_welcome_on(gid, val):
    """welcome_on toggle karo — baaki columns (video/image/sticker) preserve karo"""
    try:
        # Row ensure karo pehle
        c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",
                  (gid, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # Sirf welcome_on update karo — baaki sab preserve
        c.execute("UPDATE group_welcome_settings SET welcome_on=?,updated_date=? WHERE group_id=?",
                  (val, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gid))
        conn.commit()
    except Exception as e:
        print(f"[SET_WEL_ON] {e}")

def set_group_rules(gid, rules):
    try:
        c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",
                  (gid, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE group_welcome_settings SET group_rules=?,updated_date=? WHERE group_id=?",
                  (rules, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gid))
        conn.commit()
    except Exception as e:
        print(f"[SET_RULES] {e}")

c.execute("INSERT OR IGNORE INTO welcome_settings(id) VALUES(1)")
c.execute("INSERT OR IGNORE INTO admins(user_id,added_by,added_date) VALUES(?,?,?)",
          (OWNER_ID,OWNER_ID,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
for f in ['number','username','aadhar','instagram','freefire','tgid','freefire_like',
          'vehicle','bomber']:
    c.execute("INSERT OR IGNORE INTO feature_toggles(feature_name,is_enabled) VALUES(?,1)",(f,))
conn.commit()

FORCE_JOIN_DEFAULT_CHANNELS = [
    ("@Felix_modz1", "Felix Modz", "https://t.me/Felix_modz1"),
    ("@Felix_bhai1", "Felix Bhai", "https://t.me/Felix_bhai1"),
]

def _fj_normalize(cid):
    """Normalize chat_id for dedup: strip @, lowercase, strip spaces, handle t.me URLs."""
    s = str(cid).strip().lower()
    if 't.me/' in s:
        s = s.split('t.me/')[-1].strip('/')
    if s.startswith('@'): s = s[1:]
    return s

def _dedup_force_join_channels():
    """DB se Felix default channels remove karo — code se manage honge. Baaki dedup karo."""
    try:
        # Felix ke default channels DB se hata do — get_force_join_channels mein hardcode hain
        default_nks = {_fj_normalize(cid) for cid, _, _ in FORCE_JOIN_DEFAULT_CHANNELS}
        all_rows = c.execute("SELECT id, chat_id FROM force_join_channels").fetchall()
        seen = {}
        to_delete = []
        for row_id, chat_id in all_rows:
            nk = _fj_normalize(chat_id)
            # Default channels DB se delete karo
            if nk in default_nks:
                to_delete.append(row_id)
                continue
            # Baaki channels — dedup
            if nk in seen:
                to_delete.append(row_id)
            else:
                seen[nk] = row_id
        for rid in to_delete:
            c.execute("DELETE FROM force_join_channels WHERE id=?", (rid,))
        if to_delete:
            _orig_conn.commit()
            print(f"[FJ_DEDUP] Cleaned {len(to_delete)} rows")
    except Exception as e:
        print(f"[FJ_DEDUP] Error: {e}")

# Order: pehle dedup, phir ensure (taaki ensure ke baad dedup na karna pade)
_dedup_force_join_channels()

# ── CLONE MODE: agar ye bot clone hai to admin panel disabled ──
# _run_clone_bot is mein CLONE_OWNER_ID set karta hai apne aap
_IS_CLONE = (OWNER_ID != 8335023642)  # agar owner main owner nahi hai to ye clone hai
_IS_CLASSIC = False  # Normal/Classic clone mode — _run_clone2_bot True set karta hai inject se
_MAIN_OWNER = 8335023642  # Original owner ID hamesha same

# Clone bot ke liye Felix channels clone_forced_channels mein ensure karo
if _IS_CLONE:
    for _fj_cid, _fj_title, _fj_url in FORCE_JOIN_DEFAULT_CHANNELS:
        try:
            _ex2 = c.execute("SELECT id FROM clone_forced_channels WHERE chat_id=? AND clone_owner_uid=?",(_fj_cid, OWNER_ID)).fetchone()
            if not _ex2:
                c.execute("INSERT INTO clone_forced_channels(clone_owner_uid,chat_id,chat_title,chat_url,added_by,added_date,is_active,is_fake) VALUES(?,?,?,?,?,?,1,0)",
                         (OWNER_ID,_fj_cid,_fj_title,_fj_url,OWNER_ID,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        except: pass
    try: _orig_conn.commit()
    except: pass

# Border helpers
# Original bot: premium diamond emoji border
# Clone bot:    simple line ───────────────────────────────
_PREM_EMOJI = "<tg-emoji emoji-id='5465277838993141300'>💎</tg-emoji>"
def _CL_TOP(): return "───────────────────────────────" if _IS_CLONE else _PREM_EMOJI*10
def _CL_BOT(): return "───────────────────────────────" if _IS_CLONE else _PREM_EMOJI*10
# Separator used throughout (clone=line, original=diamond line)
def _SEP():    return "━━━━━━━━━━━━━━━━━━━━━━━━━━" if _IS_CLONE else _F
# ── Credit line helpers ──
# Original bot: 💎💎💎 (premium tg-emoji x10) │ BOT BY : @FELIX_MODZ1
# Clone bot:    ━━━━━━━━━━━━━━━━━━━━━ ⚡ BOT BY : @Felix_modz1 ━━━
def _orig_credit():
    """Original bot credit footer"""
    _L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"
    _SM = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _CK = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    return f"{_L*10}\n{_SM} @Felix_Bhai {_CK}\n{_L*10}"
def _clone_credit():
    """Clone bot credit footer — simple line border"""
    L = "━━━━━━━━━━━━━━━━━━━━━"
    return f"{L}\n⚡ BOT BY : @Felix_modz1\n{L}"
def _credit(): return _orig_credit()  # dono bots pe same footer

# Clone bot ka is_active status (toggle ke liye)
_CLONE_BOT_ACTIVE = True  # Clone bot ON/OFF toggle
_MAIN_BOT_ACTIVE = True   # Default: active (original bot ke liye — admin se toggle)

def is_admin(uid):
    # Clone bot mein: OWNER_ID (clone ka owner) + _MAIN_OWNER + clone_admins
    if _IS_CLONE:
        if uid == OWNER_ID or uid == _MAIN_OWNER: return True
        # Original owner ne jo admins add kiye clone pe
        try:
            c.execute("SELECT COUNT(*) FROM clone_admins WHERE clone_owner_uid=? AND admin_uid=?",(OWNER_ID,uid))
            if c.fetchone()[0]>0: return True
        except: pass
        return False
    if uid==OWNER_ID: return True
    if uid in _admin_cache: return _admin_cache[uid]
    c.execute("SELECT COUNT(*) FROM admins WHERE user_id=? AND is_active=1",(uid,))
    result = c.fetchone()[0]>0
    _admin_cache[uid] = result
    return result

_admin_cache = {}  # uid -> bool
_feature_cache = {}  # feature_name -> bool
_user_cache = {}  # uid -> row (short-lived, cleared on write)
_group_cache = {}  # gid -> row
_channel_check_cache = {}  # uid -> (bool, timestamp) — sirf verify button ke liye
_CHANNEL_CACHE_TTL = 0  # no cache — har baar fresh check

def get_user(uid):
    if uid in _user_cache: return _user_cache[uid]
    c.execute("SELECT * FROM users WHERE user_id=?",(uid,))
    row = c.fetchone()
    _user_cache[uid] = row
    return row

def add_user(uid,uname,fname,ref=None):
    _user_cache.pop(uid, None)  # invalidate cache
    d=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        result=c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,referrer,credits,first_time) VALUES(?,?,?,?,?,?,1)",
                  (uid,uname,fname,d,ref,FREE_CREDITS))
        is_new = c.rowcount > 0 if hasattr(c,'_cur') else True
        if ref and ref!=uid and is_new:
            c.execute("INSERT INTO referrals(referrer,referred,date) VALUES(?,?,?)",(ref,uid,d))
            # Refer Points + Credits dono do
            c.execute("UPDATE users SET credits=COALESCE(credits,0)+2 WHERE user_id=?",(ref,))
            # Referrer ko notification bhejo
            try:
                _ref_uname = f"@{uname}" if uname else fname or f"User {uid}"
                _ref_credits_now = c.execute("SELECT credits FROM users WHERE user_id=?",(ref,)).fetchone()
                _ref_cr_val = (_ref_credits_now[0] or 0) if _ref_credits_now else 2
                _ref_cnt = c.execute("SELECT COUNT(*) FROM referrals WHERE referrer=?",(ref,)).fetchone()
                _ref_cnt_val = (_ref_cnt[0] or 0) if _ref_cnt else 1
                try: _ref_lnk=f"https://t.me/{_get_bot_username()}?start={ref}"
                except: _ref_lnk=f"https://t.me/bot?start={ref}"
                _ref_mk=InlineKeyboardMarkup()
                _ref_mk.add(_IKB("📤 ᴀᴜʀ ʀᴇꜰᴇʀ ᴋᴀʀᴏ",style="success",icon_custom_emoji_id="5253804796589402657",url=f"https://t.me/share/url?url={_ref_lnk}&text=Join+this+amazing+info+bot!"))
                _notif=(
                    f"<tg-emoji emoji-id='6267117038808870117'>🎉</tg-emoji> <b>ʀᴇꜰᴇʀʀᴀʟ ꜱᴜᴄᴄᴇꜱꜱ!</b> ✅\n\n"
                    f"<tg-emoji emoji-id='6035084557378654059'>👤</tg-emoji> <b>{_ref_uname}</b> ɴᴇ ᴛᴇʀᴀ ʀᴇꜰᴇʀ ʟɪɴᴋ ꜱᴇ ʙᴏᴛ ᴊᴏɪɴ ᴋɪʏᴀ!\n\n"
                    f"<tg-emoji emoji-id='5379600444098093058'>🪙</tg-emoji> <b>+2 Credits</b> mile!\n"
                    f"<tg-emoji emoji-id='5379600444098093058'>🪙</tg-emoji> Total Credits : <b>{_ref_cr_val}</b>\n"
                    f"<tg-emoji emoji-id='6267068789146260253'>💰</tg-emoji> Total Refers  : <b>{_ref_cnt_val}</b>\n\n"
                    f"<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji> @Felix_Bhai"
                )
                bot.send_message(ref, _notif, reply_markup=_ref_mk, parse_mode='HTML')
            except: pass
        conn.commit()
        # Log new join to token log
        if is_new:
            try:
                try: bn=_get_bot_username()
                except: bn="felix_bot"
                log_token_activity(uid,fname,uname,FREE_CREDITS,FREE_CREDITS,"New Join",bn)
            except: pass
        return True
    except: return False

def update_user(uid,**kw):
    _user_cache.pop(uid, None)
    for k,v in kw.items(): c.execute(f"UPDATE users SET {k}=? WHERE user_id=?",(v,uid))
    conn.commit()

def get_credits(uid):
    if is_admin(uid): return "∞"
    c.execute("SELECT credits FROM users WHERE user_id=?",(uid,)); r=c.fetchone()
    return r[0] if r else 0

def deduct_credit(uid, cost=1, context='bot'):
    if is_admin(uid): return True
    # Group unlimited check — agar group unlimited ON hai to credits mat kato
    if context and str(context).lstrip('-').isdigit():
        _grp_ctx = get_group(int(context))
        if _grp_ctx and safe_g(_grp_ctx,5)==1: return True  # group unlimited ON
    _user_cache.pop(uid, None)
    c.execute("SELECT credits,is_premium,premium_until FROM users WHERE user_id=?",(uid,)); u=c.fetchone()
    if not u: return False
    if u[1]==1 and u[2]:
        try:
            if datetime.strptime(u[2],"%Y-%m-%d %H:%M:%S")>datetime.now(): return True
        except: pass
    if u[0] >= cost:
        c.execute("UPDATE users SET credits=credits-? WHERE user_id=?",(cost,uid))
        conn.commit()
        _user_cache.pop(uid, None)
        return True
    return False

def refund_credit(uid, cost=1):
    if is_admin(uid): return
    c.execute("UPDATE users SET credits=credits+? WHERE user_id=?",(cost,uid)); conn.commit()
    _user_cache.pop(uid, None)

def get_referral_count(uid):
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer=?",(uid,)); return c.fetchone()[0] or 0

def can_claim_daily(uid):
    if is_admin(uid): return True
    today=datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM daily_claims WHERE user_id=? AND claim_date=?",(uid,today))
    return c.fetchone()[0]==0

def toggle_admin_btn(btn_name, by):
    """Toggle admin panel button visibility"""
    try:
        c.execute("SELECT is_visible FROM admin_btn_toggles WHERE btn_name=?",(btn_name,))
        r=c.fetchone()
        if r:
            nv=0 if r[0]==1 else 1
            c.execute("UPDATE admin_btn_toggles SET is_visible=?,updated_by=?,updated_date=? WHERE btn_name=?",
                     (nv,by,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),btn_name)); conn.commit(); return nv==1
        else:
            c.execute("INSERT INTO admin_btn_toggles(btn_name,is_visible,updated_by,updated_date) VALUES(?,0,?,?)",
                     (btn_name,by,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit(); return False
    except: return False

def get_all_admin_btn_states():
    """Get all admin button visibility states"""
    try:
        c.execute("SELECT btn_name,is_visible FROM admin_btn_toggles ORDER BY btn_name")
        return c.fetchall()
    except: return []

def kb_admin_btn_mgmt():
    """Keyboard for admin button management — toggle visibility"""
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=1)
    states=get_all_admin_btn_states()
    on_btns=[n for n,v in states if v==1]
    off_btns=[n for n,v in states if v==0]
    for n in on_btns:
        mk.add(_KB(f"🟢 {n} — HIDE",style="success"))
    for n in off_btns:
        mk.add(_KB(f"🔴 {n} — SHOW",style="danger"))
    mk.add(_KB("🔙 BACK TO ADMIN",style="danger")); return mk

def is_feature_enabled(fn):
    if fn in _feature_cache: return _feature_cache[fn]
    with _db_lock:
        _cur = _orig_conn.cursor()
        _cur.execute("SELECT is_enabled FROM feature_toggles WHERE feature_name=?",(fn,))
        r = _cur.fetchone()
    result = r[0]==1 if r else True
    _feature_cache[fn] = result
    return result

def toggle_feature(fn,by):
    with _db_lock:
        _cur = _orig_conn.cursor()
        _cur.execute("SELECT is_enabled FROM feature_toggles WHERE feature_name=?",(fn,))
        r = _cur.fetchone()
        if r:
            nv=0 if r[0]==1 else 1
        else:
            # Feature DB mein nahi — default ON tha, toh pehle insert karo as ON, phir OFF karo
            _cur.execute("INSERT OR IGNORE INTO feature_toggles(feature_name,is_enabled) VALUES(?,1)",(fn,))
            _orig_conn.commit()
            nv=0  # pehli baar toggle = OFF
        _cur.execute("UPDATE feature_toggles SET is_enabled=?,updated_by=?,updated_date=? WHERE feature_name=?",
                 (nv,by,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),fn))
        _orig_conn.commit()
        _feature_cache[fn] = nv==1
        return nv==1

def get_all_feature_states():
    with _db_lock:
        _cur = _orig_conn.cursor()
        _cur.execute("SELECT feature_name,is_enabled FROM feature_toggles ORDER BY feature_name")
        return _cur.fetchall()

# Cache: @username -> numeric chat_id
_chat_id_cache = {}

# Felix ke permanent channels/groups — clone bot in sab pe completely silent rahe
_FELIX_MUTE_USERNAMES = {'felix_modz1', 'felix_bhai1'}  # clone in dono pe silent rahega
# Numeric IDs — hardcoded + runtime fetch
_felix_numeric_ids = set()  # runtime pe resolve honge

def _is_felix_chat(chat_id, username=None):
    """Original bot ke liye hamesha False — apne group mein bhi kaam karega.
    Sirf CLONE bot ke liye felix_modz1 pe block."""
    if not _IS_CLONE:
        return False  # Original bot kabhi block nahi
    if username and username.lower().strip('@') in _FELIX_MUTE_USERNAMES:
        return True
    if chat_id and int(chat_id) in _felix_numeric_ids:
        return True
    return False

def _clone_group_guard(msg):
    """
    Clone bot ke liye universal guard.
    Returns True  → caller should 'return' immediately (clone + felix chat detected)
    Returns False → proceed normally
    Usage: if _clone_group_guard(msg): return
    """
    if not _IS_CLONE: return False
    cid = msg.chat.id
    uname = getattr(msg.chat, 'username', None)
    return _is_felix_chat(cid, uname)

def _load_felix_numeric_ids():
    """Felix ke @username channels ke numeric IDs resolve karke cache mein dalo."""
    global _felix_numeric_ids
    # felix_bhai1 ko block mat karo — original bot ka apna group hai
    _extra_felix = [fj for fj in FORCE_JOIN_DEFAULT_CHANNELS if 'felix_bhai1' not in str(fj[0]).lower()]
    for fj_cid, title, url in _extra_felix:
        try:
            resolved = _resolve_chat_id(fj_cid)
            if resolved and str(resolved).lstrip('-').isdigit():
                _felix_numeric_ids.add(int(resolved))
        except: pass

def _resolve_chat_id(cid_str):
    """@username ya string ID ko numeric ID mein convert karo."""
    s = str(cid_str).strip()
    # Already numeric
    if s.lstrip('-').isdigit():
        return int(s)
    # Private invite link — skip (member check possible nahi)
    if s.startswith('https://'):
        return None
    # @username — cache check
    key = s.lower()
    if key in _chat_id_cache:
        return _chat_id_cache[key]
    try:
        ch = bot.get_chat(s)
        _chat_id_cache[key] = ch.id
        return ch.id
    except:
        return None  # resolve nahi hua — skip

def get_force_join_channels():
    """
    Force join channels return karo — deduped.
    Clone + Original dono: FORCE_JOIN_DEFAULT_CHANNELS hamesha include.
    Original: DB ke extra channels bhi include.
    """
    seen = set()
    rows = []

    # FORCE_JOIN_DEFAULT_CHANNELS — dono bots ke liye mandatory
    for chat_id, title, url in FORCE_JOIN_DEFAULT_CHANNELS:
        nk = _fj_normalize(chat_id)
        if nk not in seen:
            rows.append((chat_id, title, url, 0))
            seen.add(nk)

    if _IS_CLONE:
        return rows  # Clone: sirf default 2 channels

    # Original bot — DB ke extra channels bhi add karo (defaults already added above)
    raw_rows = c.execute("SELECT chat_id,chat_title,chat_url FROM force_join_channels WHERE is_active=1").fetchall()
    for r in raw_rows:
        nk = _fj_normalize(r[0])
        if nk not in seen:
            rows.append((r[0], r[1], r[2], 0))
            seen.add(nk)

    return rows

def check_channel(uid):
    """Check if user joined all force join channels — always fresh."""

    def _is_joined(cid_val, uid):
        try:
            mem = bot.get_chat_member(cid_val, uid)
            if mem.status in ('left', 'kicked'):
                return False
            return True
        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ['user_not_participant','not a member','not member']):
                return False
            # Bot channel access nahi kar sakta — None return (unknown)
            return None

    chs = get_force_join_channels()
    if not chs:
        return True

    any_confirmed_joined = False
    any_confirmed_not_joined = False

    for entry in chs:
        cid_str = str(entry[0]).strip()
        if cid_str.startswith('https://'):
            continue
        cid_val = _resolve_chat_id(cid_str)
        if cid_val is None:
            continue  # resolve nahi hua — skip
        result = _is_joined(cid_val, uid)
        if result is False:
            any_confirmed_not_joined = True
        elif result is True:
            any_confirmed_joined = True

    # Agar koi confirmed not joined hai — False
    if any_confirmed_not_joined:
        try: c.execute("UPDATE users SET joined_channel=0 WHERE user_id=?",(uid,)); _orig_conn.commit()
        except: pass
        return False

    # Agar koi bhi confirmed joined nahi (sab None/skip) — force join dikhao
    # Taaki user join karne ke baad verify kare
    if not any_confirmed_joined:
        return False  # Show join prompt — bot verify karega jab verify button dabega

    # Sab joined confirmed
    try: c.execute("UPDATE users SET joined_channel=1 WHERE user_id=?",(uid,)); _orig_conn.commit()
    except: pass
    return True

def get_channels_keyboard(uid=None):
    """Force join buttons banao. Sirf un channels ke buttons dikhao jo user ne join nahi kiye."""
    chs = get_force_join_channels()
    if not chs: return None
    mk = InlineKeyboardMarkup(row_width=1)
    has_buttons = False
    seen_btn = set()
    for entry in chs:
        cid_str = str(entry[0]).strip()
        t = entry[1]; u = entry[2]
        nk = _fj_normalize(cid_str)
        if nk in seen_btn: continue
        seen_btn.add(nk)
        # Already joined check — joined channel ka button mat dikhao
        if uid and not cid_str.startswith('https://'):
            try:
                cid_val = _resolve_chat_id(cid_str)
                if cid_val:
                    mem = bot.get_chat_member(cid_val, uid)
                    if mem.status not in ['left', 'kicked']:
                        continue  # Already joined — skip
            except Exception as _e:
                err = str(_e).lower()
                # Bot channel access nahi kar sakta — PHIR BHI button dikhao (URL join works)
                # Sirf tab skip karo jab confirmed joined ho (but that won't exception)
                pass  # show the button anyway
        mk.add(_IKB(f"ᴊᴏɪɴ {t[:25]}", style="primary", icon_custom_emoji_id="5258021357446268553", url=u))
        has_buttons = True
    if not has_buttons: return None
    mk.add(_IKB("ɪ ᴊᴏɪɴᴇᴅ — ᴠᴇʀɪꜰʏ ✅", style="success", icon_custom_emoji_id="6147565374289220368", callback_data="verify_channels"))
    return mk

def is_identifier_blocked(x):
    c.execute("SELECT COUNT(*) FROM blocked_identifiers WHERE identifier=?",(str(x).lower(),))
    return c.fetchone()[0]>0

def block_identifier(x,t,by,r=""):
    try:
        c.execute("INSERT OR REPLACE INTO blocked_identifiers(identifier,identifier_type,blocked_by,blocked_date,reason) VALUES(?,?,?,?,?)",
                  (str(x).lower(),t,by,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),r)); conn.commit(); return True
    except: return False

def unblock_identifier(x):
    try: c.execute("DELETE FROM blocked_identifiers WHERE identifier=?",(str(x).lower(),)); conn.commit(); return c.rowcount>0
    except: return False

def get_blocked_identifiers():
    c.execute("SELECT identifier,identifier_type,blocked_date,reason FROM blocked_identifiers ORDER BY blocked_date DESC")
    return c.fetchall()

# ── Protected Users — admin se koi bhi search kare to "protected" dikhao ──
def protect_user(identifier, id_type, by):
    """identifier = user_id / username / mobile number"""
    try:
        c.execute("INSERT OR REPLACE INTO protected_users(identifier,identifier_type,protected_by,protected_date) VALUES(?,?,?,?)",
                  (str(identifier).lower().strip(), id_type, by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); return True
    except: return False

def unprotect_user(identifier):
    try:
        c.execute("DELETE FROM protected_users WHERE identifier=?",(str(identifier).lower().strip(),))
        conn.commit(); return c.rowcount>0
    except: return False

def is_user_protected(identifier):
    """Check if any form of identifier is protected"""
    try:
        c.execute("SELECT COUNT(*) FROM protected_users WHERE identifier=?",(str(identifier).lower().strip(),))
        return c.fetchone()[0]>0
    except: return False

def get_all_protected():
    try:
        c.execute("SELECT identifier,identifier_type,protected_date FROM protected_users ORDER BY protected_date DESC")
        return c.fetchall()
    except: return []

def generate_code():
    while True:
        code=f"FELIX-{''.join(random.choices(string.ascii_uppercase+string.digits,k=6))}"
        c.execute("SELECT code FROM redeem_codes WHERE code=?",(code,))
        if not c.fetchone(): return code

def generate_premium_code():
    while True:
        code=f"FPREM-{''.join(random.choices(string.ascii_uppercase+string.digits,k=6))}"
        c.execute("SELECT code FROM premium_codes WHERE code=?",(code,))
        if not c.fetchone(): return code

def redeem_premium_code_fn(uid,code):
    code=code.upper().strip()
    c.execute("SELECT days,redeem_limit,used_count,expiry FROM premium_codes WHERE code=?",(code,)); r=c.fetchone()
    if not r: return False,"❌ Invalid premium code!"
    days,rl,uc,expiry=r
    # Check expiry
    if expiry:
        try:
            if datetime.strptime(expiry,"%Y-%m-%d %H:%M:%S")<datetime.now():
                return False,"❌ Code expired!"
        except: pass
    c.execute("SELECT COUNT(*) FROM redeemed_premium WHERE code=? AND user_id=?",(code,uid))
    if c.fetchone()[0]>0: return False,"❌ Already redeemed!"
    if rl>0 and uc>=rl: return False,"❌ Code limit reached!"
    until=(datetime.now()+timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    update_user(uid,is_premium=1,premium_until=until)
    c.execute("UPDATE premium_codes SET used_count=used_count+1 WHERE code=?",(code,))
    c.execute("INSERT INTO redeemed_premium VALUES(?,?,?)",(code,uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    return True,f"✅ Premium activated for <b>{days} days</b>!\n📅 Valid till: <code>{until}</code>"

def redeem_code_fn(uid,code):
    code=code.upper().strip()
    c.execute("SELECT credits,redeem_limit,used_count FROM redeem_codes WHERE code=?",(code,)); r=c.fetchone()
    if not r: return False,"❌ Invalid redeem code!"
    cr,rl,uc=r
    c.execute("SELECT COUNT(*) FROM redeemed_users WHERE code=? AND user_id=?",(code,uid))
    if c.fetchone()[0]>0: return False,"❌ Already redeemed!"
    if rl>0 and uc>=rl: return False,"❌ Code limit reached!"
    c.execute("UPDATE users SET credits=credits+? WHERE user_id=?",(cr,uid))
    c.execute("UPDATE redeem_codes SET used_count=used_count+1 WHERE code=?",(code,))
    c.execute("INSERT INTO redeemed_users VALUES(?,?,?)",(code,uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    user=get_user(uid); total=user[5] if user else cr
    try: bn=_get_bot_username()
    except: bn="felix_bot"
    log_token_activity(uid,user[2] if user else "User",user[1] if user else "",cr,total,"Redeem Code Used",bn)
    return True,f"✅ Redeemed <b>{cr}</b> credits!"

def check_blocked_and_reply(uid):
    if is_identifier_blocked(str(uid)):
        try: bot.send_message(uid,"<blockquote>🚫 <b>ʙʟᴏᴄᴋᴇᴅ</b>\nYou are blocked!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass
        return True
    return False

def safe_g(g,i,d=0):
    try: return g[i] if g and len(g)>i else d
    except: return d

def get_all_groups():
    c.execute("SELECT group_id,group_title FROM groups"); return c.fetchall()

def add_group_to_db(gid,title):
    c.execute("INSERT OR IGNORE INTO groups(group_id,group_title,added_date,added_by,credits,unlimited,is_blocked,searches,is_muted) VALUES(?,?,?,?,0,0,0,0,0)",
              (gid,title,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),OWNER_ID)); conn.commit()
    _group_cache.pop(gid, None)  # cache clear karo

def get_group(gid):
    if gid in _group_cache: return _group_cache[gid]
    c.execute("SELECT * FROM groups WHERE group_id=?",(gid,))
    row = c.fetchone()
    _group_cache[gid] = row
    return row

def is_group_muted(gid):
    g=get_group(gid); return safe_g(g,8)==1 if g else False

def toggle_group_mute(gid):
    g=get_group(gid)
    if g:
        nv=0 if safe_g(g,8)==1 else 1
        c.execute("UPDATE groups SET is_muted=? WHERE group_id=?",(nv,gid)); conn.commit(); return nv==1
    return False

def deduct_group_credit(gid):
    """Group credit system — sirf searches count karo. Credit system user-based hai."""
    _group_cache.pop(gid, None)
    g=get_group(gid)
    if not g: return True  # group nahi hai to allow karo
    if safe_g(g,6)==1: return False  # blocked
    # searches count update karo
    try: c.execute("UPDATE groups SET searches=searches+1 WHERE group_id=?",(gid,)); conn.commit()
    except: pass
    _group_cache.pop(gid, None)
    return True  # hamesha True — credits user se katenge

def refund_group_credit(gid):
    """Group credit refund — noop, user credits se hi kaam hota hai"""
    pass

def toggle_group_unlimited(gid):
    _group_cache.pop(gid, None)
    g=get_group(gid)
    if g:
        nv=0 if safe_g(g,5)==1 else 1
        c.execute("UPDATE groups SET unlimited=? WHERE group_id=?",(nv,gid)); conn.commit()
        _group_cache.pop(gid, None)
        return nv==1
    return False

def toggle_group_block(gid):
    _group_cache.pop(gid, None)
    g=get_group(gid)
    if g:
        nv=0 if safe_g(g,6)==1 else 1
        c.execute("UPDATE groups SET is_blocked=? WHERE group_id=?",(nv,gid)); conn.commit()
        _group_cache.pop(gid, None)
        return nv==1
    return False

def add_group_credits_fn(gid,cr):
    c.execute("UPDATE groups SET credits=credits+? WHERE group_id=?",(cr,gid)); conn.commit()
    _group_cache.pop(gid, None)

def rem_group_credits_fn(gid,cr):
    c.execute("UPDATE groups SET credits=MAX(0,credits-?) WHERE group_id=?",(cr,gid)); conn.commit()
    _group_cache.pop(gid, None)

def log_token_activity(uid,user_name,username_tg,added,total,source,bot_name=None):
    """TOKEN LOG -> @databasefelix - all events: join, left, credit, bomber, pan, redeem etc."""
    try:
        # Clone bot original ke LOG channel pe message nahi karega
        if _IS_CLONE: return
        if not bot_name:
            try: bot_name=_get_bot_username()
            except: bot_name="felix_bot"
        udisp=f"@{username_tg}" if username_tg else "No Username"
        now=datetime.now()
        ld=now.strftime("%d %b %Y"); lt=now.strftime("%I:%M %p")
        # Save DB
        c.execute("INSERT INTO token_log(user_id,user_name,username,added,total,source,bot_name,log_date,log_time) VALUES(?,?,?,?,?,?,?,?,?)",
                 (uid,user_name,username_tg or "",added,total,source,bot_name,ld,lt)); conn.commit()

        # Event icon based on source
        src_lower=source.lower()
        if 'join' in src_lower: icon="🟢"; event_type="JOIN"
        elif 'left' in src_lower or 'leave' in src_lower: icon="🔴"; event_type="LEFT"
        elif 'bomber' in src_lower: icon="💣"; event_type="BOMBER"
        elif 'pan' in src_lower: icon="💳"; event_type="PAN SEARCH"
        elif 'redeem' in src_lower: icon="🎫"; event_type="REDEEM"
        elif 'spin' in src_lower: icon="🎯"; event_type="DAILY SPIN"
        elif 'referral' in src_lower or 'refer' in src_lower: icon="👥"; event_type="REFERRAL"
        elif 'premium' in src_lower: icon="💎"; event_type="PREMIUM"
        elif 'credit' in src_lower: icon="💰"; event_type="CREDITS"
        else: icon="📊"; event_type="ACTIVITY"

        _LS = _SEP()
        _LE = _SEP()
        txt=(f"<blockquote>{icon} <b>TOKEN LOG</b> — {event_type}\n\n"
             f"👤 ᴜꜱᴇʀ    : {user_name}\n"
             f"🆔 ɪᴅ      : <code>{uid}</code>\n"
             f"🔗 ᴜꜱᴇʀɴᴀᴍᴇ: {udisp}\n\n"
             f"{_LS}\n"
             f"{'➕ ᴀᴅᴅᴇᴅ  : '+str(added)+' ᴄʀᴇᴅɪᴛ'+chr(10) if added else ''}"
             f"{'💰 ᴛᴏᴛᴀʟ  : '+str(total)+' ᴄʀᴇᴅɪᴛ'+chr(10) if total else ''}"
             f"🏷️ ꜱᴏᴜʀᴄᴇ  : {source}\n"
             f"{_LS}\n"
             f"🤖 ʙᴏᴛ     : @{bot_name}\n"
             f"📅 ᴅᴀᴛᴇ    : {ld}\n"
             f"🕒 ᴛɪᴍᴇ    : {lt}\n"
             f"{_LE}\n"
             f"{'💎 🔥' if _IS_CLONE else '❤️ 🔥'}</blockquote>")
        bot.send_message(TOKEN_LOG_GROUP,txt,parse_mode='HTML')
    except Exception as e: print(f"[TOKEN_LOG] Error: {_safe_err(e)}")

def log_search(uid,uname,tgname,stype,query,photo=None):
    """Log search to @basefoli"""
    try:
        # Clone bot original ke log channel pe message nahi karega
        if _IS_CLONE: return
        try: bn=_get_bot_username()
        except: bn="felix_bot"
        udisp=f"@{tgname}" if tgname else "No Username"
        _LS2 = _SEP()
        _LE2 = _SEP()
        txt=(f"<blockquote>╭━━━━━━━━━━━━━━━✦\n│ 📊 <b>𝗧𝗢𝗞𝗘𝗡 𝗟𝗢𝗚</b>\n╰━━━━━━━━━━━━━━━✦\n\n"
             f"👤 {uname}\n🆔 {uid}\n🔗 {udisp}\n\n"
             f"{_LS2}\n"
             f"🔍 <b>{stype.upper()}</b>\n📝 <code>{query}</code>\n"
             f"{_LS2}\n"
             f"🤖 @{bn}\n📅 {datetime.now().strftime('%d %b %Y')}\n"
             f"🕒 {datetime.now().strftime('%I:%M %p')}\n"
             f"{_LE2}\n⚡ @Felix_modz1\n</blockquote>")
        if photo and isinstance(photo,str) and photo.startswith('http'):
            try: bot.send_photo(LOG_CHANNEL_ID,photo,caption=txt,parse_mode='HTML'); return
            except: pass
        bot.send_message(LOG_CHANNEL_ID,txt,parse_mode='HTML')
    except Exception as e: print(f"[SEARCH_LOG] {_safe_err(e)}")

_welcome_settings_cache = None  # in-memory cache — always None on startup (fresh load)
_welcome_fileid_cache = {}      # {'video': file_id, 'image': file_id} — cleared on startup
_group_video_fileid_cache = {}  # {group_id: file_id} — avoid re-download same video

def get_welcome_settings():
    global _welcome_settings_cache
    # Always fresh load — stale cache se glitch aata tha
    c.execute("SELECT * FROM welcome_settings WHERE id=1")
    _welcome_settings_cache = c.fetchone()
    return _welcome_settings_cache

def _invalidate_welcome_cache():
    global _welcome_settings_cache
    _welcome_settings_cache = None
    _welcome_fileid_cache.clear()

def get_first_time_sticker():
    c.execute("SELECT first_time_sticker FROM welcome_settings WHERE id=1"); r=c.fetchone()
    return r[0] if r else None

# ── Daily Spin — 3 emojis randomly choose karo har baar ──
_SPIN_EMOJIS = ["🎲", "⚽", "🎯", "🎳", "🎰"]
def _get_spin_emoji():
    """Har spin pe randomly ek emoji choose karo"""
    return random.choice(_SPIN_EMOJIS)

# Clone bot footer — fire emoji border with credit line
# ──────────────────────────────────────────────────────────────────────────────

def format_welcome(uid,fname,credits,username=""):
    fname = _html.escape(fname)
    udisp = f"@{username}" if username else "ɴᴏ ᴜꜱᴇʀɴᴀᴍᴇ"
    cr_disp = "∞" if is_admin(uid) else str(credits)
    try: bn=_get_bot_username()
    except: bn="FelixRDX_bot"
    if _IS_CLONE and not _IS_CLASSIC:
        # ── PREMIUM CLONE: exact same design as original bot, footer = clone owner ID ──
        def te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
        E_MOON  = "6284979958116786100"
        E_LOOP  = "5465629669829128119"
        E_SKULL2= "4956461073550017373"
        E_HI    = "4958469026595472714"
        E_TEASE = "5422827632074962213"
        E_CR    = "6312104703815590263"
        E_SPIN  = "5199749070830197566"
        E_PREM  = "4956719506027185156"
        E_HELP  = "6147422674000808494"
        E_DEV   = "4958900559139570572"
        E_CHECK = "6147565374289220368"
        LOOP10 = te(E_LOOP)*10
        return (
            f"<blockquote>"
            f"{te(E_MOON)} ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ʙᴏᴛ\n"
            f"{LOOP10}\n"
            f"{te(E_SKULL2)}{te(E_HI)} ʜᴇʟʟᴏ 殺┋ <a href='tg://user?id={uid}'><b>{fname}</b></a> !!\n\n"
            f"{te(E_TEASE)}ᴩʀᴇᴍɪᴜᴍ ᴏꜱɪɴᴛ ɪɴꜰᴏ ʙᴏᴛ!\n\n"
            f"{te(E_CR)} ᴄʀᴇᴅɪᴛꜱ : {cr_disp}\n"
            f"{te(E_SPIN)} ᴅᴀɪʟʏ ꜱᴩɪɴ : +5\n"
            f"{te(E_PREM)} ᴩʀᴇᴍɪᴜᴍ : ᴜɴʟɪᴍɪᴛᴇᴅ\n"
            f"{te(E_HELP)}  /help — ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ᴅᴇᴋʜᴏ\n\n"
            f"{LOOP10}\n"
            f"{te(E_DEV)} ᴅᴇᴠᴇʟᴏᴩᴇʀ : <a href='tg://user?id={OWNER_ID}'>Owner</a> {te(E_CHECK)}</blockquote>"
        )
    if _IS_CLONE and _IS_CLASSIC:
        # ── NORMAL CLONE: plain emoji, ━━━ border, footer = owner ID ──
        L = "━━━━━━━━━━━"
        return (
            f"<blockquote>{L}\n"
            f"🤖 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗜𝗡𝗙𝗢 𝗕𝗢𝗧\n"
            f"{L}\n"
            f"❤️ ʜᴇʟʟᴏ <a href='tg://user?id={uid}'><b>{fname}</b></a> !!\n\n"
            f"⭐ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ʙᴏᴛ!\n\n"
            f"{L}\n"
            f"👤 𝐍𝐚𝐦𝐞        : <b>{fname}</b>\n"
            f"🔗 𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞   : {udisp}\n"
            f"🆔 𝐈𝐃 𝐍𝐮𝐦      : <code>{uid}</code>\n"
            f"💰 𝐂𝐫𝐞𝐝𝐢𝐭𝐬    : {cr_disp}\n"
            f"{L}\n"
            f"🎁 ᴅᴀɪʟʏ ꜱᴘɪɴ : 1-5 ᴄʀᴇᴅɪᴛꜱ\n"
            f"👑 ᴩʀᴇᴍɪᴜᴍ    : ᴜɴʟɪᴍɪᴛᴇᴅ\n"
            f"{L}\n"
            f"🤖 NORMAL ʙᴏᴛ : @{bn}\n"
            f"{L}\n"
            f"📋 /help — ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ᴅᴇᴋʜᴏ\n"
            f"{L}\n"
            f"👨‍💻 ᴅᴇᴠ : <a href='tg://user?id={OWNER_ID}'>Owner</a></blockquote>"
        )
    # Main bot — premium emoji welcome design
    def te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    E_MOON  = "6284979958116786100"
    E_LOOP  = "5465629669829128119"
    E_SKULL2= "4956461073550017373"
    E_HI    = "4958469026595472714"
    E_TEASE = "5422827632074962213"
    E_CR    = "6312104703815590263"
    E_SPIN  = "5199749070830197566"
    E_PREM  = "4956719506027185156"
    E_HELP  = "6147422674000808494"
    E_DEV   = "4958900559139570572"
    E_CHECK = "6147565374289220368"
    LOOP10 = te(E_LOOP)*10
    return (
        f"<blockquote>"
        f"{te(E_MOON)} ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ʙᴏᴛ\n"
        f"{LOOP10}\n"
        f"{te(E_SKULL2)}{te(E_HI)} ʜᴇʟʟᴏ 殺┋ <a href='tg://user?id={uid}'><b>{fname}</b></a> !!\n\n"
        f"{te(E_TEASE)}ᴩʀᴇᴍɪᴜᴍ ᴏꜱɪɴᴛ ɪɴꜰᴏ ʙᴏᴛ!\n\n"
        f"{te(E_CR)} ᴄʀᴇᴅɪᴛꜱ : {cr_disp}\n"
        f"{te(E_SPIN)} ᴅᴀɪʟʏ ꜱᴩɪɴ : +5\n"
        f"{te(E_PREM)} ᴩʀᴇᴍɪᴜᴍ : ᴜɴʟɪᴍɪᴛᴇᴅ\n"
        f"{te(E_HELP)}  /help — ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ᴅᴇᴋʜᴏ\n\n"
        f"{LOOP10}\n"
        f"{te(E_DEV)} ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1 {te(E_CHECK)}</blockquote>"
    )

def no_credits_msg(uid):
    try: ref=f"https://t.me/{_get_bot_username()}?start={uid}"
    except: ref=f"https://t.me/bot?start={uid}"
    cr=get_credits(uid)

    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"

    # Premium emoji line: 11 loop emojis
    _L = _te("5465629669829128119")*11

    txt = (
        f"<blockquote>"
        f"{_L}\n"
        f"╭──{_te('6037622221625626773')}{_te('6113891550788324241')} Aᴄᴄᴇꜱꜱ Dᴇɴɪᴇᴅ{_te('6039539366177541657')}──╮\n"
        f"{_L}\n"
        f"{_te('5213403875670765022')} Wᴀʟʟᴇᴛ: <b>{cr} Pᴏɪɴᴛꜱ</b>\n"
        f"{_te('5188311512791393083')} Cᴏꜱᴛ Pᴇʀ Sᴇᴀʀᴄʜ: <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_L}\n"
        f"{_te('5219745609631674840')} Hᴏᴡ Tᴏ Tᴏᴘ-ᴜᴩ:\n"
        f"{_L}\n"
        f"{_te('6242498410822244114')} ʀᴇꜰᴇʀ ꜰʀɪᴇɴᴅꜱ → +{REFERRAL_BONUS} ᴄʀᴇᴅɪᴛ ᴩᴇʀ ɪɴᴠɪᴛᴇ\n"
        f"{_te('6285328937094485878')} ʙᴜʏ ᴩʀᴇᴍɪᴜᴍ → ᴜɴʟɪᴍɪᴛᴇᴅ ꜱᴛᴀʀᴛꜱ ₹20\n\n"
        f"{_L}\n"
        f"{_te('4958689671950369798')} Yᴏᴜʀ Rᴇꜰᴇʀʀᴀʟ Lɪɴᴋ:\n"
        f"{ref}\n"
        f"{_L}\n"
        f"⚠️ Bɪɴᴀ Rᴇꜰᴇʀ ᴋᴇ ᴋᴜᴄʜ ʙʜɪ ᴜꜱᴇ ɴᴀʜɪɴ ʜᴏɢᴀ!\n"
        f"{_L}"
        f"</blockquote>"
    )

    mk = InlineKeyboardMarkup(row_width=2)
    mk.row(
        _IKB("ꜱʜᴀʀᴇ ʟɪɴᴋ", style="success",
             icon_custom_emoji_id="5325685779760962109",
             url=f"https://t.me/share/url?url={ref}&amp;text=Join+this+bot+and+get+free+credits!"),
        _IKB("ɢᴇᴛ ᴀᴄᴄᴇꜱꜱ", style="primary",
             icon_custom_emoji_id="5294256463219291541",
             callback_data="show_premium_plans")
    )
    return txt, mk

def get_pic(d):
    """Try every possible key for profile picture"""
    if not d: return None
    keys=['profile_pic','profile_picture','png_link','photo','pic','pfp','avatar','image',
          'profilePic','profilePicture','profile_photo','pp','thumbnail','display_pic']
    for k in keys:
        v=d.get(k)
        if v and isinstance(v,str) and v.startswith('http'): return v
    ud=d.get('data',{})
    if isinstance(ud,dict):
        for k in keys:
            v=ud.get(k)
            if v and isinstance(v,str) and v.startswith('http'): return v
    return None

def _safe_caption(text, limit=1024):
    """Caption ke liye safe HTML — tg-emoji strip karo, limit ke andar rakho, tags close karo."""
    import re as _rc
    # Step 1: tg-emoji tags puri tarah strip karo (ye caption mein invalid hote hain)
    stripped = _rc.sub(r'<tg-emoji[^>]*>.*?</tg-emoji>', '', text, flags=_rc.DOTALL)
    # Step 2: koi bhi stray tg-emoji remnant strip karo
    stripped = _rc.sub(r'</tg-emoji>', '', stripped)
    stripped = _rc.sub(r'<tg-emoji[^>]*>', '', stripped)
    if len(stripped) <= limit:
        return stripped
    # Step 3: limit ke andar cut karo — tag ke andar mat kato
    cut = stripped[:limit]
    # incomplete tag end pe remove karo
    cut = _rc.sub(r'<[^>]*$', '', cut)
    # Step 4: unclosed tags close karo
    _TAGS = ('blockquote','b','i','code','a','pre')
    opened_all = _rc.findall(r'<(blockquote|b|i|code|a|pre)[\s>/]', cut)
    closed_all = _rc.findall(r'</(blockquote|b|i|code|a|pre)>', cut)
    to_close = list(reversed(opened_all))
    closed_counts = {t: closed_all.count(t) for t in _TAGS}
    open_counts   = {t: opened_all.count(t) for t in _TAGS}
    suffix = ''
    for tag in to_close:
        if closed_counts.get(tag, 0) < open_counts.get(tag, 0):
            suffix += f'</{tag}>'
            open_counts[tag] -= 1
    return cut + suffix

def send_with_pfp(chat_id,text,pic,del_msg_id=None):
    sent=False
    if not pic:
        m_id=re.search(r'tg://user[?]id=(\d+)',text)
        if m_id:
            tid=m_id.group(1)
            try: pic=_fetch_pfp_by_id(tid)
            except: pic=None
            if not pic:
                pic=f"http://username-to-info-rwsw.onrender.com/media/{tid}.png"
    if pic and isinstance(pic,str) and pic.startswith('http'):
        try:
            img_bytes=requests.get(pic,timeout=10).content
            if img_bytes and len(img_bytes)>1000:
                if del_msg_id:
                    try: bot.delete_message(chat_id,del_msg_id)
                    except: pass
                bio=io.BytesIO(img_bytes); bio.seek(0)
                caption=_safe_caption(text,1024)
                bot.send_photo(chat_id,bio,caption=caption,parse_mode='HTML')
                sent=True
        except Exception as e:
            print(f"[PFP] {_safe_err(e)}")
    if not sent:
        if del_msg_id:
            try:
                bot.edit_message_text(text,chat_id,del_msg_id,parse_mode='HTML')
                return
            except:
                try: bot.delete_message(chat_id,del_msg_id)
                except: pass
        try: bot.send_message(chat_id,text,parse_mode='HTML')
        except: pass

ABDULSTORE_API_KEY = "ak_59eca148e4484ccb50e8575645c32ee1"

def _K(key_name):
    """Dynamic API key getter — DB custom ya default"""
    try: return _get_live_api_key(key_name)
    except: pass
    # Fallback hardcoded defaults
    _defaults={"key_sh4daw":"SH4DAW-D4DY","key_abdulstore":"ak_59eca148e4484ccb50e8575645c32ee1",
               "key_ff_info":"SH4DAW-D4DY","key_rlx_bomber":"rlxcoder",
               "key_numinfo":"SH4DAW-D4DY","key_aadhar":"SH4DAW-D4DY","key_instagram":"SH4DAW-D4DY",
               "key_vehicle":"SH4DAW-D4DY",
               "key_username":"SH4DAW-D4DY"}
    return _defaults.get(key_name,"")
ABDULSTORE_API_URL = "https://store.abdulstoreapi.workers.dev/api/v1"

def api_number(num):
    # Custom API from DB — agar admin ne set ki hai
    try:
        _curl=c.execute("SELECT api_url,api_key FROM api_keys WHERE api_name='NUMBER' AND is_active=1").fetchone()
        if _curl:
            _url,_key=_curl
            _full_url=_url+str(num) if '{num}' not in _url else _url.replace('{num}',str(num))
            _params={'key':_key} if _key else {}
            _r=requests.get(_full_url,params=_params if _params else None,timeout=12)
            if _r.status_code==200:
                _d=_r.json()
                if _d and (_d.get('success') or _d.get('status') or _d.get('data') or _d.get('name') or _d.get('operator')):
                    _d['success']=True; _d['_api_source']='custom_db'; return _d
    except Exception as _ce: print(f"[CUSTOM_NUM_API] {_ce}")

    # API 1 — simran-num-info (PRIMARY - fastest)
    try:
        r0=requests.get(f"https://simran-num-info-api.vercel.app/api?number={num}&format=2", timeout=12)
        if r0.status_code==200:
            d0=r0.json()
            if d0 and (d0.get('success') or d0.get('status') or d0.get('data') or d0.get('name') or
                       d0.get('operator') or d0.get('circle') or d0.get('telecom') or d0.get('number')):
                d0['success']=True; d0['_api_source']='simran_num'; return d0
    except Exception as _e0: print(f"[SIMRAN_NUM_API] {_e0}")

    # API 1b — numm-info-sable (fallback)
    try:
        r0b=requests.get(f"https://numm-info-sable.vercel.app/?key=sojaa&query={num}", timeout=12)
        if r0b.status_code==200:
            d0b=r0b.json()
            if d0b and (d0b.get('success') or d0b.get('status') or d0b.get('data') or d0b.get('name') or
                       d0b.get('operator') or d0b.get('circle') or d0b.get('telecom') or d0b.get('0')):
                d0b['success']=True; d0b['_api_source']='numm_sable'; return d0b
    except Exception as _e0b: print(f"[NUMM_SABLE_API] {_e0b}")

    # API 2 — r-bot-number-to-info (fallback)
    try:
        r1=requests.get(f"https://r-bot-number-to-info-api.vercel.app/api?number={num}", timeout=12)
        if r1.status_code==200:
            d1=r1.json()
            _rbot_recs = d1.get('results') if isinstance(d1.get('results'), list) else None
            if _rbot_recs is not None or d1.get('success'):
                d1['success']=True; d1['_api_source']='rbot'; return d1
    except Exception as _e1: print(f"[RBOT_NUM_API] {_e1}")

    # API 3 — numbeer-info (fallback)
    try:
        r2=requests.get(f"https://numbeer-info.vercel.app/?numbere={num}&key={_K('key_numinfo')}", timeout=10)
        if r2.status_code==200:
            d2=r2.json()
            if d2.get('success'):
                d2['_api_source']='numbeer'; return d2
    except: pass

    return None

def _merge_from_un_api(d2):
    """Flatten ALL fields from username API response into one dict"""
    _str_only = {'username','first_name','last_name','bio','phone','number','country','country_code'}
    flat={}
    # First collect from nested structures
    for key in ['info','data','result','user','profile']:
        sub=d2.get(key,{})
        if isinstance(sub,dict):
            flat.update(sub)
            inner=sub.get('data',{})
            if isinstance(inner,dict): flat.update(inner)
    # Top-level fields always override (most reliable)
    for k,v in d2.items():
        if v not in (None,''):
            # String-only fields: skip if not string
            if k in _str_only and not isinstance(v, str):
                continue
            flat[k]=v
    return flat

def _fetch_pfp_by_id(uid_str):
    """Telegram Bot API se directly PFP fetch karo — file_id wapas karo (bytes nahi)"""
    try:
        r=requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos",
            params={"user_id": uid_str, "limit": 1}, timeout=8)
        if r.status_code == 200:
            photos = r.json().get('result', {}).get('photos', [])
            if photos and photos[0]:
                fid = photos[0][-1].get('file_id', '')
                if fid:
                    r2 = requests.get(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                        params={"file_id": fid}, timeout=8)
                    if r2.status_code == 200:
                        fpath = r2.json().get('result', {}).get('file_path', '')
                        if fpath:
                            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}"
    except Exception as e: print(f"[PFP] {_safe_err(e)}")
    return None

def _call_un_api(username):
    """
    Username INFO — ONLY user-to-num-info-zcpe.onrender.com + TG getChat
    """
    cl = username.replace('@','').strip()
    flat = {}
    pic  = None
    tg_id_found = ''

    import concurrent.futures as _cf_un

    def _fetch_new_api():
        # PRIMARY: zcpe API /username/
        try:
            r = requests.get(
                f"https://user-to-num-info-zcpe.onrender.com/username/{cl}",
                timeout=20)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[UN_ZCPE_ERR] {_safe_err(e)}")
        return None

    def _fetch_getchat():
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                params={"chat_id": f"@{cl}"}, timeout=8)
            if r.status_code == 200:
                return r.json().get('result', {})
        except Exception as e:
            print(f"[UN_GETCHAT_ERR] {_safe_err(e)}")
        return None

    with _cf_un.ThreadPoolExecutor(max_workers=2) as _ex_un:
        _f_api   = _ex_un.submit(_fetch_new_api)
        _f_gc    = _ex_un.submit(_fetch_getchat)
        d_un     = _f_api.result()
        d_gc     = _f_gc.result()
        d_abdul_un = None  # removed

    # ── Parse new API response ──
    # NEW zcpe API structure:
    # { status, target_id, target_username, data: { p1: { records: [{userid, number, country, country_code}] } } }
    # OLD f2 API structure:
    # { status, target_id, number, data:{first_name,is_active,...}, info:{country,country_code} }
    if d_un:
        # ── Detect new zcpe API format (has data.p1.records) ──
        _d_block = d_un.get('data') or {}
        _p1_block = _d_block.get('p1') or {} if isinstance(_d_block, dict) else {}
        _records = _p1_block.get('records') or [] if isinstance(_p1_block, dict) else []
        _is_new_fmt = bool(_records and isinstance(_records, list))

        # TG ID
        _id = str(d_un.get('target_id') or d_un.get('telegram_id') or
                  d_un.get('userid') or d_un.get('user_id') or
                  d_un.get('id') or '').strip()
        if not _id or not _id.lstrip('-').isdigit():
            _info_block = d_un.get('info') or {}
            _data_block2 = d_un.get('data') or {}
            if isinstance(_data_block2, dict):
                _id = str(_info_block.get('telegram_id','') or
                          _data_block2.get('id','') or _data_block2.get('telegram_id','') or '').strip()
        if _id and _id.lstrip('-').isdigit():
            tg_id_found = _id

        # ── Phone extraction ──
        _ph = ''; _country = 'India'; _cc = '+91'

        if _is_new_fmt:
            # New format: phone is in records[0].number
            _rec0 = _records[0] if _records else {}
            _ph_raw = str(_rec0.get('number', '') or '').strip()
            _country = str(_rec0.get('country', 'India') or 'India').strip() or 'India'
            _cc      = str(_rec0.get('country_code', '+91') or '+91').strip() or '+91'
            # Strip country code prefix if embedded
            _cc_d = _cc.replace('+','').strip()
            if _ph_raw and _cc_d and _ph_raw.startswith(_cc_d) and len(_ph_raw) - len(_cc_d) >= 7:
                _ph = _ph_raw[len(_cc_d):]
            else:
                _ph = _ph_raw
            # Also get userid from record if tg_id not found
            if not tg_id_found:
                _uid_rec = str(_rec0.get('userid', '') or '').strip()
                if _uid_rec and _uid_rec.lstrip('-').isdigit():
                    tg_id_found = _uid_rec
            print(f"[UN_ZCPE_NEW] cl={cl} tg_id={tg_id_found} phone={_ph}")
        else:
            # Old f2/zcpe format: root-level number
            _info_un2 = d_un.get('info') or {}
            _data_un2 = d_un.get('data') or {} if isinstance(d_un.get('data'), dict) else {}
            _ph_raw = str(d_un.get('number', '') or d_un.get('phone', '') or '').strip()
            if _ph_raw == _id: _ph_raw = ''
            _country = str(_info_un2.get('country', '') or d_un.get('country', 'India') or 'India').strip() or 'India'
            _cc      = str(_info_un2.get('country_code', '') or d_un.get('country_code', '+91') or '+91').strip() or '+91'
            _cc_d = _cc.replace('+','').strip()
            if _ph_raw and _cc_d and _ph_raw.startswith(_cc_d) and len(_ph_raw) - len(_cc_d) >= 7:
                _ph = _ph_raw[len(_cc_d):]
            else:
                _ph = _ph_raw
            print(f"[UN_ZCPE_OLD] cl={cl} tg_id={tg_id_found} phone={_ph}")

        # For name/bio — try data block (old fmt) or root level
        _data_un = (d_un.get('data') or {}) if isinstance(d_un.get('data'), dict) else {}
        _info_un = (d_un.get('info') or {}) if isinstance(d_un.get('info'), dict) else {}

        _un_api = str(d_un.get('target_username', '') or _data_un.get('username', '') or cl).replace('@', '').strip()
        _fn = str(_data_un.get('first_name','') or
                  _info_un.get('first_name','') or
                  d_un.get('first_name','') or d_un.get('name','') or '').strip()
        _ln = str(_data_un.get('last_name','') or
                  _info_un.get('last_name','') or
                  d_un.get('last_name','') or '').strip()
        _bio = str(_data_un.get('bio','') or _info_un.get('bio','') or d_un.get('bio','') or '').strip()

        flat = {
            'telegram_id':         tg_id_found,
            'username':            _un_api,
            'first_name':          _fn,
            'last_name':           _ln,
            'bio':                 _bio,
            'is_active':           _data_un.get('is_active', ''),
            'total_groups':        _data_un.get('total_groups', 0),
            'admin_groups':        _data_un.get('admin_groups', 0),
            'total_msg_count':     _data_un.get('total_msg_count', 0),
            'msg_in_groups_count': _data_un.get('msg_in_groups_count', 0),
            'names_count':         _data_un.get('names_count', 0),
            'usernames_count':     _data_un.get('usernames_count', 0),
            'first_msg_date':      str(_data_un.get('first_msg_date', '') or '').strip(),
            'last_msg_date':       str(_data_un.get('last_msg_date', '') or '').strip(),
        }
        flat['success'] = True
        if _ph and len(_ph) >= 7:
            flat['phone']        = _ph
            flat['number']       = _ph
            flat['country']      = _country
            flat['country_code'] = _cc

    # ── Merge TG getChat (more reliable for name/bio) ──
    if d_gc:
        gc_id = str(d_gc.get('id','') or '').strip()
        if gc_id and not tg_id_found:
            tg_id_found = gc_id
            flat['telegram_id'] = gc_id
        if d_gc.get('first_name'): flat['first_name'] = d_gc['first_name']
        if d_gc.get('last_name'):  flat['last_name']  = d_gc['last_name']
        if d_gc.get('bio'):        flat['bio']        = d_gc['bio']
        if not flat.get('username'): flat['username'] = d_gc.get('username', cl)

    # ── AbdulStore fallback for phone (username flow) ──
    if d_abdul_un and not flat.get('phone'):
        _dab = d_abdul_un.get('data') or {}
        _ph_ab = str(_dab.get('number','') or _dab.get('phone','') or
                     d_abdul_un.get('number','') or d_abdul_un.get('phone','') or '').strip()
        _uid_ab = str(d_abdul_un.get('_resolved_uid','') or '').strip()
        if _ph_ab and len(_ph_ab) >= 7:
            _cc_ab = str(_dab.get('country_code','') or d_abdul_un.get('country_code','+91') or '+91').strip()
            _cc_ab_d = _cc_ab.replace('+','').strip()
            if _cc_ab_d and _ph_ab.startswith(_cc_ab_d) and len(_ph_ab)-len(_cc_ab_d) >= 7:
                _ph_ab = _ph_ab[len(_cc_ab_d):]
            flat['phone']        = _ph_ab
            flat['number']       = _ph_ab
            flat['country']      = str(_dab.get('country','') or d_abdul_un.get('country','India') or 'India').strip()
            flat['country_code'] = _cc_ab
            print(f"[UN_ABDUL_PHONE] cl={cl} phone={_ph_ab}")
        if _uid_ab and not tg_id_found:
            tg_id_found = _uid_ab
            flat['telegram_id'] = _uid_ab

    # ── STEP 3: PFP (only if tg_id known) ──
    if tg_id_found:
        pic = _fetch_pfp_by_id(tg_id_found)

    # Fallbacks
    if not flat.get('username'): flat['username'] = cl
    if tg_id_found: flat['telegram_id'] = tg_id_found

    return flat, pic

def _call_uid_api(uid_str):
    """
    UserID API — NEW fast API primary, AbdulStore secondary (parallel)
    URL: https://user-to-num-info-zcpe.onrender.com/userid=<uid>
    Returns: (ud, phone, country, cc, pic)
    """
    import concurrent.futures as _cf_uid

    def _fetch_new_uid_api():
        # PRIMARY: user-to-num-info-zcpe API
        try:
            r = requests.get(
                f"https://user-to-num-info-zcpe.onrender.com/userid={uid_str}",
                timeout=20)
            if r.status_code == 200:
                _d = r.json()
                if _d: return _d
        except Exception as e:
            print(f"[UID_ZCPE_ERR] {_safe_err(e)}")
        # FALLBACK: tg-id-2-numb-v3 API
        for _attempt in range(2):
            try:
                r = requests.get(
                    f"https://tg-id-2-numb-and-tg-info-v3.vercel.app/api/tg?info={uid_str}",
                    timeout=20)
                if r.status_code == 200:
                    _d = r.json()
                    if _d: return _d
                break
            except Exception as e:
                print(f"[UID_TGV3_ERR] attempt={_attempt+1} {_safe_err(e)}")
                if _attempt == 0: time.sleep(1)
        return None

    def _fetch_abdulstore():
        try:
            r = requests.get("https://store.abdulstoreapi.workers.dev/api/v1",
                             params={"key": "ak_59eca148e4484ccb50e8575645c32ee1", "userid": uid_str},
                             timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[UID_ABDUL_ERR] {_safe_err(e)}")
        return None

    # Run both APIs in parallel
    with _cf_uid.ThreadPoolExecutor(max_workers=2) as _ex_uid:
        _f_new   = _ex_uid.submit(_fetch_new_uid_api)
        _f_abdul = _ex_uid.submit(_fetch_abdulstore)
        d_new   = _f_new.result()
        d_abdul = _f_abdul.result()

    phone = ''; country = 'India'; cc = '+91'; ud = {}

    # ── Parse user-to-num-info-zcpe API (PRIMARY) ──
    # Structure: {status:true, target_id:"...", target_type:"user_id",
    #   data:{ p1:{ title, description, records:[{userid,msg,country,country_code,number}] } },
    #   developer:"@...", time:"..."}
    # Fallback (tg-id-2-numb-v3): {status, target_id, number, data:{...}, info:{country,country_code}}
    if d_new:
        _status = d_new.get('status', False)

        # ── Try user-to-num-info-zcpe format FIRST ──
        _p1_block = None
        _top_data = d_new.get('data') or {}
        if isinstance(_top_data, dict):
            _p1_block = _top_data.get('p1') or {}
        _zcpe_recs = _p1_block.get('records', []) if isinstance(_p1_block, dict) else []

        if _zcpe_recs and isinstance(_zcpe_recs, list) and len(_zcpe_recs) > 0:
            # zcpe format detected
            _rec0 = _zcpe_recs[0]
            _ph = str(_rec0.get('number', '') or '').strip()
            country = str(_rec0.get('country', '') or 'India').strip() or 'India'
            cc      = str(_rec0.get('country_code', '') or '+91').strip() or '+91'
            if _ph and _ph != uid_str and len(_ph) >= 7:
                phone = _ph
                # Strip embedded country code if present
                _cc_d = cc.replace('+','').strip()
                if _cc_d and phone.startswith(_cc_d) and len(phone) - len(_cc_d) >= 7:
                    phone = phone[len(_cc_d):]
            ud = {
                'telegram_id': uid_str,
                'success': True,
            }
            if phone: ud['number'] = phone; ud['phone'] = phone
            if country: ud['country'] = country
            if cc: ud['country_code'] = cc
            print(f"[UID_ZCPE] uid={uid_str} phone={phone} country={country} cc={cc}")
        else:
            # ── Fallback: tg-id-2-numb-v3 format ──
            # Structure: {status, target_id, number, data:{first_name,bio,...}, info:{country,country_code}}
            _data = _top_data if isinstance(_top_data, dict) else {}
            _info = d_new.get('info') or {}

            _ph = str(d_new.get('number', '') or '').strip()
            if _ph and _ph != uid_str and len(_ph) >= 7:
                phone   = _ph
                country = str(_info.get('country', '') or 'India').strip() or 'India'
                cc      = str(_info.get('country_code', '') or '+91').strip() or '+91'
                _cc_d = cc.replace('+','').strip()
                if _cc_d and phone.startswith(_cc_d) and len(phone) - len(_cc_d) >= 7:
                    phone = phone[len(_cc_d):]

            ud = {
                'telegram_id':       uid_str,
                'username':          str(d_new.get('target_username', '') or _data.get('username', '') or '').strip(),
                'first_name':        str(_data.get('first_name', '') or d_new.get('first_name', '') or '').strip(),
                'last_name':         str(_data.get('last_name', '') or d_new.get('last_name', '') or '').strip(),
                'bio':               str(_data.get('bio', '') or d_new.get('bio', '') or '').strip(),
                'is_active':         _data.get('is_active', ''),
                'total_groups':      _data.get('total_groups', 0),
                'admin_groups':      _data.get('admin_groups', 0),
                'total_msg_count':   _data.get('total_msg_count', 0),
                'msg_in_groups_count': _data.get('msg_in_groups_count', 0),
                'names_count':       _data.get('names_count', 0),
                'usernames_count':   _data.get('usernames_count', 0),
                'first_msg_date':    str(_data.get('first_msg_date', '') or '').strip(),
                'last_msg_date':     str(_data.get('last_msg_date', '') or '').strip(),
                'success':           True,
            }
            if phone: ud['number'] = phone; ud['phone'] = phone
            if country: ud['country'] = country
            if cc: ud['country_code'] = cc
            print(f"[UID_TGV3] uid={uid_str} phone={phone} active={ud.get('is_active')} groups={ud.get('total_groups')}")

    # ── AbdulStore fallback / supplement if phone not found ──
    if d_abdul and not phone:
        d1_inner = d_abdul.get('data') or {}
        _ph2 = str(d1_inner.get('number','') or d1_inner.get('phone','') or
                   d_abdul.get('number','') or d_abdul.get('phone','') or '').strip()
        if _ph2 and _ph2 != uid_str and len(_ph2) >= 7:
            phone   = _ph2
            country = d1_inner.get('country','') or d_abdul.get('country','India') or 'India'
            cc      = d1_inner.get('country_code','') or d_abdul.get('country_code','+91') or '+91'
            if not ud: ud = dict(d_abdul); ud['success'] = True
            ud['number'] = phone; ud['phone'] = phone
            print(f"[UID_ABDUL] uid={uid_str} phone={phone}")

    pic = _fetch_pfp_by_id(uid_str)

    if ud:
        return ud, phone or 'N/A', country, cc, pic

    # TG direct fallback
    tg_fb = _fetch_tg_user_direct(uid_str)
    pic_fb = pic or _fetch_pfp_by_id(uid_str)
    if tg_fb:
        ud_fb = {
            'telegram_id': uid_str,
            'first_name': tg_fb.get('first_name',''),
            'last_name':  tg_fb.get('last_name',''),
            'username':   tg_fb.get('username',''),
            'bio':        tg_fb.get('bio',''),
            'success': True
        }
        return ud_fb, 'N/A', 'India', '+91', pic_fb or tg_fb.get('pfp_url')
    return {}, 'N/A', 'India', '+91', pic

MERGE_KEYS=['username','bio','first_name','last_name','is_active','members',
            'total_groups','admin_groups','total_messages','group_messages',
            'names_used','usernames_used','first_message','last_message',
            'premium','verified','last_seen','telegram_id']

def _build_ud(uid_data, flat):
    """Merge userid API data + username API flat data — username API wins for detail fields"""
    ud=dict(uid_data)
    _str_keys=('bio','username','first_name','last_name','country','country_code','phone','number')
    for key in MERGE_KEYS:
        val=flat.get(key)
        # String fields — sirf string values accept karo (dict/list nahi)
        if key in _str_keys:
            if val not in (None,'') and isinstance(val, str):
                ud[key]=val
        else:
            if val not in (None,'',0):
                ud[key]=val
            elif key not in ud or ud.get(key) in (None,'',0):
                if val is not None: ud[key]=val
    return ud

def api_userid(uid_t):
    """
    Fetch user info using 3 sources concurrently:
    1. Telegram Bot API (getChat + getUserProfilePhotos) — PRIMARY, most reliable
    2. userid API (sh4dow)
    3. username API (username-to-info)
    Merge all, best data wins.
    """
    import concurrent.futures as _cfu2
    import time as _t_uid
    ci=re.sub(r'\D','',str(uid_t))
    _t_uid_start = _t_uid.time()
    try:
        with _cfu2.ThreadPoolExecutor(max_workers=3) as ex:
            f_tg   = ex.submit(_fetch_tg_user_direct, ci)
            f_uid  = ex.submit(_call_uid_api, ci)
            f_unid = ex.submit(_call_un_api_by_id, ci)
            tg       = f_tg.result()
            uid_data, phone, country, cc, pic1 = f_uid.result()
            flat2, pic2 = f_unid.result()

        # If we got username from TG or APIs, try username API too
        un_from_tg = (tg.get('username') or uid_data.get('username') or flat2.get('username') or '').replace('@','').strip()
        flat = flat2
        if un_from_tg and not flat2:
            flat, pic2 = _call_un_api(un_from_tg)

        # Build merged ud
        ud = _build_ud(uid_data, flat)

        # Telegram direct overrides everything for name/username/bio (most reliable)
        if tg.get('first_name'): ud['first_name'] = tg['first_name']
        if tg.get('last_name'):  ud['last_name']  = tg['last_name']
        if tg.get('username'):   ud['username']   = tg['username']
        if tg.get('bio'):        ud['bio']        = tg['bio']
        ud['telegram_id'] = ci

        # Fill missing from flat (activity fields from username API)
        for key in MERGE_KEYS:
            if key not in ud or ud.get(key) in (None,'',0):
                val=flat.get(key)
                if val not in (None,'',0): ud[key]=val

        # Phone: AbdulStore already called in _call_uid_api
        # Also check flat (from _call_un_api which also calls AbdulStore)
        if not phone or phone=='N/A':
            phone=(flat.get('phone') or flat.get('number') or 'N/A')
        if country=='India' and flat.get('country'): country=flat.get('country','India')
        if cc=='+91' and flat.get('country_code'): cc=flat.get('country_code','+91')

        # PFP
        pic_media = f"http://username-to-info-rwsw.onrender.com/media/{ci}.png"
        pic = tg.get('pfp_url') or pic2 or pic_media or pic1

        _rt = f"{int((_t_uid.time()-_t_uid_start)*1000)}ms"
        return {'success':True,'phone':phone,'target_id':ci,'telegram_id':ci,
                'country':country,'country_code':cc,'data':ud,'profile_pic':pic,
                'response_time':_rt}
    except Exception as e:
        print(f"[API_USERID] {_safe_err(e)}")
    # Minimal fallback
    tg=_fetch_tg_user_direct(ci)
    ud={'telegram_id':ci}
    if tg.get('first_name'): ud['first_name']=tg['first_name']
    if tg.get('last_name'):  ud['last_name']=tg['last_name']
    if tg.get('username'):   ud['username']=tg['username']
    if tg.get('bio'):        ud['bio']=tg['bio']
    pic=tg.get('pfp_url') or f"http://username-to-info-rwsw.onrender.com/media/{ci}.png"
    return {'success':True,'phone':'N/A','target_id':ci,'telegram_id':ci,'country':'—',
            'country_code':'','data':ud,'profile_pic':pic,'response_time':'N/A'}

def _call_un_api_by_id(uid_str):
    """Try new tg-id-2-numb / f2 API first, then AbdulStore — get phone + activity by user ID"""
    # Parser for f2 / tg-id-2-numb structure:
    # {status, telegram_id/target_id, number, data:{first_name,...}, info:{country,country_code}}
    def _parse_uid_flat(d, uid_str):
        _data = d.get('data') or {}
        _info = d.get('info') or {}
        phone = str(d.get('number', '') or d.get('phone', '') or '').strip()
        _ph_valid = phone and phone != uid_str and len(phone) >= 7
        # Accept even if phone missing — as long as activity data or status exists
        _has_data = bool(_data or d.get('status') or d.get('first_name') or
                         d.get('telegram_id') or d.get('target_id'))
        if not _ph_valid and not _has_data:
            return None
        flat = {
            'telegram_id':         uid_str,
            'first_name':          str(_data.get('first_name', '') or d.get('first_name', '') or '').strip(),
            'last_name':           str(_data.get('last_name', '') or d.get('last_name', '') or '').strip(),
            'is_active':           _data.get('is_active', ''),
            'total_groups':        _data.get('total_groups', 0),
            'admin_groups':        _data.get('admin_groups', 0),
            'total_msg_count':     _data.get('total_msg_count', 0),
            'msg_in_groups_count': _data.get('msg_in_groups_count', 0),
            'names_count':         _data.get('names_count', 0),
            'usernames_count':     _data.get('usernames_count', 0),
            'first_msg_date':      str(_data.get('first_msg_date', '') or '').strip(),
            'last_msg_date':       str(_data.get('last_msg_date', '') or '').strip(),
        }
        if _ph_valid:
            flat['phone']        = phone
            flat['number']       = phone
            flat['country']      = str(_info.get('country', '') or d.get('country', 'India') or 'India').strip()
            flat['country_code'] = str(_info.get('country_code', '') or d.get('country_code', '+91') or '+91').strip()
        return flat

    try:
        r = requests.get(
            f"https://tg-id-2-numb-and-tg-info-v3.vercel.app/api/tg?info={uid_str}",
            timeout=12)
        if r.status_code == 200:
            d = r.json()
            flat = _parse_uid_flat(d, uid_str)
            if flat:
                pic = _fetch_pfp_by_id(uid_str)
                return flat, pic
    except Exception as e: print(f"[UN_BY_ID_TGV3_ERR] {_safe_err(e)}")
    # Fallback: old zcpe
    try:
        r = requests.get(
            f"https://user-to-num-info-zcpe.onrender.com/userid={uid_str}",
            timeout=10)
        if r.status_code == 200:
            d = r.json()
            flat = _parse_uid_flat(d, uid_str)
            if flat:
                pic = _fetch_pfp_by_id(uid_str)
                return flat, pic
    except Exception as e: print(f"[UN_BY_ID_NEWAPI_ERR] {_safe_err(e)}")

    # Fallback: AbdulStore
    try:
        r = requests.get("https://store.abdulstoreapi.workers.dev/api/v1",
                         params={"key": "ak_59eca148e4484ccb50e8575645c32ee1", "userid": uid_str}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d and (d.get('success') or d.get('number') or d.get('phone') or d.get('name')):
                phone = str(d.get('number','') or d.get('phone','') or '').strip()
                flat = {
                    'telegram_id':  uid_str,
                    'phone':        phone if phone != uid_str else '',
                    'number':       phone if phone != uid_str else '',
                    'country':      d.get('country','India') or 'India',
                    'country_code': d.get('country_code','+91') or '+91',
                }
                pic = _fetch_pfp_by_id(uid_str)
                return flat, pic
    except Exception as e: print(f"[UN_BY_ID_ABDUL_ERR] {_safe_err(e)}")
    return {}, None

def _fetch_tg_user_direct(uid_str):
    """
    Fetch user info DIRECTLY from Telegram Bot API.
    Returns dict with: first_name, last_name, username, bio, pfp_url
    This is the most reliable source — works even when 3rd party APIs fail.
    """
    result={}
    _raw = str(uid_str).strip()
    # Username (@abc) ya numeric ID — dono support karo
    if _raw.startswith('@') or (not _raw.lstrip('-').isdigit()):
        # Username case: @ ke saath raho, sirf clean karo
        uid_str = '@' + _raw.replace('@','').strip()
        _for_photo = None  # getUserProfilePhotos username pe kaam nahi karta
    else:
        uid_str = re.sub(r'\D','',_raw)
        _for_photo = uid_str
    # 1. getChat — gets name, username, bio
    try:
        r=requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
            params={"chat_id":uid_str}, timeout=10)
        if r.status_code==200:
            d=r.json().get('result',{})
            result['first_name'] = d.get('first_name','') or ''
            result['last_name']  = d.get('last_name','') or ''
            result['username']   = d.get('username','') or ''
            result['bio']        = d.get('bio','') or ''
            result['type']       = d.get('type','')
            result['tg_id']      = str(d.get('id',uid_str))
            # Username case: getChat ne numeric ID diya — photo fetch ke liye use karo
            if _for_photo is None and d.get('id'):
                _for_photo = str(d['id'])
    except Exception as e: print(f"[TG_DIRECT getChat] {_safe_err(e)}")

    # 2. getUserProfilePhotos — gets PFP (sirf numeric ID pe kaam karta hai)
    if _for_photo:
        try:
            r2=requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos",
                params={"user_id":_for_photo,"limit":1}, timeout=10)
            if r2.status_code==200:
                photos=r2.json().get('result',{}).get('photos',[])
                if photos and photos[0]:
                    file_id=photos[0][-1].get('file_id','')
                    if file_id:
                        r3=requests.get(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                            params={"file_id":file_id}, timeout=10)
                        if r3.status_code==200:
                            fpath=r3.json().get('result',{}).get('file_path','')
                            if fpath:
                                result['pfp_url']=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}"
        except Exception as e: print(f"[TG_DIRECT photo] {_safe_err(e)}")

    return result

def api_full_user(query, _timeout=30):
    """
    UNIFIED: query = @username ya numeric ID
    Teeno sources se maximum data nikalo aur merge karo.
    Username button, TG ID button, Select User — teeno yahi use karein.
    Returns same format as api_userid.
    """
    import concurrent.futures as _cff
    import time as _t_full
    query=str(query).strip()
    is_uid = query.lstrip('-').isdigit()
    cl = query.replace('@','').strip()
    _t_start = _t_full.time()

    # Run all 3 sources concurrently
    def _run_tg(q):
        try: return _fetch_tg_user_direct(re.sub(r'\D','',q) if q.lstrip('-').isdigit() else q)
        except: return {}
    def _run_uid(q):
        if q.lstrip('-').isdigit():
            return _call_uid_api(q)
        # Username case: pehle TG ID dhundho via getChat, phir uid API chalao
        try:
            _uname_clean = q.replace('@','').strip()
            _gc = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                params={"chat_id": f"@{_uname_clean}"}, timeout=10)
            if _gc.status_code == 200:
                _gc_id = str(_gc.json().get('result', {}).get('id', '') or '').strip()
                if _gc_id and _gc_id.lstrip('-').isdigit():
                    return _call_uid_api(_gc_id)
        except: pass
        return {},'N/A','India','+91',None
    def _run_un(q):
        if q.lstrip('-').isdigit():
            r1,p1=_call_un_api_by_id(q)
            if r1: return r1,p1
            return {},None
        return _call_un_api(q)

    try:
        with _cff.ThreadPoolExecutor(max_workers=3) as ex:
            ft = ex.submit(_run_tg, query)
            fu = ex.submit(_run_uid, query)
            fn = ex.submit(_run_un, cl)
            tg = ft.result()
            uid_res = fu.result()
            un_res  = fn.result()

        # Unpack uid result
        if isinstance(uid_res, tuple) and len(uid_res)==5:
            uid_data, phone, country, cc, pic1 = uid_res
        else:
            uid_data={}; phone='N/A'; country='India'; cc='+91'; pic1=None

        flat,pic2 = un_res if (isinstance(un_res,tuple) and len(un_res)==2) else ({},None)
        flat = flat or {}

        # Get tg_id
        tg_id = (tg.get('tg_id') or
                 str(flat.get('telegram_id') or flat.get('id') or '') or
                 uid_data.get('telegram_id','') or
                 (re.sub(r'\D','',query) if is_uid else ''))

        # If we have username from TG but no flat data, try username API
        un_from_tg=(tg.get('username') or flat.get('username') or uid_data.get('username') or '').replace('@','').strip()
        if un_from_tg and not flat and not is_uid:
            try: flat,pic2=_call_un_api(un_from_tg)
            except: pass
        flat=flat or {}

        # Build merged ud
        ud=_build_ud(uid_data, flat)

        # TG direct is most reliable — override
        if tg.get('first_name'): ud['first_name']=tg['first_name']
        if tg.get('last_name'):  ud['last_name']=tg['last_name']
        if tg.get('username'):   ud['username']=tg['username']
        if tg.get('bio'):        ud['bio']=tg['bio']
        if tg_id: ud['telegram_id']=tg_id

        # Fill any remaining gaps from flat
        for key in MERGE_KEYS:
            if key not in ud or ud.get(key) in (None,'',0):
                val=flat.get(key)
                if val not in (None,'',0): ud[key]=val

        # Phone/country fallback chain
        if not phone or phone=='N/A':
            phone=(flat.get('phone') or flat.get('number') or 'N/A')
        if country=='India' and flat.get('country') and flat['country']!='India':
            country=flat['country']
        if cc=='+91' and flat.get('country_code') and flat['country_code']!='+91':
            cc=flat['country_code']
        # Strip embedded country code from phone (e.g. "919817015923" with cc "+91" → "9817015923")
        if phone and phone!='N/A' and cc:
            _cc_d2 = cc.replace('+','').strip()
            if _cc_d2 and phone.startswith(_cc_d2) and len(phone)-len(_cc_d2) >= 7:
                phone = phone[len(_cc_d2):]

        # PFP: TG direct > username API > media URL > userid API
        pic_media=f"http://username-to-info-rwsw.onrender.com/media/{tg_id}.png" if tg_id else None
        pic=tg.get('pfp_url') or pic2 or pic_media or pic1
        if not pic and tg_id:
            pic=_fetch_pfp_by_id(tg_id)

        _rt_full = f"{int((_t_full.time()-_t_start)*1000)}ms"
        return {'success':True,'phone':phone,'telegram_id':tg_id,'target_id':tg_id,
                'target_username':un_from_tg or cl,'country':country,'country_code':cc,
                'profile_pic':pic,'profile_picture':pic,'data':ud,
                'response_time':_rt_full}
    except Exception as e:
        print(f"[API_FULL_USER] {_safe_err(e)}")
        # Minimal fallback
        tg=_fetch_tg_user_direct(re.sub(r'\D','',query) if is_uid else query)
        ud={'telegram_id':tg.get('tg_id',query)}
        for k in ('first_name','last_name','username','bio'):
            if tg.get(k): ud[k]=tg[k]
        pic=tg.get('pfp_url')
        return {'success':bool(tg),'phone':'N/A','telegram_id':query,'target_id':query,
                'target_username':cl,'country':'—','country_code':'','profile_pic':pic,
                'data':ud,'response_time':'N/A'}

def api_aadhar(an):
    try:
        an=re.sub(r'\D','',str(an))
        if len(an)!=12: return None
        r=requests.get(f"https://adhar-to-info.vercel.app/?key={_K("key_aadhar")}&aadhar={an}",timeout=15)
        if r.status_code==200:
            d=r.json()
            if d.get('status') and d.get('results',{}).get('success'):
                res=d.get('results',{})
                return {'success':True,'aadhaar':res.get('aadhaar',an),'total_records':res.get('total_records',0),'data':res.get('data',[])}
    except: pass
    return None

def api_instagram(un):
    try:
        u=un.replace('@','').lower()
        r=requests.get(f"https://insta-info-eta.vercel.app/?username={u}&key={_K("key_instagram")}",timeout=15)
        if r.status_code==200:
            d=r.json()
            if d.get('username'):
                pic=d.get('pic',''); pic=pic if pic and pic.startswith('http') else None
                return {'success':True,'id':d.get('id','N/A'),'username':d.get('username',u),
                        'name':d.get('name','N/A'),'bio':d.get('bio',''),
                        'verified':d.get('verified',False),'private':d.get('private',False),
                        'pic':pic,'followers':d.get('followers',0),
                        'following':d.get('following',0),'posts':d.get('posts',0)}
    except: pass
    return None

def api_ff(uid_ff):
    """FF INFO using sextyinfo.vercel.app/player-info API"""
    try:
        uid_ff=re.sub(r'\D','',str(uid_ff))

        r=requests.get(f"https://sextyinfo.vercel.app/player-info?uid={uid_ff}",timeout=30)
        if r.status_code!=200: return None
        d=r.json()
        if not d or not d.get('basicInfo'): return None

        bi=d.get('basicInfo',{})
        si=d.get('socialInfo',{})
        pet=d.get('petInfo',{})
        clan=d.get('clanBasicInfo',{})
        cap=d.get('captainBasicInfo',{})
        cr=d.get('creditScoreInfo',{})

        # Timestamps
        from datetime import datetime as _dt
        def ts2str(ts):
            try: return _dt.fromtimestamp(int(ts)).strftime("%d %b %Y %I:%M %p")
            except: return str(ts)

        created=ts2str(bi.get('createAt','')) if bi.get('createAt') else 'N/A'
        last_login=ts2str(bi.get('lastLoginAt','')) if bi.get('lastLoginAt') else 'N/A'

        # Rank names
        BR_RANKS={0:'Bronze',100:'Bronze',200:'Silver',300:'Gold',400:'Platinum',
                  500:'Diamond',600:'Heroic',700:'Grandmaster',800:'Challenger'}
        def rank_name(pts):
            try:
                p=int(pts); tier=p//100*100
                return BR_RANKS.get(tier,f"Rank {p}")
            except: return 'N/A'

        br_pts=bi.get('rankingPoints',0)
        cs_pts=bi.get('csRankingPoints',0)
        max_br=bi.get('maxRank',0)
        max_cs=bi.get('csMaxRank',0)

        # Mode preference
        mode_map={'ModePrefer_BR':'Battle Royale','ModePrefer_CS':'Clash Squad',
                  'ModePrefer_LONE_WOLF':'Lone Wolf','ModePrefer_RANKED':'Ranked'}
        mode=mode_map.get(si.get('modePrefer',''),'BR')

        # Language
        lang_map={'Language_EN':'🇬🇧 English','Language_HI':'🇮🇳 Hindi','Language_ID':'🇮🇩 Indonesian',
                  'Language_PT':'🇧🇷 Portuguese','Language_TH':'🇹🇭 Thai','Language_VN':'🇻🇳 Vietnamese',
                  'Language_RU':'🇷🇺 Russian','Language_AR':'🇦🇪 Arabic','Language_ES':'🇪🇸 Spanish',
                  'Language_CN_TRADITIONAL':'🇹🇼 Traditional Chinese','Language_ZH':'🇨🇳 Chinese'}
        lang=lang_map.get(si.get('language',''),si.get('language','N/A'))

        return {
            'success':True,
            'uid':bi.get('accountId',uid_ff),
            'nickname':bi.get('nickname','N/A'),
            'region':bi.get('region','N/A'),
            'level':bi.get('level',0),
            'exp':bi.get('exp',0),
            'liked':bi.get('liked',0),
            'badges':bi.get('badgeCnt',0),
            'rank_pts':br_pts,
            'cs_rank_pts':cs_pts,
            'rank_name':rank_name(br_pts),
            'cs_rank_name':rank_name(cs_pts),
            'max_br_name':rank_name(max_br),
            'max_cs_name':rank_name(max_cs),
            'signature':si.get('signature','—') or '—',
            'language':lang,
            'mode':mode,
            'create_at':created,
            'last_login':last_login,
            'ban_status':'NOT BANNED',
            'credit_score':cr.get('creditScore',0),
            'version':bi.get('releaseVersion','N/A'),
            'pet_id':pet.get('id',0),
            'pet_level':pet.get('level',0),
            'pet_exp':pet.get('exp',0),
            'clan_name':clan.get('clanName','No Clan'),
            'clan_id':clan.get('clanId',''),
            'clan_level':clan.get('clanLevel',0),
            'clan_members':clan.get('memberNum',0),
            'clan_leader':cap.get('nickname',''),
            'avatar_url':'',
        }
    except Exception as e: print(f"[API_FF] {_safe_err(e)}")
    return None

def api_ff_like(uid_ff):
    """Get FF like info (before count) using FF info API"""
    try:
        uid_ff=re.sub(r'\D','',str(uid_ff))
        r=requests.get(f"https://sextyinfo.vercel.app/player-info?uid={uid_ff}",timeout=30)
        if r.status_code==200:
            d=r.json()
            if d and d.get('basicInfo'):
                bi=d['basicInfo']
                return {
                    'success':True,
                    'uid':bi.get('accountId',uid_ff),
                    'nickname':bi.get('nickname','N/A'),
                    'level':bi.get('level',0),
                    'liked':bi.get('liked',0),
                    'region':bi.get('region','IND'),
                }
    except Exception as e: print(f"[API_FF_LIKE] {_safe_err(e)}")
    return None

def do_ff_like_send(chat_id, msg_id, uid, region, user_id, fname):
    """Send likes using 6 APIs in parallel — simran API new primary"""
    import concurrent.futures as _cfl
    region_display=REGION_NAMES.get(region.lower(),region.upper())

    _anim_stop=[False]
    def _animate_pbar():
        steps=[(5,0.2),(20,0.3),(40,0.3),(60,0.3),(80,0.3),(93,0.2)]
        for pct,delay in steps:
            if _anim_stop[0]: break
            try:
                bot.edit_message_text(
                    f"<blockquote>{pbar(pct)}\n⚡ ꜱᴇɴᴅɪɴɢ ʟɪᴋᴇꜱ...</blockquote>",
                    chat_id,msg_id,parse_mode='HTML')
            except: pass
            time.sleep(delay)

    anim_thread=threading.Thread(target=_animate_pbar,daemon=True)
    anim_thread.start()

    def try_api0():
        try:
            r=requests.get(LIKE_API_0,params={"uid":uid,"server_name":region.lower()},timeout=25)
            if r.status_code==200: return r.json()
        except: pass
        return None

    def try_api1():
        try:
            r=requests.get(LIKE_API_1,params={"uid":uid,"server_name":region.lower()},
                           headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"},timeout=25)
            if r.status_code==200: return r.json()
        except: pass
        return None

    def try_api2():
        try:
            r=requests.get(LIKE_API_2,params={"uid":uid,"server_name":region.lower()},timeout=25)
            if r.status_code==200: return r.json()
        except: pass
        return None

    def try_api3():
        try:
            r=requests.get(LIKE_API_3,params={"uid":uid,"server_name":region.upper()},
                           headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"},timeout=25)
            if r.status_code==200: return r.json()
        except: pass
        return None

    def try_api4():
        try:
            r=requests.get(LIKE_API_4,params={"uid":uid,"region":region,"key":"UDIT"},timeout=25)
            if r.status_code==200: return r.json()
        except: pass
        return None

    def try_api5():
        try:
            r=requests.get(LIKE_API_5,params={"uid":uid,"server_name":region.lower()},timeout=25)
            if r.status_code==200: return r.json()
        except: pass
        return None

    with _cfl.ThreadPoolExecutor(max_workers=6) as ex:
        f0=ex.submit(try_api0); fa=ex.submit(try_api1); fb=ex.submit(try_api2)
        fc=ex.submit(try_api3); fd=ex.submit(try_api4); fe=ex.submit(try_api5)
        d0=f0.result(); d1=fa.result(); d2=fb.result()
        d3=fc.result(); d4=fd.result(); d5=fe.result()

    _anim_stop[0]=True
    anim_thread.join(timeout=1)

    now_str=_now_ist()
    total_given=0; results_txt=""
    already_liked=False

    api_results=[("1",d1),("2",d2),("3",d3),("4",d4),("5",d5),("6",d0)]
    for i,(label,data) in enumerate(api_results):
        if not data: continue
        if "error" in data:
            results_txt+=f"\n◆ 𝐀𝐏𝐈 {label} : ❌ {data.get('error','')}"; continue
        status=data.get("status",0)
        msg_txt=str(data.get("message",data.get("msg",""))).lower()
        if "already" in msg_txt or "max" in msg_txt or "limit" in msg_txt:
            already_liked=True
            results_txt+=f"\n{'◆' if int(label)%2!=0 else '◇'} 𝐀𝐏𝐈 {label} : ⚠️ Already Liked"
        elif status in [1,2,3]:
            lb=data.get("LikesbeforeCommand",data.get("likes_before",0))
            la=data.get("LikesafterCommand",data.get("likes_after",0))
            lg=data.get("LikesGivenByAPI",data.get("likes_given",1))
            total_given+=int(lg or 0)
            results_txt+=f"\n{'◆' if int(label)%2!=0 else '◇'} 𝐀𝐏𝐈 {label} : {lb} → {la} (+{lg})"
        else:
            results_txt+=f"\n{'◆' if int(label)%2!=0 else '◇'} 𝐀𝐏𝐈 {label} : ⚠️ {data.get('message',data.get('msg','Failed'))}"

    if not results_txt:
        results_txt="\n◆ ❌ ᴋᴏɪ ʙʜɪ API ʀᴇꜱᴩᴏɴᴅ ɴᴀʜɪ ᴋɪ"

    if total_given>0: _like_update_cooldown(user_id,uid,region); _like_update_ratelimit(user_id)
    remain=_like_remaining_daily(user_id)
    next_t=(datetime.now()+timedelta(hours=LIKE_COOLDOWN_HOURS)).strftime("%I:%M %p")

    _TE = lambda eid, fb: f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"
    _LOOP10 = _TE("5465629669829128119","➿")*10

    if already_liked and total_given==0:
        status_icon=f"{_TE('6179105681375760937','✅')} ᴀʟʀᴇᴀᴅʏ ʟɪᴋᴇᴅ"
    elif total_given>0:
        status_icon=f"{_TE('6179105681375760937','✅')} <b>LIKES SENT!</b> {_TE('5436040291507247633','🎉')}"
    else:
        status_icon=f"❌ <b>LIKE FAILED</b>"

    # Build per-API lines — plain version for inside blockquote
    api_lines_premium = ""
    api_lines_plain = ""
    player_name=""
    try:
        pinfo=api_ff_like(uid)
        if pinfo: player_name=pinfo.get('nickname','') or ''
    except: pass
    for i,(label,data) in enumerate(api_results):
        if not data: continue
        _gm = _TE("5350803719170564382","🎮")
        _crown = _TE("6158882647473920838","👑")
        if "error" in data:
            api_lines_premium += f"│ {_gm} ᴀᴩɪ {label}: ❌ {data.get('error','')}\n"
            continue
        status=data.get("status",0)
        msg_txt=str(data.get("message",data.get("msg",""))).lower()
        if "already" in msg_txt or "max" in msg_txt or "limit" in msg_txt:
            api_lines_premium += f"│ {_gm} ᴀᴩɪ {label}: ⚠️ Already Liked\n"
        elif status in [1,2,3]:
            lb2=data.get("LikesbeforeCommand",data.get("likes_before",0))
            la2=data.get("LikesafterCommand",data.get("likes_after",0))
            lg2=data.get("LikesGivenByAPI",data.get("likes_given",1))
            api_lines_premium += f"│ {_gm} ᴀᴩɪ {label}: {_crown} {lb2} → {la2} (+{lg2})\n"
        else:
            api_lines_premium += f"│ {_gm} ᴀᴩɪ {label}: ⚠️ {data.get('message',data.get('msg','Failed'))}\n"

    _pe_uid  = _TE("5888781182249738113","🆔")
    _pe_usr  = _TE("6035084557378654059","👤")
    _pe_flag = _TE("5447419223242449630","🇮🇳")
    _pe_globe= _TE("6114021507908767611","🌎")
    _region_pe = f"{_pe_flag} {region_display.replace('🇮🇳','').strip()}" if "India" in region_display or "IND" in region_display.upper() else f"{_pe_globe} {region_display}"

    txt=(
        f"<blockquote>"
        f"{_LOOP10}\n"
        f"   {_TE('6158973086600273462','🎮')} ꜰꜰ ʟɪᴋᴇ ʀᴇꜱᴜʟᴛ\n"
        f"{_LOOP10}\n\n"
        f"{status_icon}\n\n"
        f"╭─── {_pe_usr} ᴩʟᴀʏᴇʀ ───╮\n"
        f"{'│ 🎫 ɴᴀᴍᴇ   : '+player_name+chr(10) if player_name else ''}"
        f"│ {_pe_uid} UID    : {uid}\n"
        f"│ {_pe_globe} ʀᴇɢɪᴏɴ : {_region_pe}\n"
        f"╰──────────────────╯\n\n"
        f"╭─── 📊 ᴀᴩɪ ʀᴇꜱᴜʟᴛꜱ ───╮\n"
        f"{api_lines_premium}"
        f"╰──────────────────╯\n\n"
        f"{_LOOP10}\n"
        f"   {_TE('5436040291507247633','🎉')}  TOTAL : +{total_given} LIKES ! {_TE('5469785308386041323','💥')}\n"
        f"{_LOOP10}\n\n"
        f"{_TE('5413704112220949842','⏰')} ɴᴇxᴛ (ᴛʜɪꜱ ᴜɪᴅ): {next_t}\n"
        f"{_TE('5431577498364158238','📊')} ᴅᴀɪʟʏ ʟᴇꜰᴛ: {remain}/{LIKE_DAILY_MAX}\n"
        f"{_TE('5472146462362048818','💡')} ᴅɪꜰꜰᴇʀᴇɴᴛ ᴜɪᴅꜱ = ɴᴏ ᴄᴏᴏʟᴅᴏᴡɴ!\n\n"
        f"{_TE('6242308461598610637','😀')} {now_str}\n"
        f"{_LOOP10}\n"
        f"{_TE('6147464060305676048','😎')} @Felix_modz1 {_TE('6147565374289220368','✅')}\n"
        f"{_LOOP10}"
        f"</blockquote>"
    )
    try: bot.edit_message_text(txt,chat_id,msg_id,parse_mode='HTML')
    except: bot.send_message(chat_id,txt,parse_mode='HTML')

def api_vehicle(rc):
    try:
        r=requests.get(f"https://vehicle-rc-to-num.vercel.app/?rc={rc}&key={_K("key_vehicle")}",timeout=15)
        if r.status_code==200:
            d=r.json()
            if d.get('success'):
                return {'success':True,'rc_number':rc,'owner_name':d.get('owner_name','N/A'),
                        'mobile_number':d.get('mobile_number','N/A'),'vehicle_model':d.get('vehicle_model','N/A'),
                        'registration_date':d.get('registration_date','N/A'),'fuel_type':d.get('fuel_type','N/A'),
                        'engine_number':d.get('engine_number','N/A'),'chassis_number':d.get('chassis_number','N/A'),
                        'insurance_valid_till':d.get('insurance_valid_till','N/A'),'tax_valid_till':d.get('tax_valid_till','N/A')}
    except: pass
    return None

FLIX_BOMBER_API  = "https://bombar-api-2.vercel.app/all"
FLIX_BOMBER_STOP = "https://flix-bombar.onrender.com/stop"
RLX_BOMBER_API   = "https://rlxbomber.vercel.app/api/attack"
RLX_BOMBER_KEY   = "rlxcoder"
RLX_BOMBER_API2  = "https://rlxbomber.vercel.app/api/attack"
RLX_BOMBER_KEY2  = "rlxcoder"

def _call_flix(num):
    try:
        r=requests.get(FLIX_BOMBER_API,params={"num":num},timeout=40)
        if r.status_code==200:
            try:
                d=r.json()
                s=int(d.get("sms",0) or 0); cl=int(d.get("calls",0) or 0)
                w=int(d.get("wa",0) or 0)
                return {"ok":True,"sms":s,"calls":cl,"wa":w}
            except:
                if r.text.strip(): return {"ok":True,"sms":0,"calls":0,"wa":0}
    except Exception as e: print(f"[FLIX] {_safe_err(e)}")
    return {"ok":False,"sms":0,"calls":0,"wa":0}

def _call_rlx(num):
    try:
        r=requests.get(RLX_BOMBER_API,params={"number":num,"key":_K("key_rlx_bomber")},timeout=40)
        if r.status_code==200:
            try:
                d=r.json()
                s=int(d.get("sms",0) or d.get("count",0) or 0)
                return {"ok":True,"sms":s,"calls":0,"wa":0}
            except:
                if r.text.strip(): return {"ok":True,"sms":0,"calls":0,"wa":0}
    except Exception as e: print(f"[RLX] {_safe_err(e)}")
    return {"ok":False,"sms":0,"calls":0,"wa":0}

def api_bomber_single(num):
    """Fire both APIs in parallel, merge results"""
    import concurrent.futures as _cf
    with _cf.ThreadPoolExecutor(max_workers=2) as ex:
        f1=ex.submit(_call_flix,num)
        f2=ex.submit(_call_rlx,num)
        r1=f1.result(); r2=f2.result()
    ok=r1["ok"] or r2["ok"]
    if not ok: return None
    return {"success":True,
            "sms":r1["sms"]+r2["sms"],
            "calls":r1["calls"]+r2["calls"],
            "wa":r1["wa"]+r2["wa"],
            "total":r1["sms"]+r2["sms"]+r1["calls"]+r2["calls"]+r1["wa"]+r2["wa"] or 1}

def api_bomber_stop(num):
    """Stop bomber via flix API"""
    try: requests.get(FLIX_BOMBER_STOP, params={"num": num}, timeout=10)
    except: pass

def run_bomber(uid, chat_id, number, msg_id):
    MAX=600; start=time.time(); sms=0; calls=0; wa=0; rounds=0
    bomber_jobs[uid]={'running':True,'number':number,'sms':0,'calls':0,'rounds':0,'start_time':start,'msg_id':msg_id,'chat_id':chat_id}

    # Start attack
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*10
    try:
        bot.edit_message_text(
            (f"<blockquote>{_L}\n"
             f"   {_te('5469654973308476699')} ʙᴏᴍʙᴇʀ ꜱᴛᴀʀᴛɪɴɢ...\n"
             f"{_L}\n\n"
             f"{_te('5301176488756788169')} ᴛᴀʀɢᴇᴛ: +91{number}\n"
             f"{pbar(0)}\n\n"
             f"{_te('6179142317446796557')} ꜱᴛᴏᴩ ʙᴏᴍʙᴇʀ ᴅᴀʙᴀᴏ ʙᴀɴᴅ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ\n\n"
             f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
             f"</blockquote>"),
            chat_id,msg_id,parse_mode='HTML')
    except: pass

    # Initial API call to start attack
    res=api_bomber_single(number)
    if res and res.get('success'):
        sms=res.get('sms',0); calls=res.get('calls',0); wa=res.get('wa',0); rounds=1
        bomber_jobs[uid].update({'sms':sms,'calls':calls,'rounds':rounds})

    while bomber_jobs.get(uid,{}).get('running',False):
        el=time.time()-start
        if el>=MAX: bomber_jobs[uid]['running']=False; break

        # Poll every 20s
        time.sleep(20)
        el=time.time()-start
        if el>=MAX: break

        # Re-fetch to get updated stats
        try:
            import concurrent.futures as _cf2
            with _cf2.ThreadPoolExecutor(max_workers=2) as ex2:
                rf1=ex2.submit(_call_flix,number)
                rf2=ex2.submit(_call_rlx,number)
                rd1=rf1.result(); rd2=rf2.result()
            ns=rd1["sms"]+rd2["sms"]; nc=rd1["calls"]+rd2["calls"]; nw=rd1["wa"]+rd2["wa"]
            if ns>sms: sms=ns
            if nc>calls: calls=nc
            if nw>wa: wa=nw
            rounds+=1
            bomber_jobs[uid].update({"sms":sms,"calls":calls,"rounds":rounds})
        except: rounds+=1

        rem=int(MAX-el); m_=rem//60; s_=rem%60; pct=min(int((el/MAX)*100),99)
        def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
        _L=_te("5465629669829128119")*10
        try:
            bot.edit_message_text(
                (f"<blockquote>{_L}\n"
                 f"   {_te('5469654973308476699')} ʙᴏᴍʙɪɴɢ ɪɴ ᴩʀᴏɢʀᴇꜱꜱ...\n"
                 f"{_L}\n\n"
                 f"{_te('5301176488756788169')} ᴛᴀʀɢᴇᴛ: +91{number}\n\n"
                 f"{_te('5386367538735104399')} ᴛɪᴍᴇ: {int(el)}s\n"
                 f"{_te('5267421370114914946')} {m_}m {s_}s ʀᴇᴍᴀɪɴɪɴɢ\n\n"
                 f"{pbar(pct)}\n\n"
                 f"{_te('5406631276042002796')} SMS | {_te('6093587384954262033')} ᴄᴀʟʟꜱ | {_te('5465300082628763143')} WA\n"
                 f"{_te('5373310679241466020')} ʀᴏᴜɴᴅꜱ: {rounds}\n\n"
                 f"{_te('6179142317446796557')} ꜱᴛᴏᴩ ʙᴏᴍʙᴇʀ ᴅᴀʙᴀᴏ ʙᴀɴᴅ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ\n\n"
                 f"{_te('6204263190319081111')} @Felix_Bhai {_te('6147565374289220368')}"
                 f"</blockquote>"),
                chat_id,msg_id,parse_mode='HTML')
        except: pass

    # Stop attack via API
    threading.Thread(target=api_bomber_stop,args=(number,),daemon=True).start()

    # Final message
    el=int(time.time()-start)
    reason="⏱️ 10 MIN AUTO-STOP" if el>=MAX else "🔴 STOPPED BY USER"
    try:
        bot.edit_message_text(
            (f"<blockquote>💣 <b>ʙᴏᴍʙᴇʀ</b> ⏱ {reason}\n\n"
             f"📱 <b>ᴛᴀʀɢᴇᴛ:</b> +91{number}\n"
             f"{_F}\n"
             f"📨 <b>SMS:</b> {sms}\n"
             f"📞 <b>ᴄᴀʟʟꜱ:</b> {calls}\n"
             f"💬 <b>WA:</b> {wa}\n"
             f"🔄 <b>ʀᴏᴜɴᴅꜱ:</b> {rounds}\n"
             f"🕐 <b>ᴛɪᴍᴇ:</b> {el}s\n\n"
             f"⚡ @Felix_modz1</blockquote>"),
            chat_id,msg_id,parse_mode='HTML')
    except: pass
    bomber_jobs.pop(uid,None)
    # Token log: bomber used
    try:
        user=get_user(uid)
        fname_log=user[2] if user else "User"
        uname_log=user[1] if user else ""
        try: bn=_get_bot_username()
        except: bn="felix_bot"
        log_token_activity(uid,fname_log,uname_log,0,user[5] if user else 0,
                           f"Bomber | +91{number} | SMS:{sms} Calls:{calls}",bn)
    except: pass


def _s(t):
    """Convert to small caps stylish text"""
    M={'A':'ᴀ','B':'ʙ','C':'ᴄ','D':'ᴅ','E':'ᴇ','F':'ꜰ','G':'ɢ','H':'ʜ','I':'ɪ','J':'ᴊ',
       'K':'ᴋ','L':'ʟ','M':'ᴍ','N':'ɴ','O':'ᴏ','P':'ᴘ','Q':'Q','R':'ʀ','S':'ꜱ','T':'ᴛ',
       'U':'ᴜ','V':'ᴠ','W':'ᴡ','X':'x','Y':'ʏ','Z':'ᴢ'}
    return ''.join(M.get(c.upper(),c) for c in str(t))


def _fmt_tg_user_short(res, query_display, now_str, credits_left=None):
    """
    USERNAME/TGID INFO — clean short card as per Felix's spec:
    Name, Username, TG ID, Country, Code, Number + credit footer
    """
    _L = "➿"*10  # fallback
    try:
        _TE = lambda eid, fb: f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"
        _L = _TE("5465629669829128119","➿")*10
    except: pass

    if not res or not res.get('success'):
        return (f"<blockquote>{_L}\n"
                f"🔍 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗜𝗡𝗙𝗢\n"
                f"{_L}\n\n"
                f"❌ No Data Found\n🔍 <code>{query_display}</code>\n\n"
                f"{_L}\n{_credit()}</blockquote>"), None

    ud = res.get('data', {}) or {}
    tg_id = str(ud.get('telegram_id') or res.get('telegram_id') or res.get('target_id','') or '').strip()

    fn  = str(ud.get('first_name','') or res.get('first_name','') or '').strip()
    ln  = str(ud.get('last_name','')  or res.get('last_name','') or '').strip()

    # ── Agar naam nahi mila toh TG getChat se seedha fetch karo ──
    if not fn and tg_id:
        try:
            import requests as _rq_nm
            _r_nm = _rq_nm.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                params={"chat_id": tg_id}, timeout=8)
            if _r_nm.status_code == 200:
                _d_nm = _r_nm.json().get('result', {})
                fn = str(_d_nm.get('first_name','') or '').strip()
                ln = str(_d_nm.get('last_name','')  or '').strip()
        except: pass
    # Username se bhi try karo agar tg_id nahi tha
    if not fn:
        _un_try = str(ud.get('username') or res.get('target_username','') or '').replace('@','').strip()
        if _un_try:
            try:
                import requests as _rq_nm2
                _r_nm2 = _rq_nm2.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                    params={"chat_id": f"@{_un_try}"}, timeout=8)
                if _r_nm2.status_code == 200:
                    _d_nm2 = _r_nm2.json().get('result', {})
                    fn = str(_d_nm2.get('first_name','') or '').strip()
                    ln = str(_d_nm2.get('last_name','')  or '').strip()
                    if not tg_id:
                        tg_id = str(_d_nm2.get('id','') or '').strip()
            except: pass

    nm  = f"{fn} {ln}".strip() or '—'

    _raw_un = (ud.get('username') or res.get('username') or res.get('target_username','') or '') or ''
    if isinstance(_raw_un, str): un = _raw_un.replace('@','').strip()
    else: un = ''
    un_display = f"@{un}" if un else query_display if query_display.startswith('@') else f"@{query_display}"

    # Phone
    phone = str(res.get('phone','') or res.get('number','') or ud.get('phone','') or ud.get('number','') or '').strip()
    if phone and phone == tg_id: phone = ''
    country  = str(res.get('country','') or ud.get('country','') or 'India').strip() or 'India'
    cc       = str(res.get('country_code','') or ud.get('country_code','') or '+91').strip() or '+91'
    if phone and cc:
        _cc_d = cc.replace('+','').strip()
        if _cc_d and phone.startswith(_cc_d) and len(phone)-len(_cc_d) >= 7:
            phone = phone[len(_cc_d):]
    if phone:
        num_display = f"+{cc.replace('+','')} {phone}"
    else:
        _pe_lock = f"<tg-emoji emoji-id='5890882606668452641'>🔒</tg-emoji>"
        num_display = f"{_pe_lock} Not Available"

    try:
        _TE2 = lambda eid, fb: f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"
        _cr_line = f"\n{_TE2('5379600444098093058','🪙')} ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ:- <b>{credits_left}</b>" if credits_left is not None else ""
        txt = (
            f"<blockquote>{_L}\n"
            f"{_TE2('6318752565865482087','🔍')} 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗜𝗡𝗙𝗢\n"
            f"{_L}\n"
            f"{_TE2('6030656587830399914','🆔')} Uꜱᴇʀ Iᴅᴇɴᴛɪᴛʏ\n\n"
            f"{_TE2('5798459514663473705','🍾')} Nᴀᴍᴇ:- <b>{nm}</b>\n"
            f"{_TE2('5913534466051021148','🌀')} Uꜱᴇʀɴᴀᴍᴇ:- {un_display}\n"
            f"{_TE2('5929312878816400493','✉️')} Tɢ ɪᴅ:- <code>{tg_id if tg_id else '—'}</code>\n\n"
            f"{_TE2('5789607097440147328','🩶')} Lᴏᴄᴀᴛɪᴏɴ\n\n"
            f"{_TE2('6178984829585986541','🌏')} Cᴏᴜɴᴛʀʏ:- {country}\n"
            f"{_TE2('6181649972757271368','⚜')} Cᴏᴅᴇ:- {cc}\n"
            f"{_TE2('5458568138004112273','📱')} Nᴜᴍʙᴇʀ:- <b>{num_display}</b>\n\n"
            f"{_L}{_cr_line}\n{_credit()}</blockquote>"
        )
    except:
        _cr_line2 = f"\n🪙 Credits Left: {credits_left}" if credits_left is not None else ""
        txt = (
            f"<blockquote>{_L}\n🔍 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗜𝗡𝗙𝗢\n{_L}\n\n"
            f"🍾 Name: <b>{nm}</b>\n"
            f"🌀 Username: {un_display}\n"
            f"✉️ TG ID: <code>{tg_id if tg_id else '—'}</code>\n\n"
            f"🌏 Country: {country}\n"
            f"⚜ Code: {cc}\n"
            f"📱 Number: <b>{num_display}</b>\n\n"
            f"{_L}{_cr_line2}\n{_credit()}</blockquote>"
        )
    return txt, None

def _fmt_tg_user(res, title_icon, title_text, query_display, now_str, credits_left=None):
    """
    Username / TG ID / Select User — same card. No pfp.
    Activity section hidden if all zero/unknown.
    """
    SEP = "━━━━━━━━━━━━━━━━━━"

    if not res or not res.get('success'):
        return (f"<blockquote>📋 {title_icon} <b>𝗨𝗦𝗘𝗥 𝗜𝗡𝗙𝗢</b>\n"
                f"{SEP}\n\n"
                f"❌ No Data Found\n🔍 <code>{query_display}</code>\n\n"
                f"{_credit()}</blockquote>"), None

    ud = res.get('data', {}) or {}

    # ── TG ID — primary key ──
    tg_id = str(ud.get('telegram_id') or res.get('telegram_id') or res.get('target_id','') or '').strip()

    # Agar tg_id nahi mila aur username hai — getChat se try karo
    if not tg_id:
        _un_try = str(ud.get('username') or res.get('username') or res.get('target_username','') or '').replace('@','').strip()
        if _un_try:
            try:
                _gc = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                                   params={"chat_id": f"@{_un_try}"}, timeout=8)
                if _gc.status_code == 200:
                    _gc_r = _gc.json().get('result', {})
                    tg_id = str(_gc_r.get('id', '')).strip()
                    if not ud.get('first_name') and _gc_r.get('first_name'): ud['first_name'] = _gc_r['first_name']
                    if not ud.get('last_name') and _gc_r.get('last_name'):   ud['last_name']  = _gc_r['last_name']
                    if not ud.get('bio') and _gc_r.get('bio'):               ud['bio']        = _gc_r['bio']
            except: pass

    # ── PFP ──
    pic = res.get('profile_pic') or res.get('profile_picture') or get_pic(res) or get_pic(ud)
    if not pic and tg_id:
        pic = _fetch_pfp_by_id(tg_id)
    # Last fallback: media URL from username-to-info API
    if not pic and tg_id:
        pic = f"http://username-to-info-rwsw.onrender.com/media/{tg_id}.png"

    # ── Fields ──
    fn  = str(ud.get('first_name','') or res.get('first_name','') or '').strip()
    ln  = str(ud.get('last_name','')  or res.get('last_name','') or '').strip()
    nm  = f"{fn} {ln}".strip() or '—'
    _raw_un = (ud.get('username') or res.get('username') or
               res.get('target_username','') or '') or ''
    # username sirf string accept karo — dict/object aaye to empty
    if isinstance(_raw_un, str): un = _raw_un.replace('@','').strip()
    else: un = ''
    # Display: agar username set nahi toh ɴᴏᴛ ꜱᴇᴛ ʏᴇᴛ
    un_display = f"@{un}" if un else "ɴᴏᴛ ꜱᴇᴛ ʏᴇᴛ !"
    bio = str(ud.get('bio','') or res.get('bio','') or '').strip() or ''

    # ── Number: multi-source se fetch karo ──
    phone = ''; country = 'India'; cc = '+91'

    def _is_real_phone(ph, tid):
        ph = str(ph or '').strip()
        if not ph or ph in ('N/A','null','None','','0'): return False
        if ph == str(tid or '').strip(): return False
        if len(ph) < 7 or len(ph) > 15: return False
        return True

    # Source 1: p1.records (already in res)
    _p1_recs = ((res.get('data') or {}).get('p1') or {}).get('records') or []
    if _p1_recs:
        _rec0 = _p1_recs[0]
        _ph0  = str(_rec0.get('number','') or '').strip()
        if _is_real_phone(_ph0, tg_id):
            phone   = _ph0
            country = str(_rec0.get('country','India') or 'India').strip() or 'India'
            cc      = str(_rec0.get('country_code','+91') or '+91').strip() or '+91'

    # Source 2: res/ud fields
    if not phone:
        _ph2 = str(res.get('phone','') or res.get('number','') or
                   ud.get('phone','') or ud.get('number','') or '').strip()
        if _is_real_phone(_ph2, tg_id):
            phone   = _ph2
            country = str(res.get('country','') or ud.get('country','') or 'India').strip() or 'India'
            cc      = str(res.get('country_code','') or ud.get('country_code','') or '+91').strip() or '+91'

    # Source 3: AbdulStore direct
    if not phone and tg_id:
        try:
            _ra = requests.get(
                "https://store.abdulstoreapi.workers.dev/api/v1",
                params={"key": "ak_59eca148e4484ccb50e8575645c32ee1", "userid": tg_id},
                timeout=10)
            if _ra.status_code == 200:
                _da = _ra.json()
                # AbdulStore wraps number inside data{} — check both levels
                _da_inner = _da.get('data') or {}
                _pha = str(_da_inner.get('number','') or _da_inner.get('phone','') or
                           _da.get('number','') or _da.get('phone','') or '').strip()
                if _is_real_phone(_pha, tg_id):
                    phone   = _pha
                    country = _da_inner.get('country','') or _da.get('country','India') or 'India'
                    cc      = _da_inner.get('country_code','') or _da.get('country_code','+91') or '+91'
        except: pass

    # Source 4: skip - only AbdulStore used now

    # ── Activity fields ──
    # Activity: check ud first, fallback to res root (in case data not nested properly)
    def _gv(key, *alts):
        for src in (ud, res):
            for k in (key,) + alts:
                v = src.get(k)
                if v not in (None, '', 0, '0'): return v
        return 0
    is_active    = ud.get('is_active','') or res.get('is_active','')
    act_str      = ('✅ True'  if str(is_active).lower() in ['true','1','yes'] else
                    '❌ False' if str(is_active).lower() in ['false','0','no'] else
                    str(is_active) if is_active not in ('','None','null') else '')
    total_groups = int(_gv('total_groups') or 0)
    admin_groups = int(_gv('admin_groups') or 0)
    total_msgs   = int(_gv('total_msg_count','total_messages') or 0)
    grp_msgs     = int(_gv('msg_in_groups_count','group_messages') or 0)
    names_used   = int(_gv('names_count','names_used') or 0)
    unames_used  = int(_gv('usernames_count','usernames_used') or 0)

    def _fmt_date(raw):
        if not raw or str(raw) in ('N/A','null','None',''): return ''
        raw=str(raw)
        try:
            from datetime import datetime as _dt
            dt=_dt.strptime(raw[:19],'%Y-%m-%dT%H:%M:%S')
            return dt.strftime('%d %b %Y %H:%M')
        except: return raw[:16]

    first_msg = _fmt_date(ud.get('first_msg_date') or ud.get('first_message','') or
                          res.get('first_msg_date','') or res.get('first_message',''))
    last_msg  = _fmt_date(ud.get('last_msg_date')  or ud.get('last_message','') or
                          res.get('last_msg_date','')  or res.get('last_message',''))

    # ── Activity section show karo SIRF tab jab kuch meaningful data ho ──
    _has_activity = (
        act_str not in ('','❓ Unknown') or
        total_groups > 0 or admin_groups > 0 or total_msgs > 0 or
        grp_msgs > 0 or names_used > 0 or unames_used > 0 or
        bool(first_msg) or bool(last_msg)
    )

    # Response time
    resp_time = str(res.get('response_time','') or '').strip()

    # Premium / verified
    premium  = ud.get('premium','')  or ''
    verified = ud.get('verified','') or ''
    is_bot   = ud.get('is_bot','')   or ''

    # ── Title ──
    if title_text == 'SELECTED USER':  card_title = '𝗦𝗘𝗟𝗘𝗖𝗧𝗘𝗗 𝗨𝗦𝗘𝗥'
    elif title_text == 'USERNAME INFO': card_title = '𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗜𝗡𝗙𝗢'
    elif title_text == 'TG ID INFO':    card_title = '𝗧𝗚 𝗜𝗗 𝗜𝗡𝗙𝗢'
    else: card_title = '𝗨𝗦𝗘𝗥 𝗜𝗡𝗙𝗢'

    # Strip country code prefix
    _ph_display = phone
    if phone and cc:
        _cc_digits = cc.replace('+', '').strip()
        if _cc_digits and _ph_display.startswith(_cc_digits):
            _stripped = _ph_display[len(_cc_digits):]
            if len(_stripped) >= 7:
                _ph_display = _stripped
    num_display = (f"<b>+{cc.replace('+','')} {_ph_display}</b>" if phone and cc
                   else f"<b>{phone}</b>" if phone
                   else "🔒 Not Available")

    def _pe(eid, fb): return f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"
    _L = _pe("5465629669829128119","➿")*10

    # Credits left line
    _cr_line = ""
    if credits_left is not None:
        _cr_line = f"\n<tg-emoji emoji-id='5379600444098093058'>🪙</tg-emoji> ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ:- <b>{credits_left}</b>"

    # Clean card — no pfp
    txt = (
        f"<blockquote>{_L}\n"
        f"{_pe('6318752565865482087','🔍')} <b>{card_title}</b>\n"
        f"{_L}\n"
        f"{_pe('6030656587830399914','🆔')} Uꜱᴇʀ Iᴅᴇɴᴛɪᴛʏ\n\n"
        f"{_pe('5798459514663473705','🍾')} Nᴀᴍᴇ:- <b>{nm}</b>\n"
        f"{_pe('5913534466051021148','🌀')} Uꜱᴇʀɴᴀᴍᴇ:- {un_display}\n"
        f"{_pe('5929312878816400493','✉️')} Tɢ ɪᴅ:- <code>{tg_id if tg_id else '—'}</code>\n\n"
        f"{_pe('5789607097440147328','🩶')} Lᴏᴄᴀᴛɪᴏɴ\n\n"
        f"{_pe('6178984829585986541','🌏')} Cᴏᴜɴᴛʀʏ:- {country}\n"
        f"{_pe('6181649972757271368','⚜')} Cᴏᴅᴇ:- {cc if cc else '—'}\n"
        f"{_pe('5458568138004112273','📱')} Nᴜᴍʙᴇʀ:- {num_display}\n\n"
        f"{_L}{_cr_line}\n{_credit()}</blockquote>"
    )
    return txt, None

def fmt_userid(res,tid,searcher):
    now=_now_ist()
    return _fmt_tg_user(res,'🆔','TG ID INFO',str(tid),now)

def fmt_number_page(d, num, page=1, per_page=5):
    """Returns (text, total_pages, has_prev, has_next) for a given page"""
    SEP="━━━━━━━━━━━━━━━━━━━━━━━━━━"
    REC_SEP="──────────────────────"
    if not d or not d.get('success'):
        return (f"<blockquote>{SEP}\n📱 <b>NUMBER INFO</b>\n{SEP}\n\n"
                f"❌ No Data Found\n📱 <code>{num}</code>\n\n"
                f"{_credit()}</blockquote>"), 1, False, False

    # ── simran-num-info API format: {data: [{name,mobile,address,alt,circle,email,fname,id},...]} ──
    if d.get('_api_source') == 'simran_num':
        recs = d.get('data', [])
        if not isinstance(recs, list): recs = []
        total = len(recs)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = min(start + per_page, total)
        page_recs = recs[start:end]

        if not page_recs:
            return (f"<blockquote>{SEP}\n📱 <b>NUMBER INFO</b>\n{SEP}\n\n"
                    f"❌ No Data Found\n📱 <code>{num}</code>\n\n"
                    f"{_credit()}</blockquote>"), 1, False, False

        txt = (f"<blockquote>{SEP}\n"
               f"📱 <b>NUMBER INFO</b>\n"
               f"{SEP}\n\n"
               f"├📱 NUMBER  : <code>{num}</code>\n"
               f"└📊 RECORDS : {total} | Page {page}/{total_pages}\n\n")
        for i, rec in enumerate(page_recs, start + 1):
            nm2   = rec.get('name', 'N/A') or 'N/A'
            ft    = rec.get('fname', '') or ''
            mob   = rec.get('mobile', num) or num
            addr  = rec.get('address', '') or ''
            alt   = rec.get('alt', '') or ''
            circle= rec.get('circle', '') or ''
            email = rec.get('email', '') or ''
            rid   = rec.get('id', '') or ''
            txt += (f"{REC_SEP}\n"
                    f"👤 RECORD {i}/{total}\n"
                    f"{REC_SEP}\n"
                    f"├📟 MOBILE  : <code>{mob}</code>\n"
                    f"├👑 NAME    : {nm2}\n")
            if ft:     txt += f"├👨 FATHER  : {ft}\n"
            if addr:   txt += f"├🏠 ADDRESS : {addr}\n"
            if alt:    txt += f"├📱 ALT NUM : <code>{alt}</code>\n"
            if circle: txt += f"├📡 CIRCLE  : {circle}\n"
            if rid:    txt += f"├🆔 ID      : <code>{rid}</code>\n"
            if email:  txt += f"└📧 EMAIL   : {email}\n"
            txt += "\n"
        txt += f"{_credit()}</blockquote>"
        return txt, total_pages, page > 1, page < total_pages

    # ── r-bot-number-to-info API format: {success, type, count, results: [...]} ──
    if d.get('_api_source') == 'rbot':
        recs = d.get('results', [])
        if not isinstance(recs, list): recs = []
        total = d.get('count', len(recs))  # API gives count directly
        total_pages = max(1, (len(recs) + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = min(start + per_page, len(recs))
        page_recs = recs[start:end]

        txt = (f"<blockquote>{SEP}\n"
               f"📱 <b>NUMBER INFO</b>\n"
               f"{SEP}\n\n"
               f"├📱 NUMBER  : <code>{num}</code>\n"
               f"└📊 RECORDS : {total} | Page {page}/{total_pages}\n\n")
        for i, rec in enumerate(page_recs, start + 1):
            nm2   = rec.get('name', 'N/A') or 'N/A'
            ft    = rec.get('fname', '') or ''
            mob   = rec.get('mobile', num) or num
            addr  = rec.get('address', '') or ''
            alt   = rec.get('alt', '') or ''
            circle= rec.get('circle', '') or ''
            email = rec.get('email', '') or ''
            rid   = rec.get('id', '') or ''
            txt += (f"{REC_SEP}\n"
                    f"👤 RECORD {i}/{total}\n"
                    f"{REC_SEP}\n"
                    f"├📟 MOBILE  : <code>{mob}</code>\n"
                    f"├👑 NAME    : {nm2}\n")
            if ft:     txt += f"├👨 FATHER  : {ft}\n"
            if addr:   txt += f"├🏠 ADDRESS : {addr}\n"
            if alt:    txt += f"├📱 ALT NUM : <code>{alt}</code>\n"
            if circle: txt += f"├📡 CIRCLE  : {circle}\n"
            if rid:    txt += f"├🆔 ID      : <code>{rid}</code>\n"
            if email:  txt += f"└📧 EMAIL   : {email}\n"
            txt += "\n"
        txt += f"{_credit()}</blockquote>"
        return txt, total_pages, page > 1, page < total_pages

    # ── API 2 ka apna format ──
    if d.get('_api_source')=='api2':
        # API2 flat response — operator/circle/telecom info wala
        name   = d.get('name','N/A')
        mobile = d.get('mobile',d.get('phone',num))
        op     = d.get('operator',d.get('telecom',d.get('network','N/A')))
        circle = d.get('circle',d.get('state',d.get('region','N/A')))
        city   = d.get('city',d.get('location','N/A'))
        ctype  = d.get('connection_type',d.get('type','N/A'))
        roam   = d.get('roaming','N/A')
        mnc    = d.get('mnc','')
        mcc    = d.get('mcc','')
        series = d.get('series',d.get('prefix','N/A'))
        # Nested data check
        inner = d.get('data',{}) or {}
        if isinstance(inner,dict):
            if name=='N/A' and inner.get('name'): name=inner.get('name')
            if op=='N/A' and inner.get('operator'): op=inner.get('operator')
            if circle=='N/A' and inner.get('circle'): circle=inner.get('circle')
            if city=='N/A' and inner.get('city'): city=inner.get('city')
        txt=(f"<blockquote>{SEP}\n"
             f"📱 <b>NUMBER INFO</b>\n"
             f"{SEP}\n\n"
             f"├📟 NUMBER   : <code>{mobile}</code>\n")
        if name and name!='N/A': txt+=f"├👑 NAME     : {name}\n"
        txt+=(f"├📡 OPERATOR : {op}\n"
              f"├🗺️ CIRCLE   : {circle}\n")
        if city and city!='N/A': txt+=f"├🏙️ CITY     : {city}\n"
        if ctype and ctype!='N/A': txt+=f"├🔌 TYPE     : {ctype}\n"
        if roam and roam not in ('N/A','null','None',None,''): txt+=f"├✈️ ROAMING  : {roam}\n"
        if series and series!='N/A': txt+=f"├🔢 SERIES   : {series}\n"
        if mnc: txt+=f"├🏷️ MNC      : {mnc}\n"
        if mcc: txt+=f"└🏷️ MCC      : {mcc}\n"
        txt+=f"\n{_credit()}</blockquote>"
        return txt, 1, False, False

    # ── API 1 format (records list) ──
    E1="<tg-emoji emoji-id='5465144557568010803'>⭐</tg-emoji>"
    HDR_SEP = "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    recs=[d[k] for k in sorted(d.keys()) if k.isdigit() and d[k]]
    total=len(recs); total_pages=max(1,(total+per_page-1)//per_page)
    page=max(1,min(page,total_pages))
    start=(page-1)*per_page; end=min(start+per_page,total)
    page_recs=recs[start:end]
    txt=(f"<blockquote>{HDR_SEP}\n"
         f"📱 <b>NUMBER INFO</b>\n"
         f"{HDR_SEP}\n\n"
         f"├📱 NUMBER : <code>{num}</code>\n"
         f"└📊 RECORDS: {total} | Page {page}/{total_pages}\n\n")
    for i,rec in enumerate(page_recs, start+1):
        nm2=rec.get('name','N/A')
        ft=rec.get('fname',rec.get('father_name','N/A'))
        mob=rec.get('mobile',num)
        addr=rec.get('address','N/A')
        alt=rec.get('alt_num',rec.get('alternate_number',''))
        circle=rec.get('circle',rec.get('operator_circle',''))
        email=rec.get('email','')
        tid=rec.get('id',rec.get('telecom_id',''))
        txt+=(f"{REC_SEP}\n"
              f"👤 RECORD {i}/{total}\n"
              f"{REC_SEP}\n"
              f"├📟 MOBILE  : <code>{mob}</code>\n"
              f"├👑 NAME    : {nm2}\n"
              f"├👨 FATHER  : {ft}\n"
              f"├🏠 ADDRESS : {addr}\n")
        if alt:    txt+=f"├📱 ALT NUM : <code>{alt}</code>\n"
        if circle: txt+=f"├📡 CIRCLE  : {circle}\n"
        if tid:    txt+=f"├🆔 ID      : <code>{tid}</code>\n"
        if email:  txt+=f"└📧 EMAIL   : {email}\n"
        txt+="\n"
    txt+=(f"{_credit()}</blockquote>")
    return txt, total_pages, page>1, page<total_pages

def fmt_number(d,num,s):
    """Legacy wrapper — single page (used when no pagination needed)"""
    txt,_,_,_=fmt_number_page(d,num,1)
    return txt

# Per-user number result cache for pagination
_num_cache={}   # uid -> {'data':d,'num':num,'page':cur_page,'total':total_pages}

def fmt_aadhar(r,an,s):
    if not r or not r.get('success'):
        return (f"<blockquote>📋 🆔 <b>{_s('AADHAR INFO')}</b>\n\n❌ {_s('No Data')}\n🆔 <code>{an}</code>\n\n"
                f"{_F}\n{_credit()}</blockquote>")
    dl=r.get('data',[]); tot=r.get('total_records',0)
    txt=(f"<blockquote>📋 🆔 <b>{_s('AADHAR INFO')}</b>\n\n"
         f"├🆔 {_s('AADHAR')}: <code>{an}</code>\n└📊 {_s('RECORDS')}: {tot}\n\n")
    for i,rec in enumerate(dl,1):
        txt+=(f"{_F}\n📌 {_s('RECORD')} {i}\n{_F}\n"
              f"├👑 {_s('NAME')}: {rec.get('name','N/A')}\n"
              f"├👨 {_s('FATHER')}: {rec.get('father_name','N/A')}\n"
              f"├📱 {_s('MOBILE')}: <code>{rec.get('mobile','N/A')}</code>\n"
              f"└🏠 {_s('ADDRESS')}: {rec.get('address','N/A')}\n\n")
    txt+=(f"{_F}\n{_credit()}</blockquote>"); return txt

def fmt_instagram(r,un,s):
    _insta_PE = "<tg-emoji emoji-id='5281024850096301559'>📸</tg-emoji>"
    if not r:
        return (f"<blockquote>📋 {_insta_PE} <b>{_s('INSTAGRAM INFO')}</b>\n\n❌ {_s('No Data')}\n{_insta_PE} @{un}\n\n"
                f"{_F}\n{_credit()}</blockquote>"),None
    pic=r.get('pic')
    if pic and not pic.startswith('http'): pic=None
    _insta_L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"*10
    txt=(f"<blockquote>📋 {_insta_PE} <b>{_s('INSTAGRAM INFO')}</b>\n\n"
         f"👤 <b>{_s('PROFILE DETAILS')}</b>\n"
         f"├👤 {_s('USERNAME')}: @{r.get('username','N/A')}\n"
         f"├👑 {_s('NAME')}: {r.get('name','N/A')}\n"
         f"├🆔 {_s('ID')}: <code>{r.get('id','N/A')}</code>\n"
         f"├✅ {_s('VERIFIED')}: {'✅ '+_s('Yes') if r.get('verified') else '❌ '+_s('No')}\n"
         f"├🔒 {_s('PRIVATE')}: {'🔒 '+_s('Yes') if r.get('private') else '🔓 '+_s('No')}\n"
         f"├👥 {_s('FOLLOWERS')}: {r.get('followers',0)}\n"
         f"├➡️ {_s('FOLLOWING')}: {r.get('following',0)}\n"
         f"├📸 {_s('POSTS')}: {r.get('posts',0)}\n"
         f"└📝 {_s('BIO')}: {r.get('bio','None')}\n\n"
         f"{_insta_L}\n"
         f"{_credit()}</blockquote>")
    return txt,pic

def fmt_ff(r,uid_ff,s):
    if not r or not r.get('success'):
        return ("<blockquote>"+_CL_TOP()+"\n"
                f"│  🎮 FREE FIRE INFO\n"
                +_CL_BOT()+"\n\n"
                f"❌ No Data Found\n🆔 UID: <code>{uid_ff}</code>\n\n"
                f"{_F}\n{_credit()}</blockquote>"), None
    now=_now_ist()
    ban=r.get('ban_status','UNKNOWN')
    ban_str='🚫 BANNED' if 'BAN' in str(ban).upper() and 'NOT' not in str(ban).upper() else '✅ NOT BANNED'

    p1=("<blockquote>"+_CL_TOP()+"\n"
        f"│  🎮 <b>FREE FIRE INFO</b> 🔥\n"
        +_CL_BOT()+"\n"
        f"🕐 {now}\n\n"
        f"╭─── 👤 <b>PLAYER</b> ───╮\n"
        f"│ 🏷️ Name    : <b>{r.get('nickname','N/A')}</b>\n"
        f"│ 🆔 UID     : <code>{r.get('uid',uid_ff)}</code>\n"
        f"│ 🌍 Region  : {r.get('region','N/A')}\n"
        f"│ 🎖️ Level   : {r.get('level',0)}\n"
        f"│ 📈 XP      : {r.get('exp',0):,}\n"
        f"│ 👍 Likes   : {r.get('liked',0):,}\n"
        f"│ 🏆 Badges  : {r.get('badges',0)}\n"
        f"│ ⭐ Credit  : {r.get('credit_score',0)}\n"
        f"│ 📱 Version : {r.get('version','N/A')}\n"
        f"│ 🛡️ Ban     : {ban_str}\n"
        f"╰──────────────────╯\n\n"
        f"╭─── 🏆 <b>RANK</b> ───╮\n"
        f"│ 🎯 BR Rank : {r.get('rank_name','N/A')} ({r.get('rank_pts',0)} pts)\n"
        f"│ 🎯 CS Rank : {r.get('cs_rank_name','N/A')} ({r.get('cs_rank_pts',0)} pts)\n"
        f"│ 🥇 Max BR  : {r.get('max_br_name','N/A')}\n"
        f"│ 🥇 Max CS  : {r.get('max_cs_name','N/A')}\n"
        f"╰──────────────────╯\n\n"
        f"╭─── 💬 <b>SOCIAL</b> ───╮\n"
        f"│ ✍️ Bio     : {r.get('signature','—') or '—'}\n"
        f"│ 🌐 Lang    : {r.get('language','N/A')}\n"
        f"│ 🎮 Mode    : {r.get('mode','BR')}\n"
        f"╰──────────────────╯\n\n"
        f"╭─── 🐾 <b>PET</b> ───╮\n"
        f"│ 🆔 ID      : {r.get('pet_id',0)}\n"
        f"│ 🎖️ Level   : {r.get('pet_level',0)}\n"
        f"│ 📈 EXP     : {r.get('pet_exp',0)}\n"
        f"╰──────────────────╯\n\n"
        f"╭─── ⚔️ <b>CLAN</b> ───╮\n"
        f"│ 🏰 Name    : {r.get('clan_name','No Clan')}\n"
        f"│ 🆔 ID      : <code>{r.get('clan_id','N/A') or 'N/A'}</code>\n"
        f"│ 🏅 Level   : {r.get('clan_level',0)}\n"
        f"│ 👥 Members : {r.get('clan_members',0)}\n"
        f"│ 👑 Leader  : {r.get('clan_leader','N/A') or 'N/A'}\n"
        f"╰──────────────────╯\n\n"
        f"╭─── 📅 <b>DATES</b> ───╮\n"
        f"│ 📅 Created : {r.get('create_at','N/A')}\n"
        f"│ 🕒 Login   : {r.get('last_login','N/A')}\n"
        f"╰──────────────────╯\n\n"
        f"{_F}\n"
        f"{_credit()}</blockquote>")
    p2=None  # sextyinfo API doesn't return avatar URL
    return p1, p2

def fmt_ff_like(r,uid_ff,s,likes_before=0):
    now=_now_ist()
    if not r or not r.get('success'):
        return ("<blockquote>"+_CL_TOP()+"\n"
                f"│  ❤️ FF LIKE\n"
                +_CL_BOT()+"\n\n"
                f"❌ Like Failed!\n🆔 UID: <code>{uid_ff}</code>\n\n"
                f"{_F}\n{_credit()}</blockquote>")
    cooldown=r.get('cooldown',False)
    cooldown_time=r.get('cooldown_time','')
    try_after=r.get('try_after',0)
    msg=r.get('message','Like sent!') or ''
    err=r.get('error','') or ''
    nickname=r.get('nickname','') or ''
    level=r.get('level',0) or 0
    lb=int(r.get('likes_before',0) or likes_before or 0)
    la=int(r.get('likes_after',0) or 0)
    lg=int(r.get('likes_given',0) or 0)
    if lb and la and not lg:
        try: lg=la-lb
        except: pass
    if lb and lg and not la:
        try: la=lb+lg
        except: pass
    if cooldown:
        h=0; m=0
        if try_after:
            try: h=int(try_after)//60; m=int(try_after)%60
            except: pass
        time_str=f"{h}h {m}m" if h else f"{m}m"
        if cooldown_time: time_str=cooldown_time
        return ("<blockquote>"+_CL_TOP()+"\n"
                f"│  ⏰ <b>COOLDOWN ACTIVE</b>\n"
                +_CL_BOT()+"\n\n"
                f"❌ You cannot send likes yet!\n\n"
                f"⏱️ <b>Time Remaining:</b> {time_str}\n"
                f"🆔 <b>UID:</b> <code>{uid_ff}</code>\n"
                f"{'👤 <b>Player:</b> '+nickname+chr(10) if nickname else ''}"
                f"\n📌 Next available: After 12 hours cooldown\n"
                f"💡 Different UIDs also require cooldown!\n\n"
                f"{_F}\n{_credit()}</blockquote>")
    status_line="✅ <b>LIKE SENT!</b> 🎉" if not err else "⚠️ <b>LIKE SENT FAILED</b> 😐"
    total_given = lg  # total_given = likes given is la - lb
    likes_banner=(f"\n"+_CL_TOP()+"\n"
                  f"   🎉  <b>TOTAL : +{total_given} LIKES !</b> 💥\n"
                  +_CL_BOT()+"\n") if total_given>0 else ""
    return ("<blockquote>"+_CL_TOP()+"\n"
            f"   ❤️ <b>FF LIKE</b>\n"
            +_CL_BOT()+"\n\n"
            f"{status_line}\n\n"
            f"╭─── 👤 <b>PLAYER INFO</b> ───╮\n"
            f"{'│ 👤 ɴᴀᴍᴇ  : <b>'+nickname+'</b>'+chr(10) if nickname else ''}"
            f"│ 🆔 UID   : <code>{uid_ff}</code>\n"
            f"{'│ 🎖️ ʟᴇᴠᴇʟ : <b>'+str(level)+'</b>'+chr(10) if level else ''}"
            f"╰──────────────────────╯\n\n"
            f"╭─── ❤️ <b>LIKE DETAILS</b> ───╮\n"
            f"│ 👍 Likes Before : {lb}\n"
            f"│ ❤️ Likes After  : {la}\n"
            f"│ ➕ Likes Given  : {lg}\n"
            f"╰──────────────────────╯"
            f"{likes_banner}\n"
            f"🕐 {now}\n"
            f"{_F}\n{_credit()}</blockquote>")

def fmt_vehicle(r,rc,s):
    if not r or not r.get('success'):
        return (f"<blockquote>📋 🚗 <b>{_s('VEHICLE INFO')}</b>\n\n❌ {_s('No Data')}\n🚗 <code>{rc}</code>\n\n"
                f"{_F}\n{_credit()}</blockquote>")
    return (f"<blockquote>📋 🚗 <b>{_s('VEHICLE INFO')}</b>\n\n"
            f"├🚗 {_s('RC NUMBER')}: <code>{rc}</code>\n"
            f"├👑 {_s('OWNER')}: {r.get('owner_name','N/A')}\n"
            f"├📱 {_s('MOBILE')}: <code>{r.get('mobile_number','N/A')}</code>\n"
            f"├🚘 {_s('MODEL')}: {r.get('vehicle_model','N/A')}\n"
            f"├📅 {_s('REG DATE')}: {r.get('registration_date','N/A')}\n"
            f"├⛽ {_s('FUEL')}: {r.get('fuel_type','N/A')}\n"
            f"├🔧 {_s('ENGINE')}: <code>{r.get('engine_number','N/A')}</code>\n"
            f"└🛡️ {_s('INSURANCE')}: {r.get('insurance_valid_till','N/A')}\n\n"
            f"{_F}\n{_credit()}</blockquote>")


# PAGE 1: ɴᴜᴍ, ꜱᴇʟᴇᴄᴛ, ᴜꜱᴇʀɴᴀᴍᴇ, ᴛɢɪᴅ, ʙᴏᴍʙᴇʀ, ɪɴꜱᴛᴀ, ʀᴇᴅᴇᴇᴍ, ꜱᴘɪɴ, ʀᴇꜰ, NEXT, ADMIN
# PAGE 2: ꜰꜰ ɪɴꜰᴏ, ꜰꜰ ʟɪᴋᴇ, ᴠᴇʜɪᴄʟᴇ, ᴩɪɴᴄᴏᴅᴇ, ᴩᴀᴋ, ᴀᴀᴅʜᴀʀ, ᴩᴀɴ, ᴄʀᴇᴅɪᴛꜱ, ᴄʟᴏɴᴇ, ʜᴇʟᴩ, ᴏᴡɴᴇʀ

# Premium emoji IDs list (Felix ke diye hue)
_PE_IDS = [
    "5888620056551625531","5884366771913233289","5406926593698312391",
    "6325767939676964769","5253997076169115797","5301176488756788169",
    "6312140764361006715","6314298001879735512","6314162714704878982",
    "6314344267267450186","6314500762990811983","6311939527963319025",
    "6314409378971657327","5310162878894999252","5395779525772599106",
    "5350820491017874900","6120410409200521433","6238011071941057341",
    "5267193101193083992","5224450179368767019","5197269100878907942",
    "5332455502917949981","5195033767969839232","5197288647275071607",
]

def _rpe():
    """Random premium emoji id from list"""
    return random.choice(_PE_IDS)

def kb_p1(uid):
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    if not _IS_CLONE:
        # Number info — akela full width row
        mk.row(
            _KB("ɴᴜᴍʙᴇʀ ɪɴꜰᴏ", style="success", icon_custom_emoji_id="5465169893580086142"))
        # Pairs
        mk.row(
            _KB("ᴛɢ ᴜꜱᴇʀ ᴛᴏ ɴᴜᴍ", style="success", icon_custom_emoji_id="5188217332748527444"),
            _KB("ꜱᴇʟᴇᴄᴛ ᴛᴀʀɢᴇᴛ",   style="success", icon_custom_emoji_id="6109432142079466939",
                request_user=KeyboardButtonRequestUser(request_id=1, user_is_bot=False)))
        mk.row(
            _KB("ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ",  style="success", icon_custom_emoji_id="5472159355853888315"),
            _KB("ꜰʀᴇᴇ ꜰɪʀᴇ ʟɪᴋᴇ",  style="success", icon_custom_emoji_id="6208452093397699863"))
        mk.row(
            _KB("ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ",  style="success", icon_custom_emoji_id="5281024850096301559"),
            _KB("ʙᴏᴍʙᴇʀ",           style="success", icon_custom_emoji_id="5469654973308476699"))
        mk.row(
            _KB("ᴅᴀɪʟʏ ꜱᴘɪɴ",      style="success", icon_custom_emoji_id="5449800250032143374"),
            _KB("ᴡᴀʟʟᴇᴛ & ʀᴇꜰᴇʀ",  style="success", icon_custom_emoji_id="5224257782013769471"))
        mk.row(
            _KB("ꜱᴜᴩᴩᴏʀᴛ",          style="success", icon_custom_emoji_id="6269490656779965144"))
        if is_admin(uid):
            mk.row(
                _KB("ɴᴇxᴛ ᴩᴀɢᴇ",   style="danger", icon_custom_emoji_id="5832251986635920010"),
                _KB("ᴀᴅᴍɪɴ ᴩᴀɴᴇʟ", style="danger", icon_custom_emoji_id="6237699910150397736"))
        else:
            mk.row(
                _KB("ɴᴇxᴛ ᴩᴀɢᴇ",   style="danger", icon_custom_emoji_id="5832251986635920010"))
    else:
        # Clone bot — PREMIUM clone: same as original (with premium emoji icons)
        # NORMAL clone (_IS_CLASSIC): plain emoji, no icon_custom_emoji_id
        _classic = _IS_CLASSIC
        if not _classic:
            mk.row(
                _KB("ɴᴜᴍʙᴇʀ ɪɴꜰᴏ", style="success", icon_custom_emoji_id="5465169893580086142"))
            mk.row(
                _KB("ᴛɢ ᴜꜱᴇʀ ᴛᴏ ɴᴜᴍ", style="success", icon_custom_emoji_id="5188217332748527444"),
                _KB("ꜱᴇʟᴇᴄᴛ ᴛᴀʀɢᴇᴛ",   style="success", icon_custom_emoji_id="6109432142079466939",
                    request_user=KeyboardButtonRequestUser(request_id=1, user_is_bot=False)))
            mk.row(
                _KB("ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ",  style="success", icon_custom_emoji_id="5472159355853888315"),
                _KB("ꜰʀᴇᴇ ꜰɪʀᴇ ʟɪᴋᴇ",  style="success", icon_custom_emoji_id="6208452093397699863"))
            mk.row(
                _KB("ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ",  style="success", icon_custom_emoji_id="5281024850096301559"),
                _KB("ʙᴏᴍʙᴇʀ",           style="success", icon_custom_emoji_id="5469654973308476699"))
            mk.row(
                _KB("ᴅᴀɪʟʏ ꜱᴘɪɴ",      style="success", icon_custom_emoji_id="5449800250032143374"),
                _KB("ᴡᴀʟʟᴇᴛ & ʀᴇꜰᴇʀ",  style="success", icon_custom_emoji_id="5224257782013769471"))
            mk.row(
                _KB("ꜱᴜᴩᴩᴏʀᴛ",          style="success", icon_custom_emoji_id="6269490656779965144"))
            if is_admin(uid):
                mk.row(
                    _KB("ɴᴇxᴛ ᴩᴀɢᴇ",   style="danger", icon_custom_emoji_id="5832251986635920010"),
                    _KB("ᴀᴅᴍɪɴ ᴩᴀɴᴇʟ", style="danger", icon_custom_emoji_id="6237699910150397736"))
            else:
                mk.row(
                    _KB("ɴᴇxᴛ ᴩᴀɢᴇ",   style="danger", icon_custom_emoji_id="5832251986635920010"))
        else:
            # NORMAL CLONE — plain emoji, no premium icon
            mk.row(_KB("📱 ɴᴜᴍʙᴇʀ ɪɴꜰᴏ", style="success"))
            mk.row(
                _KB("👤 ᴜꜱᴇʀ ɪɴꜰᴏ", style="success"),
                _KB("🎯 ꜱᴇʟᴇᴄᴛ ᴛᴀʀɢᴇᴛ", style="success",
                    request_user=KeyboardButtonRequestUser(request_id=1, user_is_bot=False)))
            mk.row(
                _KB("🎮 ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ", style="success"),
                _KB("❤️ ꜰꜰ ʟɪᴋᴇ",        style="success"))
            mk.row(
                _KB("📸 ɪɴꜱᴛᴀɢʀᴀᴍ",  style="success"),
                _KB("💣 ʙᴏᴍʙᴇʀ",     style="success"))
            mk.row(
                _KB("🎁 ᴅᴀɪʟʏ ꜱᴘɪɴ",    style="success"),
                _KB("💰 ᴡᴀʟʟᴇᴛ & ʀᴇꜰᴇʀ", style="success"))
            mk.row(_KB("🆘 ꜱᴜᴩᴩᴏʀᴛ", style="success"))
            if is_admin(uid):
                mk.row(
                    _KB("➡️ NORMAL ɴᴇxᴛ ᴩᴀɢᴇ", style="danger"),
                    _KB("⚙️ ᴀᴅᴍɪɴ ᴩᴀɴᴇʟ",      style="danger"))
            else:
                mk.row(_KB("➡️ NORMAL ɴᴇxᴛ ᴩᴀɢᴇ", style="danger"))
    return mk

def kb_p2(uid):
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    # Both original and clone same page 2
    mk.row(
        _KB("ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ", style="success", icon_custom_emoji_id="5409008750893734809"),
        _KB("ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ", style="success", icon_custom_emoji_id="5418010521309815154"))
    mk.row(
        _KB("ʜᴇʟᴩ",         style="success", icon_custom_emoji_id="5215644719022874555"),
        _KB("ᴄʟᴏɴᴇ ʙᴏᴛ",    style="success", icon_custom_emoji_id="5372981976804366741"))
    nav=[_KB("ᴩᴀɢᴇ 1", style="danger", icon_custom_emoji_id="5469735272017043817")]
    if is_admin(uid): nav.append(_KB("ᴀᴅᴍɪɴ ᴩᴀɴᴇʟ", style="danger", icon_custom_emoji_id="5341715473882955310"))
    mk.row(*nav); return mk

def kb_bomber():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    mk.row(_KB("💣 ɴᴇᴡ ʙᴏᴍʙᴇʀ",style="success"),_KB("🔴 ꜱᴛᴏᴩ ʙᴏᴍʙᴇʀ",style="danger"))
    mk.row(_KB("🔙 ᴍᴀɪɴ ᴍᴇɴᴜ",style="danger")); return mk

def kb_admin_p1():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    if _IS_CLONE:
        mk.row(_KB("📊 DASHBOARD",style="success"),_KB("👥 USER LIST",style="success"))
        mk.row(_KB("📢 CHANNEL MGMT",style="success"),_KB("⚙️ TOGGLE FEATURES",style="success"))
        mk.row(_KB("➕ ADD CHANNEL",style="success"),_KB("➖ REMOVE CHANNEL",style="success"))
        mk.row(_KB("👥 GROUP MANAGEMENT",style="success"),_KB("🌟 GROUP WELCOME SETTINGS",style="success"))
        mk.row(_KB("👋 BOT WELCOME SETTINGS",style="success"),_KB("📜 HISTORY",style="success"))
        mk.row(_KB("🚫 BLOCK USER (ID)",style="danger"),_KB("✅ UNBLOCK USER (ID)",style="success"))
        mk.row(_KB("⚡ᴩʀᴏᴛᴇᴄᴛ ᴜꜱᴇʀ ɪɴꜰᴏ",style="primary"))
        mk.row(_KB("🎫 GEN REDEEM CODE",style="success"))
        mk.row(_KB("🎛️ GROUP CONTROL",style="primary"))
        # ── Clone bot ON/OFF toggle button ──
        _clone_ob_btn = "🔴 ᴏꜰꜰ ᴍʏ ʙᴏᴛ" if _CLONE_BOT_ACTIVE else "🟢 ᴏɴ ᴍʏ ʙᴏᴛ"
        mk.row(_KB(_clone_ob_btn, style="danger" if _CLONE_BOT_ACTIVE else "success"))
        mk.row(_KB("🔙 MAIN MENU",style="danger")); return mk
    # ── Original bot — PAGE 1 (half buttons) ──
    mk.row(_KB("📊 DASHBOARD",style="success"),_KB("👥 USER LIST",style="success"))
    mk.row(_KB("📢 BROADCAST",style="success"),_KB("💎 PREMIUM BROADCAST",style="success"))
    mk.row(_KB("📜 HISTORY",style="success"),_KB("👋 BOT WELCOME SETTINGS",style="success"))
    mk.row(_KB("⚙️ TOGGLE FEATURES",style="success"),_KB("🌟 GROUP WELCOME SETTINGS",style="success"))
    mk.row(_KB("👥 ADMIN MGMT",style="success"),_KB("📢 CHANNEL MGMT",style="success"))
    mk.row(_KB("⚡ᴩʀᴏᴛᴇᴄᴛ ᴜꜱᴇʀ ɪɴꜰᴏ",style="primary"))
    # ── Original bot ON/OFF toggle button ──
    _orig_ob_btn = "🔴 ᴏꜰꜰ ᴍʏ ʙᴏᴛ" if _MAIN_BOT_ACTIVE else "🟢 ᴏɴ ᴍʏ ʙᴏᴛ"
    mk.row(_KB(_orig_ob_btn, style="danger" if _MAIN_BOT_ACTIVE else "success"))
    mk.row(_KB("➡️ ADMIN PAGE 2",style="danger"),_KB("🔙 MAIN MENU",style="danger")); return mk

def kb_admin_p2():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    # ── Original bot — PAGE 2 (remaining buttons) ──
    mk.row(_KB("🎛️ GROUP CONTROL",style="primary"),_KB("👥 GROUP MANAGEMENT",style="success"))
    mk.row(_KB("🔗 BOT API URLS",style="primary"),_KB("🔑 BOT API KEYS",style="primary"))
    mk.row(_KB("💎 PREMIUM CLONE",style="primary"),_KB("🤖 NORMAL CLONE",style="primary"))
    mk.row(_KB("💀 REVOKE ALL PREMIUM",style="danger"))
    mk.row(_KB("💎 ADD PREMIUM",style="success"),_KB("💰 ADD CREDITS",style="success"))
    mk.row(_KB("➖ REMOVE CREDITS",style="success"),_KB("🎫 GEN REDEEM CODE",style="success"))
    mk.row(_KB("🎁 GEN PREMIUM CODE",style="success"))
    mk.row(_KB("⬅️ ADMIN PAGE 1",style="danger"),_KB("🔙 MAIN MENU",style="danger")); return mk


def kb_protect_user_panel():
    """Protect User Info sub-panel keyboard"""
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    mk.row(_KB("🔒ʜɪᴅᴇ ᴜꜱᴇʀ ɪɴꜰᴏ",style="danger"),_KB("🔓ꜱʜᴏᴡ ᴜꜱᴇʀ ɪɴꜰᴏ",style="success"))
    mk.row(_KB("👁 ᴛᴏᴛᴀʟ ʜɪᴅᴇ ᴜꜱᴇʀ",style="primary"))
    mk.row(_KB("⬅️ ᴀᴅᴍɪɴ ᴩᴀɢᴇ 1",style="danger")); return mk

def kb_group_mgmt():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    mk.row(_KB("📋 VIEW GROUPS",style="success"),_KB("➕ ADD GROUP",style="success"))
    mk.row(_KB("🔙 BACK TO ADMIN",style="danger")); return mk

def kb_welcome():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    mk.row(_KB("🖼 SET WELCOME IMAGE",style="success"),_KB("🎥 SET WELCOME VIDEO",style="success"))
    mk.row(_KB("📝 SET WELCOME CAPTION",style="success"),_KB("🎪 SET FIRST TIME STICKER",style="success"))
    mk.row(_KB("🔄 RESET TO DEFAULT",style="success"))
    mk.row(_KB("🔙 BACK TO ADMIN",style="danger")); return mk

def kb_group_welcome():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    mk.row(_KB("🖼 GROUP IMAGE SET",style="success"),_KB("🎥 GROUP VIDEO SET",style="success"))
    mk.row(_KB("🎞 GROUP VIDEO LIST",style="success"),_KB("🎪 GROUP STICKER SET",style="success"))
    mk.row(_KB("📝 GROUP WELCOME TEXT",style="success"),_KB("🔄 GROUP WELCOME RESET",style="success"))
    mk.row(_KB("🔙 BACK TO ADMIN",style="danger")); return mk

def kb_admin_mgmt():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    mk.row(_KB("➕ ADD ADMIN",style="success"),_KB("➖ REMOVE ADMIN",style="success"))
    mk.row(_KB("📋 ADMIN LIST",style="success"))
    mk.row(_KB("🔙 BACK TO ADMIN",style="danger")); return mk

def kb_channel_mgmt():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    mk.row(_KB("➕ ADD CHANNEL",style="success"),_KB("➖ REMOVE CHANNEL",style="success"))
    mk.row(_KB("📋 CHANNEL LIST",style="success"))
    mk.row(_KB("🔙 BACK TO ADMIN",style="danger")); return mk

def kb_features():
    """Feature toggle - P1 + P2 ke saare features ek hi screen pe inline ON/OFF buttons"""
    mk=InlineKeyboardMarkup(row_width=2)
    states_dict = {fn: en for fn, en in get_all_feature_states()}
    _ALL_FEATS = [
        ("number",       "📱 Number Info"),
        ("username",     "👤 Username Info"),
        ("tgid",         "🆔 TG ID Info"),
        ("aadhar",       "🪪 Aadhar Info"),
        ("instagram",    "📸 Instagram"),
        ("bomber",       "💣 Bomber"),
        ("freefire",     "🎮 Free Fire"),
        ("freefire_like","❤️ FF Like"),
        ("vehicle",      "🚗 Vehicle RC"),
    ]
    btns = []
    for fn, label in _ALL_FEATS:
        is_on = states_dict.get(fn, True)
        status = "✅" if is_on else "❌"
        btn_text = f"{status} {label}"
        btns.append(_IKB(btn_text, style="success" if is_on else "danger", callback_data=f"ftog_{fn}"))
    for i in range(0, len(btns), 2):
        mk.row(*btns[i:i+2])
    mk.add(_IKB("🔙 ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴ", style="danger", callback_data="ftog_back"))
    return mk

def kb_select_user():
    mk=ReplyKeyboardMarkup(resize_keyboard=True,row_width=1)
    mk.add(_KB("👤 SELECT USER",style="success",request_user=KeyboardButtonRequestUser(request_id=1,user_is_bot=False)))
    mk.add(_KB("🔙 CANCEL",style="success"))
    return mk

def kb_groups_inline(page=1):
    groups=get_all_groups()
    if not groups: return None
    pp=5; st=(page-1)*pp; en=st+pp; tp=(len(groups)+pp-1)//pp
    mk=InlineKeyboardMarkup(row_width=1)
    for gid,title in groups[st:en]:
        g=get_group(gid); s=safe_g(g,7); bl=safe_g(g,6); mu=safe_g(g,8)
        mi="🔇" if mu==1 else "🔊"
        _blk="🚫" if bl==1 else "✅"
        dn=title[:20]+"..." if len(title)>20 else title
        mk.add(_IKB(f"📌 {dn} | S:{s} {_blk}{mi}",style="primary",callback_data=f"grp_sel_{gid}"))
    nav=[]
    if page>1: nav.append(_IKB("⬅️",callback_data=f"grp_pg_{page-1}"))
    nav.append(_IKB(f"{page}/{tp}",callback_data="noop"))
    if en<len(groups): nav.append(_IKB("➡️",callback_data=f"grp_pg_{page+1}"))
    if len(nav)>1: mk.row(*nav)
    mk.add(_IKB("🔙 BACK TO ADMIN",style="danger",callback_data="grp_back_menu")); return mk

def kb_group_ctrl(gid):
    g=get_group(gid)
    if not g: return None
    bl=safe_g(g,6); mu=safe_g(g,8)
    mk=InlineKeyboardMarkup(row_width=2)
    mk.add(_IKB("✅ UNBLOCK" if bl else "🚫 BLOCK",style="danger",callback_data=f"grp_blk_{gid}"),
           _IKB("🔊 UNMUTE" if mu else "🔇 MUTE",style="primary",callback_data=f"grp_mute_{gid}"))
    mk.add(_IKB("📊 INFO",style="primary",callback_data=f"grp_info_{gid}"))
    mk.add(_IKB("🔙 BACK TO LIST",style="danger",callback_data="grp_back_list")); return mk

def refresh_group_msg(chat_id,msg_id,gid):
    g=get_group(gid); title=next((t for gi,t in get_all_groups() if gi==gid),"Unknown")
    if not g: return
    bl=safe_g(g,6); s=safe_g(g,7); mu=safe_g(g,8)
    txt=(f"<blockquote>👥 <b>ɢʀᴏᴜᴩ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</b>\n\n"
         f"📌 <b>{title}</b>\n🆔 <code>{gid}</code>\n"
         f"{_F}\n"
         f"🚫 Block: {'🚫 YES' if bl else '✅ NO'} | 🔇 Mute: {'🔇 YES' if mu else '🔊 NO'}\n"
         f"🔍 Total Searches: <code>{s}</code>\n"
         f"{_F}\n⚡ @Felix_modz1</blockquote>")
    try: bot.edit_message_text(txt,chat_id,msg_id,reply_markup=kb_group_ctrl(gid),parse_mode='HTML')
    except: pass

def kb_menu_p1(uid=None):
    """Menu page 1 - screenshot jaisi: Check Number, Choose User, Check Username, TG ID Info, Aadhar, Instagram, My Credits, Channel, Help, NEXT, CLOSE"""
    mk=InlineKeyboardMarkup(row_width=2)
    # Row 1
    row1=[]
    if is_feature_enabled('number'): row1.append(_IKB("ɴᴜᴍʙᴇʀ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5465169893580086142",callback_data="menu_number"))
    row1.append(_IKB("ꜱᴇʟᴇᴄᴛ ᴜꜱᴇʀ",style="primary",icon_custom_emoji_id="6109432142079466939",callback_data="menu_select_user"))
    if row1: mk.add(*row1)
    # Row 2
    row2=[]
    if is_feature_enabled('username'): row2.append(_IKB("ᴜꜱᴇʀɴᴀᴍᴇ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5258362837411045098",callback_data="menu_username"))
    if is_feature_enabled('tgid'): row2.append(_IKB("ᴛɢ ɪᴅ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5188217332748527444",callback_data="menu_tgid"))
    if row2: mk.add(*row2)
    # Row 3
    row3=[]
    if is_feature_enabled('aadhar'): row3.append(_IKB("ᴀᴀᴅʜᴀʀ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5431577498364158238",callback_data="menu_aadhar"))
    if is_feature_enabled('instagram'): row3.append(_IKB("ɪɴꜱᴛᴀ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5281024850096301559",callback_data="menu_instagram"))
    if row3: mk.add(*row3)
    # Row 4
    mk.row(_IKB("ᴍʏ ᴄʀᴇᴅɪᴛꜱ",style="primary",icon_custom_emoji_id="5379600444098093058",callback_data="menu_mycredits"),
           _IKB("ᴄʜᴀɴɴᴇʟ",style="primary",icon_custom_emoji_id="5258021357446268553",callback_data="menu_channel"))
    # Row 5
    mk.row(_IKB("ʜᴇʟᴩ",style="primary",icon_custom_emoji_id="5215644719022874555",callback_data="menu_helpinfo"),
           _IKB("ɴᴇxᴛ ➡️",style="success",icon_custom_emoji_id="5832251986635920010",callback_data="menu_p2"))
    # Row 6 - close full width
    mk.add(_IKB("ᴄʟᴏꜱᴇ",style="danger",icon_custom_emoji_id="5471937446368975982",callback_data="menu_close"))
    return mk

def kb_menu_p2(uid=None):
    """Menu page 2 - sirf enabled features dikhao, disabled hide karo"""
    mk=InlineKeyboardMarkup(row_width=2)
    row1=[]
    if is_feature_enabled('freefire'): row1.append(_IKB("ꜰꜰ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5472159355853888315",callback_data="menu_freefire"))
    if is_feature_enabled('freefire_like'): row1.append(_IKB("ꜰꜰ ʟɪᴋᴇ",style="primary",icon_custom_emoji_id="6208452093397699863",callback_data="menu_freefire_like"))
    if row1: mk.add(*row1)
    row2=[]
    if is_feature_enabled('vehicle'): row2.append(_IKB("ᴠᴇʜɪᴄʟᴇ",style="primary",icon_custom_emoji_id="5372981976804366741",callback_data="menu_vehicle"))
    if is_feature_enabled('bomber'): row2.append(_IKB("ʙᴏᴍʙᴇʀ",style="primary",icon_custom_emoji_id="5469654973308476699",callback_data="menu_bomber"))
    if row2: mk.add(*row2)
    mk.add(_IKB("⬅️ ʙᴀᴄᴋ",style="success",icon_custom_emoji_id="5469735272017043817",callback_data="menu_p1"),
           _IKB("ᴄʟᴏꜱᴇ",style="danger",icon_custom_emoji_id="5471937446368975982",callback_data="menu_close")); return mk

@bot.message_handler(commands=['start'])
def cmd_start(msg):
  try:
    if msg.chat.type == 'channel': return  # channel pe ignore
    uid=msg.from_user.id; uname=msg.from_user.username or ""; fname=_html.escape(msg.from_user.first_name or "User")

    # ── VERIFY BLOCK ──
    parts = msg.text.split()
    start_param = parts[1] if len(parts) > 1 else None

    # ── RECLONE — bot restart ke baad owner request bhejo ──
    if start_param == 'reclone' and not _IS_CLONE:
        existing = c.execute("SELECT bot_token,is_active FROM bot_clones WHERE user_id=?",(uid,)).fetchone()
        if existing:
            token, is_active = existing
            if is_active:
                bot.send_message(uid,"<blockquote>✅ Tera clone bot already active hai!</blockquote>",parse_mode='HTML')
            else:
                # Re-request bhejo owner ko
                user_state[uid] = S_CLONE
                bot.send_message(uid,
                    f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔄 <b>Re-Deploy Request</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Bot restart hua tha isliye tera clone band ho gaya.\n\n"
                    f"📌 Apna <b>Bot Token</b> bhejo — owner review karega.\n"
                    f"━━━━━━━━━━━━━━━━━━━━</blockquote>",parse_mode='HTML')
        else:
            bot.send_message(uid,"<blockquote>❌ Tera koi clone nahi hai.\n\n📌 Clone ke liye 20 referrals chahiye!</blockquote>",parse_mode='HTML')
        return
    # ── RECLONE END ──

    if start_param and start_param.startswith('verify_'):
        token = start_param[7:]
        today = datetime.now().strftime("%Y-%m-%d")
        if not get_user(uid):
            add_user(uid, uname, fname, None)
        row = c.execute("SELECT user_id FROM verify_tokens WHERE token=?", (token,)).fetchone()
        if not row:
            bot.reply_to(msg, "<blockquote>❌ Invalid verify link!</blockquote>", parse_mode='HTML'); return
        if row[0] != uid:
            bot.reply_to(msg, "<blockquote>❌ Ye link tumhara nahi hai!</blockquote>", parse_mode='HTML'); return
        if c.execute("SELECT id FROM verify_claims WHERE user_id=? AND claim_date=?", (uid, today)).fetchone():
            bot.reply_to(msg, "<blockquote>⚠️ Aaj already verify kar chuke ho!</blockquote>", parse_mode='HTML'); return
        c.execute("INSERT INTO verify_claims(user_id, claim_date) VALUES (?,?)", (uid, today))
        c.execute("UPDATE users SET credits = credits + 5 WHERE user_id=?", (uid,))
        c.execute("DELETE FROM verify_tokens WHERE token=?", (token,))
        conn.commit()
        bot.reply_to(msg, (f"<blockquote>{_F}\n"
                      f"✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥!\n{_F}\n\n"
                      f"🎉 <b>+5 Credits</b> mil gaye!\n"
                      f"📅 Kal dobara verify kar sakte ho.\n"
                      f"{_F}\n👨‍💻 𝐃𝐄𝐕 : @Felix_modz1</blockquote>"), parse_mode='HTML')
        return
    # ── VERIFY BLOCK END ──

    try:
        # Reaction sirf non-clone ya non-felix-group pe do
        _skip_react = _IS_CLONE and _is_felix_chat(msg.chat.id, getattr(msg.chat, 'username', None))
        if not _skip_react:
            bot.set_message_reaction(
                msg.chat.id,
                msg.message_id,
                [telebot.types.ReactionTypeEmoji("⚡")],
                is_big=True
            )
    except: pass

    if msg.chat.type in ['group','supergroup']:
        add_group_to_db(msg.chat.id,msg.chat.title or "Unknown")
        if _IS_CLONE and _is_felix_chat(msg.chat.id, msg.chat.username): return
        user=get_user(uid)
        if not user: add_user(uid,uname,fname)
        credits=get_credits(uid)
        try: bn=_get_bot_username()
        except: bn="felix_modz1"
        st=get_welcome_settings()
        wvid=st[4] if st else None; wimg=st[3] if st else None

        cr_disp = "∞" if is_admin(uid) else str(credits)

        if _IS_CLONE and _IS_CLASSIC:
            # NORMAL CLONE group /start — plain emoji
            txt = (
                f"<blockquote>━━━━━━━━━━━\n"
                f"🤖 NORMAL ᴍᴇɴᴜ ᴏᴩᴇɴᴇᴅ!\n"
                f"━━━━━━━━━━━\n\n"
                f"👤 ɴᴀᴍᴇ : <a href='tg://user?id={uid}'><b>{fname}</b></a>\n"
                f"🆔 ɪᴅ   : <code>{uid}</code>\n\n"
                f"💰 ᴄʀᴇᴅɪᴛꜱ : {cr_disp}\n"
                f"━━━━━━━━━━━\n"
                f"👇 ᴄʟɪᴄᴋ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴜꜱᴇ ꜰᴇᴀᴛᴜʀᴇ:\n"
                f"</blockquote>"
            )
        elif _IS_CLONE:
            # PREMIUM CLONE group /start — same premium design, footer = owner
            def _te_gs(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
            E11 = "5041866884778034602"
            E13 = "6145434301711259786"
            txt = (
                f"<blockquote>╭━━━━━━━━━━━━━✦\n"
                f"│ {_te_gs(E11)} ᴍᴇɴᴜ ᴏᴩᴇɴᴇᴅ!\n"
                f"╰━━━━━━━━━━━━━✦\n\n"
                f"<tg-emoji emoji-id='6035084557378654059'>👤</tg-emoji> ɴᴀᴍᴇ : <a href='tg://user?id={uid}'><b>{fname}</b></a>\n"
                f"<tg-emoji emoji-id='6039614175917903752'>✏</tg-emoji> ɪᴅ   : <code>{uid}</code>\n\n"
                f"<tg-emoji emoji-id='5379600444098093058'>🪙</tg-emoji> ᴄʀᴇᴅɪᴛꜱ : {cr_disp}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{_te_gs(E13)} ᴄʟɪᴄᴋ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴜꜱᴇ ꜰᴇᴀᴛᴜʀᴇ:\n"
                f"</blockquote>"
            )
        else:
            # ORIGINAL BOT group /start
            def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
            E11 = "5041866884778034602"
            E13 = "6145434301711259786"
            txt = (
                f"<blockquote>╭━━━━━━━━━━━━━✦\n"
                f"│ {_te(E11)} ᴍᴇɴᴜ ᴏᴩᴇɴᴇᴅ!\n"
                f"╰━━━━━━━━━━━━━✦\n\n"
                f"<tg-emoji emoji-id=\"6035084557378654059\">👤</tg-emoji> ɴᴀᴍᴇ : <a href='tg://user?id={uid}'><b>{fname}</b></a>\n"
                f"<tg-emoji emoji-id=\"6039614175917903752\">✏</tg-emoji> ɪᴅ   : <code>{uid}</code>\n\n"
                f"<tg-emoji emoji-id=\"5379600444098093058\">🪙</tg-emoji> ᴄʀᴇᴅɪᴛꜱ : {cr_disp}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{_te(E13)} ᴄʟɪᴄᴋ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴜꜱᴇ ꜰᴇᴀᴛᴜʀᴇ:\n"
                f"</blockquote>"
            )

        grp_mk=InlineKeyboardMarkup(row_width=2)
        if _IS_CLONE:
            grp_mk.add(_IKB("📞 ɴᴜᴍʙᴇʀ ɪɴꜰᴏ",style="primary",callback_data=f"grp_num_{uid}_{msg.chat.id}"))
            grp_mk.row(
                _IKB("🆔 ᴛɢ ɪᴅ ɪɴꜰᴏ",style="primary",callback_data=f"grp_usr_{uid}_{msg.chat.id}"),
                _IKB("👤 ꜱᴇʟᴇᴄᴛ ᴜꜱᴇʀ",style="primary",url=f"https://t.me/{bn}?start=dm_selectuser")
            )
            grp_mk.row(
                _IKB("📷 ɪɴꜱᴛᴀ ɪɴꜰᴏ",style="primary",callback_data=f"grp_insta_{uid}_{msg.chat.id}"),
                _IKB("🎯 ᴅᴀɪʟʏ ꜱᴘɪɴ",style="primary",callback_data=f"grp_spn_{uid}_{msg.chat.id}")
            )
            grp_mk.row(_IKB("💣 ʙᴏᴍʙᴇʀ",style="primary",callback_data=f"grp_bomb_{uid}_{msg.chat.id}"))
            grp_mk.add(_IKB("🦋 ᴄʟᴏꜱᴇ",style="danger",callback_data=f"grp_cls_{uid}"))
        else:
            grp_mk.add(_IKB("ɴᴜᴍʙᴇʀ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5465169893580086142",callback_data=f"grp_num_{uid}_{msg.chat.id}"))
            grp_mk.row(
                _IKB("ᴛɢ ɪᴅ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5188217332748527444",callback_data=f"grp_usr_{uid}_{msg.chat.id}"),
                _IKB("ꜱᴇʟᴇᴄᴛ ᴜꜱᴇʀ",style="primary",icon_custom_emoji_id="6071222227523605159",url=f"https://t.me/{bn}?start=dm_selectuser")
            )
            grp_mk.row(
                _IKB("ɪɴꜱᴛᴀ ɪɴꜰᴏ",style="primary",icon_custom_emoji_id="5281024850096301559",callback_data=f"grp_insta_{uid}_{msg.chat.id}"),
                _IKB("ᴅᴀɪʟʏ ꜱᴘɪɴ",style="primary",icon_custom_emoji_id="5449800250032143374",callback_data=f"grp_spn_{uid}_{msg.chat.id}")
            )
            grp_mk.row(_IKB("ʙᴏᴍʙᴇʀ",style="primary",icon_custom_emoji_id="5469654973308476699",callback_data=f"grp_bomb_{uid}_{msg.chat.id}"))
            grp_mk.add(_IKB("ᴄʟᴏꜱᴇ",style="danger",icon_custom_emoji_id="5471937446368975982",callback_data=f"grp_cls_{uid}"))
        # Group /start — group-specific media use karo
        gwimg2,gwvid2,gwvlist2,gwstk2=get_group_welcome_media(msg.chat.id)
        # Group /start pe sticker nahi (sirf new member join pe)
        _grp_sent=False
        if gwvlist2:
            _fid2=get_next_group_video(msg.chat.id)
            if _fid2:
                try: bot.send_video(msg.chat.id,_fid2,caption=txt,reply_markup=grp_mk,parse_mode='HTML'); _grp_sent=True
                except: pass
        if not _grp_sent and gwvid2 and os.path.exists(gwvid2):
            try:
                with open(gwvid2,'rb') as f: bot.send_video(msg.chat.id,f,caption=txt,reply_markup=grp_mk,parse_mode='HTML'); _grp_sent=True
            except: pass
        if not _grp_sent and gwimg2 and os.path.exists(gwimg2):
            try:
                with open(gwimg2,'rb') as f: bot.send_photo(msg.chat.id,f,caption=txt,reply_markup=grp_mk,parse_mode='HTML'); _grp_sent=True
            except: pass
        if not _grp_sent and wvid and os.path.exists(wvid):
            try:
                with open(wvid,'rb') as f: bot.send_video(msg.chat.id,f,caption=txt,reply_markup=grp_mk,parse_mode='HTML'); _grp_sent=True
            except: pass
        if not _grp_sent and wimg and os.path.exists(wimg):
            try:
                with open(wimg,'rb') as f: bot.send_photo(msg.chat.id,f,caption=txt,reply_markup=grp_mk,parse_mode='HTML'); _grp_sent=True
            except: pass
        if not _grp_sent:
            _send_react(msg.chat.id, txt, reply_markup=grp_mk, parse_mode='HTML')
        return
    ref=None
    if len(msg.text.split())>1:
        param=msg.text.split()[1]
        if param=="dm_selectuser":
            bot.send_message(uid,"<blockquote>👤 <b>ꜱᴇʟᴇᴄᴛ ᴜꜱᴇʀ</b>\nNeeche button dabao:</blockquote>",reply_markup=kb_select_user(),parse_mode='HTML'); return
        try:
            ref=int(param)
            if ref==uid: ref=None
        except: pass

    # ── FORCE JOIN CHECK — safe try-except mein ──
    try:
        _fj_chs = get_force_join_channels()
        _fj_channels_exist = bool(_fj_chs)
    except Exception as _fje:
        print(f"[FJ_CHECK] {_fje}")
        _fj_channels_exist = False

    if _fj_channels_exist:
        try:
            _not_joined = not check_channel(uid)
        except Exception as _cce:
            print(f"[CHECK_CH] {_cce}")
            _not_joined = False

        if _not_joined:
            try:
                mk=get_channels_keyboard(uid)
            except Exception as _mke:
                print(f"[CH_KB] {_mke}")
                mk=None
            if mk:
                # ref ko session mein save karo — verify ke baad use hoga
                if ref: user_state[uid] = {'pending_ref': ref}
                _safe_send(uid,
                    f"<tg-emoji emoji-id='5188463524568926712'>⚠️</tg-emoji> ᴊᴏɪɴ ʀᴇQᴜɪʀᴇᴅ!\n\n"
                    f" Bᴏᴛ ᴜꜱᴇ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ ɴᴇᴇᴄʜᴇ ᴋᴇ ꜱᴀʀᴇ ᴄʜᴀɴɴᴇʟꜱ ᴊᴏɪɴ ᴋᴀʀᴏ:\n\n"
                    f"Jᴏɪɴ ᴋᴀʀɴᴇ ᴋᴇ ʙᴀᴀᴅ <tg-emoji emoji-id='5289934755456889065'>🌟</tg-emoji> <b>I Jᴏɪɴᴇᴅ — Vᴇʀɪꜰʏ</b> ᴅᴀʙᴀᴏ!\n\n"
                    f"<tg-emoji emoji-id='5888781182249738113'>🆔</tg-emoji> ᴏᴡɴᴇʀ: @Felix_Bhai",
                    reply_markup=mk,parse_mode='HTML')
                return
            # mk=None — bot ko channel access nahi, proceed karo

    # ── REGISTER USER — channels joined ya koi channel nahi ──
    user=get_user(uid); is_first=not user
    if not user: add_user(uid,uname,fname,ref)
    else: is_first=(user[10]==1 if user and len(user)>10 else True)
    credits=get_credits(uid); st=get_welcome_settings()
    wvid=st[4] if st else None; wimg=st[3] if st else None

    try:
        wtxt=format_welcome(uid,fname,credits,uname)
    except Exception as _fwe:
        print(f"[FORMAT_WELCOME] {_fwe}")
        wtxt=f"<blockquote>👋 ʜᴇʟʟᴏ <a href='tg://user?id={uid}'><b>{fname}</b></a>!\n\n💰 Credits: {credits}\n\n⚡ @Felix_Bhai</blockquote>"
    # Caption ke liye tg-emoji strip hoti hai — isliye text-only welcome bhejo premium emoji ke sath
    # Sirf video/image ke liye plain caption use karo, tg-emoji wala welcome alag se bhejo
    wtxt_plain_cap = f"👋 ʜᴇʟʟᴏ <a href='tg://user?id={uid}'><b>{fname}</b></a>!\n\n💰 ᴄʀᴇᴅɪᴛꜱ: {credits}\n⚡ @Felix_Bhai"
    try: rl=f"https://t.me/{_get_bot_username()}?start={uid}"
    except: rl=f"https://t.me/bot?start={uid}"

    # Main menu keyboard (ReplyKeyboard)
    rmk=kb_p1(uid)

    # Sticker hamesha bhejo (first time + returning dono)
    stk=get_first_time_sticker()
    if stk:
        try: bot.send_sticker(uid,stk)
        except: pass

    # ── Welcome message: video/image ke saath hi wtxt + keyboard ek hi message mein ──
    sent=False
    _wv_fid = _welcome_fileid_cache.get('video')
    _wi_fid = _welcome_fileid_cache.get('image')
    if _wv_fid:
        try: bot.send_video(uid,_wv_fid,caption=wtxt,parse_mode='HTML',reply_markup=rmk,message_effect_id="5046509860389126442"); sent=True
        except Exception as _e1:
            _welcome_fileid_cache.pop('video',None)
            print(f"[START_VID_FID] {_e1}")
    if not sent and _wi_fid:
        try: bot.send_photo(uid,_wi_fid,caption=wtxt,parse_mode='HTML',reply_markup=rmk,message_effect_id="5046509860389126442"); sent=True
        except Exception as _e2:
            _welcome_fileid_cache.pop('image',None)
            print(f"[START_IMG_FID] {_e2}")
    if not sent and wvid and os.path.exists(wvid):
        try:
            with open(wvid,'rb') as f:
                sm=bot.send_video(uid,f,caption=wtxt,parse_mode='HTML',reply_markup=rmk,message_effect_id="5046509860389126442")
                if sm and sm.video: _welcome_fileid_cache['video']=sm.video.file_id
                sent=True
        except Exception as _e3:
            print(f"[START_VID] {_e3}")
    if not sent and wimg and os.path.exists(wimg):
        try:
            with open(wimg,'rb') as f:
                sm=bot.send_photo(uid,f,caption=wtxt,parse_mode='HTML',reply_markup=rmk,message_effect_id="5046509860389126442")
                if sm and sm.photo: _welcome_fileid_cache['image']=sm.photo[-1].file_id
                sent=True
        except Exception as _e4:
            print(f"[START_IMG] {_e4}")
    if sent:
        # Media + welcome text + keyboard ek hi message mein gaya — reaction add karo
        pass
    if not sent:
        # Text-only fallback — full wtxt with tg-emoji + keyboard saath
        try:
            _wm2 = _send_react(uid, wtxt, reply_markup=rmk, parse_mode='HTML', message_effect_id="5046509860389126442")
            sent=True
            # Welcome msg pe 😍 reaction
            if _wm2:
                try: bot.set_message_reaction(uid, _wm2.message_id, [telebot.types.ReactionTypeEmoji("😍")], is_big=True)
                except: pass
        except Exception as _e6:
            print(f"[START_TXT] {_e6}")
            # Last resort: plain text no parse_mode
            try:
                import re as _re5
                _plain = _re5.sub(r'<[^>]+>', '', wtxt)
                bot.send_message(uid, _plain, reply_markup=rmk)
            except: pass
    if is_first: update_user(uid,first_time=0)
    # Clone bot: main owner ko aaj ka gift do (ek baar per day)
  except Exception as _start_e:
    import traceback; traceback.print_exc()
    print(f"[CMD_START] {_start_e}")
    try: bot.send_message(msg.chat.id,"<blockquote>⚠️ Kuch error hua, dobara /start karo!\n⚡ @Felix_Bhai</blockquote>",parse_mode='HTML')
    except: pass

@bot.message_handler(commands=['menu'])
def cmd_menu(msg):
    uid=msg.from_user.id; fname=_html.escape(msg.from_user.first_name or 'User')
    # /menu sirf private mein — group pe ignore
    if msg.chat.type in ['group','supergroup']: return
    user=get_user(uid)
    if not user:
        try: bot.reply_to(msg,"<blockquote>⚠️ Pehle bot DM mein /start karo!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass
        return
    cr=get_credits(uid)
    cr_disp="∞" if is_admin(uid) else str(cr)
    txt=(
        f"<blockquote>🤖 ᴍᴀɪɴ ᴍᴇɴᴜ\n"
        f"👇 Feature select karo:\n\n"
        f"👋 ʜᴇʟʟᴏ <a href='tg://user?id={uid}'><b>{fname}</b></a>\n"
        f"💰 ᴄʀᴇᴅɪᴛꜱ: <b>{cr_disp}</b>\n"
        f"⚡ @Felix_modz1</blockquote>"
    )
    bot.reply_to(msg, txt, reply_markup=kb_p1(uid), parse_mode='HTML')

@bot.message_handler(commands=['bomb'])
def cmd_bomb(msg):
    uid=msg.from_user.id; chat_id=msg.chat.id
    if _clone_group_guard(msg): return
    if not is_feature_enabled('bomber'): return
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        bot.reply_to(msg,"<blockquote>💣 <b>Usage:</b> <code>/bomb 9876543210</code>\n⚠️ Sirf apne number par use karo!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    num=re.sub(r'\D','',parts[1])
    if len(num)==12 and num.startswith('91'): num=num[2:]
    if not re.match(r'^[6-9]\d{9}$',num):
        bot.reply_to(msg,"<blockquote>❌ Invalid! 10-digit Indian number.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if bomber_jobs.get(uid,{}).get('running',False):
        bot.reply_to(msg,"<blockquote>💣 Already running! Use /stopbomb first.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>" + pbar(0) + "\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _stop_b1=_start_anim(msg.chat.id,sm.message_id,'bomber')
    _stop_b1[0]=True
    threading.Thread(target=run_bomber,args=(uid,chat_id,num,sm.message_id),daemon=True).start()

@bot.message_handler(commands=['stopbomb'])
def cmd_stopbomb(msg):
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if uid in bomber_jobs: bomber_jobs[uid]['running']=False
    bot.reply_to(msg,"<blockquote>🔴 <b>Bomber stop signal sent!</b>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['like'])
def cmd_like(msg):
    """/like [region] uid — FF Like using likev2 system"""
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if not is_feature_enabled('freefire_like'): return
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    # /like uid  OR  /like region uid
    region="ind"; ff_uid=None
    if len(parts)==2:
        ff_uid=re.sub(r'\D','',parts[1])
    elif len(parts)>=3:
        region=parts[1].lower() if parts[1].lower() in VALID_REGIONS else "ind"
        ff_uid=re.sub(r'\D','',parts[-1])
    if not ff_uid or len(ff_uid)<5:
        rlist="\n".join([f"• {r.upper()} - {REGION_NAMES.get(r,r.upper())}" for r in VALID_REGIONS])
        bot.reply_to(msg,(f"<blockquote>{_F}\n❤️ <b>FF LIKE</b>\n{_F}\n\n"
                          f"📌 Usage:\n<code>/like uid</code>\n<code>/like region uid</code>\n\n"
                          f"Example:\n<code>/like 2819649271</code>\n<code>/like ind 2819649271</code>\n\n"
                          f"🌍 Regions:\n{rlist}\n\n"
                          f"{_F}\n⚡ @Felix_modz1\n{_F}</blockquote>"),parse_mode='HTML'); return
    if not _like_check_ratelimit(uid) and not is_admin(uid):
        bot.reply_to(msg,f"<blockquote>⚠️ Daily limit! Max {LIKE_DAILY_MAX}/day\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    can,rem,cinfo=_like_check_cooldown(uid,ff_uid)
    if not can and not is_admin(uid):
        h=int(rem//3600); mn=int((rem%3600)//60)
        bot.reply_to(msg,(f"<blockquote>{_F}\n⏰ <b>UID ON COOLDOWN</b>\n{_F}\n\n"
                          f"❌ This UID is on cooldown!\n🆔 UID: <code>{ff_uid}</code>\n"
                          f"⏱️ Remaining: {h}h {mn}m\n\n"
                          f"💡 Different UID like karo — no cooldown!\n\n"
                          f"{_F}\n⚡ @Felix_modz1\n{_F}</blockquote>"),parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    threading.Thread(target=do_ff_like_send,args=(msg.chat.id,sm.message_id,ff_uid,region,uid,msg.from_user.first_name or "User"),daemon=True).start()

# ── VIP LIKE — Owner only, dual API (like62y3 + druu) ───────────────────────
VIPLIKE_API_1 = "https://like62y3.onrender.com/like"
VIPLIKE_API_2 = "https://druu-likes-15-day.vercel.app/like"

@bot.message_handler(commands=['viplike'])
def cmd_viplike(msg):
    """/viplike uid — Owner only VIP FF Like via dual special API"""
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if uid != _MAIN_OWNER:
        try: bot.reply_to(msg,"<blockquote>❌ Owner only command!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass
        return
    parts=msg.text.split()
    if len(parts)<2:
        bot.reply_to(msg,(
            f"<blockquote>{_CL_TOP()}\n"
            f"│  💎 <b>VIP LIKE</b>\n"
            f"{_CL_BOT()}\n\n"
            f"📌 Usage: <code>/viplike uid</code>\n"
            f"ᴇxᴀᴍᴩʟᴇ: <code>/viplike 1946875262</code>\n\n"
            f"⚡ ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @FELIX_BHAI</blockquote>"
        ),parse_mode='HTML'); return
    ff_uid=re.sub(r'\D','',parts[1])
    if len(ff_uid)<5:
        bot.reply_to(msg,"<blockquote>❌ Invalid FF UID!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _sf_vip=_start_anim(msg.chat.id,sm.message_id,'viplike')

    def _do_viplike():
        import concurrent.futures as _cfl_vip

        def _call_v1():
            try:
                r=requests.get(VIPLIKE_API_1,params={"uid":ff_uid,"server_name":"ind"},timeout=30)
                if r.status_code==200: return r.json()
            except: pass
            return None

        def _call_v2():
            try:
                r=requests.get(VIPLIKE_API_2,params={"uid":ff_uid,"server_name":"ind"},timeout=30)
                if r.status_code==200: return r.json()
            except: pass
            return None

        with _cfl_vip.ThreadPoolExecutor(max_workers=2) as _ex_vip:
            _fv1=_ex_vip.submit(_call_v1); _fv2=_ex_vip.submit(_call_v2)
            dv1=_fv1.result(); dv2=_fv2.result()

        _sf_vip[0]=True
        now=_now_ist()
        total_vip=0; results_vip=""; player_vip=""
        already_vip=False

        for _lbl,_dat in [("💎 API 1 (like62y3)",dv1),("🔥 API 2 (druu)",dv2)]:
            if not _dat: continue
            _msg_v=str(_dat.get("message",_dat.get("msg",""))).lower()
            _status_v=_dat.get("status",0)
            if not player_vip:
                player_vip=_dat.get("PlayerNickname") or _dat.get("nickname") or _dat.get("name") or ""
            if "already" in _msg_v or "max" in _msg_v or "limit" in _msg_v:
                already_vip=True
                results_vip+=f"\n│ {_lbl}: ⚠️ ᴀʟʀᴇᴀᴅʏ ʟɪᴋᴇᴅ"
            elif _status_v in [1,2,3]:
                _lb=_dat.get("LikesbeforeCommand",_dat.get("likes_before",0))
                _la=_dat.get("LikesafterCommand",_dat.get("likes_after",0))
                _lg=_dat.get("LikesGivenByAPI",_dat.get("likes_given",1))
                total_vip+=int(_lg or 0)
                results_vip+=f"\n│ {_lbl}: ✅ {_lb} → {_la} (+{_lg})"
            else:
                results_vip+=f"\n│ {_lbl}: ⚠️ {_dat.get('message',_dat.get('msg','No response'))}"

        if not results_vip: results_vip="\n│ ❌ ᴋᴏɪ ʙʜɪ API ʀᴇꜱᴩᴏɴᴅ ɴᴀʜɪ ᴋɪ"

        if already_vip and total_vip==0: _icon_v="⚠️ ᴀʟʀᴇᴀᴅʏ ʟɪᴋᴇᴅ"
        elif total_vip>0: _icon_v="✅ <b>VIP LIKES SENT!</b> 🎉"
        else: _icon_v="❌ <b>LIKE FAILED</b>"

        _banner_v=("\n"+_CL_TOP()+"\n"
                   f"   🎉  <b>TOTAL : +{total_vip} VIP LIKES !</b> 💥\n"
                   +_CL_BOT()+"\n") if total_vip>0 else ""

        txt=(
            f"<blockquote>{_CL_TOP()}\n"
            f"   💎 <b>VIP LIKE RESULT</b>\n"
            f"{_CL_BOT()}\n\n"
            f"{_icon_v}\n\n"
            f"╭─── 👤 <b>PLAYER</b> ───╮\n"
            f"{'│ 🏷️ ɴᴀᴍᴇ   : <b>'+player_vip+'</b>'+chr(10) if player_vip else ''}"
            f"│ 🆔 UID    : <code>{ff_uid}</code>\n"
            f"│ 🌍 Region : 🇮🇳 IND\n"
            f"╰──────────────────╯\n\n"
            f"╭─── 📊 <b>API RESULTS</b> ───╮{results_vip}\n"
            f"╰──────────────────╯"
            f"{_banner_v}\n"
            f"🕐 {now}\n"
            f"{_F}\n⚡ @Felix_modz1</blockquote>"
        )
        try: bot.edit_message_text(txt,msg.chat.id,sm.message_id,parse_mode='HTML')
        except: bot.send_message(msg.chat.id,txt,parse_mode='HTML')

    threading.Thread(target=_do_viplike,daemon=True).start()
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['ffinfo','freefire'])
def cmd_ffinfo(msg):
    """/ffinfo <uid> — FF Info + Cloth PNG silently"""
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if not is_feature_enabled('freefire'): return
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        bot.reply_to(msg,(
            "<blockquote>"+_CL_TOP()+"\n"
            "│  🎮 <b>FF INFO</b>\n"
            +_CL_BOT()+"\n\n"
            "📌 Usage: <code>/ffinfo uid</code>\n"
            "Example: <code>/ffinfo 1382401870</code>\n\n"
            "⚡ @Felix_modz1</blockquote>"
        ),parse_mode='HTML'); return
    ff_uid=re.sub(r'\D','',parts[1])
    if len(ff_uid)<5:
        bot.reply_to(msg,"<blockquote>❌ Invalid FF UID!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user=get_user(uid)
    if not user: add_user(uid,msg.from_user.username or "",msg.from_user.first_name or "User"); user=get_user(uid)
    if not deduct_credit(uid):
        txt,mk=no_credits_msg(uid); bot.reply_to(msg,txt,reply_markup=mk,parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _sf_ff=_start_anim(msg.chat.id,sm.message_id,'freefire')
    res=api_ff(ff_uid)
    _sf_ff[0]=True
    p1,p2=fmt_ff(res,ff_uid,msg.from_user.first_name or "User")
    if not (res and res.get('success')) and not is_admin(uid): refund_credit(uid)
    try: bot.edit_message_text(p1,msg.chat.id,sm.message_id,parse_mode='HTML')
    except: bot.send_message(msg.chat.id,p1,parse_mode='HTML')
    if p2:
        try: bot.send_photo(msg.chat.id,p2,caption="🎮 <b>Player Avatar</b>",parse_mode='HTML')
        except: pass
    # Cloth silently in background
    if res and res.get('success'):
        c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                 (uid,S_FF,ff_uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
        log_search(uid,msg.from_user.first_name or "User",msg.from_user.username or "","FF INFO",ff_uid)

@bot.message_handler(commands=['numinfo'])
def cmd_numinfo(msg):
    """/numinfo <number> - Number to info"""
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if not is_feature_enabled('number'): return
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        bot.reply_to(msg,(f"<blockquote>{_F}\n✭ 𝗡𝗨𝗠𝗕𝗘𝗥 𝗜𝗡𝗙𝗢 𝗖𝗢𝗠𝗠𝗔𝗡𝗗\n{_F}\n\n"
                          f"★ 𝐔𝐬𝐚𝐠𝐞   : <code>/numinfo {{number}}</code>\n"
                          f"★ 𝐄𝐱𝐚𝐦𝐩𝐥𝐞 : <code>/numinfo 9876543210</code>\n\n"
                          f"{_F}\n👨‍💻 𝐃𝐄𝐕 : @felix_modz1\n{_F}</blockquote>"),parse_mode='HTML'); return
    num=re.sub(r'\D','',parts[1])
    if len(num)==12 and num.startswith('91'): num=num[2:]
    if not re.match(r'^[6-9]\d{9}$',num):
        bot.reply_to(msg,"<blockquote>❌ Invalid! 10-digit Indian number\n👨‍💻 𝐃𝐄𝐕 : @felix_modz1</blockquote>",parse_mode='HTML'); return
    user=get_user(uid)
    if not user: add_user(uid,msg.from_user.username or "",msg.from_user.first_name or "User"); user=get_user(uid)
    if not deduct_credit(uid):
        txt,mk=no_credits_msg(uid); bot.reply_to(msg,txt,reply_markup=mk,parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _sf_ni=_start_anim(msg.chat.id,sm.message_id,'number')
    res=api_number(num); _sf_ni[0]=True; txt=fmt_number(res,num,msg.from_user.first_name or "User")
    if not (res and res.get('success')) and not is_admin(uid): refund_credit(uid)
    try: bot.edit_message_text(txt,msg.chat.id,sm.message_id,parse_mode='HTML')
    except: bot.send_message(msg.chat.id,txt,parse_mode='HTML')
    if res and res.get('success'):
        c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                 (uid,S_NUM,num,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
        log_search(uid,msg.from_user.first_name or "User",msg.from_user.username or "","NUMBER",num)

@bot.message_handler(commands=['num2'])
def cmd_num2(msg):
    uid = msg.from_user.id
    if _clone_group_guard(msg): return
    if check_blocked_and_reply(uid): return
    if not check_channel(uid):
        mk = get_channels_keyboard(uid)
        if mk:
            bot.reply_to(msg,
                "<blockquote>⚠️ <b>ᴊᴏɪɴ ʀᴇꞯᴜɪʀᴇᴅ!</b>\n\nBot use karne ke liye channels join karo!\n\n⚡ @Felix_modz1</blockquote>",
                reply_markup=mk, parse_mode='HTML')
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, (f"<blockquote>{_F}\n✭ 𝗡𝗨𝗠𝟮 𝗜𝗡𝗙𝗢 𝗖𝗢𝗠𝗠𝗔𝗡𝗗\n{_F}\n\n"
                           f"★ 𝐔𝐬𝐚𝐠𝐞   : <code>/num2 {{number}}</code>\n"
                           f"★ 𝐄𝐱𝐚𝐦𝐩𝐥𝐞 : <code>/num2 9876543210</code>\n\n"
                           f"{_F}\n👨‍💻 𝐃𝐄𝐕 : @Felix_modz1\n{_F}</blockquote>"), parse_mode='HTML')
        return
    num = re.sub(r'\D', '', parts[1])
    if len(num) == 12 and num.startswith('91'): num = num[2:]
    if not re.match(r'^[6-9]\d{9}$', num):
        bot.reply_to(msg, "<blockquote>❌ Invalid! 10-digit Indian number daal.\n👨‍💻 𝐃𝐄𝐕 : @Felix_modz1</blockquote>", parse_mode='HTML')
        return
    if not deduct_credit(uid):
        txt, mk = no_credits_msg(uid); bot.reply_to(msg, txt, reply_markup=mk, parse_mode='HTML'); return
    sm = bot.reply_to(msg, "<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>", parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _sf_n2=_start_anim(msg.chat.id,sm.message_id,'number')
    try:
        # ── API 1: Rocky API (main info) ──
        r = requests.get("https://rocky-numbar-to-info-cfpi.vercel.app/api/index", params={"number": num}, timeout=15)
        d = r.json()
        if not d.get("success"):
            _sf_n2[0]=True
            try: bot.edit_message_text("<blockquote>❌ Data nahi mila.\n👨‍💻 𝐃𝐄𝐕 : @Felix_modz1</blockquote>", msg.chat.id, sm.message_id, parse_mode='HTML')
            except: pass
            refund_credit(uid); return

        data = d.get("data", {})
        sim = data.get("sim", {}); loc = data.get("location", {})
        device = data.get("device", {}); owner = data.get("owner", {})
        tracking = data.get("tracking", {}); status = data.get("status", {})
        mob_locs = ", ".join(loc.get("mobile_locations") or []) or "N/A"
        twr_locs = ", ".join(loc.get("tower_locations") or []) or "N/A"
        personality = ", ".join(owner.get("personality") or []) or "N/A"

        # ── API 2: r-bot API se name/father/alt/id/email ──
        owner_name = 'N/A'; father_name = 'N/A'; alt_number = 'N/A'
        owner_id = 'N/A'; owner_email = 'N/A'
        try:
            r2 = requests.get(f"https://r-bot-number-to-info-api.vercel.app/api?number={num}", timeout=12)
            d2 = r2.json()
            recs = d2.get('results') if isinstance(d2.get('results'), list) else []
            if recs:
                rec = recs[0]
                owner_name  = rec.get('name')  or 'N/A'
                father_name = rec.get('fname') or 'N/A'
                alt_number  = rec.get('alt')   or 'N/A'
                owner_id    = rec.get('id')    or 'N/A'
                owner_email = rec.get('email') or 'N/A'
        except: pass

        _sf_n2[0]=True  # animation stop
        txt = (
            f"<blockquote>{_F}\n"
            f"📱 𝗡𝗨𝗠𝟮 — 𝗡𝗨𝗠𝗕𝗘𝗥 𝗜𝗡𝗙𝗢\n{_F}\n\n"
            f"📞 𝐍𝐮𝐦𝐛𝐞𝐫     : <code>{data.get('number','N/A')}</code>\n"
            f"🌍 𝐂𝐨𝐮𝐧𝐭𝐫𝐲    : {data.get('country','N/A')}\n"
            f"🗣 𝐋𝐚𝐧𝐠𝐮𝐚𝐠𝐞   : {data.get('language','N/A')}\n"
            f"📶 𝐂𝐨𝐧𝐧𝐞𝐜𝐭𝐢𝐨𝐧 : {data.get('connection','N/A')}\n\n"
            f"📡 𝗦𝗜𝗠 𝗜𝗡𝗙𝗢\n{_F}\n"
            f"🏢 𝐎𝐩𝐞𝐫𝐚𝐭𝐨𝐫   : {sim.get('operator','N/A')}\n"
            f"📍 𝐂𝐢𝐫𝐜𝐥𝐞     : {sim.get('circle') or 'N/A'}\n\n"
            f"🗺 𝗟𝗢𝗖𝗔𝗧𝗜𝗢𝗡\n{_F}\n"
            f"🏠 𝐇𝐨𝐦𝐞𝐭𝐨𝐰𝐧   : {loc.get('hometown','N/A')}\n"
            f"📮 𝐀𝐝𝐝𝐫𝐞𝐬𝐬    : {loc.get('owner_address','N/A')}\n"
            f"📌 𝐌𝐨𝐛 𝐋𝐨𝐜    : {mob_locs}\n"
            f"📡 𝐓𝐨𝐰𝐞𝐫 𝐋𝐨𝐜  : {twr_locs}\n\n"
            f"📲 𝗗𝗘𝗩𝗜𝗖𝗘\n{_F}\n"
            f"🔢 𝐈𝐌𝐄𝐈       : <code>{device.get('imei','N/A')}</code>\n"
            f"🌐 𝐈𝐏         : <code>{device.get('ip','N/A')}</code>\n"
            f"💾 𝐌𝐀𝐂        : <code>{device.get('mac','N/A')}</code>\n\n"
            f"👤 𝗢𝗪𝗡𝗘𝗥\n{_F}\n"
            f"🧑 𝐍𝐚𝐦𝐞       : {owner_name}\n"
            f"👨 𝐅𝐚𝐭𝐡𝐞𝐫     : {father_name}\n"
            f"📞 𝐀𝐥𝐭 𝐍𝐮𝐦    : {alt_number}\n"
            f"🪪 𝐀𝐀𝐃𝐇𝐀𝐀𝐑  : {owner_id}\n"
            f"📧 𝐄𝐦𝐚𝐢𝐥      : {owner_email}\n"
            f"🧠 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐥𝐢𝐭𝐲: {personality}\n\n"
            f"🛰 𝗧𝗥𝗔𝗖𝗞𝗜𝗡𝗚\n{_F}\n"
            f"🔑 𝐓𝐫𝐚𝐜𝐤𝐞𝐫 𝐈𝐃 : {tracking.get('tracker_id','N/A')}\n"
            f"📊 𝐇𝐢𝐬𝐭𝐨𝐫𝐲    : {tracking.get('history','N/A')}\n"
            f"⚠️ 𝐂𝐨𝐦𝐩𝐥𝐚𝐢𝐧𝐭𝐬 : {status.get('complaints','N/A')}\n"
            f"{_F}\n👨‍💻 𝐃𝐄𝐕 : @Felix_modz1</blockquote>"
        )
        try: bot.edit_message_text(txt, msg.chat.id, sm.message_id, parse_mode='HTML')
        except: bot.send_message(msg.chat.id, txt, parse_mode='HTML')
        log_search(uid, msg.from_user.first_name or "User", msg.from_user.username or "", "NUM2", num)
    except Exception as e:
        _sf_n2[0]=True
        try: bot.edit_message_text(f"<blockquote>❌ Error: <code>{_safe_err(e)}</code></blockquote>", msg.chat.id, sm.message_id, parse_mode='HTML')
        except: pass
        refund_credit(uid)

@bot.message_handler(commands=['usernum'])
def cmd_usernum(msg):
    """/usernum <@username or user_id> - user number + pfp"""
    uid=msg.from_user.id
    # Clone bot: Felix ke group/channels pe bilkul silent
    if _IS_CLONE and _is_felix_chat(msg.chat.id, msg.chat.username): return
    # Original bot sab groups pe /usernum karta hai
    if not is_feature_enabled('username'): return
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        bot.reply_to(msg,(f"<blockquote>{_F}\n✭ 𝗨𝗦𝗘𝗥 𝗡𝗨𝗠 𝗖𝗢𝗠𝗠𝗔𝗡𝗗\n{_F}\n\n"
                          f"★ 𝐔𝐬𝐚𝐠𝐞   : <code>/usernum @username</code>\n"
                          f"          : <code>/usernum 123456789</code>\n"
                          f"★ 𝐄𝐱𝐚𝐦𝐩𝐥𝐞 : <code>/usernum @durov</code>\n\n"
                          f"{_F}\n👨‍💻 𝐃𝐄𝐕 : @felix_modz1\n{_F}</blockquote>"),parse_mode='HTML'); return
    query=parts[1].strip()
    user=get_user(uid)
    if not user: add_user(uid,msg.from_user.username or "",msg.from_user.first_name or "User"); user=get_user(uid)
    if not deduct_credit(uid):
        txt,mk=no_credits_msg(uid); bot.reply_to(msg,txt,reply_markup=mk,parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _sf_un=_start_anim(msg.chat.id,sm.message_id,'usernum')
    fname=_html.escape(msg.from_user.first_name or 'User')
    res=api_full_user(query)
    _sf_un[0]=True  # ← animation stop karo
    now=_now_ist()
    stype=S_USER if (query.startswith('@') or not query.lstrip('-').isdigit()) else S_TID
    _cr_left_un = get_credits(uid) if not is_admin(uid) else '∞'
    if stype==S_USER:
        rtxt,_=_fmt_tg_user_short(res,query,now,_cr_left_un)
    else:
        rtxt,_=_fmt_tg_user(res,'🔍','USER INFO',query,now,_cr_left_un)
    if not (res and res.get('success')) and not is_admin(uid): refund_credit(uid)
    try: bot.edit_message_text(rtxt,msg.chat.id,sm.message_id,parse_mode='HTML')
    except: bot.send_message(msg.chat.id,rtxt,parse_mode='HTML')
    if res and res.get('success'):
        c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                 (uid,stype,query,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
        log_search(uid,fname,msg.from_user.username or "","USERNUM",query,None)

@bot.message_handler(commands=['infoff'])
def cmd_infoff(msg):
    """/infoff <uid> - group: only works if unlimited ON, else silent"""
    uid=msg.from_user.id; chat_type=msg.chat.type
    if _clone_group_guard(msg): return
    if not is_feature_enabled('freefire'): return
    # In group: only work if unlimited is ON, else SILENT (no reply)
    if chat_type in ['group','supergroup']:
        g=get_group(msg.chat.id)
        if not g or safe_g(g,5)!=1: return  # Silent if no unlimited
        if safe_g(g,6)==1: return  # Silent if blocked
        if safe_g(g,8)==1: return  # Silent if muted
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        if chat_type=='private':
            bot.reply_to(msg,(f"<blockquote>{_F}\n✭ /𝗶𝗻𝗳𝗼𝗳𝗳 𝗖𝗢𝗠𝗠𝗔𝗡𝗗\n{_F}\n\n"
                              f"★ 𝐔𝐬𝐚𝐠𝐞   : <code>/infoff {{uid}}</code>\n"
                              f"★ 𝐄𝐱𝐚𝐦𝐩𝐥𝐞 : <code>/infoff 2819649271</code>\n\n"
                              f"{_F}\n👨‍💻 𝐃𝐄𝐕 : @felix_modz1\n{_F}</blockquote>"),parse_mode='HTML')
        return
    ff_uid=re.sub(r'\D','',parts[1])
    if len(ff_uid)<5: return
    user=get_user(uid)
    if not user: add_user(uid,msg.from_user.username or "",msg.from_user.first_name or "User"); user=get_user(uid)
    # Group ya private — user ka credit ghata
    if not deduct_credit(uid):
        txt,mk=no_credits_msg(uid); bot.reply_to(msg,txt,reply_markup=mk,parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _sf_ioff=_start_anim(msg.chat.id,sm.message_id,'freefire')
    res=api_ff(ff_uid); _sf_ioff[0]=True; p1,p2=fmt_ff(res,ff_uid,msg.from_user.first_name or "User")
    if not (res and res.get('success')) and not is_admin(uid): refund_credit(uid)
    try: bot.edit_message_text(p1,msg.chat.id,sm.message_id,parse_mode='HTML')
    except: bot.send_message(msg.chat.id,p1,parse_mode='HTML')
    if p2: bot.send_message(msg.chat.id,p2,parse_mode='HTML')
    if res and res.get('success'):
        c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                 (uid,S_FF,ff_uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
        log_search(uid,msg.from_user.first_name or "User",msg.from_user.username or "","FF INFO",ff_uid)

@bot.message_handler(commands=['unlimited'])
def cmd_unlimited(msg):
    """/unlimited on|off|list — Group unlimited toggle (admin only)"""
    uid=msg.from_user.id
    if not is_admin(uid):
        bot.reply_to(msg,"<blockquote>\u274c Sirf admin use kar sakta hai!</blockquote>",parse_mode='HTML'); return
    parts=msg.text.split()
    usage=(
        "<blockquote>"+_F+"\n"
        "\u26a1 <b>/unlimited COMMAND</b>\n"+_F+"\n\n"
        "\u2605 <b>Usage:</b>\n"
        "  <code>/unlimited on &lt;group_id&gt;</code>\n"
        "  <code>/unlimited off &lt;group_id&gt;</code>\n"
        "  <code>/unlimited list</code> \u2014 sabhi groups ka status\n\n"
        "\u2605 <b>Example:</b>\n"
        "  <code>/unlimited on -1001234567890</code>\n"+_F+"\n"
        "\u26a1 @Felix_modz1</blockquote>"
    )
    if len(parts)<2:
        bot.reply_to(msg,usage,parse_mode='HTML'); return
    sub=parts[1].lower()
    if sub=='list':
        groups=get_all_groups()
        if not groups:
            bot.reply_to(msg,"<blockquote>\u274c Koi group nahi mila!</blockquote>",parse_mode='HTML'); return
        lines=[]
        for gid,title in groups:
            g=get_group(gid); unl=safe_g(g,5)==1
            icon="\u2705" if unl else "\u274c"
            lines.append(icon+" <code>"+str(gid)+"</code> \u2014 "+title[:25])
        txt="<blockquote>"+_F+"\n\U0001f4cb <b>GROUP UNLIMITED STATUS</b>\n"+_F+"\n\n"+"\n".join(lines)+"\n"+_F+"\n\u26a1 @Felix_modz1</blockquote>"
        bot.reply_to(msg,txt,parse_mode='HTML'); return
    if sub not in ('on','off') or len(parts)<3:
        bot.reply_to(msg,usage,parse_mode='HTML'); return
    try: gid=int(parts[2])
    except:
        bot.reply_to(msg,"<blockquote>\u274c Invalid group ID! Negative integer chahiye.\nExample: <code>-1001234567890</code></blockquote>",parse_mode='HTML'); return
    g=get_group(gid)
    if not g:
        add_group(gid,"Group "+str(gid),uid)
        g=get_group(gid)
    curr_unl=safe_g(g,5)==1; want_on=(sub=='on')
    if curr_unl==want_on:
        state="ON" if want_on else "OFF"
        bot.reply_to(msg,"<blockquote>\u2139\ufe0f Group <code>"+str(gid)+"</code> pehle se <b>unlimited "+state+"</b> hai!</blockquote>",parse_mode='HTML'); return
    toggle_group_unlimited(gid)
    new_state="\u2705 ON" if want_on else "\u274c OFF"
    bot.reply_to(msg,"<blockquote>"+_F+"\n\u26a1 <b>UNLIMITED UPDATED</b>\n"+_F+"\n\n\U0001f3f7 Group ID : <code>"+str(gid)+"</code>\n\U0001f504 Status   : <b>Unlimited "+new_state+"</b>\n\n"+_F+"\n\u26a1 @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['redeem'])
def cmd_redeem(msg):
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        user_state[uid]=S_REDEEM
        bot.reply_to(msg,"<blockquote>🎫 Send redeem code:\nExample: <code>FELIX-XXXXXX</code>\n👨‍💻 𝐃𝐄𝐕 : @felix_modz1</blockquote>",parse_mode='HTML'); return
    ok,rmsg=redeem_code_fn(uid,parts[1])
    bot.reply_to(msg,f"<blockquote>{rmsg}\n👨‍💻 𝐃𝐄𝐕 : @felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['premium'])
def cmd_premium(msg):
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        user_state[uid]=S_PREM_REDEEM
        bot.reply_to(msg,
            "<blockquote>💎 <b>ᴩʀᴇᴍɪᴜᴍ ᴄᴏᴅᴇ ʀᴇᴅᴇᴇᴍ</b>\n"
            f"{_F}\n"
            "📤 Send premium code:\n"
            "Example: <code>FPREM-XXXXXX</code>\n"
            f"{_F}\n"
            "👨‍💻 𝐃𝐄𝐕 : @felix_modz1</blockquote>",
            parse_mode='HTML'); return
    ok,rmsg=redeem_premium_code_fn(uid,parts[1])
    bot.reply_to(msg,f"<blockquote>{rmsg}\n👨‍💻 𝐃𝐄𝐕 : @felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['hello','help','h','cmd'])
def cmd_hello(msg):
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    try: bn=_get_bot_username()
    except: bn="bot"

    # Group mein sirf group commands
    if msg.chat.type in ['group','supergroup']:
        gtxt=(
            f"<blockquote>╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━✦\n"
            f"│  📋 <b>ɢʀᴏᴜᴩ ᴄᴏᴍᴍᴀɴᴅꜱ</b> ⚡\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━✦\n\n"
            f"╭─── 📱 <b>ɴᴜᴍʙᴇʀ ɪɴꜰᴏ</b> ───╮\n"
            f"│ Bas number type karo:\n"
            f"│ <code>9876543210</code> → Name, Operator, SIM\n"
            f"╰──────────────────────────╯\n\n"
            f"╭─── 👤 <b>ᴜꜱᴇʀɴᴀᴍᴇ ɪɴꜰᴏ</b> ───╮\n"
            f"│ Bas @username type karo:\n"
            f"│ <code>@username</code> → TG Number + Info\n"
            f"╰──────────────────────────╯\n\n"
            f"╭─── 🚀 <b>ᴄᴏᴍᴍᴀɴᴅꜱ</b> ───╮\n"
            f"│ /start    → ᴍᴇɴᴜ\n"
            f"│ /spin     → ᴅᴀɪʟʏ ꜱᴘɪɴ\n"
            f"│ /freespin → ɢʀᴏᴜᴩ ꜱᴘɪɴ\n"
            f"╰─────────────────╯\n\n"
            f"╭─── 🎮 <b>ꜰʀᴇᴇ ꜰɪʀᴇ</b> ───╮\n"
            f"│ /like <code>uid</code>     → ❤️ ʟɪᴋᴇꜱ\n"
            f"│ /like <code>ind uid</code>  → ʀᴇɢɪᴏɴ\n"
            f"│ /info <code>uid</code>     → 🎮 ɪɴꜰᴏ\n"
            f"╰───────────────────╯\n\n"
            f"╭─── 👤 <b>TG ᴜꜱᴇʀ</b> ───╮\n"
            f"│ /user <code>123456789</code>\n"
            f"╰────────────────────╯\n\n"
            f"╭─── 💣 <b>ʙᴏᴍʙᴇʀ</b> ───╮\n"
            f"│ /bomb <code>9876543210</code>\n"
            f"│ /stopbomb → ʙᴀɴᴅ ᴋᴀʀᴏ\n"
            f"╰──────────────────╯\n\n"
            f"╭─── 📸 <b>ɪɴꜱᴛᴀɢʀᴀᴍ</b> ───╮\n"
            f"│ /insta <code>username</code>\n"
            f"╰────────────────────╯\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>"
        )
        bot.reply_to(msg,gtxt,parse_mode='HTML')
        return

    # Private DM — full commands
    txt=(
        f"<blockquote>╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━✦\n"
        f"│  📋 <b>ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ʟɪꜱᴛ</b> ⚡\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"╭─── 🚀 <b>MAIN</b> ───╮\n"
        f"│ /start   → ʙᴏᴛ ꜱᴛᴀʀᴛ\n"
        f"│ /menu    → ᴍᴇɴᴜ\n"
        f"│ /help    → ᴄᴏᴍᴍᴀɴᴅꜱ\n"
        f"│ /redeem  → ᴄʀᴇᴅɪᴛ ᴄᴏᴅᴇ\n"
        f"│ /premium → ᴩʀᴇᴍɪᴜᴍ ᴄᴏᴅᴇ\n"
        f"│ /spin    → ᴅᴀɪʟʏ ꜱᴘɪɴ\n"
        f"╰─────────────────╯\n\n"
        f"╭─── 📱 <b>NUMBER INFO</b> ───╮\n"
        f"│ /numinfo <code>9876543210</code>\n"
        f"│ → ɴᴀᴍᴇ, ᴏᴩᴇʀᴀᴛᴏʀ, ꜱɪᴍ\n"
        f"╰──────────────────────╯\n\n"
        f"╭─── 👤 <b>USER INFO</b> ───╮\n"
        f"│ /usernum <code>@username</code>\n"
        f"│ /usernum <code>123456789</code>\n"
        f"╰────────────────────╯\n\n"
        f"╭─── 📸 <b>INSTAGRAM</b> ───╮\n"
        f"│ /insta <code>username</code>\n"
        f"╰─────────────────────╯\n\n"
        f"╭─── 🎮 <b>FREE FIRE</b> ───╮\n"
        f"│ /ffinfo <code>uid</code>\n"
        f"│ /like <code>uid</code> | /like <code>ind uid</code>\n"
        f"╰────────────────────╯\n\n"
        f"╭─── 💣 <b>BOMBER</b> ───╮\n"
        f"│ /bomb <code>9876543210</code>\n"
        f"│ /stopbomb\n"
        f"╰──────────────────╯\n\n"
        f"╭─── ⚡ <b>AUTO DETECT</b> ───╮\n"
        f"│ <code>9876543210</code> → 📱 ɴᴜᴍ\n"
        f"│ <code>@username</code>  → 👤 ᴜꜱᴇʀ\n"
        f"╰──────────────────────╯\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>"
    )
    bot.reply_to(msg,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["➡️ NEXT PAGE","➡️ ɴᴇxᴛ ᴩᴀɢᴇ","ɴᴇxᴛ ᴩᴀɢᴇ"])
def go_p2(m):
    if _clone_group_guard(m): return
    if check_blocked_and_reply(m.from_user.id): return
    user_state[m.from_user.id]=S_NONE; bot.send_message(m.from_user.id,"<blockquote>📄 <b>Page 2</b></blockquote>",reply_markup=kb_p2(m.from_user.id),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["⬅️ PAGE 1","⬅️ ᴩᴀɢᴇ 1","ᴩᴀɢᴇ 1"])
def go_p1(m):
    if _clone_group_guard(m): return
    if check_blocked_and_reply(m.from_user.id): return
    user_state[m.from_user.id]=S_NONE; bot.send_message(m.from_user.id,"<blockquote>📄 <b>Page 1</b></blockquote>",reply_markup=kb_p1(m.from_user.id),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🔙 MAIN MENU","🔙 ᴍᴀɪɴ ᴍᴇɴᴜ"])
def go_main(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    user_state[uid]=S_NONE; user=get_user(uid)
    nm=user[2] if user else "User"; un=user[1] if user else ""
    cr=get_credits(uid)
    cr_disp="∞" if is_admin(uid) else str(cr)
    # Bot owner name — clone pe clone owner, original pe Felix_bhai1
    try: _bot_owner_un = f"@{_get_bot_username()}"
    except: _bot_owner_un = "@Felix_bhai1"
    if _IS_CLONE and _IS_CLASSIC:
        txt=(
            f"<blockquote>━━━━━━━━━━━\n"
            f"🤖 NORMAL ᴍᴀɪɴ ᴍᴇɴᴜ\n"
            f"━━━━━━━━━━━\n"
            f"💰 ᴄʀᴇᴅɪᴛꜱ: <b>{cr_disp}</b>\n"
            f"━━━━━━━━━━━\n"
            f"👨‍💻 ᴅᴇᴠ : <a href='tg://user?id={OWNER_ID}'>Owner</a></blockquote>"
        )
    else:
        txt=(
            f"<blockquote>⬇️ ᴍᴀɪɴ ᴍᴇɴᴜ\n"
            f"💰 ᴄʀᴇᴅɪᴛꜱ: <b>{cr_disp}</b>\n"
            f"⚡ {_bot_owner_un}</blockquote>"
        )
    bot.send_message(uid, txt, reply_markup=kb_p1(uid), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🔙 ᴄᴀɴᴄʟᴇ" and m.chat.type=='private')
def h_cancle(m):
    uid=m.from_user.id
    if check_blocked_and_reply(uid): return
    user_state[uid]=S_NONE
    bot.send_message(uid,"<blockquote>⬇️ ᴍᴀɪɴ ᴍᴇɴᴜ</blockquote>",reply_markup=kb_p1(uid),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🔙 CANCEL","🔙 ᴄᴀɴᴄᴇʟ"])
def go_cancel(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    user_state[uid]=S_NONE
    bot.send_message(uid,"<blockquote>⬇️ ᴍᴀɪɴ ᴍᴇɴᴜ</blockquote>",reply_markup=kb_p1(uid),parse_mode='HTML')

def feat_ok(uid, fn, chat_id=None):
    if check_blocked_and_reply(uid): return False
    target = chat_id if chat_id else uid
    # Main bot OFF hone par sirf admin ke liye kaam kare, baaki users ko silent
    if not _IS_CLONE and not _MAIN_BOT_ACTIVE and not is_admin(uid):
        bot.send_message(target,"<blockquote>🔴 <b>ʙᴏᴛ ᴏꜰꜰʟɪɴᴇ</b>\nBot abhi maintenance mode mein hai.\nThodi der baad try karo.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return False
    if not is_feature_enabled(fn):
        bot.send_message(target,(
            f"<blockquote>━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🛠️ ʜᴀᴍ ɪꜱ ꜰᴇᴀᴛᴜʀᴇ ᴋᴏ ᴀᴩᴅᴀᴛᴇ ᴋᴀʀ ʀᴀʜᴇ ʜᴀɪɴ\n"
            f"📝 ᴄᴀᴜꜱᴇ: 🔧 System maintenance\n"
            f"⏳ ᴛʜᴏᴅɪ ᴅᴇʀ ᴍᴇɪɴ ᴡᴀᴩᴀꜱ ᴀᴀ ᴊᴀᴇɢᴀ!\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>"
        ),parse_mode='HTML'); return False
    return True

@bot.message_handler(func=lambda m: m.text in ["ɴᴜᴍʙᴇʀ ɪɴꜰᴏ","📱 NUMBER INFO","ɴᴜᴍʙᴇʀ ɪɴꜰᴏ","ɴᴜᴍʙᴇʀ ɪɴꜰᴏ","ɴᴜᴍʙᴇʀ ɪɴꜰᴏ"])
def h_num(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'number'): return
    user_state[uid]=S_NUM
    _cr=get_credits(uid)
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5465169893580086142')} <b>𝗡𝗨𝗠𝗕𝗘𝗥 𝗜𝗡𝗙𝗢</b>\n"
        f"{_L}\n\n"
        f"{_te('5258362837411045098')} ꜱᴇɴᴅ <b>10-ᴅɪɢɪᴛ ᴍᴏʙɪʟᴇ ɴᴜᴍʙᴇʀ</b>\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>9876543210</code>\n\n"
        f"{_te('5472146462362048818')} ᴛɪᴩ: ᴡɪᴛʜ ᴏʀ ᴡɪᴛʜᴏᴜᴛ +91\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["👤 SELECT USER","ꜱᴇʟᴇᴄᴛ ᴜꜱᴇʀ","ꜱᴇʟᴇᴄᴛ ᴜꜱᴇʀ","ꜱᴇʟᴇᴄᴛ ᴛᴀʀɢᴇᴛ"])
def h_sel(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    # ꜱᴇʟᴇᴄᴛ ᴛᴀʀɢᴇᴛ button mein request_user already hai — sirf state set karo
    user_state[uid]=S_USER

@bot.message_handler(func=lambda m: m.text in ["🔍 ᴜꜱᴇʀɴᴀᴍᴇ ᴛᴏ ɴᴜᴍ","🔍 USERNAME INFO","🔍 ᴜꜱᴇʀɴᴀᴍᴇ ɪɴꜰᴏ","ᴜꜱᴇʀɴᴀᴍᴇ ᴛᴏ ɴᴜᴍ","ᴛɢ ᴜꜱᴇʀ ᴛᴏ ɴᴜᴍ"])
def h_user(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'username'): return
    user_state[uid]=S_USER
    _cr=get_credits(uid)
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5188217332748527444')} <b>𝗧𝗚 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗧𝗢 𝗡𝗨𝗠𝗕𝗘𝗥</b>\n"
        f"{_L}\n\n"
        f"{_te('5258362837411045098')} ꜱᴇɴᴅ <b>@username</b> ʏᴀ <b>TG ID</b>\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>@durov</code> ʏᴀ <code>123456789</code>\n\n"
        f"{_te('5472146462362048818')} ᴛɪᴩ: ʏᴏᴜ ᴄᴀɴ ꜰɪɴᴅ ᴀɴʏᴏɴᴇ'ꜱ ᴜꜱᴇʀ ɪᴅ ᴜꜱɪɴɢ @userinfobot\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🆔 ᴛɢ ɪᴅ ᴛᴏ ɴᴜᴍ","🆔 TG ID INFO","🆔 ᴛɢ ɪᴅ ɪɴꜰᴏ","ᴛɢ ɪᴅ ᴛᴏ ɴᴜᴍ"])
def h_tid(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'tgid'): return
    user_state[uid]=S_TID
    _cr=get_credits(uid)
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5888620056551625531')} <b>𝗧𝗚 𝗜𝗗 𝗧𝗢 𝗡𝗨𝗠𝗕𝗘𝗥</b>\n"
        f"{_L}\n\n"
        f"{_te('5258362837411045098')} ꜱᴇɴᴅ <b>Telegram User ID</b>\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>123456789</code>\n\n"
        f"{_te('5472146462362048818')} ᴛɪᴩ: ʏᴏᴜ ᴄᴀɴ ɢᴇᴛ ɪᴅ ꜰʀᴏᴍ @userinfobot\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🆔 AADHAR INFO","🆔 ᴀᴀᴅʜᴀʀ ɪɴꜰᴏ"])
def h_adh(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'aadhar'): return
    _cr=get_credits(uid)
    user_state[uid]=S_ADH
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5350820491017874900')} <b>𝗔𝗔𝗗𝗛𝗔𝗥 𝗜𝗡𝗙𝗢</b>\n"
        f"{_L}\n\n"
        f"{_te('5258362837411045098')} ꜱᴇɴᴅ <b>12-ᴅɪɢɪᴛ Aadhar</b>\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>649964855626</code>\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["📸 ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ","📸 INSTAGRAM INFO","ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ","ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ"])
def h_insta(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'instagram'): return
    _cr=get_credits(uid)
    user_state[uid]=S_INSTA
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*10
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5309875627187254382')} <b>𝗜𝗡𝗦𝗧𝗔𝗚𝗥𝗔𝗠 𝗜𝗡𝗙𝗢</b>\n"
        f"{_L}\n\n"
        f"{_te('6273721156616852730')} ꜱᴇɴᴅ ɪɴꜱᴛᴀɢʀᴀᴍ ᴜꜱᴇʀɴᴀᴍᴇ\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>felix_bhai1</code>\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text in ["💣 ʙᴏᴍʙᴇʀ","ʙᴏᴍʙᴇʀ","ʙᴏᴍʙᴇʀ"])
def h_bomber_menu(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'bomber'): return
    _cr=get_credits(uid)
    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119")*12
    bot.send_message(uid,(
        f"<blockquote>"
        f"{_L}\n"
        f"{_te('5469654973308476699')} 𝗡𝗨𝗠𝗕𝗘𝗥 𝗕𝗢𝗠𝗕𝗘𝗥 𝗠𝗘𝗡𝗨\n"
        f"{_L}\n"
        f"{_te('5226813248900187912')} ꜰʀᴇᴇ ʙᴏᴍʙᴇʀ — SMS + Call + WA\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>4 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
        f"</blockquote>"
    ), reply_markup=kb_bomber(), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["💣 ɴᴇᴡ ʙᴏᴍʙᴇʀ","💣 NEW BOMBER"])
def h_new_bomber(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'bomber'): return
    if bomber_jobs.get(uid,{}).get('running',False):
        bot.reply_to(m,"<blockquote>Already running! Stop bomber first.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[uid]=S_BOMB
    _cr=get_credits(uid)
    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>"
        f"{_L}\n"
        f"{_te('5469654973308476699')} 𝗡𝗘𝗪 𝗕𝗢𝗠𝗕𝗘𝗥\n"
        f"{_L}\n"
        f"{_te('5258362837411045098')} ꜱᴇɴᴅ <b>10-ᴅɪɢɪᴛ ᴛᴀʀɢᴇᴛ ɴᴜᴍʙᴇʀ</b>\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>9876543210</code>\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>4 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
        f"</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🔴 ꜱᴛᴏᴩ ʙᴏᴍʙᴇʀ","🔴 STOP BOMBER"])
def h_stop_bomber(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if uid in bomber_jobs: bomber_jobs[uid]['running']=False
    user_state[uid]=S_NONE
    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*11
    bot.reply_to(m,(
        f"<blockquote>"
        f"{_L}\n"
        f"{_te('5469654973308476699')} ʙᴏᴍʙᴇʀ ꜱᴛᴏᴩᴩᴇᴅ\n"
        f"{_L}\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
        f"</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["📋 BOMBER HISTORY","📋 ʙᴏᴍʙᴇʀ ʜɪꜱᴛᴏʀʏ"])
def h_bomber_hist(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    job=bomber_jobs.get(uid,{})
    if job.get('running',False):
        el=int(time.time()-job.get('start_time',time.time()))
        txt=(f"<blockquote>💣 <b>ʙᴏᴍʙᴇʀ ʀᴜɴɴɪɴɢ</b> ⏱ 10 MIN AUTO-STOP\n\n"
             f"📱 ᴛᴀʀɢᴇᴛ: +91{job.get('number','?')}\n"
             f"📨 ꜱᴍꜱ ꜱᴇɴᴛ: {job.get('sms',0)}\n"
             f"📞 ᴄᴀʟʟꜱ ꜱᴇɴᴛ: {job.get('calls',0)}\n"
             f"🔄 ʀᴏᴜɴᴅꜱ: {job.get('rounds',0)}\n"
             f"🕐 ᴛɪᴍᴇ: {el}s\n\n"
             f"📋 BOMBER HISTORY dabao history dekhne ke liye\n⚡ @Felix_modz1</blockquote>")
    else:
        c.execute("SELECT query,search_date,result FROM search_history WHERE user_id=? AND search_type='bomber' ORDER BY search_date DESC LIMIT 1",(uid,))
        last=c.fetchone()
        if last:
            try:
                d=json.loads(last[2])
                txt=(f"<blockquote>📋 <b>ʟᴀꜱᴛ ʙᴏᴍʙᴇʀ</b>\n\n"
                     f"📱 Target: {last[0]}\n📨 SMS: {d.get('sms',0)}\n📞 Calls: {d.get('calls',0)}\n"
                     f"📅 Date: {last[1]}\n⚡ @Felix_modz1</blockquote>")
            except: txt="<blockquote>📋 No history.\n⚡ @Felix_modz1</blockquote>"
        else: txt="<blockquote>📋 No bomber history.\n⚡ @Felix_modz1</blockquote>"
    bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["💎 PAID BOMBER","💎 ᴩᴀɪᴅ ʙᴏᴍʙᴇʀ"])
def h_paid_bomber(m):
    if _clone_group_guard(m): return
    bot.reply_to(m,"<blockquote>💎 <b>ᴩᴀɪᴅ ʙᴏᴍʙᴇʀ</b>\nPremium & More Powerful!\nContact @Felix_modz1\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

def _do_group_spin(uid, fname, uname_tg, cid):
    """Group spin logic — anyone can call, handles cooldown, sends result to cid"""
    try:
        user=get_user(uid)
        if not user:
            add_user(uid, uname_tg, fname)
            user=get_user(uid)
        FS=_SEP()
        if not (is_admin(uid) or can_claim_daily(uid)):
            bot.send_message(cid,
                f"<blockquote>{FS}\n"
                f"⏰ <a href=\'tg://user?id={uid}\'><b>{fname}</b></a>\n"
                f"❌ Aaj ka spin already le chuke ho!\n🕐 Kal wapis aao!\n"
                f"{FS}\n⚡ @Felix_modz1</blockquote>", parse_mode='HTML')
            return
        dm=bot.send_dice(cid, emoji=_get_spin_emoji())
        time.sleep(5)
        cw={1:1,2:1,3:2,4:3,5:4,6:5}.get(dm.dice.value, 1)
        c.execute("UPDATE users SET credits=credits+? WHERE user_id=?",(cw,uid)); conn.commit()
        if not is_admin(uid):
            c.execute("INSERT OR IGNORE INTO daily_claims VALUES(?,?)",(uid,datetime.now().strftime("%Y-%m-%d"))); conn.commit()
        user_obj=get_user(uid); tot=user_obj[5] if user_obj else cw
        try: bn2=_get_bot_username()
        except: bn2="felix_bot"
        log_token_activity(uid,fname,uname_tg,cw,tot,"Daily Spin",bn2)
        bot.send_message(cid,
            f"<blockquote>{FS}\n"
            f"🎯 <b>ᴅᴀɪʟʏ ꜱᴩɪɴ</b>\n{FS}\n\n"
            f"<a href=\'tg://user?id={uid}\'><b>{fname}</b></a> ne spin kiya!\n\n"
            f"🎉 Won: <code>+{cw}</code> credits!\n"
            f"💰 Total: <code>{tot}</code>\n\n"
            f"{FS}\n⚡ @Felix_modz1</blockquote>", parse_mode='HTML')
    except Exception as _spin_e:
        print(f"[SPIN_ERR] {_spin_e}")

@bot.message_handler(func=lambda m: m.text in ["🎁 DAILY SPIN","🎁 ᴅᴀɪʟʏ ꜱᴘɪɴ","🎁 ᴅᴀɪʟʏ ꜱᴘɪɴ","ᴅᴀɪʟʏ ꜱᴘɪɴ","ᴅᴀɪʟʏ ꜱᴘɪɴ"])
def h_spin(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    if is_admin(uid) or can_claim_daily(uid):
        dm=bot.send_dice(uid,emoji=_get_spin_emoji()); time.sleep(5)
        cw={1:1,2:1,3:2,4:3,5:4,6:5}.get(dm.dice.value,1)
        c.execute("UPDATE users SET credits=credits+? WHERE user_id=?",(cw,uid))
        if not is_admin(uid): c.execute("INSERT OR IGNORE INTO daily_claims VALUES(?,?)",(uid,datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        _user_cache.pop(uid, None)
        user=get_user(uid); tot=user[5] if user else cw
        _SS = _SEP()
        _SE = _SEP()
        _spin_ref2 = f"https://t.me/{_get_bot_username()}?start={uid}"
        _spin_vp2 = _spin_ref2
        _spin_mk2 = InlineKeyboardMarkup()
        # Refer Share Button
        def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
        _L2 = _te("5465629669829128119")*11
        _spin_mk2.add(_IKB("ꜱʜᴀʀᴇ — +2 ᴄʀᴇᴅɪᴛ ᴩᴀᴏ", style="success",
            icon_custom_emoji_id="5253804796589402657",
            url="https://t.me/share/url?url="+_spin_vp2+"&text=Yaar+is+bot+ko+join+karo+aur+free+credits+pao!"))
        _spin_mk2.add(_IKB("ᴍʏ ᴄʀᴇᴅɪᴛꜱ ᴅᴇᴋʜᴏ", style="primary",
            icon_custom_emoji_id="5372981976804366741",
            callback_data="show_my_credits"))
        bot.send_message(uid,(
            f"<blockquote>"
            f"{_L2}\n"
            f"{_te('6242498410822244114')} ᴅᴀɪʟʏ ꜱᴘɪɴ\n"
            f"{_L2}\n"
            f"{_te('5219745609631674840')} Wᴏɴ: <code>+{cw}</code> ᴄʀᴇᴅɪᴛꜱ\n"
            f"{_te('5224257782013769471')} Tᴏᴛᴀʟ: <b>{tot}</b>\n"
            f"{_L2}\n"
            f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
            f"</blockquote>"),
            reply_markup=_spin_mk2, parse_mode='HTML')
        try: bn=_get_bot_username()
        except: bn="felix_bot"
        log_token_activity(uid,m.from_user.first_name or "User",m.from_user.username or "",cw,tot,"Daily Spin",bn)
    else:
        bot.reply_to(m,"<blockquote>❌ Already claimed today!\n⏳ Come back tomorrow!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["👥 REFERRALS","👥 ʀᴇꜰᴇʀʀᴀʟꜱ","🎯 GET REFER POINT","🎯 ɢᴇᴛ ʀᴇꜰᴇʀ ᴩᴏɪɴᴛ"])
def h_ref(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    cnt=get_referral_count(uid)
    try: lnk=f"https://t.me/{_get_bot_username()}?start={uid}"
    except: lnk=f"https://t.me/bot?start={uid}"
    cr=get_credits(uid)
    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119")*11
    mk=InlineKeyboardMarkup()
    mk.add(_IKB("ꜱʜᴀʀᴇ ʀᴇꜰᴇʀʀᴀʟ ʟɪɴᴋ",style="success",icon_custom_emoji_id="5253804796589402657",url=f"https://t.me/share/url?url={lnk}&text=Join+this+amazing+info+bot!"))
    bot.reply_to(m,(
        f"<blockquote>"
        f"{_L}\n"
        f"╭──{_te('6037622221625626773')}{_te('5253804796589402657')} ʀᴇꜰᴇʀʀᴀʟ ᴩᴀɴᴇʟ{_te('6039539366177541657')}──╮\n"
        f"{_L}\n"
        f"{_te('5224257782013769471')} Cʀᴇᴅɪᴛꜱ       : <b>{cr}</b>\n"
        f"{_te('6242498410822244114')} Tᴏᴛᴀʟ Rᴇꜰᴇʀꜱ  : <b>{cnt}</b>\n"
        f"{_te('5219745609631674840')} Bᴏɴᴜꜱ ᴩᴇʀ ʀᴇꜰᴇʀ : <b>+{REFERRAL_BONUS} ᴩᴏɪɴᴛ</b>\n\n"
        f"{_L}\n"
        f"{_te('4958689671950369798')} Yᴏᴜʀ Rᴇꜰᴇʀʀᴀʟ Lɪɴᴋ:\n"
        f"<code>{lnk}</code>\n"
        f"{_L}\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
        f"</blockquote>"
    ),reply_markup=mk,parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text in ["🎮 ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ","🎮 FREE FIRE INFO","ꜰꜰ ɪɴꜰᴏ","ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ","ꜰʀᴇᴇ ꜰɪʀᴇ ɪɴꜰᴏ"])
def h_ff(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'freefire'): return
    user_state[uid]=S_FF
    _cr=get_credits(uid)
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5350820491017874900')} <b>𝗙𝗥𝗘𝗘 𝗙𝗜𝗥𝗘 𝗙𝗨𝗟𝗟 𝗜𝗡𝗙𝗢</b>\n"
        f"{_L}\n\n"
        f"{_te('5458457963503049376')} ꜱᴇɴᴅ FF UID\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>1231557272</code>\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["❤️ ꜰʀᴇᴇ ꜰɪʀᴇ ʟɪᴋᴇ","❤️ FREE FIRE LIKE","ꜰꜰ ʟɪᴋᴇ","ꜰʀᴇᴇ ꜰɪʀᴇ ʟɪᴋᴇ","ꜰʀᴇᴇ ꜰɪʀᴇ ʟɪᴋᴇ"])
def h_ffl(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'freefire_like'): return
    user_state[uid]=S_FF_LIKE_UID
    _cr=get_credits(uid)
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5350820491017874900')} <b>𝗙𝗥𝗘𝗘 𝗙𝗜𝗥𝗘 𝗟𝗜𝗞𝗘</b>\n"
        f"{_L}\n\n"
        f"{_te('5458457963503049376')} ꜱᴇɴᴅ FF UID\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>1231557272</code>\n\n"
        f"{_te('5224450179368767019')} Default: IND\n"
        f"{_te('5447419223242449630')} Custom: <code>/like ind UID</code>\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🚗 VEHICLE INFO","🚗 ᴠᴇʜɪᴄʟᴇ ɪɴꜰᴏ"])
def h_veh(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if not feat_ok(uid,'vehicle'): return
    _cr=get_credits(uid)
    user_state[uid]=S_VEH
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L=_te("5465629669829128119")*12
    bot.reply_to(m,(
        f"<blockquote>{_L}\n"
        f"{_te('5350820491017874900')} <b>𝗩𝗘𝗛𝗜𝗖𝗟𝗘 𝗜𝗡𝗙𝗢</b>\n"
        f"{_L}\n\n"
        f"{_te('5258362837411045098')} ꜱᴇɴᴅ <b>RC Number</b>\n"
        f"ᴇxᴀᴍᴩʟᴇ: <code>MH12AB1234</code>\n\n"
        f"{_te('5224257782013769471')} Tᴏᴛᴀʟ Pᴏɪɴᴛ :- <b>{_cr} Pᴏɪɴᴛ</b>\n"
        f"{_te('5188311512791393083')} Sᴇᴀʀᴄʜ Cᴏꜱᴛ :- <b>1 Pᴏɪɴᴛ</b>\n\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}</blockquote>"
    ),parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text in ["💰 MY CREDITS","💰 ᴍʏ ᴄʀᴇᴅɪᴛꜱ","ᴍʏ ᴄʀᴇᴅɪᴛꜱ","MY CREDITS","my credits","ᴍʏ ᴄʀᴇᴅɪᴛꜱ","ᴡᴀʟʟᴇᴛ & ʀᴇꜰᴇʀ"] or (m.text and "MY CREDITS" in m.text.upper() and m.chat.type=="private"))
def h_credits(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    cr=get_credits(uid); refs=get_referral_count(uid)
    user=get_user(uid)
    is_prem=bool(user[8]) if user else False
    prem_str="💎 ᴜɴʟɪᴍɪᴛᴇᴅ" if is_prem else f"{cr}"
    spin_done=not can_claim_daily(uid)
    spin_str="✅ ᴄʟᴀɪᴍᴇᴅ" if spin_done else "🎁 ᴀᴠᴀɪʟᴀʙʟᴇ"
    try: rl=f"https://t.me/{_get_bot_username()}?start={uid}"
    except: rl="--"
    rl_short=rl
    show_v=False
    mk=InlineKeyboardMarkup(row_width=2)
    mk.row(
        _IKB("ꜱʜᴀʀᴇ ʟɪɴᴋ", style="success",
             icon_custom_emoji_id="5325685779760962109",
             url=f"https://t.me/share/url?url={rl_short}&amp;text=Join+karo!"),
        _IKB("ɢᴇᴛ ᴀᴄᴄᴇꜱꜱ", style="primary",
             icon_custom_emoji_id="5294256463219291541",
             callback_data="show_premium_plans")
    )
    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119")*11
    _cr_txt = (
        f"<blockquote>"
        f"{_L}\n"
        f"╭──{_te('6037622221625626773')}{_te('5213403875670765022')} Wᴀʟʟᴇᴛ & ʀᴇꜰᴇʀ{_te('6039539366177541657')}──╮\n"
        f"{_L}\n"
        f"{_te('5224257782013769471')} Cʀᴇᴅɪᴛꜱ      : <b>{prem_str}</b>\n"
        f"{_te('5219745609631674840')} ᴅᴀɪʟʏ ꜱᴩɪɴ  : {spin_str}\n"
        f"{_te('6285328937094485878')} ᴩʀᴇᴍɪᴜᴍ     : {'<b>ᴜɴʟɪᴍɪᴛᴇᴅ</b>' if is_prem else 'ɴᴏ'}\n\n"
        f"{_L}\n"
        f"{_te('6242498410822244114')} ʀᴇꜰᴇʀ ꜰʀɪᴇɴᴅꜱ → +{REFERRAL_BONUS} ᴄʀᴇᴅɪᴛ ᴩᴀᴏ\n"
        f"{_te('6242498410822244114')} Tᴏᴛᴀʟ ʀᴇꜰᴇʀʀᴀʟꜱ : <b>{refs}</b>\n\n"
        f"{_te('4958689671950369798')} Rᴇꜰᴇʀ ʟɪɴᴋ:\n{rl_short}\n"
        f"{_L}\n"
        f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
        f"</blockquote>"
    )
    try:
        bot.reply_to(m, _cr_txt, reply_markup=mk, parse_mode='HTML')
    except Exception as _hcr_e:
        try:
            bot.send_message(m.chat.id, _cr_txt, reply_markup=mk, parse_mode='HTML')
        except Exception as _hcs_e:
            print(f"[H_CREDITS] {_hcs_e}")

@bot.message_handler(func=lambda m: m.text in ["🎫 ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ","🎫 REDEEM CODE","ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ","ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ"])
def h_redeem(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    # Show both redeem + premium code option
    mk=InlineKeyboardMarkup(row_width=1)
    mk.add(_IKB("🎫 ʀᴇᴅᴇᴇᴍ ᴄʀᴇᴅɪᴛ ᴄᴏᴅᴇ",style="success",callback_data="redeem_credit_code"))
    mk.add(_IKB("💎 ʀᴇᴅᴇᴇᴍ ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴅᴇ",style="primary",callback_data="redeem_premium_code"))
    bot.reply_to(m,(
        f"<blockquote>{_CL_TOP()}\n"
        f"│  🎫 <b>ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ</b>\n"
        f"{_CL_BOT()}\n\n"
        f"🎫 Credit Code: <code>FELIX-XXXXXX</code>\n"
        f"💎 Premium Code: <code>FPREM-XXXXXX</code>\n\n"
        f"Kaunsa code redeem karna hai?\n\n"
        f"{_F}\n⚡ @Felix_modz1</blockquote>"
    ), reply_markup=mk, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🎫 ᴄʟᴏɴᴇ ʙᴏᴛ (50 ᴄʀᴇᴅɪᴛ ᴩᴏɪɴᴛ)","🤖 BOT CLONE","🤖 ʙᴏᴛ ᴄʟᴏɴᴇ","🤖 ᴄʟᴏɴᴇ ʙᴏᴛ","ᴄʟᴏɴᴇ ʙᴏᴛ","ᴄʟᴏɴᴇ ʙᴏᴛ"])
def h_clone(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    refs=get_referral_count(uid)
    BOT_CLONE_REF_REQUIRED = 30
    if not is_admin(uid) and refs < BOT_CLONE_REF_REQUIRED:
        needed = BOT_CLONE_REF_REQUIRED - refs
        try: rl=f"https://t.me/{_get_bot_username()}?start={uid}"
        except: rl="--"
        mk=InlineKeyboardMarkup()
        mk.add(_IKB("📤 ʀᴇꜰᴇʀ ᴋᴀʀᴏ — ᴜɴʟᴏᴄᴋ ᴄʟᴏɴᴇ",style="success",icon_custom_emoji_id="5253804796589402657",url=f"https://t.me/share/url?url={rl}"))
        # Progress bar for referrals
        _pct = int(refs / BOT_CLONE_REF_REQUIRED * 100)
        _filled = int(refs / BOT_CLONE_REF_REQUIRED * 10)
        _pbar = '█' * _filled + '░' * (10 - _filled)
        bot.reply_to(m,(
            f"<blockquote>🤖 ᴄʟᴏɴᴇ ʙᴏᴛ\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 ᴩʀᴏɢʀᴇꜱꜱ: [{_pbar}] {refs}/{BOT_CLONE_REF_REQUIRED}\n"
            f"❌ ꜱᴛɪʟʟ ɴᴇᴇᴅᴇᴅ: {needed} ᴍᴏʀᴇ ʀᴇꜰᴇʀʀᴀʟꜱ\n\n"
            f"👥 Refer karke {BOT_CLONE_REF_REQUIRED} referrals poore karo\n"
            f"   Tab apna khud ka bot clone milega! 🎉\n\n"
            f"⚡ ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai</blockquote>"
        ), reply_markup=mk, parse_mode='HTML'); return
    # Referrals complete — token maango
    user_state[uid]=S_CLONE
    bot.reply_to(m,(
        f"<blockquote>🤖 ᴄʟᴏɴᴇ ʙᴏᴛ\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴꜱ! 30 ʀᴇꜰᴇʀʀᴀʟꜱ ᴄᴏᴍᴘʟᴇᴛᴇ!\n\n"
        f"📝 ꜱᴇɴᴅ ʏᴏᴜʀ ʙᴏᴛ ᴛᴏᴋᴇɴ:\n"
        f"1️⃣ ɢᴏ ᴛᴏ @BotFather\n"
        f"2️⃣ ᴜꜱᴇ /newbot ᴄᴏᴍᴍᴀɴᴅ\n"
        f"3️⃣ ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ʙᴏᴛ ᴀɴᴅ ᴄᴏᴘʏ ᴛʜᴇ ᴛᴏᴋᴇɴ\n"
        f"4️⃣ ᴘᴀꜱᴛᴇ ᴛʜᴇ ᴛᴏᴋᴇɴ ʜᴇʀᴇ\n\n"
        f"ᴇxᴀᴍᴘʟᴇ: 1234567890:ABCdef...\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ @Felix_modz1</blockquote>"
    ),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["ℹ️ HELP","ℹ️ ʜᴇʟᴩ","ʜᴇʟᴩ","ʜᴇʟᴩ"])
def h_help(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return
    _sep="━━━━━━━━━━━━━━━━━━"
    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119")*10
    if _IS_CLONE:
        txt=(f"<blockquote>{_L}\n"
             f"{_te('5197269100878907942')} <b>ʜᴇʟᴩ — ᴄᴏᴍᴍᴀɴᴅꜱ</b>\n{_sep}\n\n"
             f"{_te('5888781182249738113')} <b>INFO LOOKUP</b>\n"
             f"{_te('5431577498364158238')} Number Info\n"
             f"{_te('5373012449597335010')} TG ID / Username Info\n"
             f"{_te('5470135030393090150')} Instagram Info\n\n"
             f"{_te('5406631276042002796')} <b>FREE FIRE</b>\n"
             f"{_te('4958734459869332468')} FF Info — player stats\n"
             f"{_te('5372926953978341366')} FF Like — send likes\n\n"
             f"{_te('5888781182249738113')} <b>GROUP COMMANDS</b>\n"
             f"/spin — Daily spin (credits)\n"
             f"/like [region] [uid] — FF like\n"
             f"/info [uid] — FF info\n"
             f"/user [userid] — TG user info\n"
             f"/bomb [number] — Call bomber\n"
             f"/stopbomb — Stop bomber\n\n"
             f"{_te('4958734459869332468')} <b>CREDITS</b>\n"
             f"/redeem [code] — redeem code\n\n"
             f"{_sep}\n"
             f"1 credit/search | FF Like = 2cr | Bomber = 4cr\n"
             f"{_L}\n"
             f"{_te('6147464060305676048')} @Felix_modz1 {_te('6147565374289220368')}\n"
             f"{_te('5888781182249738113')} ᴏᴡɴᴇʀ: @Felix_Bhai\n"
             f"{_L}</blockquote>")
    else:
        txt=(f"<blockquote>{_L}\n"
             f"{_te('5197269100878907942')} <b>ʜᴇʟᴩ — ᴄᴏᴍᴍᴀɴᴅꜱ</b>\n{_sep}\n\n"
             f"{_te('5888781182249738113')} <b>INFO LOOKUP</b>\n"
             f"{_te('5431577498364158238')} Number Info — Indian number details\n"
             f"{_te('5888781182249738113')} TG ID Info — Telegram user by ID\n"
             f"{_te('5373012449597335010')} Username Info — TG user by @username\n"
             f"{_te('5373012449597335010')} Select User — share contact\n"
             f"{_te('5888781182249738113')} Aadhar Info\n"
             f"{_te('5470135030393090150')} Instagram Info\n"
             f"{_te('5888781182249738113')} Vehicle Info\n"
             f"{_te('5888781182249738113')} PAN Info\n"
             f"{_te('5431577498364158238')} Pak Number Info\n\n"
             f"{_te('5406631276042002796')} <b>FREE FIRE</b>\n"
             f"{_te('4958734459869332468')} FF Info — player stats + outfit\n"
             f"{_te('5372926953978341366')} FF Like — send likes to UID\n\n"
             f"{_te('5888781182249738113')} <b>BOMBER</b>\n"
             f"/bomb [10-digit number]\n"
             f"/stopbomb — stop running bomber\n\n"
             f"{_te('5888781182249738113')} <b>GROUP COMMANDS</b>\n"
             f"/spin — Daily spin\n"
             f"/like [region] [uid] — FF like\n"
             f"/info [uid] — FF player info\n"
             f"/user [userid] — TG user info\n\n"
             f"{_te('4958734459869332468')} <b>CREDITS</b>\n"
             f"{_te('5197269100878907942')} Daily Spin — earn credits\n"
             f"{_te('5465300082628763143')} Refer friends — earn credits\n"
             f"/redeem [code] — redeem code\n\n"
             f"{_te('5888781182249738113')} <b>CLONE BOT</b>\n"
             f"Bot clone karo — apna bot banao!\n\n"
             f"{_sep}\n"
             f"1 cr/search | FF Like=2cr | Bomber=4cr\n"
             f"{_L}\n"
             f"{_te('6147464060305676048')} @Felix_modz1 {_te('6147565374289220368')}\n"
             f"{_te('5888781182249738113')} ᴏᴡɴᴇʀ: @Felix_Bhai\n"
             f"{_L}</blockquote>")
    bot.reply_to(m, txt, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["👑 OWNER","👑 ᴏᴡɴᴇʀ","👆 ᴏᴡɴᴇʀ","ᴏᴡɴᴇʀ","ꜱᴜᴩᴩᴏʀᴛ"])
def h_owner(m):
    if _clone_group_guard(m): return
    if check_blocked_and_reply(m.from_user.id): return
    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119")*10
    _SM = _te("6147464060305676048")
    _CK = _te("6147565374289220368")
    _Crown = _te("6289741869962236795")
    _Star  = _te("5465629669829128119")
    mk = InlineKeyboardMarkup()
    mk.add(_IKB("📩 Contact @Felix_bhai", url="https://t.me/Felix_bhai"))
    mk.add(_IKB("📢 Join @Felix_modz1", url="https://t.me/Felix_modz1"))
    bot.reply_to(m,
        f"<blockquote>{_L}\n"
        f"{_Crown} <b>ᴏᴡɴᴇʀ / ꜱᴜᴩᴩᴏʀᴛ</b>\n\n"
        f"ɪꜰ ʏᴏᴜ ꜰᴀᴄᴇ ᴀɴʏ ɪꜱꜱᴜᴇꜱ, ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ ᴀᴅᴍɪɴ:\n"
        f"🌐 @Felix_bhai\n"
        f"⭐ 5908171064\n\n"
        f"{_L}\n"
        f"{_SM} @Felix_Bhai {_CK}\n"
        f"{_L}</blockquote>",
        reply_markup=mk, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🏆 LEADERBOARD","🏆 ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ","ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ","ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ"])
def h_leaderboard(m):
    uid=m.from_user.id
    if _clone_group_guard(m): return
    if check_blocked_and_reply(uid): return

    # Weekly referrals — current week (Monday se aaj tak)
    today=datetime.now()
    week_start=(today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    rows=c.execute(
        "SELECT u.user_id,u.first_name,u.username,COUNT(r.id) as cnt "
        "FROM users u LEFT JOIN referrals r ON u.user_id=r.referrer "
        "AND r.date >= ? "
        "GROUP BY u.user_id ORDER BY cnt DESC LIMIT 10",
        (week_start,)
    ).fetchall()

    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    LOOP        = _te("5465629669829128119")*12
    TROPHY      = _te("5409008750893734809")
    WIN_TROPHY  = _te("5886579736632629397")
    DEV_EMOJI   = _te("6147464060305676048")
    CHECK_EMOJI = _te("6147565374289220368")

    num_emojis = [
        "6269400956387987689",  # 1st
        "5447203607294265305",  # 2nd
        "5453902265922376865",  # 3rd
        "6219826747345471627",  # 4
        "6219909202127620214",  # 5
        "6221746649266391336",  # 6
        "6220028211376425519",  # 7
        "6222219718439209089",  # 8
        "6222084349659973777",  # 9
        "5312157624915999161",  # 10
    ]

    top1 = rows[0] if rows else None
    top1_disp = ""
    if top1:
        top1_disp = f"@{top1[2]}" if top1[2] else (top1[1] or "User")[:15]

    txt = f"{LOOP}\n\n{TROPHY} ᴡᴇᴇᴋʟʏ ʀᴇꜰᴇʀʀᴀʟ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ\n\n{LOOP}\n\n"

    # Sunday (weekday==6) pe top1 ko 3 day premium do
    if today.weekday()==6 and top1 and top1[3]>0:
        txt += f"{WIN_TROPHY} {top1_disp} ᴡᴏɴ 3ᴅᴀʏꜱ ᴩʀᴇᴍɪᴜᴍ !!\n\n"
        try:
            until=(datetime.now()+timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            c.execute("UPDATE users SET is_premium=1,premium_until=? WHERE user_id=?",(until,top1[0]))
            conn.commit()
        except: pass

    for i,(ruid,fname,uname,cnt) in enumerate(rows):
        disp = f"@{uname}" if uname else (fname or "User")[:15]
        eid  = num_emojis[i] if i<len(num_emojis) else "6219826747345471627"
        you  = " ← ʏᴏᴜ" if ruid==uid else ""
        rw   = "refs" if cnt!=1 else "ref"
        txt += f"{_te(eid)} {disp} — {cnt} {rw}{you}\n"

    bot.reply_to(m, f"<blockquote>{txt}</blockquote>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🔴 ᴏꜰꜰ ᴍʏ ʙᴏᴛ","🟢 ᴏɴ ᴍʏ ʙᴏᴛ"] and _IS_CLONE)
def h_toggle_clone_bot(m):
    """Clone bot ka ON/OFF toggle — sirf clone owner ya main owner use kar sakta hai"""
    global _CLONE_BOT_ACTIVE
    uid = m.from_user.id
    # Sirf clone bot ka owner ya main original owner access kar sakta hai
    if uid != OWNER_ID and uid != _MAIN_OWNER:
        bot.reply_to(m,"<blockquote>❌ Sirf bot owner use kar sakta hai!</blockquote>",parse_mode='HTML'); return
    _CLONE_BOT_ACTIVE = not _CLONE_BOT_ACTIVE
    status_icon = "🟢" if _CLONE_BOT_ACTIVE else "🔴"
    status_text = "ON — Ab bot responses dega!" if _CLONE_BOT_ACTIVE else "OFF — Bot silent ho gaya!"
    bot.reply_to(m,
        f"<blockquote>─────────────────────\n"
        f"   {status_icon} <b>ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ ᴜᴩᴅᴀᴛᴇᴅ</b>\n"
        f"─────────────────────\n\n"
        f"Status: <b>{status_text}</b>\n\n"
        f"─────────────────────\n"
        f"⚡ @Felix_modz1</blockquote>",
        reply_markup=kb_admin_p1(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🔴 ᴏꜰꜰ ᴍʏ ʙᴏᴛ","🟢 ᴏɴ ᴍʏ ʙᴏᴛ"] and not _IS_CLONE and is_admin(m.from_user.id))
def h_toggle_main_bot(m):
    """Original bot ka ON/OFF toggle — sirf main owner (admin panel pe)"""
    global _MAIN_BOT_ACTIVE
    uid = m.from_user.id
    if uid != OWNER_ID:
        bot.reply_to(m,"<blockquote>❌ Sirf main owner use kar sakta hai!</blockquote>",parse_mode='HTML'); return
    _MAIN_BOT_ACTIVE = not _MAIN_BOT_ACTIVE
    status_icon = "🟢" if _MAIN_BOT_ACTIVE else "🔴"
    status_text = "ON — Bot ab responses dega!" if _MAIN_BOT_ACTIVE else "OFF — Bot silent mode mein!"
    bot.reply_to(m,
        f"<blockquote>{_F}\n"
        f"   {status_icon} <b>ᴍᴀɪɴ ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ</b>\n"
        f"{_F}\n\n"
        f"Status: <b>{status_text}</b>\n\n"
        f"{_F}\n⚡ @Felix_modz1</blockquote>",
        reply_markup=kb_admin_p1(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["⚙️ ADMIN PANEL","⚙️ ᴀᴅᴍɪɴ ᴩᴀɴᴇʟ","ᴀᴅᴍɪɴ ᴩᴀɴᴇʟ"] and is_admin(m.from_user.id))
def h_admin(m):
    user_state[m.from_user.id]='ADMIN_PANEL'
    bot.send_message(m.chat.id,"<blockquote>⚙️ <b>ᴀᴅᴍɪɴ ᴩᴀɴᴇʟ P1</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="➡️ ADMIN PAGE 2" and is_admin(m.from_user.id) and not _IS_CLONE)
def h_adp2(m): bot.send_message(m.chat.id,"<blockquote>⚙️ <b>Admin P2</b></blockquote>",reply_markup=kb_admin_p2(),parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text in ["⬅️ ADMIN PAGE 1","⬅️ ᴀᴅᴍɪɴ ᴩᴀɢᴇ 1"] and is_admin(m.from_user.id))
def h_adp1b(m): bot.send_message(m.chat.id,"<blockquote>⚙️ <b>Admin P1</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML')  # works in both


@bot.message_handler(func=lambda m: m.text=="🔙 BACK TO ADMIN" and is_admin(m.from_user.id))
def h_adback(m):
    user_state[m.from_user.id]='ADMIN_PANEL'
    bot.send_message(m.chat.id,"<blockquote>⚙️ <b>Admin Panel</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML')

# ── PROTECT USER INFO — Admin Panel ──────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text=="⚡ᴩʀᴏᴛᴇᴄᴛ ᴜꜱᴇʀ ɪɴꜰᴏ" and is_admin(m.from_user.id))
def h_protect_panel(m):
    uid=m.from_user.id
    total=len(get_all_protected())
    bot.send_message(m.chat.id,(
        f"<blockquote>{_F}\n"
        f"⚡ <b>ᴩʀᴏᴛᴇᴄᴛ ᴜꜱᴇʀ ɪɴꜰᴏ</b>\n"
        f"{_F}\n\n"
        f"🔒 <b>Hide User Info</b> — User ID / Username / Number\n"
        f"Jab koi search karega to \"This user is protected\" dikhega.\n\n"
        f"🔓 <b>Show User Info</b> — Protection hata do\n\n"
        f"👁 <b>Total Hidden</b>: <code>{total}</code> users\n\n"
        f"{_F}\n⚡ @Felix_modz1</blockquote>"
    ), reply_markup=kb_protect_user_panel(), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🔒ʜɪᴅᴇ ᴜꜱᴇʀ ɪɴꜰᴏ" and is_admin(m.from_user.id))
def h_hide_user(m):
    uid=m.from_user.id
    user_state[uid]='PROTECT_HIDE'
    bot.reply_to(m,(
        f"<blockquote>{_F}\n"
        f"🔒 <b>ʜɪᴅᴇ ᴜꜱᴇʀ ɪɴꜰᴏ</b>\n"
        f"{_F}\n\n"
        f"📤 Kisi bhi ek bhejo:\n"
        f"• <b>User ID</b>: <code>123456789</code>\n"
        f"• <b>Username</b>: <code>@username</code>\n"
        f"• <b>Mobile Number</b>: <code>9876543210</code>\n\n"
        f"⚡ @Felix_modz1</blockquote>"
    ), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🔓ꜱʜᴏᴡ ᴜꜱᴇʀ ɪɴꜰᴏ" and is_admin(m.from_user.id))
def h_show_user(m):
    uid=m.from_user.id
    user_state[uid]='PROTECT_SHOW'
    bot.reply_to(m,(
        f"<blockquote>{_F}\n"
        f"🔓 <b>ꜱʜᴏᴡ ᴜꜱᴇʀ ɪɴꜰᴏ</b>\n"
        f"{_F}\n\n"
        f"📤 Jis user ki protection hatani hai uska bhejo:\n"
        f"• <b>User ID</b>: <code>123456789</code>\n"
        f"• <b>Username</b>: <code>@username</code>\n"
        f"• <b>Mobile Number</b>: <code>9876543210</code>\n\n"
        f"⚡ @Felix_modz1</blockquote>"
    ), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="👁 ᴛᴏᴛᴀʟ ʜɪᴅᴇ ᴜꜱᴇʀ" and is_admin(m.from_user.id))
def h_total_hidden(m):
    rows=get_all_protected()
    if not rows:
        bot.reply_to(m,"<blockquote>📋 Koi protected user nahi hai abhi.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    txt=f"<blockquote>🔒 <b>ᴩʀᴏᴛᴇᴄᴛᴇᴅ ᴜꜱᴇʀꜱ</b> ({len(rows)})\n{_F}\n\n"
    for i,(identifier,id_type,pdate) in enumerate(rows[:20],1):
        txt+=f"{i}. <code>{identifier}</code> [{id_type}]\n   📅 {pdate[:10]}\n"
    if len(rows)>20: txt+=f"\n...+{len(rows)-20} more\n"
    txt+=f"\n{_F}\n⚡ @Felix_modz1</blockquote>"
    bot.reply_to(m,txt,parse_mode='HTML')

# ── Protect/Unprotect state handler ──
@bot.message_handler(func=lambda m: m.chat.type=='private' and is_admin(m.from_user.id) and
                     user_state.get(m.from_user.id) in ('PROTECT_HIDE','PROTECT_SHOW'))
def h_protect_input(m):
    uid=m.from_user.id; st=user_state.get(uid); txt=(m.text or "").strip()
    if not txt:
        bot.reply_to(m,"<blockquote>❌ Text bhejo!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    # Normalize
    identifier=txt.lstrip('@').strip()
    # Determine type
    if re.match(r'^\d{5,15}$', identifier):
        id_type = "userid" if len(identifier)<11 else "mobile"
    elif re.match(r'^[6-9]\d{9}$', identifier):
        id_type = "mobile"
    else:
        id_type = "username"
    if st=='PROTECT_HIDE':
        ok=protect_user(identifier, id_type, uid)
        # Also protect with @ prefix if username
        if id_type=='username': protect_user(f"@{identifier}", id_type, uid)
        user_state[uid]=S_NONE
        if ok:
            bot.reply_to(m,(
                f"<blockquote>✅ <b>ʜɪᴅᴅᴇɴ!</b>\n{_F}\n\n"
                f"🔒 Identifier: <code>{identifier}</code>\n"
                f"🏷️ Type: <b>{id_type}</b>\n\n"
                f"Ab koi bhi is user ko search karega to\n"
                f"<b>\"This user is protected by Admin\"</b> dikhega.\n\n"
                f"{_F}\n⚡ @Felix_modz1</blockquote>"
            ), reply_markup=kb_protect_user_panel(), parse_mode='HTML')
        else:
            bot.reply_to(m,"<blockquote>❌ Error! Dobara try karo.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
    else:  # PROTECT_SHOW
        ok=unprotect_user(identifier)
        if id_type=='username': unprotect_user(f"@{identifier}")
        user_state[uid]=S_NONE
        if ok:
            bot.reply_to(m,(
                f"<blockquote>✅ <b>ᴜɴᴩʀᴏᴛᴇᴄᴛᴇᴅ!</b>\n{_F}\n\n"
                f"🔓 Identifier: <code>{identifier}</code>\n\n"
                f"Ab ye user normal search mein dikhega.\n\n"
                f"{_F}\n⚡ @Felix_modz1</blockquote>"
            ), reply_markup=kb_protect_user_panel(), parse_mode='HTML')
        else:
            bot.reply_to(m,(
                f"<blockquote>❌ <b>Not Found!</b>\n\n"
                f"<code>{identifier}</code> protected list mein nahi hai.\n"
                f"⚡ @Felix_modz1</blockquote>"
            ), reply_markup=kb_protect_user_panel(), parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="📊 DASHBOARD" and is_admin(m.from_user.id))
def h_dash(m):
    tot=c.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0
    tod=c.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date)=DATE('now')").fetchone()[0] or 0
    srch=c.execute("SELECT COUNT(*) FROM search_history").fetchone()[0] or 0
    grps=len(get_all_groups())
    tkns=c.execute("SELECT COUNT(*) FROM token_log").fetchone()[0] or 0
    bot.reply_to(m,(f"<blockquote>📊 <b>ᴅᴀꜱʜʙᴏᴀʀᴅ</b>\n{_F}\n"
                    f"👥 Users: {tot} (Today: {tod})\n👥 Groups: {grps}\n"
                    f"🔍 Searches: {srch}\n📊 Token Logs: {tkns}\n"
                    f"{_F}\n⚡ @Felix_modz1</blockquote>"),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="👥 USER LIST" and is_admin(m.from_user.id))
def h_userlist(m):
    users=c.execute("SELECT user_id,first_name,credits,is_premium,is_blocked FROM users ORDER BY join_date DESC LIMIT 15").fetchall()
    txt=f"<blockquote>👥 <b>ᴜꜱᴇʀꜱ</b>\n{_F}\n"
    for u in users:
        s=("💎" if u[3] else "👤")+("🚫" if u[4] else "")
        txt+=f"{s} <code>{u[0]}</code> {(u[1] or '')[:12]} | {u[2]}cr\n"
    txt+="⚡ @Felix_modz1</blockquote>"; bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="📢 BROADCAST" and is_admin(m.from_user.id))
def h_broad(m):
    bot.register_next_step_handler(bot.reply_to(m,"<blockquote>📢 Send message to ALL users:</blockquote>",parse_mode='HTML'),do_broadcast)

@bot.message_handler(func=lambda m: m.text=="💎 PREMIUM BROADCAST" and is_admin(m.from_user.id))
def h_prem_broad(m):
    user_count  = c.execute("SELECT COUNT(*) FROM users WHERE is_blocked=0").fetchone()[0] or 0
    group_count = c.execute("SELECT COUNT(*) FROM groups WHERE is_blocked=0").fetchone()[0] or 0
    bot.register_next_step_handler(
        bot.reply_to(m,
            f"<blockquote>💎 <b>PREMIUM BROADCAST</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Users : <b>{user_count}</b>\n"
            f"📢 Groups: <b>{group_count}</b>\n\n"
            f"✅ Premium emoji FULL dikhega (hide nahi hoga)\n"
            f"📋 copy_message se bheja jayega\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 Apna message bhejo (photo/video/text sab OK):\n"
            f"⚡ @Felix_modz1</blockquote>",
            parse_mode='HTML'),
        do_premium_broadcast)

@bot.message_handler(func=lambda m: m.text=="📜 HISTORY" and is_admin(m.from_user.id))
def h_hist(m):
    data=c.execute("SELECT user_id,search_type,query,search_date FROM search_history ORDER BY search_date DESC LIMIT 15").fetchall()
    txt=f"<blockquote>📜 <b>ʜɪꜱᴛᴏʀʏ</b>\n{_F}\n"
    for d in data: txt+=f"<code>{d[0]}</code> | {d[1]} | <code>{d[2]}</code>\n"
    if not data: txt+="Empty\n"
    txt+="⚡ @Felix_modz1</blockquote>"; bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🔗 ADD CLONE CHANNEL" and is_admin(m.from_user.id) and not _IS_CLONE)
def h_add_clone_channel(m):
    """Original bot se ek channel add karo jo SABHI clone bots me force join ban jaye"""
    uid=m.from_user.id
    if uid!=OWNER_ID:
        bot.reply_to(m,"<blockquote>❌ Sirf original owner use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[uid]='ADD_CLONE_CHANNEL'
    bot.send_message(uid,
        f"<blockquote>{_F}\n"
        f"🔗 <b>ADD CLONE CHANNEL</b>\n"
        f"{_F}\n\n"
        f"📢 Channel ka t.me link bhejo:\n"
        f"<code>https://t.me/channelname</code>\n\n"
        f"✅ Ye channel SABHI clone bots me force join ban jayegi!\n"
        f"❌ Clone owners ise remove nahi kar sakte.\n\n"
        f"{_F}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     user_state.get(m.from_user.id)=='ADD_CLONE_CHANNEL' and not _IS_CLONE)
def h_add_clone_channel_input(m):
    """Handle channel link input for ADD CLONE CHANNEL"""
    uid=m.from_user.id; txt=m.text.strip() if m.text else ""
    if txt.lower() in ['cancel','/cancel','🔙 back to admin','🔙 main menu']:
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>❌ Cancelled!\n⚡ @Felix_modz1</blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML'); return
    if not txt.startswith('https://t.me/'):
        bot.reply_to(m,"<blockquote>❌ Valid t.me link bhejo!\nExample: <code>https://t.me/channelname</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    # Channel info fetch karo
    chat_title="Channel"; chat_id_str=txt
    try:
        if '+' not in txt:
            un=txt.split('t.me/')[1].strip('/')
            try:
                ch=bot.get_chat(f"@{un}")
                chat_title=ch.title or un
                chat_id_str=str(ch.id)
            except:
                chat_title=un; chat_id_str=f"@{un}"
        else:
            chat_title="Private Channel"; chat_id_str=txt
    except: pass
    # Sabhi clone owners ke liye clone_forced_channels me add karo
    try:
        clone_owners=c.execute("SELECT user_id FROM bot_clones WHERE is_active=1").fetchall()
        added_count=0
        for (cow,) in clone_owners:
            try:
                # Check if already exists
                existing=c.execute("SELECT id FROM clone_forced_channels WHERE clone_owner_uid=? AND chat_id=?",(cow,chat_id_str)).fetchone()
                if not existing:
                    c.execute("INSERT INTO clone_forced_channels(clone_owner_uid,chat_id,chat_title,chat_url,added_by,added_date,is_active,is_fake) VALUES(?,?,?,?,?,?,1,0)",
                             (cow,chat_id_str,chat_title,txt,uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    added_count+=1
            except: pass
        conn.commit()
        user_state[uid]=S_NONE
        bot.reply_to(m,
            f"<blockquote>{_F}\n"
            f"✅ <b>CLONE CHANNEL ADDED!</b>\n"
            f"{_F}\n\n"
            f"🔗 Channel: <b>{chat_title}</b>\n"
            f"🆔 ID: <code>{chat_id_str}</code>\n"
            f"🤖 Total Clones Updated: <code>{added_count}/{len(clone_owners)}</code>\n\n"
            f"ℹ️ Ye channel sabhi active clone bots me force join ban gai!\n"
            f"❌ Clone owners ise remove nahi kar sakte.\n\n"
            f"{_F}\n⚡ @Felix_modz1</blockquote>",
            reply_markup=kb_admin_p1(),parse_mode='HTML')
    except Exception as e:
        bot.reply_to(m,f"<blockquote>❌ Error: {_safe_err(e)}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

# ── FORCE ADD CLONE — bina 20 refer ke admin se seedha deploy ──
S_FORCE_ADD_CLONE = 'force_add_clone'
S_FORCE_ADD_CLONE_TOKEN = 'force_add_clone_token'

@bot.message_handler(func=lambda m: m.text in ["🤖 FORCE ADD CLONE","💎 PREMIUM CLONE"] and m.from_user.id==OWNER_ID and not _IS_CLONE)
def h_force_add_clone(m):
    user_state[m.from_user.id]=S_FORCE_ADD_CLONE
    bot.send_message(m.chat.id,
        f"<blockquote>{_F}\n"
        f"🤖 <b>FORCE ADD CLONE</b>\n"
        f"{_F}\n\n"
        f"Clone owner ka <b>User ID ya @username</b> bhejo:\n"
        f"• ID example: <code>123456789</code>\n"
        f"• Username example: <code>@rahul123</code>\n\n"
        f"💡 Note: User ka /start karna zaruri NAHI hai\n"
        f"(Ye user bina 20 refer ke clone pega)\n"
        f"{_F}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     user_state.get(m.from_user.id)==S_FORCE_ADD_CLONE and not _IS_CLONE)
def h_force_clone_userid(m):
    uid=m.from_user.id; txt=m.text.strip() if m.text else ""
    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>❌ Cancelled!</blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML'); return

    target_uid=None; fname=None; udisp=None

    # Case 1: numeric User ID
    if re.match(r'^\d{5,12}$', txt):
        target_uid=int(txt)
        row=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(target_uid,)).fetchone()
        if row:
            fname=row[0] or f"User_{target_uid}"
            udisp=f"@{row[1]}" if row[1] else f"ID:{target_uid}"
        else:
            # DB mein nahi — Telegram se try karo
            try:
                _gc=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                                  params={"chat_id":target_uid},timeout=8)
                if _gc.status_code==200:
                    _gd=_gc.json().get('result',{})
                    fname=(_gd.get('first_name','') or '') + ' ' + (_gd.get('last_name','') or '')
                    fname=fname.strip() or f"User_{target_uid}"
                    _gun=_gd.get('username','')
                    udisp=f"@{_gun}" if _gun else f"ID:{target_uid}"
                else:
                    fname=f"User_{target_uid}"; udisp=f"ID:{target_uid}"
            except:
                fname=f"User_{target_uid}"; udisp=f"ID:{target_uid}"
        # Ensure user exists in DB
        c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,credits,first_time) VALUES(?,?,?,?,?,0)",
                  (target_uid, udisp.lstrip('@') if udisp.startswith('@') else '', fname,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"), FREE_CREDITS)); conn.commit()

    # Case 2: @username
    elif txt.startswith('@') or (not txt.startswith('https://') and re.match(r'^[a-zA-Z][a-zA-Z0-9_]{3,}$',txt)):
        un=txt.lstrip('@').strip()
        # DB mein dhundo pehle
        row=c.execute("SELECT user_id,first_name,username FROM users WHERE username=? COLLATE NOCASE",(un,)).fetchone()
        if row:
            target_uid=row[0]; fname=row[1] or f"@{un}"; udisp=f"@{row[2]}" if row[2] else f"@{un}"
        else:
            # Telegram API se resolve karo
            try:
                _gc2=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                                   params={"chat_id":f"@{un}"},timeout=8)
                if _gc2.status_code==200:
                    _gd2=_gc2.json().get('result',{})
                    target_uid=_gd2.get('id')
                    fname=(_gd2.get('first_name','') or '') + ' ' + (_gd2.get('last_name','') or '')
                    fname=fname.strip() or f"@{un}"
                    udisp=f"@{_gd2.get('username',un)}"
                else:
                    target_uid=None
            except:
                target_uid=None
        if not target_uid:
            bot.reply_to(m,
                f"<blockquote>❌ @{un} ka ID resolve nahi hua!\n\n"
                f"• Numeric User ID try karo\n"
                f"• Ya @userinfobot se ID leke bhejo\n"
                f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        # Ensure user in DB
        c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,credits,first_time) VALUES(?,?,?,?,?,0)",
                  (target_uid, un, fname, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), FREE_CREDITS)); conn.commit()
    else:
        bot.reply_to(m,
            f"<blockquote>❌ Sahi format bhejo:\n"
            f"• User ID: <code>123456789</code>\n"
            f"• Username: <code>@rahul123</code>\n"
            f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

    # Save state with target_uid and ask for token
    user_state[uid]={'state':S_FORCE_ADD_CLONE_TOKEN,'target_uid':target_uid,'target_name':fname}
    bot.reply_to(m,
        f"<blockquote>✅ Owner: <b>{fname}</b> ({udisp})\n"
        f"🆔 ID: <code>{target_uid}</code>\n\n"
        f"Ab clone bot ka <b>Bot Token</b> bhejo:\n"
        f"Example: <code>1234567890:ABCdef...</code>\n\n"
        f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     isinstance(user_state.get(m.from_user.id),dict) and
                     user_state.get(m.from_user.id,{}).get('state')==S_FORCE_ADD_CLONE_TOKEN and not _IS_CLONE)
def h_force_clone_token(m):
    uid=m.from_user.id; txt=m.text.strip() if m.text else ""
    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>❌ Cancelled!</blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML'); return
    st=user_state[uid]; target_uid=st['target_uid']; target_name=st['target_name']
    if not re.match(r'^\d{8,12}:[A-Za-z0-9_-]{35,}$',txt):
        bot.reply_to(m,"<blockquote>❌ Invalid token format!\nExample: <code>1234567890:ABCdef...</code></blockquote>",parse_mode='HTML'); return
    # Validate token
    try:
        r=requests.get(f"https://api.telegram.org/bot{txt}/getMe",timeout=10)
        if r.status_code!=200 or not r.json().get('ok'):
            bot.reply_to(m,"<blockquote>❌ Invalid token! Bot nahi mila.</blockquote>",parse_mode='HTML'); return
        bi=r.json().get('result',{})
        bot_username=bi.get('username','?'); bot_name=bi.get('first_name','Bot')
    except Exception as e:
        bot.reply_to(m,f"<blockquote>❌ Token check error: {_safe_err(e)}</blockquote>",parse_mode='HTML'); return
    # Insert into bot_clones and deploy
    try:
        c.execute("INSERT OR REPLACE INTO bot_clones(user_id,bot_token,created_date,is_active) VALUES(?,?,?,1)",
                  (target_uid,txt,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        # Also ensure user exists in DB
        c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,credits,first_time) VALUES(?,?,?,?,?,0)",
                  (target_uid,'',target_name,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),FREE_CREDITS)); conn.commit()
        user_state[uid]=S_NONE
        # Deploy clone
        threading.Thread(target=_run_clone_bot,args=(txt,target_uid),daemon=True).start()
        threading.Thread(target=_promote_clone_on_orig_chats,args=(txt,),daemon=True).start()
        bot.send_message(uid,
            f"<blockquote>{_F}\n"
            f"✅ <b>CLONE FORCE DEPLOYED!</b>\n"
            f"{_F}\n\n"
            f"👤 Owner: <b>{target_name}</b> (<code>{target_uid}</code>)\n"
            f"🤖 Bot: @{bot_username} (<b>{bot_name}</b>)\n"
            f"🔑 Token: <code>{txt[:20]}...</code>\n\n"
            f"🟢 Clone deploy ho gaya bina 20 refer ke!\n"
            f"{_F}</blockquote>",
            reply_markup=kb_admin_p1(),parse_mode='HTML')
        # Notify clone owner
        try:
            bot.send_message(target_uid,
                f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
                f"   🎉 ʙᴏᴛ ᴄʟᴏɴᴇ ᴀᴩᴩʀᴏᴠᴇᴅ! ✅\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 Tera bot deploy ho gaya!\n"
                f"🤖 @{bot_username}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━</blockquote>",parse_mode='HTML')
        except: pass
    except Exception as e:
        bot.reply_to(m,f"<blockquote>❌ Deploy error: {_safe_err(e)}</blockquote>",parse_mode='HTML')

# ═══════════════════════════════════════════════════════════
# FORCE CLONE 2 — Classic/Simple bot (bilkul alag design)
# ═══════════════════════════════════════════════════════════
S_FC2 = 'force_clone2'
S_FC2_TOKEN = 'force_clone2_token'

def _run_clone2_bot(clone_token, owner_uid):
    """
    Normal Clone (Classic) — simple design:
    - No premium emoji, no tg-emoji tags
    - Plain ━━━ separators in header/footer
    - Footer: owner ka mention
    - Same features but classic look
    """
    try:
        import subprocess, sys, os, re as _re_c2
        script_path = os.path.abspath(__file__)
        with open(script_path, 'r', encoding='utf-8') as f:
            src = f.read()

        # ── Token replace ──
        src = src.replace(f'BOT_TOKEN = "{BOT_TOKEN}"', f'BOT_TOKEN = "{clone_token}"', 1)

        # ── Owner replace ──
        src = src.replace(f'OWNER_ID = {OWNER_ID}', f'OWNER_ID = {owner_uid}', 1)

        # ── Force _IS_CLONE=True + _IS_CLASSIC=True — ek hi step mein inject ──
        # Step 1: _IS_CLONE line replace karo
        src = src.replace(
            '_IS_CLONE = (OWNER_ID != 8335023642)  # agar owner main owner nahi hai to ye clone hai',
            '_IS_CLONE = True  # ye clone hai',
            1)
        # Step 2: _IS_CLASSIC = False line ko True se replace karo (alag line hai — override rokne ke liye)
        src = src.replace(
            '_IS_CLASSIC = False  # Normal/Classic clone mode — _run_clone2_bot True set karta hai inject se',
            '_IS_CLASSIC = True  # Classic mode — simple design (injected by _run_clone2_bot)',
            1)

        # ── ALL tg-emoji tags hata do — fallback text rakh do ──
        src = _re_c2.sub(r'<tg-emoji[^>]*>([^<]*)</tg-emoji>', r'\1', src)

        # ── _PREM_EMOJI var bhi plain kar do ──
        src = src.replace(
            "_PREM_EMOJI = \"<tg-emoji emoji-id='5465277838993141300'>💎</tg-emoji>\"",
            '_PREM_EMOJI = "━"',
            1)

        # ── _CL_TOP / _CL_BOT — plain ━━━ line ──
        src = src.replace(
            'def _CL_TOP(): return "───────────────────────────────" if _IS_CLONE else _PREM_EMOJI*10',
            'def _CL_TOP(): return "━━━━━━━━━━━━━━━━━━━━━━━━━━"',
            1)
        src = src.replace(
            'def _CL_BOT(): return "───────────────────────────────" if _IS_CLONE else _PREM_EMOJI*10',
            'def _CL_BOT(): return "━━━━━━━━━━━━━━━━━━━━━━━━━━"',
            1)

        # ── _orig_credit / _clone_credit — plain line ──
        src = _re_c2.sub(
            r'def _orig_credit\(\):.*?def _clone_credit',
            'def _orig_credit(): return "━━━━━━━━━━━━━━━━━━━━━━━━━━"\ndef _clone_credit',
            src, count=1, flags=_re_c2.DOTALL)

        # ── Footer: ALL felix references → owner mention ──
        src = _re_c2.sub(
            r'ᴅᴇᴠᴇʟᴏᴩᴇʀ\s*:\s*@Felix_modz1',
            f'ᴅᴇᴠᴇʟᴏᴩᴇʀ : <a href="tg://user?id={owner_uid}">Owner</a>',
            src)
        src = _re_c2.sub(r'⚡\s*@Felix_modz1', f'⚡ <a href="tg://user?id={owner_uid}">Owner</a>', src)
        src = _re_c2.sub(r'@Felix_Bhai\b', 'Owner', src)
        src = _re_c2.sub(r'@Felix_modz1\b', 'Owner', src)

        # ── DB in clones2/ folder ──
        clone_dir = os.path.join(os.path.dirname(script_path), 'clones2')
        os.makedirs(clone_dir, exist_ok=True)
        src = src.replace(
            '_DB_FILE = os.path.join(_SCRIPT_DIR, f"bot_{_BOT_ID}.db")',
            f'_DB_FILE = os.path.join(r"{clone_dir}", f"bot_{{_BOT_ID}}.db")', 1)

        clone_file = os.path.join(clone_dir, f'clone2_{owner_uid}.py')
        _kill_old_clone(owner_uid, clone_dir)
        time.sleep(0.5)

        with open(clone_file, 'w', encoding='utf-8') as f:
            f.write(src)

        proc = subprocess.Popen(
            [sys.executable, clone_file],
            stdout=open(os.path.join(clone_dir, f'clone2_{owner_uid}.log'), 'a'),
            stderr=subprocess.STDOUT,
            cwd=clone_dir)

        pid_file = os.path.join(clone_dir, f'clone2_{owner_uid}.pid')
        with open(pid_file, 'w') as pf:
            pf.write(str(proc.pid))

        print(f"[CLONE2] Started uid={owner_uid} token={clone_token[:20]}... PID={proc.pid}")

    except Exception as e:
        print(f"[CLONE2] Error: {_safe_err(e)}")
        try: bot.send_message(OWNER_ID, f"<blockquote>❌ Clone2 start error:\n{_safe_err(e)}</blockquote>", parse_mode='HTML')
        except: pass


@bot.message_handler(func=lambda m: m.text in ["🤖 FORCE CLONE 2","🤖 NORMAL CLONE"] and m.from_user.id==OWNER_ID and not _IS_CLONE)
def h_force_clone2(m):
    user_state[m.from_user.id]=S_FC2
    bot.send_message(m.chat.id,
        f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>FORCE CLONE 2</b> — Classic Bot\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Ye clone <b>classic/simple</b> design ka hoga:\n"
        f"• No premium emoji — plain text\n"
        f"• Footer = Clone owner ka mention\n"
        f"• Simple separators\n\n"
        f"Clone owner ka <b>User ID ya @username</b> bhejo:\n"
        f"• ID: <code>123456789</code>\n"
        f"• Username: <code>@rahul123</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     user_state.get(m.from_user.id)==S_FC2 and not _IS_CLONE)
def h_fc2_userid(m):
    uid=m.from_user.id; txt=m.text.strip() if m.text else ""
    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>❌ Cancelled!</blockquote>",reply_markup=kb_admin_p2(),parse_mode='HTML'); return

    target_uid=None; fname=None; udisp=None

    if re.match(r'^\d{5,12}$', txt):
        target_uid=int(txt)
        row=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(target_uid,)).fetchone()
        if row:
            fname=row[0] or f"User_{target_uid}"
            udisp=f"@{row[1]}" if row[1] else f"ID:{target_uid}"
        else:
            try:
                _gc=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                                  params={"chat_id":target_uid},timeout=8)
                if _gc.status_code==200:
                    _gd=_gc.json().get('result',{})
                    fname=((_gd.get('first_name','') or '')+' '+(_gd.get('last_name','') or '')).strip() or f"User_{target_uid}"
                    udisp=f"@{_gd.get('username','')}" if _gd.get('username') else f"ID:{target_uid}"
                else: fname=f"User_{target_uid}"; udisp=f"ID:{target_uid}"
            except: fname=f"User_{target_uid}"; udisp=f"ID:{target_uid}"
        c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,credits,first_time) VALUES(?,?,?,?,?,0)",
                  (target_uid,udisp.lstrip('@') if udisp and udisp.startswith('@') else '',fname,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),FREE_CREDITS)); conn.commit()

    elif txt.startswith('@') or re.match(r'^[a-zA-Z][a-zA-Z0-9_]{3,}$',txt):
        un=txt.lstrip('@').strip()
        row=c.execute("SELECT user_id,first_name,username FROM users WHERE username=? COLLATE NOCASE",(un,)).fetchone()
        if row:
            target_uid=row[0]; fname=row[1] or f"@{un}"; udisp=f"@{row[2]}" if row[2] else f"@{un}"
        else:
            try:
                _gc2=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                                   params={"chat_id":f"@{un}"},timeout=8)
                if _gc2.status_code==200:
                    _gd2=_gc2.json().get('result',{})
                    target_uid=_gd2.get('id')
                    fname=((_gd2.get('first_name','') or '')+' '+(_gd2.get('last_name','') or '')).strip() or f"@{un}"
                    udisp=f"@{_gd2.get('username',un)}"
                else: target_uid=None
            except: target_uid=None
        if not target_uid:
            bot.reply_to(m,f"<blockquote>❌ @{un} resolve nahi hua!\n• Numeric ID try karo\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,credits,first_time) VALUES(?,?,?,?,?,0)",
                  (target_uid,un,fname,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),FREE_CREDITS)); conn.commit()
    else:
        bot.reply_to(m,f"<blockquote>❌ Sahi format:\n• ID: <code>123456789</code>\n• Username: <code>@rahul123</code></blockquote>",parse_mode='HTML'); return

    user_state[uid]={'state':S_FC2_TOKEN,'target_uid':target_uid,'target_name':fname}
    bot.reply_to(m,
        f"<blockquote>✅ Owner: <b>{fname}</b> ({udisp})\n"
        f"🆔 ID: <code>{target_uid}</code>\n\n"
        f"Ab clone bot ka <b>Bot Token</b> bhejo:\n"
        f"Example: <code>1234567890:ABCdef...</code>\n\n"
        f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     isinstance(user_state.get(m.from_user.id),dict) and
                     user_state.get(m.from_user.id,{}).get('state')==S_FC2_TOKEN and not _IS_CLONE)
def h_fc2_token(m):
    uid=m.from_user.id; txt=m.text.strip() if m.text else ""
    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>❌ Cancelled!</blockquote>",reply_markup=kb_admin_p2(),parse_mode='HTML'); return
    st=user_state[uid]; target_uid=st['target_uid']; target_name=st['target_name']
    if not re.match(r'^\d{8,12}:[A-Za-z0-9_-]{35,}$',txt):
        bot.reply_to(m,"<blockquote>❌ Invalid token!\nExample: <code>1234567890:ABCdef...</code></blockquote>",parse_mode='HTML'); return
    try:
        r=requests.get(f"https://api.telegram.org/bot{txt}/getMe",timeout=10)
        if r.status_code!=200 or not r.json().get('ok'):
            bot.reply_to(m,"<blockquote>❌ Invalid token! Bot nahi mila.</blockquote>",parse_mode='HTML'); return
        bi=r.json().get('result',{})
        bot_username=bi.get('username','?'); bot_name=bi.get('first_name','Bot')
    except Exception as e:
        bot.reply_to(m,f"<blockquote>❌ Token error: {_safe_err(e)}</blockquote>",parse_mode='HTML'); return
    try:
        c.execute("INSERT OR REPLACE INTO bot_clones(user_id,bot_token,created_date,is_active) VALUES(?,?,?,1)",
                  (target_uid,txt,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,join_date,credits,first_time) VALUES(?,?,?,?,?,0)",
                  (target_uid,'',target_name,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),FREE_CREDITS)); conn.commit()
        user_state[uid]=S_NONE
        threading.Thread(target=_run_clone2_bot,args=(txt,target_uid),daemon=True).start()
        bot.send_message(uid,
            f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>CLASSIC CLONE 2 DEPLOYED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Owner: <b>{target_name}</b> (<code>{target_uid}</code>)\n"
            f"🤖 Bot: @{bot_username} (<b>{bot_name}</b>)\n"
            f"🔑 Token: <code>{txt[:20]}...</code>\n\n"
            f"🟢 Classic clone deploy ho gaya!\n"
            f"━━━━━━━━━━━━━━━━━━━━</blockquote>",
            reply_markup=kb_admin_p2(),parse_mode='HTML')
        try:
            bot.send_message(target_uid,
                f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
                f"   ✅ BOT CLONE APPROVED!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 Tera bot deploy ho gaya!\n"
                f"🤖 @{bot_username}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━</blockquote>",parse_mode='HTML')
        except: pass
    except Exception as e:
        bot.reply_to(m,f"<blockquote>❌ Deploy error: {_safe_err(e)}</blockquote>",parse_mode='HTML')

# All 21 APIs with their default URLs and display names
_BOT_APIS = [
    ("phone",       "📱 Phone Lookup",    "https://numbeer-info.vercel.app/?numbere={}&key=SH4DAW-D4DY"),
    ("userid",      "🆔 User ID",         "https://sh4dow-d4dy.vercel.app/api/search?userid={}&apikey=SH4DAW-D4DY"),
    ("username",    "ᴜꜱᴇʀɴᴀᴍᴇ ɪɴꜰᴏ",   "https://telegram-username-to-num.vercel.app/?key=SH4DAW-D4DY&user={}"),
    ("aadhar",      "🪪 Aadhar",          "https://adhar-to-info.vercel.app/?key=SH4DAW-D4DY&aadhar={}"),
    ("instagram",   "📸 Instagram",       "https://insta-to-info.vercel.app/?key=SH4DAW-D4DY&username={}"),
    ("vehicle",     "🚗 Vehicle RC",      "https://vehicle-rc-to-num.vercel.app/?rc={}&key=SH4DAW-D4DY"),
    ("pan",         "💳 PAN Card",        "https://pancard-info.deno.dev/?pan={}"),
    ("freefire",    "🎮 Free Fire",       "https://free-fire-info-bice.vercel.app/?uid={}&key=SH4DAW-D4DY"),
    ("ff_like",     "❤️ FF Like",         "https://sexty-autolikes.vercel.app/like?uid={}&region=ind"),
    ("bomber",      "💣 Bomber",          "https://flix-bombar.onrender.com/bom?num={}"),
    ("abdulstore",  "🏪 AbdulStore",      "https://store.abdulstoreapi.workers.dev/api/v1?userid={}&key=ak_59eca148e4484ccb50e8575645c32ee1"),
    ("sh4dow",      "🌐 Sh4dow API",      "https://sh4dow-d4dy.vercel.app/api/search?userid={}&apikey=SH4DAW-D4DY"),
    ("numinfo2",    "📟 Num Info 2",      "https://numm-info-sable.vercel.app/?key=SH4DAW-D4DY&query={}"),
    ("un_to_num",   "🔗 UN→Num",          "https://telegram-username-to-num.vercel.app/?key=SH4DAW-D4DY&user={}"),
    ("un_to_info",  "📋 UN→Info",         "http://username-to-info-rwsw.onrender.com/info?username=@{}"),
    ("ff_info",     "🎮 FF Info Alt",     "https://free-fire-info-bice.vercel.app/?uid={}&key=SH4DAW-D4DY"),
    ("rlx_bomber",  "💥 RLX Bomber",      "https://rlxbomber.vercel.app/api/attack?number={}&key=rlxcoder"),
    ("ff_like2",    "❤️ FF Like 2",       "https://verma-like-api.vercel.app/like?uid={}&region=ind"),
]

def _get_api_custom_url(key):
    """DB me custom URL hai to return karo, warna None"""
    try:
        r=c.execute("SELECT api_url FROM api_keys WHERE api_name=? AND is_active=1",(key,)).fetchone()
        return r[0] if r else None
    except: return None

def _api_source_label(key):
    custom=_get_api_custom_url(key)
    return "✏️ Custom" if custom else "🗂️ Default"

# ── API KEY MANAGER ──────────────────────────────────────────────────────────
# Har API ka hardcoded default key + label
_BOT_API_KEYS = [
    ("key_sh4daw",      "🔑 SH4DAW (Main Key)",       "SH4DAW-D4DY"),
    ("key_abdulstore",  "🏪 AbdulStore Key",           "ak_59eca148e4484ccb50e8575645c32ee1"),
    ("key_ff_info",     "🎮 FF Info Key",              "SH4DAW-D4DY"),
    ("key_rlx_bomber",  "💥 RLX Bomber Key",           "rlxcoder"),
    ("key_numinfo",     "📱 NumInfo Key",              "SH4DAW-D4DY"),
    ("key_aadhar",      "🪪 Aadhar Key",               "SH4DAW-D4DY"),
    ("key_instagram",   "📸 Instagram Key",            "SH4DAW-D4DY"),
    ("key_vehicle",     "🚗 Vehicle RC Key",           "SH4DAW-D4DY"),
    ("key_username",    "🔍 Username API Key",         "SH4DAW-D4DY"),
]

def _get_api_custom_key(key_name):
    """DB me custom API key hai to return karo, warna None"""
    try:
        r=c.execute("SELECT api_key FROM api_keys WHERE api_name=? AND is_active=1",(key_name,)).fetchone()
        return r[0] if r and r[0] else None
    except: return None

def _get_live_api_key(key_name):
    """Live API key return karo — custom DB se ya default se"""
    custom=_get_api_custom_key(key_name)
    if custom: return custom
    info=next((k for k in _BOT_API_KEYS if k[0]==key_name),None)
    return info[2] if info else ""

def _save_api_key(key_name, new_key, by):
    """DB me API key save karo"""
    try:
        c.execute("INSERT OR REPLACE INTO api_keys(api_name,api_url,api_key,is_active,added_by,added_date) VALUES(?,?,?,1,?,?)",
                 (key_name,"",new_key,by,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); return True
    except: return False

def kb_bot_api_keys():
    """Inline keyboard — all API keys as buttons"""
    mk=InlineKeyboardMarkup(row_width=1)
    for key_name,label,_ in _BOT_API_KEYS:
        custom=_get_api_custom_key(key_name)
        icon="✏️" if custom else "🗂️"
        mk.add(_IKB(f"{icon} {label}",style="primary",callback_data=f"apikey_sel_{key_name}"))
    mk.add(_IKB("🔙 BACK TO ADMIN",style="danger",callback_data="apikey_back"))
    return mk

def _send_bot_api_keys_menu(chat_id, msg_id=None):
    """API KEY MANAGER main screen"""
    total=len(_BOT_API_KEYS)
    custom_count=sum(1 for k,_,__ in _BOT_API_KEYS if _get_api_custom_key(k) is not None)
    default_count=total-custom_count
    txt=(f"<blockquote>🔑 <b>BOT API KEY MANAGER</b>\n"
         f"━━━━━━━━━━━━━━━━━━\n"
         f"📊 Total Keys: {total}\n"
         f"✏️ Custom Set: {custom_count}\n"
         f"🗂️ Default: {default_count}\n"
         f"━━━━━━━━━━━━━━━━━━\n\n"
         f"🔑 Kaunsi API key change karna hai?\n"
         f"<i>✏️ = Custom key already set hai</i>\n"
         f"⚡ @Felix_modz1</blockquote>")
    mk=kb_bot_api_keys()
    if msg_id:
        try: bot.edit_message_text(txt,chat_id,msg_id,reply_markup=mk,parse_mode='HTML'); return
        except: pass
    bot.send_message(chat_id,txt,reply_markup=mk,parse_mode='HTML')
# ──────────────────────────────────────────────────────────────────────────────

def kb_bot_api_urls():
    """Inline keyboard — all 21 APIs as buttons (screenshot style)"""
    mk=InlineKeyboardMarkup(row_width=1)
    for key,label,default_url in _BOT_APIS:
        source=_api_source_label(key)
        btn_label=f"{label}"
        mk.add(_IKB(btn_label,style="primary",callback_data=f"apiurl_sel_{key}"))
    mk.add(_IKB("🔙 BACK TO ADMIN",style="danger",callback_data="apiurl_back"))
    return mk

def _send_bot_api_urls_menu(chat_id,msg_id=None):
    """BOT API URL MANAGER main screen — screenshot jaisa"""
    total=len(_BOT_APIS)
    custom_count=sum(1 for k,_,__ in _BOT_APIS if _get_api_custom_url(k) is not None)
    default_count=total-custom_count
    txt=(f"<blockquote>🔗 <b>BOT API URL MANAGER</b>\n"
         f"━━━━━━━━━━━━━━━━━━\n"
         f"📊 Total APIs: {total}\n"
         f"✏️ Custom Set: {custom_count}\n"
         f"🗂️ Default: {default_count}\n"
         f"━━━━━━━━━━━━━━━━━━\n\n"
         f"🖊️ Kaunsi API ka URL change karna hai?\n"
         f"<i>✏️ = Custom URL already set hai</i>\n"
         f"⚡ @Felix_modz1</blockquote>")
    mk=kb_bot_api_urls()
    if msg_id:
        try: bot.edit_message_text(txt,chat_id,msg_id,reply_markup=mk,parse_mode='HTML'); return
        except: pass
    bot.send_message(chat_id,txt,reply_markup=mk,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text in ["🔑 API CHANGE","🔗 BOT API URLS"] and is_admin(m.from_user.id))
def h_api_change(m):
    uid=m.from_user.id
    if uid!=OWNER_ID:
        bot.reply_to(m,"<blockquote>❌ Sirf owner!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    _send_bot_api_urls_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text=="🔑 BOT API KEYS" and is_admin(m.from_user.id))
def h_api_keys_mgmt(m):
    uid=m.from_user.id
    if uid!=OWNER_ID:
        bot.reply_to(m,"<blockquote>❌ Sirf owner!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    _send_bot_api_keys_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     isinstance(user_state.get(m.from_user.id),dict) and
                     user_state.get(m.from_user.id,{}).get('state','')=='API_URL_INPUT')
def h_api_url_input(m):
    uid=m.from_user.id; txt=m.text.strip() if m.text else ""
    st=user_state.get(uid,{})
    api_key=st.get('api_key',''); api_label=st.get('api_label','')
    msg_id=st.get('prompt_msg_id')

    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        try:
            if msg_id: bot.delete_message(uid,msg_id)
        except: pass
        _send_bot_api_urls_menu(uid); return

    if '{}' not in txt:
        bot.reply_to(m,
            "<blockquote>⚠️ {} placeholder zaroori hai!\n"
            "Example: <code>https://example.com/api?q={}&key=XYZ</code>\n"
            "Cancel karne ke liye button dabao.</blockquote>",
            parse_mode='HTML'); return

    # Save
    try:
        c.execute("INSERT OR REPLACE INTO api_keys(api_name,api_url,api_key,is_active,added_by,added_date) VALUES(?,?,?,1,?,?)",
                 (api_key,txt,"",uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
    except Exception as e:
        bot.reply_to(m,f"<blockquote>❌ Error: {_safe_err(e)}</blockquote>",parse_mode='HTML'); return

    user_state[uid]=S_NONE
    try:
        if msg_id: bot.delete_message(uid,msg_id)
    except: pass
    # Show success + updated URL card
    bot.send_message(uid,
        f"<blockquote>✅ 📱 <b>Phone Lookup</b> URL save ho gaya!\n\n"
        f"<b>New URL:</b>\n<code>{txt}</code>\n\n"
        f"⚡ @Felix_modz1</blockquote>".replace("Phone Lookup",api_label),
        parse_mode='HTML')
    _send_bot_api_urls_menu(uid)

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     isinstance(user_state.get(m.from_user.id),dict) and
                     user_state.get(m.from_user.id,{}).get('state','')=='API_KEY_INPUT')
def h_api_key_input(m):
    """API KEY MANAGER — naya key input handler"""
    uid=m.from_user.id; txt=m.text.strip() if m.text else ""
    st=user_state.get(uid,{})
    key_name=st.get('key_name',''); key_label=st.get('key_label','')
    msg_id=st.get('prompt_msg_id')

    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        try:
            if msg_id: bot.delete_message(uid,msg_id)
        except: pass
        _send_bot_api_keys_menu(uid); return

    if len(txt)<3:
        bot.reply_to(m,"<blockquote>⚠️ Key bahut chhoti hai! Valid API key bhejo.\nCancel ke liye button dabao.</blockquote>",parse_mode='HTML'); return

    # Save key in DB (api_url="" rakho, api_key=new key)
    if not _save_api_key(key_name, txt, uid):
        bot.reply_to(m,"<blockquote>❌ Save error! Dobara try karo.</blockquote>",parse_mode='HTML'); return

    user_state[uid]=S_NONE
    try:
        if msg_id: bot.delete_message(uid,msg_id)
    except: pass
    bot.send_message(uid,
        f"<blockquote>✅ 🔑 <b>{key_label}</b>\n\n"
        f"New Key save ho gaya!\n\n"
        f"<b>Key:</b> <code>{txt}</code>\n\n"
        f"⚡ @Felix_modz1</blockquote>",
        parse_mode='HTML')
    _send_bot_api_keys_menu(uid)

def get_custom_api(feature_name):
    """DB se custom API fetch karo — agar nahi mila to None,None"""
    try:
        r=c.execute("SELECT api_url,api_key FROM api_keys WHERE api_name=? AND is_active=1",(feature_name.upper(),)).fetchone()
        if r: return r[0],r[1]
    except: pass
    return None,None

@bot.message_handler(func=lambda m: m.text=="👋 BOT WELCOME SETTINGS" and is_admin(m.from_user.id))
def h_welcome(m):
    user_state[m.from_user.id]='ADMIN_WELCOME'
    st=get_welcome_settings()
    img="✅" if st and st[3] else "❌"; vid="✅" if st and st[4] else "❌"
    bot.send_message(m.chat.id,f"<blockquote>👋 <b>ᴡᴇʟᴄᴏᴍᴇ</b>\n🖼 Image:{img} | 🎥 Video:{vid}</blockquote>",reply_markup=kb_welcome(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🌟 GROUP WELCOME SETTINGS" and is_admin(m.from_user.id))
def h_grp_welcome(m):
    user_state[m.from_user.id]='ADMIN_GRP_WELCOME'
    groups=get_all_groups()
    if not groups:
        bot.send_message(m.chat.id,"<blockquote>❌ Koi group registered nahi hai abhi!\n⚡ @Felix_modz1</blockquote>",reply_markup=kb_group_welcome(),parse_mode='HTML'); return
    txt="<blockquote>🌟 <b>ɢʀᴏᴜᴩ ᴡᴇʟᴄᴏᴍᴇ ꜱᴇᴛᴛɪɴɢꜱ</b>\n\n"
    txt+="📋 <b>Registered Groups:</b>\n"
    for gid,title in groups[:8]:
        img,vid,vlist,stk=get_group_welcome_media(gid)
        has_img="🖼✅" if img and os.path.exists(img) else "🖼❌"
        has_vid="🎥✅" if vid and os.path.exists(vid) else "🎥❌"
        has_vlist="🎞✅" if vlist else "🎞❌"
        has_stk="🎪✅" if stk else "🎪❌"
        txt+=f"\n📌 <b>{title[:20]}</b>\n"
        txt+=f"<code>{gid}</code>\n"
        txt+=f"{has_img} {has_vid} {has_vlist} {has_stk}\n"
    txt+="\n⚡ @Felix_modz1</blockquote>"
    bot.send_message(m.chat.id,txt,reply_markup=kb_group_welcome(),parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text=="👥 GROUP MANAGEMENT" and is_admin(m.from_user.id))
def h_grpmgmt(m):
    user_state[m.from_user.id]='ADMIN_GROUP_MANAGEMENT'
    bot.send_message(m.chat.id,"<blockquote>👥 <b>ɢʀᴏᴜᴩ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</b></blockquote>",reply_markup=kb_group_mgmt(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🎛️ GROUP CONTROL" and is_admin(m.from_user.id))
def h_group_control(m):
    """Har group ka apna ON/OFF unlimited toggle button"""
    uid = m.from_user.id
    _send_group_control_panel(m.chat.id)

def _send_group_control_panel(chat_id, msg_id=None, page=1):
    """Group Control panel — har group ka apna inline button"""
    groups = get_all_groups()
    total = len(groups)
    unl_count = sum(1 for gid,_ in groups if safe_g(get_group(gid),5)==1)
    lim_count = total - unl_count

    def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119")*10

    txt = (
        f"<blockquote>{_L}\n"
        f"🎛️ <b>GROUP CONTROL PANEL</b>\n"
        f"{_L}\n\n"
        f"📊 Total Groups: <b>{total}</b>\n"
        f"✅ Unlimited: <b>{unl_count}</b>  |  🔒 Limited: <b>{lim_count}</b>\n\n"
        f"{_L}\n"
        f"💡 Tap any group button to toggle ON/OFF\n"
        f"🟢 = Unlimited (sab free)  |  🔴 = Limited (credits use)\n"
        f"{_L}</blockquote>"
    )

    pp = 8  # per page groups
    st = (page-1)*pp; en = st+pp
    tp = max(1,(total+pp-1)//pp)

    mk = InlineKeyboardMarkup(row_width=1)
    for gid, title in groups[st:en]:
        g = get_group(gid)
        is_unl = safe_g(g,5)==1
        status = "🟢 ON" if is_unl else "🔴 OFF"
        dn = title[:22]+"…" if len(title)>22 else title
        mk.add(_IKB(f"{status} │ {dn}", style="success" if is_unl else "danger",
                    callback_data=f"grpctrl_tog_{gid}_{page}"))

    # Nav buttons
    nav = []
    if page > 1: nav.append(_IKB("⬅️", callback_data=f"grpctrl_pg_{page-1}"))
    nav.append(_IKB(f"{page}/{tp}", callback_data="noop"))
    if en < total: nav.append(_IKB("➡️", callback_data=f"grpctrl_pg_{page+1}"))
    if len(nav) > 1: mk.row(*nav)

    # Global buttons
    mk.add(_IKB("🟢 ALL → UNLIMITED", style="success", callback_data="grpctrl_all_unl"))
    mk.add(_IKB("🔴 ALL → LIMITED", style="danger", callback_data="grpctrl_all_lim"))

    if msg_id:
        try: bot.edit_message_text(txt, chat_id, msg_id, reply_markup=mk, parse_mode='HTML'); return
        except: pass
    bot.send_message(chat_id, txt, reply_markup=mk, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="📋 VIEW GROUPS" and is_admin(m.from_user.id))
def h_viewgrps(m):
    groups=get_all_groups()
    if not groups: bot.send_message(m.chat.id,"<blockquote>❌ No groups.</blockquote>",parse_mode='HTML'); return
    txt=f"<blockquote>📋 <b>ɢʀᴏᴜᴩꜱ</b>\n{_F}\n"
    for i,(gid,title) in enumerate(groups[:5],1):
        g=get_group(gid); s=safe_g(g,7); cr=safe_g(g,4); ul=safe_g(g,5); mu=safe_g(g,8)
        txt+=f"{i}. <b>{title}</b>\n<code>{gid}</code> | S:{s} | C:{'∞' if ul else cr} {'🔇' if mu else '🔊'}\n\n"
    if len(groups)>5: txt+=f"...+{len(groups)-5} more\n"
    txt+="⚡ @Felix_modz1</blockquote>"
    mk=kb_groups_inline()
    if mk: bot.send_message(m.chat.id,txt,reply_markup=mk,parse_mode='HTML')
    else: bot.send_message(m.chat.id,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="➕ ADD GROUP" and is_admin(m.from_user.id))
def h_addgrp(m):
    bot.register_next_step_handler(bot.reply_to(m,"<blockquote>➕ Send group ID:</blockquote>",parse_mode='HTML'),do_addgrp)

def do_addgrp(m):
    if not is_admin(m.from_user.id): return
    try:
        gid=int(m.text.strip())
        try: ch=bot.get_chat(gid); title=ch.title
        except: title=f"Group {gid}"
        add_group_to_db(gid,title)
        bot.reply_to(m,f"<blockquote>✅ Added!\nID: <code>{gid}</code>\n{title}</blockquote>",parse_mode='HTML')
    except Exception as e: bot.reply_to(m,f"<blockquote>❌ {_safe_err(e)}</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🚫 BLOCK USER (ID)" and is_admin(m.from_user.id))
def h_blku(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>🚫 Send User ID:</blockquote>",parse_mode='HTML'),do_blku)

@bot.message_handler(func=lambda m: m.text=="✅ UNBLOCK USER (ID)" and is_admin(m.from_user.id))
def h_ublku(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>✅ Send User ID:</blockquote>",parse_mode='HTML'),do_ublku)

@bot.message_handler(func=lambda m: m.text=="🚫 BLOCK NUMBER" and is_admin(m.from_user.id))
def h_blkn(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>🚫 Send number:</blockquote>",parse_mode='HTML'),do_blkn)

@bot.message_handler(func=lambda m: m.text=="✅ UNBLOCK NUMBER" and is_admin(m.from_user.id))
def h_ublkn(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>✅ Send number:</blockquote>",parse_mode='HTML'),do_ublkn)

@bot.message_handler(func=lambda m: m.text=="📋 BLOCKED LIST" and is_admin(m.from_user.id))
def h_blklist(m):
    bl=get_blocked_identifiers()
    if not bl: bot.reply_to(m,"<blockquote>📋 Empty.</blockquote>",parse_mode='HTML'); return
    txt=f"<blockquote>📋 <b>ʙʟᴏᴄᴋᴇᴅ</b>\n{_F}\n"
    for x,t,d,r in bl[:20]: txt+=f"🔴 {t}: <code>{x}</code> | {r or '-'}\n"
    txt+="⚡ @Felix_modz1</blockquote>"; bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="💎 ADD PREMIUM" and is_admin(m.from_user.id))
def h_prem(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>💎 Send: <code>uid days</code></blockquote>",parse_mode='HTML'),do_prem)

@bot.message_handler(func=lambda m: m.text=="💰 ADD CREDITS" and is_admin(m.from_user.id))
def h_addcr(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>💰 Send: <code>uid amount</code></blockquote>",parse_mode='HTML'),do_addcr)

@bot.message_handler(func=lambda m: m.text=="➖ REMOVE CREDITS" and is_admin(m.from_user.id))
def h_remcr(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>➖ Send: <code>uid amount</code></blockquote>",parse_mode='HTML'),do_remcr)

@bot.message_handler(func=lambda m: m.text=="👥 ADMIN MGMT" and is_admin(m.from_user.id))
def h_adm(m):
    user_state[m.from_user.id]='ADMIN_ADMIN_MGMT'
    bot.send_message(m.chat.id,"<blockquote>👥 <b>Admin Mgmt</b></blockquote>",reply_markup=kb_admin_mgmt(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="➕ ADD ADMIN" and is_admin(m.from_user.id))
def h_addadm(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>➕ Send User ID:</blockquote>",parse_mode='HTML'),do_addadm)

@bot.message_handler(func=lambda m: m.text=="➖ REMOVE ADMIN" and is_admin(m.from_user.id))
def h_remadm(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>➖ Send admin ID:</blockquote>",parse_mode='HTML'),do_remadm)

@bot.message_handler(func=lambda m: m.text=="📋 ADMIN LIST" and is_admin(m.from_user.id))
def h_admlist(m):
    admins=c.execute("SELECT user_id,added_date FROM admins WHERE is_active=1").fetchall()
    txt=f"<blockquote>📋 <b>ᴀᴅᴍɪɴꜱ</b>\n{_F}\n"
    for uid,d in admins:
        role="👑" if uid==OWNER_ID else "👤"
        txt+=f"{role} <code>{uid}</code>\n"
    txt+="⚡ @Felix_modz1</blockquote>"; bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="📢 CHANNEL MGMT" and is_admin(m.from_user.id))
def h_chmgmt(m):
    user_state[m.from_user.id]='ADMIN_CHANNEL_MGMT'
    bot.send_message(m.chat.id,"<blockquote>📢 <b>Channel Mgmt</b></blockquote>",reply_markup=kb_channel_mgmt(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="➕ ADD CHANNEL" and is_admin(m.from_user.id))
def h_addch(m): bot.register_next_step_handler(bot.reply_to(m,"<blockquote>➕ Send channel link:\n<code>https://t.me/username</code></blockquote>",parse_mode='HTML'),do_addch)

@bot.message_handler(func=lambda m: m.text=="➖ REMOVE CHANNEL" and is_admin(m.from_user.id))
def h_remch(m):
    chs=get_force_join_channels()
    if not chs:
        bot.reply_to(m,"<blockquote>❌ Koi channel nahi hai abhi.</blockquote>",parse_mode='HTML'); return
    if _IS_CLONE:
        try: forced_ids={r[0] for r in c.execute("SELECT chat_id FROM clone_forced_channels WHERE is_active=1").fetchall()}
        except: forced_ids=set()
        # Felix ke default channels bhi forced hain
        felix_ids={'@Felix_modz1','@felix_modz1','@Felix_bhai1','@felix_bhai1'}
        removable=[(entry[0],entry[1],entry[2]) for entry in chs if entry[0] not in forced_ids and entry[0] not in felix_ids]
        if not removable:
            bot.reply_to(m,"<blockquote>❌ Koi removable channel nahi.\n⚠️ Original owner ke forced channels remove nahi ho sakte!</blockquote>",parse_mode='HTML'); return
        txt="<blockquote>📋 <b>Channels (Remove ke liye ID bhejo):</b>\n\n"
        for cid,t,u in removable: txt+=f"• <b>{t}</b>\n🆔 <code>{cid}</code>\n\n"
        txt+="Send channel ID to remove:</blockquote>"
        bot.register_next_step_handler(bot.reply_to(m,txt,parse_mode='HTML'),do_remch_clone)
        return
    txt="<blockquote>📋 <b>Channels (Remove ke liye ID bhejo):</b>\n\n"
    for entry in chs: txt+=f"• <b>{entry[1]}</b>\n🆔 <code>{entry[0]}</code>\n\n"
    txt+="Send channel ID to remove:</blockquote>"
    bot.register_next_step_handler(bot.reply_to(m,txt,parse_mode='HTML'),do_remch)

def do_remch_clone(m):
    """Clone me channel remove — forced channels aur Felix ke default channels ko allow nahi"""
    if not is_admin(m.from_user.id): return
    try: forced_ids={r[0] for r in c.execute("SELECT chat_id FROM clone_forced_channels WHERE is_active=1").fetchall()}
    except: forced_ids=set()
    felix_ids={'@Felix_modz1','@felix_modz1','@Felix_bhai1','@felix_bhai1'}
    cid_inp=m.text.strip()
    if cid_inp in forced_ids or cid_inp in felix_ids:
        bot.reply_to(m,"<blockquote>🚫 Ye channel protected hai, remove nahi kar sakte!</blockquote>",parse_mode='HTML'); return
    c.execute("UPDATE force_join_channels SET is_active=0 WHERE chat_id=?",(cid_inp,)); conn.commit()
    bot.reply_to(m,"<blockquote>✅ Channel remove ho gaya!</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="📋 CHANNEL LIST" and is_admin(m.from_user.id))
def h_chlist(m):
    chs=get_force_join_channels()
    if not chs:
        bot.reply_to(m,"<blockquote>📋 Koi channel nahi hai abhi.\n\n➕ ADD CHANNEL se add karo.</blockquote>",parse_mode='HTML'); return
    txt=f"<blockquote>📋 <b>Force Join Channels</b>\n{'─'*22}\n\n"
    for i,entry in enumerate(chs,1):
        cid=entry[0]; t=entry[1]; u=entry[2]
        txt+=f"{i}. <b>{t}</b>\n🆔 <code>{cid}</code>\n🔗 {u}\n\n"
    txt+=f"{'─'*22}\nTotal: {len(chs)} channel(s)</blockquote>"
    bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🎫 GEN REDEEM CODE" and is_admin(m.from_user.id))
def h_gencode(m):
    if _IS_CLONE:
        # Clone bot: 100 codes/day limit check
        today = datetime.now().strftime("%Y-%m-%d")
        used_today = c.execute(
            "SELECT COUNT(*) FROM redeem_codes WHERE created_by=? AND created_date LIKE ?",
            (m.from_user.id, today+"%")).fetchone()[0] or 0
        remaining = 100 - used_today
        if remaining <= 0:
            bot.reply_to(m, f"<blockquote>❌ <b>Daily limit reached!</b>\n100 codes/day limit — kal aao!\n⚡ @Felix_modz1</blockquote>", parse_mode='HTML')
            return
        bot.register_next_step_handler(bot.reply_to(m,
            f"<blockquote>🎫 Send: <code>credits limit</code>\nExample: <code>50 10</code>\n\n"
            f"⚠️ Max credits per code: <b>100</b>\n"
            f"📊 Aaj ke baaki codes: <b>{remaining}/100</b>\n⚡ @Felix_modz1</blockquote>",
            parse_mode='HTML'), do_gencode)
    else:
        bot.register_next_step_handler(bot.reply_to(m,"<blockquote>🎫 Send: <code>credits limit</code>\nExample: <code>10 50</code></blockquote>",parse_mode='HTML'),do_gencode)

@bot.message_handler(func=lambda m: m.text=="🎁 GEN PREMIUM CODE" and is_admin(m.from_user.id))
def h_gen_prem_code(m):
    bot.register_next_step_handler(bot.reply_to(m,
        "<blockquote>🎁 <b>ɢᴇɴ ᴩʀᴇᴍɪᴜᴍ ᴄᴏᴅᴇ</b>\n"
        f"{_F}\n"
        "Send: <code>days limit</code>\n"
        "Example: <code>30 1</code> → 30 din ka premium, 1 user\n"
        "Example: <code>7 5</code> → 7 din, 5 users\n"
        f"{_F}\n⚡ @Felix_modz1</blockquote>",
        parse_mode='HTML'),do_gen_premium_code)

@bot.message_handler(func=lambda m: m.text=="💀 REVOKE ALL PREMIUM" and is_admin(m.from_user.id))
def h_revoke_premium(m):
    mk=InlineKeyboardMarkup()
    mk.row(_IKB("💀 YES, REVOKE ALL",style="danger",callback_data="confirm_revoke_premium"),
           _IKB("❌ CANCEL",style="success",callback_data="cancel_revoke_premium"))
    # Count how many will be affected
    prem_users=c.execute("SELECT COUNT(*) FROM users WHERE is_premium=1").fetchone()[0] or 0
    prem_codes=c.execute("SELECT COUNT(*) FROM premium_codes").fetchone()[0] or 0
    bot.send_message(m.chat.id,(
        f"<blockquote>"+_CL_TOP()+"\n"
        f"│  💀 <b>REVOKE ALL PREMIUM</b>\n"
        +_CL_BOT()+"\n\n"
        f"⚠️ <b>YE ACTION:</b>\n"
        f"• 💎 {prem_users} users ka premium remove hoga\n"
        f"• 🎟️ {prem_codes} premium codes delete honge\n"
        f"• 💰 Jo credits codes se mile the, woh bhi remove honge\n"
        f"• ❌ Sabhi redeemed records clear honge\n\n"
        f"<b>Confirm karo?</b>\n\n"
        f"{_F}\n⚡ @Felix_modz1</blockquote>"
    ),reply_markup=mk,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🧹 CLEAR HISTORY" and is_admin(m.from_user.id))
def h_clear(m):
    mk=InlineKeyboardMarkup()
    mk.row(_IKB("✅ YES",style="success",callback_data="confirm_clear"),_IKB("❌ NO",style="danger",callback_data="cancel_clear"))
    bot.send_message(m.chat.id,"<blockquote>⚠️ Clear all search history?</blockquote>",reply_markup=mk,parse_mode='HTML')

# Welcome settings handlers
@bot.message_handler(func=lambda m: m.text=="🖼 SET WELCOME IMAGE" and is_admin(m.from_user.id))
def h_wimg(m):
    bot.reply_to(m,"<blockquote>🖼 Send image:</blockquote>",parse_mode='HTML')
    bot.register_next_step_handler_by_chat_id(m.chat.id,do_wimg)

def do_wimg(m):
    if not is_admin(m.from_user.id): return
    if m.photo:
        try:
            fi=bot.get_file(m.photo[-1].file_id); d=bot.download_file(fi.file_path)
            fn=os.path.join(_SCRIPT_DIR, f"wimg_{_BOT_ID}_{int(time.time())}.jpg")
            with open(fn,'wb') as f: f.write(d)
            c.execute("INSERT OR IGNORE INTO welcome_settings(id) VALUES(1)")
            c.execute("UPDATE welcome_settings SET welcome_image=? WHERE id=1",(fn,)); conn.commit()
            _invalidate_welcome_cache()
            bot.reply_to(m,"<blockquote>✅ <b>Welcome image set!</b>\nAb naye /start pe ye image aayegi.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except Exception as _we: bot.reply_to(m,f"<blockquote>❌ Error: {_we}</blockquote>",parse_mode='HTML')
    else: bot.reply_to(m,"<blockquote>❌ Photo bhejo (image)!</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🎥 SET WELCOME VIDEO" and is_admin(m.from_user.id))
def h_wvid(m):
    bot.reply_to(m,"<blockquote>🎥 Send video:</blockquote>",parse_mode='HTML')
    bot.register_next_step_handler_by_chat_id(m.chat.id,do_wvid)

def do_wvid(m):
    if not is_admin(m.from_user.id): return
    if m.video:
        try:
            fi=bot.get_file(m.video.file_id); d=bot.download_file(fi.file_path)
            fn=os.path.join(_SCRIPT_DIR, f"wvid_{_BOT_ID}_{int(time.time())}.mp4")
            with open(fn,'wb') as f: f.write(d)
            c.execute("INSERT OR IGNORE INTO welcome_settings(id) VALUES(1)")
            c.execute("UPDATE welcome_settings SET welcome_video=? WHERE id=1",(fn,)); conn.commit()
            _invalidate_welcome_cache()
            bot.reply_to(m,"<blockquote>✅ <b>Welcome video set!</b>\nAb naye /start pe ye video aayega.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except Exception as _wve: bot.reply_to(m,f"<blockquote>❌ Error: {_wve}</blockquote>",parse_mode='HTML')
    else: bot.reply_to(m,"<blockquote>❌ Video file bhejo!</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="📝 SET WELCOME CAPTION" and is_admin(m.from_user.id))
def h_wcap(m):
    msg=bot.reply_to(m,"<blockquote>📝 Send caption:</blockquote>",parse_mode='HTML')
    def do(msg2):
        c.execute("UPDATE welcome_settings SET welcome_caption=? WHERE id=1",(msg2.text,)); conn.commit()
        bot.reply_to(msg2,"<blockquote>✅ Done!</blockquote>",parse_mode='HTML')
    bot.register_next_step_handler(msg,do)

@bot.message_handler(func=lambda m: m.text=="🎪 SET FIRST TIME STICKER" and is_admin(m.from_user.id))
def h_stk(m):
    bot.reply_to(m,"<blockquote>🎪 Send sticker:</blockquote>",parse_mode='HTML')
    bot.register_next_step_handler_by_chat_id(m.chat.id,do_stk)

def do_stk(m):
    if not is_admin(m.from_user.id): return
    if m.sticker:
        c.execute("INSERT OR IGNORE INTO welcome_settings(id) VALUES(1)")
        c.execute("UPDATE welcome_settings SET first_time_sticker=? WHERE id=1",(m.sticker.file_id,)); conn.commit()
        bot.reply_to(m,"<blockquote>✅ <b>Sticker set!</b>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
    else: bot.reply_to(m,"<blockquote>❌ Sticker bhejo!</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🔄 RESET TO DEFAULT" and is_admin(m.from_user.id))
def h_wreset(m):
    c.execute("UPDATE welcome_settings SET welcome_image=NULL,welcome_video=NULL,first_time_sticker=NULL WHERE id=1")
    conn.commit(); bot.reply_to(m,"<blockquote>✅ Reset!</blockquote>",parse_mode='HTML')

def _gw_group_list_txt(prefix):
    groups=get_all_groups()
    if not groups: return None,None
    txt=f"<blockquote>{prefix}\n\nKis group ke liye?\n"
    for i,(gid,title) in enumerate(groups[:10],1):
        txt+=f"{i}. {title[:25]} — <code>{gid}</code>\n"
    txt+="\nGroup ID bhejo (ya 0 = all groups):\n⚡ @Felix_modz1</blockquote>"
    return txt,groups

@bot.message_handler(func=lambda m: m.text=="🖼 GROUP IMAGE SET" and is_admin(m.from_user.id))
def h_gwimg(m):
    txt,groups=_gw_group_list_txt("🖼 <b>GROUP IMAGE SET</b>")
    if not txt: bot.reply_to(m,"<blockquote>❌ Koi group nahi!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[m.from_user.id]={'state':'GW_IMG_WAIT_GID'}
    bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🎥 GROUP VIDEO SET" and is_admin(m.from_user.id))
def h_gwvid(m):
    txt,groups=_gw_group_list_txt("🎥 <b>GROUP VIDEO SET</b>")
    if not txt: bot.reply_to(m,"<blockquote>❌ Koi group nahi!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[m.from_user.id]={'state':'GW_VID_WAIT_GID'}
    bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🎞 GROUP VIDEO LIST" and is_admin(m.from_user.id))
def h_gwvlist(m):
    txt,groups=_gw_group_list_txt("🎞 <b>GROUP VIDEO LIST</b>\n(1-5 videos — har member pe alag video)")
    if not txt: bot.reply_to(m,"<blockquote>❌ Koi group nahi!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[m.from_user.id]={'state':'GW_VLIST_WAIT_GID'}
    bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🎪 GROUP STICKER SET" and is_admin(m.from_user.id))
def h_gwstk(m):
    txt,groups=_gw_group_list_txt("🎪 <b>GROUP STICKER SET</b>\n⚠️ Sticker sirf GROUP welcome mein — BOT DM mein nahi")
    if not txt: bot.reply_to(m,"<blockquote>❌ Koi group nahi!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[m.from_user.id]={'state':'GW_STK_WAIT_GID'}
    bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="📝 GROUP WELCOME TEXT" and is_admin(m.from_user.id))
def h_gwtxt(m):
    txt,groups=_gw_group_list_txt("📝 <b>GROUP WELCOME TEXT</b>\nVariables: {name} {id} {username} {group}")
    if not txt: bot.reply_to(m,"<blockquote>❌ Koi group nahi!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[m.from_user.id]={'state':'GW_TXT_WAIT_GID'}
    bot.reply_to(m,txt,parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="🔄 GROUP WELCOME RESET" and is_admin(m.from_user.id))
def h_gwreset(m):
    txt,groups=_gw_group_list_txt("🔄 <b>GROUP WELCOME RESET</b>\n(0 = ALL groups reset)")
    if not txt: bot.reply_to(m,"<blockquote>❌ Koi group nahi!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[m.from_user.id]={'state':'GW_RESET_WAIT_GID'}
    bot.reply_to(m,txt,parse_mode='HTML')

# ── Group Welcome STATE MACHINE ──
@bot.message_handler(func=lambda m: m.chat.type=='private' and is_admin(m.from_user.id) and isinstance(user_state.get(m.from_user.id),dict) and user_state.get(m.from_user.id,{}).get('state','').startswith('GW_'), content_types=['text','photo','video','sticker','document'])
def h_gw_state(m):
    uid=m.from_user.id; st=user_state.get(uid,{}); sname=st.get('state','')

    def _get_target_gids(txt):
        try:
            v=int(txt.strip())
            if v==0: return [gid for gid,_ in get_all_groups()]
            return [v]
        except: return []

    # ── Waiting for GID input ──
    WAIT_GID_STATES=('GW_IMG_WAIT_GID','GW_VID_WAIT_GID','GW_VLIST_WAIT_GID',
                     'GW_STK_WAIT_GID','GW_TXT_WAIT_GID','GW_RESET_WAIT_GID')
    if sname in WAIT_GID_STATES:
        if not m.text:
            bot.reply_to(m,"<blockquote>❌ Text mein group ID bhejo!</blockquote>",parse_mode='HTML'); return
        gids=_get_target_gids(m.text)
        if not gids:
            bot.reply_to(m,"<blockquote>❌ Valid group ID nahi! List mein se copy karo.</blockquote>",parse_mode='HTML'); return
        new_state=sname.replace('_WAIT_GID','_WAIT_MEDIA')
        if new_state=='GW_RESET_WAIT_MEDIA':
            for gid in gids:
                try:
                    c.execute("UPDATE group_welcome_settings SET welcome_image=NULL,welcome_video=NULL,video_list=NULL,group_sticker=NULL,welcome_text=NULL WHERE group_id=?",(gid,))
                    conn.commit()
                except: pass
            user_state[uid]={'state':'ADMIN_GRP_WELCOME'}
            bot.reply_to(m,f"<blockquote>✅ <b>{len(gids)} group(s) reset!</b>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
            return
        labels={
            'GW_IMG_WAIT_MEDIA':"🖼 Ab image bhejo (photo send karo):",
            'GW_VID_WAIT_MEDIA':"🎥 Ab video file bhejo:",
            'GW_VLIST_WAIT_MEDIA':"🎞 Ek-ek karke 1-5 videos bhejo\n(Telegram video file bhejo)\nJab sab ho jaye toh <b>DONE</b> likho:",
            'GW_STK_WAIT_MEDIA':"🎪 Ab sticker bhejo:",
            'GW_TXT_WAIT_MEDIA':"📝 Ab welcome text bhejo:\n<i>Variables: {name} {id} {username} {group}</i>",
        }
        user_state[uid]={'state':new_state,'gids':gids,'vlist':[]}
        bot.reply_to(m,f"<blockquote>{labels.get(new_state,'Send media:')}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        return

    # ── Waiting for MEDIA ──
    gids=st.get('gids',[])
    if not gids: user_state[uid]={'state':'none'}; return

    if sname=='GW_IMG_WAIT_MEDIA':
        if not m.photo:
            bot.reply_to(m,"<blockquote>❌ Photo bhejo (image)!</blockquote>",parse_mode='HTML'); return
        fi=bot.get_file(m.photo[-1].file_id); d=bot.download_file(fi.file_path)
        for gid in gids:
            fn=os.path.join(_SCRIPT_DIR,f"gwimg_{gid}_{int(time.time())}.jpg")
            with open(fn,'wb') as f: f.write(d)
            set_group_welcome_image(gid,fn)
        user_state[uid]={'state':'ADMIN_GRP_WELCOME'}
        bot.reply_to(m,f"<blockquote>✅ <b>Group image set!</b> ({len(gids)} group(s))\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

    elif sname=='GW_VID_WAIT_MEDIA':
        if not m.video:
            bot.reply_to(m,"<blockquote>❌ Video file bhejo!</blockquote>",parse_mode='HTML'); return
        fi=bot.get_file(m.video.file_id); d=bot.download_file(fi.file_path)
        for gid in gids:
            fn=os.path.join(_SCRIPT_DIR,f"gwvid_{gid}_{int(time.time())}.mp4")
            with open(fn,'wb') as f: f.write(d)
            set_group_welcome_video(gid,fn)
        user_state[uid]={'state':'ADMIN_GRP_WELCOME'}
        bot.reply_to(m,f"<blockquote>✅ <b>Group video set!</b> ({len(gids)} group(s))\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

    elif sname=='GW_VLIST_WAIT_MEDIA':
        vlist=st.get('vlist',[])
        if m.text and m.text.strip().upper()=='DONE':
            if not vlist:
                bot.reply_to(m,"<blockquote>❌ Pehle kuch videos bhejo!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            for gid in gids: set_group_welcome_video_list(gid,json.dumps(vlist))
            user_state[uid]={'state':'ADMIN_GRP_WELCOME'}
            bot.reply_to(m,f"<blockquote>✅ <b>{len(vlist)} videos set! ({len(gids)} group(s))</b>\nHar naye member pe alag video chalega.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
            return
        fid=None
        if m.video: fid=m.video.file_id
        elif m.document and m.document.mime_type and m.document.mime_type.startswith('video'): fid=m.document.file_id
        if fid:
            vlist.append(fid)
            user_state[uid]={'state':sname,'gids':gids,'vlist':vlist}
            remaining=5-len(vlist)
            if remaining>0:
                bot.reply_to(m,f"<blockquote>✅ Video {len(vlist)} add hua!\n{remaining} aur bhej sakte ho.\nJab ho jaye <b>DONE</b> likho.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
            else:
                for gid in gids: set_group_welcome_video_list(gid,json.dumps(vlist))
                user_state[uid]={'state':'ADMIN_GRP_WELCOME'}
                bot.reply_to(m,f"<blockquote>✅ <b>5 videos set! ({len(gids)} group(s))</b>\nHar naye member pe alag video.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        else:
            bot.reply_to(m,"<blockquote>❌ Video file bhejo ya DONE likho!</blockquote>",parse_mode='HTML')

    elif sname=='GW_STK_WAIT_MEDIA':
        if not m.sticker:
            bot.reply_to(m,"<blockquote>❌ Sticker bhejo!</blockquote>",parse_mode='HTML'); return
        for gid in gids: set_group_welcome_sticker(gid,m.sticker.file_id)
        user_state[uid]={'state':'ADMIN_GRP_WELCOME'}
        bot.reply_to(m,f"<blockquote>✅ <b>Group sticker set!</b> ({len(gids)} group(s))\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

    elif sname=='GW_TXT_WAIT_MEDIA':
        if not m.text:
            bot.reply_to(m,"<blockquote>❌ Text bhejo!</blockquote>",parse_mode='HTML'); return
        for gid in gids:
            c.execute("INSERT OR IGNORE INTO group_welcome_settings(group_id,welcome_on,group_rules,updated_date) VALUES(?,1,'',?)",(gid,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            c.execute("UPDATE group_welcome_settings SET welcome_text=?,updated_date=? WHERE group_id=?",(m.text,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),gid))
            conn.commit()
        user_state[uid]={'state':'ADMIN_GRP_WELCOME'}
        bot.reply_to(m,f"<blockquote>✅ <b>Group welcome text set!</b> ({len(gids)} group(s))\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text=="⚙️ TOGGLE FEATURES" and is_admin(m.from_user.id))
def h_toggle_features(m):
    uid=m.from_user.id
    user_state[uid]='ADMIN_FEATURE_TOGGLE'
    bot.send_message(m.chat.id,
        f"<blockquote>━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ <b>ꜰᴇᴀᴛᴜʀᴇ ᴛᴏɢɢʟᴇ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ = ON   |   ❌ = OFF\n"
        f"Kisi bhi button ko tap karo toggle karne ke liye:\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ @Felix_modz1</blockquote>",
        reply_markup=kb_features(), parse_mode='HTML')

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("ftog_") and is_admin(c.from_user.id))
def cb_ftog(call):
    uid=call.from_user.id
    fn=call.data[5:]  # strip "ftog_"
    if fn=='back':
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(uid,"<blockquote>⚙️ <b>Admin Panel</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML')
        bot.answer_callback_query(call.id,"🔙 Back to Admin")
        return
    valid_fns={'number','username','tgid','aadhar','instagram','bomber','freefire','freefire_like','vehicle'}
    if fn not in valid_fns:
        bot.answer_callback_query(call.id,"❌ Invalid feature!"); return
    new_state=toggle_feature(fn,uid)
    status="✅ ON" if new_state else "❌ OFF"
    bot.answer_callback_query(call.id, f"{fn.upper()} → {status}")
    # Refresh inline keyboard
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb_features())
    except: pass



@bot.message_handler(func=lambda m: m.text and is_admin(m.from_user.id) and user_state.get(m.from_user.id)=='ADMIN_FEAT_ENABLE')
def h_feat_enable(m):
    uid=m.from_user.id; txt=m.text.strip().lower()
    fm={'freefire_like':'freefire_like','freefire':'freefire','number':'number','username':'username',
        'aadhar':'aadhar','instagram':'instagram','tgid':'tgid','vehicle':'vehicle',
        'bomber':'bomber'}
    if txt in fm:
        # Force enable karo
        c.execute("UPDATE feature_toggles SET is_enabled=1,updated_by=?,updated_date=? WHERE feature_name=?",
                 (uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),fm[txt])); conn.commit()
        bot.send_message(uid,f"<blockquote>✅ <b>{txt.upper()}</b> enable ho gaya!</blockquote>",parse_mode='HTML')
    else:
        bot.send_message(uid,"<blockquote>❌ Invalid feature name!</blockquote>",parse_mode='HTML')
    user_state[uid]='ADMIN_FEATURE_TOGGLE'
    bot.send_message(uid,"<blockquote>⚙️ Features:</blockquote>",reply_markup=kb_features(),parse_mode='HTML')

# Admin process functions
def do_broadcast(m):
    if not is_admin(m.from_user.id): return
    users=c.execute("SELECT user_id FROM users WHERE is_blocked=0").fetchall()
    groups=c.execute("SELECT group_id FROM groups WHERE is_blocked=0").fetchall()
    tot=len(users)+len(groups); sent=0; fail=0
    sm=bot.reply_to(m,f"<blockquote>📢 Broadcasting to {len(users)} users + {len(groups)} groups...</blockquote>",parse_mode='HTML')

    def _send_one(chat_id):
        """copy_message — premium tg-emoji ke saath exact copy, hide nahi hoga"""
        try:
            bot.copy_message(chat_id, m.chat.id, m.message_id)
            return True
        except:
            # Fallback: content type ke hisaab se bhejo
            try:
                if m.content_type=='text': bot.send_message(chat_id, m.text, parse_mode='HTML')
                elif m.content_type=='photo': bot.send_photo(chat_id, m.photo[-1].file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='video': bot.send_video(chat_id, m.video.file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='sticker': bot.send_sticker(chat_id, m.sticker.file_id)
                elif m.content_type=='document': bot.send_document(chat_id, m.document.file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='animation': bot.send_animation(chat_id, m.animation.file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='voice': bot.send_voice(chat_id, m.voice.file_id)
                elif m.content_type=='audio': bot.send_audio(chat_id, m.audio.file_id, caption=m.caption or "", parse_mode='HTML')
                return True
            except: return False

    # Users ko bhejo
    for (uid,) in users:
        if _send_one(uid): sent+=1
        else: fail+=1
        time.sleep(0.04)

    # Groups ko bhi bhejo
    for (gid,) in groups:
        if _send_one(gid): sent+=1
        else: fail+=1
        time.sleep(0.05)

    try: bot.edit_message_text(
        f"<blockquote>✅ <b>Broadcast Done!</b>\n"
        f"👥 Users: <b>{len(users)}</b> | 📢 Groups: <b>{len(groups)}</b>\n"
        f"✅ Sent: <b>{sent}</b> | ❌ Failed: <b>{fail}</b>\n"
        f"⚡ @Felix_modz1</blockquote>",
        sm.chat.id, sm.message_id, parse_mode='HTML')
    except: pass

def do_premium_broadcast(m):
    """
    💎 PREMIUM BROADCAST — Sab users + groups ko copy_message se bhejo.
    copy_message → tg-emoji / premium emoji FULLY visible, hide nahi hoga.
    """
    if not is_admin(m.from_user.id): return
    users  = c.execute("SELECT user_id FROM users WHERE is_blocked=0").fetchall()
    groups = c.execute("SELECT group_id FROM groups WHERE is_blocked=0").fetchall()
    total  = len(users) + len(groups)
    sent=0; fail=0

    sm=bot.reply_to(m,
        f"<blockquote>💎 <b>PREMIUM BROADCAST</b>\n"
        f"👥 Users: <b>{len(users)}</b> | 📢 Groups: <b>{len(groups)}</b>\n\n"
        f"⏳ Sending with full premium emoji...</blockquote>",
        parse_mode='HTML')

    def _copy_one(chat_id):
        """copy_message — premium tg-emoji ke saath exact copy, bilkul hide nahi hoga"""
        try:
            bot.copy_message(chat_id, m.chat.id, m.message_id)
            return True
        except:
            # Fallback: direct send
            try:
                if m.content_type=='text':
                    bot.send_message(chat_id, m.text, parse_mode='HTML')
                elif m.content_type=='photo':
                    bot.send_photo(chat_id, m.photo[-1].file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='video':
                    bot.send_video(chat_id, m.video.file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='sticker':
                    bot.send_sticker(chat_id, m.sticker.file_id)
                elif m.content_type=='document':
                    bot.send_document(chat_id, m.document.file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='animation':
                    bot.send_animation(chat_id, m.animation.file_id, caption=m.caption or "", parse_mode='HTML')
                elif m.content_type=='voice':
                    bot.send_voice(chat_id, m.voice.file_id)
                elif m.content_type=='audio':
                    bot.send_audio(chat_id, m.audio.file_id, caption=m.caption or "", parse_mode='HTML')
                return True
            except: return False

    # Sab users
    for (recv_uid,) in users:
        if _copy_one(recv_uid): sent+=1
        else: fail+=1
        time.sleep(0.04)

    # Sab groups
    for (gid,) in groups:
        if _copy_one(gid): sent+=1
        else: fail+=1
        time.sleep(0.05)

    try: bot.edit_message_text(
        f"<blockquote>✅ <b>💎 Premium Broadcast Done!</b>\n\n"
        f"👥 Users: <b>{len(users)}</b> | 📢 Groups: <b>{len(groups)}</b>\n"
        f"✅ Sent: <b>{sent}</b> | ❌ Failed: <b>{fail}</b>\n\n"
        f"💎 Premium emoji — fully visible!\n"
        f"⚡ @Felix_modz1</blockquote>",
        sm.chat.id, sm.message_id, parse_mode='HTML')
    except: pass

def do_blku(m):
    if not is_admin(m.from_user.id): return
    try:
        uid=int(m.text.strip())
        if uid==OWNER_ID or is_admin(uid): bot.reply_to(m,"<blockquote>❌ Can't block this user!</blockquote>",parse_mode='HTML'); return
        block_identifier(str(uid),'user_id',m.from_user.id,"Blocked by admin"); update_user(uid,is_blocked=1)
        bot.reply_to(m,f"<blockquote>✅ User <code>{uid}</code> blocked!</blockquote>",parse_mode='HTML')
    except: bot.reply_to(m,"<blockquote>❌ Invalid ID!</blockquote>",parse_mode='HTML')

def do_ublku(m):
    if not is_admin(m.from_user.id): return
    x=m.text.strip()
    if unblock_identifier(x):
        try: update_user(int(x),is_blocked=0)
        except: pass
        bot.reply_to(m,"<blockquote>✅ Unblocked!</blockquote>",parse_mode='HTML')
    else: bot.reply_to(m,"<blockquote>❌ Not found!</blockquote>",parse_mode='HTML')

def do_blkn(m):
    if not is_admin(m.from_user.id): return
    n=re.sub(r'\D','',m.text.strip())
    if len(n)!=10: bot.reply_to(m,"<blockquote>❌ Invalid!</blockquote>",parse_mode='HTML'); return
    block_identifier(n,'number',m.from_user.id,"Blocked"); bot.reply_to(m,f"<blockquote>✅ Number blocked!</blockquote>",parse_mode='HTML')

def do_ublkn(m):
    if not is_admin(m.from_user.id): return
    if unblock_identifier(m.text.strip()): bot.reply_to(m,"<blockquote>✅ Unblocked!</blockquote>",parse_mode='HTML')
    else: bot.reply_to(m,"<blockquote>❌ Not found!</blockquote>",parse_mode='HTML')

def do_prem(m):
    if not is_admin(m.from_user.id): return
    try:
        p=m.text.split(); uid_t,days=int(p[0]),int(p[1])
        until=(datetime.now()+timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        update_user(uid_t,is_premium=1,premium_until=until)
        bot.reply_to(m,f"<blockquote>✅ Premium {days} days to <code>{uid_t}</code>!</blockquote>",parse_mode='HTML')
    except: bot.reply_to(m,"<blockquote>❌ Format: uid days</blockquote>",parse_mode='HTML')

def do_addcr(m):
    if not is_admin(m.from_user.id): return
    try:
        p=m.text.split(); uid_t,cr=int(p[0]),int(p[1])
        c.execute("UPDATE users SET credits=credits+? WHERE user_id=?",(cr,uid_t)); conn.commit()
        bot.reply_to(m,f"<blockquote>✅ +{cr} credits to <code>{uid_t}</code>!</blockquote>",parse_mode='HTML')
    except: bot.reply_to(m,"<blockquote>❌ Format: uid amount</blockquote>",parse_mode='HTML')

def do_remcr(m):
    if not is_admin(m.from_user.id): return
    try:
        p=m.text.split(); uid_t,amt=int(p[0]),int(p[1])
        user=get_user(uid_t)
        if not user: bot.reply_to(m,"<blockquote>❌ User not found!</blockquote>",parse_mode='HTML'); return
        nc=max(0,user[5]-amt); c.execute("UPDATE users SET credits=? WHERE user_id=?",(nc,uid_t)); conn.commit()
        bot.reply_to(m,f"<blockquote>✅ -{amt} credits. New: {nc}</blockquote>",parse_mode='HTML')
    except: bot.reply_to(m,"<blockquote>❌ Format: uid amount</blockquote>",parse_mode='HTML')

def do_addadm(m):
    if not is_admin(m.from_user.id): return
    try:
        uid=int(m.text.strip())
        c.execute("INSERT OR REPLACE INTO admins(user_id,added_by,added_date,is_active) VALUES(?,?,?,1)",
                 (uid,m.from_user.id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        _admin_cache.pop(uid, None)  # cache invalidate karo taaki turant admin bane
        bot.reply_to(m,f"<blockquote>✅ <code>{uid}</code> is now admin!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
    except: bot.reply_to(m,"<blockquote>❌ Invalid!</blockquote>",parse_mode='HTML')

def do_remadm(m):
    if not is_admin(m.from_user.id): return
    try:
        uid=int(m.text.strip())
        if uid==OWNER_ID: bot.reply_to(m,"<blockquote>❌ Can't remove owner!</blockquote>",parse_mode='HTML'); return
        c.execute("UPDATE admins SET is_active=0 WHERE user_id=?",(uid,)); conn.commit()
        _admin_cache.pop(uid, None)  # cache invalidate
        bot.reply_to(m,f"<blockquote>✅ Admin <code>{uid}</code> removed!</blockquote>",parse_mode='HTML')
    except: bot.reply_to(m,"<blockquote>❌ Invalid!</blockquote>",parse_mode='HTML')

def do_addch(m):
    if not is_admin(m.from_user.id): return
    lnk=m.text.strip()
    # @username format bhi support karo
    if lnk.startswith('@') and not lnk.startswith('https://'):
        lnk = f"https://t.me/{lnk.lstrip('@')}"
    if not lnk.startswith('https://t.me/'):
        bot.reply_to(m,"<blockquote>❌ Invalid link!\nExample: <code>https://t.me/yourchannel</code>\nPrivate: <code>https://t.me/+invitelink</code>\nYa @username</blockquote>",parse_mode='HTML'); return
    try:
        if '+' in lnk:
            # Private channel invite link — directly save karo, member check zaruri nahi
            cid=lnk; t="Private Channel"
            c.execute("INSERT OR REPLACE INTO force_join_channels(chat_id,chat_title,chat_url,added_by,added_date,is_active) VALUES(?,?,?,?,?,1)",
                     (cid,t,lnk,m.from_user.id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
            bot.reply_to(m,f"<blockquote>✅ Private channel force join me add ho gaya!\n📢 Private Channel\n🔗 <code>{lnk}</code>\n\n⚠️ Note: Bot ko channel ka admin banana hoga member check ke liye.</blockquote>",parse_mode='HTML')
        else:
            u=lnk.split('t.me/')[1].strip('/')
            try:
                ch=bot.get_chat(f"@{u}"); cid=str(ch.id); t=ch.title or u
            except:
                # Bot channel mein nahi — phir bhi @username se save karo
                cid=f"@{u}"; t=u
            c.execute("INSERT OR REPLACE INTO force_join_channels(chat_id,chat_title,chat_url,added_by,added_date,is_active) VALUES(?,?,?,?,?,1)",
                     (cid,t,lnk,m.from_user.id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
            bot.reply_to(m,f"<blockquote>✅ Force Join channel add ho gaya!\n📢 <b>{t}</b>\n🆔 <code>{cid}</code>\n🔗 {lnk}</blockquote>",parse_mode='HTML')
    except Exception as e:
        bot.reply_to(m,f"<blockquote>❌ Error: {_safe_err(e)}\n\nSahi format:\n<code>https://t.me/channelname</code></blockquote>",parse_mode='HTML')

def do_remch(m):
    if not is_admin(m.from_user.id): return
    c.execute("UPDATE force_join_channels SET is_active=0 WHERE chat_id=?",(m.text.strip(),)); conn.commit()
    bot.reply_to(m,"<blockquote>✅ Removed!</blockquote>",parse_mode='HTML')

def do_gencode(m):
    if not is_admin(m.from_user.id): return
    try:
        p=m.text.strip().split(); cr=int(p[0]); lim=int(p[1]) if len(p)>1 else 0
        # Clone bot: max 100 credits per code
        if _IS_CLONE and cr > 100:
            bot.reply_to(m,
                f"<blockquote>❌ <b>Max 100 credits allowed!</b>\n"
                f"📊 Tune {cr} dala — max 100 hi de sakta hai.\n"
                f"💡 Example: <code>100 50</code>\n"
                f"⚡ @Felix_modz1</blockquote>", parse_mode='HTML'); return
        # Clone bot: 100 codes/day limit
        if _IS_CLONE:
            today = datetime.now().strftime("%Y-%m-%d")
            used_today = c.execute(
                "SELECT COUNT(*) FROM redeem_codes WHERE created_by=? AND created_date LIKE ?",
                (m.from_user.id, today+"%")).fetchone()[0] or 0
            remaining = 100 - used_today
            if remaining <= 0:
                bot.reply_to(m,
                    f"<blockquote>❌ <b>Daily limit reach ho gayi!</b>\n"
                    f"📊 Aaj 100/100 codes generate ho chuke hain.\n"
                    f"🕐 Kal midnight ke baad dobara try karo.\n"
                    f"⚡ @Felix_modz1</blockquote>", parse_mode='HTML'); return
        code=generate_code()
        c.execute("INSERT INTO redeem_codes(code,credits,redeem_limit,created_by,created_date) VALUES(?,?,?,?,?)",
                 (code,cr,lim,m.from_user.id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        # Clone mein remaining count bhi dikhao
        _rem_txt = ""
        if _IS_CLONE:
            today2 = datetime.now().strftime("%Y-%m-%d")
            _used2 = c.execute("SELECT COUNT(*) FROM redeem_codes WHERE created_by=? AND created_date LIKE ?",
                (m.from_user.id, today2+"%")).fetchone()[0] or 0
            _rem_txt = f"\n📊 Aaj baaki: <b>{100-_used2}/100</b>"
        bot.reply_to(m,(f"<blockquote>✅ <b>Code Generated!</b>\n"
                        f"🎫 Code: <code>{code}</code>\n"
                        f"💰 Credits: <b>{cr}</b>\n"
                        f"🔢 Limit: <b>{lim or 'Unlimited'}</b>"
                        f"{_rem_txt}\n⚡ @Felix_modz1</blockquote>"),parse_mode='HTML')
    except Exception as e: bot.reply_to(m,f"<blockquote>❌ {_safe_err(e)}</blockquote>",parse_mode='HTML')

def do_gen_premium_code(m):
    if not is_admin(m.from_user.id): return
    try:
        p=m.text.strip().split(); days=int(p[0]); lim=int(p[1]) if len(p)>1 else 1
        code=generate_premium_code()
        c.execute("INSERT INTO premium_codes(code,days,redeem_limit,created_by,created_date) VALUES(?,?,?,?,?)",
                 (code,days,lim,m.from_user.id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        bot.reply_to(m,(f"<blockquote>💎 <b>ᴩʀᴇᴍɪᴜᴍ ᴄᴏᴅᴇ ɢᴇɴᴇʀᴀᴛᴇᴅ!</b>\n"
                        f"{_F}\n"
                        f"🔑 Code: <code>{code}</code>\n"
                        f"📅 Days: <b>{days}</b>\n"
                        f"🔢 Limit: <b>{lim}</b> user{'s' if lim>1 else ''}\n"
                        f"{_F}\n"
                        f"📤 User is ko /premium se redeem kare\n"
                        f"⚡ @Felix_modz1</blockquote>"),parse_mode='HTML')
    except Exception as e: bot.reply_to(m,f"<blockquote>❌ Format: days limit\nExample: 30 1\n{_safe_err(e)}</blockquote>",parse_mode='HTML')

@bot.message_handler(content_types=['users_shared'])
def h_user_shared(m):
    uid=m.from_user.id; user=get_user(uid)
    if not user or not m.users_shared or not m.users_shared.user_ids: return
    if user[6]==1: bot.reply_to(m,"<blockquote>⚠️ You are blocked!</blockquote>",parse_mode='HTML'); return
    if not check_channel(uid):
        mk=get_channels_keyboard(uid)
        if mk:
            bot.reply_to(m,
                "<blockquote>⚠️ <b>ᴊᴏɪɴ ʀᴇꞯᴜɪʀᴇᴅ!</b>\n\nBot use karne ke liye sabhi channels join karo!\n"
                "Join ke baad ✅ <b>I Joined — Verify</b> dabao\n\n⚡ @Felix_modz1</blockquote>",
                reply_markup=mk,parse_mode='HTML')
            return
    if user[5]<=0 and not is_admin(uid) and user[7]!=1:
        txt,mk=no_credits_msg(uid); bot.reply_to(m,txt,reply_markup=mk,parse_mode='HTML'); return
    # SharedUser object ya numeric ID — safely extract numeric ID only
    _raw_obj = m.users_shared.user_ids[0]
    if hasattr(_raw_obj, 'user_id'):
        raw = _raw_obj.user_id  # SharedUser object se numeric ID nikalo
    elif isinstance(_raw_obj, dict):
        raw = _raw_obj.get('user_id') or _raw_obj.get('id')
    else:
        raw = _raw_obj
    try: raw = int(raw)
    except:
        bot.send_message(uid,"<blockquote>❌ User ID detect nahi hua!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    ld=bot.send_message(uid,"<blockquote>" + pbar(5) + "\n⚡ ꜰᴇᴛᴄʜɪɴɢ ᴀʟʟ ᴅᴀᴛᴀ...</blockquote>",parse_mode='HTML')
    deduct_credit(uid)

    # Animate while fetching
    stop_sel=[False]
    def _sel_anim():
        for pct in [15,30,50,70,85]:
            if stop_sel[0]: break
            try: bot.edit_message_text(f"<blockquote>{pbar(pct)}\n⚡ ꜰᴇᴛᴄʜɪɴɢ ᴀʟʟ ᴅᴀᴛᴀ...</blockquote>",uid,ld.message_id,parse_mode='HTML')
            except: pass
            time.sleep(0.15)
    _sel_t=threading.Thread(target=_sel_anim,daemon=True); _sel_t.start()

    # api_full_user — all 3 sources: TG Bot API + userid API + username API (30s timeout)
    import concurrent.futures as _cfu_sel
    try:
        with _cfu_sel.ThreadPoolExecutor(max_workers=1) as _ex_sel:
            _fut_sel = _ex_sel.submit(api_full_user, str(raw))
            res = _fut_sel.result(timeout=45)
    except Exception: res = None
    stop_sel[0]=True; _sel_t.join(timeout=1)

    # PFP — media URL primary (always works), TG Bot API fallback
    pic = None
    if res:
        pic = res.get('profile_pic') or res.get('profile_picture')
    if not pic:
        pic = f"http://username-to-info-rwsw.onrender.com/media/{raw}.png"
    # TG Bot API se verify karo — agar valid hai toh override karo
    _tg_pic = _fetch_pfp_by_id(str(raw))
    if _tg_pic:
        pic = _tg_pic

    now=_now_ist()

    if res and res.get('success'):
        ud2=res.get('data',{}) or {}
        _un2_raw = ud2.get('username') or res.get('username') or res.get('target_username') or ''
        un2 = _un2_raw.replace('@','').strip() if isinstance(_un2_raw, str) else ''
        label=f"@{un2} | {raw}" if un2 else f"User ID: {raw}"
        _cr_left_su = get_credits(uid)
        txt,_=_fmt_tg_user(res,'👤','SELECTED USER',label,now,_cr_left_su)
        # No pfp — sirf text bhejo
        try: bot.edit_message_text(txt,uid,ld.message_id,parse_mode='HTML')
        except: bot.send_message(uid,txt,parse_mode='HTML')
        bot.send_message(uid,"<blockquote>⬇️ ᴍᴀɪɴ ᴍᴇɴᴜ</blockquote>",reply_markup=kb_p1(uid),parse_mode='HTML')
        c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                 (uid,'user_id',str(raw),datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
        log_search(uid,m.from_user.first_name or "User",m.from_user.username or "","SELECT USER",str(raw),None)
    else:
        # API fail — TG direct se jo bhi mila wo show karo
        if not is_admin(uid) and user[7]!=1: refund_credit(uid)
        tg_direct=_fetch_tg_user_direct(str(raw))
        fn=tg_direct.get('first_name','') or ''
        ln=tg_direct.get('last_name','') or ''
        un2=tg_direct.get('username','') or ''
        label=f"@{un2} | {raw}" if un2 else f"User ID: {raw}"
        minimal_res={
            'success': bool(fn or un2),
            'phone':'N/A','telegram_id':str(raw),'target_id':str(raw),
            'country':'—','country_code':'',
            'data':{
                'first_name':fn,'last_name':ln,'username':un2,
                'telegram_id':str(raw),'bio':tg_direct.get('bio','') or ''
            }
        }
        _cr_left_su2 = get_credits(uid)
        err,_=_fmt_tg_user(minimal_res,'👤','SELECTED USER',label,now,_cr_left_su2)
        try: bot.edit_message_text(err,uid,ld.message_id,parse_mode='HTML')
        except: bot.send_message(uid,err,parse_mode='HTML')
        bot.send_message(uid,"<blockquote>⬇️ ᴍᴀɪɴ ᴍᴇɴᴜ</blockquote>",reply_markup=kb_p1(uid),parse_mode='HTML')

@bot.channel_post_handler(func=lambda m: True)
def h_channel_post(m):
    """Channel posts — bot bilkul respond nahi karega"""
    return  # Silent — channels pe koi bhi kaam nahi

@bot.message_handler(func=lambda m: m.chat.type in ['group','supergroup','channel'])
def h_group(m):
    """Group: number/username auto-detect + /like /info /bomb /stopbomb /user commands"""
    if m.chat.type == 'channel': return  # Channel pe bilkul kaam nahi
    cid=m.chat.id; uid=m.from_user.id; txt=(m.text or "").strip()
    if not txt: return

    # ── Clone bot: Felix ke apne channels/groups pe silent rahe, baki sab group mein kaam kare ──
    if _IS_CLONE and _is_felix_chat(cid, m.chat.username if hasattr(m.chat,'username') else None):
        return

    add_group_to_db(cid,m.chat.title or "Unknown")

    fname=_html.escape(m.from_user.first_name or 'User'); uname=m.from_user.username or ""
    # ── Force join check — sab commands pe (except /start /wel /weloff /setrules) ──
    _fj_skip_cmds = ['/start','/wel','/weloff','/setrules']
    _is_skip = any(txt.startswith(cc) for cc in _fj_skip_cmds)
    _is_real_search = (
        bool(re.match(r'^[6-9]\d{9}$', txt)) or
        bool(re.match(r'^@[a-zA-Z0-9_.]{4,}$', txt)) or
        any(txt.startswith(x) for x in ['/bomb','/like','/info','/user','/insta','/spin','/freespin'])
    )
    if not _is_skip and _is_real_search and not is_admin(uid):
        _user_grp = get_user(uid)
        if not _user_grp: add_user(uid,uname,fname); _user_grp=get_user(uid)
        if not check_channel(uid):
            _mk_fj2 = get_channels_keyboard(uid)  # sirf unjoined channels ke buttons
            if _mk_fj2:
                try:
                    bot.reply_to(m,
                        "<blockquote>⚠️ <b>ᴊᴏɪɴ ʀᴇꞯᴜɪʀᴇᴅ!</b>\n\nBot use karne ke liye neeche ke channels join karo!\n"
                        "Join ke baad ✅ <b>I Joined — Verify</b> dabao.\n\n⚡ @Felix_modz1</blockquote>",
                        reply_markup=_mk_fj2, parse_mode='HTML')
                except: pass
            return

    # ── /freespin / /spin — group daily spin ──
    if txt.startswith('/freespin') or txt.startswith('/spin'):
        if check_blocked_and_reply(uid): return
        threading.Thread(target=_do_group_spin, args=(uid, fname, uname, cid), daemon=True).start()
        return

    # ── /bomb ──
    if txt.startswith('/bomb'):
        if not is_feature_enabled('bomber'):
            bot.reply_to(m,"<blockquote>━━━━━━━━━━━━━━━━━━\n⚙️ ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ\n━━━━━━━━━━━━━━━━━━\n🛠️ System maintenance\n⏳ ᴛʜᴏᴅɪ ᴅᴇʀ ᴍᴇɪɴ ᴡᴀᴩᴀꜱ ᴀᴀ ᴊᴀᴇɢᴀ!\n━━━━━━━━━━━━━━━━━━\n💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>",parse_mode='HTML'); return
        parts=txt.split(); num=re.sub(r'\D','',parts[1]) if len(parts)>1 else ''
        if len(num)==12 and num.startswith('91'): num=num[2:]
        if not re.match(r'^[6-9]\d{9}$',num):
            bot.reply_to(m,"<blockquote>💣 Usage: <code>/bomb 9876543210</code></blockquote>",parse_mode='HTML'); return
        if bomber_jobs.get(uid,{}).get('running',False):
            bot.reply_to(m,"<blockquote>💣 Already running! Use /stopbomb</blockquote>",parse_mode='HTML'); return
        if not is_admin(uid):
            _ucr_b = get_credits(uid)
            try: _ucr_b_int = int(_ucr_b) if _ucr_b != "∞" else 999
            except: _ucr_b_int = 0
            if _ucr_b_int <= 0:
                _nc_t,_nc_m=no_credits_msg(uid)
                try: bot.reply_to(m,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                except: bot.send_message(cid,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                return
        sm=bot.reply_to(m,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
        try: bot.send_chat_action(cid,'typing')
        except: pass
        _start_anim(cid,sm.message_id,'bomber')
        threading.Thread(target=run_bomber,args=(uid,cid,num,sm.message_id),daemon=True).start()
        return

    # ── /stopbomb ──
    if txt.startswith('/stopbomb'):
        if uid in bomber_jobs: bomber_jobs[uid]['running']=False
        bot.reply_to(m,"<blockquote>🔴 <b>Bomber stopped!</b></blockquote>",parse_mode='HTML'); return

    # ── /like <uid> ──
    if txt.startswith('/like'):
        if not is_feature_enabled('freefire_like'):
            bot.reply_to(m,"<blockquote>━━━━━━━━━━━━━━━━━━\n⚙️ ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ\n━━━━━━━━━━━━━━━━━━\n🛠️ System maintenance\n⏳ ᴛʜᴏᴅɪ ᴅᴇʀ ᴍᴇɪɴ ᴡᴀᴩᴀꜱ ᴀᴀ ᴊᴀᴇɢᴀ!\n━━━━━━━━━━━━━━━━━━\n💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>",parse_mode='HTML'); return
        parts=txt.split(); ff_uid=re.sub(r'\D','',parts[-1]) if len(parts)>1 else ''
        if len(ff_uid)<5:
            bot.reply_to(m,"<blockquote>❤️ Usage: <code>/like 2819649271</code></blockquote>",parse_mode='HTML'); return
        if not is_admin(uid) and int(get_credits(uid) if get_credits(uid)!='∞' else 999) <= 0:
            _nc_txt,_nc_mk=no_credits_msg(uid)
            try: bot.reply_to(m,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            except: bot.send_message(cid,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            return
        try: bot.send_chat_action(cid, 'playing')
        except: pass
        sm=bot.reply_to(m,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
        try: bot.send_chat_action(cid,'typing')
        except: pass
        threading.Thread(target=do_ff_like_send,args=(cid,sm.message_id,ff_uid,'ind',uid,fname),daemon=True).start()
        return

    # ── /info <uid> ──
    if txt.startswith('/info'):
        if not is_feature_enabled('freefire'):
            bot.reply_to(m,"<blockquote>━━━━━━━━━━━━━━━━━━\n⚙️ ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ\n━━━━━━━━━━━━━━━━━━\n🛠️ System maintenance\n⏳ ᴛʜᴏᴅɪ ᴅᴇʀ ᴍᴇɪɴ ᴡᴀᴩᴀꜱ ᴀᴀ ᴊᴀᴇɢᴀ!\n━━━━━━━━━━━━━━━━━━\n💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>",parse_mode='HTML'); return
        if is_group_muted(cid): return
        g=get_group(cid)
        if safe_g(g,6)==1 if g else False: return
        parts=txt.split(); ff_uid=re.sub(r'\D','',parts[-1]) if len(parts)>1 else ''
        if len(ff_uid)<5: return
        if not deduct_credit(uid, 1, cid):
            _nc_txt,_nc_mk=no_credits_msg(uid)
            try: bot.reply_to(m,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            except: bot.send_message(cid,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            return
        sm=bot.reply_to(m,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
        try: bot.send_chat_action(cid,'typing')
        except: pass
        _sf_gif=_start_anim(cid,sm.message_id,'freefire')
        res=api_ff(ff_uid)
        _sf_gif[0]=True; p1,p2=fmt_ff(res,ff_uid,fname)
        try: bot.edit_message_text(p1,cid,sm.message_id,parse_mode='HTML')
        except: bot.send_message(cid,p1,parse_mode='HTML')
        if p2: bot.send_message(cid,p2,parse_mode='HTML')
        if not (res and res.get('success')): refund_credit(uid, 1)
        return

    # ── /user <userid> ──
    if txt.startswith('/user'):
        if not is_feature_enabled('tgid'):
            bot.reply_to(m,"<blockquote>━━━━━━━━━━━━━━━━━━\n⚙️ ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ\n━━━━━━━━━━━━━━━━━━\n🛠️ System maintenance\n⏳ ᴛʜᴏᴅɪ ᴅᴇʀ ᴍᴇɪɴ ᴡᴀᴩᴀꜱ ᴀᴀ ᴊᴀᴇɢᴀ!\n━━━━━━━━━━━━━━━━━━\n💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>",parse_mode='HTML'); return
        if is_group_muted(cid): return
        g=get_group(cid)
        if g and safe_g(g,6)==1: return
        parts=txt.split(); qid=re.sub(r'\D','',parts[-1]) if len(parts)>1 else ''
        if len(qid)<5: return
        if not deduct_credit(uid, 1, cid):
            _nc_txt,_nc_mk=no_credits_msg(uid)
            try: bot.reply_to(m,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            except: bot.send_message(cid,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            return
        sm=bot.reply_to(m,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
        try: bot.send_chat_action(cid,'typing')
        except: pass
        _sf_gus=_start_anim(cid,sm.message_id,'tgid')
        res=api_userid(qid)
        _sf_gus[0]=True
        _cr_left_gus = get_credits(uid)
        rtxt,_=_fmt_tg_user(res,'🆔','TG ID INFO',f"ID: {qid}",_now_ist(),_cr_left_gus)
        try: bot.edit_message_text(rtxt,cid,sm.message_id,parse_mode='HTML')
        except: bot.send_message(cid,rtxt,parse_mode='HTML')
        if not (res and res.get('success')): refund_credit(uid, 1)
        return

    # ── /insta <username> ──
    if txt.startswith('/insta'):
        if not is_feature_enabled('instagram'):
            bot.reply_to(m,"<blockquote>━━━━━━━━━━━━━━━━━━\n⚙️ ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ\n━━━━━━━━━━━━━━━━━━\n🛠️ System maintenance\n⏳ ᴛʜᴏᴅɪ ᴅᴇʀ ᴍᴇɪɴ ᴡᴀᴩᴀꜱ ᴀᴀ ᴊᴀᴇɢᴀ!\n━━━━━━━━━━━━━━━━━━\n💀 ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1</blockquote>",parse_mode='HTML'); return
        if is_group_muted(cid): return
        g=get_group(cid)
        if g and safe_g(g,6)==1: return
        parts=txt.split(); insta_id=parts[-1].replace('@','').strip() if len(parts)>1 else ''
        if not insta_id or not re.match(r'^[a-zA-Z0-9_.]{1,30}$',insta_id):
            bot.reply_to(m,"<blockquote>📸 Usage: <code>/insta username</code>\nExample: <code>/insta felixbhai</code></blockquote>",parse_mode='HTML'); return
        if not deduct_credit(uid, 1, cid):
            _nc_txt,_nc_mk=no_credits_msg(uid)
            try: bot.reply_to(m,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            except: bot.send_message(cid,_nc_txt,reply_markup=_nc_mk,parse_mode='HTML')
            return
        sm=bot.reply_to(m,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
        try: bot.send_chat_action(cid,'typing')
        except: pass
        _sf_gin=_start_anim(cid,sm.message_id,'instagram')
        res=api_instagram(insta_id)
        _sf_gin[0]=True; rtxt,pic=fmt_instagram(res,insta_id,fname)
        send_with_pfp(cid,rtxt,pic,sm.message_id)
        if res and res.get('success'): log_search(uid,fname,uname,"INSTAGRAM(GRP)",insta_id,pic)
        else: refund_credit(uid, 1)
        return

    st_data=user_state.get(uid)
    if isinstance(st_data,dict) and st_data.get('group') and st_data.get('chat_id')==cid and st_data.get('requester')==uid:
        st=st_data.get('state')
        ask_id=st_data.get('ask_id')
        try: bot.delete_message(cid,ask_id)
        except: pass
        user_state.pop(uid,None)
        if st==S_NUM:
            num=re.sub(r'\D','',txt)
            if len(num)==12 and num.startswith('91'): num=num[2:]
            if not re.match(r'^[6-9]\d{9}$',num):
                bot.reply_to(m,"<blockquote>❌ Invalid! 10-digit Indian number bhejo.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            if not deduct_credit(uid, 1, cid):
                _nc_t,_nc_m=no_credits_msg(uid)
                try: bot.reply_to(m,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                except: bot.send_message(cid,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                return
            ld=bot.reply_to(m,"<blockquote>" + pbar(0) + "\n⚡ ꜰᴇᴛᴄʜɪɴɢ...</blockquote>",parse_mode='HTML')
            res=api_number(num); rtxt=fmt_number(res,num,fname)
            try: bot.edit_message_text(rtxt,cid,ld.message_id,parse_mode='HTML')
            except: bot.send_message(cid,rtxt,parse_mode='HTML')
            if res and res.get('success'): log_search(uid,fname,uname,"NUMBER(GRP)",num)
            else: refund_credit(uid, 1)
            return
        elif st==S_USER:
            un=txt if txt.startswith('@') else '@'+txt
            if not deduct_credit(uid, 1, cid):
                _nc_t,_nc_m=no_credits_msg(uid)
                try: bot.reply_to(m,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                except: bot.send_message(cid,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                return
            ld=bot.reply_to(m,"<blockquote>" + pbar(0) + "\n⚡ ꜰᴇᴛᴄʜɪɴɢ...</blockquote>",parse_mode='HTML')
            import concurrent.futures as _cfu_gbs
            try:
                with _cfu_gbs.ThreadPoolExecutor(max_workers=1) as _ex_gbs:
                    res = _ex_gbs.submit(api_full_user, un).result(timeout=30)
            except Exception: res = None
            now=_now_ist()
            _cr_left_gbs = get_credits(uid) if not is_admin(uid) else '∞'
            rtxt,_=_fmt_tg_user_short(res,un,now,_cr_left_gbs)
            try: bot.edit_message_text(rtxt,cid,ld.message_id,parse_mode='HTML')
            except: bot.send_message(cid,rtxt,parse_mode='HTML')
            if res and res.get('success'): log_search(uid,fname,uname,"USERNAME(GRP)",un,None)
            else: refund_credit(uid, 1)
            return
        elif st==S_INSTA:
            insta_id=txt.replace('@','').strip()
            if not re.match(r'^[a-zA-Z0-9_.]{1,30}$',insta_id):
                bot.reply_to(m,"<blockquote>❌ Invalid Instagram username!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            if not deduct_credit(uid, 1, cid):
                _nc_t,_nc_m=no_credits_msg(uid)
                try: bot.reply_to(m,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                except: bot.send_message(cid,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                return
            ld=bot.reply_to(m,"<blockquote>" + pbar(0) + "\n⚡ ꜰᴇᴛᴄʜɪɴɢ ɪɴꜱᴛᴀ...</blockquote>",parse_mode='HTML')
            res=api_instagram(insta_id); rtxt,pic=fmt_instagram(res,insta_id,fname)
            send_with_pfp(cid,rtxt,pic,ld.message_id)
            if res and res.get('success'): log_search(uid,fname,uname,"INSTAGRAM(GRP)",insta_id,pic)
            else: refund_credit(uid, 1)
            return
        elif st==S_BOMB:
            num=re.sub(r'\D','',txt)
            if len(num)==12 and num.startswith('91'): num=num[2:]
            if not re.match(r'^[6-9]\d{9}$',num):
                bot.reply_to(m,"<blockquote>❌ Invalid! 10-digit number bhejo.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            if bomber_jobs.get(uid,{}).get('running',False):
                bot.reply_to(m,"<blockquote>💣 Already running! /stopbomb use karo.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            if not deduct_credit(uid, 1, cid):
                _nc_t,_nc_m=no_credits_msg(uid)
                try: bot.reply_to(m,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                except: bot.send_message(cid,_nc_t,reply_markup=_nc_m,parse_mode='HTML')
                return
            sm=bot.reply_to(m,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
            try: bot.send_chat_action(cid,'typing')
            except: pass
            _start_anim(cid,sm.message_id,'bomber')
            threading.Thread(target=run_bomber,args=(uid,cid,num,sm.message_id),daemon=True).start()
            return

        # Ignore ALL other commands

    # ── /balance / /bal / /credits / /mybalance ──
    if txt.startswith('/balance') or txt.startswith('/bal') or txt.startswith('/credits') or txt.startswith('/mybalance'):
        # Group mein reply pe target user ka balance dikhao
        _target_uid = uid
        _target_fname = fname
        _target_uname = uname
        _is_self = True
        if m.reply_to_message and m.reply_to_message.from_user:
            _ru = m.reply_to_message.from_user
            if not _ru.is_bot:
                _target_uid = _ru.id
                _target_fname = _ru.first_name or "User"
                _target_uname = _ru.username or ""
                _is_self = (_target_uid == uid)
                add_user(_target_uid, _target_uname, _target_fname)

        add_user(uid, uname, fname)
        _cr = get_credits(_target_uid)
        _ref_cnt = get_referral_count(_target_uid)
        try:
            _coins_t = c.execute("SELECT coins FROM users WHERE user_id=?", (_target_uid,)).fetchone()
            _coins_t = _coins_t[0] if _coins_t else 0
        except: _coins_t = 0
        try:
            _row=c.execute("SELECT is_premium,premium_until FROM users WHERE user_id=?",(_target_uid,)).fetchone()
            if _row and _row[0]==1 and _row[1]:
                try:
                    _exp=datetime.strptime(_row[1],"%Y-%m-%d %H:%M:%S")
                    _pt="💎 Premium" if _exp>datetime.now() else "👤 Free User"
                    _pe=f"Expires: <code>{_row[1]}</code>" if _exp>datetime.now() else "Expired"
                except: _pt="💎 Premium"; _pe=""
            elif _row and _row[0]==1: _pt="💎 Premium"; _pe=""
            else: _pt="👤 Free User"; _pe=""
        except: _pt="👤 Free User"; _pe=""
        if is_admin(_target_uid): _pt="👑 Bot Owner"; _pe=""
        try:
            _urow=c.execute("SELECT join_date FROM users WHERE user_id=?",(_target_uid,)).fetchone()
            _jd=_urow[0] if _urow and _urow[0] else "—"
        except: _jd="—"
        _uname_bal=f"@{_target_uname}" if _target_uname else "No Username"
        _title = "MY BALANCE" if _is_self else "USER BALANCE"
        def _pb(eid,fb): return f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"
        _L = _pb('5465629669829128119','➿')*10
        _SM = _pb('6147464060305676048','😎')
        _CK = _pb('6147565374289220368','✅')
        _bal_txt=(
            f"<blockquote>{_L}\n"
            f"{_pb('6179428482527793899','💰')} <b>{_title}</b>\n"
            f"{_L}\n\n"
            f"{_pb('5373012449597335010','👤')} ɴᴀᴍᴇ    : <a href='tg://user?id={_target_uid}'><b>{_target_fname}</b></a>\n"
            f"{_pb('5888781182249738113','🆔')} ɪᴅ      : <code>{_target_uid}</code>\n"
            f"{_pb('5470135030393090150','📛')} ᴜꜱᴇʀɴᴀᴍᴇ: {_uname_bal}\n\n"
            f"{_L}\n"
            f"⚡ ᴄʀᴇᴅɪᴛꜱ  : <b>{_cr}</b>\n"
            f"🎫 ʀᴇꜰᴇʀ ᴘᴛꜱ: <b>{_coins_t}</b>\n"
            f"{_pb('5465300082628763143','👥')} ʀᴇꜰᴇʀʀᴀʟꜱ: <b>{_ref_cnt}</b>\n\n"
            f"🏅 ꜱᴛᴀᴛᴜꜱ   : {_pt}\n"
            +(f"{_pb('6242308461598610637','📅')} {_pe}\n" if _pe else "")
            +f"{_pb('6242308461598610637','📅')} ᴊᴏɪɴᴇᴅ   : {_jd}\n"
            f"{_L}\n"
            f"📤 Refer karo → +2 Credits + 1 Point 🎫\n"
            f"{_SM} @Felix_Bhai {_CK}\n{_L}</blockquote>"
        )
        try: bot.reply_to(m,_bal_txt,parse_mode='HTML')
        except: bot.send_message(cid,_bal_txt,parse_mode='HTML')
        return

    # ── /wel on | /wel off (group handler) ──
    if txt.startswith('/wel'):
        try:
            _cm=bot.get_chat_member(cid,uid)
            if _cm.status not in ['administrator','creator'] and not is_admin(uid):
                bot.reply_to(m,"<blockquote>❌ Sirf <b>group admin</b> use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        except: return
        _parts=txt.split(); _arg=_parts[1].lower() if len(_parts)>1 else ''
        if _arg=='off':
            set_group_welcome_on(cid,0)
            bot.reply_to(m,f"<blockquote>🔕 <b>Welcome Message OFF</b>\n\n❌ Ab naye members ka welcome nahi aayega.\n\n👑 Admin: <a href='tg://user?id={uid}'>{fname}</a>\n💡 ON: <code>/wel on</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        elif _arg=='on':
            set_group_welcome_on(cid,1)
            bot.reply_to(m,f"<blockquote>🔔 <b>Welcome Message ON</b>\n\n✅ Ab naye members ka welcome aayega! 🎉\n\n👑 Admin: <a href='tg://user?id={uid}'>{fname}</a>\n💡 OFF: <code>/wel off</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        else:
            try:
                _wr=c.execute("SELECT bye_on,welcome_on FROM group_welcome_settings WHERE group_id=?",(cid,)).fetchone()
                _ws="🟢 ON" if (_wr and _wr[1]==1) else "🔴 OFF"
                _bs="🟢 ON" if (_wr and _wr[0]==1) else "🔴 OFF"
            except: _ws="🔴 OFF"; _bs="🔴 OFF"
            bot.reply_to(m,f"<blockquote>ℹ️ <b>Group Settings</b>\n\n👋 Welcome: {_ws}\n🚪 Leave  : {_bs}\n\n• <code>/wel on</code> / <code>/wel off</code>\n• <code>/leave on</code> / <code>/leave off</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        return

    # ── /leave on | /leave off (group handler) ──
    if txt.startswith('/leave'):
        try:
            _cm=bot.get_chat_member(cid,uid)
            if _cm.status not in ['administrator','creator'] and not is_admin(uid):
                bot.reply_to(m,"<blockquote>❌ Sirf <b>group admin</b> use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        except: return
        _parts=txt.split(); _arg=_parts[1].lower() if len(_parts)>1 else ''
        if _arg=='off':
            set_group_bye_on(cid,0)
            bot.reply_to(m,f"<blockquote>🔕 <b>Leave Message OFF</b>\n\n❌ Ab koi member chhodega toh msg nahi aayega.\n\n👑 Admin: <a href='tg://user?id={uid}'>{fname}</a>\n💡 ON: <code>/leave on</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        elif _arg=='on':
            set_group_bye_on(cid,1)
            bot.reply_to(m,f"<blockquote>🔔 <b>Leave Message ON</b>\n\n✅ Ab jab koi member chhodega toh msg aayega! 👋\n\n👑 Admin: <a href='tg://user?id={uid}'>{fname}</a>\n💡 OFF: <code>/leave off</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        else:
            try:
                _wr=c.execute("SELECT bye_on,welcome_on FROM group_welcome_settings WHERE group_id=?",(cid,)).fetchone()
                _ws="🟢 ON" if (_wr and _wr[1]==1) else "🔴 OFF"
                _bs="🟢 ON" if (_wr and _wr[0]==1) else "🔴 OFF"
            except: _ws="🔴 OFF"; _bs="🔴 OFF"
            bot.reply_to(m,f"<blockquote>ℹ️ <b>Group Settings</b>\n\n👋 Welcome: {_ws}\n🚪 Leave  : {_bs}\n\n• <code>/wel on</code> / <code>/wel off</code>\n• <code>/leave on</code> / <code>/leave off</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        return

    if txt.startswith('/'): 
        # ── /help group mein — commands list dikhao ──
        if txt.startswith('/help') or txt.startswith('/start'):
            if check_blocked_and_reply(uid): return
            _cr_g = get_credits(uid)
            _cr_disp = "∞" if is_admin(uid) else str(_cr_g)
            try: _ref_g = f"https://t.me/{_get_bot_username()}?start={uid}"
            except: _ref_g = f"https://t.me/bot?start={uid}"
            _sep = "━━━━━━━━━━━━━━━━━━"
            _help_txt = (
                f"<blockquote>{_sep}\n"
                f"🤖 <b>ɢʀᴏᴜᴩ ᴄᴏᴍᴍᴀɴᴅꜱ</b>\n"
                f"{_sep}\n\n"
                f"💰 ᴄʀᴇᴅɪᴛꜱ: <b>{_cr_disp}</b>  |  1 ꜱᴇᴀʀᴄʜ = 1 ᴄʀᴇᴅɪᴛ\n\n"
                f"{_sep}\n"
                f"📱 <b>SEARCH</b>\n"
                f"• 9876543210 — Number Info\n"
                f"• @username — Username Info\n\n"
                f"🎮 <b>FREE FIRE</b>\n"
                f"• /info [uid] — FF Player Info\n"
                f"• /like [uid] — FF Likes\n\n"
                f"🆔 <b>TG INFO</b>\n"
                f"• /user [userid] — TG User Info\n\n"
                f"📸 <b>INSTAGRAM</b>\n"
                f"• /insta [username] — Insta Info\n\n"
                f"💣 <b>BOMBER</b>\n"
                f"• /bomb [number] — Start Bomber\n"
                f"• /stopbomb — Stop Bomber\n\n"
                f"🎁 <b>DAILY SPIN</b>\n"
                f"• /spin — Daily Spin (credits kamao)\n\n"
                f"{_sep}\n"
                f"📤 ᴄʀᴇᴅɪᴛꜱ ᴋʜᴀᴛᴀᴍ? Refer karo:\n"
                f"{_ref_g}\n"
                f"{_sep}\n"
                f"⚡ @Felix_modz1</blockquote>"
            )
            try: bot.reply_to(m, _help_txt, parse_mode='HTML')
            except: bot.send_message(cid, _help_txt, parse_mode='HTML')
            return
        return  # baaki unknown commands ignore
    # Ignore button text
    if txt.startswith('⚙️') or txt.startswith('🔙') or txt.startswith('➡️') or txt.startswith('⬅️'): return

    # Number: sirf exact 10-digit Indian number (6-9 se shuru)
    n_match=re.match(r'^[6-9]\d{9}$',txt)
    # Username: sirf @ se shuru hona chahiye (random words pe trigger nahi hoga)
    u_match=re.match(r'^@[a-zA-Z0-9_.]{4,}$',txt) if txt.startswith('@') else None
    if not n_match and not u_match: return  # SILENT

    if is_identifier_blocked(str(uid)): return  # SILENT
    if is_group_muted(cid): return  # MUTED = fully silent

    # Group blocked check
    grp_g=get_group(cid)
    if grp_g and safe_g(grp_g,6)==1: return  # group blocked

    # ── USER personal credit check ──
    user_g=get_user(uid)
    if not user_g: add_user(uid,uname,fname); user_g=get_user(uid)

    # Group unlimited check — agar group unlimited ON hai to credit check skip karo
    _grp_unl = grp_g and safe_g(grp_g,5)==1

    if not is_admin(uid) and not _grp_unl:
        _ucr=get_credits(uid)
        try: _ucr_int = int(_ucr) if _ucr != "∞" else 999
        except: _ucr_int = 0
        if _ucr_int <= 0:
            _nocr_txt, _nocr_mk = no_credits_msg(uid)
            try: bot.reply_to(m, _nocr_txt, reply_markup=_nocr_mk, parse_mode='HTML')
            except: bot.send_message(cid, _nocr_txt, reply_markup=_nocr_mk, parse_mode='HTML')
            return

    if not deduct_credit(uid,1,cid): return
    ld=bot.reply_to(m,"<blockquote>" + pbar(0) + "\n⚡ ꜰᴇᴛᴄʜɪɴɢ...</blockquote>",parse_mode='HTML')

    try:
        if n_match:
            num=txt
            if is_identifier_blocked(num):
                try: bot.edit_message_text("<blockquote>🚫 Blocked.</blockquote>",cid,ld.message_id,parse_mode='HTML')
                except: pass
                refund_credit(uid,1); return
            # Protected user check
            if not is_admin(uid) and is_user_protected(num):
                try: bot.edit_message_text(
                    f"<blockquote>{_CL_TOP()}\n│  🔒 <b>ᴩʀᴏᴛᴇᴄᴛᴇᴅ ᴜꜱᴇʀ</b>\n{_CL_BOT()}\n\n"
                    f"🛡️ <b>This user is protected by Admin.</b>\n❌ Iska data access nahi kar sakte!\n\n{_F}\n⚡ @Felix_modz1</blockquote>",
                    cid,ld.message_id,parse_mode='HTML')
                except: pass
                refund_credit(uid, 1); return
            res=api_number(num); rtxt=fmt_number(res,num,"")
            # Credits left append karo
            _cr_left_num = get_credits(uid)
            if not is_admin(uid):
                def _pe_n(eid,fb): return f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"
                _cr_line_n = f"\n{_pe_n('5379600444098093058','🪙')} ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ:- <b>{_cr_left_num}</b>"
                rtxt = rtxt.replace("</blockquote>", _cr_line_n + "\n</blockquote>", 1)
            try: bot.edit_message_text(rtxt,cid,ld.message_id,parse_mode='HTML')
            except: bot.send_message(cid,rtxt,parse_mode='HTML')
            if res and res.get('success'):
                c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                         (uid,'number',num,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
                log_search(uid,fname,uname,"NUMBER(GROUP)",num)
            else: refund_credit(uid,1)

        elif u_match:
            un=txt
            if is_identifier_blocked(un.replace('@','').lower()):
                try: bot.edit_message_text("<blockquote>🚫 Blocked.</blockquote>",cid,ld.message_id,parse_mode='HTML')
                except: pass
                refund_credit(uid,1); return
            # Protected user check
            _un_clean = un.lstrip('@').lower()
            if not is_admin(uid) and (is_user_protected(un) or is_user_protected(_un_clean)):
                try: bot.edit_message_text(
                    f"<blockquote>{_CL_TOP()}\n│  🔒 <b>ᴩʀᴏᴛᴇᴄᴛᴇᴅ ᴜꜱᴇʀ</b>\n{_CL_BOT()}\n\n"
                    f"🛡️ <b>This user is protected by Admin.</b>\n❌ Iska data access nahi kar sakte!\n\n{_F}\n⚡ @Felix_modz1</blockquote>",
                    cid,ld.message_id,parse_mode='HTML')
                except: pass
                refund_credit(uid,1); return
            # api_full_user — same as username/tgid/select user buttons (max data)
            import concurrent.futures as _cfu_grp
            try:
                with _cfu_grp.ThreadPoolExecutor(max_workers=1) as _ex_grp:
                    _fut_grp = _ex_grp.submit(api_full_user, un)
                    res = _fut_grp.result(timeout=30)
            except Exception: res = None
            now=_now_ist()
            _cr_left_grp = get_credits(uid)
            rtxt,pic=_fmt_tg_user_short(res,un,now,_cr_left_grp)
            # No pfp in group
            try: bot.edit_message_text(rtxt,cid,ld.message_id,parse_mode='HTML')
            except: bot.send_message(cid,rtxt,parse_mode='HTML')
            if res and res.get('success'):
                c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                         (uid,'username',un,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
                log_search(uid,fname,uname,"USERNAME(GROUP)",un,pic)
            else: refund_credit(uid,1)
    except Exception as e:
        try: bot.edit_message_text(f"<blockquote>❌ Error: {_safe_err(e)}</blockquote>",cid,ld.message_id,parse_mode='HTML')
        except: pass

def do_search(uid,stype,query,m):
    _user_cache.pop(uid, None)
    user=get_user(uid)
    if not user: add_user(uid,m.from_user.username or "",m.from_user.first_name or "User"); user=get_user(uid)
    if not check_channel(uid):
        mk=get_channels_keyboard(uid)
        if mk:
            bot.reply_to(m,
                "<blockquote>⚠️ <b>ᴊᴏɪɴ ʀᴇꞯᴜɪʀᴇᴅ!</b>\n\n"
                "Bot use karne ke liye sabhi channels join karo!\n"
                "Join ke baad ✅ <b>I Joined — Verify</b> dabao\n\n"
                "⚡ @Felix_modz1</blockquote>",
                reply_markup=mk,parse_mode='HTML')
        user_state[uid]=S_NONE; return
    if not is_admin(uid) and user[7]!=1 and user[5]<=0:
        txt,mk=no_credits_msg(uid); bot.reply_to(m,txt,reply_markup=mk,parse_mode='HTML')
        user_state[uid]=S_NONE; return
    # ── Protected user check — agar query protected hai to block karo ──
    if not is_admin(uid):
        _q_clean = str(query).lower().strip().lstrip('@')
        if is_user_protected(query) or is_user_protected(_q_clean):
            bot.reply_to(m,
                f"<blockquote>{_CL_TOP()}\n"
                f"│  🔒 <b>ᴩʀᴏᴛᴇᴄᴛᴇᴅ ᴜꜱᴇʀ</b>\n"
                f"{_CL_BOT()}\n\n"
                f"🛡️ <b>This user is protected by Admin.</b>\n\n"
                f"❌ Iska data access nahi kar sakte!\n\n"
                f"{_F}\n⚡ @Felix_modz1</blockquote>",
                parse_mode='HTML')
            user_state[uid]=S_NONE; return
    # Cost per search type
    _cost = 1  # sab searches 1 credit
    if not deduct_credit(uid, _cost):
        bot.reply_to(m,"<blockquote>❌ No credits!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        user_state[uid]=S_NONE; return

    sm=bot.reply_to(m,"<blockquote>" + pbar(0) + "\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')

    # stype → label key map
    _stype_key_map = {
        S_NUM: 'number', S_USER: 'username', S_TID: 'tgid',
        S_ADH: 'aadhar', S_INSTA: 'instagram', S_FF: 'freefire',
        S_FFL: 'like', S_VEH: 'vehicle', S_BOMB: 'bomber',
    }
    try: bot.send_chat_action(m.chat.id, 'typing')
    except: pass
    stop_anim = _start_anim(m.chat.id, sm.message_id, _stype_key_map.get(stype, 'number'))

    res=None; rtxt=None; pic=None; nm=m.from_user.first_name or "User"; extra_ff=None

    if stype==S_NUM:
        res=api_number(query)
        rtxt,total_pages,_,has_next=fmt_number_page(res,query,1)
        _num_cache[uid]={'data':res,'num':query,'page':1,'total':total_pages}
    elif stype in (S_USER, S_TID):
        # Unified: teeno buttons (username, tgid, select user) same max data — 30s timeout
        import concurrent.futures as _cfu_ds
        try:
            with _cfu_ds.ThreadPoolExecutor(max_workers=1) as _ex_ds:
                _fut_ds = _ex_ds.submit(api_full_user, query)
                res = _fut_ds.result(timeout=30)
        except Exception: res = None
        now=_now_ist()
        icon='🔍' if stype==S_USER else '🆔'
        title_t='USERNAME INFO' if stype==S_USER else 'TG ID INFO'
        label=query if stype==S_USER else f"ID: {query}"
        # credits after deduction
        _cr_left = get_credits(uid) if not is_admin(uid) else '∞'
        if stype==S_USER:
            rtxt,_=_fmt_tg_user_short(res,label,now,_cr_left)
        else:
            rtxt,_=_fmt_tg_user(res,icon,title_t,label,now,_cr_left)
        pic=None  # no pfp for username/tgid
    elif stype==S_ADH:
        res=api_aadhar(query); rtxt=fmt_aadhar(res,query,nm)
    elif stype==S_INSTA:
        res=api_instagram(query); rtxt,pic=fmt_instagram(res,query,nm)
    elif stype==S_FF:
        res=api_ff(query); p1ff,p2ff=fmt_ff(res,query,nm); rtxt=p1ff; extra_ff=p2ff
    elif stype==S_FFL:
        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=2) as _ex:
            _f1=_ex.submit(api_ff,query)
            _f2=_ex.submit(api_ff_like,query)
            ff_info=_f1.result(); res=_f2.result()
        lb=ff_info.get('liked',0) if ff_info else 0
        rtxt=fmt_ff_like(res,query,nm,lb)
    elif stype==S_VEH:
        res=api_vehicle(query); rtxt=fmt_vehicle(res,query,nm)
    elif stype==S_BOMB:
        stop_anim[0]=True
        if bomber_jobs.get(uid,{}).get('running',False):
            try: bot.edit_message_text("<blockquote>💣 Already running! STOP first.</blockquote>",uid,sm.message_id,parse_mode='HTML')
            except: pass
            user_state[uid]=S_NONE; return
        threading.Thread(target=run_bomber,args=(uid,uid,query,sm.message_id),daemon=True).start()
        user_state[uid]=S_NONE; return

    stop_anim[0]=True

    # ── Credits left inject — sab result texts mein (except S_USER/S_TID jo already have it) ──
    if rtxt and stype not in (S_USER, S_TID):
        try:
            _cr_now = get_credits(uid) if not is_admin(uid) else '∞'
            _te_cr = f"<tg-emoji emoji-id='5379600444098093058'>🪙</tg-emoji>"
            _cr_inject = f"\n{_te_cr} ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ:- <b>{_cr_now}</b>"
            # blockquote ke closing tag se pehle insert karo
            if rtxt.endswith("</blockquote>"):
                rtxt = rtxt[:-len("</blockquote>")] + _cr_inject + "</blockquote>"
        except: pass

    ok=res and (res.get('success') or res.get('blocked'))
    if not ok and not is_admin(uid) and user[7]!=1: refund_credit(uid, _cost)

    # Number info — send with pagination buttons if multiple pages
    if stype==S_NUM:
        cache=_num_cache.get(uid,{})
        total_pages=cache.get('total',1)
        has_next=total_pages>1
        if rtxt:
            if has_next:
                mk_pg=InlineKeyboardMarkup()
                mk_pg.add(_IKB("➡️ NEXT PAGE",style="primary",callback_data=f"numpage_{uid}_2"))
                try: bot.edit_message_text(rtxt,m.chat.id,sm.message_id,reply_markup=mk_pg,parse_mode='HTML')
                except: bot.send_message(m.chat.id,rtxt,reply_markup=mk_pg,parse_mode='HTML')
            else:
                try: bot.edit_message_text(rtxt,m.chat.id,sm.message_id,parse_mode='HTML')
                except: bot.send_message(m.chat.id,rtxt,parse_mode='HTML')
    elif stype in (S_USER, S_TID):
        # No pfp — sirf text
        if rtxt:
            try: bot.edit_message_text(rtxt,m.chat.id,sm.message_id,parse_mode='HTML')
            except: bot.send_message(m.chat.id,rtxt,parse_mode='HTML')
    elif rtxt:
        send_with_pfp(m.chat.id,rtxt,pic,sm.message_id)

    if ok and res:
        c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                 (uid,stype,query,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
        log_search(uid,m.from_user.first_name or "User",m.from_user.username or "",stype,query,pic)
    if stype==S_FF and ok and extra_ff and isinstance(extra_ff,str) and extra_ff.startswith('http'):
        try: bot.send_photo(m.chat.id,extra_ff,caption="🎮 <b>Profile Avatar</b>",parse_mode='HTML')
        except: pass
    elif stype==S_FF and ok and extra_ff:
        try: bot.send_message(m.chat.id,extra_ff,parse_mode='HTML')
        except: pass
    user_state[uid]=S_NONE

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/') and m.chat.type=='private')
def h_private(m):
    uid=m.from_user.id; txt=m.text.strip(); st=user_state.get(uid,S_NONE)
    # Clone bot OFF hone par sirf toggle button allow karo
    if _IS_CLONE and not _CLONE_BOT_ACTIVE and uid not in [OWNER_ID, _MAIN_OWNER]:
        if txt not in ["🟢 ᴏɴ ᴍʏ ʙᴏᴛ","🔴 ᴏꜰꜰ ᴍʏ ʙᴏᴛ"]:
            bot.reply_to(m,"<blockquote>🔴 <b>Bot abhi offline hai.</b>\nOwner se contact karo.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if check_blocked_and_reply(uid): return

    # ── AUTO-DETECT when state is NONE: number → number info, @username → username info ──
    if st == S_NONE:
        # 10-digit Indian number auto-detect
        if re.match(r'^[6-9]\d{9}$', txt) and is_feature_enabled('number'):
            user=get_user(uid)
            if not user: add_user(uid,m.from_user.username or "",m.from_user.first_name or "User")
            do_search(uid, S_NUM, txt, m)
            return
        # @username auto-detect
        if re.match(r'^@[a-zA-Z0-9_.]{5,}$', txt) and is_feature_enabled('username'):
            user=get_user(uid)
            if not user: add_user(uid,m.from_user.username or "",m.from_user.first_name or "User")
            do_search(uid, S_USER, txt, m)
            return

    if st==S_NUM:
        if re.match(r'^[6-9]\d{9}$',txt): do_search(uid,S_NUM,txt,m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid! 10-digit number</blockquote>",parse_mode='HTML')
    elif st==S_USER:
        if txt.startswith('@') and len(txt)>1: do_search(uid,S_USER,txt,m)
        elif re.sub(r'\D','',txt) and len(re.sub(r'\D','',txt))>=5:
            do_search(uid,S_TID,re.sub(r'\D','',txt),m)  # username state pe bhi ID accept karo
        else: bot.reply_to(m,"<blockquote>❌ @username ya numeric TG ID bhejo!</blockquote>",parse_mode='HTML')
    elif st==S_TID:
        cl=re.sub(r'\D','',txt)
        if len(cl)>=5: do_search(uid,S_TID,cl,m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid User ID!</blockquote>",parse_mode='HTML')
    elif st==S_ADH:
        cl=re.sub(r'\D','',txt)
        if len(cl)==12: do_search(uid,S_ADH,cl,m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid! 12-digit Aadhar</blockquote>",parse_mode='HTML')
    elif st==S_INSTA:
        cl=txt.replace('@','').strip()
        if re.match(r'^[a-zA-Z0-9_.]{1,30}$',cl): do_search(uid,S_INSTA,cl,m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid Instagram!</blockquote>",parse_mode='HTML')
    elif st==S_FF:
        cl=re.sub(r'\D','',txt)
        if len(cl)>=5: do_search(uid,S_FF,cl,m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid FF UID!</blockquote>",parse_mode='HTML')
    elif st==S_FFL or st==S_FF_LIKE_UID:
        cl=re.sub(r'\D','',txt)
        if len(cl)>=5:
            user_state[uid]=S_NONE
            if not _like_check_ratelimit(uid) and not is_admin(uid):
                bot.reply_to(m,f"<blockquote>⚠️ Daily limit reached! Max {LIKE_DAILY_MAX}/day\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            can,rem,cinfo=_like_check_cooldown(uid,cl)
            if not can and not is_admin(uid):
                h=int(rem//3600); mn=int((rem%3600)//60)
                bot.reply_to(m,(f"<blockquote>{_F}\n⏰ <b>UID ON COOLDOWN</b>\n{_F}\n\n"
                                f"❌ This UID is on cooldown!\n\n"
                                f"🆔 UID: <code>{cl}</code>\n"
                                f"⏱️ Remaining: {h}h {mn}m\n\n"
                                f"💡 Different UID like karo — no cooldown!\n\n"
                                f"{_F}\n⚡ @Felix_modz1\n{_F}</blockquote>"),parse_mode='HTML'); return
            sm=bot.reply_to(m,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
            try: bot.send_chat_action(m.chat.id,'typing')
            except: pass
            threading.Thread(target=do_ff_like_send,args=(uid,sm.message_id,cl,"ind",uid,m.from_user.first_name or "User"),daemon=True).start()
        else: bot.reply_to(m,"<blockquote>❌ Invalid FF UID!</blockquote>",parse_mode='HTML')
    elif st==S_VEH:
        cl=txt.upper().replace(' ','')
        if re.match(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$',cl): do_search(uid,S_VEH,cl,m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid RC! Example: MH12AB1234</blockquote>",parse_mode='HTML')
    elif st==S_BOMB:
        n=re.sub(r'\D','',txt)
        if len(n)==12 and n.startswith('91'): n=n[2:]
        if re.match(r'^[6-9]\d{9}$',n): do_search(uid,S_BOMB,n,m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid number!\n⚠️ Sirf apne number!</blockquote>",parse_mode='HTML')
    elif st==S_REDEEM:
        ok,msg=redeem_code_fn(uid,txt)
        bot.send_message(uid,f"<blockquote>{msg}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        user_state[uid]=S_NONE
    elif st==S_PREM_REDEEM:
        ok,pmsg=redeem_premium_code_fn(uid,txt)
        bot.send_message(uid,f"<blockquote>{pmsg}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        user_state[uid]=S_NONE
    elif st==S_CLONE:
        if re.match(r'^\d{8,12}:[A-Za-z0-9_-]{35,}$',txt.strip()): do_clone(uid,txt.strip(),m)
        else: bot.reply_to(m,"<blockquote>❌ Invalid token!</blockquote>",parse_mode='HTML')

def do_clone(uid,token,m):
    try:
        r=requests.get(f"https://api.telegram.org/bot{token}/getMe",timeout=10)
        if r.status_code!=200 or not r.json().get('ok'):
            bot.reply_to(m,"<blockquote>❌ Invalid token!</blockquote>",parse_mode='HTML')
            user_state[uid]=S_NONE; return
        bi=r.json().get('result',{})
        c.execute("INSERT OR REPLACE INTO bot_clones(user_id,bot_token,created_date,is_active) VALUES(?,?,?,1)",
                  (uid,token,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        bot.reply_to(m,(f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
                        f"   ✅ ʙᴏᴛ ᴄʟᴏɴᴇ ʀᴇQᴜᴇꜱᴛ ꜱᴇɴᴛ! 📨\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"🤖 Bot: @{bi.get('username','Unknown')}\n\n"
                        f"⏳ Owner review karega, jald deploy hoga!\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ @Felix_modz1</blockquote>"),parse_mode='HTML')
        # Owner ko request bhejo with accept button
        user=get_user(uid)
        uname_disp=f"@{user[1]}" if user and user[1] else f"ID:{uid}"
        fname_disp=user[2] if user and user[2] else "User"
        bot_username=bi.get('username','?')
        bot_name=bi.get('first_name','Bot')
        mk=InlineKeyboardMarkup()
        mk.row(_IKB("✅ ACCEPT & DEPLOY",style="success",callback_data=f"clone_accept_{uid}"),
               _IKB("❌ REJECT",style="danger",callback_data=f"clone_reject_{uid}"))
        try: bot.send_message(OWNER_ID,
            f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
            f"   🤖 ɴᴇᴡ ᴄʟᴏɴᴇ ʀᴇQᴜᴇꜱᴛ! 🆕\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>Requester:</b>\n"
            f"   • Name: <a href='tg://user?id={uid}'>{fname_disp}</a>\n"
            f"   • Username: {uname_disp}\n"
            f"   • ID: <code>{uid}</code>\n\n"
            f"🤖 <b>Bot Details:</b>\n"
            f"   • Bot Name: <b>{bot_name}</b>\n"
            f"   • Bot Username: @{bot_username}\n"
            f"   • Token: <code>{token}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Accept karo to deploy hoga!</blockquote>",
            reply_markup=mk,parse_mode='HTML')
        except: pass
    except Exception as e: bot.reply_to(m,f"<blockquote>❌ Error: {_safe_err(e)}</blockquote>",parse_mode='HTML')
    user_state[uid]=S_NONE

@bot.callback_query_handler(func=lambda call: call.data.startswith('clone_accept_') or call.data.startswith('clone_reject_'))
def h_clone_decision(call):
    if call.from_user.id!=OWNER_ID:
        bot.answer_callback_query(call.id,"❌ Sirf owner!"); return
    parts=call.data.split('_')
    action=parts[1]; target_uid=int(parts[2])
    if action=='accept':
        bot.answer_callback_query(call.id,"✅ Deploying...")
        c.execute("UPDATE users SET credits=credits+20 WHERE user_id=?",(target_uid,)); conn.commit()
        clone_row=c.execute("SELECT bot_token FROM bot_clones WHERE user_id=? AND is_active=1",(target_uid,)).fetchone()
        if clone_row:
            clone_token=clone_row[0]
            threading.Thread(target=_run_clone_bot,args=(clone_token,target_uid),daemon=True).start()
            # ── Original bot clone ko apne channels/groups pe admin banata hai ──
            threading.Thread(target=_promote_clone_on_orig_chats,args=(clone_token,),daemon=True).start()
        try:
            bot.send_message(target_uid,
                f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
                f"   🎉 ʙᴏᴛ ᴄʟᴏɴᴇ ᴀᴩᴩʀᴏᴠᴇᴅ! ✅\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 Tera bot deploy ho gaya!\n"
                f"💰 Tujhe <b>20 Bonus Credits</b> mile!\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass
        try: bot.edit_message_text(
            f"<blockquote>✅ <b>ACCEPTED!</b>\n👤 User: <code>{target_uid}</code>\n💰 20 bonus credits diye!\n🤖 Bot deploy hua!</blockquote>",
            call.message.chat.id,call.message.message_id,parse_mode='HTML')
        except: pass
    else:
        bot.answer_callback_query(call.id,"❌ Rejected")
        try:
            bot.send_message(target_uid,
                f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n"
                f"   ❌ ʙᴏᴛ ᴄʟᴏɴᴇ ʀᴇᴊᴇᴄᴛᴇᴅ\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚠️ Abhi deploy nahi ho sakta.\n"
                f"📩 Contact @Felix_modz1\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass
        try: bot.edit_message_text(
            f"<blockquote>❌ <b>REJECTED</b>\n👤 User: <code>{target_uid}</code></blockquote>",
            call.message.chat.id,call.message.message_id,parse_mode='HTML')
        except: pass

def _promote_clone_on_orig_chats(clone_token):
    """Original bot clone ko apne force-join channels + registered groups pe admin promote karta hai"""
    try:
        import telebot as _tb_promo
        _cb_promo=_tb_promo.TeleBot(clone_token)
        try: clone_bot_id=_cb_promo.get_me().id
        except: return
        # ── Force join channels pe promote ──
        fj_rows=c.execute("SELECT chat_id FROM force_join_channels WHERE is_active=1").fetchall()
        for (cid_str,) in fj_rows:
            try:
                cid_val=int(cid_str) if str(cid_str).lstrip('-').isdigit() else cid_str
                bot.promote_chat_member(
                    cid_val, clone_bot_id,
                    can_manage_chat=True,
                    can_post_messages=True,
                    can_invite_users=True,
                    can_restrict_members=False,
                    can_delete_messages=False,
                    can_pin_messages=False,
                    can_promote_members=False)
                time.sleep(0.5)
            except Exception as ep: print(f"[PROMO_CH] {cid_str}: {ep}")
        # ── Registered groups pe promote ──
        grp_rows=c.execute("SELECT group_id FROM groups WHERE is_blocked=0").fetchall()
        for (gid,) in grp_rows:
            try:
                bot.promote_chat_member(
                    gid, clone_bot_id,
                    can_manage_chat=True,
                    can_post_messages=False,
                    can_invite_users=True,
                    can_restrict_members=False,
                    can_delete_messages=False,
                    can_pin_messages=False,
                    can_promote_members=False)
                time.sleep(0.5)
            except Exception as ep: print(f"[PROMO_GRP] {gid}: {ep}")
    except Exception as e: print(f"[PROMOTE_CLONE] {_safe_err(e)}")

def _kill_old_clone(owner_uid, clone_dir=None):
    """Purani clone process kill karo agar chal rahi ho — restart ke liye"""
    import os, signal
    if clone_dir is None:
        clone_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clones')
    pid_file = os.path.join(clone_dir, f'clone_{owner_uid}.pid')
    killed = False
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as pf:
                old_pid = int(pf.read().strip())
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.kill(old_pid, sig)
                    killed = True
                    time.sleep(0.5)
                except (ProcessLookupError, OSError):
                    break
                except: pass
            try: os.remove(pid_file)
            except: pass
    except: pass
    return killed

def _delete_clone_files(owner_uid, clone_dir=None):
    """Clone .py aur .pid files delete karo — sirf remove ke waqt call karo"""
    import os
    if clone_dir is None:
        clone_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clones')
    for ext in ('.py', '.pid'):
        try:
            f = os.path.join(clone_dir, f'clone_{owner_uid}{ext}')
            if os.path.exists(f): os.remove(f)
        except: pass

def _run_clone_bot(clone_token, owner_uid):
    """Clone bot ko same code se run karo — alag DB, alag token, owner = clone requester.
    Original bot off/on hone par bhi clone auto-restart hota hai via _auto_restart_clones."""
    try:
        import subprocess, sys, os
        script_path = os.path.abspath(__file__)
        with open(script_path, 'r', encoding='utf-8') as f:
            src = f.read()

        # ── Token replace ──
        src = src.replace(f'BOT_TOKEN = "{BOT_TOKEN}"', f'BOT_TOKEN = "{clone_token}"', 1)

        # ── Owner replace ──
        src = src.replace(f'OWNER_ID = {OWNER_ID}', f'OWNER_ID = {owner_uid}', 1)

        # ── FREE_CREDITS replace — clone bhi 3 se shuru (same as original) ──
        src = src.replace(
            'FREE_CREDITS = 3         # Starting credits (new users ko sirf 3 milenge) - DO NOT CHANGE',
            'FREE_CREDITS = 3         # Starting credits (new users ko sirf 3 milenge) - DO NOT CHANGE',
            1)  # keep same — 3 credits for clone too

        # ── Force _IS_CLONE=True ──
        src = src.replace(
            '_IS_CLONE = (OWNER_ID != 8335023642)  # agar owner main owner nahi hai to ye clone hai',
            '_IS_CLONE = True  # ye clone hai',
            1)

        # ── Clone ka DB clones/ folder mein rakhna hai — alag DB ──
        clone_dir = os.path.join(os.path.dirname(script_path), 'clones')
        os.makedirs(clone_dir, exist_ok=True)

        # _DB_FILE override — clones/ folder mein alag file
        src = src.replace(
            '_DB_FILE = os.path.join(_SCRIPT_DIR, f"bot_{_BOT_ID}.db")',
            f'_DB_FILE = os.path.join(r"{clone_dir}", f"bot_{{_BOT_ID}}.db")',
            1)

        # ── Clone me _F separator — same as original ──
        # (No change — clone aur original same separator use karenge)

        # ── Clone me @Felix_modz1 footer preserve karo — same as original ──
        # (No replacement — clone bhi same footer dikhayega)

        clone_file = os.path.join(clone_dir, f'clone_{owner_uid}.py')

        # Purana process kill karo (file delete mat karo — replace karenge)
        _kill_old_clone(owner_uid, clone_dir)
        time.sleep(0.5)

        with open(clone_file, 'w', encoding='utf-8') as f:
            f.write(src)

        proc = subprocess.Popen(
            [sys.executable, clone_file],
            stdout=open(os.path.join(clone_dir, f'clone_{owner_uid}.log'), 'a'),
            stderr=subprocess.STDOUT,
            cwd=clone_dir)

        # PID save karo taaki restart pe kill kar sake
        pid_file = os.path.join(clone_dir, f'clone_{owner_uid}.pid')
        with open(pid_file, 'w') as pf:
            pf.write(str(proc.pid))

        print(f"[CLONE] Started uid={owner_uid} token={clone_token[:20]}... PID={proc.pid}")

    except Exception as e:
        print(f"[CLONE] Error: {_safe_err(e)}")
        try: bot.send_message(OWNER_ID, f"<blockquote>❌ Clone start error:\n{_safe_err(e)}</blockquote>", parse_mode='HTML')
        except: pass

@bot.message_handler(commands=['resetgroupcredits'])
def cmd_reset_group_credits(msg):
    """Sabhi groups ki credits 0 karo — sirf owner. Ab sirf user personal credits kaam karengi."""
    uid = msg.from_user.id
    if uid != OWNER_ID:
        bot.reply_to(msg, "<blockquote>❌ Sirf owner use kar sakta hai!</blockquote>", parse_mode='HTML')
        return
    try:
        c.execute("UPDATE groups SET credits=0, unlimited=0")
        conn.commit()
        _group_cache.clear()
        count = c.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
        bot.reply_to(msg,
            f"<blockquote>✅ <b>Group Credits Reset Done!</b>\n\n"
            f"🔢 Total Groups: <code>{count}</code>\n"
            f"💰 All Group Credits → <b>0</b>\n"
            f"∞ Unlimited → <b>OFF</b>\n\n"
            f"Ab sirf user ke personal credits kaam karenge.\n"
            f"⚡ @Felix_modz1</blockquote>",
            parse_mode='HTML')
    except Exception as e:
        bot.reply_to(msg, f"<blockquote>❌ Error: {_safe_err(e)}</blockquote>", parse_mode='HTML')

@bot.message_handler(commands=['add'])
def cmd_add_credits(msg):
    """/add <amount> — reply pe user ko credits do (sirf owner/admin)"""
    uid = msg.from_user.id
    if not is_admin(uid):
        bot.reply_to(msg, "<blockquote>❌ Sirf admin use kar sakta hai!\n⚡ @Felix_Bhai</blockquote>", parse_mode='HTML')
        return
    # Reply check
    if not msg.reply_to_message:
        bot.reply_to(msg,
            "<blockquote>⚠️ <b>Usage:</b>\n"
            "Kisi user ke message ko reply karke:\n"
            "<code>/add 50</code>\n\n"
            "Usse 50 credits mil jayenge!\n⚡ @Felix_Bhai</blockquote>",
            parse_mode='HTML')
        return
    # Amount parse karo
    parts = msg.text.strip().split()
    if len(parts) < 2 or not parts[1].lstrip('-').isdigit():
        bot.reply_to(msg, "<blockquote>❌ Format: <code>/add 50</code>\n⚡ @Felix_Bhai</blockquote>", parse_mode='HTML')
        return
    amount = int(parts[1])
    if amount == 0:
        bot.reply_to(msg, "<blockquote>❌ Amount 0 nahi ho sakta!\n⚡ @Felix_Bhai</blockquote>", parse_mode='HTML')
        return
    # Target user
    target = msg.reply_to_message.from_user
    tid = target.id
    tfname = _html.escape(target.first_name or "User")
    tuname = target.username or ""
    # Ensure user in DB
    if not get_user(tid):
        add_user(tid, tuname, tfname)
    # Credits update karo
    c.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (amount, tid))
    conn.commit()
    _user_cache.pop(tid, None)
    new_cr = get_credits(tid)
    # Premium emoji footer
    def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
    _L = _te("5465629669829128119") * 10
    _SM = _te("6147464060305676048")
    _CK = _te("6147565374289220368")
    _COIN = _te("5379600444098093058")
    _PLUS = _te("6179105681375760937")
    action = "➕ ᴀᴅᴅᴇᴅ" if amount > 0 else "➖ ʀᴇᴍᴏᴠᴇᴅ"
    bot.reply_to(msg, (
        f"<blockquote>{_L}\n"
        f"{_PLUS} <b>ᴄʀᴇᴅɪᴛꜱ ᴜᴘᴅᴀᴛᴇᴅ!</b>\n"
        f"{_L}\n\n"
        f"{_te('5373012449597335010')} ᴜꜱᴇʀ: <a href='tg://user?id={tid}'><b>{tfname}</b></a>\n"
        f"{_te('5888781182249738113')} ɪᴅ: <code>{tid}</code>\n\n"
        f"{_COIN} {action}: <b>{abs(amount)}</b>\n"
        f"{_COIN} ɴᴇᴡ ᴛᴏᴛᴀʟ: <b>{new_cr}</b>\n\n"
        f"{_L}\n"
        f"{_SM} @Felix_Bhai {_CK}\n"
        f"{_L}</blockquote>"
    ), parse_mode='HTML')
    # Target user ko bhi notify karo
    try:
        bot.send_message(tid, (
            f"<blockquote>{_L}\n"
            f"{_PLUS} <b>ᴄʀᴇᴅɪᴛꜱ ᴍɪʟᴇ!</b>\n"
            f"{_L}\n\n"
            f"{_COIN} +<b>{abs(amount)}</b> credits add ho gaye!\n"
            f"{_COIN} ᴛᴏᴛᴀʟ: <b>{new_cr}</b>\n\n"
            f"{_L}\n"
            f"{_SM} @Felix_Bhai {_CK}\n"
            f"{_L}</blockquote>"
        ), parse_mode='HTML')
    except: pass
    # Log
    try:
        try: bn = _get_bot_username()
        except: bn = "felix_bot"
        log_token_activity(tid, tfname, tuname, amount, new_cr if isinstance(new_cr,int) else 0, f"Admin /add by {uid}", bn)
    except: pass

@bot.message_handler(commands=['spin'])
def cmd_spin(msg):
    """/spin - Daily spin — group + private dono mein kaam karta hai"""
    uid=msg.from_user.id
    fname=_html.escape(msg.from_user.first_name or 'User')
    uname=msg.from_user.username or ""
    cid=msg.chat.id
    chat_type=msg.chat.type
    if _clone_group_guard(msg): return
    if check_blocked_and_reply(uid): return
    user=get_user(uid)
    if not user: add_user(uid, uname, fname)
    if not check_channel(uid):
        mk_fj=get_channels_keyboard(uid)
        if mk_fj:
            bot.reply_to(msg,
                "<blockquote>⚠️ <b>ᴊᴏɪɴ ʀᴇꞯᴜɪʀᴇᴅ!</b>\n\nSpin ke liye sabhi channels join karo!\n"
                "⚡ @Felix_modz1</blockquote>",
                reply_markup=mk_fj, parse_mode='HTML')
            return
    if chat_type in ['group','supergroup']:
        # Group: dice group mein jayega
        threading.Thread(target=_do_group_spin, args=(uid, fname, uname, cid), daemon=True).start()
    else:
        # DM/Private: seedha handle karo
        if is_admin(uid) or can_claim_daily(uid):
            dm = bot.send_dice(uid, emoji=_get_spin_emoji())
            time.sleep(5)
            cw = {1:1, 2:1, 3:2, 4:3, 5:4, 6:5}.get(dm.dice.value, 1)
            c.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (cw, uid))
            if not is_admin(uid):
                c.execute("INSERT OR IGNORE INTO daily_claims VALUES(?,?)",
                          (uid, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            _user_cache.pop(uid, None)
            user_obj = get_user(uid)
            tot = user_obj[5] if user_obj else cw
            _SS = _SEP(); _SE = _SEP()
            # Vplink — get more credits button
            _spin_ref = f"https://t.me/{_get_bot_username()}?start={uid}"
            _spin_vp_url = _spin_ref
            _spin_mk = InlineKeyboardMarkup()
            _spin_mk.add(_IKB("🎁 Get More +5 Credits", style="success", icon_custom_emoji_id="5361552478416986392", url=_spin_vp_url))
            bot.send_message(uid,
                f"<blockquote>{_SS}\n🎁 <b>ᴅᴀɪʟʏ ꜱᴘɪɴ</b>\n{_SS}\n"
                f"🎉 Won: <code>+{cw}</code> credits!\n"
                f"💰 Total: <code>{tot}</code>\n"
                f"{_SE}\n"
                f"💰 ᴄʀᴇᴅɪᴛꜱ ʟᴇꜰᴛ: <b>{tot}</b>\n"
                f"⚡ @Felix_modz1</blockquote>",
                reply_markup=_spin_mk, parse_mode='HTML')
            try: bn = _get_bot_username()
            except: bn = "felix_bot"
            log_token_activity(uid, fname, uname, cw, tot, "Daily Spin", bn)
        else:
            bot.reply_to(msg,
                "<blockquote>❌ <b>Already claimed today!</b>\n"
                "⏳ Kal wapis aao!\n"
                "⚡ @Felix_modz1</blockquote>",
                parse_mode='HTML')

@bot.message_handler(commands=['insta'])
def cmd_insta(msg):
    """/insta <id> - Instagram info (works in group + private)"""
    uid=msg.from_user.id; chat_type=msg.chat.type
    if _clone_group_guard(msg): return
    if not is_feature_enabled('instagram'): return
    # In group: check group permissions
    if chat_type in ['group','supergroup']:
        g=get_group(msg.chat.id)
        if not g or safe_g(g,6)==1: return  # blocked
        if safe_g(g,8)==1: return  # muted
    if check_blocked_and_reply(uid): return
    parts=msg.text.split()
    if len(parts)<2:
        bot.reply_to(msg,(
            "<blockquote>"+_CL_TOP()+"\n"
            "│  📸 <b>INSTAGRAM INFO</b>\n"
            +_CL_BOT()+"\n\n"
            "📌 Usage: <code>/insta username</code>\n"
            "Example: <code>/insta cristiano</code>\n\n"
            "⚡ @Felix_modz1</blockquote>"
        ),parse_mode='HTML'); return
    raw=' '.join(parts[1:]).strip()
    # Support: @user, <user>, user, @yrrr_afridi etc
    insta_id=raw.replace('@','').replace('<','').replace('>','').strip()
    if not re.match(r'^[a-zA-Z0-9_.]{1,30}$',insta_id):
        bot.reply_to(msg,"<blockquote>❌ Invalid Instagram username!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user=get_user(uid)
    if not user: add_user(uid,msg.from_user.username or "",msg.from_user.first_name or "User"); user=get_user(uid)
    # Group ya private — hamesha user personal credit ghata (no group credit system)
    if chat_type in ['group','supergroup']:
        if is_group_muted(msg.chat.id): return
        g2=get_group(msg.chat.id)
        if g2 and safe_g(g2,6)==1: return  # group blocked
    if not deduct_credit(uid):
        txt2,mk=no_credits_msg(uid); bot.reply_to(msg,txt2,reply_markup=mk,parse_mode='HTML'); return
    sm=bot.reply_to(msg,"<blockquote>"+pbar(0)+"\nꜱᴛᴀʀᴛɪɴɢ...</blockquote>",parse_mode='HTML')
    try: bot.send_chat_action(msg.chat.id,'typing')
    except: pass
    _sf_ins=_start_anim(msg.chat.id,sm.message_id,'instagram')
    _sf_ins[0]=True
    res=api_instagram(insta_id)
    rtxt,pic=fmt_instagram(res,insta_id,msg.from_user.first_name or "User")
    if not (res and res.get('success')) and not is_admin(uid): refund_credit(uid)
    send_with_pfp(msg.chat.id,rtxt,pic,sm.message_id)
    if res and res.get('success'):
        c.execute("INSERT INTO search_history(user_id,search_type,query,search_date,result) VALUES(?,?,?,?,?)",
                 (uid,S_INSTA,insta_id,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),json.dumps(res))); conn.commit()
        log_search(uid,msg.from_user.first_name or "User",msg.from_user.username or "","INSTAGRAM",insta_id,pic)

@bot.message_handler(commands=['wel','welcomeon','weloff','welcomeoff','onwelcome','offwelcome'])
def cmd_wel_toggle(msg):
    if msg.chat.type not in ['group','supergroup']:
        bot.reply_to(msg,"<blockquote>⚠️ Ye command sirf group mein kaam karta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if _clone_group_guard(msg): return
    uid=msg.from_user.id
    try:
        cm=bot.get_chat_member(msg.chat.id,uid)
        if cm.status not in ['administrator','creator'] and not is_admin(uid):
            bot.reply_to(msg,"<blockquote>❌ Sirf group admin ya bot owner use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    except: return

    cmd=msg.text.split()[0].lower().lstrip('/')
    parts=msg.text.strip().split()
    arg=parts[1].lower() if len(parts)>1 else ''

    # Determine ON or OFF
    _wel_L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"*10
    _wel_CK = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    _wel_SM = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _wel_BELL = "<tg-emoji emoji-id='5430351082980836609'>🔔</tg-emoji>"
    _wel_MUTE = "<tg-emoji emoji-id='5447420334186936822'>🔕</tg-emoji>"
    try:
        if cmd in ('weloff','welcomeoff','offwelcome') or arg=='off':
            set_group_welcome_on(msg.chat.id, 0)
            bot.reply_to(msg,f"<blockquote>{_wel_L}\n{_wel_MUTE} <b>Welcome OFF</b>\n{_wel_L}\n\n❌ Ab naye members ka welcome message nahi aayega.\n\n💡 ON karne ke liye: <code>/onwelcome</code>\n\n{_wel_L}\n{_wel_SM} @Felix_Bhai {_wel_CK}\n{_wel_L}</blockquote>",parse_mode='HTML')
        elif cmd in ('welcomeon','onwelcome') or arg=='on':
            set_group_welcome_on(msg.chat.id, 1)
            bot.reply_to(msg,f"<blockquote>{_wel_L}\n{_wel_BELL} <b>Welcome ON</b>\n{_wel_L}\n\n✅ Ab naye members ka welcome message aayega! 🎉\n\n💡 OFF karne ke liye: <code>/offwelcome</code>\n\n{_wel_L}\n{_wel_SM} @Felix_Bhai {_wel_CK}\n{_wel_L}</blockquote>",parse_mode='HTML')
        else:
            # /wel bina arg — current status dikhao
            _cur_state = c.execute("SELECT welcome_on FROM group_welcome_settings WHERE group_id=?",(msg.chat.id,)).fetchone()
            _is_on = _cur_state[0] if _cur_state else 1
            _status_txt = f"{_wel_BELL} <b>Welcome abhi ON hai</b>" if _is_on else f"{_wel_MUTE} <b>Welcome abhi OFF hai</b>"
            bot.reply_to(msg,f"<blockquote>{_wel_L}\n{_status_txt}\n{_wel_L}\n\n💡 ON: <code>/wel on</code>\n💡 OFF: <code>/wel off</code>\n\n{_wel_L}\n{_wel_SM} @Felix_Bhai {_wel_CK}\n{_wel_L}</blockquote>",parse_mode='HTML')
    except Exception as _we: 
        print(f"[WEL_TOGGLE] {_we}")
        try: bot.reply_to(msg,"<blockquote>❌ Error: Welcome toggle fail hua. Bot ko group admin banao!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass

@bot.message_handler(commands=['stopwelcome'])
def cmd_stop_welcome(msg):
    """Owner + group admin: /stopwelcome — welcome band karo"""
    if msg.chat.type not in ['group','supergroup']:
        bot.reply_to(msg,"<blockquote>⚠️ Ye command sirf group mein kaam karta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if _clone_group_guard(msg): return
    uid=msg.from_user.id
    try:
        cm=bot.get_chat_member(msg.chat.id,uid)
        if cm.status not in ['administrator','creator'] and not is_admin(uid):
            bot.reply_to(msg,"<blockquote>❌ Sirf group admin ya bot owner use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    except: return
    set_group_welcome_on(msg.chat.id, 0)
    _sw_L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"*10
    _sw_CK = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    _sw_SM = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _sw_MUTE = "<tg-emoji emoji-id='5447420334186936822'>🔕</tg-emoji>"
    bot.reply_to(msg,f"<blockquote>{_sw_L}\n{_sw_MUTE} <b>Welcome OFF</b>\n{_sw_L}\n\n❌ Ab naye members ka welcome message nahi aayega.\n\n💡 Dobara ON karne ke liye:\n<code>/startwelcome</code>\n\n{_sw_L}\n{_sw_SM} @Felix_Bhai {_sw_CK}\n{_sw_L}</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['startwelcome'])
def cmd_start_welcome(msg):
    """Owner + group admin: /startwelcome — welcome ON karo"""
    if msg.chat.type not in ['group','supergroup']:
        bot.reply_to(msg,"<blockquote>⚠️ Ye command sirf group mein kaam karta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if _clone_group_guard(msg): return
    uid=msg.from_user.id
    try:
        cm=bot.get_chat_member(msg.chat.id,uid)
        if cm.status not in ['administrator','creator'] and not is_admin(uid):
            bot.reply_to(msg,"<blockquote>❌ Sirf group admin ya bot owner use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    except: return
    set_group_welcome_on(msg.chat.id, 1)
    _stw_L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"*10
    _stw_CK = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    _stw_SM = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _stw_BELL = "<tg-emoji emoji-id='5430351082980836609'>🔔</tg-emoji>"
    bot.reply_to(msg,f"<blockquote>{_stw_L}\n{_stw_BELL} <b>Welcome ON</b>\n{_stw_L}\n\n✅ Ab naye members ka welcome message aayega! 🎉\n\n💡 Band karne ke liye:\n<code>/stopwelcome</code>\n\n{_stw_L}\n{_stw_SM} @Felix_Bhai {_stw_CK}\n{_stw_L}</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['offbye'])
def cmd_off_bye(msg):
    """Owner + group admin: /offbye — goodbye msg OFF karo"""
    if msg.chat.type not in ['group','supergroup']:
        bot.reply_to(msg,"<blockquote>⚠️ Ye command sirf group mein kaam karta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if _clone_group_guard(msg): return
    uid=msg.from_user.id
    try:
        cm=bot.get_chat_member(msg.chat.id,uid)
        if cm.status not in ['administrator','creator'] and not is_admin(uid):
            bot.reply_to(msg,"<blockquote>❌ Sirf group admin ya bot owner use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    except: return
    set_group_bye_on(msg.chat.id, 0)
    _ob_L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"*10
    _ob_CK = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    _ob_SM = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _ob_MUTE = "<tg-emoji emoji-id='5447420334186936822'>🔕</tg-emoji>"
    bot.reply_to(msg,f"<blockquote>{_ob_L}\n{_ob_MUTE} <b>Goodbye OFF</b>\n{_ob_L}\n\n❌ Ab group se jane wale members ka goodbye message nahi aayega.\n\n💡 Dobara ON karne ke liye:\n<code>/onbye</code>\n\n{_ob_L}\n{_ob_SM} @Felix_Bhai {_ob_CK}\n{_ob_L}</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['onbye'])
def cmd_on_bye(msg):
    """Owner + group admin: /onbye — goodbye msg ON karo"""
    if msg.chat.type not in ['group','supergroup']:
        bot.reply_to(msg,"<blockquote>⚠️ Ye command sirf group mein kaam karta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if _clone_group_guard(msg): return
    uid=msg.from_user.id
    try:
        cm=bot.get_chat_member(msg.chat.id,uid)
        if cm.status not in ['administrator','creator'] and not is_admin(uid):
            bot.reply_to(msg,"<blockquote>❌ Sirf group admin ya bot owner use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    except: return
    set_group_bye_on(msg.chat.id, 1)
    _nb_L = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"*10
    _nb_CK = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    _nb_SM = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _nb_BELL = "<tg-emoji emoji-id='5430351082980836609'>🔔</tg-emoji>"
    bot.reply_to(msg,f"<blockquote>{_nb_L}\n{_nb_BELL} <b>Goodbye ON</b>\n{_nb_L}\n\n✅ Ab group se jane wale members ka goodbye message aayega! 👋\n\n💡 Band karne ke liye:\n<code>/offbye</code>\n\n{_nb_L}\n{_nb_SM} @Felix_Bhai {_nb_CK}\n{_nb_L}</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['leaved'])
def cmd_leaved_toggle(msg):
    """Group admin: /leaved on | /leaved off — bye/leave message toggle"""
    if msg.chat.type not in ['group','supergroup']:
        bot.reply_to(msg,"<blockquote>⚠️ Ye command sirf group mein kaam karta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    if _clone_group_guard(msg): return
    uid=msg.from_user.id
    try:
        cm=bot.get_chat_member(msg.chat.id,uid)
        if cm.status not in ['administrator','creator'] and not is_admin(uid):
            bot.reply_to(msg,"<blockquote>❌ Sirf group admin ya bot owner use kar sakta hai!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    except: return
    parts=msg.text.strip().split()
    arg=parts[1].lower() if len(parts)>1 else ''
    fname=msg.from_user.first_name or ''
    _L    = "<tg-emoji emoji-id='5465629669829128119'>➿</tg-emoji>"*10
    _CK   = "<tg-emoji emoji-id='6147565374289220368'>✅</tg-emoji>"
    _SM   = "<tg-emoji emoji-id='6147464060305676048'>😎</tg-emoji>"
    _BELL = "<tg-emoji emoji-id='5430351082980836609'>🔔</tg-emoji>"
    _MUTE = "<tg-emoji emoji-id='5447420334186936822'>🔕</tg-emoji>"
    try:
        if arg=='off':
            set_group_bye_on(msg.chat.id, 0)
            bot.reply_to(msg,
                f"<blockquote>{_L}\n{_MUTE} <b>Leave Message OFF</b>\n{_L}\n\n"
                f"❌ Ab koi member chhodega toh msg nahi aayega.\n\n"
                f"👑 Admin: <a href='tg://user?id={uid}'>{fname}</a>\n"
                f"💡 ON: <code>/leaved on</code>\n\n"
                f"{_L}\n{_SM} @Felix_Bhai {_CK}\n{_L}</blockquote>",
                parse_mode='HTML')
        elif arg=='on':
            set_group_bye_on(msg.chat.id, 1)
            bot.reply_to(msg,
                f"<blockquote>{_L}\n{_BELL} <b>Leave Message ON</b>\n{_L}\n\n"
                f"✅ Ab jab koi member chhodega toh msg aayega! 👋\n\n"
                f"👑 Admin: <a href='tg://user?id={uid}'>{fname}</a>\n"
                f"💡 OFF: <code>/leaved off</code>\n\n"
                f"{_L}\n{_SM} @Felix_Bhai {_CK}\n{_L}</blockquote>",
                parse_mode='HTML')
        else:
            # Bina arg — current status dikhao
            _wr=c.execute("SELECT bye_on,welcome_on FROM group_welcome_settings WHERE group_id=?",(msg.chat.id,)).fetchone()
            _ws="🟢 ON" if (_wr and _wr[1]==1) else "🔴 OFF"
            _bs="🟢 ON" if (_wr and _wr[0]==1) else "🔴 OFF"
            bot.reply_to(msg,
                f"<blockquote>{_L}\nℹ️ <b>Group Settings</b>\n{_L}\n\n"
                f"👋 Welcome : {_ws}\n🚪 Leave   : {_bs}\n\n"
                f"• <code>/leaved on</code>  /  <code>/leaved off</code>\n"
                f"• <code>/wel on</code>     /  <code>/wel off</code>\n\n"
                f"{_L}\n{_SM} @Felix_Bhai {_CK}\n{_L}</blockquote>",
                parse_mode='HTML')
    except Exception as _le:
        print(f"[LEAVED_TOGGLE] {_le}")
        try: bot.reply_to(msg,"<blockquote>❌ Error. Bot ko group admin banao!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass

@bot.message_handler(commands=['setvideo'])
def cmd_setvideo(msg):
    """Owner: /setvideo - reply to a video to set as welcome video globally"""
    uid=msg.from_user.id
    if _clone_group_guard(msg): return
    if not is_admin(uid):
        try: bot.reply_to(msg,"<blockquote>❌ Owner only command!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        except: pass
        return
    # Check if replying to a video
    reply=msg.reply_to_message
    if not reply or not reply.video:
        bot.reply_to(msg,
            "<blockquote>🎥 <b>SET WELCOME VIDEO</b>\n\n"
            "Kisi video ko reply karke /setvideo bhejo!\n\n"
            "⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    try:
        file_id=reply.video.file_id
        file_info=bot.get_file(file_id)
        file_path_remote=file_info.file_path
        r=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path_remote}",timeout=60)
        if r.status_code==200:
            _SCRIPT_DIR2=os.path.dirname(os.path.abspath(__file__))
            local_path=os.path.join(_SCRIPT_DIR2,f"welcome_video_{_BOT_ID}.mp4")
            with open(local_path,'wb') as vf: vf.write(r.content)
            c.execute("UPDATE welcome_settings SET welcome_video=? WHERE id=1",(local_path,)); conn.commit()
            bot.reply_to(msg,
                "<blockquote>✅ <b>Welcome Video Set!</b>\n"
                "Ab naye members ke welcome mein ye video aayega!\n\n"
                "⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        else:
            bot.reply_to(msg,"<blockquote>❌ Video download failed!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
    except Exception as e:
        bot.reply_to(msg,f"<blockquote>❌ Error: {_safe_err(e)}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

@bot.message_handler(commands=['setrules'])
def cmd_setrules(msg):
    if msg.chat.type not in ['group','supergroup']: return
    if _clone_group_guard(msg): return
    uid=msg.from_user.id
    try:
        cm=bot.get_chat_member(msg.chat.id,uid)
        if cm.status not in ['administrator','creator'] and not is_admin(uid): return
    except: return
    parts=msg.text.split(None,1)
    if len(parts)<2:
        bot.reply_to(msg,"<blockquote>📋 Usage: <code>/setrules Rules text yahan likho</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    rules=parts[1].strip()
    set_group_rules(msg.chat.id, rules)
    bot.reply_to(msg,f"<blockquote>✅ <b>Group Rules Set!</b>\n\n📋 {rules}\n\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')

# ── Join dedup cache — prevents double welcome (new_chat_members + chat_member_handler) ──
_join_dedup = {}  # key = f"{cid}:{uid}", value = timestamp

def _join_already_welcomed(cid, uid):
    """Return True agar last 5 seconds mein already welcome bheja gaya ho"""
    key = f"{cid}:{uid}"
    now = time.time()
    last = _join_dedup.get(key, 0)
    if now - last < 5:
        return True
    _join_dedup[key] = now
    # Old entries clean karo
    for k in list(_join_dedup.keys()):
        if now - _join_dedup[k] > 30:
            _join_dedup.pop(k, None)
    return False

@bot.message_handler(content_types=['new_chat_members'])
def h_newmember(m):
    cid=m.chat.id; chat_title=m.chat.title or "Group"
    if _clone_group_guard(m): return
    for mb in m.new_chat_members:
        if mb.id==bot.get_me().id:
            add_group_to_db(cid,chat_title); continue
        # Dedup — agar 5s mein already welcomed to skip
        if _join_already_welcomed(cid, mb.id): continue
        try:
            wel_on, rules = get_group_welcome(cid)
            if not wel_on: continue
        except: continue
        try:
            fname     = mb.first_name or "User"
            lname     = mb.last_name or ""
            full_name = (fname+" "+lname).strip()
            uname     = "@"+mb.username if mb.username else "No Username"
            tgid      = mb.id
            now       = _now_ist()
            try: mem_count=bot.get_chat_members_count(cid)
            except: mem_count="?"
            # TG direct photo — use requests to be reliable
            pic=None
            try:
                # getUserProfilePhotos via requests (avoids pyTeleBot object issues)
                r_ph=requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos",
                    params={"user_id":tgid,"limit":1},timeout=8)
                if r_ph.status_code==200:
                    photos=r_ph.json().get('result',{}).get('photos',[])
                    if photos and photos[0]:
                        file_id=photos[0][-1].get('file_id','')
                        if file_id:
                            r_fi=requests.get(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                                params={"file_id":file_id},timeout=8)
                            if r_fi.status_code==200:
                                fpath=r_fi.json().get('result',{}).get('file_path','')
                                if fpath:
                                    pic=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}"
            except Exception as ep: print(f"[WELCOME_PFP] {ep}")
            # Rules section — default rules agar admin ne set nahi kiye
            if rules:
                rules_section="\n\n📜 ʀᴜʟᴇꜱ:\n"+rules
            else:
                rules_section=(
                    "\n\n📜 ʀᴜʟᴇꜱ:\n"
                    "🚫 ꜱᴘᴀᴍ | ᴀʙᴜꜱᴇ | ᴘʀᴏᴍᴏ\n"
                    "⚠️ ʀᴇꜱᴘᴇᴄᴛ ᴀʟʟ\n"
                    "💬 ꜱᴛᴀʏ ᴀᴄᴛɪᴠᴇ 😎"
                )
            def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
            # ── New premium emoji IDs (user-provided list) ──
            # Pos 1-12  : 5465144557568010803  → top row stars
            # Pos 13    : 6204223208468521357  → center title emoji
            # Pos 14-25 : 5465144557568010803  → top row stars
            # Pos 26    : 6151963850297051287  → hello start
            # Pos 27    : 5976721148736445255  → hello end (!!)
            # Pos 28    : 5976312108936076061  → welcome emoji
            # Pos 29-37 : 5465629669829128119  → MID border (9)
            # Pos 38    : 5039789890133296083  → Name
            # Pos 39    : 5041975203853239332  → Username
            # Pos 40    : 5041792560368977040  → ID
            # Pos 41    : 6201751179911766993  → Member
            # Pos 42-50 : 5465629669829128119  → MID border (9)
            # Pos 51-60 : 5465277838993141300  → BOT border (10)
            _E1 ="5465144557568010803"
            _E13="6204223208468521357"
            _E26="6151963850297051287"; _E27="5976721148736445255"; _E28="5976312108936076061"
            _E59="5465629669829128119"; _E54="5465277838993141300"
            _E38="5039789890133296083"; _E39="5041975203853239332"; _E40="5041792560368977040"
            _E41="6201751179911766993"
            _TOP_R1  = _te(_E1)*12
            _TOP_R2  = _te(_E1)*12
            _MID=_te(_E59)*9; _BOT_BORDER=_te(_E54)*10
            # uname display — agar username nahi to ID show karo
            uname_disp = uname if uname != "No Username" else f"<code>{tgid}</code>"

            # ── Group-specific welcome media ──
            gwimg,gwvid,gwvlist,gwstk=get_group_welcome_media(cid)

            # Custom welcome text override
            try:
                c.execute("SELECT welcome_text FROM group_welcome_settings WHERE group_id=?",(cid,))
                gwtext_row=c.fetchone(); gwtext=gwtext_row[0] if gwtext_row and gwtext_row[0] else None
            except: gwtext=None

            if _IS_CLONE:
                # Clone bot — sticker + video bhejo, text welcome nahi
                # Sticker pehle
                if gwstk:
                    try: bot.send_sticker(cid, gwstk)
                    except: pass
                # Video list > single video > image > pfp only (no text card)
                _cl_sent=False
                if gwvlist:
                    _fid=get_next_group_video(cid)
                    if _fid:
                        try: bot.send_video(cid,_fid,caption=f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!",parse_mode="HTML"); _cl_sent=True
                        except: pass
                if not _cl_sent and gwvid and os.path.exists(gwvid):
                    _cl_cached_fid = _group_video_fileid_cache.get(f"{cid}:{gwvid}")
                    if _cl_cached_fid:
                        try: bot.send_video(cid,_cl_cached_fid,caption=f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!",parse_mode="HTML"); _cl_sent=True
                        except: _group_video_fileid_cache.pop(f"{cid}:{gwvid}",None)
                    if not _cl_sent:
                        try:
                            with open(gwvid,'rb') as _f:
                                _cl_sv=bot.send_video(cid,_f,caption=f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!",parse_mode="HTML")
                                _cl_sent=True
                                if _cl_sv and _cl_sv.video:
                                    _group_video_fileid_cache[f"{cid}:{gwvid}"] = _cl_sv.video.file_id
                        except: pass
                if not _cl_sent and gwimg and os.path.exists(gwimg):
                    try:
                        with open(gwimg,'rb') as _f: bot.send_photo(cid,_f,caption=f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!",parse_mode="HTML"); _cl_sent=True
                    except: pass
                if not _cl_sent and pic:
                    try: bot.send_photo(cid,pic,caption=f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!",parse_mode="HTML"); _cl_sent=True
                    except: pass
                # Agar kuch bhi nahi bheja to bhi silent raho (clone pe text welcome nahi)
                try:
                    try: bn=_get_bot_username()
                    except: bn="felix_bot"
                    log_token_activity(tgid,full_name,mb.username or "",0,0,"Group Join",bn)
                except: pass
                continue

            # ── Original bot welcome — new premium emoji design ──
            # ── New emoji IDs (user list positions 1-28) ──
            _GW_1  = "4958830950604604428"  # pos 1  — welcome bird
            _GW_2  = "5465629669829128119"  # pos 2-11 — top row (10x)
            _GW_12 = "4956461073550017373"  # pos 12 — skull
            _GW_13 = "6147422674000808494"  # pos 13 — help
            _GW_14 = "4958636483075376288"  # pos 14 — rule1
            _GW_15 = "4958472587123360612"  # pos 15 — rule2
            _GW_16 = "4956525562483967357"  # pos 16 — rule3
            _GW_17 = "4958724224962265918"  # pos 17 — rules header
            _GW_18 = "5465629669829128119"  # pos 18-27 — bottom row (10x)
            _GW_28 = "4958900559139570572"  # pos 28 — developer

            _GW_LOOP10 = _te(_GW_2)*10

            if rules:
                _rules_lines = "\n".join(f"• {r.strip()}" for r in rules.splitlines() if r.strip())
            else:
                _rules_lines = (
                    f"{_te(_GW_14)} ɴᴏ ꜱᴘᴀᴍ\n"
                    f"{_te(_GW_15)} ɴᴏ ᴀʙᴜꜱᴇ\n"
                    f"{_te(_GW_16)} ʀᴇꜱᴩᴇᴄᴛ ᴇᴠᴇʀʏᴏɴᴇ"
                )

            welcome_txt=(
                f"<blockquote>"
                f"{_te(_GW_1)} ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ <b>{chat_title}</b> !!\n"
                f"{_GW_LOOP10}\n"
                f"{_te(_GW_12)}{_te('4958469026595472714')} ʜᴇʟʟᴏ 殺┋ <a href='tg://user?id={tgid}'><b>{full_name}</b></a> !!\n\n"
                f"{_te(_GW_13)}  /help — ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ᴅᴇᴋʜᴏ\n\n"
                f"{_te(_GW_17)} ʀᴜʟᴇꜱ:\n"
                f"{_rules_lines}\n\n"
                f"{_GW_LOOP10}\n"
                f"{_te(_GW_28)} ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1"
                f"</blockquote>"
            )
            if gwtext:
                welcome_txt=gwtext.replace("{name}",full_name).replace("{id}",str(tgid)).replace("{username}",uname).replace("{group}",chat_title)

            # Sticker (group specific) — sirf group pe, bot DM welcome mein nahi
            if gwstk:
                try: bot.send_sticker(cid,gwstk)
                except: pass

            # Video list (round-robin) > single video > image > pfp > text only
            sent=False
            if gwvlist:
                fid=get_next_group_video(cid)
                if fid:
                    try: bot.send_video(cid,fid,caption=welcome_txt,parse_mode="HTML"); sent=True
                    except: pass
            if not sent and gwvid and os.path.exists(gwvid):
                # file_id cache check — agar same video pehle bheja ho to re-download mat karo
                _cached_vid_fid = _group_video_fileid_cache.get(f"{cid}:{gwvid}")
                if _cached_vid_fid:
                    try: bot.send_video(cid,_cached_vid_fid,caption=welcome_txt,parse_mode="HTML"); sent=True
                    except: _group_video_fileid_cache.pop(f"{cid}:{gwvid}",None)
                if not sent:
                    try:
                        with open(gwvid,'rb') as _f:
                            _sv=bot.send_video(cid,_f,caption=welcome_txt,parse_mode="HTML")
                            sent=True
                            # file_id cache karo future ke liye
                            if _sv and _sv.video:
                                _group_video_fileid_cache[f"{cid}:{gwvid}"] = _sv.video.file_id
                    except: pass
            if not sent and gwimg and os.path.exists(gwimg):
                try:
                    with open(gwimg,'rb') as _f: bot.send_photo(cid,_f,caption=welcome_txt,parse_mode="HTML"); sent=True
                except: pass
            if not sent and pic:
                try: bot.send_photo(cid,pic,caption=welcome_txt,parse_mode="HTML"); sent=True
                except: pass
            if not sent:
                # 429 retry logic
                for _retry in range(2):
                    try:
                        bot.send_message(cid,welcome_txt,parse_mode="HTML")
                        sent=True; break
                    except Exception as _we:
                        _err_str = str(_we)
                        if '429' in _err_str:
                            # retry_after extract karo
                            import re as _re429
                            _m429 = _re429.search(r'retry after (\d+)', _err_str)
                            _wait = int(_m429.group(1)) if _m429 else 5
                            time.sleep(_wait + 1)
                        else: break
            try:
                try: bn=_get_bot_username()
                except: bn="felix_bot"
                log_token_activity(tgid,full_name,mb.username or "",0,0,"Group Join",bn)
            except: pass
        except Exception as e:
            _es = str(e)
            if '429' not in _es:  # 429 errors log nahi karo — spam karta hai
                print("[WELCOME] "+_es)
            try:
                if '429' not in _es:
                    bot.send_message(cid,
                        "<blockquote>👋 ʜᴇʟʟᴏ <a href='tg://user?id='+str(mb.id)+""><b>"+_html.escape(mb.first_name or "User")+"</b></a>\n"
                        "🎉 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <b>"+chat_title+"</b>\n"
                        "⚡ @Felix_modz1</blockquote>",parse_mode="HTML")
            except: pass

@bot.message_handler(content_types=['left_chat_member'])
def h_leftmember(m):
    mb=m.left_chat_member
    if not mb or mb.id==_get_bot_id(): return
    cid=m.chat.id; chat_title=m.chat.title or "Group"
    if _clone_group_guard(m): return
    # Check agar ye force join channel hai
    try:
        fj_channels=get_force_join_channels()
        fj_ids=set()
        for entry in fj_channels:
            cid_str=str(entry[0])
            resolved=_resolve_chat_id(cid_str)
            if resolved: fj_ids.add(int(resolved))
        if int(cid) in fj_ids:
            # User ne force join channel leave kiya — cache + DB update
            _channel_check_cache.pop(mb.id, None)
            try: c.execute("UPDATE users SET joined_channel=0 WHERE user_id=?",(mb.id,)); _orig_conn.commit()
            except: pass
            # DM mein rejoin msg bhejo
            try:
                mk=get_channels_keyboard(mb.id)
                bot.send_message(mb.id,
                    f"<blockquote>⚠️ <b>ᴀʀᴇ ʙʜᴀɪ!</b>\n\n"
                    f"Tune <b>{chat_title}</b> leave kar diya! 😢\n\n"
                    f"Bot use karne ke liye wapis join karna hoga!\n"
                    f"Join ke baad ✅ <b>I Joined — Verify</b> dabao.\n\n"
                    f"⚡ @Felix_modz1</blockquote>",
                    reply_markup=mk, parse_mode='HTML')
            except: pass
            return  # group pe left msg mat bhejo channel pe
    except: pass
    try:
        # Goodbye on/off check — sirf bye_on dekho, welcome se alag setting hai
        if not get_group_bye(cid): return
    except: return
    try:
        fname     = mb.first_name or "Hidden User"
        lname     = mb.last_name or ""
        full_name = (fname+" "+lname).strip()
        # Hidden user — username bhi nahi hoga
        uname     = "@"+mb.username if mb.username else "ʜɪᴅᴅᴇɴ ᴜꜱᴇʀ"
        now       = _now_ist()
        try: mem_count=bot.get_chat_members_count(cid)
        except: mem_count="?"
        def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
        _L1  = "4958830950604604428"  # pos 1
        _L2  = "5465629669829128119"  # pos 2-11 loop (10x)
        _L12 = "4956461073550017373"  # pos 12
        _L13 = "6147422674000808494"  # pos 13
        _L14 = "4958636483075376288"  # pos 14
        _L15 = "4958472587123360612"  # pos 15
        _L16 = "4956525562483967357"  # pos 16
        _L17 = "4958724224962265918"  # pos 17
        _L28 = "4958900559139570572"  # pos 28
        _LOOP10 = _te(_L2)*10
        left_txt=(
            f"<blockquote>"
            f"{_te(_L1)} <a href='tg://user?id={mb.id}'><b>{full_name}</b></a> ʜᴀꜱ ʟᴇꜰᴛ ᴛʜᴇ ɢʀᴏᴜᴩ 😢\n"
            f"{_LOOP10}\n\n"
            f"{_te(_L12)} ɴᴀᴍᴇ  : <b>{full_name}</b>\n"
            f"{_te(_L13)} ɪᴅ    : <code>{mb.id}</code>\n"
            f"{_te(_L14)} ᴜꜱᴇʀ  : {uname}\n\n"
            f"{_te(_L17)} ɢʀᴏᴜᴩ : <b>{chat_title}</b>\n"
            f"{_te(_L15)} ᴍᴇᴍʙᴇʀꜱ : <b>{mem_count}</b>\n"
            f"{_te(_L16)} ᴛɪᴍᴇ  : {now}\n\n"
            f"{_LOOP10}\n"
            f"{_te(_L28)} ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1"
            f"</blockquote>"
        )
        bot.send_message(cid,left_txt,parse_mode="HTML")
        try:
            log_token_activity(mb.id,full_name,mb.username or "",0,0,"Group Left",_get_bot_username())
        except: pass
    except Exception as e: print("[LEFT] "+str(e))

@bot.callback_query_handler(func=lambda call: call.data.startswith('numpage_'))
def h_numpage(call):
    parts=call.data.split('_')
    if len(parts)<3: bot.answer_callback_query(call.id); return
    try:
        owner_uid=int(parts[1]); page=int(parts[2])
    except: bot.answer_callback_query(call.id); return
    uid=call.from_user.id
    if uid!=owner_uid:
        bot.answer_callback_query(call.id,"❌ Sirf search karne wala use kar sakta hai!"); return
    cache=_num_cache.get(uid)
    if not cache:
        bot.answer_callback_query(call.id,"❌ Data expire ho gaya. Dobara search karo."); return
    bot.answer_callback_query(call.id)
    data=cache['data']; num=cache['num']; total=cache['total']
    page=max(1,min(page,total))
    rtxt,_,has_prev,has_next=fmt_number_page(data,num,page)
    _num_cache[uid]['page']=page
    mk_pg=InlineKeyboardMarkup(row_width=2)
    btns=[]
    if has_prev: btns.append(_IKB("⬅️ PREVIOUS PAGE",style="primary",callback_data=f"numpage_{uid}_{page-1}"))
    if has_next: btns.append(_IKB("➡️ NEXT PAGE",style="primary",callback_data=f"numpage_{uid}_{page+1}"))
    if btns: mk_pg.row(*btns)
    try: bot.edit_message_text(rtxt,call.message.chat.id,call.message.message_id,reply_markup=mk_pg if btns else None,parse_mode='HTML')
    except: bot.send_message(call.message.chat.id,rtxt,reply_markup=mk_pg if btns else None,parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.startswith('un_more_'))
def h_un_more_callback(call):
    """Show More Details button for username lookup"""
    bot.answer_callback_query(call.id, "⏳ Loading full details...")
    uid = call.from_user.id
    d = call.data  # un_more_{uid}_{msg_id}
    parts = d.split('_')
    # parts: ['un', 'more', uid, msg_id]
    try:
        _orig_uid = int(parts[2])
        _orig_mid = parts[3]
    except: _orig_uid = uid; _orig_mid = ""

    _key = f"unres_{_orig_uid}_{_orig_mid}"
    cached = _user_temp_cache.get(_key)
    if not cached:
        bot.answer_callback_query(call.id, "❌ Data expired! Search again.", show_alert=True)
        return

    res  = cached.get('res')
    query = cached.get('query','')
    now  = _now_ist()
    rtxt, _ = _fmt_tg_user_short(res, query, now)
    if isinstance(rtxt, tuple): rtxt = rtxt[0]

    try:
        bot.send_message(call.message.chat.id, rtxt, parse_mode='HTML')
    except Exception as _e:
        print(f"[UN_MORE_CB] {_safe_err(_e)}")

@bot.callback_query_handler(func=lambda call: True)
def h_callback(call):
    uid=call.from_user.id; d=call.data
    fname=_html.escape(call.from_user.first_name or 'User')
    uname_tg=call.from_user.username or ""
    # Clone bot: Felix ke group/channels pe koi callback respond nahi
    if _IS_CLONE and call.message and _is_felix_chat(call.message.chat.id, getattr(call.message.chat,'username',None)):
        bot.answer_callback_query(call.id); return
    if is_identifier_blocked(str(uid)): bot.answer_callback_query(call.id,"❌ Blocked!"); return

    # ── rst_ callbacks (REDEPLOY/DELETE/EDIT) → dedicated handler ──
    if d.startswith('rst_'):
        h_rst_callback(call)
        return

    # ── show premium plans ──
    if d=="show_premium_plans":
        bot.answer_callback_query(call.id)
        def _te(eid): return f"<tg-emoji emoji-id='{eid}'>⭐</tg-emoji>"
        _L = _te("5465629669829128119")*11
        plans_txt = (
            f"<blockquote>"
            f"{_L}\n"
            f"{_te('6285328937094485878')} {_te('5312361253610475399')} 𝗧ʜᴇ 𝗙ᴇʟɪx {_te('6113891550788324241')} 𝗜ɴꜰᴏ 𝗕ᴏᴛ ᴩʀᴇᴍɪᴜᴍ ᴜᴩɢʀᴀᴅᴇ\n"
            f"{_L}\n"
            f"ᴜᴩɪ ɪᴅ :- <code>afreedi@fam</code>\n\n"
            f"{_te('5312361253610475399')} ᴘʟᴀɴꜱ\n"
            f"├ 1 ᴅᴀʏ  : ₹20\n"
            f"├ 7 ᴅᴀʏꜱ : ₹50\n"
            f"└ 30 ᴅᴀʏꜱ : ₹120\n\n"
            f"{_L}\n"
            f"{_te('6037622221625626773')} {_te('5258204546391351475')} ꜱᴛᴇᴩꜱ\n"
            f"➤ ꜱᴄᴀɴ Qʀ ᴀɴᴅ ᴘᴀʏ\n"
            f"➤ ꜱᴇɴᴅ {_te('5377660214096974712')} Tʀᴀɴꜱꜰᴇʀ ɪᴅ\n"
            f"➤ ꜱᴇɴᴅ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ᴛᴏ ᴀᴅᴍɪɴ\n\n"
            f"{_te('6204263190319081111')} ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @Felix_Bhai {_te('6147565374289220368')}"
            f"</blockquote>"
        )
        back_mk = InlineKeyboardMarkup()
        back_mk.add(_IKB("⬅️ ʙᴀᴄᴋ", style="danger",
                         icon_custom_emoji_id="6039539366177541657",
                         callback_data="back_to_nocredits"))
        try:
            bot.edit_message_text(plans_txt, call.message.chat.id,
                                  call.message.message_id,
                                  reply_markup=back_mk, parse_mode='HTML')
        except:
            bot.send_message(uid, plans_txt, reply_markup=back_mk, parse_mode='HTML')
        return

    # ── back to no credits msg ──
    if d=="back_to_nocredits":
        bot.answer_callback_query(call.id)
        txt, mk = no_credits_msg(uid)
        try:
            bot.edit_message_text(txt, call.message.chat.id,
                                  call.message.message_id,
                                  reply_markup=mk, parse_mode='HTML')
        except:
            bot.send_message(uid, txt, reply_markup=mk, parse_mode='HTML')
        return

    # ── verify channels ──
    if d=="verify_channels":
        _channel_check_cache.pop(uid, None)  # force fresh check
        _is_group_verify = call.message.chat.type in ['group','supergroup']

        # Bot ka access check karo channels pe
        def _bot_has_channel_access():
            chs = get_force_join_channels()
            for entry in chs:
                cid_str = str(entry[0]).strip()
                if cid_str.startswith('https://'): continue
                cid_val = _resolve_chat_id(cid_str)
                if not cid_val: continue
                try:
                    bot.get_chat_member(cid_val, uid)
                    return True  # ek bhi channel me check ho gaya
                except Exception as _bce:
                    err = str(_bce).lower()
                    if any(x in err for x in ['user_not_participant','not a member','not member']):
                        return True  # API working, user not joined
            return False  # sab skip — bot ko access nahi

        verified = check_channel(uid)
        # Agar bot ko channel access nahi — user ko pass kar do (can't verify)
        if not verified and not _bot_has_channel_access():
            verified = True  # bot admin nahi — assume joined, let user in

        if verified:
            bot.answer_callback_query(call.id,"✅ Verified!")
            try: bot.delete_message(call.message.chat.id,call.message.message_id)
            except: pass
            if _is_group_verify:
                try:
                    bot.send_message(call.message.chat.id,
                        f"<blockquote>✅ <a href='tg://user?id={uid}'><b>{call.from_user.first_name}</b></a> verified! Ab bot use kar sakte ho!</blockquote>",
                        parse_mode='HTML')
                except: pass
            else:
                # pending_ref check — referral link se aaya tha kya
                _pref = user_state.pop(uid, None)
                _pending_ref = _pref.get('pending_ref') if isinstance(_pref, dict) else None
                user=get_user(uid); nm=user[2] if user else "User"; cr=get_credits(uid)
                # Agar naya user hai aur pending_ref hai — register + credit do
                if not user:
                    add_user(uid, call.from_user.username or "", call.from_user.first_name or "User", _pending_ref)
                    user=get_user(uid); nm=user[2] if user else "User"; cr=get_credits(uid)
                elif _pending_ref and not get_user(uid):
                    add_user(uid, call.from_user.username or "", call.from_user.first_name or "User", _pending_ref)
                try: rl=f"https://t.me/{_get_bot_username()}?start={uid}"
                except: rl="--"
                _wmk=InlineKeyboardMarkup()
                _wmk.add(_IKB("ꜱʜᴀʀᴇ",style="success",icon_custom_emoji_id="5253804796589402657",url=f"https://t.me/share/url?url={rl}&amp;text=Join+this+amazing+Info+Bot!"))
                wtxt_v=format_welcome(uid,nm,cr,call.from_user.username or "")
                wtxt_v_cap=_safe_caption(wtxt_v,1024)
                st_v=get_welcome_settings()
                wvid_v=st_v[4] if st_v else None; wimg_v=st_v[3] if st_v else None
                _v_sent=False
                _wv_fid_v=_welcome_fileid_cache.get('video')
                _wi_fid_v=_welcome_fileid_cache.get('image')
                if _wv_fid_v:
                    try: bot.send_video(uid,_wv_fid_v,caption=wtxt_v_cap,reply_markup=kb_p1(uid),parse_mode='HTML',message_effect_id="5046509860389126442"); _v_sent=True
                    except: _welcome_fileid_cache.pop('video',None)
                if not _v_sent and _wi_fid_v:
                    try: bot.send_photo(uid,_wi_fid_v,caption=wtxt_v_cap,reply_markup=kb_p1(uid),parse_mode='HTML',message_effect_id="5046509860389126442"); _v_sent=True
                    except: _welcome_fileid_cache.pop('image',None)
                if not _v_sent and wvid_v and os.path.exists(wvid_v):
                    try:
                        with open(wvid_v,'rb') as _fv: bot.send_video(uid,_fv,caption=wtxt_v_cap,reply_markup=kb_p1(uid),parse_mode='HTML',message_effect_id="5046509860389126442"); _v_sent=True
                    except: pass
                if not _v_sent and wimg_v and os.path.exists(wimg_v):
                    try:
                        with open(wimg_v,'rb') as _fi: bot.send_photo(uid,_fi,caption=wtxt_v_cap,reply_markup=kb_p1(uid),parse_mode='HTML',message_effect_id="5046509860389126442"); _v_sent=True
                    except: pass
                if not _v_sent:
                    try: _send_react(uid,wtxt_v,reply_markup=kb_p1(uid),parse_mode='HTML',message_effect_id="5046509860389126442")
                    except:
                        import re as _rev; bot.send_message(uid,_rev.sub(r'<[^>]+>','',wtxt_v),reply_markup=kb_p1(uid))
        else:
            # Sirf unjoined channels dikhao
            _mk_still = get_channels_keyboard(uid)
            if _mk_still:
                bot.answer_callback_query(call.id,"⚠️ Abhi bhi kuch channels join nahi kiye!")
                try:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=_mk_still)
                except: pass
            else:
                bot.answer_callback_query(call.id,"⚠️ Join all channels first!")
        return

    # ── noop ──
    if d=="noop": bot.answer_callback_query(call.id); return

    # ── Redeem credit code inline button ──
    if d=="redeem_credit_code":
        bot.answer_callback_query(call.id)
        user_state[uid]=S_REDEEM
        bot.send_message(uid,
            "<blockquote>🎫 <b>ᴄʀᴇᴅɪᴛ ᴄᴏᴅᴇ</b>\n\n"
            "📤 Code bhejo:\n"
            "Example: <code>FELIX-XXXXXX</code>\n\n"
            "⚡ @Felix_modz1</blockquote>",
            parse_mode='HTML'); return

    # ── Redeem premium code inline button ──
    if d=="redeem_premium_code":
        bot.answer_callback_query(call.id)
        user_state[uid]=S_PREM_REDEEM
        bot.send_message(uid,
            "<blockquote>💎 <b>ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴅᴇ</b>\n\n"
            "📤 Code bhejo:\n"
            "Example: <code>FPREM-XXXXXX</code>\n\n"
            "⚡ @Felix_modz1</blockquote>",
            parse_mode='HTML'); return

    # ── refer_no_points — insufficient points, refer karne bolo ──
    if d=="refer_no_points" or d.startswith("refer_need_"):
        bot.answer_callback_query(call.id)
        try: lnk=f"https://t.me/{_get_bot_username()}?start={uid}"
        except: lnk=f"https://t.me/bot?start={uid}"
        # Fetch coins from DB
        try:
            _coins_row=c.execute("SELECT coins FROM users WHERE user_id=?",(uid,)).fetchone()
            coins=_coins_row[0] if _coins_row and _coins_row[0] else 0
        except: coins=0
        # Specific tier needed?
        if d.startswith("refer_need_"):
            try: tier_cost=int(d.split("_")[2]); needed=max(0,tier_cost-coins)
            except: tier_cost=5; needed=max(0,5-coins)
        else:
            tier_cost=5; needed=max(0,5-coins)
        txt=(
            f"<blockquote>╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━✦\n"
            f"│ 🔴 <b>ɪɴꜱᴜꜰꜰɪᴄɪᴇɴᴛ ᴩᴏɪɴᴛꜱ</b>\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━✦\n\n"
            f"🎫 Tumhare Refer Points: <b>{coins}</b>\n"
            f"💡 Is plan ke liye chahiye: <b>{tier_cost} 🎫</b>\n"
            f"📊 Aur chahiye: <b>{needed} 🎫</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Refer karo → Points pao → Premium lo!\n\n"
            f"🔗 Tera refer link:\n<code>{lnk}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ @Felix_modz1</blockquote>"
        )
        mk_rp=InlineKeyboardMarkup()
        mk_rp.add(_IKB("📤 ʀᴇꜰᴇʀ ᴋᴀʀᴏ — ᴩᴏɪɴᴛꜱ ᴋᴀᴍᴀᴏ",style="primary",icon_custom_emoji_id="5253804796589402657",url=f"https://t.me/share/url?url={lnk}&text=Join+this+amazing+info+bot!"))
        mk_rp.add(_IKB("🔙 ᴄʟᴏꜱᴇ",style="danger",callback_data="close_prem_claim"))
        try: bot.edit_message_text(txt,call.message.chat.id,call.message.message_id,reply_markup=mk_rp,parse_mode='HTML')
        except: bot.send_message(uid,txt,reply_markup=mk_rp,parse_mode='HTML')
        return

    if d=="close_prem_claim":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id,call.message.message_id)
        except: pass
        return

    if d=="show_my_credits":
        bot.answer_callback_query(call.id)
        cr=get_credits(uid); refs=get_referral_count(uid)
        user=get_user(uid)
        is_prem=user[7]==1 if user else False
        prem_str=str(cr)
        spin_done=not can_claim_daily(uid)
        spin_str="Claimed" if spin_done else "Available"
        try: lnk="https://t.me/"+_get_bot_username()+"?start="+str(uid)
        except: lnk="https://t.me/bot?start="+str(uid)
        mk_sc=InlineKeyboardMarkup()
        mk_sc.add(_IKB("📤 Refer Karo +2 Credits", style="success",
            icon_custom_emoji_id="5253804796589402657",
            url="https://t.me/share/url?url="+lnk+"&text=Join+karo!"))
        _smc=("<blockquote>━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰 <b>MY CREDITS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 Credits      : <b>"+prem_str+"</b>\n"
            "👥 Total Refers : <b>"+str(refs)+"</b>\n"
            "🎁 Daily Spin   : "+spin_str+"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔗 Refer Link:\n<code>"+lnk+"</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ @Felix_modz1</blockquote>")
        try: bot.send_message(uid,_smc,reply_markup=mk_sc,parse_mode="HTML")
        except: pass
        return

    # ── BOT API URL MANAGER callbacks ──
    if d.startswith("apiurl_"):
        if uid!=OWNER_ID: bot.answer_callback_query(call.id,"❌ Sirf owner!"); return
        bot.answer_callback_query(call.id)

        if d=="apiurl_back":
            # Back to admin p3
            try: bot.delete_message(call.message.chat.id,call.message.message_id)
            except: pass
            bot.send_message(uid,"<blockquote>⚙️ <b>Admin P1</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML')
            return

        if d.startswith("apiurl_sel_"):
            api_key=d[len("apiurl_sel_"):]
            # Find label & default url
            api_info=next(((k,lbl,url) for k,lbl,url in _BOT_APIS if k==api_key),None)
            if not api_info:
                bot.answer_callback_query(call.id,"❌ Unknown API"); return
            _,api_label,default_url=api_info
            custom_url=_get_api_custom_url(api_key)
            current_url=custom_url if custom_url else default_url
            source="✏️ Custom" if custom_url else "🗂️ Default"
            txt=(f"<blockquote>🔗 <b>{api_label}</b>\n"
                 f"━━━━━━━━━━━━━━━━━━\n\n"
                 f"Key: <code>{api_key}</code>\n"
                 f"Source: {source}\n\n"
                 f"<b>Current URL:</b>\n<code>{current_url}</code>\n\n"
                 f"<i>Note: URL mein {{}} placeholder hona chahiye.</i>\n"
                 f"⚡ @Felix_modz1</blockquote>")
            mk=InlineKeyboardMarkup()
            mk.add(_IKB("✏️ URL Change Karo",style="success",callback_data=f"apiurl_change_{api_key}"))
            if custom_url:
                mk.add(_IKB("🗑️ Reset to Default",style="danger",callback_data=f"apiurl_reset_{api_key}"))
            mk.add(_IKB("⬅️ API List",style="primary",callback_data="apiurl_list"))
            try: bot.edit_message_text(txt,call.message.chat.id,call.message.message_id,reply_markup=mk,parse_mode='HTML')
            except: bot.send_message(uid,txt,reply_markup=mk,parse_mode='HTML')
            return

        if d.startswith("apiurl_change_"):
            api_key=d[len("apiurl_change_"):]
            api_info=next(((k,lbl,url) for k,lbl,url in _BOT_APIS if k==api_key),None)
            if not api_info:
                bot.answer_callback_query(call.id,"❌ Unknown API"); return
            _,api_label,_=api_info
            # Cancel button
            mk_cancel=InlineKeyboardMarkup()
            mk_cancel.add(_IKB("❌ Cancel",style="danger",callback_data=f"apiurl_sel_{api_key}"))
            prompt=bot.send_message(uid,
                f"<blockquote>✏️ <b>{api_label}</b>\n\n"
                f"Naya URL type karke bhejo:\n\n"
                f"Format: <code>https://example.com/api?q={{}}&key=XYZ</code>\n\n"
                f"⚠️ {{}} placeholder zaroori hai!\n"
                f"<i>Cancel karne ke liye button dabao.</i></blockquote>",
                reply_markup=mk_cancel,parse_mode='HTML')
            user_state[uid]={'state':'API_URL_INPUT','api_key':api_key,'api_label':api_label,'prompt_msg_id':prompt.message_id}
            return

        if d.startswith("apiurl_reset_"):
            api_key=d[len("apiurl_reset_"):]
            try:
                c.execute("DELETE FROM api_keys WHERE api_name=?",(api_key,)); conn.commit()
            except: pass
            api_info=next(((k,lbl,url) for k,lbl,url in _BOT_APIS if k==api_key),None)
            lbl=api_info[1] if api_info else api_key
            bot.send_message(uid,f"<blockquote>✅ <b>{lbl}</b> reset to default!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
            _send_bot_api_urls_menu(uid)
            return

        if d=="apiurl_list":
            _send_bot_api_urls_menu(uid,call.message.message_id)
            return

        return

    # ── BOT API KEY MANAGER callbacks ──
    if d.startswith("apikey_"):
        if uid!=OWNER_ID: bot.answer_callback_query(call.id,"❌ Sirf owner!"); return
        bot.answer_callback_query(call.id)

        if d=="apikey_back":
            try: bot.delete_message(call.message.chat.id,call.message.message_id)
            except: pass
            bot.send_message(uid,"<blockquote>⚙️ <b>Admin P1</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML')
            return

        if d=="apikey_list":
            _send_bot_api_keys_menu(uid,call.message.message_id)
            return

        if d.startswith("apikey_sel_"):
            key_name=d[len("apikey_sel_"):]
            key_info=next(((k,lbl,dk) for k,lbl,dk in _BOT_API_KEYS if k==key_name),None)
            if not key_info:
                bot.answer_callback_query(call.id,"❌ Unknown Key"); return
            _,key_label,default_key=key_info
            custom_key=_get_api_custom_key(key_name)
            current_key=custom_key if custom_key else default_key
            source="✏️ Custom" if custom_key else "🗂️ Default"
            # Show key partially masked for security
            masked=current_key[:6]+"***"+current_key[-4:] if len(current_key)>10 else current_key
            txt2=(f"<blockquote>🔑 <b>{key_label}</b>\n"
                  f"━━━━━━━━━━━━━━━━━━\n\n"
                  f"Key Name: <code>{key_name}</code>\n"
                  f"Source: {source}\n\n"
                  f"<b>Current Key:</b>\n<code>{masked}</code>\n\n"
                  f"<i>Naya key set karne ke liye button dabao.</i>\n"
                  f"⚡ @Felix_modz1</blockquote>")
            mk2=InlineKeyboardMarkup()
            mk2.add(_IKB("✏️ Key Change Karo",style="success",callback_data=f"apikey_change_{key_name}"))
            if custom_key:
                mk2.add(_IKB("🗑️ Reset to Default",style="danger",callback_data=f"apikey_reset_{key_name}"))
            mk2.add(_IKB("⬅️ Key List",style="primary",callback_data="apikey_list"))
            try: bot.edit_message_text(txt2,call.message.chat.id,call.message.message_id,reply_markup=mk2,parse_mode='HTML')
            except: bot.send_message(uid,txt2,reply_markup=mk2,parse_mode='HTML')
            return

        if d.startswith("apikey_change_"):
            key_name=d[len("apikey_change_"):]
            key_info=next(((k,lbl,dk) for k,lbl,dk in _BOT_API_KEYS if k==key_name),None)
            if not key_info:
                bot.answer_callback_query(call.id,"❌ Unknown Key"); return
            _,key_label,_=key_info
            mk_cancel=InlineKeyboardMarkup()
            mk_cancel.add(_IKB("❌ Cancel",style="danger",callback_data=f"apikey_sel_{key_name}"))
            prompt=bot.send_message(uid,
                f"<blockquote>✏️ <b>{key_label}</b>\n\n"
                f"Naya API key type karke bhejo:\n\n"
                f"Example: <code>SH4DAW-NEWKEY</code>\n\n"
                f"<i>Cancel karne ke liye button dabao.</i></blockquote>",
                reply_markup=mk_cancel,parse_mode='HTML')
            user_state[uid]={'state':'API_KEY_INPUT','key_name':key_name,'key_label':key_label,'prompt_msg_id':prompt.message_id}
            return

        if d.startswith("apikey_reset_"):
            key_name=d[len("apikey_reset_"):]
            try:
                # Sirf api_key column clear karo (api_url wala row rehne do)
                c.execute("UPDATE api_keys SET api_key='' WHERE api_name=?",(key_name,)); conn.commit()
                # Agar row hi nahi to ignore
            except: pass
            key_info=next(((k,lbl,dk) for k,lbl,dk in _BOT_API_KEYS if k==key_name),None)
            lbl=key_info[1] if key_info else key_name
            default_k=key_info[2] if key_info else "—"
            bot.send_message(uid,f"<blockquote>✅ <b>{lbl}</b> default pe reset!\nDefault: <code>{default_k}</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
            _send_bot_api_keys_menu(uid)
            return

        return

    # ── back to main ──
    if d=="back_to_main":
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>⬇️ ᴍᴀɪɴ ᴍᴇɴᴜ</blockquote>",reply_markup=kb_p1(uid),parse_mode='HTML')
        bot.answer_callback_query(call.id); return

    # ── menu page 2 ──
    if d=="menu_p2":
        bot.answer_callback_query(call.id)
        try: bot.edit_message_reply_markup(call.message.chat.id,call.message.message_id,reply_markup=kb_menu_p2(uid))
        except: pass; return

    if d=="menu_p1":
        bot.answer_callback_query(call.id)
        try: bot.edit_message_reply_markup(call.message.chat.id,call.message.message_id,reply_markup=kb_menu_p1(uid))
        except: pass; return

    if d=="menu_close":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id,call.message.message_id)
        except: pass; return

    # ── menu feature callbacks ──
    smap={'menu_number':S_NUM,'menu_username':S_USER,'menu_tgid':S_TID,'menu_aadhar':S_ADH,
          'menu_instagram':S_INSTA,'menu_freefire':S_FF,'menu_freefire_like':S_FF_LIKE_UID,
          'menu_vehicle':S_VEH}
    prompt_map={'menu_number':"📱 10-digit number bhejo:",'menu_username':"🔍 @username bhejo:",
                'menu_tgid':"🆔 Telegram ID bhejo:","menu_aadhar":"🆔 Aadhar number bhejo:",
                'menu_instagram':"📸 Instagram username bhejo:","menu_freefire":"🎮 FF UID bhejo:",
                'menu_freefire_like':"❤️ FF UID bhejo:","menu_vehicle":"🚗 RC number bhejo:",
}
    if d in smap:
        bot.answer_callback_query(call.id)
        user_state[uid]=smap[d]
        _cr_inline=get_credits(uid)
        _rate_map={'menu_number':'1','menu_username':'1','menu_tgid':'1','menu_aadhar':'1',
                   'menu_instagram':'1','menu_freefire':'1','menu_freefire_like':'2',
                   'menu_vehicle':'1','menu_vehicle':'1'}
        _prompt_full_map={
            'menu_number':(f"📱 ꜱᴇɴᴅ <b>10-ᴅɪɢɪᴛ ᴍᴏʙɪʟᴇ ɴᴜᴍʙᴇʀ</b>\nᴇxᴀᴍᴩʟᴇ: <code>9876543210</code>"),
            'menu_username':(f"🔍 ꜱᴇɴᴅ <b>@username</b> ʏᴀ <b>TG ID</b>\nᴇxᴀᴍᴩʟᴇ: <code>@durov</code>"),
            'menu_tgid':(f"🆔 ꜱᴇɴᴅ <b>Telegram ID</b>\nᴇxᴀᴍᴩʟᴇ: <code>123456789</code>"),
            'menu_aadhar':(f"🆔 ꜱᴇɴᴅ <b>12-ᴅɪɢɪᴛ Aadhar</b>\nᴇxᴀᴍᴩʟᴇ: <code>649964855626</code>"),
            'menu_instagram':(f"📸 ꜱᴇɴᴅ <b>Instagram Username</b>\nᴇxᴀᴍᴩʟᴇ: <code>cristiano</code>"),
            'menu_freefire':(f"🎮 ꜱᴇɴᴅ <b>FF UID</b>\nᴇxᴀᴍᴩʟᴇ: <code>1382401870</code>"),
            'menu_freefire_like':(f"❤️ ꜱᴇɴᴅ <b>FF UID</b>\nᴇxᴀᴍᴩʟᴇ: <code>1382401870</code>"),
            'menu_vehicle':(f"🚗 ꜱᴇɴᴅ <b>RC Number</b>\nᴇxᴀᴍᴩʟᴇ: <code>MH12AB1234</code>"),
        }
        _rate=_rate_map.get(d,'1')
        _ptext=_prompt_full_map.get(d,"Value bhejo:")
        bot.send_message(uid,(
            f"<blockquote>{_ptext}\n\n"
            f"💰 ꜱᴇᴀʀᴄʜ ʀᴀᴛᴇ :- <b>{_rate} ᴄʀᴇᴅɪᴛ</b>\n"
            f"💳 ᴀᴀᴩᴋᴇ ᴄʀᴇᴅɪᴛꜱ :- <b>{_cr_inline}</b>\n\n"
            f"⚡ ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ : @FELIX_BHAI</blockquote>"
        ),parse_mode='HTML'); return

    if d=="menu_mycredits":
        bot.answer_callback_query(call.id)
        cr=get_credits(uid); refs=get_referral_count(uid)
        user_row=get_user(uid); is_prem=bool(user_row[8]) if user_row else False
        spin_done=not can_claim_daily(uid)
        spin_str="✅ ᴄʟᴀɪᴍᴇᴅ" if spin_done else "🎁 ᴀᴠᴀɪʟᴀʙʟᴇ"
        prem_str="💎 ᴜɴʟɪᴍɪᴛᴇᴅ" if is_prem else str(cr)
        try: rl=f"https://t.me/{_get_bot_username()}?start={uid}"
        except: rl=f"https://t.me/bot?start={uid}"
        rl_short=rl
        mk2=InlineKeyboardMarkup()
        mk2.add(_IKB("📤 ʀᴇꜰᴇʀ ᴋᴀʀᴏ — +2 ᴄʀᴇᴅɪᴛꜱ",style="success",url=f"https://t.me/share/url?url={rl_short}&text=Join+karo+is+amazing+bot!"))
        _mc_txt=(
            f"<blockquote>━━━━━━━━━━━━━━━━━━━━━━\n"
            f"╭─── 💰 <b>ᴍʏ ᴄʀᴇᴅɪᴛꜱ</b> ───╮\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 ᴄʀᴇᴅɪᴛꜱ       : <b>{prem_str}</b>\n"
                f"🎁 ᴅᴀɪʟʏ ꜱᴩɪɴ   : {spin_str}\n"
            f"💎 ᴩʀᴇᴍɪᴜᴍ      : {'<b>ᴜɴʟɪᴍɪᴛᴇᴅ</b>' if is_prem else 'ɴᴏ'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"╭━━━━━━━━━━━━━━━✦\n"
            f"│ 👥 ʀᴇꜰᴇʀʀᴀʟꜱ\n"
            f"╰━━━━━━━━━━━━━━━✦\n\n"
            f"🔄 ʀᴇꜰᴇʀ ᴋʀᴏ → +2 ᴄʀᴇᴅɪᴛ ᴩᴀᴏ!\n\n"
            f"📊 ᴛᴏᴛᴀʟ ʀᴇꜰᴇʀʀᴀʟꜱ : <b>{refs}</b>\n\n"
            f"🔗 ʀᴇꜰᴇʀ ʟɪɴᴋ :\n{rl_short}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 ᴄʀᴇᴅɪᴛꜱ : {cr} | 👥 ʀᴇꜰᴇʀꜱ : {refs}\n"
            f"🎁 ᴩᴇʀ ʀᴇꜰᴇʀʀᴀʟ : +2 ᴄʀᴇᴅɪᴛꜱ\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ @Felix_modz1</blockquote>"
        )
        try: bot.send_message(uid,_mc_txt,reply_markup=mk2,parse_mode='HTML')
        except Exception as _mce: print(f"[MENU_CREDITS] {_mce}")
        return

    if d=="menu_channel":
        bot.answer_callback_query(call.id)
        chs=get_force_join_channels()
        if chs:
            mk=InlineKeyboardMarkup()
            for ch_id,ch_title,ch_url in chs:
                if ch_url: mk.add(_IKB(f"📢 {ch_title}",url=ch_url))
            bot.send_message(uid,"<blockquote>📢 <b>Channels:</b></blockquote>",reply_markup=mk,parse_mode='HTML')
        else: bot.send_message(uid,"<blockquote>📢 No channels set.</blockquote>",parse_mode='HTML'); return

    if d=="menu_helpinfo":
        bot.answer_callback_query(call.id)
        bot.send_message(uid,
            "<blockquote>ℹ️ <b>HELP</b>\n\n"
            "📱 Number Info - Indian number lookup\n"
            "🔍 Username - TG username lookup\n"
            "🆔 TG ID - Telegram user info\n"
            "💣 Bomber - SMS bomber\n"
            "🎮 FF Info - Free Fire player info\n"
            "❤️ FF Like - Send likes\n"
            "🚗 Vehicle - RC number lookup\n"
            "🎁 Daily Spin - Free credits daily\n\n"
            "⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

    if d=="menu_select_user":
        bot.answer_callback_query(call.id)
        bot.send_message(uid,"<blockquote>👤 <b>ꜱᴇʟᴇᴄᴛ ᴜꜱᴇʀ</b>\nNeeche button dabao aur user select karo:</blockquote>",reply_markup=kb_select_user(),parse_mode='HTML'); return

    if d=="menu_bomber":
        bot.answer_callback_query(call.id)
        if not is_feature_enabled('bomber'): return
        user_state[uid]=S_BOMB
        bot.send_message(uid,"<blockquote>💣 10-digit number bhejo (bomber ke liye):\n<code>9876543210</code>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

    # ── Group /start close ──
    if d.startswith("grp_cls_"):
        try:
            owner_uid=int(d[len("grp_cls_"):])
            if uid!=owner_uid: bot.answer_callback_query(call.id,"❌ Sirf button dabane wala close kar sakta hai!"); return
        except: pass
        try: bot.delete_message(call.message.chat.id,call.message.message_id)
        except: pass
        bot.answer_callback_query(call.id); return

    # ── Group number button ──
    if d.startswith("grp_num_"):
        try:
            rest=d[len("grp_num_"):]
            last_us=rest.rfind("_")
            owner_uid=int(rest[:last_us]); cid=int(rest[last_us+1:])
        except: bot.answer_callback_query(call.id); return
        if uid!=owner_uid: bot.answer_callback_query(call.id,"❌ Sirf /start karne wala use kar sakta hai!"); return
        if not is_feature_enabled('number'): bot.answer_callback_query(call.id,"❌ Feature OFF!"); return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        ask=bot.send_message(cid,
            f"<blockquote>📱 <b>ɴᴜᴍʙᴇʀ ɪɴꜰᴏ</b>\n\n"
            f"<a href='tg://user?id={uid}'><b>{fname}</b></a> — number bhejo:\n"
            f"<i>Example: 9876543210</i>\n\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        user_state[uid]={'state':S_NUM,'chat_id':cid,'ask_id':ask.message_id,'group':True,'requester':uid}; return

    # ── Group Instagram button (username search) ──
    if d.startswith("grp_insta_"):
        try:
            rest=d[len("grp_insta_"):]
            last_us=rest.rfind("_")
            owner_uid=int(rest[:last_us]); cid=int(rest[last_us+1:])
        except: bot.answer_callback_query(call.id); return
        if uid!=owner_uid: bot.answer_callback_query(call.id,"❌ Sirf /start karne wala use kar sakta hai!"); return
        if not is_feature_enabled('instagram'): bot.answer_callback_query(call.id,"❌ Feature OFF!"); return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        ask=bot.send_message(cid,
            f"<blockquote>📸 <b>ɪɴꜱᴛᴀɢʀᴀᴍ ɪɴꜰᴏ</b>\n\n"
            f"<a href='tg://user?id={uid}'><b>{fname}</b></a> — Instagram @username bhejo:\n"
            f"<i>Example: @cristiano</i>\n\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        user_state[uid]={'state':S_INSTA,'chat_id':cid,'ask_id':ask.message_id,'group':True,'requester':uid}; return

    # ── Group Bomber button ──
    if d.startswith("grp_bomb_"):
        try:
            rest=d[len("grp_bomb_"):]
            last_us=rest.rfind("_")
            owner_uid=int(rest[:last_us]); cid=int(rest[last_us+1:])
        except: bot.answer_callback_query(call.id); return
        if uid!=owner_uid: bot.answer_callback_query(call.id,"❌ Sirf /start karne wala use kar sakta hai!"); return
        if not is_feature_enabled('bomber'): bot.answer_callback_query(call.id,"❌ Feature OFF!"); return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        ask=bot.send_message(cid,
            f"<blockquote>💣 <b>ʙᴏᴍʙᴇʀ</b>\n\n"
            f"<a href='tg://user?id={uid}'><b>{fname}</b></a> — 10-digit number bhejo:\n"
            f"<i>Example: 9876543210</i>\n\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        user_state[uid]={'state':S_BOMB,'chat_id':cid,'ask_id':ask.message_id,'group':True,'requester':uid}; return

    # ── Group TG ID / username button ──
    if d.startswith("grp_usr_"):
        try:
            rest=d[len("grp_usr_"):]
            last_us=rest.rfind("_")
            owner_uid=int(rest[:last_us]); cid=int(rest[last_us+1:])
        except: bot.answer_callback_query(call.id); return
        if uid!=owner_uid: bot.answer_callback_query(call.id,"❌ Sirf /start karne wala use kar sakta hai!"); return
        if not is_feature_enabled('tgid'): bot.answer_callback_query(call.id,"❌ Feature OFF!"); return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        ask=bot.send_message(cid,
            f"<blockquote>🆔 <b>ᴛɢ ɪᴅ ɪɴꜰᴏ</b>\n\n"
            f"<a href='tg://user?id={uid}'><b>{fname}</b></a> — TG ID bhejo:\n"
            f"<i>Example: 123456789</i>\n\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        user_state[uid]={'state':S_TID,'chat_id':cid,'ask_id':ask.message_id,'group':True,'requester':uid}; return

    # ── Group daily spin (🎯 — anyone can tap, deletes menu msg) ──
    if d.startswith("grp_spn_"):
        bot.answer_callback_query(call.id)
        try:
            rest=d[len("grp_spn_"):]
            last_us=rest.rfind("_"); cid=int(rest[last_us+1:])
        except: return
        # Force join check — group spin pe bhi
        user_obj_spn=get_user(uid)
        if not user_obj_spn: add_user(uid,uname_tg,fname); user_obj_spn=get_user(uid)
        if not check_channel(uid):
            mk_fj=get_channels_keyboard(uid)
            if mk_fj:
                bot.send_message(uid,
                    "<blockquote>⚠️ <b>ᴊᴏɪɴ ʀᴇꞯᴜɪʀᴇᴅ!</b>\n\nSpin ke liye sabhi channels join karo!\n"
                    "Join ke baad ✅ <b>I Joined — Verify</b> dabao\n\n⚡ @Felix_modz1</blockquote>",
                    reply_markup=mk_fj,parse_mode='HTML')
                return
        # Delete the /start menu message so group stays clean
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        threading.Thread(target=_do_group_spin, args=(uid, fname, uname_tg, cid), daemon=True).start()
        return

    # ── Group choose user button (owner only → DM mein select user) ──
    if d.startswith("grp_cho_"):
        try:
            rest=d[len("grp_cho_"):]
            last_us=rest.rfind("_")
            owner_uid=int(rest[:last_us]); cid=int(rest[last_us+1:])
        except: bot.answer_callback_query(call.id); return
        if uid!=owner_uid: bot.answer_callback_query(call.id,"❌ Sirf /start karne wala use kar sakta hai!"); return
        bot.answer_callback_query(call.id)
        try: bn3=_get_bot_username()
        except: bn3="felix_bot"
        dm_url=f"https://t.me/{bn3}?start=dm_selectuser"
        try:
            bot.send_message(uid,
                "<blockquote>👤 <b>ѕᴇʟᴇᴄᴛ ᴜѕᴇʀ</b>\nNeeche button dabao aur user select karo:</blockquote>",
                reply_markup=kb_select_user(),parse_mode='HTML')
        except: pass
        # Also send DM button in group so others know
        mk_dm=InlineKeyboardMarkup()
        mk_dm.add(_IKB("Open in DM",style="primary",url=dm_url))
        bot.send_message(cid,"<blockquote>DM check karo! @Felix_modz1</blockquote>",reply_markup=mk_dm,parse_mode="HTML"); return
    # ── group management callbacks ──
    if d.startswith("grp_") and is_admin(uid):
        if d.startswith("grp_pg_"):
            pg=int(d.split("grp_pg_")[1])
            try: bot.edit_message_reply_markup(call.message.chat.id,call.message.message_id,reply_markup=kb_groups_inline(pg))
            except: pass
            bot.answer_callback_query(call.id); return
        if d=="grp_back_list":
            try: bot.edit_message_reply_markup(call.message.chat.id,call.message.message_id,reply_markup=kb_groups_inline())
            except: pass
            bot.answer_callback_query(call.id); return
        if d=="grp_back_menu":
            bot.answer_callback_query(call.id)
            bot.send_message(uid,"<blockquote>📌 <b>ADMIN</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML'); return
        if d.startswith("grp_sel_"):
            gid2=int(d.split("grp_sel_")[1]); refresh_group_msg(call.message.chat.id,call.message.message_id,gid2)
            bot.answer_callback_query(call.id); return
        if d.startswith("grp_unl_"):
            gid2=int(d.split("grp_unl_")[1]); toggle_group_unlimited(gid2); refresh_group_msg(call.message.chat.id,call.message.message_id,gid2)
            bot.answer_callback_query(call.id,"✅ Updated"); return
        if d.startswith("grp_blk_"):
            gid2=int(d.split("grp_blk_")[1]); toggle_group_block(gid2); refresh_group_msg(call.message.chat.id,call.message.message_id,gid2)
            bot.answer_callback_query(call.id,"✅ Updated"); return
        if d.startswith("grp_mute_"):
            gid2=int(d.split("grp_mute_")[1]); toggle_group_mute(gid2); refresh_group_msg(call.message.chat.id,call.message.message_id,gid2)
            bot.answer_callback_query(call.id,"✅ Updated"); return
        if d.startswith("grp_info_"):
            gid2=int(d.split("grp_info_")[1]); refresh_group_msg(call.message.chat.id,call.message.message_id,gid2)
            bot.answer_callback_query(call.id); return

    # ── GROUP CONTROL panel (all groups) ──
    if d.startswith("grpctrl_") and is_admin(uid):
        bot.answer_callback_query(call.id)
        groups = get_all_groups()

        # ── Per-group toggle ──
        if d.startswith("grpctrl_tog_"):
            parts_tog = d.split("_")
            # grpctrl_tog_<gid>_<page>
            try:
                gid_tog = int(parts_tog[2])
                page_tog = int(parts_tog[3]) if len(parts_tog) > 3 else 1
            except: gid_tog=0; page_tog=1
            if gid_tog:
                g_tog = get_group(gid_tog)
                if g_tog:
                    new_state = toggle_group_unlimited(gid_tog)
                    status_txt = "🟢 UNLIMITED" if new_state else "🔴 LIMITED"
                    title_tog = next((t for gi,t in groups if gi==gid_tog), str(gid_tog))
                    bot.answer_callback_query(call.id, f"{status_txt} — {title_tog[:20]}", show_alert=False)
            _send_group_control_panel(call.message.chat.id, call.message.message_id, page_tog)
            return

        # ── Page navigation ──
        if d.startswith("grpctrl_pg_"):
            try: page_nav = int(d.split("_")[2])
            except: page_nav = 1
            _send_group_control_panel(call.message.chat.id, call.message.message_id, page_nav)
            return

        if d == "grpctrl_all_unl":
            count=0
            for gid2,_ in groups:
                g2=get_group(gid2)
                if g2 and safe_g(g2,5)!=1:
                    toggle_group_unlimited(gid2); count+=1
            bot.answer_callback_query(call.id, f"✅ {count} groups → UNLIMITED")
            _send_group_control_panel(call.message.chat.id, call.message.message_id)
            return
        if d == "grpctrl_all_lim":
            count=0
            for gid2,_ in groups:
                g2=get_group(gid2)
                if g2 and safe_g(g2,5)==1:
                    toggle_group_unlimited(gid2); count+=1
            bot.answer_callback_query(call.id, f"🔴 {count} groups → LIMITED")
            _send_group_control_panel(call.message.chat.id, call.message.message_id)
            return
        if d == "grpctrl_add_credits":
            user_state[uid]={'state':'GRPCTRL_ADD_CREDITS','msg_id':call.message.message_id,'chat_id':call.message.chat.id}
            bot.send_message(uid,
                f"<blockquote>💰 <b>ALL GROUPS CREDITS ADD</b>\n\n"
                f"Kitne credits add karne hain <b>sabhi {len(groups)} groups</b> ko?\n"
                f"Example: <code>100</code>\n\n"
                f"⚡ @Felix_modz1</blockquote>", parse_mode='HTML')
            return
        if d == "grpctrl_rem_credits":
            user_state[uid]={'state':'GRPCTRL_REM_CREDITS','msg_id':call.message.message_id,'chat_id':call.message.chat.id}
            bot.send_message(uid,
                f"<blockquote>🗑️ <b>ALL GROUPS CREDITS REMOVE</b>\n\n"
                f"Kitne credits hatane hain <b>sabhi {len(groups)} groups</b> se?\n"
                f"Example: <code>50</code>\n\n"
                f"⚡ @Felix_modz1</blockquote>", parse_mode='HTML')
            return
        if d == "grpctrl_view":
            if not groups:
                bot.send_message(uid, "<blockquote>❌ No groups found.</blockquote>", parse_mode='HTML'); return
            lines = []
            for gid2, title2 in groups[:20]:
                g2=get_group(gid2); ul2=safe_g(g2,5); cr2=safe_g(g2,4)
                lines.append(f"• <b>{title2[:18]}</b> | {'∞' if ul2 else str(cr2)+'cr'} | <code>{gid2}</code>")
            txt2=(f"<blockquote>📋 <b>ALL GROUPS ({len(groups)})</b>\n\n"+"\n".join(lines))
            if len(groups)>20: txt2+=f"\n...+{len(groups)-20} more"
            txt2+=f"\n\n⚡ @Felix_modz1</blockquote>"
            bot.send_message(uid, txt2, parse_mode='HTML')
            return

    # ── revoke premium ──
    if d=="confirm_revoke_premium" and is_admin(uid):
        bot.answer_callback_query(call.id,"💀 Revoking...")
        try:
            prem_users=c.execute("SELECT user_id FROM users WHERE is_premium=1").fetchall()
            for (puid,) in prem_users: c.execute("UPDATE users SET is_premium=0,premium_until=NULL,credits=? WHERE user_id=?",(FREE_CREDITS,puid))
            c.execute("UPDATE users SET credits=? WHERE is_premium=0",(FREE_CREDITS,))
            c.execute("DELETE FROM redeemed_premium"); c.execute("DELETE FROM premium_codes")
            c.execute("DELETE FROM redeemed_users"); c.execute("DELETE FROM redeem_codes"); conn.commit()
            count=len(prem_users)
            try: bot.edit_message_text(f"<blockquote>💀 <b>REVOKE DONE!</b>\n💎 {count} users premium removed.\n⚡ @Felix_modz1</blockquote>",call.message.chat.id,call.message.message_id,parse_mode='HTML')
            except: pass
        except Exception as e:
            try: bot.edit_message_text(f"<blockquote>❌ {_safe_err(e)}</blockquote>",call.message.chat.id,call.message.message_id,parse_mode='HTML')
            except: pass
        return

    if d=="cancel_revoke_premium":
        bot.answer_callback_query(call.id,"❌ Cancelled")
        try: bot.delete_message(call.message.chat.id,call.message.message_id)
        except: pass; return

    if d=="confirm_clear" and is_admin(uid):
        bot.answer_callback_query(call.id)
        c.execute("DELETE FROM search_history"); conn.commit()
        try: bot.edit_message_text("<blockquote>✅ History cleared!</blockquote>",call.message.chat.id,call.message.message_id,parse_mode='HTML')
        except: pass; return

    if d=="cancel_clear":
        bot.answer_callback_query(call.id,"❌ Cancelled")
        try: bot.delete_message(call.message.chat.id,call.message.message_id)
        except: pass; return

    # ── BOT MGMT callbacks — must be inside h_callback (True handler runs first) ──
    if d.startswith('botmgmt_') and uid==OWNER_ID:
        if d=="botmgmt_back":
            bot.answer_callback_query(call.id)
            bot.send_message(uid,"<blockquote>⚙️ <b>Admin P1</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML'); return

        if d=="botmgmt_panel_btns":
            bot.answer_callback_query(call.id)
            user_state[uid]='ADMIN_BTN_TOGGLE'
            bot.send_message(uid,
                f"<blockquote>{_F}\n🎛️ <b>ADMIN PANEL BUTTON TOGGLE</b>\n{_F}\n\n"
                f"🟢 = Visible (HIDE karo)\n🔴 = Hidden (SHOW karo)\n\n"
                f"Button dabao toggle karne ke liye:\n⚡ @Felix_modz1</blockquote>",
                reply_markup=kb_admin_btn_mgmt(),parse_mode='HTML'); return

        if d=="botmgmt_list":
            bot.answer_callback_query(call.id)
            clones=c.execute("SELECT id,user_id,bot_token,created_date,is_active FROM bot_clones ORDER BY created_date DESC").fetchall()
            txt2,mk2=_build_botmgmt_msg_mk(clones)
            try: bot.edit_message_text(txt2,call.message.chat.id,call.message.message_id,reply_markup=mk2,parse_mode='HTML')
            except: bot.send_message(uid,txt2,reply_markup=mk2,parse_mode='HTML')
            return

        if d.startswith('botmgmt_view_'):
            owner_uid=int(d.split('_')[2])
            row=c.execute("SELECT bot_token,created_date,is_active FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
            if not row: bot.answer_callback_query(call.id,"❌ Not found!"); return
            clone_token,created_date,is_active=row
            bot.answer_callback_query(call.id)
            clone_un=_get_clone_username(clone_token)
            u=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(owner_uid,)).fetchone()
            owner_un=(f"@{u[1]}" if u and u[1] else (u[0] if u and u[0] else f"ID:{owner_uid}"))
            status="🟢 ACTIVE" if is_active else "🔴 INACTIVE"
            cadmins=c.execute("SELECT admin_uid FROM clone_admins WHERE clone_owner_uid=?",(owner_uid,)).fetchall()
            adm_list="\n".join(f"  • <code>{a[0]}</code>" for a in cadmins) if cadmins else "  None"
            cfj=c.execute("SELECT chat_title,chat_url FROM clone_forced_channels WHERE clone_owner_uid=? AND is_active=1",(owner_uid,)).fetchall()
            fj_list="\n".join(f"  • {t} ({u2})" for t,u2 in cfj) if cfj else "  None"
            dtxt=(f"<blockquote>{_F}\n🤖 <b>CLONE BOT DETAIL</b>\n{_F}\n\n"
                  f"🤖 Bot: <b>{clone_un or 'Unknown'}</b>\n"
                  f"👤 Owner: {owner_un}\n🆔 Owner ID: <code>{owner_uid}</code>\n"
                  f"📅 Created: {created_date[:10]}\nStatus: <b>{status}</b>\n\n"
                  f"👑 Admins:\n{adm_list}\n\n🔗 Channels:\n{fj_list}\n\n"
                  f"{_F}\n⚡ @Felix_modz1</blockquote>")
            mk3=InlineKeyboardMarkup(row_width=2)
            tog_lbl="🔴 Turn OFF" if is_active else "🟢 Turn ON"
            tog_style="danger" if is_active else "success"
            mk3.row(_IKB(tog_lbl,style=tog_style,callback_data=f"botmgmt_toggle_{owner_uid}"),
                    _IKB("👑 Add Admin",style="primary",callback_data=f"botmgmt_addadmin_{owner_uid}"))
            mk3.add(_IKB("🔗 Add Channel",style="primary",callback_data=f"botmgmt_addfj_{owner_uid}"))
            mk3.add(_IKB("⬅️ Back to List",style="danger",callback_data="botmgmt_list"))
            try: bot.edit_message_text(dtxt,call.message.chat.id,call.message.message_id,reply_markup=mk3,parse_mode='HTML')
            except: bot.send_message(uid,dtxt,reply_markup=mk3,parse_mode='HTML')
            return

        if d.startswith('botmgmt_toggle_'):
            owner_uid=int(d.split('_')[2])
            row=c.execute("SELECT is_active,bot_token FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
            if not row: bot.answer_callback_query(call.id,"❌ Clone not found!"); return
            is_active,clone_token=row
            new_active=0 if is_active==1 else 1
            c.execute("UPDATE bot_clones SET is_active=? WHERE user_id=?",(new_active,owner_uid)); conn.commit()
            bot.answer_callback_query(call.id,f"✅ {'🟢 ON' if new_active else '🔴 OFF'}")
            if new_active==0:
                try: bot.send_message(owner_uid,"<blockquote>🔴 <b>Tera bot band kar diya gaya!</b>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
                except: pass
            else:
                try:
                    threading.Thread(target=_run_clone_bot,args=(clone_token,owner_uid),daemon=True).start()
                    bot.send_message(owner_uid,"<blockquote>🟢 <b>Tera bot wapas ON ho gaya!</b>\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
                except: pass
            # Refresh detail view
            row2=c.execute("SELECT bot_token,created_date,is_active FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
            if row2:
                ct2,cd2,ia2=row2; clone_un2=_get_clone_username(ct2)
                u2=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(owner_uid,)).fetchone()
                ou2=(f"@{u2[1]}" if u2 and u2[1] else (u2[0] if u2 and u2[0] else f"ID:{owner_uid}"))
                ca2=c.execute("SELECT admin_uid FROM clone_admins WHERE clone_owner_uid=?",(owner_uid,)).fetchall()
                al2="\n".join(f"  • <code>{a[0]}</code>" for a in ca2) if ca2 else "  None"
                cf2=c.execute("SELECT chat_title,chat_url FROM clone_forced_channels WHERE clone_owner_uid=? AND is_active=1",(owner_uid,)).fetchall()
                fl2="\n".join(f"  • {t} ({u3})" for t,u3 in cf2) if cf2 else "  None"
                st2="🟢 ACTIVE" if ia2 else "🔴 INACTIVE"
                t2=(f"<blockquote>{_F}\n🤖 <b>CLONE BOT DETAIL</b>\n{_F}\n\n"
                    f"🤖 Bot: <b>{clone_un2 or 'Unknown'}</b>\n👤 Owner: {ou2}\n"
                    f"🆔 Owner ID: <code>{owner_uid}</code>\n📅 Created: {cd2[:10]}\nStatus: <b>{st2}</b>\n\n"
                    f"👑 Admins:\n{al2}\n\n🔗 Channels:\n{fl2}\n\n{_F}\n⚡ @Felix_modz1</blockquote>")
                m3=InlineKeyboardMarkup(row_width=2)
                tl2="🔴 Turn OFF" if ia2 else "🟢 Turn ON"; ts2="danger" if ia2 else "success"
                m3.row(_IKB(tl2,style=ts2,callback_data=f"botmgmt_toggle_{owner_uid}"),
                       _IKB("👑 Add Admin",style="primary",callback_data=f"botmgmt_addadmin_{owner_uid}"))
                m3.add(_IKB("🔗 Add Channel",style="primary",callback_data=f"botmgmt_addfj_{owner_uid}"))
                m3.add(_IKB("⬅️ Back to List",style="danger",callback_data="botmgmt_list"))
                try: bot.edit_message_text(t2,call.message.chat.id,call.message.message_id,reply_markup=m3,parse_mode='HTML')
                except: pass
            return

        if d.startswith('botmgmt_addadmin_'):
            owner_uid=int(d.split('_')[2])
            bot.answer_callback_query(call.id)
            user_state[uid]={'state':'BOTMGMT_ADDADMIN','clone_owner':owner_uid}
            bot.send_message(uid,
                f"<blockquote>👑 <b>ADD ADMIN ON CLONE</b>\n\nClone Owner: <code>{owner_uid}</code>\n\n"
                f"Admin ka Telegram ID bhejo:\n(sirf numeric ID)\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

        if d.startswith('botmgmt_addfj_'):
            owner_uid=int(d.split('_')[2])
            bot.answer_callback_query(call.id)
            user_state[uid]={'state':'BOTMGMT_ADDFJ','clone_owner':owner_uid}
            bot.send_message(uid,
                f"<blockquote>🔗 <b>ADD CHANNEL TO CLONE BOT</b>\n\nClone Owner: <code>{owner_uid}</code>\n\n"
                f"📢 Channel ka t.me link bhejo:\n<code>https://t.me/channelname</code>\n\n"
                f"ℹ️ Bot ko channel admin banana zaruri nahi.\n"
                f"Clone ka owner ise remove nahi kar sakta!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

        bot.answer_callback_query(call.id); return

    bot.answer_callback_query(call.id)

def _get_clone_username(clone_token):
    """Clone bot ka @username Telegram API se fetch karo"""
    try:
        r=requests.get(f"https://api.telegram.org/bot{clone_token}/getMe",timeout=6)
        if r.status_code==200:
            res=r.json().get('result',{})
            un=res.get('username','')
            if un: return f"@{un}"
    except: pass
    return None

def _build_botmgmt_msg_mk(clones):
    """CLONE MGMT message + inline keyboard — fast list, no per-clone API call"""
    active=sum(1 for r in clones if r[4]==1); total=len(clones)
    txt=(f"<blockquote>{_orig_credit()}\n\n"
         f"🤖 <b>CLONE MANAGEMENT</b>\n\n"
         f"📊 Total Clones: <b>{total}</b>\n"
         f"🟢 Active: <b>{active}</b> | 🔴 Off: <b>{total-active}</b>\n\n"
         f"{_orig_credit()}</blockquote>")
    mk=InlineKeyboardMarkup(row_width=1)
    for row in clones[:15]:
        cid_db,owner_uid,clone_token,created_date,is_active=row
        status="🟢" if is_active else "🔴"
        # Owner name DB se — no slow API call
        u=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(owner_uid,)).fetchone()
        owner_name=(f"@{u[1]}" if u and u[1] else (u[0][:15] if u and u[0] else f"ID:{owner_uid}"))
        # Token ka short preview
        tok_preview=clone_token[:10]+"..."
        lbl=f"{status} {owner_name} | {tok_preview}"
        mk.add(_IKB(lbl, style="success" if is_active else "danger",
                   callback_data=f"botmgmt_view_{owner_uid}"))
    mk.add(_IKB("🎛️ ADMIN PANEL BUTTONS",style="primary",callback_data="botmgmt_panel_btns"))
    mk.add(_IKB("🔙 BACK",style="danger",callback_data="botmgmt_back"))
    return txt, mk

@bot.message_handler(func=lambda m: m.text=="🤖 CLONE MGMT" and is_admin(m.from_user.id) and not _IS_CLONE)
def h_bot_mgmt(m):
    uid=m.from_user.id
    if uid!=OWNER_ID:
        bot.reply_to(m,"<blockquote>❌ Sirf main owner!</blockquote>",parse_mode='HTML'); return
    clones=c.execute("SELECT id,user_id,bot_token,created_date,is_active FROM bot_clones ORDER BY created_date DESC").fetchall()
    txt,mk=_build_botmgmt_msg_mk(clones)
    bot.send_message(m.chat.id,txt,reply_markup=mk,parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('botmgmt_'))
def h_botmgmt_cb(call):
    uid=call.from_user.id
    if uid!=OWNER_ID:
        bot.answer_callback_query(call.id,"❌ Sirf owner!"); return
    d=call.data

    # ── Back to admin ──
    if d=="botmgmt_back":
        bot.answer_callback_query(call.id)
        bot.send_message(uid,"<blockquote>⚙️ <b>Admin P1</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML'); return

    # ── Admin panel button toggle page ──
    if d=="botmgmt_panel_btns":
        bot.answer_callback_query(call.id)
        user_state[uid]='ADMIN_BTN_TOGGLE'
        bot.send_message(uid,
            f"<blockquote>{_F}\n🎛️ <b>ADMIN PANEL BUTTON TOGGLE</b>\n{_F}\n\n"
            f"🟢 = Visible (HIDE karo)\n🔴 = Hidden (SHOW karo)\n\n"
            f"Button dabao toggle karne ke liye:\n⚡ @Felix_modz1</blockquote>",
            reply_markup=kb_admin_btn_mgmt(),parse_mode='HTML'); return

    # ── View single clone detail ──
    if d.startswith('botmgmt_view_'):
        owner_uid=int(d[len('botmgmt_view_'):])
        row=c.execute("SELECT bot_token,created_date,is_active FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        if not row: bot.answer_callback_query(call.id,"❌ Not found!"); return
        clone_token,created_date,is_active=row
        bot.answer_callback_query(call.id)
        clone_un=_get_clone_username(clone_token)
        u=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(owner_uid,)).fetchone()
        owner_un=(u[1] and f"@{u[1]}") or (u[0] or f"ID:{owner_uid}") if u else f"ID:{owner_uid}"
        status="🟢 ACTIVE" if is_active else "🔴 INACTIVE"
        # Clone admins list
        cadmins=c.execute("SELECT admin_uid FROM clone_admins WHERE clone_owner_uid=?",(owner_uid,)).fetchall()
        adm_list="\n".join(f"  • <code>{a[0]}</code>" for a in cadmins) if cadmins else "  None"
        # Clone forced channels list
        cfj=c.execute("SELECT chat_title,chat_url FROM clone_forced_channels WHERE clone_owner_uid=? AND is_active=1",(owner_uid,)).fetchall()
        fj_list="\n".join(f"  • {t} {u}" for t,u in cfj) if cfj else "  None"
        txt=(f"<blockquote>{_orig_credit()}\n\n"
             f"🤖 <b>CLONE BOT DETAIL</b>\n\n"
             f"🤖 Bot: <b>{clone_un or 'Unknown'}</b>\n"
             f"👤 Owner: {owner_un}\n"
             f"🆔 Owner ID: <code>{owner_uid}</code>\n"
             f"📅 Created: {created_date[:10]}\n"
             f"Status: <b>{status}</b>\n\n"
             f"👑 Admins:\n{adm_list}\n\n"
             f"🔗 Forced Channels:\n{fj_list}\n\n"
             f"{_orig_credit()}</blockquote>")
        mk=InlineKeyboardMarkup(row_width=2)
        tog_lbl="🔴 Turn OFF" if is_active else "🟢 Turn ON"
        tog_style="danger" if is_active else "success"
        mk.row(_IKB(tog_lbl,style=tog_style,callback_data=f"botmgmt_toggle_{owner_uid}"),
               _IKB("👑 Add Admin",style="primary",callback_data=f"botmgmt_addadmin_{owner_uid}"))
        mk.add(_IKB("🔗 Add Force Join",style="primary",callback_data=f"botmgmt_addfj_{owner_uid}"))
        mk.add(_IKB("🗑️ REMOVE CLONE",style="danger",callback_data=f"botmgmt_remove_{owner_uid}"))
        mk.add(_IKB("⬅️ Back to List",style="danger",callback_data="botmgmt_list"))
        try: bot.edit_message_text(txt,call.message.chat.id,call.message.message_id,reply_markup=mk,parse_mode='HTML')
        except: bot.send_message(uid,txt,reply_markup=mk,parse_mode='HTML')
        return

    # ── Back to clone list ──
    if d=="botmgmt_list":
        bot.answer_callback_query(call.id)
        clones=c.execute("SELECT id,user_id,bot_token,created_date,is_active FROM bot_clones ORDER BY created_date DESC").fetchall()
        txt,mk=_build_botmgmt_msg_mk(clones)
        try: bot.edit_message_text(txt,call.message.chat.id,call.message.message_id,reply_markup=mk,parse_mode='HTML')
        except: bot.send_message(uid,txt,reply_markup=mk,parse_mode='HTML')
        return

    # ── Toggle ON/OFF ──
    if d.startswith('botmgmt_toggle_'):
        owner_uid=int(d[len('botmgmt_toggle_'):])
        row=c.execute("SELECT is_active,bot_token FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        if not row: bot.answer_callback_query(call.id,"❌ Clone not found!"); return
        is_active,clone_token=row
        new_active=0 if is_active==1 else 1
        c.execute("UPDATE bot_clones SET is_active=? WHERE user_id=?",(new_active,owner_uid)); conn.commit()
        status="🟢 ACTIVE" if new_active else "🔴 INACTIVE"
        bot.answer_callback_query(call.id,f"✅ {status}")
        if new_active==0:
            try: bot.send_message(owner_uid,
                f"<blockquote>🔴 <b>Tera clone bot band kar diya gaya!</b>\nOwner ne disable kiya.\n⚡ @Felix_modz1</blockquote>",
                parse_mode='HTML')
            except: pass
        else:
            try:
                threading.Thread(target=_run_clone_bot,args=(clone_token,owner_uid),daemon=True).start()
                bot.send_message(owner_uid,
                    f"<blockquote>🟢 <b>Tera clone bot wapas ON ho gaya!</b>\n⚡ @Felix_modz1</blockquote>",
                    parse_mode='HTML')
            except: pass
        # Refresh view
        row2=c.execute("SELECT bot_token,created_date,is_active FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        if row2:
            clone_token2,created_date2,ia2=row2
            clone_un2=_get_clone_username(clone_token2)
            u2=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(owner_uid,)).fetchone()
            owner_un2=(u2[1] and f"@{u2[1]}") or (u2[0] or f"ID:{owner_uid}") if u2 else f"ID:{owner_uid}"
            cadmins2=c.execute("SELECT admin_uid FROM clone_admins WHERE clone_owner_uid=?",(owner_uid,)).fetchall()
            adm_list2="\n".join(f"  • <code>{a[0]}</code>" for a in cadmins2) if cadmins2 else "  None"
            cfj2=c.execute("SELECT chat_title,chat_url FROM clone_forced_channels WHERE clone_owner_uid=? AND is_active=1",(owner_uid,)).fetchall()
            fj_list2="\n".join(f"  • {t} {u}" for t,u in cfj2) if cfj2 else "  None"
            st2="🟢 ACTIVE" if ia2 else "🔴 INACTIVE"
            txt2=(f"<blockquote>{_orig_credit()}\n\n🤖 <b>CLONE BOT DETAIL</b>\n\n"
                  f"🤖 Bot: <b>{clone_un2 or 'Unknown'}</b>\n"
                  f"👤 Owner: {owner_un2}\n🆔 Owner ID: <code>{owner_uid}</code>\n"
                  f"📅 Created: {created_date2[:10]}\nStatus: <b>{st2}</b>\n\n"
                  f"👑 Admins:\n{adm_list2}\n\n🔗 Forced Channels:\n{fj_list2}\n\n"
                  f"{_F}\n⚡ @Felix_modz1</blockquote>")
            mk2=InlineKeyboardMarkup(row_width=2)
            tl2="🔴 Turn OFF" if ia2 else "🟢 Turn ON"
            ts2="danger" if ia2 else "success"
            mk2.row(_IKB(tl2,style=ts2,callback_data=f"botmgmt_toggle_{owner_uid}"),
                    _IKB("👑 Add Admin",style="primary",callback_data=f"botmgmt_addadmin_{owner_uid}"))
            mk2.add(_IKB("🔗 Add Force Join",style="primary",callback_data=f"botmgmt_addfj_{owner_uid}"))
            mk2.add(_IKB("🗑️ REMOVE CLONE",style="danger",callback_data=f"botmgmt_remove_{owner_uid}"))
            mk2.add(_IKB("⬅️ Back to List",style="danger",callback_data="botmgmt_list"))
            try: bot.edit_message_text(txt2,call.message.chat.id,call.message.message_id,reply_markup=mk2,parse_mode='HTML')
            except: pass
        return

    # ── Add Admin on clone ──
    if d.startswith('botmgmt_addadmin_'):
        owner_uid=int(d[len('botmgmt_addadmin_'):])
        bot.answer_callback_query(call.id)
        user_state[uid]={'state':'BOTMGMT_ADDADMIN','clone_owner':owner_uid}
        bot.send_message(uid,
            f"<blockquote>👑 <b>ADD ADMIN ON CLONE</b>\n\n"
            f"Clone Owner: <code>{owner_uid}</code>\n\n"
            f"Admin ka Telegram ID bhejo:\n"
            f"(sirf numeric ID)\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

    # ── Add Force Join on clone ──
    if d.startswith('botmgmt_addfj_'):
        owner_uid=int(d[len('botmgmt_addfj_'):])
        bot.answer_callback_query(call.id)
        user_state[uid]={'state':'BOTMGMT_ADDFJ','clone_owner':owner_uid}
        bot.send_message(uid,
            f"<blockquote>🔗 <b>ADD CHANNEL TO CLONE BOT</b>\n\n"
            f"Clone Owner: <code>{owner_uid}</code>\n\n"
            f"📢 Channel ka t.me link bhejo:\n"
            f"<code>https://t.me/channelname</code>\n\n"
            f"ℹ️ Bot ko channel admin banana zaruri nahi.\n"
            f"Clone ka owner ise remove nahi kar sakta!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

    # ── Remove Clone — confirm ──
    if d.startswith('botmgmt_remove_'):
        owner_uid=int(d[len('botmgmt_remove_'):])
        bot.answer_callback_query(call.id)
        row=c.execute("SELECT bot_token,created_date FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        if not row: bot.answer_callback_query(call.id,"❌ Clone not found!"); return
        clone_token,created_date=row
        clone_un=_get_clone_username(clone_token)
        u=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(owner_uid,)).fetchone()
        owner_un=(u[1] and f"@{u[1]}") or (u[0] or f"ID:{owner_uid}") if u else f"ID:{owner_uid}"
        txt_conf=(f"<blockquote>{_F}\n"
                  f"🗑️ <b>REMOVE CLONE — CONFIRM?</b>\n{_F}\n\n"
                  f"🤖 Bot: <b>{clone_un or 'Unknown'}</b>\n"
                  f"👤 Owner: {owner_un}\n"
                  f"🆔 Owner ID: <code>{owner_uid}</code>\n"
                  f"📅 Created: {created_date[:10]}\n\n"
                  f"⚠️ Ye clone permanently delete ho jaayega!\n"
                  f"Clone ka saara data (admins, channels) bhi hata diya jaayega.\n\n"
                  f"{_F}\n⚡ @Felix_modz1</blockquote>")
        mk_conf=InlineKeyboardMarkup(row_width=2)
        mk_conf.row(_IKB("✅ HAAN, REMOVE KRO",style="danger",callback_data=f"botmgmt_confirmremove_{owner_uid}"),
                    _IKB("❌ CANCEL",style="success",callback_data=f"botmgmt_view_{owner_uid}"))
        try: bot.edit_message_text(txt_conf,call.message.chat.id,call.message.message_id,reply_markup=mk_conf,parse_mode='HTML')
        except: bot.send_message(uid,txt_conf,reply_markup=mk_conf,parse_mode='HTML')
        return

    # ── Remove Clone — confirmed delete ──
    if d.startswith('botmgmt_confirmremove_'):
        owner_uid=int(d[len('botmgmt_confirmremove_'):])
        bot.answer_callback_query(call.id,"🗑️ Removing...")
        row=c.execute("SELECT bot_token FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        clone_token=row[0] if row else None
        # Stop clone bot agar chal raha ho
        if clone_token:
            try:
                _crm=telebot.TeleBot(clone_token)
                _crm.remove_webhook()
                _crm.send_message(owner_uid,
                    f"<blockquote>🗑️ <b>Tera clone bot hata diya gaya!</b>\nMain owner ne remove kar diya.\n⚡ @Felix_modz1</blockquote>",
                    parse_mode='HTML')
            except: pass
        # DB se saara data delete karo
        try:
            c.execute("DELETE FROM bot_clones WHERE user_id=?",(owner_uid,))
            c.execute("DELETE FROM clone_admins WHERE clone_owner_uid=?",(owner_uid,))
            c.execute("DELETE FROM clone_forced_channels WHERE clone_owner_uid=?",(owner_uid,))
            conn.commit()
        except Exception as e:
            bot.send_message(uid,f"<blockquote>❌ DB Error: {_safe_err(e)}</blockquote>",parse_mode='HTML'); return
        # Referral coins reset (optional — nahi karte, owner ka record rahe)
        txt_done=(f"<blockquote>{_F}\n"
                  f"✅ <b>CLONE REMOVED!</b>\n{_F}\n\n"
                  f"🆔 Owner ID: <code>{owner_uid}</code>\n"
                  f"🗑️ Clone bot + admins + channels — sab delete.\n\n"
                  f"{_F}\n⚡ @Felix_modz1</blockquote>")
        clones=c.execute("SELECT id,user_id,bot_token,created_date,is_active FROM bot_clones ORDER BY created_date DESC").fetchall()
        txt2,mk2=_build_botmgmt_msg_mk(clones)
        try: bot.edit_message_text(txt_done,call.message.chat.id,call.message.message_id,parse_mode='HTML')
        except: pass
        bot.send_message(uid,txt2,reply_markup=mk2,parse_mode='HTML')
        return

@bot.message_handler(func=lambda m: m.chat.type=='private' and is_admin(m.from_user.id) and not _IS_CLONE and user_state.get(m.from_user.id)=='ADMIN_BTN_TOGGLE' and m.text and (m.text.startswith("🟢 ") or m.text.startswith("🔴 ")))
def h_admin_btn_toggle(m):
    """Admin panel button toggle handler"""
    uid=m.from_user.id
    if uid!=OWNER_ID: return
    txt=m.text
    # Extract button name: "🟢 BUTTON NAME — HIDE" or "🔴 BUTTON NAME — SHOW"
    match=re.match(r'^[🟢🔴] (.+?) — (HIDE|SHOW)$', txt)
    if not match:
        if txt=="🔙 BACK TO ADMIN":
            user_state[uid]='ADMIN_PANEL'
            bot.send_message(uid,"<blockquote>⚙️ <b>Admin P1</b></blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML')
            return
        return
    btn_name=match.group(1); action=match.group(2)
    new_visible=toggle_admin_btn(btn_name,uid)
    status="🟢 VISIBLE" if new_visible else "🔴 HIDDEN"
    bot.reply_to(m,f"<blockquote>✅ <b>{btn_name}</b>\n{status}\n⚡ @Felix_modz1</blockquote>",
                 reply_markup=kb_admin_btn_mgmt(),parse_mode='HTML')

@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     isinstance(user_state.get(m.from_user.id),dict) and
                     user_state.get(m.from_user.id,{}).get('state','').startswith('BOTMGMT_'))
def h_botmgmt_state(m):
    """Handle BOTMGMT input states: add admin / add force join on clone"""
    uid=m.from_user.id; st=user_state.get(uid,{}); sname=st.get('state','')
    clone_owner=st.get('clone_owner')
    txt=m.text.strip() if m.text else ""

    # ── Add Admin on clone ──
    if sname=='BOTMGMT_ADDADMIN':
        try:
            admin_uid=int(txt)
        except:
            bot.reply_to(m,"<blockquote>❌ Valid numeric Telegram ID bhejo!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        # DB me save karo
        try:
            c.execute("INSERT OR IGNORE INTO clone_admins(clone_owner_uid,admin_uid,added_by,added_date) VALUES(?,?,?,?)",
                     (clone_owner,admin_uid,uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        except Exception as e:
            bot.reply_to(m,f"<blockquote>❌ Error: {_safe_err(e)}</blockquote>",parse_mode='HTML'); return
        user_state[uid]={}
        bot.reply_to(m,
            f"<blockquote>{_F}\n"
            f"✅ <b>ADMIN ADDED!</b>\n"
            f"{_F}\n\n"
            f"👑 Admin ID: <code>{admin_uid}</code>\n"
            f"🤖 Clone Owner: <code>{clone_owner}</code>\n\n"
            f"Ab ye user clone bot me admin hoga.\n"
            f"{_F}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        # Clone bot ko notify karo (agar token mile)
        crow=c.execute("SELECT bot_token FROM bot_clones WHERE user_id=?",(clone_owner,)).fetchone()
        if crow:
            try:
                import telebot as _tb_adm
                _cb=_tb_adm.TeleBot(crow[0])
                _cb.send_message(admin_uid,
                    f"<blockquote>👑 <b>Admin Access!</b>\nAapko <code>{clone_owner}</code> ke clone bot pe admin access diya gaya hai!\n⚡ @Felix_modz1</blockquote>",
                    parse_mode='HTML')
            except: pass
        return

    # ── Add Force Join on clone ──
    if sname=='BOTMGMT_ADDFJ':
        if not txt.startswith('https://t.me/'):
            bot.reply_to(m,"<blockquote>❌ Valid t.me link bhejo!\nExample: https://t.me/channelname\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        # Channel title fetch karo — bot admin nahi hai to bhi title milega
        chat_title="Channel"; chat_id_str=txt
        try:
            if '+' not in txt:
                un=txt.split('t.me/')[1].strip('/')
                try:
                    ch=bot.get_chat(f"@{un}")
                    chat_title=ch.title or un
                    chat_id_str=str(ch.id)
                except:
                    # Bot member nahi — username hi title banao
                    chat_title=un
                    chat_id_str=f"@{un}"
            else:
                chat_title="Private Channel"
                chat_id_str=txt
        except: pass
        try:
            c.execute("INSERT INTO clone_forced_channels(clone_owner_uid,chat_id,chat_title,chat_url,added_by,added_date,is_active,is_fake) VALUES(?,?,?,?,?,?,1,0)",
                     (clone_owner,chat_id_str,chat_title,txt,uid,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit()
        except Exception as e:
            bot.reply_to(m,f"<blockquote>❌ Error: {_safe_err(e)}</blockquote>",parse_mode='HTML'); return
        user_state[uid]={}
        bot.reply_to(m,
            f"<blockquote>{_F}\n"
            f"✅ <b>CHANNEL ADDED TO CLONE!</b>\n"
            f"{_F}\n\n"
            f"🔗 Channel: <b>{chat_title}</b>\n"
            f"🤖 Clone Owner: <code>{clone_owner}</code>\n\n"
            f"ℹ️ Ye channel clone bot ke force join list me add ho gaya.\n"
            f"Clone ka owner ise remove nahi kar sakta!\n"
            f"{_F}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        return

# ── Group Credits input handler ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.chat.type=='private' and is_admin(m.from_user.id) and
                     isinstance(user_state.get(m.from_user.id),dict) and
                     user_state.get(m.from_user.id,{}).get('state','') in ('GRP_ADDCR','GRP_RMCR','GRPCTRL_ADD_CREDITS','GRPCTRL_REM_CREDITS'))
def h_grp_cr_input(m):
    uid=m.from_user.id; st=user_state.get(uid,{}); sname=st.get('state','')
    gid=st.get('gid'); msg_id=st.get('msg_id'); chat_id_saved=st.get('chat_id')
    txt=m.text.strip() if m.text else ""
    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>❌ Cancelled!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    try:
        amount=int(txt)
        if amount<=0: raise ValueError
    except:
        bot.reply_to(m,"<blockquote>❌ Valid number bhejo! (e.g. 50)\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
    user_state[uid]=S_NONE

    # ── ALL GROUPS control ──
    if sname=='GRPCTRL_ADD_CREDITS':
        groups=get_all_groups()
        for gid2,_ in groups: add_group_credits_fn(gid2,amount)
        bot.reply_to(m,
            f"<blockquote>✅ <b>+{amount} Credits Added!</b>\n"
            f"👥 All {len(groups)} groups ko {amount} credits mile!\n"
            f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        return
    if sname=='GRPCTRL_REM_CREDITS':
        groups=get_all_groups()
        for gid2,_ in groups: rem_group_credits_fn(gid2,amount)
        bot.reply_to(m,
            f"<blockquote>✅ <b>-{amount} Credits Removed!</b>\n"
            f"👥 All {len(groups)} groups se {amount} credits hate!\n"
            f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        return

    if sname=='GRP_ADDCR':
        add_group_credits_fn(gid,amount)
        g=get_group(gid)
        new_cr=safe_g(g,4) if g else "?"
        bot.reply_to(m,
            f"<blockquote>✅ <b>+{amount} Credits Added!</b>\n"
            f"🆔 Group: <code>{gid}</code>\n"
            f"💰 New Balance: <code>{new_cr}</code>\n"
            f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
    else:
        rem_group_credits_fn(gid,amount)
        g=get_group(gid)
        new_cr=safe_g(g,4) if g else "?"
        bot.reply_to(m,
            f"<blockquote>✅ <b>-{amount} Credits Removed!</b>\n"
            f"🆔 Group: <code>{gid}</code>\n"
            f"💰 New Balance: <code>{new_cr}</code>\n"
            f"⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
    # Group detail view refresh karo
    if chat_id_saved and msg_id:
        try: refresh_group_msg(chat_id_saved,msg_id,gid)
        except: pass

# ── FORCE REMOVE CLONE removed — ab CLONE MGMT se karo ──

def _auto_restart_clones():
    """Bot restart ke baad OWNER ke bot pe saare band clone ka full details bhejo.
    Redeploy ya Delete ka option bhi do. Clone owners ko koi msg nahi."""
    if _IS_CLONE: return
    try:
        active_clones = c.execute(
            "SELECT user_id, bot_token FROM bot_clones WHERE is_active=1"
        ).fetchall()
        if not active_clones:
            print("[CLONE] No active clones to notify.")
            return
        print(f"[CLONE] Bot restart — {len(active_clones)} clone(s) band hue, owner ko notify karo...")

        for owner_uid, clone_token in active_clones:
            # is_active=0 kar do — bot band hai
            try:
                c.execute("UPDATE bot_clones SET is_active=0 WHERE user_id=?", (owner_uid,))
                conn.commit()
            except: pass

            # Owner ka naam/username DB se
            try:
                _ur=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(owner_uid,)).fetchone()
                _owner_name=(_ur[0] or f"User") if _ur else "User"
                _owner_un=(f"@{_ur[1]}" if _ur and _ur[1] else f"ID:{owner_uid}") if _ur else f"ID:{owner_uid}"
            except:
                _owner_name="User"; _owner_un=f"ID:{owner_uid}"

            # Clone bot ka username (fast try, skip if slow)
            _clone_un="Unknown"
            try:
                _cr=requests.get(f"https://api.telegram.org/bot{clone_token}/getMe",timeout=5)
                if _cr.status_code==200:
                    _cun=_cr.json().get('result',{}).get('username','')
                    if _cun: _clone_un=f"@{_cun}"
            except: pass

            # Clone ke admins
            try:
                _cadms=c.execute("SELECT admin_uid FROM clone_admins WHERE clone_owner_uid=?",(owner_uid,)).fetchall()
                _adm_txt=", ".join(f"<code>{a[0]}</code>" for a in _cadms) if _cadms else "None"
            except: _adm_txt="None"

            # Clone ke force join channels
            try:
                _cfjs=c.execute("SELECT chat_title FROM clone_forced_channels WHERE clone_owner_uid=? AND is_active=1",(owner_uid,)).fetchall()
                _fj_txt=", ".join(t[0] for t in _cfjs) if _cfjs else "None"
            except: _fj_txt="None"

            _tok_preview=clone_token  # pura token
            _now_t=_now_ist()

            # Inline buttons: Redeploy, Edit, Delete
            mk_rst=InlineKeyboardMarkup(row_width=2)
            mk_rst.row(
                _IKB("🔄 REDEPLOY",style="success",callback_data=f"rst_redeploy_{owner_uid}"),
                _IKB("🗑️ DELETE",style="danger",callback_data=f"rst_delete_{owner_uid}")
            )
            mk_rst.add(_IKB("✏️ EDIT (Token/Owner)",style="primary",callback_data=f"rst_edit_{owner_uid}"))

            _msg=(
                f"<blockquote>━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ <b>BOT RESTART — CLONE BAND HUA</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 <b>Clone Bot :</b> {_clone_un}\n"
                f"🔑 <b>Token     :</b> <code>{_tok_preview}</code>\n\n"
                f"👤 <b>Owner     :</b> {_owner_name} ({_owner_un})\n"
                f"🆔 <b>Owner ID  :</b> <code>{owner_uid}</code>\n\n"
                f"👑 <b>Admins    :</b> {_adm_txt}\n"
                f"🔗 <b>Channels  :</b> {_fj_txt}\n\n"
                f"🕒 <b>Time      :</b> {_now_t}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⬇️ Kya karna hai is clone ke saath?\n"
                f"━━━━━━━━━━━━━━━━━━━━━━</blockquote>"
            )
            try:
                bot.send_message(OWNER_ID, _msg, reply_markup=mk_rst, parse_mode='HTML')
                print(f"[CLONE] Owner ko notified: owner_uid={owner_uid} clone={_clone_un}")
            except Exception as e:
                print(f"[CLONE] Owner notify failed: {_safe_err(e)}")

    except Exception as e:
        print(f"[CLONE] Auto-notify error: {_safe_err(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('rst_'))
def h_rst_callback(call):
    """Restart recovery — redeploy / edit / delete clone"""
    uid=call.from_user.id
    if uid!=OWNER_ID:
        bot.answer_callback_query(call.id,"❌ Sirf main owner!"); return
    d=call.data

    # ── REDEPLOY ──
    if d.startswith('rst_redeploy_'):
        try: owner_uid=int(d[len('rst_redeploy_'):])
        except: bot.answer_callback_query(call.id,"❌ Invalid!"); return
        bot.answer_callback_query(call.id,"🔄 Redeploying...")
        row=c.execute("SELECT bot_token FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        if not row:
            try: bot.edit_message_text(
                f"<blockquote>❌ Clone DB mein nahi mila!\nOwner ID: <code>{owner_uid}</code>\n⚡ @Felix_modz1</blockquote>",
                call.message.chat.id,call.message.message_id,parse_mode='HTML')
            except: bot.send_message(uid,f"<blockquote>❌ Clone not found!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
            return
        clone_token=row[0]
        # Token validate karo
        try:
            _rv=requests.get(f"https://api.telegram.org/bot{clone_token}/getMe",timeout=10)
            _rv_ok=_rv.status_code==200 and _rv.json().get('ok')
            _cun=_rv.json().get('result',{}).get('username','?') if _rv_ok else None
        except: _rv_ok=False; _cun=None
        if not _rv_ok:
            # Token invalid — EDIT button dikhao
            mk_inv=InlineKeyboardMarkup(row_width=1)
            mk_inv.add(_IKB("✏️ NAYA TOKEN DALO",style="primary",callback_data=f"rst_edit_{owner_uid}"))
            mk_inv.add(_IKB("🗑️ DELETE",style="danger",callback_data=f"rst_delete_{owner_uid}"))
            try: bot.edit_message_text(
                f"<blockquote>❌ <b>Token invalid ya expired!</b>\n\n"
                f"Owner ID: <code>{owner_uid}</code>\n\n"
                f"Naya token dalo ya clone delete karo.\n"
                f"⚡ @Felix_modz1</blockquote>",
                call.message.chat.id,call.message.message_id,reply_markup=mk_inv,parse_mode='HTML')
            except: bot.send_message(uid,
                f"<blockquote>❌ Token invalid!\nOwner ID: <code>{owner_uid}</code>\n⚡ @Felix_modz1</blockquote>",
                reply_markup=mk_inv,parse_mode='HTML')
            return
        # Deploy karo
        c.execute("UPDATE bot_clones SET is_active=1 WHERE user_id=?",(owner_uid,)); conn.commit()
        threading.Thread(target=_run_clone_bot,args=(clone_token,owner_uid),daemon=True).start()
        try: bot.edit_message_text(
            f"<blockquote>✅ <b>REDEPLOY HO GAYA!</b>\n\n"
            f"🤖 Bot: @{_cun}\n"
            f"👤 Owner ID: <code>{owner_uid}</code>\n\n"
            f"🟢 Clone wapas chal raha hai!\n"
            f"⚡ @Felix_modz1</blockquote>",
            call.message.chat.id,call.message.message_id,parse_mode='HTML')
        except: bot.send_message(uid,
            f"<blockquote>✅ Redeploy hua! @{_cun}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
        return

    # ── EDIT (Token / Owner username change) ──
    if d.startswith('rst_edit_'):
        try: owner_uid=int(d[len('rst_edit_'):])
        except: bot.answer_callback_query(call.id,"❌ Invalid!"); return
        bot.answer_callback_query(call.id)
        row=c.execute("SELECT bot_token FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        if not row:
            bot.send_message(uid,f"<blockquote>❌ Clone not found!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        tok_prev=row[0][:20]+"..."
        # Sub-menu dikhao
        mk_edit=InlineKeyboardMarkup(row_width=1)
        mk_edit.add(_IKB("🔑 Token Change Karo",style="primary",callback_data=f"rst_chtoken_{owner_uid}"))
        mk_edit.add(_IKB("👤 Owner Change Karo (Username/ID)",style="primary",callback_data=f"rst_chowner_{owner_uid}"))
        mk_edit.add(_IKB("🔙 Cancel",style="danger",callback_data=f"rst_cancel_{owner_uid}"))
        try: bot.edit_message_text(
            f"<blockquote>━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✏️ <b>EDIT CLONE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Owner ID: <code>{owner_uid}</code>\n"
            f"🔑 Token: <code>{tok_prev}</code>\n\n"
            f"Kya change karna hai?\n"
            f"━━━━━━━━━━━━━━━━━━━━━━</blockquote>",
            call.message.chat.id,call.message.message_id,reply_markup=mk_edit,parse_mode='HTML')
        except: bot.send_message(uid,
            f"<blockquote>✏️ <b>EDIT CLONE</b>\nOwner: <code>{owner_uid}</code>\nKya change karna hai?</blockquote>",
            reply_markup=mk_edit,parse_mode='HTML')
        return

    # ── CHANGE TOKEN ──
    if d.startswith('rst_chtoken_'):
        try: owner_uid=int(d[len('rst_chtoken_'):])
        except: bot.answer_callback_query(call.id,"❌ Invalid!"); return
        bot.answer_callback_query(call.id)
        user_state[uid]={'state':'RST_NEW_TOKEN','owner_uid':owner_uid,'msg_id':call.message.message_id,'chat_id':call.message.chat.id}
        bot.send_message(uid,
            f"<blockquote>🔑 <b>NAYA TOKEN BHEJO</b>\n\n"
            f"Owner ID: <code>{owner_uid}</code>\n\n"
            f"Bot ka naya token bhejo:\n"
            f"Example: <code>1234567890:ABCdef...</code>\n\n"
            f"Cancel ke liye /cancel</blockquote>",parse_mode='HTML')
        return

    # ── CHANGE OWNER ──
    if d.startswith('rst_chowner_'):
        try: owner_uid=int(d[len('rst_chowner_'):])
        except: bot.answer_callback_query(call.id,"❌ Invalid!"); return
        bot.answer_callback_query(call.id)
        user_state[uid]={'state':'RST_NEW_OWNER','owner_uid':owner_uid,'msg_id':call.message.message_id,'chat_id':call.message.chat.id}
        bot.send_message(uid,
            f"<blockquote>👤 <b>NAYA OWNER BHEJO</b>\n\n"
            f"Purana Owner ID: <code>{owner_uid}</code>\n\n"
            f"Naye owner ka <b>User ID ya @username</b> bhejo:\n"
            f"• ID: <code>123456789</code>\n"
            f"• Username: <code>@rahul123</code>\n\n"
            f"Cancel ke liye /cancel</blockquote>",parse_mode='HTML')
        return

    # ── CANCEL ──
    if d.startswith('rst_cancel_'):
        bot.answer_callback_query(call.id,"❌ Cancelled")
        try: bot.delete_message(call.message.chat.id,call.message.message_id)
        except: pass
        return

    # ── DELETE ──
    if d.startswith('rst_delete_'):
        try: owner_uid=int(d[len('rst_delete_'):])
        except: bot.answer_callback_query(call.id,"❌ Invalid!"); return
        bot.answer_callback_query(call.id,"🗑️ Deleting...")
        row=c.execute("SELECT bot_token FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
        clone_token=row[0] if row else None
        # Clone owner ko notify
        if clone_token:
            try:
                import telebot as _tb_rst
                _crst=_tb_rst.TeleBot(clone_token,threaded=False)
                _crst.send_message(owner_uid,
                    f"<blockquote>🗑️ <b>Tera clone bot permanently delete kar diya gaya!</b>\n"
                    f"Main owner ne remove kiya.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML')
            except: pass
        # Kill + delete
        try: _kill_old_clone(owner_uid)
        except: pass
        try: _delete_clone_files(owner_uid)
        except: pass
        try:
            c.execute("DELETE FROM bot_clones WHERE user_id=?",(owner_uid,))
            c.execute("DELETE FROM clone_admins WHERE clone_owner_uid=?",(owner_uid,))
            c.execute("DELETE FROM clone_forced_channels WHERE clone_owner_uid=?",(owner_uid,))
            conn.commit()
        except: pass
        try: bot.edit_message_text(
            f"<blockquote>🗑️ <b>CLONE DELETE HO GAYA!</b>\n\n"
            f"👤 Owner ID: <code>{owner_uid}</code>\n"
            f"🗑️ Bot + Admins + Channels — sab remove.\n\n"
            f"⚡ @Felix_modz1</blockquote>",
            call.message.chat.id,call.message.message_id,parse_mode='HTML')
        except: bot.send_message(uid,
            f"<blockquote>🗑️ Clone deleted! Owner: <code>{owner_uid}</code>\n⚡ @Felix_modz1</blockquote>",
            parse_mode='HTML')
        return

    bot.answer_callback_query(call.id)

# ── RST EDIT state handler — naya token / naya owner input ──
@bot.message_handler(func=lambda m: m.chat.type=='private' and m.from_user.id==OWNER_ID and
                     isinstance(user_state.get(m.from_user.id),dict) and
                     user_state.get(m.from_user.id,{}).get('state','') in ('RST_NEW_TOKEN','RST_NEW_OWNER'))
def h_rst_edit_input(m):
    uid=m.from_user.id; st=user_state.get(uid,{}); sname=st.get('state','')
    owner_uid=st.get('owner_uid'); txt=m.text.strip() if m.text else ""

    if txt.lower() in ['cancel','/cancel']:
        user_state[uid]=S_NONE
        bot.send_message(uid,"<blockquote>❌ Cancelled!</blockquote>",reply_markup=kb_admin_p1(),parse_mode='HTML'); return

    # ── Naya Token ──
    if sname=='RST_NEW_TOKEN':
        if not re.match(r'^\d{8,12}:[A-Za-z0-9_-]{35,}$',txt):
            bot.reply_to(m,"<blockquote>❌ Invalid token format!\nExample: <code>1234567890:ABCdef...</code></blockquote>",parse_mode='HTML'); return
        # Validate token
        try:
            _rv=requests.get(f"https://api.telegram.org/bot{txt}/getMe",timeout=10)
            if not (_rv.status_code==200 and _rv.json().get('ok')):
                bot.reply_to(m,"<blockquote>❌ Token invalid! Bot nahi mila.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            _cun=_rv.json().get('result',{}).get('username','?')
            _cnm=_rv.json().get('result',{}).get('first_name','Bot')
        except Exception as e:
            bot.reply_to(m,f"<blockquote>❌ Token check error: {_safe_err(e)}</blockquote>",parse_mode='HTML'); return
        # DB update
        c.execute("UPDATE bot_clones SET bot_token=?,is_active=0 WHERE user_id=?",(txt,owner_uid)); conn.commit()
        user_state[uid]=S_NONE
        # Redeploy option do
        mk_dep=InlineKeyboardMarkup(row_width=1)
        mk_dep.add(_IKB("🔄 Abhi Redeploy Karo",style="success",callback_data=f"rst_redeploy_{owner_uid}"))
        mk_dep.add(_IKB("🗑️ Delete",style="danger",callback_data=f"rst_delete_{owner_uid}"))
        bot.reply_to(m,
            f"<blockquote>✅ <b>Token Updated!</b>\n\n"
            f"🤖 Bot: @{_cun} ({_cnm})\n"
            f"👤 Owner ID: <code>{owner_uid}</code>\n\n"
            f"Ab redeploy karo?\n"
            f"⚡ @Felix_modz1</blockquote>",
            reply_markup=mk_dep,parse_mode='HTML')
        return

    # ── Naya Owner ──
    if sname=='RST_NEW_OWNER':
        new_owner_uid=None; new_fname=None

        # Numeric ID
        if re.match(r'^\d{5,12}$',txt):
            new_owner_uid=int(txt)
            row=c.execute("SELECT first_name,username FROM users WHERE user_id=?",(new_owner_uid,)).fetchone()
            if row: new_fname=row[0] or f"User_{new_owner_uid}"
            else:
                try:
                    _gc=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                                      params={"chat_id":new_owner_uid},timeout=8)
                    if _gc.status_code==200:
                        _gd=_gc.json().get('result',{})
                        new_fname=((_gd.get('first_name','') or '')+" "+(_gd.get('last_name','') or '')).strip() or f"User_{new_owner_uid}"
                    else: new_fname=f"User_{new_owner_uid}"
                except: new_fname=f"User_{new_owner_uid}"

        # @username
        elif txt.startswith('@') or re.match(r'^[a-zA-Z][a-zA-Z0-9_]{3,}$',txt):
            un=txt.lstrip('@')
            row=c.execute("SELECT user_id,first_name FROM users WHERE username=? COLLATE NOCASE",(un,)).fetchone()
            if row: new_owner_uid=row[0]; new_fname=row[1] or f"@{un}"
            else:
                try:
                    _gc2=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                                       params={"chat_id":f"@{un}"},timeout=8)
                    if _gc2.status_code==200:
                        _gd2=_gc2.json().get('result',{})
                        new_owner_uid=_gd2.get('id')
                        new_fname=((_gd2.get('first_name','') or '')+" "+(_gd2.get('last_name','') or '')).strip() or f"@{un}"
                    else: new_owner_uid=None
                except: new_owner_uid=None
            if not new_owner_uid:
                bot.reply_to(m,f"<blockquote>❌ @{un} resolve nahi hua!\nNumeric User ID try karo.\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
        else:
            bot.reply_to(m,"<blockquote>❌ Valid ID ya @username bhejo!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

        # DB: purana owner_uid → naya owner_uid
        try:
            # bot_clones mein owner change
            row_tok=c.execute("SELECT bot_token FROM bot_clones WHERE user_id=?",(owner_uid,)).fetchone()
            if not row_tok:
                bot.reply_to(m,"<blockquote>❌ Clone DB mein nahi mila!\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return
            clone_token=row_tok[0]
            c.execute("DELETE FROM bot_clones WHERE user_id=?",(new_owner_uid,))  # agar naya owner ka pehle se clone ho to
            c.execute("UPDATE bot_clones SET user_id=?,is_active=0 WHERE user_id=?",(new_owner_uid,owner_uid))
            c.execute("UPDATE clone_admins SET clone_owner_uid=? WHERE clone_owner_uid=?",(new_owner_uid,owner_uid))
            c.execute("UPDATE clone_forced_channels SET clone_owner_uid=? WHERE clone_owner_uid=?",(new_owner_uid,owner_uid))
            # Naya user ensure karo DB mein
            c.execute("INSERT OR IGNORE INTO users(user_id,first_name,join_date,credits,first_time) VALUES(?,?,?,?,0)",
                      (new_owner_uid,new_fname,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),FREE_CREDITS))
            conn.commit()
        except Exception as e:
            bot.reply_to(m,f"<blockquote>❌ DB Error: {_safe_err(e)}\n⚡ @Felix_modz1</blockquote>",parse_mode='HTML'); return

        user_state[uid]=S_NONE
        mk_dep2=InlineKeyboardMarkup(row_width=1)
        mk_dep2.add(_IKB("🔄 Abhi Redeploy Karo",style="success",callback_data=f"rst_redeploy_{new_owner_uid}"))
        mk_dep2.add(_IKB("🗑️ Delete",style="danger",callback_data=f"rst_delete_{new_owner_uid}"))
        bot.reply_to(m,
            f"<blockquote>✅ <b>Owner Changed!</b>\n\n"
            f"👤 Purana Owner: <code>{owner_uid}</code>\n"
            f"👤 Naya Owner: <b>{new_fname}</b> (<code>{new_owner_uid}</code>)\n\n"
            f"Ab redeploy karo?\n"
            f"⚡ @Felix_modz1</blockquote>",
            reply_markup=mk_dep2,parse_mode='HTML')

# ── Hidden join/leave handler — catches events not visible via new_chat_members / left_chat_member ──
@bot.chat_member_handler()
def h_chat_member_updated(update):
    """Handle hidden joins and hidden leaves via ChatMemberUpdated"""
    try:
        if not update or not update.new_chat_member: return
        new_m = update.new_chat_member
        old_m = update.old_chat_member
        cid = update.chat.id
        chat_title = update.chat.title or "Group"
        old_status = old_m.status if old_m else 'left'
        new_status = new_m.status
        mb = new_m.user
        if not mb or mb.is_bot: return

        # ── HIDDEN LEAVE — member left but left_chat_member event nahi aaya ──
        if old_status in ('member','administrator','creator','restricted') and new_status in ('left','kicked'):
            if _IS_CLONE and _is_felix_chat(cid, update.chat.username): return
            try:
                _bye_val = get_group_bye(cid)
                if not _bye_val: return  # bye_on=0 → silently skip
            except: return
            try:
                fname     = mb.first_name or "Hidden User"
                lname     = mb.last_name or ""
                full_name = (fname+" "+lname).strip()
                uname     = "@"+mb.username if mb.username else "ʜɪᴅᴅᴇɴ ᴜꜱᴇʀ"
                now       = _now_ist()
                try: mem_count=bot.get_chat_members_count(cid)
                except: mem_count="?"
                def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
                _LOOP10 = _te("5465629669829128119")*10
                left_txt=(
                    f"<blockquote>"
                    f"{_te('4958830950604604428')} <a href='tg://user?id={mb.id}'><b>{full_name}</b></a> ʜᴀꜱ ʟᴇꜰᴛ ᴛʜᴇ ɢʀᴏᴜᴩ 😢\n"
                    f"{_LOOP10}\n\n"
                    f"{_te('4956461073550017373')} ɴᴀᴍᴇ  : <b>{full_name}</b>\n"
                    f"{_te('6147422674000808494')} ɪᴅ    : <code>{mb.id}</code>\n"
                    f"{_te('4958636483075376288')} ᴜꜱᴇʀ  : {uname}\n\n"
                    f"{_te('4958724224962265918')} ɢʀᴏᴜᴩ : <b>{chat_title}</b>\n"
                    f"{_te('4958472587123360612')} ᴍᴇᴍʙᴇʀꜱ : <b>{mem_count}</b>\n"
                    f"{_te('4956525562483967357')} ᴛɪᴍᴇ  : {now}\n\n"
                    f"{_LOOP10}\n"
                    f"{_te('4958900559139570572')} ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1"
                    f"</blockquote>"
                )
                bot.send_message(cid,left_txt,parse_mode="HTML")
            except Exception as _hl_e: print(f"[HIDDEN_LEFT] {_hl_e}")
            return

        # ── HIDDEN JOIN — invite link / added by admin ──
        if old_status in ('left','kicked') and new_status in ('member','administrator','creator','restricted'):
            # Clone bot: Felix ke channels/groups pe bilkul silent raho
            if _IS_CLONE and _is_felix_chat(cid, update.chat.username): return
            # Dedup — agar h_newmember ne already welcome bheja to skip
            if _join_already_welcomed(cid, mb.id): return
            try:
                wel_on, rules = get_group_welcome(cid)
                if not wel_on: return
            except: return
            try:
                fname = mb.first_name or "User"
                lname = mb.last_name or ""
                full_name = (fname+" "+lname).strip()
                uname = "@"+mb.username if mb.username else "No Username"
                tgid = mb.id
                now = _now_ist()
                try: mem_count=bot.get_chat_members_count(cid)
                except: mem_count="?"
                pic=_fetch_pfp_by_id(str(tgid))
                def _te(e): return f"<tg-emoji emoji-id='{e}'>⭐</tg-emoji>"
                uname_disp=uname if uname!="No Username" else f"<code>{tgid}</code>"
                gwimg,gwvid,gwvlist,gwstk=get_group_welcome_media(cid)
                try:
                    c.execute("SELECT welcome_text FROM group_welcome_settings WHERE group_id=?",(cid,))
                    gwtext_row=c.fetchone(); gwtext=gwtext_row[0] if gwtext_row and gwtext_row[0] else None
                except: gwtext=None
                if _IS_CLONE:
                    _cl_sent=False
                    if gwstk:
                        try: bot.send_sticker(cid, gwstk)
                        except: pass
                    if gwvlist:
                        _fid=get_next_group_video(cid)
                        if _fid:
                            _cl_cap=(
                                f"━━━━━━━━━━━\n"
                                f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!\n"
                                f"━━━━━━━━━━━\n"
                                f"👨‍💻 ᴅᴇᴠ : <a href='tg://user?id={OWNER_ID}'>Owner</a>"
                            ) if globals().get('_IS_CLASSIC',False) else f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!"
                            try: bot.send_video(cid, _fid, caption=_cl_cap, parse_mode="HTML"); _cl_sent=True
                            except: pass
                    if not _cl_sent and gwvid and os.path.exists(gwvid):
                        _cmu_cached_fid = _group_video_fileid_cache.get(f"{cid}:{gwvid}")
                        _cl_cap2=(
                            f"━━━━━━━━━━━\n"
                            f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!\n"
                            f"━━━━━━━━━━━\n"
                            f"👨‍💻 ᴅᴇᴠ : <a href='tg://user?id={OWNER_ID}'>Owner</a>"
                        ) if globals().get('_IS_CLASSIC',False) else f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!"
                        if _cmu_cached_fid:
                            try: bot.send_video(cid, _cmu_cached_fid, caption=_cl_cap2, parse_mode="HTML"); _cl_sent=True
                            except: _group_video_fileid_cache.pop(f"{cid}:{gwvid}", None)
                        if not _cl_sent:
                            try:
                                with open(gwvid,'rb') as _f:
                                    _cmu_sv=bot.send_video(cid,_f,caption=_cl_cap2,parse_mode="HTML")
                                    _cl_sent=True
                                    if _cmu_sv and _cmu_sv.video:
                                        _group_video_fileid_cache[f"{cid}:{gwvid}"] = _cmu_sv.video.file_id
                            except: pass
                    if not _cl_sent and gwimg and os.path.exists(gwimg):
                        _cl_cap3=(
                            f"━━━━━━━━━━━\n"
                            f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!\n"
                            f"━━━━━━━━━━━\n"
                            f"👨‍💻 ᴅᴇᴠ : <a href='tg://user?id={OWNER_ID}'>Owner</a>"
                        ) if globals().get('_IS_CLASSIC',False) else f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!"
                        try:
                            with open(gwimg,'rb') as _f: bot.send_photo(cid,_f,caption=_cl_cap3,parse_mode="HTML"); _cl_sent=True
                        except: pass
                    if not _cl_sent and pic:
                        _cl_cap4=(
                            f"━━━━━━━━━━━\n"
                            f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!\n"
                            f"━━━━━━━━━━━\n"
                            f"👨‍💻 ᴅᴇᴠ : <a href='tg://user?id={OWNER_ID}'>Owner</a>"
                        ) if globals().get('_IS_CLASSIC',False) else f"👋 ᴡᴇʟᴄᴏᴍᴇ <a href='tg://user?id={tgid}'><b>{full_name}</b></a>!"
                        try: bot.send_photo(cid,pic,caption=_cl_cap4,parse_mode="HTML")
                        except: pass
                    if not _cl_sent and not pic:
                        # Text-only fallback for NORMAL CLONE group welcome
                        if globals().get('_IS_CLASSIC',False):
                            _norm_gwel=(
                                f"<blockquote>━━━━━━━━━━━\n"
                                f"👋 ᴡᴇʟᴄᴏᴍᴇ {uname_disp} !!\n"
                                f"━━━━━━━━━━━\n\n"
                                f"👤 ɴᴀᴍᴇ : <b>{full_name}</b>\n"
                                f"🆔 ɪᴅ   : <code>{tgid}</code>\n\n"
                                f"📋 /help — ᴄᴏᴍᴍᴀɴᴅꜱ\n\n"
                                f"━━━━━━━━━━━\n"
                                f"👨‍💻 ᴅᴇᴠ : <a href='tg://user?id={OWNER_ID}'>Owner</a></blockquote>"
                            )
                            try: bot.send_message(cid,_norm_gwel,parse_mode="HTML")
                            except: pass
                    return
                # ── Original bot / PREMIUM CLONE — new emoji welcome ──
                _LOOP10 = _te("5465629669829128119")*10
                # PREMIUM CLONE footer = owner ID, Original bot = @Felix_modz1
                if _IS_CLONE:
                    _dev_footer = f"{_te('4958900559139570572')} ᴅᴇᴠᴇʟᴏᴩᴇʀ : <a href='tg://user?id={OWNER_ID}'>Owner</a>"
                else:
                    _dev_footer = f"{_te('4958900559139570572')} ᴅᴇᴠᴇʟᴏᴩᴇʀ : @Felix_modz1"
                if rules:
                    _rules_lines = "\n".join(f"• {r.strip()}" for r in rules.splitlines() if r.strip())
                else:
                    _rules_lines = (
                        f"{_te('4958636483075376288')} ɴᴏ ꜱᴘᴀᴍ\n"
                        f"{_te('4958472587123360612')} ɴᴏ ᴀʙᴜꜱᴇ\n"
                        f"{_te('4956525562483967357')} ʀᴇꜱᴩᴇᴄᴛ ᴇᴠᴇʀʏᴏɴᴇ"
                    )
                welcome_txt=(
                    f"<blockquote>"
                    f"{_te('4958830950604604428')} ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ <b>{chat_title}</b> !!\n"
                    f"{_LOOP10}\n"
                    f"{_te('4956461073550017373')}{_te('4958469026595472714')} ʜᴇʟʟᴏ 殺┋ <a href='tg://user?id={tgid}'><b>{full_name}</b></a> !!\n\n"
                    f"{_te('6147422674000808494')}  /help — ꜱᴀʀᴇ ᴄᴏᴍᴍᴀɴᴅ ᴅᴇᴋʜᴏ\n\n"
                    f"{_te('4958724224962265918')} ʀᴜʟᴇꜱ:\n"
                    f"{_rules_lines}\n\n"
                    f"{_LOOP10}\n"
                    f"{_dev_footer}"
                    f"</blockquote>"
                )
                if gwtext:
                    welcome_txt=gwtext.replace("{name}",full_name).replace("{id}",str(tgid)).replace("{username}",uname).replace("{group}",chat_title)
                if gwstk:
                    try: bot.send_sticker(cid,gwstk)
                    except: pass
                sent2=False
                if gwvlist:
                    fid2=get_next_group_video(cid)
                    if fid2:
                        try: bot.send_video(cid,fid2,caption=welcome_txt,parse_mode="HTML"); sent2=True
                        except: pass
                if not sent2 and gwvid and os.path.exists(gwvid):
                    _cached_vid_fid2 = _group_video_fileid_cache.get(f"{cid}:{gwvid}")
                    if _cached_vid_fid2:
                        try: bot.send_video(cid,_cached_vid_fid2,caption=welcome_txt,parse_mode="HTML"); sent2=True
                        except: _group_video_fileid_cache.pop(f"{cid}:{gwvid}",None)
                    if not sent2:
                        try:
                            with open(gwvid,'rb') as _f:
                                _sv2=bot.send_video(cid,_f,caption=welcome_txt,parse_mode="HTML")
                                sent2=True
                                if _sv2 and _sv2.video:
                                    _group_video_fileid_cache[f"{cid}:{gwvid}"] = _sv2.video.file_id
                        except: pass
                if not sent2 and gwimg and os.path.exists(gwimg):
                    try:
                        with open(gwimg,'rb') as _f: bot.send_photo(cid,_f,caption=welcome_txt,parse_mode="HTML",message_effect_id="5046509860389126442"); sent2=True
                    except: pass
                if not sent2 and pic:
                    try: bot.send_photo(cid,pic,caption=welcome_txt,parse_mode="HTML",message_effect_id="5046509860389126442"); sent2=True
                    except: pass
                if not sent2:
                    try: bot.send_message(cid,welcome_txt,parse_mode="HTML",message_effect_id="5046509860389126442")
                    except: pass
            except Exception as _hj_e:
                print(f"[HIDDEN_JOIN] {_hj_e}")
    except Exception as _cmu_e:
        print(f"[CHAT_MEMBER_UPD] {_cmu_e}")

if __name__=="__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║        FELIX INFO BOT - v24 (API + TOGGLE FIX)         ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  ✅ 📱 Num Info → simran-num-info (data[] format fixed) ║")
    print("║  ✅ 🆔 UserID→Num → zcpe records[0].number fixed       ║")
    print("║  ✅ /leaved on/off → dedicated handler added            ║")
    print("║  ✅ /wel on/off → working (v23 fix retained)            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    # STEP 1: Restore from channel
    _tg_channel_restore()
    # STEP 2: DB reconnect — restore ke baad conn stale tha (deleted file pe point kar raha tha)
    try:
        _orig_conn.close()
    except: pass
    _new_raw_conn = sqlite3.connect(_DB_FILE, check_same_thread=False)
    _new_raw_conn.execute("PRAGMA journal_mode=WAL")
    _new_raw_conn.execute("PRAGMA synchronous=NORMAL")
    _new_raw_conn.commit()
    _orig_conn = _new_raw_conn
    conn._c = _new_raw_conn
    c._conn = _new_raw_conn
    print("[DB_REINIT] ✅ DB reconnected after restore")
    try: bot.remove_webhook()
    except: pass
    time.sleep(0.5)
    # Auto-restart all active clones after a short delay
    threading.Thread(target=lambda: (time.sleep(3), _auto_restart_clones()), daemon=True).start()
    # Felix channels ke numeric IDs load karo
    threading.Thread(target=lambda: (time.sleep(5), _load_felix_numeric_ids()), daemon=True).start()
    threading.Thread(target=_tg_backup_loop, daemon=True).start()
    while True:
        try:
            print("🟢 Felix Info Bot running...")
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=[
                    "message","edited_message","callback_query",
                    "chat_member","my_chat_member","inline_query",
                    "chosen_inline_result","channel_post"
                ]
            )
        except KeyboardInterrupt:
            print("\n🛑 Stopped!"); conn.close(); break
        except Exception as e:
            print(f"❌ Error: {_safe_err(e)}"); time.sleep(5)
