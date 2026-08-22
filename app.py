#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===================================================================
   ✨ 𝐀𝐈 𝐈𝐌𝐀𝐆𝐄 𝐆𝐄𝐍𝐄𝐑𝐀𝐓𝐎𝐑 𝐁𝐎𝐓 ✨
===================================================================
Developed By: Shuvom -- Team X
Description: Generate stunning AI images from text prompts.
API: https://tobi-paras-aotpy-api-gen.vercel.app/
===================================================================
"""

import os
import sys
import io
import requests
import logging
import threading
import time
from typing import Optional, Dict, Any

try:
    import telebot
    from telebot import types
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
except ImportError:
    print("❌ Install: pip install pyTelegramBotAPI")
    sys.exit(1)

try:
    from flask import Flask, jsonify
except ImportError:
    print("❌ Install: pip install flask")
    sys.exit(1)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8107376372:AAHMDy0DZNJTY6rd6vRUhDvlHCrSaprHriY"  # Replace with your bot token
ADMIN_ID = 7479467987  # Your Telegram ID
DEVELOPER = "𝐒𝐇𝐔𝐕𝐎𝐌 - 𝐓𝐄𝐀𝐌 𝐗"
BOT_NAME = "✨ 𝐀𝐈 𝐈𝐌𝐀𝐆𝐄 𝐆𝐄𝐍𝐄𝐑𝐀𝐓𝐎𝐑"

# AI API Endpoint
API_URL = "https://tobi-paras-aotpy-api-gen.vercel.app"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ==================== HELPERS ====================
def generate_image(prompt: str) -> Optional[bytes]:
    """
    Call the AI image generation API with the given prompt.
    Returns image bytes if successful, else None.
    """
    try:
        params = {"prompt": prompt}
        response = requests.get(API_URL, params=params, timeout=60)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '')

        if 'application/json' in content_type:
            data = response.json()
            image_url = data.get('image_url') or data.get('url')
            if image_url:
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                return img_response.content
            if 'data' in data:
                import base64
                return base64.b64decode(data['data'])
            logger.error("JSON response did not contain image data.")
            return None
        else:
            return response.content

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

# ==================== KEYBOARD ====================
def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("🎨 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞"),
        KeyboardButton("❓ 𝐇𝐞𝐥𝐩")
    ]
    keyboard.add(*buttons)
    return keyboard

# ==================== BOT COMMANDS ====================
@bot.message_handler(commands=['start'])
def start_cmd(message: types.Message):
    user = message.from_user
    welcome = f"""
✨ <b>𝐀𝐈 𝐈𝐌𝐀𝐆𝐄 𝐆𝐄𝐍𝐄𝐑𝐀𝐓𝐎𝐑</b> ✨
━━━━━━━━━━━━━━━━━━━━━━━━

👋 𝐇𝐞𝐥𝐥𝐨, <b>{user.first_name}</b>!

🎨 <b>𝐓𝐮𝐫𝐧 𝐲𝐨𝐮𝐫 𝐰𝐨𝐫𝐝𝐬 𝐢𝐧𝐭𝐨 𝐚𝐫𝐭.</b>
𝐉𝐮𝐬𝐭 𝐬𝐞𝐧𝐝 𝐦𝐞 𝐚 𝐝𝐞𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧, 𝐚𝐧𝐝 𝐈'𝐥𝐥 𝐠𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐚𝐧 𝐀𝐈 𝐢𝐦𝐚𝐠𝐞 𝐟𝐨𝐫 𝐲𝐨𝐮.

<b>📝 𝐄𝐱𝐚𝐦𝐩𝐥𝐞:</b>
<code>A majestic lion in a futuristic city</code>

━━━━━━━━━━━━━━━━━━━━━━━━
🔰 <b>𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫:</b> {DEVELOPER}
"""
    bot.reply_to(message, welcome, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['help'])
def help_cmd(message: types.Message):
    text = f"""
