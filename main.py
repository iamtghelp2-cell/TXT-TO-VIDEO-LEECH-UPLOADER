import os
import re
import sys
import json
import time
import asyncio
import requests
import subprocess

import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN, ADMINS, OWNER_ID
from aiohttp import ClientSession
from pyromod import listen
from subprocess import getstatusoutput

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ParseMode

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN)

WELCOME_IMAGE_PATH = "welcome.jpg"

def is_valid_url(url):
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def extract_url_from_line(line):
    line = line.strip()
    if not line:
        return None, None
    
    url_match = re.search(r'https?://[^\s]+', line)
    if url_match:
        url = url_match.group()
        title = line.replace(url, '').strip().rstrip(':').strip('|').strip()
        if not title:
            title = f"File_{hash(url) % 1000}"
        return title, url
    return None, None

def get_platform_headers(url):
    """पहचानकर हर ऐप के हिसाब से सही हेडर लगाना"""
    headers_cmd = ""
    u = url.lower()
    
    if "akamaized.net" in u or "khanglobalstudies" in u:
        headers_cmd = '--add-header "Origin: https://khanglobalstudies.com" --add-header "Referer: https://khanglobalstudies.com/"'
    elif "classplusapp" in u or "cpvod" in u:
        headers_cmd = '--add-header "Origin: https://web.classplusapp.com" --add-header "Referer: https://web.classplusapp.com/"'
    elif "pw.live" in u or "penpencil" in u:
        headers_cmd = '--add-header "Origin: https://www.pw.live" --add-header "Referer: https://www.pw.live/"'
    elif "careerwill" in u:
        headers_cmd = '--add-header "Origin: https://careerwill.com" --add-header "Referer: https://careerwill.com/"'
    elif "adda247" in u:
        headers_cmd = '--add-header "Origin: https://www.adda247.com" --add-header "Referer: https://www.adda247.com/"'
    elif "drishtiias" in u:
        headers_cmd = '--add-header "Origin: https://www.drishtiias.com" --add-header "Referer: https://www.drishtiias.com/"'
    else:
        headers_cmd = '--add-header "Accept: */*" --add-header "Connection: keep-alive"'
        
    return headers_cmd

