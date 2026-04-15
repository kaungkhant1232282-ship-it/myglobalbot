import telebot
import sqlite3
import time
from telebot import types

# --- Bot Setup ---
TOKEN = '8681666452:AAEzz72DRmegiaOslzQr2h85Ku8EV7-4aZk'
ADMIN_ID = 8333737237 
bot = telebot.TeleBot(TOKEN)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, name TEXT, bio TEXT DEFAULT 'No bio yet', 
                       last_message_time REAL DEFAULT 0, is_banned INTEGER DEFAULT 0,
                       mute_until REAL DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS message_owner 
                      (msg_id INTEGER PRIMARY KEY, sender_id INTEGER, content TEXT, original_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS likes 
                      (msg_id INTEGER, user_id INTEGER, PRIMARY KEY (msg_id, user_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments 
                      (comment_id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id INTEGER, user_id INTEGER, text TEXT)''')
    conn.commit()
    return conn

db_conn = init_db()

# --- Helper Functions ---
def is_admin(user_id):
    return user_id == ADMIN_ID

def get_user_stats(user_id):
    cursor = db_conn.cursor()
    cursor.execute('''SELECT COUNT(likes.user_id) FROM likes 
                      JOIN message_owner ON likes.msg_id = message_owner.original_id 
                      WHERE message_owner.sender_id = ? AND message_owner.msg_id = message_owner.original_id''', (user_id,))
    total_likes = cursor.fetchone()[0]
    if total_likes < 20: title = "🆕 Newbie"
    elif total_likes < 100: title = "🔥 Active"
    elif total_likes < 300: title = "Expert"
    else: title = "👑 Legend"
    return total_likes, title

def update_all_buttons(orig_id):
    cursor = db_conn.cursor()
    l_c = cursor.execute('SELECT COUNT(*) FROM likes WHERE msg_id = ?', (orig_id,)).fetchone()[0]
    c_c = cursor.execute('SELECT COUNT(*) FROM comments WHERE msg_id = ?', (orig_id,)).fetchone()[0]
    
    l_txt = f"❤️ {l_c}" if l_c > 0 else "❤️"
    c_txt = f"💬 {c_c}" if c_c > 0 else "💬"
    
    instances = cursor.execute('SELECT msg_id, sender_id FROM message_owner WHERE original_id = ?', (orig_id,)).fetchall()
    
    for m_id, u_id in instances:
        markup = types.InlineKeyboardMarkup()
        btn_row = [
            types.InlineKeyboardButton(l_txt, callback_data=f"L_{orig_id}"),
            types.InlineKeyboardButton(c_txt, callback_data=f"C_{orig_id}")
        ]
        markup.row(*btn_row)
        
        if is_admin(u_id):
            cursor.execute('SELECT sender_id FROM message_owner WHERE original_id = ?', (orig_id,))
            p_id = cursor.fetchone()[0]
            markup.add(
                types.InlineKeyboardButton("🚫 Ban", callback_data=f"BAN_{p_id}"),
                types.InlineKeyboardButton("🔇 Mute", callback_data=f"MUTEBUTTON_{p_id}")
            )
            
        try: bot.edit_message_reply_markup(u_id, m_id, reply_markup=markup)
        except: continue

# --- Admin Commands ---
@bot.message_handler(commands=['admin'])
def admin_help(message):
    if is_admin(message.chat.id):
        txt = ("🛠 **Admin Control Panel**\n━━━━━━━━━━━━━━\n"
               "📊 `/stats` - Bot အခြေအနေကြည့်ရန်\n"
               "📢 `/broadcast` - အားလုံးဆီ စာပို့ရန်\n"
               "🚫 `/ban [ID]` - အပြီးပိတ်ရန်\n"
               "🔓 `/unban [ID]` - ပြန်ဖွင့်ရန်\n"
               "🔇 `/mute [ID] [Min]` - စာပို့ခွင့်ခေတ္တပိတ်ရန်\n"
               "🔊 `/unmute [ID]` - ပြန်ဖွင့်ရန်")
        bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")

@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if is_admin(message.chat.id):
        try:
            args = message.text.split()
            tid, mins = int(args[1]), int(args[2])
            until = time.time() + (mins * 60)
            db_conn.cursor().execute('UPDATE users SET mute_until = ? WHERE user_id = ?', (until, tid))
            db_conn.commit()
            bot.send_message(ADMIN_ID, f"🔇 User {tid} ကို {mins} မိနစ် Mute လိုက်ပါပြီ။")
            bot.send_message(tid, f"🔇 သင့်ကို Global Chat တွင် စာပို့ခွင့် {mins} မိနစ် ပိတ်လိုက်ပါသည်။")
        except: bot.send_message(ADMIN_ID, "❌ Usage: `/mute [ID] [Minutes]`")

@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if is_admin(message.chat.id):
        try:
            tid = int(message.text.split()[1])
            db_conn.cursor().execute('UPDATE users SET mute_until = 0 WHERE user_id = ?', (tid,))
            db_conn.commit()
            bot.send_message(ADMIN_ID, f"🔊 User {tid} ကို Unmute လုပ်လိုက်ပါပြီ။")
            bot.send_message(tid, "🔊 သင့်ကို Global Chat တွင် ပြန်လည်စာပို့ခွင့် ပြုလိုက်ပါပြီ။")
        except: bot.send_message(ADMIN_ID, "Usage: `/unmute [ID]`")

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if is_admin(message.chat.id):
        cursor = db_conn.cursor()
        u = cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        p = cursor.execute('SELECT COUNT(*) FROM message_owner WHERE msg_id = original_id').fetchone()[0]
        bot.send_message(ADMIN_ID, f"📊 **Stats:** Users: {u}, Posts: {p}")

@bot.message_handler(commands=['broadcast'])
def start_bc(message):
    if is_admin(message.chat.id):
        msg = bot.send_message(ADMIN_ID, "ပို့ချင်တဲ့ စာသား/ပုံ ကို ပို့ပေးပါ။")
        bot.register_next_step_handler(msg, do_bc)

def do_bc(message):
    users = db_conn.cursor().execute('SELECT user_id FROM users').fetchall()
    for u in users:
        try: bot.copy_message(u[0], message.chat.id, message.message_id)
        except: continue
    bot.send_message(ADMIN_ID, "✅ Broadcast Done!")

@bot.message_handler(commands=['ban'])
def ban_u(message):
    if is_admin(message.chat.id):
        try:
            tid = int(message.text.split()[1])
            db_conn.cursor().execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (tid,))
            db_conn.commit()
            bot.send_message(ADMIN_ID, f"🚫 User {tid} banned.")
        except: bot.send_message(ADMIN_ID, "Usage: `/ban ID`")

@bot.message_handler(commands=['unban'])
def unban_u(message):
    if is_admin(message.chat.id):
        try:
            tid = int(message.text.split()[1])
            db_conn.cursor().execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (tid,))
            db_conn.commit()
            bot.send_message(ADMIN_ID, f"🔓 User {tid} unbanned.")
        except: bot.send_message(ADMIN_ID, "Usage: `/unban ID`")

# --- User Commands ---
@bot.message_handler(commands=['start'])
def start(message):
    cursor = db_conn.cursor()
    exists = cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (message.chat.id,)).fetchone()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)', (message.chat.id, message.from_user.first_name))
    db_conn.commit()
    
    # Auto Welcome Logic
    if not exists:
        welcome_msg = f"🎊 **User အသစ်ရောက်ရှိလာပါပြီ!**\n━━━━━━━━━━━━━━\n👤 အမည်: {message.from_user.first_name}\n🆔 ID: `{message.chat.id}`\n\nနွေးထွေးစွာ ကြိုဆိုပါတယ်ဗျ! ✨"
        all_u = [r[0] for r in cursor.execute('SELECT user_id FROM users WHERE is_banned = 0').fetchall()]
        for u in all_u:
            try: bot.send_message(u, welcome_msg, parse_mode="Markdown")
            except: continue

    help_txt = (f"👋 **မင်္ဂလာပါ {message.from_user.first_name}!**\n\n"
                "🌐 **Global Chat Bot မှ ကြိုဆိုပါတယ်**\n━━━━━━━━━━━━━━\n"
                "🔹 `/profile` - အဆင့်ကြည့်ရန်\n"
                "🔹 `/setbio` - Bio ရေးရန်\n"
                "🔹 `/top` - Ranking ကြည့်ရန်\n"
                "🔹 `/history` - မှတ်တမ်းကြည့်ရန်\n━━━━━━━━━━━━━━\n"
                "💬 ပို့စ်တင်လျှင် ၁၀ မိနစ်ခြားပေးပါ။")
    bot.send_message(message.chat.id, help_txt, parse_mode="Markdown")

@bot.message_handler(commands=['profile'])
def show_profile(message):
    cursor = db_conn.cursor()
    data = cursor.execute('SELECT name, bio FROM users WHERE user_id = ?', (message.chat.id,)).fetchone()
    lks, title = get_user_stats(message.chat.id)
    bot.send_message(message.chat.id, f"👤 **PROFILE**\n━━━━━━━━\n📛 Name: {data[0]}\n🏅 Title: {title}\n❤️ Likes: {lks}\n🆔 ID: `{message.chat.id}`\n\n📝 Bio: {data[1]}", parse_mode="Markdown")

@bot.message_handler(commands=['history'])
def show_history(message):
    cursor = db_conn.cursor()
    cursor.execute('''SELECT mo.content, (SELECT COUNT(*) FROM likes WHERE msg_id = mo.original_id) 
                      FROM message_owner mo WHERE mo.sender_id = ? AND mo.msg_id = mo.original_id 
                      ORDER BY mo.msg_id DESC LIMIT 10''', (message.chat.id,))
    rows = cursor.fetchall()
    res = "📜 **သင့်မှတ်တမ်း**\n━━━━━━━━\n" + "\n".join([f"• {r[0][:20]}... (❤️ {r[1]})" for r in rows]) if rows else "မှတ်တမ်းမရှိပါ။"
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

@bot.message_handler(commands=['setbio'])
def set_bio(message):
    bio = ' '.join(message.text.split()[1:])
    if bio:
        db_conn.cursor().execute('UPDATE users SET bio = ? WHERE user_id = ?', (bio, message.chat.id))
        db_conn.commit()
        bot.send_message(message.chat.id, "✅ Bio Updated!")

@bot.message_handler(commands=['top'])
def show_top(message):
    cursor = db_conn.cursor()
    cursor.execute('''SELECT users.name, COUNT(likes.msg_id) as lks FROM message_owner 
                      JOIN likes ON message_owner.original_id = likes.msg_id 
                      JOIN users ON message_owner.sender_id = users.user_id 
                      WHERE message_owner.msg_id = message_owner.original_id
                      GROUP BY message_owner.sender_id ORDER BY lks DESC LIMIT 5''')
    res = "🏆 **TOP 5 POPULAR**\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(cursor.fetchall()): res += f"{i+1}. {r[0]} — ❤️ {r[1]}\n"
    bot.send_message(message.chat.id, res)

# --- Global Chat Logic ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'video_note'])
def handle_global_chat(message):
    if message.text and message.text.startswith('/'): return
    cursor = db_conn.cursor()
    user = cursor.execute('SELECT is_banned, last_message_time, mute_until FROM users WHERE user_id = ?', (message.chat.id,)).fetchone()
    
    if user:
        if user[0] == 1: return
        if time.time() < user[2]:
            rem = int((user[2] - time.time()) / 60)
            bot.reply_to(message, f"🔇 သင် Mute ခံထားရပါသည်။ ကျန်ရှိချိန်: {rem} မိနစ်။")
            return

    if message.reply_to_message:
        handle_comment_logic(message)
        return

    current_time = time.time()
    if not is_admin(message.chat.id) and user and (current_time - user[1]) < 600:
        bot.reply_to(message, f"⏳ Slow Mode: {int((600-(current_time-user[1]))/60)} မိနစ် ထပ်စောင့်ပါ။")
        return

    cursor.execute('UPDATE users SET last_message_time = ? WHERE user_id = ?', (current_time, message.chat.id))
    _, title = get_user_stats(message.chat.id)
    header = f"👤 **[{title}] {message.from_user.first_name}**\n🆔 ID: `{message.chat.id}`\n━━━━━━━━━━━━━━"
    orig_id = message.message_id 

    all_u = [r[0] for r in cursor.execute('SELECT user_id FROM users WHERE is_banned = 0').fetchall()]
    for u_id in all_u:
        if u_id == message.chat.id: continue
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("❤️", callback_data=f"L_{orig_id}"),
                   types.InlineKeyboardButton("💬", callback_data=f"C_{orig_id}"))
        if is_admin(u_id):
            markup.add(
                types.InlineKeyboardButton("🚫 Ban", callback_data=f"BAN_{message.chat.id}"),
                types.InlineKeyboardButton("🔇 Mute", callback_data=f"MUTEBUTTON_{message.chat.id}")
            )
        
        try:
            if message.content_type == 'text':
                sent = bot.send_message(u_id, f"{header}\n{message.text}", reply_markup=markup, parse_mode="Markdown")
                cont = message.text
            elif message.content_type == 'photo':
                cap = f"{header}\n{message.caption or ''}"
                sent = bot.send_photo(u_id, message.photo[-1].file_id, caption=cap, reply_markup=markup, parse_mode="Markdown")
                cont = f"[Photo] {message.caption or ''}"
            elif message.content_type == 'video':
                cap = f"{header}\n{message.caption or ''}"
                sent = bot.send_video(u_id, message.video.file_id, caption=cap, reply_markup=markup, parse_mode="Markdown")
                cont = f"[Video] {message.caption or ''}"
            
            cursor.execute('INSERT INTO message_owner (msg_id, sender_id, content, original_id) VALUES (?, ?, ?, ?)', 
                           (sent.message_id, message.chat.id, cont, orig_id))
        except: continue
    
    cursor.execute('INSERT OR REPLACE INTO message_owner (msg_id, sender_id, content, original_id) VALUES (?, ?, ?, ?)', 
                   (orig_id, message.chat.id, message.text or "[Media]", orig_id))
    db_conn.commit()
    bot.send_message(message.chat.id, "✨ ပို့ပြီးပါပြီ။")

def handle_comment_logic(message):
    cursor = db_conn.cursor()
    cursor.execute('SELECT original_id, sender_id FROM message_owner WHERE msg_id = ?', (message.reply_to_message.message_id,))
    row = cursor.fetchone()
    if row:
        orig_id, owner_id = row
        cursor.execute('INSERT INTO comments (msg_id, user_id, text) VALUES (?, ?, ?)', (orig_id, message.chat.id, message.text))
        db_conn.commit()
        try: bot.send_message(owner_id, f"💬 **{message.from_user.first_name}** က မှတ်ချက်ပေးလိုက်သည်:\n\n_{message.text}_", parse_mode="Markdown")
        except: pass
        update_all_buttons(orig_id)
        bot.reply_to(message, "✅ မှတ်ချက် ပို့ပြီးပါပြီ။")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    act, oid = call.data.split('_')[0], int(call.data.split('_')[1])
    cursor = db_conn.cursor()
    if act == 'L':
        cursor.execute('INSERT OR IGNORE INTO likes (msg_id, user_id) VALUES (?, ?)', (oid, call.from_user.id))
        db_conn.commit()
        bot.answer_callback_query(call.id, "❤️ Liked!")
        update_all_buttons(oid)
    elif act == 'BAN' and is_admin(call.from_user.id):
        cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (oid,))
        db_conn.commit()
        bot.answer_callback_query(call.id, f"🚫 User {oid} Banned!", show_alert=True)
    elif act == 'MUTEBUTTON' and is_admin(call.from_user.id):
        until = time.time() + 3600
        cursor.execute('UPDATE users SET mute_until = ? WHERE user_id = ?', (until, oid))
        db_conn.commit()
        bot.answer_callback_query(call.id, f"🔇 User {oid} Muted for 1 hour!", show_alert=True)
        bot.send_message(oid, "🔇 သင့်ကို Global Chat တွင် စာပို့ခွင့် ၁ နာရီ ပိတ်လိုက်ပါသည်။")
    elif act == 'C':
        cursor.execute('SELECT users.name, comments.text FROM comments JOIN users ON comments.user_id = users.user_id WHERE comments.msg_id = ?', (oid,))
        cmts = cursor.fetchall()
        res = "💬 **မှတ်ချက်များ**\n━━━━━━━━\n" + "\n".join([f"• *{n}:* {t}" for n, t in cmts]) if cmts else "မှတ်ချက်မရှိပါ။"
        bot.send_message(call.message.chat.id, res, parse_mode="Markdown")

print("Bot is running with Auto-Welcome & Mute system...")
bot.infinity_polling()