❓ <b>𝐇𝐎𝐖 𝐓𝐎 𝐔𝐒𝐄</b>
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>𝐒𝐭𝐞𝐩 𝟏:</b>
𝐓𝐲𝐩𝐞 𝐚 𝐜𝐫𝐞𝐚𝐭𝐢𝐯𝐞 𝐩𝐫𝐨𝐦𝐩𝐭
𝐄𝐱: <code>a cat wearing a hat</code>

🎯 <b>𝐒𝐭𝐞𝐩 𝟐:</b>
𝐒𝐞𝐧𝐝 𝐭𝐡𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞
𝐈'𝐥𝐥 𝐠𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐚𝐧 𝐢𝐦𝐚𝐠𝐞 𝐟𝐨𝐫 𝐲𝐨𝐮

🎯 <b>𝐒𝐭𝐞𝐩 𝟑:</b>
𝐂𝐥𝐢𝐜𝐤 "𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐀𝐠𝐚𝐢𝐧" 𝐭𝐨 𝐫𝐞-𝐠𝐞𝐧𝐞𝐫𝐚𝐭𝐞

━━━━━━━━━━━━━━━━━━━━━━━━
✨ <b>𝐓𝐢𝐩𝐬:</b>
• 𝐁𝐞 𝐝𝐞𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐯𝐞 𝐟𝐨𝐫 𝐛𝐞𝐬𝐭 𝐫𝐞𝐬𝐮𝐥𝐭𝐬
• 𝐀𝐝𝐝 𝐬𝐭𝐲𝐥𝐞 (𝐞.𝐠., 𝐫𝐞𝐚𝐥𝐢𝐬𝐭𝐢𝐜, 𝐚𝐧𝐢𝐦𝐞, 𝐨𝐢𝐥 𝐩𝐚𝐢𝐧𝐭𝐢𝐧𝐠)
• 𝐈𝐧𝐜𝐥𝐮𝐝𝐞 𝐜𝐨𝐥𝐨𝐫𝐬, 𝐦𝐨𝐨𝐝, 𝐚𝐧𝐝 𝐝𝐞𝐭𝐚𝐢𝐥𝐬

━━━━━━━━━━━━━━━━━━━━━━━━
🔰 <b>𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫:</b> {DEVELOPER}
"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['generate'])
def generate_cmd(message: types.Message):
    prompt = message.text.replace('/generate', '', 1).strip()
    if not prompt:
        bot.reply_to(message, "❌ <b>𝐏𝐥𝐞𝐚𝐬𝐞 𝐩𝐫𝐨𝐯𝐢𝐝𝐞 𝐚 𝐩𝐫𝐨𝐦𝐩𝐭.</b>\n𝐄𝐱𝐚𝐦𝐩𝐥𝐞: /generate <b>a cat</b>")
        return
    process_generation(message, prompt)

@bot.message_handler(func=lambda m: True)
def handle_message(message: types.Message):
    if message.text and message.text.startswith('/'):
        return
    prompt = message.text
    if not prompt:
        bot.reply_to(message, "❌ <b>𝐏𝐥𝐞𝐚𝐬𝐞 𝐬𝐞𝐧𝐝 𝐚 𝐭𝐞𝐱𝐭 𝐩𝐫𝐨𝐦𝐩𝐭.</b>")
        return
    process_generation(message, prompt)