@bot.on_message(filters.command(["start"]))
async def start(bot: Client, m: Message):
    welcome_text = (
        f"<b>👋 Hello {m.from_user.mention}!</b>\n\n"
        f"<blockquote>📁 <b>Universal TXT-to-Telegram Uploader</b>\n\n"
        f"⚡ <b>Supported:</b> All Major Coaching Apps (KGS, Classplus, PW, Careerwill, Adda247), YouTube, Google Drive & PDFs.\n\n"
        f"🚀 Send <b>/upload</b> command to start downloading.</blockquote>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Upload Files", callback_data="upload_files")],
        [InlineKeyboardButton("🔔 Channel", url="https://t.me/iamtghelp")]
    ])
    
    if os.path.exists(WELCOME_IMAGE_PATH):
        await m.reply_photo(photo=WELCOME_IMAGE_PATH, caption=welcome_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await m.reply_text(welcome_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@bot.on_callback_query()
async def callback_handler(bot: Client, query: CallbackQuery):
    if query.data == "upload_files":
        await query.answer("Send /upload command to start!", show_alert=True)

@bot.on_message(filters.command("stop"))
async def restart_handler(_, m):
    await m.reply_text("**🛑 Stopped**", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command(["upload"]))
async def upload(bot: Client, m: Message):
    editable = await m.reply_text('📤 Send your TXT file with links ⚡️')
    input_msg: Message = await bot.listen(editable.chat.id)
    x = await input_msg.download()
    await input_msg.delete(True)

    path = f"./downloads/{m.chat.id}"
    os.makedirs(path, exist_ok=True)

    try:
        with open(x, "r", encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split("\n")
        links = []
        for line in lines:
            title, url = extract_url_from_line(line)
            if title and url and is_valid_url(url):
                links.append([title, url])
        
        os.remove(x)
        if not links:
            await editable.edit("❌ **No valid links found in the file!**")
            return
            
    except Exception as e:
        await editable.edit(f"❌ **Error reading file:** {str(e)}")
        if os.path.exists(x):
            os.remove(x)
        return
    
    await editable.edit(f"📊 **Total Links Found:** {len(links)}\n\n📝 **Send starting number** (default: 1)")
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)

    await editable.edit("📝 **Enter your batch name:**")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    
    await editable.edit("🎬 **Select video quality:**\n\n360, 480, 720, 1080")
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text.strip()
    await input2.delete(True)
    if raw_text2 not in ["360", "480", "720", "1080"]:
        raw_text2 = "720"
    
    await editable.edit("💬 **Enter caption for files:**")
    input3: Message = await bot.listen(editable.chat.id)
    MR = input3.text
    await input3.delete(True)
    
    await editable.edit("🖼 **Send thumbnail URL** (or send 'no' to skip):")
    input6 = await bot.listen(editable.chat.id)
    thumb_input = input6.text.strip()
    await input6.delete(True)
    await editable.delete()

    thumb = "no"
    if thumb_input.startswith(("http://", "https://")):
        try:
            getstatusoutput(f"wget '{thumb_input}' -O 'thumb.jpg'")
            if os.path.exists('thumb.jpg'):
                thumb = "thumb.jpg"
        except:
            thumb = "no"

    try:
        count = max(1, int(raw_text)) if raw_text.isdigit() else 1
    except:
        count = 1

    successful_downloads = 0
    failed_downloads = 0

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

    for i in range(count - 1, len(links)):
        try:
            title, url = links[i]
            
            # YouTube embed फिक्स
            if "youtube.com/embed/" in url:
                yt_id = url.split("embed/")[1].split("?")[0]
                url = f"https://www.youtube.com/watch?v={yt_id}"

            # Google drive direct link फिक्स
            if "drive.google.com" in url:
                url = url.replace("file/d/", "uc?export=download&id=").replace("/view?usp=sharing", "")

            name1 = re.sub(r'[<>:"/\\|?*]', '', title)[:60].strip()
            name = f'{str(count).zfill(3)}) {name1}'

            prog = await m.reply_text(
                f"⬇️ **Downloading...**\n\n"
                f"📁 **Name:** `{name1}`\n"
                f"📊 **Progress:** {count}/{len(links)}"
            )

            platform_headers = get_platform_headers(url)

            # 1. PDF फाइल्स
            if url.endswith('.pdf') or "pdf" in url.lower():
                cmd = f'yt-dlp --no-check-certificates {platform_headers} -o "{name}.pdf" "{url}"'
            # 2. सभी वीडियो प्लेटफॉर्म्स (KGS, Classplus, PW, YouTube, Akamai, CloudFront)
            else:
                cmd = (
                    f'yt-dlp '
                    f'--no-check-certificates '
                    f'--retries 20 '
                    f'--fragment-retries 20 '
                    f'--concurrent-fragments 5 '
                    f'--user-agent "{user_agent}" '
                    f'{platform_headers} '
                    f'-f "best[height<={raw_text2}]/bestvideo[height<={raw_text2}]+bestaudio/best" '
                    f'"{url}" '
                    f'-o "{name}.%(ext)s"'
                )

            cc = f'**📹 Video #{str(count).zfill(3)}**\n**📁 Title:** {name1}\n**📦 Batch:** {raw_text0}\n{MR}'
            cc1 = f'**📄 Document #{str(count).zfill(3)}**\n**📁 Title:** {name1}\n**📦 Batch:** {raw_text0}\n{MR}'

            try:
                if ".pdf" in url.lower():
                    subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    expected_pdf = f"{name}.pdf"
                    if os.path.exists(expected_pdf):
                        await bot.send_document(chat_id=m.chat.id, document=expected_pdf, caption=cc1)
                        os.remove(expected_pdf)
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                        await prog.edit(f"❌ **Failed:** {name1}")
                        await asyncio.sleep(2)
                else:
                    subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    found_file = None
                    for ext in ['.mp4', '.mkv', '.webm', '.ts']:
                        if os.path.exists(f"{name}{ext}"):
                            found_file = f"{name}{ext}"
                            break
                    
                    if found_file:
                        await helper.send_vid(bot, m, cc, found_file, thumb, name, prog)
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                        await prog.edit(f"❌ **Failed:** {name1}")
                        await asyncio.sleep(2)

                await prog.delete()
                count += 1
                time.sleep(1)

            except FloodWait as e:
                await asyncio.sleep(e.x)
                continue
            except Exception as e:
                failed_downloads += 1
                await prog.edit(f"❌ **Error:** {str(e)[:100]}")
                await asyncio.sleep(2)
                continue

        except Exception as e:
            failed_downloads += 1
            continue

    summary_text = (
        f"🎉 **Batch Complete!**\n\n"
        f"✅ **Successful:** {successful_downloads}\n"
        f"❌ **Failed:** {failed_downloads}\n"
        f"📊 **Total:** {successful_downloads + failed_downloads}"
    )
    await m.reply_text(summary_text)

if __name__ == "__main__":
    bot.run()
