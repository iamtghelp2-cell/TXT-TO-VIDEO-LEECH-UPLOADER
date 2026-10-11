import os
import time
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures

from utils import progress_bar

from pyrogram import Client, filters
from pyrogram.types import Message

def duration(filename):
    try:
        if not os.path.exists(filename):
            return 0
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of",
                                 "default=noprint_wrappers=1:nokey=1", filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        if result.returncode == 0:
            return float(result.stdout.decode().strip())
        return 0
    except Exception as e:
        print(f"Error getting duration: {e}")
        return 0


async def download_with_requests(url, filename):
    """Fallback download using requests library"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, allow_redirects=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return filename
        return None
    except Exception as e:
        print(f"Error in requests download: {e}")
        return None


async def download_video(url, cmd, name, progress_callback=None):
    download_cmd = f'{cmd} -R 25 --fragment-retries 25 --no-check-certificates'
    global failed_counter
    print(download_cmd)
    logging.info(download_cmd)
    
    try:
        k = subprocess.run(download_cmd, shell=True, capture_output=True, text=True)
        
        if k.returncode != 0:
            print(f"yt-dlp failed with return code {k.returncode}")
            print(f"Error output: {k.stderr}")
            
            error_indicators = [
                "Unable to download webpage",
                "HTTP Error 400",
                "HTTP Error 403",
                "HTTP Error 404",
                "Unable to extract",
                "No video formats found",
                "Bad Request"
            ]
            
            if any(indicator in k.stderr for indicator in error_indicators):
                print("yt-dlp failed, attempting direct download...")
                result = await direct_download_video(url, name.split('.')[0], progress_callback)
                if result:
                    return result
                
                print("Aiohttp failed, trying requests...")
                return await download_with_requests(url, f"{name.split('.')[0]}.mp4")
            
            if "visionias" in cmd and failed_counter <= 10:
                failed_counter += 1
                await asyncio.sleep(5)
                return await download_video(url, cmd, name, progress_callback)
        
        failed_counter = 0
        
        possible_files = [
            name,
            f"{name}.webm",
            f"{name.split('.')[0]}.mkv",
            f"{name.split('.')[0]}.mp4",
            f"{name.split('.')[0]}.mp4.webm"
        ]
        
        for file_path in possible_files:
            if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                return file_path
        
        print("No file found after yt-dlp, attempting direct download...")
        return await direct_download_video(url, name.split('.')[0], progress_callback)
                
    except Exception as e:
        print(f"Error in download_video: {e}")
        try:
            return await direct_download_video(url, name.split('.')[0], progress_callback)
        except:
            return None


async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name):
    try:
        reply = await m.reply_text(f"Uploading » `{name}`")
        time.sleep(1)
        start_time = time.time()
        await m.reply_document(ka, caption=cc1)
        count += 1
        await reply.delete(True)
        time.sleep(1)
        if os.path.exists(ka):
            os.remove(ka)
        time.sleep(3)
    except Exception as e:
        print(f"Error in send_doc: {e}")


async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog):
    try:
        if not os.path.exists(filename):
            await m.reply_text(f"**Error: File not found** - `{filename}`")
            return
            
        thumbnail_cmd = f'ffmpeg -i "{filename}" -ss 00:00:12 -vframes 1 -y "{filename}.jpg"'
        subprocess.run(thumbnail_cmd, shell=True, stderr=subprocess.DEVNULL)
        
        if prog:
            await prog.delete(True)
        reply = await m.reply_text(f"**Uploading ...** - `{name}`")
        
        try:
            if thumb == "no":
                thumbnail = f"{filename}.jpg"
            else:
                thumbnail = thumb
        except Exception as e:
            thumbnail = f"{filename}.jpg"
            await m.reply_text(str(e))

        dur = int(duration(filename))
        start_time = time.time()

        try:
            await m.reply_video(filename, caption=cc, supports_streaming=True, height=720, width=1280, thumb=thumbnail, duration=dur, progress=progress_bar, progress_args=(reply, start_time))
        except Exception:
            await m.reply_document(filename, caption=cc, progress=progress_bar, progress_args=(reply, start_time))

        if os.path.exists(filename):
            os.remove(filename)

        if os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")
        await reply.delete(True)
        
    except Exception as e:
        print(f"Error in send_vid: {e}")
        await m.reply_text(f"**Error uploading video:** {str(e)}")

    
def exec(cmd):
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.stdout.decode()
    print(output)
    return output
        
def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        fut = executor.map(exec, cmds)
        
async def aio(url, name):
    k = f'{name}.pdf'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(k, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
        return k
    except Exception as e:
        print(f"Error in aio download: {e}")
        return None


async def test_url_accessibility(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.head(url, allow_redirects=True) as response:
                return {
                    'accessible': response.status == 200,
                    'status': response.status,
                    'content_type': response.headers.get('content-type', ''),
                    'content_length': response.headers.get('content-length', '0'),
                    'is_video': 'video' in response.headers.get('content-type', '').lower()
                }
    except Exception as e:
        print(f"URL test failed: {e}")
        return {
            'accessible': False,
            'status': 0,
            'content_type': '',
            'content_length': '0',
            'is_video': False,
            'error': str(e)
        }


def get_video_download_strategy(url):
    youtube_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
    if any(domain in url.lower() for domain in youtube_domains):
        return 'ytdlp_primary'
    
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    if any(ext in url.lower() for ext in video_extensions):
        return 'direct_primary'
    
    streaming_domains = ['visionias', 'classplusapp', 'jw-prod']
    if any(domain in url.lower() for domain in streaming_domains):
        return 'ytdlp_primary'
    
    return 'ytdlp_fallback_direct'


async def download(url, name):
    ka = f'{name}.pdf'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(ka, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
        return ka
    except Exception as e:
        print(f"Error in download: {e}")
        return None


def parse_vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 2)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info


def vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = dict()
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 3)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.update({f'{i[2]}': f'{i[0]}'})
            except:
                pass
    return new_info


async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode == 1:
        return False
    if stdout:
        return f'[stdout]\n{stdout.decode()}'
    if stderr:
        return f'[stderr]\n{stderr.decode()}'

    
def old_download(url, file_name, chunk_size=1024 * 10):
    try:
        if os.path.exists(file_name):
            os.remove(file_name)
        r = requests.get(url, allow_redirects=True, stream=True)
        with open(file_name, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    fd.write(chunk)
        return file_name
    except Exception as e:
        print(f"Error in old_download: {e}")
        return None


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"


failed_counter = 0

async def direct_download_video(url, name, progress_callback=None):
    try:
        print(f"Attempting direct download from: {url}")
        
        if url.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm')):
            ext = url.split('.')[-1].split('?')[0].lower()
        else:
            ext = 'mp4'
            
        filename = f"{name}.{ext}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        timeout = aiohttp.ClientTimeout(total=7200)
        
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        async with aiohttp.ClientSession(
            timeout=timeout, 
            headers=headers, 
            connector=connector
        ) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    async with aiofiles.open(filename, 'wb') as file:
                        async for chunk in response.content.iter_chunked(16384):
                            await file.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                try:
                                    await progress_callback(downloaded, total_size)
                                except:
                                    pass
                    
                    if os.path.exists(filename) and os.path.getsize(filename) > 0:
                        print(f"Direct download successful: {filename}")
                        return filename
                else:
                    print(f"HTTP Error {response.status} for direct download")
                    return None
                    
    except Exception as e:
        print(f"Error in direct_download_video: {e}")
        try:
            return await download_with_requests(url, f"{name}.mp4")
        except:
            return None