def process_generation(message: types.Message, prompt: str):
    # Send a "generating" message
    status_msg = bot.reply_to(message, "🎨 <b>𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐢𝐧𝐠...</b>\n⏳ <i>𝐏𝐥𝐞𝐚𝐬𝐞 𝐰𝐚𝐢𝐭 𝐚 𝐟𝐞𝐰 𝐦𝐨𝐦𝐞𝐧𝐭𝐬</i>")

    # Call API
    img_bytes = generate_image(prompt)

    if img_bytes:
        try:
            # Send as photo
            bot.send_photo(
                message.chat.id,
                photo=io.BytesIO(img_bytes),
                caption=f"🖼️ <b>𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝 𝐈𝐦𝐚𝐠𝐞</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n📝 <b>𝐏𝐫𝐨𝐦𝐩𝐭:</b> <code>{prompt[:200]}</code>\n━━━━━━━━━━━━━━━━━━━━━━━━\n✨ <i>𝐏𝐨𝐰𝐞𝐫𝐞𝐝 𝐛𝐲 𝐀𝐈</i>",
                reply_to_message_id=message.message_id,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐀𝐠𝐚𝐢𝐧", callback_data=f"again_{prompt}")]
                ])
            )
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ <b>𝐅𝐚𝐢𝐥𝐞𝐝 𝐭𝐨 𝐬𝐞𝐧𝐝 𝐢𝐦𝐚𝐠𝐞:</b> {e}", message.chat.id, status_msg.message_id)
    else:
        bot.edit_message_text(
            "❌ <b>𝐅𝐚𝐢𝐥𝐞𝐝 𝐭𝐨 𝐠𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐢𝐦𝐚𝐠𝐞</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔴 𝐓𝐡𝐞 𝐀𝐏𝐈 𝐦𝐚𝐲 𝐛𝐞 𝐝𝐨𝐰𝐧 𝐨𝐫 𝐭𝐡𝐞 𝐩𝐫𝐨𝐦𝐩𝐭 𝐢𝐬 𝐧𝐨𝐭 𝐬𝐮𝐩𝐩𝐨𝐫𝐭𝐞𝐝.\n\n"
            "💡 <b>𝐓𝐫𝐲:</b>\n"
            "• 𝐀 𝐝𝐢𝐟𝐟𝐞𝐫𝐞𝐧𝐭 𝐩𝐫𝐨𝐦𝐩𝐭\n"
            "• 𝐀 𝐬𝐢𝐦𝐩𝐥𝐞𝐫 𝐝𝐞𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧\n"
            "• 𝐂𝐨𝐧𝐭𝐚𝐜𝐭 𝐭𝐡𝐞 𝐝𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫",
            message.chat.id,
            status_msg.message_id
        )

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("again_"))
def again_callback(call: types.CallbackQuery):
    prompt = call.data.replace("again_", "", 1)
    bot.answer_callback_query(call.id, "🔄 𝐑𝐞-𝐠𝐞𝐧𝐞𝐫𝐚𝐭𝐢𝐧𝐠...")
    process_generation(call.message, prompt)

# ==================== ADMIN COMMANDS (optional) ====================
@bot.message_handler(commands=['admin'])
def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, 
        "👑 <b>𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ 𝐁𝐨𝐭 𝐢𝐬 𝐫𝐮𝐧𝐧𝐢𝐧𝐠 𝐬𝐦𝐨𝐨𝐭𝐡𝐥𝐲.\n"
        "📊 𝐍𝐨 𝐢𝐬𝐬𝐮𝐞𝐬 𝐝𝐞𝐭𝐞𝐜𝐭𝐞𝐝.\n\n"
        f"🔰 <b>𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫:</b> {DEVELOPER}"
    )

# ==================== FLASK KEEP-ALIVE (for Render) ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "🎨 AI Image Generator Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ==================== MAIN ====================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   ███████╗██╗  ██╗    ███████╗████████╗ ██████╗ ██████╗    ║
    ║   ██╔════╝██║  ██║    ██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗   ║
    ║   ███████╗███████║    ███████╗   ██║   ██║   ██║██████╔╝   ║
    ║   ╚════██║██╔══██║    ╚════██║   ██║   ██║   ██║██╔══██╗   ║
    ║   ███████║██║  ██║    ███████║   ██║   ╚██████╔╝██║  ██║   ║
    ║   ╚══════╝╚═╝  ╚═╝    ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ║
    ║                                                              ║
    ║         🎨 AI IMAGE GENERATOR BOT 🎨                        ║
    ║                                                              ║
    ║         👑 Developer: SHUVOM - TEAM X                       ║
    ║         🚀 Bot is starting...                               ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    # Start Flask keep-alive thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    # Start bot
    try:
        bot.infinity_polling(timeout=30)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        time.sleep(5)
