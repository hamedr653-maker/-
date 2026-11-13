# Native Marimo notebook; complete user program is embedded below.
import marimo
import asyncio as _marimo_asyncio

app = marimo.App()

@app.cell
async def _():
    # Imports inside the Marimo cell: module-level imports are not cell-local dependencies.
    import asyncio as _marimo_asyncio
    _embedded_source = r'''
    import sys, subprocess, os

    # ====== تنظیم موتور انتقال آپلود WZGram (باید قبل از ساخت/ایمپورت wzgram ست شود) ======
    # ریشهٔ کندی آپلود نسبت به دانلود در WZGram:
    # ۱) آپلود (روی اکانت‌های غیرپریمیوم و بات‌ها) یک AdaptiveBucket دارد که با هر
    #    FloodWait نرخ را ×۰.۸۵ کاهش می‌دهد و بازیابی‌اش فقط ۱ پارت/ثانیه است؛ سقف
    #    پیش‌فرض کاربر ۳۲ پارت×۵۱۲KiB = ۱۶ MB/s است که در عمل به ~۲-۳ MB/s سقوط می‌کند.
    # ۲) دانلود همین کنترلگر را دارد ولی قطعه‌های ۱ مگابایتی و بربستر بزرگ‌تر دارد،
    #    و در عمل زودتر به سقف خود می‌رسد.
    # ۳) پول نشست‌های رسانه‌ای آپلود برای کاربر ۱۲ نشست است؛ آن را به سقف عملی ۱۶ می‌رسانیم.
    # این متغیرها چون در همین سلول و قبل از «from wzgram import ...» ست می‌شوند،
    # هم در سطح کلاس کتابخانه و هم در زمان هر آپلود دیده می‌شوند.
    def _wz_env_default(key, value):
        if not os.environ.get(key):
            os.environ[key] = str(value)

    # سقف مجاز نرخ آپلود (پارت ۵۱۲KiB در ثانیه). ۶۴ ≈ ۳۲ MB/s — بالاتر از هر آپ‌لینک خانگی؛
    # AdaptiveBucket همچنان هنگام FloodWait واقعی خودش کم می‌کند (×۰.۸۵).
    _wz_env_default("WZGRAM_UPLOAD_RATE_USER", 64)
    _wz_env_default("WZGRAM_UPLOAD_RATE_BOT", 64)
    _wz_env_default("WZGRAM_UPLOAD_RATE_PREMIUM", 300)
    # تعداد نشست‌های رسانه‌ای موازی روی دی‌سی آپلود (کتابخانه در MEDIA_POOL_CAP=16 سقف می‌بندد)
    _wz_env_default("WZGRAM_UPLOAD_POOL_USER", 16)
    _wz_env_default("WZGRAM_UPLOAD_POOL_BOT", 12)
    _wz_env_default("WZGRAM_UPLOAD_POOL_PREMIUM", 16)
    # WZGRAM_MAX_INFLIGHT_MEDIA و WZGRAM_SOCKET_BUFFER عمداً دست نمی‌خورند؛
    # مستندات WZGram صراحتاً می‌گویند افزایش آن‌ها سرعت را بیشتر نمی‌کند.
    # لاگ تشخیصی (نمایش FloodWait و دلیل واقعی افت سرعت): با WZGRAM_DEBUG=1 فعال می‌شود
    if os.environ.get("WZGRAM_DEBUG", "").strip().lower() in ("1", "true", "yes"):
        import logging as _wz_logging
        _wz_logging.basicConfig(
            level=_wz_logging.DEBUG,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )
        print("🪵 لاگ تشخیصی WZGram فعال است (WZGRAM_DEBUG=1)")

    _previous_bot_thread = globals().get("_BOT_ACTIVE_THREAD")
    if _previous_bot_thread is not None and _previous_bot_thread.is_alive():
        raise RuntimeError("ربات قبلی هنوز در حال اجراست؛ ابتدا سلول قبلی را متوقف کنید.")

    RUNTIME_ROOT = '/content' if os.path.isdir('/content') else os.getcwd()

    def _run_setup_command(command, label):
        try:
            result = subprocess.run(command, check=False)
            if result.returncode != 0:
                print(f"⚠️ دستور نصب {label} با کد {result.returncode} تمام شد؛ ادامه می‌دهم.")
        except Exception as exc:
            print(f"⚠️ اجرای دستور نصب {label} ممکن نشد: {exc}")

    #================== نصب پیش‌نیازها ==================
    # ⚠️ بعد از هر ری‌استارت رانتایم کل فایل رو دوباره اجرا کن؛ نصب‌ها ایدمپوتن
    # ⚠️ numpy عمداً اینجا نصب/آپدیت نمی‌شود — OpenCV فقط در کد و در صورت نیاز نصب می‌شود
    _run_setup_command(["apt-get", "update", "-y"], "apt-get update")
    _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"], "pip/setuptools/wheel")
    _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "yt-dlp[default,curl-cffi]"], "yt-dlp")  # stable release; avoid nightly/pre-release regressions
    try:
        from importlib.metadata import version as _dist_version, PackageNotFoundError as _PackageNotFoundError
        try:
            _dist_version("pyrogram")
        except _PackageNotFoundError:
            pass
        else:
            _run_setup_command([sys.executable, "-m", "pip", "uninstall", "-y", "pyrogram"], "remove conflicting Pyrogram distribution")
    except Exception as _dist_check_error:
        print(f"⚠️ بررسی نسخهٔ Pyrogram انجام نشد: {_dist_check_error}")
    _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "wzgram[fast]", "requests-toolbelt", "ffmpeg-python", "requests", "beautifulsoup4", "playwright"], "WZGram / Python dependencies")
    _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "Pillow>=10.0", "arabic-reshaper", "python-bidi"], "Pillow/Persian text dependencies")
    _run_setup_command([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], "Playwright Chromium")

    #================== تنظیمات پایه و ایمپورت‌ها ==================
    import asyncio, os, tempfile, subprocess, math, shutil, time, random, sys, threading, traceback
    import requests
    import json
    from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
    from wzgram import Client as _WZGramNativeClient, filters as _wzgram_filters
    from types import SimpleNamespace
    from yt_dlp import YoutubeDL
    import subprocess
    # playwright chromium توی سلول اول نصب میشه؛ اینجا فقط یه چک بی‌صداست
    # (با check=True نباشه تا یه خطای گذرای شبکه کل سلول رو کرش نکنه)
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
                       capture_output=True, timeout=900, check=False)
    except Exception as e:
        print("⚠️ chromium playwright (بی‌خطر):", e)

    # OpenCV — فقط اگه واقعاً در دسترس نباشه نصب میشه.
    # (نصب قاطی‌شدهٔ numpy/opencv روی Colab دلیل اصلی کرش‌ها بود؛
    #  اگه cv2 هست، دست به numpy نمی‌زنیم که خراب نشه)
    try:
        import cv2 as _cv2_check
        print("✅ OpenCV موجود:", _cv2_check.__version__)
    except Exception:
        print("📥 OpenCV در دسترس نیست — نصب می‌شود...")
        _cv2_res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "opencv-python-headless"],
            capture_output=True, text=True, timeout=900
        )
        if _cv2_res.returncode == 0:
            print("✅ OpenCV نصب شد")
        else:
            print("⚠️ نصب OpenCV خطا داد (تشخیص چهره غیرفعال می‌شود، بقیه ربات کار می‌کنه):")
            print(((_cv2_res.stderr or "") + (_cv2_res.stdout or ""))[-300:])

    def _pil_smoke_test():
        """تست واردسازی واقعیِ ماژول‌هایی که ربات استفاده می‌کند — نسخهٔ قاطی همین‌جا لو می‌رود"""
        import importlib
        for m in list(sys.modules):
            if m.lower() in ("pil", "pillow") or m.lower().startswith(("pil.", "pillow.")):
                del sys.modules[m]
        import PIL
        for mod in ("Image", "ImageDraw", "ImageFont", "ImageOps", "ImageChops"):
            importlib.import_module(f"PIL.{mod}")
        return PIL.__version__

    def _pil_repair():
        """ترمیم کامل Pillow: uninstall → حذف دستی هرچه مونده → نصب تازه → تأیید.
        بازگشت: True اگر بعد از ترمیم Pillow سالم واردسازی شود."""
        import shutil, glob, site
        print("📥 ترمیم کامل Pillow (حذف فایل‌های قاطی‌شده)...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "Pillow"],
                           capture_output=True, timeout=300)
        except Exception:
            pass
        # حذف دستی — حتی فایل‌هایی که uninstall حذفشان نکرده (RECORD خراب)
        site_dirs = set()
        try: site_dirs.update(site.getsitepackages() or [])
        except Exception: pass
        try: site_dirs.add(site.getusersitepackages())
        except Exception: pass
        try:
            import PIL as _p
            site_dirs.add(os.path.dirname(os.path.dirname(_p.__file__)))
        except Exception:
            pass
        site_dirs.discard(None)
        for d in site_dirs:
            if not d or not os.path.isdir(d):
                continue
            for pat in (os.path.join(d, "PIL"), os.path.join(d, "pillow-*"), os.path.join(d, "Pillow-*")):
                for p in glob.glob(pat):
                    try: shutil.rmtree(p)
                    except Exception: pass
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "Pillow"],
            capture_output=True, text=True, timeout=900)
        ok = False
        if res.returncode == 0:
            try:
                _pil_smoke_test(); ok = True
            except Exception as e:
                print("⚠️ بعد از نصب اول هنوز خراب:", e)
        if not ok:
            print("📥 تلاش دوم با نسخهٔ ثابت Pillow==11.3.0 ...")
            res2 = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-cache-dir", "Pillow==11.3.0"],
                capture_output=True, text=True, timeout=900)
            if res2.returncode == 0:
                try:
                    _pil_smoke_test(); ok = True
                except Exception as e:
                    print("❌ ترمیم ممکن نشد:", e)
        if ok:
            print("✅ Pillow ترمیم شد — ربات با نسخهٔ سالم ادامه می‌دهد")
        return ok

    # سلامت‌چک Pillow — اگه فایل‌های دو نسخه قاطی شده باشند (مثلاً از Stop زدن وسط نصب)،
    # خطای «cannot import name ... from PIL._typing» همهٔ اسکرین‌شات‌ها را از بین می‌برد
    try:
        print("✅ Pillow:", _pil_smoke_test())
    except Exception as _pil_err:
        print("⚠️ Pillow خراب است (فایل‌های دو نسخه قاطی شده):", _pil_err)
        _pil_repair()

    from playwright.async_api import async_playwright
    from urllib.parse import urlparse
    import aiohttp
    import re
    from urllib.parse import urljoin
    from xml.etree import ElementTree as ET

    # Telegram status edits must not flood the main MTProto connection.
    # One global lock + a small interval prevents progress callbacks from
    # sending many editMessage RPCs at the same moment.
    # Async primitives are created later, inside the dedicated Telegram uvloop thread.
    # This prevents accidental binding to Marimo's own event loop.
    _safe_edit_lock = None
    _safe_edit_last_at = 0.0
    _SAFE_EDIT_MIN_INTERVAL = 1.5

    async def safe_edit(msg, text):
        global _safe_edit_last_at
        if msg is None:
            return False
        text = str(text)
        for attempt in range(3):
            try:
                async with _safe_edit_lock:
                    current = getattr(msg, "message", "") or ""
                    if current.strip() == text.strip():
                        return True
                    wait = _SAFE_EDIT_MIN_INTERVAL - (time.monotonic() - _safe_edit_last_at)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    await msg.edit(text)
                    _safe_edit_last_at = time.monotonic()
                return True
            except Exception as e:
                error_name = type(e).__name__.lower()
                if "messagenotmodified" in error_name:
                    return True
                if "floodwait" in error_name:
                    delay = max(
                        1.0,
                        float(getattr(e, "value", getattr(e, "seconds", getattr(e, "x", 3))) or 3)
                    )
                    print(f"⏳ محدودیت موقت تلگرام برای ویرایش وضعیت؛ {delay:.0f} ثانیه مکث")
                    if attempt >= 2:
                        return False
                    await asyncio.sleep(min(delay, 90.0))
                    continue
                err = str(e).lower()
                transient = any(token in err for token in (
                    "429", "invalid response buffer", "flood", "timeout",
                    "connection reset", "connection closed", "server closed",
                    "not connected", "cannot send requests"
                ))
                print("safe_edit error:", repr(e))
                if not transient or attempt >= 2:
                    return False
                delay = (3.0, 8.0)[attempt]
                print(f"🔁 تلاش دوباره برای ویرایش وضعیت پس از {delay:.0f} ثانیه...")
                await asyncio.sleep(delay)
        return False

    # uvloop runs in its own thread below. Do not patch or replace Marimo's event loop.
    try:
        import uvloop
        _UVLOOP_AVAILABLE = True
        print(f"✅ uvloop آماده است: {getattr(uvloop, '__version__', 'unknown')}")
    except Exception as _uvloop_import_error:
        uvloop = None
        _UVLOOP_AVAILABLE = False
        print(f"⚠️ uvloop در دسترس نیست؛ استفاده از asyncio استاندارد: {_uvloop_import_error}")

    # --------- مشخصات تلگرام ----------
    api_id = 17275707
    api_hash = "21e40998ca4bb43c6b3e0192547042d4"
    phone = "+"
    OWNER_ID = 1232259973

    # برای کیبورد اینلاین واقعی، توکن بات را در متغیر محیطی TELEGRAM_BOT_TOKEN قرار بده.
    # اگر خالی باشد، رفتار قبلی یوزربات با ورود شماره تلفن حفظ می‌شود.
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    # WZGram/Pyrogram session format is separate; keep the previous session untouched.
    SESSION_NAME = "wzgram_bot_session" if TELEGRAM_BOT_TOKEN else "wzgram_user_session"

    # === تنظیمات واترمارک و اورلی ===
    WATERMARK_TEXT = "@INO_BOKHOR1"
    WATERMARK_ENABLED = True
    OVERLAY_ENABLED = True
    cancel_flag = False

    # === تنظیم کیفیت دانلود ===
    DOWNLOAD_QUALITY = 720  # سقف کیفیت؛ با دستور «کیفیت 480» و ... تغییر می‌کند
    HLS_CONCURRENT_FRAGMENTS = 24  # دانلود هم‌زمان قطعه‌های HLS برای افزایش throughput
    # اگه برای سایتی لاگین لازمه، کوکی‌ها رو با افزونه "Get cookies.txt LOCALLY" بگیر و اینجا آپلود کن
    USER_COOKIES_FILE = os.path.join(RUNTIME_ROOT, "cookies.txt")


    def _download_format_selector(quality):
        """HLS اول؛ همهٔ مسیرهای جایگزین هم محدود به سقف کیفیت هستند."""
        q = int(quality)
        if q <= 0:
            raise ValueError("کیفیت باید عددی مثبت باشد")
        return (
            f"best[height<={q}][protocol^=m3u8]/"
            f"bestvideo[height<={q}][protocol^=m3u8]+bestaudio/"
            f"bestvideo[height<={q}]+bestaudio/"
            f"best[height<={q}]/"
            f"best[height<=?{q}]"
        )

    # === فونت برای واترمارک ===
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # ================== تنظیمات اسکرین‌شات‌ها ==================
    # کلمه‌ای که روی هر ۱۲ اسکرین‌شات نوشته میشه
    SCREENSHOT_TEXT = "کودن هاب"
    # "png" = بالاترین کیفیت ممکن (بی‌فقد) | "jpg" = حجم کمتر
    SCREENSHOT_FORMAT = "png"
    # اندازه متن نسبت به عرض تصویر (۰.۰۷۵ = ۷.۵٪ عرض تصویر)
    SCREENSHOT_TEXT_RATIO = 0.080
    # حالت رنگ: "auto" = خودکار کاملاً متضاد | "white" = همیشه سفید | "yellow" = همیشه زرد
    SCREENSHOT_TEXT_COLOR_MODE = "auto"
    # اگه True باشه، چهرهٔ افراد در کادر تشخیص داده میشه
    # و متن روی ناحیه‌ای گذاشته میشه که به چهره و بدن اون‌ها برخورد نکنه
    SCREENSHOT_AVOID_FACES = True
    # رنگ کاور پشت متن (سه‌تایی RGB) — مشکی
    SCREENSHOT_COVER_COLOR = (0, 0, 0)
    # شفافیت کاور (۰ تا ۲۵۵) — ۲۵۵ = کاملاً صاف، بدون هیچ شفافیتی
    SCREENSHOT_COVER_ALPHA = 255

    # === اگر True باشه، توی هر استارت session پاک میشه و دوباره لاگین می‌کنی ===
    # (False = با همون session قبلی سریع وصل میشه — توصیه میشه)
    FORCE_RELOGIN = False

    _PERSIAN_FONT_CACHE = None
    _PERSIAN_FONT_FAILED = False

    def _setup_persian_font():
        """دانلود فونت فارسی — مقاوم در برابر قطعی شبکه:
        چند آینه مختلف با timeout ۴۵ ثانیه + اعتبارسنجی فایل + فیل‌بک apt.
        نتیجه (موفق یا ناموفق) کش میشه تا دفعات بعد بلافاصله برگرده."""
        global _PERSIAN_FONT_CACHE, _PERSIAN_FONT_FAILED
        if _PERSIAN_FONT_CACHE:
            return _PERSIAN_FONT_CACHE
        if _PERSIAN_FONT_FAILED:
            return None
        persian_font = os.path.join(RUNTIME_ROOT, "Vazir.ttf")

        def _valid_font(path):
            try:
                from PIL import ImageFont
                if not (os.path.exists(path) and os.path.getsize(path) > 50000):
                    return False
                ImageFont.truetype(path, 20)  # فایل واقعاً فونت سالم باشه
                return True
            except Exception:
                return False

        if _valid_font(persian_font):
            _PERSIAN_FONT_CACHE = persian_font
            return persian_font
        try:
            if os.path.exists(persian_font):
                os.remove(persian_font)  # فایل ناقص/خراب از اجرای قبل
        except Exception:
            pass

        # آینه‌های مختلف (هرکدوم با timeout تا جا نمونه)
        font_urls = [
            "https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/fonts/ttf/Vazirmatn-Regular.ttf",
            "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.0.3/fonts/ttf/Vazirmatn-Regular.ttf",
            "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Regular.ttf",
            "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf",
            "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-Regular.ttf",
        ]
        for font_url in font_urls:
            try:
                print(f"📥 دانلود فونت فارسی از: {font_url}")
                r = requests.get(font_url, timeout=45,
                                 headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                if len(r.content) < 50000:
                    raise Exception(f"پاسخ ناقص است ({len(r.content)} بایت)")
                with open(persian_font, "wb") as f:
                    f.write(r.content)
                if _valid_font(persian_font):
                    print("✅ فونت فارسی دانلود شد")
                    _PERSIAN_FONT_CACHE = persian_font
                    return persian_font
                raise Exception("فایل دانلودشده فونت سالم نبود")
            except Exception as e:
                print(f"❌ خطا: {e} — تلاش بعدی...")
                try:
                    if os.path.exists(persian_font):
                        os.remove(persian_font)
                except Exception:
                    pass
                continue

        # اگه هیچ لینکی کار نکرد از apt نصب کن (دو بسته، هرکدوم که درش بود)
        try:
            print("📥 نصب فونت فارسی از apt...")
            subprocess.run(
                ["apt-get", "install", "-y", "fonts-farsiweb", "fonts-sil-scheherazade"],
                capture_output=True, timeout=180
            )
            import glob
            for pat in ("/usr/share/fonts/truetype/farsiweb/*.ttf",
                        "/usr/share/fonts/truetype/sil-scheherazade/*.ttf"):
                hits = sorted(glob.glob(pat))
                if hits and _valid_font(hits[0]):
                    print("✅ فونت از apt نصب شد")
                    _PERSIAN_FONT_CACHE = hits[0]
                    return hits[0]
        except Exception as e:
            print(f"❌ apt هم کار نکرد: {e}")

        _PERSIAN_FONT_FAILED = True  # دفعات بعد دوباره جا نبیند
        print("⚠️ فونت فارسی پیدا نشد — متن اسکرین‌شات اعمال نمی‌شود")
        return None

    # === تنظیمات حافظه موقت ===
    TEMP_PATH = "/content/temp" if os.path.exists("/content") else "./temp"
    os.makedirs(TEMP_PATH, exist_ok=True)
    WZGRAM_SESSION_DIR = os.path.join(RUNTIME_ROOT, ".wzgram_sessions")
    os.makedirs(WZGRAM_SESSION_DIR, exist_ok=True)

    # ================== پاک‌سازی فایل‌های ناقص ==================
    def cleanup_incomplete_files(reason=""):
        """حذف فایل‌های ناقص/موقت باقی‌مانده از اجرای قبلی
        همهٔ فایل‌های داخل TEMP_PATH فایل‌های کاری موقتی‌ان،
        پس پاک کردن کل پوشه کاملاً بی‌خطر است."""
        removed = 0
        freed = 0
        try:
            if os.path.exists(TEMP_PATH):
                for name in os.listdir(TEMP_PATH):
                    p = os.path.join(TEMP_PATH, name)
                    try:
                        if os.path.isfile(p):
                            freed += os.path.getsize(p)
                            os.remove(p)
                            removed += 1
                        else:
                            shutil.rmtree(p, ignore_errors=True)
                            removed += 1
                    except Exception:
                        pass
        except Exception as e:
            print("⚠️ خطا در پاک‌سازی:", e)
        print(f"🧹 پاک‌سازی ({reason or 'خروج'}): {removed} فایل حذف شد | {freed/1024/1024:.1f} MB آزاد شد")

    def _install_exit_handlers():
        """با هر توقف (دکمه Stop، سیگنال، خروج) فایل‌های ناقص پاک بشن
        تا دفعهٔ بعد ربات تمیز و بدون مشکل روشن بشه."""
        import signal
        import atexit
        def _handler(signum, frame):
            print("\n🛑 سیگنال دریافت شد — پاک‌سازی فایل‌های ناقص قبل از خروج...")
            try:
                for pat in ("ffmpeg", "yt-dlp", "chromium", "curl"):
                    subprocess.run(["pkill", "-f", pat], capture_output=True, timeout=10)
            except Exception:
                pass
            cleanup_incomplete_files("خروج")
            os._exit(0)
        try:
            signal.signal(signal.SIGTERM, _handler)
            signal.signal(signal.SIGINT, _handler)
        except Exception as e:
            print("⚠️ ثبت signal handler:", e)
        atexit.register(lambda: cleanup_incomplete_files("atexit"))

    # === WZGram compatibility boundary ===
    # WZGram uses the Pyrogram API, while the processing pipeline below historically
    # used a tiny subset of the previous event/message shape. This adapter preserves that
    # shape only; downloads/uploads always go through WZGram's native transfer engine.
    class _WZGramStatusMessage:
        def __init__(self, raw_message):
            self._raw = raw_message

        @property
        def message(self):
            return (getattr(self._raw, "text", None)
                    or getattr(self._raw, "caption", None)
                    or "")

        async def edit(self, text):
            if getattr(self._raw, "text", None) is not None:
                return await self._raw.edit_text(text)
            if getattr(self._raw, "caption", None) is not None:
                return await self._raw.edit_caption(text)
            return await self._raw.edit_text(text)

        async def delete(self):
            return await self._raw.delete()

        def __getattr__(self, name):
            return getattr(self._raw, name)


    class _WZGramMessageCompat:
        def __init__(self, raw_message):
            self._raw = raw_message

        @property
        def message(self):
            return (getattr(self._raw, "text", None)
                    or getattr(self._raw, "caption", None)
                    or "")

        @property
        def forward(self):
            return (getattr(self._raw, "forward_origin", None)
                    or getattr(self._raw, "forward_date", None)
                    or getattr(self._raw, "forward_from", None))

        @property
        def web_preview(self):
            return False

        @property
        def media(self):
            return None

        @property
        def file(self):
            media = (getattr(self._raw, "document", None)
                     or getattr(self._raw, "video", None)
                     or getattr(self._raw, "video_note", None))
            if media is not None:
                return SimpleNamespace(
                    name=(getattr(media, "file_name", None)
                          or getattr(media, "file_unique_id", None)
                          or ""),
                    size=int(getattr(media, "file_size", 0) or 0),
                )
            photo = getattr(self._raw, "photo", None)
            if photo is not None:
                sizes = getattr(photo, "sizes", None) or []
                largest = sizes[-1] if sizes else photo
                return SimpleNamespace(
                    name="photo.jpg",
                    size=int(getattr(largest, "file_size", 0) or 0),
                )
            return None

        def __getattr__(self, name):
            return getattr(self._raw, name)


    class _WZGramEventCompat:
        def __init__(self, raw_message):
            self._raw = raw_message
            self.message = _WZGramMessageCompat(raw_message)
            self.chat_id = raw_message.chat.id
            self.id = raw_message.id

        async def reply(self, text, **kwargs):
            reply_method = getattr(self._raw, "reply_text", None)
            if reply_method is None:
                reply_method = getattr(self._raw, "reply")
            sent = await reply_method(text, **kwargs)
            return _WZGramStatusMessage(sent)


    class _WZGramCompatClient:
        def __init__(self):
            try:
                max_transfers = int(os.environ.get("WZGRAM_MAX_CONCURRENT_TRANSMISSIONS", "16"))
            except (TypeError, ValueError):
                max_transfers = 16
            max_transfers = max(1, min(max_transfers, 32))
            self.raw = _WZGramNativeClient(
                SESSION_NAME,
                api_id=api_id,
                api_hash=api_hash,
                phone_number=None if TELEGRAM_BOT_TOKEN else phone,
                bot_token=TELEGRAM_BOT_TOKEN or None,
                max_concurrent_transmissions=max_transfers,
                sleep_threshold=60,
                workdir=WZGRAM_SESSION_DIR,
            )
            self.max_transfers = max_transfers

        def register_owner_handler(self, callback):
            owner_filter = _wzgram_filters.chat(OWNER_ID)

            async def _dispatch(_client, raw_message):
                await callback(_WZGramEventCompat(raw_message))

            self._dispatch_handler = self.raw.on_message(owner_filter)(_dispatch)
            return self._dispatch_handler

        async def start(self):
            return await self.raw.start()

        async def get_me(self):
            return await self.raw.get_me()

        async def download_media(self, message, file=None, progress_callback=None):
            raw_message = getattr(message, "_raw", message)
            return await self.raw.download_media(
                raw_message,
                file_name=file,
                progress=progress_callback,
            )

        async def send_video(self, chat_id, video, **kwargs):
            return await self.raw.send_video(chat_id, video, **kwargs)

        async def run_until_disconnected(self):
            # Pyrogram/WZGram idle() installs OS signal handlers. This client runs
            # on a dedicated worker thread, where signal.signal() is forbidden.
            # Keep the running loop alive without touching process-wide signals;
            # the Marimo Stop handler cancels the bot task and triggers disconnect.
            await asyncio.Event().wait()

        async def disconnect(self):
            return await self.raw.stop()


    client = None  # WZGram Client is created inside its dedicated uvloop, never on Marimo's loop.

    # === تنظیم موتور انتقال WZGram ===
    # انتقال‌های رسانه‌ای موازی توسط خود WZGram مدیریت می‌شوند.
    TG_UPLOAD_CONCURRENCY = 3
    SCREENSHOT_COUNT = 12

    async def fast_tg_download(message, dest_path, status_msg=None):
        """دانلود رسانه با موتور چندتکه و چنداتصالهٔ داخلی WZGram."""
        f = getattr(message, "file", None)
        size = int(getattr(f, "size", 0) or 0)
        loop = asyncio.get_running_loop()
        started = time.monotonic()
        last_bucket = [-10]

        def report_download(done, total):
            if not status_msg or not total:
                return
            pct = max(0, min(100, int(done * 100 / total)))
            bucket = 100 if pct >= 100 else (pct // 10) * 10
            if bucket <= last_bucket[0]:
                return
            last_bucket[0] = bucket
            elapsed = max(0.1, time.monotonic() - started)
            speed = max(0.0, done) / elapsed / (1024 * 1024)
            remain_mb = max(0, total - done) / (1024 * 1024)
            eta_seconds = int(remain_mb / speed) if speed > 0.01 else 0
            eta = f"{eta_seconds // 60}:{eta_seconds % 60:02d}" if speed > 0.01 else "..."
            bar = "█" * (bucket // 5) + "░" * (20 - bucket // 5)
            status_text = (
                f"⬇️ دانلود WZGram از تلگرام...\n"
                f"[{bar}] {bucket}%\n"
                f"⚡ سرعت: {speed:.1f} MB/s | ⏱️ باقی‌مانده: {eta}"
            )
            loop.call_soon_threadsafe(
                lambda text=status_text: asyncio.create_task(safe_edit(status_msg, text))
            )

        async def wzgram_progress(done, total):
            report_download(done, total)

        if cancel_flag:
            return None
        if size:
            print(
                f"🚀 دانلود با WZGram: {size / 1024 / 1024:.1f} MB | "
                f"موتور موازی داخلی | حداکثر انتقال هم‌زمان تنظیم‌شده: {client.max_transfers}"
            )
        try:
            result = await client.download_media(
                message,
                file=dest_path,
                progress_callback=wzgram_progress,
            )
            if cancel_flag:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return None
            if not result or not os.path.exists(result) or os.path.getsize(result) <= 0:
                raise IOError("WZGram فایل دانلودشدهٔ معتبری برنگرداند")
            actual_size = os.path.getsize(result)
            elapsed = max(0.1, time.monotonic() - started)
            print(
                f"✅ دانلود WZGram کامل شد: {actual_size / 1048576:.1f} MB در {elapsed:.1f}s | "
                f"میانگین: {actual_size / elapsed / 1048576:.2f} MB/s"
            )
            return result
        except asyncio.CancelledError:
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
            except Exception:
                pass
            raise
        except Exception:
            try:
                if os.path.exists(dest_path) and os.path.getsize(dest_path) == 0:
                    os.remove(dest_path)
            except Exception:
                pass
            raise


    # دریافت و ارسال رسانه فقط از طریق موتور داخلی WZGram انجام می‌شود.


    if os.path.exists("/content"):
        tempfile.gettempdir = lambda: TEMP_PATH

    # ================== Encoder Mode ==================
    # NVENC در این Runtime قابل استفاده نیست؛ مستقیم از CPU/libx264 استفاده می‌کنیم.

    # ================== توابع تعمیر ==================
    def is_valid_video(video_path):
        if not os.path.exists(video_path) or os.path.getsize(video_path) < 100_000:
            return False
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_path
            ], capture_output=True, text=True, timeout=10)
            return result.returncode == 0 and result.stdout.strip()
        except:
            return False

    def fix_video_file(video_path):
        if is_valid_video(video_path):
            return video_path
        fixed_path = video_path.replace(".mp4", "_fixed.mp4")
        cmd = [
            "ffmpeg", "-v", "error", "-err_detect", "ignore_err", "-i", video_path,
            "-c", "copy", "-avoid_negative_ts", "make_zero", "-fflags", "+genpts",
            "-y", fixed_path
        ]
        ret = subprocess.run(cmd, capture_output=True)
        if ret.returncode == 0 and os.path.exists(fixed_path) and os.path.getsize(fixed_path) > 100_000:
            try:
                os.remove(video_path)
                print(f"✅ فایل تعمیر شد: {fixed_path}")
            except: pass
            return fixed_path
        return None

    def run(cmd):
        global cancel_flag
        print("EXEC:", " ".join(cmd))
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        try:
            for line in p.stdout:
                if cancel_flag:
                    p.kill()
                    break
                print(line.rstrip())
        except Exception as e:
            print("run() read error:", e)
        p.wait()
        return p.returncode

    #================== توابع کمکی ==================
    def _get_video_dimensions_sync(video_path):
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", video_path]
            ).decode().strip().split('\n')[0]
            width, height = map(int, out.split('x'))
            if width > 0 and height > 0:
                return width, height
        except:
            pass
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "json", video_path]
            ).decode()
            data = json.loads(out)
            stream = data.get('streams', [{}])[0]
            width = int(stream.get('width', 0))
            height = int(stream.get('height', 0))
            if width > 0 and height > 0:
                return width, height
        except:
            pass
        return 1280, 720

    def _get_fontsize_sync(video_path):
        try:
            width, _ = _get_video_dimensions_sync(video_path)
            return min(max(25, int(width * 0.046)), 72)
        except:
            return 25

    def _get_duration_sync(video_path):
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            ).decode().strip()
            return out
        except:
            return None

    def remux_for_faststart(input_path):
        if not is_valid_video(input_path):
            return input_path
        output_path = tempfile.mktemp(suffix=".mp4")
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", "-map_metadata", "0",
               "-movflags", "+faststart", output_path]
        ret = subprocess.run(cmd, capture_output=True)
        if (ret.returncode == 0 and os.path.exists(output_path)
                and os.path.getsize(output_path) > 100_000
                and is_valid_video(output_path)):
            try:
                if output_path != input_path:
                    os.remove(input_path)
            except: pass
            return output_path
        return input_path

    def _get_thumbnail_sync(video_path):
        thumb = tempfile.mktemp(suffix=".jpg", dir=tempfile.gettempdir())
        try:
            duration_str = _get_duration_sync(video_path)
            duration = float(duration_str) if duration_str else 10
            capture_time = min(450, max(1, duration / 2))
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(capture_time), "-i", video_path,
                 "-vframes", "1", "-q:v", "1", thumb],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
        except:
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", video_path, "-vframes", "1", thumb],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
            except:
                return None
        return thumb if os.path.exists(thumb) else None

    # ================== اسکرین‌شات با کیفیت بالا + کلمه ==================
    # --- تشخیص چهره (YuNet با فیل‌بک Haar) ---
    _FACE_YUNET_MODEL = "/content/face_yunet.onnx" if os.path.exists("/content") else "./face_yunet.onnx"
    _FACE_YUNET = None      # detector کش‌شده
    _FACE_CASCADES = {}     # فیل‌بک Haar برای نسخه‌های قدیمی OpenCV

    def _get_face_yunet():
        """دریافت/ساخت detector YuNet — مدل یکبار دانلود و کش میشه (~۲۲۷ KB)"""
        global _FACE_YUNET
        if _FACE_YUNET is not None:
            return _FACE_YUNET
        try:
            import cv2
            if not hasattr(cv2, "FaceDetectorYN"):
                return None
            if not (os.path.exists(_FACE_YUNET_MODEL) and os.path.getsize(_FACE_YUNET_MODEL) > 100000):
                print("📥 دانلود مدل تشخیص چهره (YuNet)...")
                import urllib.request
                urls = [
                    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                    "https://cdn.jsdelivr.net/gh/opencv/opencv_zoo@main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                ]
                for u in urls:
                    try:
                        urllib.request.urlretrieve(u, _FACE_YUNET_MODEL)
                        if os.path.exists(_FACE_YUNET_MODEL) and os.path.getsize(_FACE_YUNET_MODEL) > 100000:
                            break
                    except Exception:
                        continue
            if os.path.exists(_FACE_YUNET_MODEL) and os.path.getsize(_FACE_YUNET_MODEL) > 100000:
                # score_threshold=0.55 → یادگیری بهتر، nms=0.3
                _FACE_YUNET = cv2.FaceDetectorYN.create(
                    _FACE_YUNET_MODEL, "", (320, 320), 0.55, 0.3, 5000
                )
                return _FACE_YUNET
        except Exception as e:
            print("⚠️ خطا در آماده‌سازی YuNet:", e)
        return None

    def _detect_face_boxes(rgb_img):
        """تشخیص چهره‌ها (YuNet، در نبودش Haar).
        برمی‌گردونه: لیست (x, y, w, h) در مختصات خود تصویر،
        هر باکس کمی بزرگ‌تر شده تا کل سر (مو، پیشونی، گوش) پوشش داده بشه.
        اگه تشخیص در دسترس نباشه یا خطا بده، لیست خالی (رفتار قبلی حفظ میشه)."""
        try:
            import cv2
            import numpy as np
            arr = np.asarray(rgb_img)
            if arr.ndim == 2:
                gray = arr
                bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            else:
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            h, w = gray.shape[:2]
            boxes = []
            # ۱) YuNet — دقیق‌تر و برای چهره‌های کج/نیم‌رخ هم جواب میده (نیاز به BGR سه‌کاناله)
            yunet = _get_face_yunet()
            if yunet is not None:
                try:
                    yunet.setInputSize((w, h))
                    _, faces = yunet.detect(bgr)
                    if faces is not None:
                        for row in faces:
                            x, y, fw, fh = [int(v) for v in row[:4]]
                            boxes.append((x, y, fw, fh))
                except Exception:
                    pass
            # ۲) Haar — فقط برای نسخه‌های قدیمی OpenCV که YuNet ندارن
            if not boxes and hasattr(cv2, "CascadeClassifier"):
                min_size = max(20, int(w * 0.03))
                for name in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
                    try:
                        if name not in _FACE_CASCADES:
                            path = os.path.join(cv2.data.haarcascades, name)
                            if not os.path.exists(path):
                                continue
                            _FACE_CASCADES[name] = cv2.CascadeClassifier(path)
                        det = _FACE_CASCADES[name].detectMultiScale(
                            gray, scaleFactor=1.1, minNeighbors=5,
                            minSize=(min_size, min_size)
                        )
                        for (x, y, fw, fh) in det:
                            boxes.append((int(x), int(y), int(fw), int(fh)))
                    except Exception:
                        pass
            # بزرگ‌تر کردن باکس‌ها برای پوشش کل سر
            out = []
            for (x, y, fw, fh) in boxes:
                x0 = max(0, x - int(fw * 0.45))
                y0 = max(0, y - int(fh * 0.55))
                x1 = min(w, x + fw + int(fw * 0.45))
                y1 = min(h, y + fh + int(fh * 0.55))
                out.append((x0, y0, x1 - x0, y1 - y0))
            return out
        except Exception as e:
            print("⚠️ خطا در تشخیص چهره:", e)
            return []

    # --- تشخیص بدن (PP-HumanSeg از OpenCV Zoo — حتی وقتی صورت در کادر نیست) ---
    _PERSON_SEG_MODEL = "/content/pphumanseg.onnx" if os.path.exists("/content") else "./pphumanseg.onnx"
    _PERSON_SEG = None

    def _get_person_segmenter():
        """دریافت مدل سگمنتیشن بدن — یکبار دانلود و کش میشه (~۶ مگابایت)"""
        global _PERSON_SEG
        if _PERSON_SEG is not None:
            return _PERSON_SEG
        try:
            import cv2
            if not (os.path.exists(_PERSON_SEG_MODEL) and os.path.getsize(_PERSON_SEG_MODEL) > 1_000_000):
                print("📥 دانلود مدل تشخیص بدن (PP-HumanSeg, ~۶MB)...")
                import urllib.request
                urls = [
                    "https://github.com/opencv/opencv_zoo/raw/main/models/human_segmentation_pphumanseg/human_segmentation_pphumanseg_2023mar.onnx",
                    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/human_segmentation_pphumanseg/human_segmentation_pphumanseg_2023mar.onnx",
                ]
                for u in urls:
                    try:
                        urllib.request.urlretrieve(u, _PERSON_SEG_MODEL)
                        if os.path.exists(_PERSON_SEG_MODEL) and os.path.getsize(_PERSON_SEG_MODEL) > 1_000_000:
                            break
                    except Exception:
                        continue
            if os.path.exists(_PERSON_SEG_MODEL) and os.path.getsize(_PERSON_SEG_MODEL) > 1_000_000:
                _PERSON_SEG = cv2.dnn.readNet(_PERSON_SEG_MODEL)
                return _PERSON_SEG
        except Exception as e:
            print("⚠️ خطا در آماده‌سازی مدل بدن:", e)
        return None

    def _detect_person_mask(rgb_img):
        """ماسک بدنِ انسان‌های کادر (HxW حقیقی) — حتی وقتی صورت دیده نمی‌شود.
        در صورت خطا None برمی‌گردونه (رفتار قبلی حفظ میشه)."""
        try:
            import cv2
            import numpy as np
            seg = _get_person_segmenter()
            if seg is None:
                return None
            arr = np.asarray(rgb_img)
            if arr.ndim == 2:
                bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            else:
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            h, w = bgr.shape[:2]
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            blob_in = cv2.resize(rgb, (192, 192)).astype(np.float32) / 255.0
            blob_in = (blob_in - 0.5) / 0.5
            seg.setInput(cv2.dnn.blobFromImage(blob_in))
            out = seg.forward()
            out = cv2.resize(out[0].transpose(1, 2, 0), (w, h), interpolation=cv2.INTER_LINEAR)
            mask = out.argmax(axis=2) == 1
            # کمی بزرگ‌تر کردن ماسک تا حاشیهٔ امن دور بدن هم رعایت بشه
            if mask.any():
                k = max(3, int(max(w, h) * 0.03))
                if k % 2 == 0:
                    k += 1
                mask = cv2.dilate(mask.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)
            return mask
        except Exception as e:
            print("⚠️ خطا در تشخیص بدن:", e)
            return None

    def _rect_overlap(a, b):
        """مساحت اشتراک دو باکس (x, y, w, h)"""
        x0 = max(a[0], b[0]); y0 = max(a[1], b[1])
        x1 = min(a[0] + a[2], b[0] + b[2]); y1 = min(a[1] + a[3], b[1] + b[3])
        return max(0, x1 - x0) * max(0, y1 - y0)

    def _pick_text_region(small_img, box_w, box_h, person_mask=None, avoid_boxes=()):
        """بهترین محل برای باکس متن+کاور — ترجیح به پایین تصویر.
        تصویر کوچیک رو به ۹ ناحیه تقسیم می‌کنه و بر اساس «شلوغی» هر ناحیه
        بهترین محل رو انتخاب می‌کنه (گوشهٔ پایین چپ/راست → پایین وسط → بالا → میانی).
        مهم‌تر از همه: باکسِ واقعیِ متن روی بدن (person_mask) و چهره (avoid_boxes)
        نیفتد — هم‌پوشانی باکس با ماسک بدن محاسبه و با جریمهٔ سنگین رد می‌شود."""
        try:
            import numpy as np
            g = np.asarray(small_img.convert("L"), dtype=np.float32)
            h, w = g.shape
            cells = {}
            for r in range(3):
                for c in range(3):
                    cell = g[r*h//3:(r+1)*h//3, c*w//3:(c+1)*w//3]
                    cells[(r, c)] = float(cell.std())
        except Exception:
            w, h = small_img.size
            g = small_img.convert("L")
            cells = {}
            for r in range(3):
                for c in range(3):
                    box = (c*w//3, r*h//3, (c+1)*w//3, (r+1)*h//3)
                    data = list(g.crop(box).getdata())
                    mean = sum(data) / len(data)
                    cells[(r, c)] = (sum((v-mean)**2 for v in data) / len(data)) ** 0.5

        # (ترجیح، ردیف، ستون) — ترجیح ۰ = پایین تصویر
        candidates = [
            (0, 2, 0), (0, 2, 2), (0, 2, 1),   # اولویت ۰ = پایین: چپ، راست، وسط
            (1, 1, 0), (1, 1, 2),              # اولویت ۱ = میانی: چپ، راست
            (2, 0, 2), (2, 0, 1),              # اولویت ۲ = بالا: راست، وسط (بالا-چپ عمداً کاندید نیست — آیکون‌های تلگرام)
        ]
        W = person_mask.shape[1] if person_mask is not None else None
        H = person_mask.shape[0] if person_mask is not None else None
        mx = int(W * 0.01) if W else 0
        my = int(H * 0.01) if H else 0
        # نقشهٔ فاصله از بدن (برای اینکه متن به بدن «چسبیده» هم نشود)
        dist_map = None
        if person_mask is not None and person_mask.any():
            try:
                import cv2
                dist_map = cv2.distanceTransform((~person_mask).astype(np.uint8), cv2.DIST_L2, 5)
            except Exception:
                dist_map = None
        results = {}
        for prio, r, c in candidates:
            cx_n = (c + 0.5) / 3.0
            cy_n = (r + 0.5) / 3.0
            # ناحیهٔ سلول در مختصات نرمال (برای باکس‌های چهره)
            cell_box = (c / 3.0, r / 3.0, 1 / 3.0, 1 / 3.0)
            # حتی کمترین برخورد با باکس چهره/بدن → جریمه سنگین
            face_penalty = 0
            for fb in avoid_boxes:
                if _rect_overlap(cell_box, fb) > 0:
                    face_penalty = 10000
                    break
            # هم‌پوشانی باکسِ واقعی با ماسک بدن — معیار اولِ انتخاب (مطلق)
            person_ratio = 0.0
            dist = 0.0
            if person_mask is not None:
                x0 = max(mx, min(W - box_w - mx, int(cx_n * W) - box_w // 2))
                y0 = max(my, min(H - box_h - my, int(cy_n * H) - box_h // 2))
                sub = person_mask[y0:y0 + box_h, x0:x0 + box_w]
                person_ratio = float(sub.mean())
                if dist_map is not None:
                    dist = float(dist_map[y0:y0 + box_h, x0:x0 + box_w].min())
            score = prio * 150 + cells[(r, c)] + face_penalty
            # انتخاب: ۱) بدون هم‌پوشانی با بدن  ۲) دورترین از بدن  ۳) پایین‌تر و خلوت‌تر
            # (گوشهٔ بالا-چپ اصلاً کاندید نیست — آیکون زمان/حجم/دانلود تلگرام روی همان ناحیه است)
            dist_band = int(round(dist / 10) * 10)
            key = (round(person_ratio, 3), -dist_band, score)
            results[(r, c)] = (key, cx_n, cy_n)

        best = min(results.values(), key=lambda t: t[0])
        return best[1], best[2]

    # ================== رندر متن فارسی (سازگار با همه نسخه‌های Pillow) ==================
    _RENDERER_SHAPES = None

    def _renderer_shapes_arabic(font_path):
        """آزمون یک‌بار: آیا موتور رندرِ Pillow خودش چیدمان RTL و چسبندگی
        حروف عربی را انجام می‌دهد؟ (Pillowهای جدید بله، قدیمی‌ها نه)
        روش: «با» و «اب» را رندر می‌کنیم و می‌بینیم نقطهٔ ب در کدام سمت است."""
        global _RENDERER_SHAPES
        if _RENDERER_SHAPES is not None:
            return _RENDERER_SHAPES
        _RENDERER_SHAPES = False
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            font = ImageFont.truetype(font_path, 44)
            def dot_x(s):
                img = Image.new("L", (300, 200), 0)
                d = ImageDraw.Draw(img)
                l, t, r, b = d.textbbox((0, 0), s, font=font)
                d.text((150 - (r - l) // 2 - l, 60 - t), s, font=font, fill=255)
                a = np.asarray(img)
                ink = a > 100
                ys, xs = np.where(ink)
                if len(xs) == 0:
                    return None
                y0, y1 = ys.min(), ys.max()
                x0, x1 = xs.min(), xs.max()
                if x1 - x0 < 10:
                    return None
                band = ink[int(y1 - (y1 - y0) * 0.13):y1, :]
                cols = band.any(axis=0)
                runs = []
                start = None
                for i in range(len(cols)):
                    if cols[i] and start is None:
                        start = i
                    elif not cols[i] and start is not None:
                        runs.append((start, i - 1)); start = None
                if start is not None:
                    runs.append((start, len(cols) - 1))
                if not runs:
                    return None
                dot = min(runs, key=lambda rr: rr[1] - rr[0])
                return ((dot[0] + dot[1]) / 2 - x0) / (x1 - x0)
            x1 = dot_x("با")
            x2 = dot_x("اب")
            if x1 is not None and x2 is not None:
                # اگر رندر RTL باشد: در «با» حرف ب سمت راست و در «اب» سمت چپ است
                _RENDERER_SHAPES = x1 > x2
        except Exception as e:
            print("⚠️ آزمون shaping:", e)
        return _RENDERER_SHAPES

    def _prepare_arabic_text(text, font_path):
        """متن را برای رندر آماده می‌کند — در همهٔ نسخه‌های Pillow درست نمایش داده میشه:
        - اگه خودِ Pillow shaping عربی (bidi+چسبندگی) را بدهد → متن منطقی همان‌طور که
          تایپ شده می‌رود (دوباره وارونه نمی‌شود).
        - اگه ندهد (Pillow قدیمی) → از روش کلاسیک reshaper+bidi استفاده می‌شود."""
        if not any('\u0600' <= ch <= '\u06FF' for ch in text):
            return text
        try:
            if _renderer_shapes_arabic(font_path):
                return text
        except Exception:
            pass
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text

    def _watermark_screenshot_sync(src_path, out_path):
        """کلمه روی اسکرین‌شات:
        - خودکار در خالی‌ترین ناحیه (اولویت پایین تصویر)
        - رنگ کاملاً متضاد با پس‌زمینه (سفید روی تیره / مشکی روی روشن)
        - کاور (کادر) نیمه‌شفاف پشت متن برای خوانایی کامل"""
        global SCREENSHOT_TEXT, SCREENSHOT_FORMAT, SCREENSHOT_TEXT_RATIO, FONT_PATH, SCREENSHOT_COVER_COLOR, SCREENSHOT_COVER_ALPHA
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as _pil_e:
            print("⚠️ خطای واردسازی Pillow — ترمیم خودکار و تلاش دوباره:", _pil_e)
            if not _pil_repair():
                print("❌ Pillow ترمیم نشد — این اسکرین‌شات رد می‌شود")
                return None
            from PIL import Image, ImageDraw, ImageFont
        try:
            img = Image.open(src_path).convert("RGB")
        except Exception as e:
            print("❌ خطا در خواندن اسکرین‌شات:", e)
            return None

        W, H = img.size

        # ۱) چهره‌ها + ماسک بدن (تا متن روی هیچ‌کدوم نیفتد)
        small = img.copy()
        small.thumbnail((240, 240))
        faces_norm = []
        person_mask = None
        try:
            if SCREENSHOT_AVOID_FACES:
                # تشخیص چهره با رزولوشن کامل تصویر (دقیق‌تر)
                fw, fh = img.size
                for (fx, fy, fww, fhh) in _detect_face_boxes(img):
                    faces_norm.append((fx / fw, fy / fh, fww / fw, fhh / fh))
                # سگمنتیشن کل بدن — حتی وقتی صورت در کادر دیده نمی‌شود
                person_mask = _detect_person_mask(img)
        except Exception as e:
            print("⚠️ خطا در تشخیص چهره/بدن:", e)
        if faces_norm:
            print(f"👤 {len(faces_norm)} چهره شناسایی شد — متن دور از چهره و بدن قرار می‌گیرد")
        elif person_mask is not None and person_mask.any():
            print("🧍 بدن در کادر دیده شد (بدون صورت) — متن دور از آن قرار می‌گیرد")

        text = (SCREENSHOT_TEXT or "").strip()
        if text:
            has_persian = any('\u0600' <= ch <= '\u06FF' for ch in text)
            font_path = _setup_persian_font() if has_persian else FONT_PATH
            can_draw = font_path is not None and os.path.exists(font_path)
            if has_persian and not can_draw:
                print("⚠️ فونت فارسی پیدا نشد — متن اسکرین‌شات اعمال نمی‌شود")
            if can_draw:
                try:
                    font_size = max(24, min(112, int(W * SCREENSHOT_TEXT_RATIO)))
                    font = ImageFont.truetype(font_path, font_size)

                    # شکل‌دهی فارسی — سازگار با همهٔ محیط‌ها (Pillow قدیمی و جدید)
                    shaped = _prepare_arabic_text(text, font_path)

                    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
                    l, t, r, b = probe.textbbox((0, 0), shaped, font=font)
                    tw, th = r - l, b - t
                    if tw > 12 and th > 12:
                        # کاور: عرض فقط دور متن (کم‌پدینگ)، ارتفاع فقط کمی بیشتر از متن
                        pad_x = int(tw * 0.08) + 6
                        pad_y = int(th * 0.15) + 5
                        box_w, box_h = tw + 2*pad_x, th + 2*pad_y
                        # باکس‌های چهره را به ناحیهٔ سر+بدن تبدیل می‌کنیم
                        avoid_norm = []
                        for (fx, fy, fww, fhh) in faces_norm:
                            cx = fx + fww / 2.0
                            pw = fww * 2.6
                            px = max(0.0, cx - pw / 2.0)
                            py = max(0.0, fy * 0.8)
                            avoid_norm.append((px, py, min(pw, 1.0 - px), max(0.0, 1.0 - py)))
                        # انتخاب مکان — باکس واقعی نباید روی بدن/چهره بیفتد
                        try:
                            cx_n, cy_n = _pick_text_region(small, box_w, box_h, person_mask, avoid_norm)
                        except Exception:
                            cx_n, cy_n = 0.5, 0.85
                        mx, my = int(W*0.01), int(H*0.01)
                        x0 = max(mx, min(W - box_w - mx, int(cx_n*W) - box_w//2))
                        y0 = max(my, min(H - box_h - my, int(cy_n*H) - box_h//2))

                        # ۲) کاور پررنگ + رنگ متن کاملاً متضاد با خودِ کاور
                        mode = (SCREENSHOT_TEXT_COLOR_MODE or "auto").lower()
                        cover_rgb = SCREENSHOT_COVER_COLOR or (0, 0, 0)
                        cover_fill = (int(cover_rgb[0]), int(cover_rgb[1]), int(cover_rgb[2]),
                                      int(max(60, min(255, SCREENSHOT_COVER_ALPHA))))
                        if mode == "white":
                            text_fill = (255, 255, 255, 255)
                        elif mode == "yellow":
                            text_fill = (255, 215, 0, 255)
                        else:  # auto — بر اساس روشنایی خودِ رنگ کاور
                            lum = 0.299*cover_rgb[0] + 0.587*cover_rgb[1] + 0.114*cover_rgb[2]
                            text_fill = (255, 255, 255, 255) if lum < 140 else (15, 15, 15, 255)

                        # ۳) کاور پررنگ + متن
                        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                        od = ImageDraw.Draw(overlay)
                        od.rounded_rectangle(
                            [x0, y0, x0+box_w, y0+box_h],
                            radius=max(8, int(box_h*0.24)), fill=cover_fill
                        )
                        od.text(
                            (x0 + (box_w - tw)//2 - l, y0 + (box_h - th)//2 - t),
                            shaped, font=font, fill=text_fill
                        )
                        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
                except Exception as e:
                    print("⚠️ خطا در رسم متن اسکرین‌شات:", e)

        # ۴) ذخیره با بالاترین کیفیت
        try:
            if (SCREENSHOT_FORMAT or "png").lower() == "png":
                img.save(out_path, "PNG", optimize=True)
            else:
                img.save(out_path, "JPEG", quality=95, subsampling=0)
            return out_path
        except Exception as e:
            print("❌ خطا در ذخیره اسکرین‌شات:", e)
            return None

    def _get_multiple_screenshots_sync(video_path, count=SCREENSHOT_COUNT):
        """استخراج فریم‌های PNG بدون افت، در رزولوشن کامل ویدیو؛ تعداد پیش‌فرض ۱۲."""
        screenshots = []
        try:
            duration_str = _get_duration_sync(video_path)
            duration = max(0.1, float(duration_str) if duration_str else 100.0)
            src = video_path
            if not is_valid_video(src):
                src = fix_video_file(src) or video_path
            count = max(1, int(count or SCREENSHOT_COUNT))
            # از ۴٪ تا ۹۶٪ ویدیو، با فاصلهٔ یکنواخت و دور از فریم‌های ابتدا/انتها
            ratios = [0.04 + (0.92 * i / max(1, count - 1)) for i in range(count)]
            capture_points = [max(0.0, min(duration - 0.03, duration * ratio)) for ratio in ratios]
            ext = ".png" if (SCREENSHOT_FORMAT or "png").lower() == "png" else ".jpg"
            for i, t in enumerate(capture_points):
                base = tempfile.mktemp(suffix=f"_pt{i}.png", dir=tempfile.gettempdir())
                out = tempfile.mktemp(suffix=f"_pt{i}_wm{ext}", dir=tempfile.gettempdir())
                try:
                    # PNG با رزولوشن اصلی؛ بدون scale و بدون فشرده‌سازی اتلافی
                    subprocess.run(
                        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", src,
                         "-frames:v", "1", "-an", "-c:v", "png", "-pred", "mixed", base],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180, check=False
                    )
                except Exception as e:
                    print(f"⚠️ خطا در گرفتن اسکرین‌شات {i + 1}:", e)
                if os.path.exists(base) and os.path.getsize(base) > 0:
                    wm_path = _watermark_screenshot_sync(base, out)
                    try:
                        os.remove(base)
                    except Exception:
                        pass
                    if wm_path:
                        screenshots.append(wm_path)
                else:
                    print(f"⚠️ فریم {i + 1} استخراج نشد")
            print(f"🖼️ فریم‌های آماده: {len(screenshots)}/{count} | PNG بی‌افت | رزولوشن اصلی")
            return screenshots
        except Exception as e:
            print("❌ خطا در گرفتن اسکرین‌شات‌ها:", e)
            return screenshots

    async def get_duration_async(video_path):
        duration_str = await asyncio.to_thread(_get_duration_sync, video_path)
        try:
            return float(duration_str)
        except:
            return None

    #================== اورلی ==================
    OVERLAY_PATH_FILE = os.path.join(RUNTIME_ROOT, "overlay_path.txt")

    def get_overlay_path():
        if os.path.exists(OVERLAY_PATH_FILE):
            try:
                with open(OVERLAY_PATH_FILE) as f:
                    p = f.read().strip()
                    if p and os.path.exists(p):
                        return p
            except: pass
        return None

    async def save_overlay_image(event):
        try:
            msg = event.message
            if not (msg.photo or msg.video or (
                msg.document and (msg.document.mime_type or "").startswith(("video", "image"))
            )):
                await event.reply("لطفاً عکس یا ویدیو (یا فایل ویدیویی) ارسال کنید.")
                return
            if msg.photo:
                ext = ".jpg"
            elif msg.video:
                ext = ".mp4"
            elif msg.document:
                mime = (msg.document.mime_type or "").lower()
                if "video" in mime: ext = ".mp4"
                elif "image" in mime: ext = ".jpg"
                else:
                    await event.reply("فقط عکس یا ویدیو قبول می‌شود.")
                    return
            else:
                await event.reply("فقط عکس یا ویدیو ارسال کنید.")
                return
            dest = os.path.join(RUNTIME_ROOT, f"overlay{ext}")
            path = await client.download_media(msg, file=dest)
            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                with open(OVERLAY_PATH_FILE, "w") as f:
                    f.write(path)
                overlay_type = "ویدیو متحرک" if ext == ".mp4" else "عکس"
                await event.reply(f"{overlay_type} اورلی با موفقیت ذخیره شد!")
            else:
                await event.reply("خطا در ذخیرهٔ اورلی — فایل دانلود نشد یا خالی است.")
        except Exception as e:
            await event.reply(f"خطا: {e}")

    #================== APPLY WATERMARK + OVERLAY ==================
    def _apply_watermark_sync(video_path, max_overlay_limit=None, progress_callback=None):
        global cancel_flag, WATERMARK_TEXT, FONT_PATH
        if cancel_flag: return None

        fixed_path = fix_video_file(video_path)
        if not fixed_path or not is_valid_video(fixed_path): return None

        overlay_file = get_overlay_path()
        apply_wm = WATERMARK_ENABLED
        apply_ol = OVERLAY_ENABLED and overlay_file and os.path.exists(overlay_file)

        if not apply_wm and not apply_ol:
            return None

        final_out = tempfile.mktemp(suffix=".mp4")
        fontsize = _get_fontsize_sync(fixed_path) if apply_wm else 0

        try:
            main_w, main_h = _get_video_dimensions_sync(fixed_path)
        except:
            main_w, main_h = 1280, 720

        try:
            total_duration = float(_get_duration_sync(fixed_path) or 0)
        except:
            total_duration = 0

        # رزولوشن و بیت‌ریت ویدیوی اصلی حفظ می‌شود؛ فقط واترمارک و اورلی با فیلتر باکیفیت ترکیب می‌شوند.
        # از CRF ثابت و بیت‌ریت بالا استفاده نمی‌کنیم تا ویدیوهای کم‌کیفیت بی‌دلیل حجیم و کند نشوند.
        try:
            source_bitrate_text = subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=bit_rate",
                "-of", "default=noprint_wrappers=1:nokey=1", fixed_path
            ], stderr=subprocess.DEVNULL).decode().strip()
            orig_bitrate = int(source_bitrate_text)
            if orig_bitrate <= 0:
                raise ValueError("video bitrate unavailable")
        except Exception:
            try:
                source_bitrate_text = subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=bit_rate",
                    "-of", "default=noprint_wrappers=1:nokey=1", fixed_path
                ], stderr=subprocess.DEVNULL).decode().strip()
                orig_bitrate = int(source_bitrate_text)
                if orig_bitrate <= 0:
                    raise ValueError("format bitrate unavailable")
            except Exception:
                orig_bitrate = 2_500_000

        target_bitrate = f"{max(250, int(orig_bitrate * 0.95 / 1000))}k"
        maxrate = f"{max(300, int(orig_bitrate / 1000))}k"
        bufsize = f"{max(600, int(orig_bitrate * 2 / 1000))}k"
        print(
            f"🎞️ رندر بدون تغییر کیفیت/رزولوشن ورودی: {main_w}x{main_h} | "
            f"بیت‌ریت ورودی {orig_bitrate/1000:.0f}k → خروجی {target_bitrate}"
        )

        cmd = ["ffmpeg", "-y", "-fflags", "+genpts", "-i", fixed_path]
        filter_complex = ""
        vout_label = "[0:v]"
        aout_label = "0:a?"

        if apply_wm:
            # تشخیص فارسی بودن متن
            has_persian = any('\u0600' <= c <= '\u06FF' for c in WATERMARK_TEXT)
            if has_persian:
                current_font = _setup_persian_font() or FONT_PATH
                font_option = f":fontfile='{current_font}'"
            else:
                font_option = ""

            filter_complex = (
                f"[0:v]drawtext=text='{WATERMARK_TEXT}'{font_option}:fontcolor=red:fontsize={fontsize}:borderw=2:bordercolor=yellow:"
                f"x='(w-text_w)/2 + (w/2-50)*sin(t*0.5 + sin(t*0.5)*2)':y='(h-text_h)/2 + (h/2-50)*cos(t*0.4 + cos(t*0.3)*2)':"
                f"enable='lt(mod(t,300),60)'[v1];"
                f"[v1]drawtext=text='{WATERMARK_TEXT}'{font_option}:fontcolor=red:fontsize={fontsize}:borderw=3:bordercolor=yellow:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(mod(t,300),60,65)'[v2];"
                f"[v2]drawtext=text='{WATERMARK_TEXT}'{font_option}:fontcolor=red:fontsize={fontsize}:borderw=3:bordercolor=yellow:"
                f"x=(w-text_w)/2:y=h-text_h-10:enable='gte(mod(t,300),65)'[vbase]"
            )
            vout_label = "[vbase]"

        if apply_ol:
            # تصویر ثابت اورلی را loop می‌کنیم تا روی تمام مدت ویدیو باقی بماند.
            overlay_ext = os.path.splitext(overlay_file)[1].lower()
            overlay_is_image = overlay_ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp")
            if overlay_is_image:
                cmd += ["-loop", "1", "-i", overlay_file]
                ov_dur = total_duration if total_duration > 0 else 36000.0
            else:
                cmd += ["-i", overlay_file]
                try:
                    ov_dur = float(subprocess.check_output([
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        overlay_file
                    ]).decode().strip())
                    if ov_dur <= 0:
                        ov_dur = total_duration if total_duration > 0 else 36000.0
                    if total_duration > 0:
                        ov_dur = min(ov_dur, total_duration)
                    if max_overlay_limit is not None:
                        ov_dur = min(ov_dur, float(max_overlay_limit))
                except Exception:
                    ov_dur = total_duration if total_duration > 0 else (float(max_overlay_limit) if max_overlay_limit is not None else 36000.0)

            overlay_has_audio = False
            source_has_audio = False
            try:
                overlay_audio_check = subprocess.check_output([
                    "ffprobe", "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=codec_type",
                    "-of", "csv=s=x:p=0", overlay_file
                ]).decode().strip()
                overlay_has_audio = "audio" in overlay_audio_check
            except Exception:
                pass
            try:
                source_audio_check = subprocess.check_output([
                    "ffprobe", "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=codec_type",
                    "-of", "csv=s=x:p=0", fixed_path
                ]).decode().strip()
                source_has_audio = "audio" in source_audio_check
            except Exception:
                pass

            ol_filter = (
                f";[1:v]scale={main_w}:{main_h}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={main_w}:{main_h}:(ow-iw)/2:(oh-ih)/2,"
                f"setsar=1[ol];"
                f"{vout_label}[ol]overlay=(W-w)/2:(H-h)/2:eof_action=pass:enable='between(t,0,{ov_dur})'[vout]"
            )
            if apply_wm:
                filter_complex += ol_filter
            else:
                filter_complex = ol_filter.lstrip(";")

            vout_label = "[vout]"
            if overlay_has_audio and source_has_audio and total_duration > ov_dur + 0.05:
                # اگر اورلی صدادار کوتاه‌تر از ویدیوی اصلی باشد، صدای اورلی سپس صدای اصلی پخش می‌شود.
                aout_label = "[aout]"
                filter_complex += (
                    f";[0:a]atrim=start={ov_dur},asetpts=PTS-STARTPTS[a0];"
                    f"[1:a]atrim=0:{ov_dur},asetpts=PTS-STARTPTS[a1];"
                    f"[a1][a0]concat=n=2:v=0:a=1[aout]"
                )
            elif overlay_has_audio:
                # اگر صدای اورلی تمام مدت را پوشش می‌دهد یا ویدیوی اصلی بی‌صداست.
                aout_label = "1:a?"
            else:
                # اورلی بی‌صداست؛ صدای ویدیوی اصلی حفظ می‌شود.
                aout_label = "0:a?"

        cmd += [
            "-filter_complex", filter_complex,
            "-map", vout_label, "-map", aout_label,
            "-map_metadata", "0", "-movflags", "+faststart"
        ]

        # همان انکود سریع قبلی: بیت‌ریت متناسب با ورودی، بدون ارتقای اجباری کیفیت و حجم
        cmd += [
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", target_bitrate, "-maxrate", maxrate, "-bufsize", bufsize,
            "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k"
        ]
        # لوپ عکس اورلی باز می‌ماند؛ خروجی حتماً به مدت ویدیوی اصلی محدود شود.
        if total_duration > 0:
            cmd += ["-t", f"{total_duration:.6f}"]
        cmd += [final_out]

        if cancel_flag: return None

        print("EXEC:", " ".join(cmd))
        start_time = time.time()
        last_pct = -1

        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1
        )
        try:
            for line in p.stdout:
                if cancel_flag:
                    p.kill()
                    break
                print(line.rstrip())
                if total_duration > 0 and progress_callback and "time=" in line:
                    try:
                        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                        if time_match:
                            h = int(time_match.group(1))
                            m = int(time_match.group(2))
                            s = float(time_match.group(3))
                            current_sec = h * 3600 + m * 60 + s
                            pct = min(int(current_sec * 100 / total_duration), 99)
                            if pct - last_pct >= 10:
                                last_pct = pct
                                elapsed = time.time() - start_time
                                if pct > 0:
                                    total_est = elapsed * 100 / pct
                                    remaining = total_est - elapsed
                                    mins = int(remaining // 60)
                                    secs = int(remaining % 60)
                                    eta_str = f"{mins}:{secs:02d}"
                                else:
                                    eta_str = "..."
                                progress_callback(pct, eta_str)
                    except:
                        pass
        except Exception as e:
            print("run() read error:", e)

        p.wait()

        # چون فقط libx264 اجرا می‌شود، هر خطای FFmpeg مستقیماً گزارش می‌شود.
        if p.returncode != 0:
            print(f"❌ پردازش ویدیو ناموفق بود (کد {p.returncode}).")
            return None
        if not os.path.exists(final_out): return None
        if cancel_flag: return None

        if os.path.exists(final_out) and is_valid_video(final_out):
            in_mb  = os.path.getsize(fixed_path) / 1024 / 1024
            out_mb = os.path.getsize(final_out)  / 1024 / 1024
            print(f"✅ فایل نهایی آماده | ورودی: {in_mb:.1f} MB → خروجی: {out_mb:.1f} MB")
            return final_out
        return None

    # ================== ساخت تامبنیل سازگار با تلگرام ==================
    def _make_telegram_thumbnail_sync(image_path):
        """ساخت کاور JPEG با حداکثر وضوح 320px و بالاترین کیفیت قابل‌قبول زیر 20KB تلگرام."""
        if not image_path or not os.path.exists(image_path):
            return None
        out_path = tempfile.mktemp(suffix="_telegram_thumb.jpg", dir=tempfile.gettempdir())
        try:
            from PIL import Image, ImageFilter, ImageOps
            with Image.open(image_path) as source:
                img = ImageOps.exif_transpose(source).convert("RGB")
            resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            img.thumbnail((320, 320), resampling)
            # Sharpen only after downscaling; the source video and original screenshot stay untouched.
            img = img.filter(ImageFilter.UnsharpMask(radius=0.45, percent=55, threshold=3))
            max_bytes = 19_990  # comfortably below Telegram thumbnail limits

            # Highest JPEG quality first. optimize=True reduces file size without reducing image quality.
            for quality in range(100, 9, -1):
                img.save(
                    out_path, "JPEG", quality=quality, optimize=True,
                    progressive=False, subsampling=0
                )
                current_size = os.path.getsize(out_path)
                if current_size <= max_bytes:
                    print(
                        f"✅ کاور نهایی با بیشترین کیفیت مجاز: {img.width}x{img.height} | "
                        f"{current_size / 1024:.2f} KB | Q={quality}"
                    )
                    return out_path

            # If a highly detailed frame still exceeds 20KB, trade a little resolution before quality.
            for side in (312, 304, 296, 288, 272, 256):
                small = img.copy()
                small.thumbnail((side, side), resampling)
                for quality in range(100, 9, -1):
                    small.save(
                        out_path, "JPEG", quality=quality, optimize=True,
                        progressive=False, subsampling=0
                    )
                    current_size = os.path.getsize(out_path)
                    if current_size <= max_bytes:
                        print(
                            f"✅ کاور فشردهٔ باکیفیت: {small.width}x{small.height} | "
                            f"{current_size / 1024:.2f} KB | Q={quality}"
                        )
                        return out_path
            if os.path.exists(out_path):
                os.remove(out_path)
            print("⚠️ ساخت کاور زیر 20KB ممکن نشد؛ تلگرام کاور خودکار می‌سازد.")
            return None
        except Exception as e:
            print("⚠️ ساخت کاور تلگرام ناموفق بود:", e)
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception:
                pass
            return None

    # =====================================================================================
    #  لایهٔ دانلود — بازنویسی‌شده (نسخهٔ ۲)
    #  ------------------------------------------------------------------------------------
    #  سه باگ اصلی که باعث می‌شد لینک‌های CDN (مثل pvvstream/ukdevilz) ۴۰۳ بگیرند:
    #   ۱) هدر Referer اشتباه: برای لینک فایل، Referer روی دامنهٔ خودِ CDN ست می‌شد
    #      (https://pvvstream.pro/) و هات‌لینک‌پروتکشن CDN دقیقاً همین را ۴۰۳ می‌کند.
    #   ۲) لینک‌های امضاشده (secure=...) در HTML با \\u0026 نوشته شده‌اند؛ رجکس قبلی
    #      آن‌ها را نصفه برمی‌داشت (vid_720p.mp4?rs=720000) و توکن گم می‌شد → ۴۰۳.
    #   ۳) دانلود تک‌اتصالی و بدون تأیید حجم: فایل ۹۷۰ مگی نصفه دانلود می‌شد،
    #      ffprobe خطا می‌داد و کل نتیجه دور ریخته می‌شد.
    #  حالا: probe با ماتریس هدر/بک‌اند → دانلود تکه‌ای چنداتصاله با Range →
    #  تمدید خودکار توکن منقضی → تأیید حجم دقیق → remux/ ffprobe ایمن.
    # =====================================================================================

    UA_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

    DIRECT_CONNECTIONS = 16                  # تعداد اتصال هم‌زمان برای فایل مستقیم
    DIRECT_SEGMENT_SIZE = 16 * 1024 * 1024   # اندازهٔ هر تکه در صف دانلود
    _PROBE_CACHE = {}
    _CURL_CFFI_OK = None

    _TEXT_ESCAPES = (
        ("\\u0026", "&"), ("\\u002F", "/"), ("\\u002f", "/"), ("\\/", "/"),
        ("\\u003D", "="), ("\\u003d", "="),
        ("&amp;", "&"), ("&#38;", "&"), ("&#x26;", "&"), ("&quot;", '"'), ("&#x2F;", "/"),
    )


    def _unescape_text(text):
        """\\u0026 / &amp; / \\/ را باز می‌کند؛ بدون این کار لینک‌های امضاشدهٔ CDN ناقص می‌شوند."""
        if not text:
            return ""
        out = text
        for a, b in _TEXT_ESCAPES:
            out = out.replace(a, b)
        return out


    def _normalize_url(url):
        u = _unescape_text((url or "").strip().strip("'\"").strip())
        return u.rstrip(".,;")


    _MEDIA_EXT_RE = re.compile(
        r"\.(mp4|m4v|mkv|webm|mov|flv|f4v|3gp|ts|m3u8|m3u|mpd|mp3|m4a|aac|ogg|zip)$", re.I
    )


    def _looks_like_media(url):
        try:
            p = urlparse(_normalize_url(url))
        except Exception:
            return False
        path = (p.path or "").rstrip("/")
        if _MEDIA_EXT_RE.search(path):
            return True
        q = (p.query or "").lower()
        return any(k in q for k in ("download=true", "download=1", "dl=1", "filename="))


    def _looks_like_hls(url):
        low = _normalize_url(url).lower()
        return ".m3u8" in low or ".m3u" in low or ".mpd" in low


    def _origin_of(url):
        try:
            p = urlparse(url)
        except Exception:
            return None
        if not p.scheme or not p.hostname:
            return None
        return f"{p.scheme}://{p.hostname}"


    # ================== هدر هوشمند ==================
    def _get_smart_headers(url, referer=None, for_media=None):
        """هدر مناسب همان میزبان.

        قاعدهٔ طلایی: برای «فایل/CDN» هرگز Referer دامنهٔ خودِ CDN را نفرست؛
        یا باید Referer صفحهٔ میزبان (page_referer) باشد یا هیچ Referer ای.
        """
        url = _normalize_url(url)
        lower = (url or "").lower()
        ua = UA_CHROME
        if for_media is None:
            for_media = _looks_like_media(url)

        if "phncdn.com" in lower or "pornhub" in lower:
            return {
                "User-Agent": ua, "Referer": "https://www.pornhub.com/",
                "Origin": "https://www.pornhub.com", "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Cookie": "accessAgeDisclaimer=1; platform=pc; ua=1; bs=1",
            }
        if "ahcdn.com" in lower or "beeg" in lower:
            return {"User-Agent": ua, "Referer": "https://beeg.com/", "Origin": "https://beeg.com", "Accept": "*/*"}
        if "xvideos" in lower or "xvcdn" in lower:
            return {"User-Agent": ua, "Referer": "https://www.xvideos.com/", "Origin": "https://www.xvideos.com", "Accept": "*/*"}
        if "xhamster" in lower or "xhcdn" in lower:
            return {"User-Agent": ua, "Referer": "https://xhamster.com/", "Origin": "https://xhamster.com", "Accept": "*/*"}
        if "spankbang" in lower:
            return {"User-Agent": ua, "Referer": "https://spankbang.com/", "Origin": "https://spankbang.com", "Accept": "*/*"}
        if "eporner" in lower:
            return {"User-Agent": ua, "Referer": "https://www.eporner.com/", "Origin": "https://www.eporner.com", "Accept": "*/*"}
        if "dood" in lower or "do0od" in lower:
            return {"User-Agent": ua, "Referer": "https://doodstream.com/", "Accept": "*/*"}
        if "streamtape" in lower:
            return {"User-Agent": ua, "Referer": "https://streamtape.com/", "Accept": "*/*"}

        headers = {"User-Agent": ua, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
        if referer:
            headers["Referer"] = _normalize_url(referer)
            org = _origin_of(referer)
            if org:
                headers["Origin"] = org
        elif not for_media:
            # درخواست یک «صفحهٔ وب» است؛ ارجاع به دامنهٔ خودش طبیعی است.
            org = _origin_of(url)
            if org:
                headers["Referer"] = org + "/"
                headers["Origin"] = org
                headers["Cookie"] = "age_verified=1; ageverified=1; agecheck=1; disclaimer=1; adult=1; over18=1"
        return headers


    # ================== لایهٔ دسترسی (requests / curl_cffi) ==================
    def _has_curl_cffi():
        global _CURL_CFFI_OK
        if _CURL_CFFI_OK is None:
            try:
                from curl_cffi import requests as _creq  # noqa: F401
                _CURL_CFFI_OK = True
            except Exception:
                _CURL_CFFI_OK = False
        return _CURL_CFFI_OK


    def _open_stream(url, headers, backend="requests", timeout=(20, 60)):
        """response استریمی. backend=curl_cffi اثر انگشت TLS کروم را می‌فرستد (ضد Cloudflare)."""
        if backend == "curl_cffi" and _has_curl_cffi():
            from curl_cffi import requests as creq
            return creq.get(url, headers=headers, impersonate="chrome", timeout=timeout,
                            stream=True, allow_redirects=True)
        return requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)


    _MEDIA_CT_HINTS = (
        "video/", "audio/", "application/octet-stream", "application/mp4", "binary/octet-stream",
        "mpegurl", "dash+xml", "matroska", "vnd.apple",
    )


    def _is_media_ct(ct, cd=""):
        ct = (ct or "").lower()
        cd = (cd or "").lower()
        return any(h in ct for h in _MEDIA_CT_HINTS) or "attachment" in cd


    def _probe_media_access(url, page_referer=None):
        """با درخواست ۲ بایتی (Range) کشف می‌کند کدام هدر/بک‌اند جواب می‌دهد.

        خروجی: dict(backend, headers, total, ranges, content_type, kind) یا None
        نکته: هیچ‌وقت بدنهٔ فایل خوانده نمی‌شود؛ پس حتی برای فایل ۱ گیگی هم فوری است.
        """
        url = _normalize_url(url)
        try:
            host = (urlparse(url).hostname or "").lower()
        except Exception:
            host = ""
        try:
            parsed = urlparse(url)
            path_key = (parsed.netloc or "") + (parsed.path or "")
        except Exception:
            path_key = host
        cache_key = (path_key, (page_referer or "")[:120], _looks_like_hls(url))
        if cache_key in _PROBE_CACHE:
            info = dict(_PROBE_CACHE[cache_key])
            info["url"] = url
            return info

        known = any(k in host for k in ("phncdn", "ahcdn", "xhcdn", "xvcdn", "spankbang",
                                        "eporner", "dood", "do0od", "streamtape", "beeg"))
        profiles = []
        if known:
            profiles.append(("site", _get_smart_headers(url)))
        if page_referer:
            profiles.append(("page", _get_smart_headers(url, referer=page_referer, for_media=True)))
        profiles.append(("clean", _get_smart_headers(url, for_media=True)))

        seen_sig, uniq_profiles = set(), []
        for name, h in profiles:
            sig = tuple(sorted(h.items()))
            if sig in seen_sig:
                continue
            seen_sig.add(sig)
            uniq_profiles.append((name, h))

        backends = ["requests"] + (["curl_cffi"] if _has_curl_cffi() else [])
        tried = []
        for backend in backends:
            for name, base_headers in uniq_profiles:
                headers = dict(base_headers)
                headers["Range"] = "bytes=0-1"
                resp = None
                try:
                    resp = _open_stream(url, headers, backend, timeout=(15, 25))
                    status = resp.status_code
                    ct = resp.headers.get("content-type") or ""
                    cd = resp.headers.get("content-disposition") or ""
                    content_range = resp.headers.get("content-range") or ""
                    if status == 530:
                        server_header = (resp.headers.get("server") or "").lower()
                        cf_ray = resp.headers.get("cf-ray") or ""
                        error_code = None
                        try:
                            error_body = next(resp.iter_content(chunk_size=4096), b"").decode("utf-8", errors="replace")
                            code_match = re.search(r"\b(1\d{3})\b", error_body[:6000])
                            if code_match:
                                error_code = code_match.group(1)
                        except Exception:
                            pass
                        is_cloudflare = "cloudflare" in server_header or bool(cf_ray)
                        if is_cloudflare:
                            detail = f" | کد 1xxx={error_code}" if error_code else ""
                            ray_detail = f" | Ray={cf_ray[:24]}" if cf_ray else ""
                            print(f"⛔ Cloudflare HTTP 530 در {backend}/{name}{detail}{ray_detail}؛ این پاسخ با تعویض هدر حل نمی‌شود", flush=True)
                            return None
                    total, ranges = 0, False
                    m = re.search(r"/\s*(\d+)\s*$", content_range)
                    if m:
                        total = int(m.group(1))
                        ranges = True
                    elif status == 206:
                        ranges = True
                    if not total and status == 200:
                        try:
                            total = int(resp.headers.get("content-length") or 0)
                        except Exception:
                            total = 0

                    if status == 416:  # فایل کوچک‌تر از بازهٔ درخواستی
                        try:
                            resp.close()
                        except Exception:
                            pass
                        headers.pop("Range", None)
                        resp = _open_stream(url, headers, backend, timeout=(15, 25))
                        status = resp.status_code
                        ct = resp.headers.get("content-type") or ""
                        cd = resp.headers.get("content-disposition") or ""
                        ranges = False
                        try:
                            total = int(resp.headers.get("content-length") or 0)
                        except Exception:
                            total = 0

                    is_hls = _looks_like_hls(url)
                    # صفحهٔ HTML را هرگز «فایل» حساب نکن (وگرنه اسکرپ/دانلود قاطی می‌شود)
                    looks_like_file = ranges and not ct.startswith("text/html")
                    ok = status in (200, 206) and (_is_media_ct(ct, cd) or is_hls or looks_like_file)
                    print(
                        f"🔎 probe[{backend}/{name}]: {status} | {(ct or '?').split(';')[0]} | "
                        f"size={total or '?'} | range={'yes' if ranges else 'no'}"
                    )
                    if ok:
                        headers.pop("Range", None)
                        headers.pop("range", None)
                        info = {
                            "backend": backend,
                            "headers": headers,
                            "total": total,
                            "ranges": ranges,
                            "content_type": ct,
                            "kind": "hls" if is_hls else "file",
                            "profile": name,
                        }
                        if not is_hls:
                            _PROBE_CACHE[cache_key] = dict(info)
                        return info
                    tried.append(f"{backend}/{name}:{status}")
                except Exception as e:
                    tried.append(f"{backend}/{name}:ERR {type(e).__name__}")
                finally:
                    if resp is not None:
                        try:
                            resp.close()
                        except Exception:
                            pass

        print("❌ probe: هیچ پروفایل هدر/بک‌اندی جواب نداد →", "، ".join(tried) or "?")
        return None


    # ================== دانلود تکه‌ای چنداتصاله ==================
    def _download_segmented_sync(url, filepath, headers, backend, total, ranges,
                                status_msg, loop, resign=None, connections=None):
        """دانلود فایل با Range در چند اتصال هم‌زمان + ادامه از محل قطع + تمدید توکن.

        - نوشتن با os.pwrite (نوشتن در آفست مشخص) → امن برای چند ترد، بدون قفل.
        - اگر سرور Range نداشت، تک‌اتصالی و ترتیبی دانلود می‌کند.
        - اگر وسط کار ۴۰۱/۴۰۳/۴۱۰ گرفت (توکن امضاشده منقضی شد) با resign لینک تازه می‌گیرد.
        """
        import threading
        import queue as _queue

        url = _normalize_url(url)
        if not ranges or total <= 0:
            connections = 1
        else:
            try:
                connections = max(1, min(int(connections or DIRECT_CONNECTIONS), 16))
            except Exception:
                connections = DIRECT_CONNECTIONS

        state = {
            "done": 0,
            "url": url,
            "stop": False,
            "error": None,
            "last_edit": 0.0,
            "started": time.time(),
        }
        lock = threading.Lock()

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            if total > 0:
                try:
                    os.ftruncate(fd, total)
                except Exception:
                    pass

            tasks = _queue.Queue()
            if total > 0:
                if ranges:
                    offset = 0
                    while offset < total:
                        end = min(offset + DIRECT_SEGMENT_SIZE, total) - 1
                        tasks.put((offset, end))
                        offset = end + 1
                else:
                    tasks.put((0, total - 1))

            def _worker():
                while True:
                    if state["stop"] or cancel_flag:
                        return
                    try:
                        seg_start, seg_end = tasks.get_nowait()
                    except _queue.Empty:
                        return
                    pos = seg_start
                    attempts = 0
                    while pos <= seg_end:
                        if state["stop"] or cancel_flag:
                            return
                        current_url = state["url"]
                        req_headers = dict(headers)
                        if ranges:
                            req_headers["Range"] = f"bytes={pos}-{seg_end}"
                        resp = None
                        try:
                            resp = _open_stream(current_url, req_headers, backend, timeout=(20, 60))
                            code = resp.status_code

                            if code in (401, 403, 410):
                                try:
                                    resp.close()
                                except Exception:
                                    pass
                                resp = None
                                new_url = None
                                if resign is not None and attempts < 3:
                                    try:
                                        new_url = resign(current_url)
                                    except Exception as _exc:
                                        print("⚠️ تمدید لینک ناموفق:", _exc)
                                if new_url and _normalize_url(new_url) != current_url:
                                    with lock:
                                        state["url"] = _normalize_url(new_url)
                                    print("🔗 توکن لینک تمدید شد → ادامهٔ دانلود")
                                    attempts += 1
                                    continue
                                state["error"] = f"HTTP {code} (CDN اجازه نداد / لینک منقضی)"
                                state["stop"] = True
                                return

                            if code not in (200, 206):
                                try:
                                    resp.close()
                                except Exception:
                                    pass
                                resp = None
                                attempts += 1
                                if attempts >= 5:
                                    state["error"] = f"HTTP {code}"
                                    state["stop"] = True
                                    return
                                time.sleep(min(2 * attempts, 8))
                                continue

                            # سرور Range را نادیده گرفته و کل فایل را فرستاده؛ نوشتن آن در آفست
                            # غلط فایل را خراب می‌کند → فقط برای تکهٔ اول (آفست ۰) مجاز است.
                            if ranges and code == 200 and pos != 0:
                                try:
                                    resp.close()
                                except Exception:
                                    pass
                                resp = None
                                attempts += 1
                                if attempts >= 3:
                                    state["error"] = "سرور Range را نادیده گرفت"
                                    state["stop"] = True
                                    return
                                time.sleep(1)
                                continue

                            got = 0
                            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                                if not chunk:
                                    continue
                                if state["stop"] or cancel_flag:
                                    break
                                if ranges and pos + len(chunk) - 1 > seg_end:
                                    chunk = chunk[: seg_end - pos + 1]
                                os.pwrite(fd, chunk, pos)
                                pos += len(chunk)
                                got += len(chunk)
                                with lock:
                                    state["done"] += len(chunk)
                            try:
                                resp.close()
                            except Exception:
                                pass
                            resp = None

                            if got == 0 and pos <= seg_end and not ranges:
                                attempts += 1
                                if attempts >= 5:
                                    state["error"] = "هیچ داده‌ای دریافت نشد"
                                    state["stop"] = True
                                    return
                                time.sleep(1)
                        except Exception as e:
                            if resp is not None:
                                try:
                                    resp.close()
                                except Exception:
                                    pass
                            attempts += 1
                            if attempts >= 5:
                                state["error"] = f"{type(e).__name__}: {e}"
                                state["stop"] = True
                                return
                            time.sleep(min(2 * attempts, 8))

            threads = [threading.Thread(target=_worker, daemon=True) for _ in range(connections)]
            for t in threads:
                t.start()

            while True:
                if cancel_flag:
                    state["stop"] = True
                alive = any(t.is_alive() for t in threads)
                now = time.time()
                if now - state["last_edit"] >= 2 or (not alive):
                    state["last_edit"] = now
                    done = state["done"]
                    elapsed = max(0.001, now - state["started"])
                    speed = done / 1048576 / elapsed
                    if total > 0:
                        pct = min(100, int(done * 100 / total))
                        filled = min(20, pct // 5)
                        bar = "█" * filled + "░" * (20 - filled)
                        remaining = max(0, total - done) / 1048576
                        eta = int(remaining / speed) if speed > 0.01 else 0
                        text = (
                            f"⚡ دانلود تکه‌ای ({connections} اتصال)\n[{bar}] {pct}%\n"
                            f"📦 {done / 1048576:.1f}/{total / 1048576:.1f} MB | "
                            f"{speed:.1f} MB/s | {eta // 60}:{eta % 60:02d}"
                        )
                    else:
                        text = f"⬇️ دانلود مستقیم...\n📦 {done / 1048576:.1f} MB | {speed:.1f} MB/s"
                    try:
                        asyncio.run_coroutine_threadsafe(safe_edit(status_msg, text), loop)
                    except Exception:
                        pass
                if not alive:
                    break
                time.sleep(0.5)
        finally:
            try:
                os.close(fd)
            except Exception:
                pass

        if cancel_flag or state["stop"]:
            raise IOError(state["error"] or "دانلود متوقف شد")

        final_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        if total > 0 and final_size != total:
            # فایل sparse ممکن است اندازهٔ ظاهری درست داشته باشد ولی داده کم داشته باشد
            if state["done"] != total:
                raise IOError(f"فایل ناقص است: {state['done']}/{total} بایت")
        return True


    async def _download_from_access(url, filepath, status_msg, access, resign=None, connections=None):
        """دانلود با اطلاعاتی که probe پیدا کرده (هدر درست + بک‌اند درست)."""
        url = _normalize_url(url)
        if not access:
            return None
        if access.get("kind") == "hls":
            print("ℹ️ محتوا HLS است؛ دانلود تکه‌ای HTTP انجام نشد")
            return None

        backend = access.get("backend") or "requests"
        headers = dict(access.get("headers") or {})
        total = int(access.get("total") or 0)
        ranges = bool(access.get("ranges"))

        if total > 0:
            await safe_edit(
                status_msg,
                f"⚡ دانلود تکه‌ای ({DIRECT_CONNECTIONS} اتصال) — {total / 1048576:.1f} MB"
                if ranges else f"⬇️ دانلود مستقیم — {total / 1048576:.1f} MB",
            )
        else:
            await safe_edit(status_msg, "⬇️ دانلود مستقیم (حجم نامشخص)...")

        loop = asyncio.get_event_loop()
        try:
            await asyncio.to_thread(
                _download_segmented_sync, url, filepath, headers, backend, total,
                ranges, status_msg, loop, resign, connections,
            )
        except Exception as e:
            print(f"❌ دانلود مستقیم ناموفق: {e}")
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except OSError:
                pass
            return None

        if cancel_flag:
            try:
                os.remove(filepath)
            except OSError:
                pass
            return None

        if os.path.isfile(filepath) and os.path.getsize(filepath) > 100_000:
            print(f"✅ دانلود کامل شد: {os.path.getsize(filepath) / 1048576:.1f} MB")
            return filepath
        print("❌ فایل خروجی خیلی کوچک/ناموجود است")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass
        return None


    def _resign_media_url_sync(page_url, old_url, quality):
        """لینک امضاشده منقضی شده → نسخهٔ تازه را از همان صفحه می‌گیرد (همان مسیر/کیفیت)."""
        if not page_url:
            return None
        try:
            html = _http_get(page_url)
        except Exception as e:
            print("⚠️ تمدید لینک:", e)
            return None
        candidates = _media_candidates_from_html(html, page_url, page_url)
        if not candidates:
            return None
        old_path = urlparse(old_url).path
        same_path = [c for c in candidates if urlparse(c["url"]).path == old_path]
        if same_path:
            return same_path[0]["url"]
        best = _pick_best_candidate(candidates, quality)
        return best["url"] if best else None


    # ================== Chromium sniff + session capture ==================
    _CHROMIUM_SESSION_HEADERS = {}
    _SAFE_BROWSER_HEADERS = (
        "accept", "accept-language", "referer", "origin", "cookie", "user-agent",
        "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site",
        "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
    )
    _SKIP_BROWSER_HEADERS = {"range", "host", "connection", "content-length", "accept-encoding", "priority", "te"}


    def _filter_browser_headers(raw):
        """هدرهای ضبط‌شدهٔ مرورگر را به یک مجموعهٔ امن/قابل استفاده تبدیل می‌کند."""
        out = {}
        for key, value in (raw or {}).items():
            if not key or value is None:
                continue
            k = str(key).strip().lower()
            if k in _SKIP_BROWSER_HEADERS:
                continue
            if k in _SAFE_BROWSER_HEADERS or k.startswith("sec-"):
                out[key if key != k else k] = str(value)
        # کلیدها را استاندارد کن
        return {("-".join(part.capitalize() for part in k.split("-")) if "-" in k else k.capitalize()): v
                for k, v in out.items()}


    async def download_with_chromium_enhanced(url, status_msg, quality=None):
        """Chromium sniff با timeout مرحله‌ای، لاگ زنده و جمع‌آوری پاسخ اصلی صفحه."""
        global _CHROMIUM_SESSION_HEADERS
        url = _normalize_url(url)
        video_url = None
        exts = (".m3u8", ".mpd", ".mp4", ".mkv", ".webm", ".flv", ".mov", ".m4v", ".m3u")
        REAL_UA = UA_CHROME
        captured_headers = {}
        found_urls = []
        verified_media_urls = set()
        playwright = None
        browser = None
        stage = "راه‌اندازی Playwright"

        def log(message):
            print(message, flush=True)

        def _is_thumb(low):
            return any(x in low for x in ("/vts:", "rs:fit:", "/thumb", "/thumbnail",
                                          "preview", "poster", "sprite", "/ads", "splash"))

        try:
            await safe_edit(status_msg, "🌐 Chromium: راه‌اندازی مرورگر...")
            log("🚀 Chromium: شروع Playwright")
            playwright = await asyncio.wait_for(async_playwright().start(), timeout=20)

            stage = "اجرای Chromium"
            log("🚀 Chromium: اجرای موتور مرورگر...")
            browser = await asyncio.wait_for(
                playwright.chromium.launch(
                    headless=True,
                    timeout=25000,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                          "--disable-dev-shm-usage", "--ignore-certificate-errors"],
                ),
                timeout=30,
            )
            log("✅ Chromium: مرورگر اجرا شد")

            stage = "ساخت نشست مرورگر"
            context = await asyncio.wait_for(
                browser.new_context(
                    user_agent=REAL_UA, viewport={"width": 1920, "height": 1080},
                    locale="en-US", extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                ),
                timeout=15,
            )
            page = await context.new_page()
            page.set_default_timeout(7000)
            page.set_default_navigation_timeout(35000)

            def _is_media_segment(raw):
                low = raw.lower().split("?", 1)[0]
                return low.endswith((".ts", ".m4s", ".cmfv", ".cmfa", ".aac", ".ac3", ".ec3")) or bool(
                    re.search(r"(?:^|[/_.-])(?:seg|segment|chunk)[_-]?\d+(?:\.|$)", low)
                )

            def _is_media_manifest_or_file(raw, content_type="", resource_type=""):
                low = raw.lower()
                ct = (content_type or "").lower().split(";", 1)[0].strip()
                if _is_media_segment(raw) or _is_thumb(low):
                    return False
                if ct in ("video/mp2t", "video/iso.segment", "audio/iso.segment",
                          "audio/aac", "audio/mpeg"):
                    return False
                if any(ext in low for ext in exts):
                    return True
                if any(mark in low for mark in ("/manifest", "playlist", "master.m3u", ".m3u8", ".mpd")):
                    return True
                if ("video/" in ct or "mpegurl" in ct or "dash+xml" in ct
                        or ct in ("application/vnd.apple.mpegurl", "application/x-mpegurl")):
                    return True
                return resource_type == "media"

            async def handle_request(req):
                try:
                    raw = _normalize_url(req.url)
                    resource_type = getattr(req, "resource_type", "") or ""
                    if (_is_media_manifest_or_file(raw, resource_type=resource_type)
                            and raw not in found_urls):
                        found_urls.append(raw)
                        verified_media_urls.add(raw)
                        captured_headers[raw] = dict(req.headers)
                        log(f"🎯 Chromium Request [{resource_type or '?'}]: {raw[:180]}")
                except Exception as exc:
                    log(f"⚠️ Chromium request-capture: {type(exc).__name__}: {exc}")

            async def handle_response(resp):
                try:
                    raw = _normalize_url(resp.url)
                    h = await resp.all_headers()
                    ct = (h.get("content-type") or "").lower()
                    resource_type = getattr(resp.request, "resource_type", "") or ""
                    media_like = _is_media_manifest_or_file(raw, ct, resource_type)
                    if media_like and resp.status >= 400:
                        host = urlparse(raw).hostname or "?"
                        log(f"⚠️ Chromium media HTTP {resp.status} | {host} | {ct.split(';')[0] or '?'}")
                    if media_like and 200 <= resp.status < 400:
                        verified_media_urls.add(raw)
                    if (media_like and 200 <= resp.status < 400 and raw not in found_urls):
                        found_urls.append(raw)
                        try:
                            captured_headers[raw] = dict(resp.request.headers)
                        except Exception:
                            pass
                        log(f"🎯 Chromium Response [{resp.status} / {ct[:50]} / {resource_type or '?'}]: {raw[:180]}")
                except Exception as exc:
                    log(f"⚠️ Chromium response-capture: {type(exc).__name__}: {exc}")

            def handle_request_failed(req):
                try:
                    parsed = urlparse(req.url)
                    host_path = f"{parsed.hostname or '?'}{parsed.path[:70]}"
                    failure = getattr(req, "failure", None) or "network error"
                    log(f"⚠️ Chromium request failed | {host_path} | {str(failure)[:120]}")
                except Exception:
                    pass

            page.on("request", handle_request)
            page.on("response", handle_response)
            page.on("requestfailed", handle_request_failed)

            stage = "بازکردن صفحهٔ سایت"
            await safe_edit(status_msg, "🌐 Chromium: باز کردن صفحه و بررسی پاسخ سایت...")
            log(f"🌐 Chromium: باز کردن {url[:180]}")
            main_response = None
            try:
                main_response = await asyncio.wait_for(
                    page.goto(url, timeout=35000, wait_until="domcontentloaded"),
                    timeout=38,
                )
                if main_response is not None:
                    log(f"📡 Chromium page response: HTTP {main_response.status} | {page.url[:180]}")
                    if main_response.status == 530:
                        detail = ""
                        try:
                            body = await asyncio.wait_for(main_response.text(), timeout=3)
                            code_match = re.search(r"\b(1\d{3})\b", body[:6000])
                            if code_match:
                                detail = f" | کد Cloudflare: {code_match.group(1)}"
                        except Exception:
                            pass
                        log(f"⛔ Chromium: صفحه با HTTP 530 برگشت؛ ادامهٔ پخش ممکن نیست{detail}")
                        await safe_edit(status_msg, f"⛔ سایت/CDN پاسخ HTTP 530 داد؛ صفحه باز نشد{detail}")
                        return None
            except asyncio.TimeoutError:
                log("⏱️ Chromium: مهلت بازکردن صفحه تمام شد؛ بررسی منابع دریافتی ادامه می‌یابد")
            except Exception as exc:
                log(f"⚠️ Chromium page.goto: {type(exc).__name__}: {exc}")

            stage = "پخش و شنود درخواست ویدیو در صفحه و iframeها"
            await safe_edit(status_msg, "🌐 Chromium: بررسی پلیر اصلی و iframeها...")
            log("🔎 Chromium: جست‌وجوی پلیر در تمام frameها آغاز شد")
            clicked_frames = set()
            last_frame_signature = None

            scanned_frame_ids = set()
            active_frame_ids = set()
            last_frame_signature = None

            async def inspect_and_activate_frames(initial=False):
                nonlocal last_frame_signature
                frames = list(page.frames)
                # در بعضی پلیرها ده‌ها iframe تبلیغاتی ساخته می‌شود؛ ابتدا فریم‌های پلیر/CDN بررسی می‌شوند.
                def frame_priority(frame):
                    low = (frame.url or "").lower()
                    if any(mark in low for mark in ("xv-cdn", "video", "player", "embed", "stream", "media")):
                        return 0
                    if any(mark in low for mark in ("doubleclick", "analytics", "banner", "advert", "/ads", "tracking")):
                        return 3
                    return 1

                ordered_frames = sorted(enumerate(frames), key=lambda item: (frame_priority(item[1]), item[0]))
                # سقف ۷۲ فریم برای جلوگیری از گیرکردن روی صفحات دارای iframeهای نامحدود؛ ۶۲ فریم لاگ قبلی همگی پوشش داده می‌شوند.
                selected = ordered_frames[:72]
                if initial:
                    scan_list = selected
                else:
                    scan_list = [item for item in selected
                                 if id(item[1]) not in scanned_frame_ids or id(item[1]) in active_frame_ids
                                 or item[1] == page.main_frame]

                semaphore = asyncio.Semaphore(12)

                async def inspect_one_frame(frame_index, frame):
                    frame_key = id(frame)
                    allow_click = frame_key not in clicked_frames
                    async with semaphore:
                        try:
                            info = await asyncio.wait_for(
                                frame.evaluate(
                                    """async (allowClick) => {
                                        const unique = (arr) => [...new Set(arr.filter(Boolean))];
                                        const videos = [];
                                        const sources = [];
                                        const frameUrls = [];
                                        const resourceUrls = [];
                                        const nodes = [];
                                        const roots = [document];
                                        const seenRoots = new Set();
                                        while (roots.length && seenRoots.size < 80) {
                                            const root = roots.shift();
                                            if (!root || seenRoots.has(root)) continue;
                                            seenRoots.add(root);
                                            for (const el of root.querySelectorAll('*')) {
                                                if (el.shadowRoot) roots.push(el.shadowRoot);
                                                if (el.matches('video')) videos.push(el);
                                                if (el.matches('source, iframe, audio, [data-src], [data-hls], [data-file], [data-video], [data-url]')) nodes.push(el);
                                            }
                                        }
                                        for (const v of videos.slice(0, 8)) {
                                            const videoSources = [];
                                            const add = (raw, type, kind) => {
                                                if (!raw) return;
                                                let abs = raw;
                                                try { abs = new URL(raw, location.href).href; } catch (_) {}
                                                if (!videoSources.some(x => x.url === abs)) videoSources.push({url: abs, type: type || '', kind});
                                            };
                                            add(v.currentSrc, v.getAttribute('type'), 'currentSrc');
                                            add(v.getAttribute('src'), v.getAttribute('type'), 'video-src');
                                            for (const source of v.querySelectorAll('source'))
                                                add(source.getAttribute('src') || source.getAttribute('data-src'), source.getAttribute('type'), 'source');
                                            for (const item of videoSources) sources.push(item);
                                            v.muted = true;
                                            v.setAttribute('muted', '');
                                            v.playsInline = true;
                                            v.setAttribute('playsinline', '');
                                            try {
                                                const p = v.play();
                                                if (p && typeof p.catch === 'function') p.catch(() => {});
                                            } catch (_) {}
                                        }
                                        for (const el of nodes.slice(0, 100)) {
                                            const tag = (el.tagName || '').toLowerCase();
                                            const attrs = tag === 'iframe' ? ['src', 'data-src'] :
                                                ['src', 'data-src', 'data-hls', 'data-file', 'data-video', 'data-url'];
                                            for (const attr of attrs) {
                                                const raw = el.getAttribute && el.getAttribute(attr);
                                                if (!raw) continue;
                                                let abs = raw;
                                                try { abs = new URL(raw, location.href).href; } catch (_) {}
                                                if (tag === 'iframe') frameUrls.push(abs);
                                                else sources.push({url: abs, type: el.getAttribute('type') || '', kind: tag + ':' + attr});
                                            }
                                        }
                                        try {
                                            for (const entry of performance.getEntriesByType('resource')) {
                                                const u = entry.name || '';
                                                if (/\\.(m3u8|mpd|mp4|m4v|webm|mov)(?:[?#]|$)|manifest|playlist/i.test(u))
                                                    resourceUrls.push(u);
                                            }
                                        } catch (_) {}
                                        let clicked = '';
                                        if (allowClick && videos.every(v => v.paused)) {
                                            const selectors = [
                                                'button.play', '.play-btn', '.play-button',
                                                '.plyr__control--overlaid', '.video-player__play',
                                                '.vjs-big-play-button', 'button[aria-label*="play" i]',
                                                '[data-testid*="play" i]'
                                            ];
                                            for (const selector of selectors) {
                                                const el = document.querySelector(selector);
                                                if (el && !el.disabled) {
                                                    const style = getComputedStyle(el);
                                                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                                                        try { el.click(); clicked = selector; break; } catch (_) {}
                                                    }
                                                }
                                            }
                                        }
                                        const hosts = [];
                                        for (const item of sources) {
                                            try {
                                                const h = new URL(item.url, location.href).host;
                                                if (h && !hosts.includes(h)) hosts.push(h);
                                            } catch (_) {}
                                        }
                                        return {
                                            videos: videos.length,
                                            videoDetails: videos.slice(0, 4).map(v => ({
                                                currentSrc: v.currentSrc || '', src: v.getAttribute('src') || '',
                                                readyState: v.readyState, networkState: v.networkState,
                                                paused: v.paused, error: v.error ? v.error.code : 0,
                                                sources: unique([...Array.from(v.querySelectorAll('source')).map(x => x.getAttribute('src')), v.currentSrc, v.getAttribute('src')]).slice(0, 6)
                                            })),
                                            nestedIframes: document.querySelectorAll('iframe').length,
                                            frameUrls: unique(frameUrls).slice(0, 20),
                                            sources: sources.slice(0, 60),
                                            resourceUrls: unique(resourceUrls).slice(0, 30),
                                            hosts: hosts.slice(0, 8),
                                            clicked
                                        };
                                    }""",
                                    allow_click,
                                ),
                                timeout=4.5,
                            )
                            return frame_index, frame, info, None
                        except Exception as exc:
                            return frame_index, frame, None, exc

                inspected = await asyncio.gather(
                    *(inspect_one_frame(i, frame) for i, frame in scan_list),
                    return_exceptions=True,
                )
                frame_summary = []
                for item in inspected:
                    if isinstance(item, BaseException):
                        log(f"⚠️ Chromium frame scan task: {type(item).__name__}")
                        continue
                    frame_index, frame, info, error = item
                    frame_key = id(frame)
                    safe_frame_url = (frame.url or "?").split("?", 1)[0][:115]
                    if error is not None or info is None:
                        log(f"⚠️ Chromium frame {frame_index + 1} بررسی نشد | {safe_frame_url} | {type(error).__name__ if error else 'unknown'}")
                        # فریم timeout شده در دور بعد دوباره بررسی می‌شود.
                        continue
                    scanned_frame_ids.add(frame_key)
                    if info.get("videos", 0) or frame == page.main_frame or frame_priority(frame) == 0:
                        active_frame_ids.add(frame_key)
                    summary = (safe_frame_url, info.get("videos", 0),
                               info.get("nestedIframes", 0), tuple(info.get("hosts", [])),
                               info.get("clicked", ""))
                    frame_summary.append(summary)
                    if info.get("clicked"):
                        clicked_frames.add(frame_key)
                        log(f"▶️ Chromium: کلیک پلیر در frame {frame_index + 1} ({info['clicked']})")
                    for detail in info.get("videoDetails", []):
                        current = detail.get("currentSrc") or detail.get("src") or "(خالی)"
                        log(f"🎞️ Chromium video state | ready={detail.get('readyState')} network={detail.get('networkState')} "
                            f"paused={detail.get('paused')} error={detail.get('error')} | src={current[:160]}")
                        if str(current).startswith("blob:"):
                            log("ℹ️ منبع فعلی پلیر blob: است؛ لینک فایل از شنود manifest/درخواست‌های شبکه پیدا می‌شود، نه از خود blob.")
                    discovered = list(info.get("sources", []))
                    discovered.extend({"url": u, "type": "", "kind": "performance-resource"}
                                      for u in info.get("resourceUrls", []))
                    for source in discovered:
                        try:
                            raw_source = source.get("url", "") if isinstance(source, dict) else str(source)
                            source_type = source.get("type", "") if isinstance(source, dict) else ""
                            media_url = _normalize_url(raw_source)
                            low = media_url.lower()
                            mime_ok = any(x in str(source_type).lower() for x in
                                          ("video/", "mpegurl", "dash+xml", "application/x-mpegurl"))
                            ext_ok = any(ext in low for ext in exts)
                            manifest_ok = any(mark in low for mark in ("/manifest", "playlist", "master.m3u"))
                            if (low.startswith(("http://", "https://")) and (ext_ok or mime_ok or manifest_ok)
                                    and not _is_media_segment(media_url) and not _is_thumb(low)
                                    and media_url not in found_urls):
                                found_urls.append(media_url)
                                verified_media_urls.add(media_url)
                                log(f"🎯 Chromium DOM {source.get('kind', 'media') if isinstance(source, dict) else 'media'}: {media_url[:180]}")
                        except Exception:
                            pass
                    for iframe_url in info.get("frameUrls", []):
                        if iframe_url and any(mark in iframe_url.lower() for mark in
                                              ("xv-cdn", "player", "embed", "video", "stream")):
                            log(f"🧩 Chromium nested player iframe: {iframe_url[:180]}")

                signature = tuple(frame_summary)
                if signature != last_frame_signature:
                    last_frame_signature = signature
                    skipped = max(0, len(frames) - len(selected))
                    log(f"🧩 Chromium frame scan: کل={len(frames)} | این دور بررسی‌شده={len(scan_list)} | " +
                        " ; ".join(
                            f"{item[0]} [video={item[1]}, iframe={item[2]}, hosts={','.join(item[3]) or '-'}]"
                            for item in frame_summary
                        ) + (f" | {skipped} فریم به‌دلیل سقف ۷۲تایی بررسی نشد" if skipped else ""))
                return len(frames)

            # کمی فرصت برای ساخت iframeهای تنبل‌بارگذاری‌شونده بده.
            try:
                await page.wait_for_timeout(1200)
            except Exception:
                await asyncio.sleep(1.2)
            await inspect_and_activate_frames(initial=True)

            # حداکثر ۲۰ ثانیه شنود؛ فریم‌های جدید و فریم‌های دارای ویدیو دوباره بررسی می‌شوند.
            for tick in range(5):
                if found_urls:
                    break
                await asyncio.sleep(4)
                await inspect_and_activate_frames(initial=False)
                log(f"⌛ Chromium: انتظار درخواست ویدیو {((tick + 1) * 4)}/20s | "
                    f"کاندید: {len(found_urls)} | frameها: {len(page.frames)}")

            cookies = await context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            _CHROMIUM_SESSION_HEADERS = {
                "User-Agent": REAL_UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
                "Referer": url,
            }
            if cookie_str:
                _CHROMIUM_SESSION_HEADERS["Cookie"] = cookie_str

            def score(u):
                low = u.lower()
                for q, marks in [(1080, ("1080", "1920")), (720, ("720", "1280")),
                                 (480, ("480", "854")), (360, ("360", "640"))]:
                    if any(x in low for x in marks):
                        return q
                m = re.search(r"(\d{3,4})p", low)
                return int(m.group(1)) if m else 0

            candidates = [u for u in found_urls
                          if (u in verified_media_urls or _is_media_manifest_or_file(u))
                          and not _is_media_segment(u) and not _is_thumb(u.lower())]
            if candidates:
                q = int(DOWNLOAD_QUALITY if quality is None else quality)
                ranked = sorted((score(u), u) for u in candidates)
                below = [item for item in ranked if 0 < item[0] <= q]
                unknown = [item for item in ranked if item[0] == 0]
                eligible = below + unknown
                hls = [item for item in eligible if ".m3u8" in item[1].lower()]
                dash = [item for item in eligible if ".mpd" in item[1].lower()]
                # ابتدا manifest واقعی HLS، سپس DASH و در نهایت فایل مستقیم انتخاب می‌شود.
                pool = hls or dash or eligible
                video_url = pool[-1][1] if pool else None
                log(f"🎯 بهترین لینک Chromium: {video_url}")
                if video_url and captured_headers.get(video_url):
                    browser_headers = _filter_browser_headers(captured_headers[video_url])
                    if browser_headers:
                        _CHROMIUM_SESSION_HEADERS.update(browser_headers)
                        log("📋 هدرهای همان درخواست مرورگر ذخیره شد")
                if video_url:
                    _CHROMIUM_SESSION_HEADERS.setdefault("Referer", url)
            else:
                try:
                    title = await page.title()
                except Exception:
                    title = ""
                frame_count = len(page.frames)
                log(f"❌ Chromium: پس از ۲۰ ثانیه هیچ لینک ویدیویی پیدا نشد | title={title[:100]!r} | "
                    f"HTTP={getattr(main_response, 'status', '?')} | frames={frame_count}. "
                    "اگر frame=1 باشد، iframe پلیر ساخته نشده یا صفحه درخواست رسانه نفرستاده است.")
                await safe_edit(status_msg, "❌ Chromium صفحه را باز کرد، اما در صفحه و iframeها درخواست ویدیو پیدا نشد.")
            return video_url

        except asyncio.TimeoutError:
            log(f"⏱️ Chromium timeout در مرحلهٔ: {stage}")
            await safe_edit(status_msg, f"⏱️ Chromium در مرحلهٔ «{stage}» به مهلت مجاز رسید.")
            return None
        except Exception as exc:
            log(f"❌ خطا Chromium در مرحلهٔ {stage}: {type(exc).__name__}: {exc}")
            await safe_edit(status_msg, f"❌ خطای Chromium در مرحلهٔ «{stage}»: {type(exc).__name__}")
            return None
        finally:
            if browser is not None:
                try:
                    await asyncio.wait_for(browser.close(), timeout=8)
                except Exception as exc:
                    log(f"⚠️ Chromium close: {type(exc).__name__}: {exc}")
            if playwright is not None:
                try:
                    await asyncio.wait_for(playwright.stop(), timeout=5)
                except Exception as exc:
                    log(f"⚠️ Playwright stop: {type(exc).__name__}: {exc}")


    async def _chromium_api_download(url, filepath, status_msg, headers):
        """آخرین راه: دانلود با استک شبکهٔ خودِ Playwright (هدر/کوکی/اثر انگشت TLS همان مرورگر).

        برای فایل‌های بزرگ تکه‌تکه (Range) می‌گیرد تا RAM پر نشود.
        """
        REAL_UA = UA_CHROME
        block = 16 * 1024 * 1024
        try:
            await safe_edit(status_msg, "🌐 Chromium API → دانلود فایل...")
            async with async_playwright() as p:
                print("🚀 Chromium API: اجرای مرورگر...", flush=True)
                browser = await asyncio.wait_for(
                    p.chromium.launch(
                        headless=True,
                        timeout=20000,
                        args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"],
                    ),
                    timeout=25,
                )
                try:
                    context = await browser.new_context(
                        user_agent=REAL_UA, locale="en-US",
                        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                    )
                    api = context.request

                    total = 0
                    head = None
                    try:
                        head = await api.head(url, headers=headers, timeout=15000,
                                              fail_on_status_code=False)
                        if head.status == 530:
                            print("⛔ Chromium API HEAD: HTTP 530؛ سرور/CDN پاسخ مبدأ را نمی‌دهد", flush=True)
                            return None
                    except Exception as e:
                        print("⚠️ Chromium API HEAD:", e)
                    if head is not None and head.status < 400:
                        try:
                            total = int(head.headers.get("content-length") or 0)
                        except Exception:
                            total = 0

                    probe = await api.get(url, headers={**headers, "Range": "bytes=0-0"},
                                          timeout=20000, fail_on_status_code=False)
                    if probe.status not in (200, 206):
                        if probe.status == 530:
                            print("⛔ Chromium API: HTTP 530؛ تکرار درخواست با همان نشست فایده‌ای ندارد", flush=True)
                        else:
                            print(f"❌ Chromium API: HTTP {probe.status}", flush=True)
                        return None
                    if not total:
                        cr = probe.headers.get("content-range") or ""
                        m = re.search(r"/\s*(\d+)\s*$", cr)
                        if m:
                            total = int(m.group(1))
                        elif probe.status == 200:
                            try:
                                total = int(probe.headers.get("content-length") or 0)
                            except Exception:
                                total = 0

                    with open(filepath, "wb") as f:
                        if total <= 0:
                            f.write(await probe.body())      # حجم نامشخص: ناچار یک‌جا
                        else:
                            offset = 0
                            while offset < total:
                                if cancel_flag:
                                    break
                                end = min(offset + block, total) - 1
                                resp = await api.get(
                                    url, headers={**headers, "Range": f"bytes={offset}-{end}"},
                                    timeout=90000, fail_on_status_code=False,
                                )
                                if resp.status not in (200, 206):
                                    print(f"❌ Chromium API: HTTP {resp.status} در آفست {offset}")
                                    raise IOError(f"HTTP {resp.status}")
                                data = await resp.body()
                                if not data:
                                    break
                                f.write(data)
                                offset += len(data)
                                await safe_edit(
                                    status_msg,
                                    f"🌐 Chromium API... 🧩 {offset / 1048576:.1f}/{total / 1048576:.1f} MB",
                                )
                finally:
                    await browser.close()

            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            print(f"✅ Chromium API download: {size / 1048576:.1f} MB")
            complete = (size == total) if total else True
            if size > 100_000 and complete:
                return filepath
            try:
                os.remove(filepath)
            except OSError:
                pass
            return None
        except Exception as e:
            print(f"❌ Chromium API download error: {e}")
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except OSError:
                pass
            return None


    async def _chromium_session_download(url, filepath, status_msg, quality=None):
        """دانلود واقعی لینکی که Chromium پیدا کرد، با همان نشست/هدرهای مرورگر."""
        url = _normalize_url(url)
        headers = dict(_CHROMIUM_SESSION_HEADERS or {})
        page_referer = headers.get("Referer")
        quality = int(DOWNLOAD_QUALITY if quality is None else quality)

        if _looks_like_hls(url):
            await safe_edit(status_msg, "🌐 استریم مرورگر → yt-dlp با کیفیت تنظیم‌شده...")
            stream_dir = tempfile.mkdtemp(prefix="stream_", dir=os.path.dirname(filepath) or ".")
            try:
                result = await _ytdlp_subprocess(url, stream_dir, status_msg, headers,
                                                 timeout_sec=900, quality=quality)
                if result:
                    shutil.move(result, filepath)
                    return filepath
                return None
            finally:
                shutil.rmtree(stream_dir, ignore_errors=True)

        await safe_edit(status_msg, "⬇️ دانلود با نشست Chromium (هدر واقعی مرورگر)...")
        access = await asyncio.to_thread(_probe_media_access, url, page_referer)
        if access and access.get("kind") != "hls":
            resign = None
            if page_referer:
                resign = lambda old: _resign_media_url_sync(page_referer, old, quality)
            result = await _download_from_access(url, filepath, status_msg, access, resign=resign)
            if result:
                return result

        if cancel_flag:
            return None
        return await _chromium_api_download(url, filepath, status_msg, headers)


    # ================== yt-dlp ==================
    async def _ytdlp_subprocess(url, output_dir, status_msg, headers, timeout_sec=600,
                                extra_args=None, quality=None):
        """yt-dlp به‌صورت زیرفرایند، با محدودیت کیفیت، پیشرفت زنده و لغوپذیری.

        تغییر مهم نسبت به نسخهٔ قبل: دیگر دانلودر خارجی aria2 اجباری نیست (اثر انگشت TLS
        آن شناسایی و ۴۰۳ می‌شود) و هدر Referer فقط وقتی معتبر است فرستاده می‌شود.
        """
        global cancel_flag
        from http.cookies import SimpleCookie
        from http.cookiejar import Cookie, MozillaCookieJar

        url = _normalize_url(url)
        q = int(DOWNLOAD_QUALITY if quality is None else quality)
        out_tmpl = os.path.join(output_dir, "video.%(ext)s")
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-playlist",
            "--retries", "10", "--fragment-retries", "10", "--file-access-retries", "3",
            "--socket-timeout", "30",
            "--concurrent-fragments", str(HLS_CONCURRENT_FRAGMENTS),
            "--skip-unavailable-fragments",
            "--retry-sleep", "fragment:exp=1:8",
            "--merge-output-format", "mp4", "--remux-video", "mp4",
            "--format", _download_format_selector(q),
            "--output", out_tmpl, "--newline", "--progress", "--progress-delta", "1",
            "--print", "before_dl:SELECTED: %(format_id)s | %(height)sp | %(protocol)s",
            "--print", "after_move:FINAL_FILE: %(filepath)s",
        ]
        if extra_args:
            cmd.extend(extra_args)

        cookie_path = None
        proc = None
        error_lines = []
        try:
            for key, value in (headers or {}).items():
                if not key or value is None:
                    continue
                if key.lower() == "cookie":
                    if os.path.isfile(USER_COOKIES_FILE):
                        continue  # کوکی‌های واقعی کاربر اولویت دارند
                    host = (urlparse(url).hostname or "").lower()
                    if not host or not value:
                        continue
                    try:
                        parsed = SimpleCookie()
                        parsed.load(value)
                        if not parsed:
                            continue
                        domain = ".pornhub.com" if host == "pornhub.com" or host.endswith(".pornhub.com") else host
                        fd, cookie_path = tempfile.mkstemp(prefix="ytdlp_cookies_", suffix=".txt", dir=output_dir)
                        os.close(fd)
                        os.chmod(cookie_path, 0o600)
                        jar = MozillaCookieJar(cookie_path)
                        for name, morsel in parsed.items():
                            jar.set_cookie(Cookie(
                                version=0, name=name, value=morsel.value,
                                port=None, port_specified=False,
                                domain=domain, domain_specified=domain.startswith("."),
                                domain_initial_dot=domain.startswith("."),
                                path="/", path_specified=True,
                                secure=urlparse(url).scheme == "https",
                                expires=None, discard=True, comment=None, comment_url=None,
                                rest={}, rfc2109=False,
                            ))
                        jar.save(ignore_discard=True, ignore_expires=True)
                        cmd += ["--cookies", cookie_path]
                    except Exception as e:
                        print("⚠️ ساخت کوکی برای yt-dlp:", e)
                    continue
                cmd += ["--add-header", f"{key}:{value}"]
            if not cookie_path and os.path.isfile(USER_COOKIES_FILE):
                cmd += ["--cookies", USER_COOKIES_FILE]
            cmd.extend(["--", url])

            print(f"🎬 سقف کیفیت: {q}p | تکه‌های هم‌زمان: {HLS_CONCURRENT_FRAGMENTS}", flush=True)
            print("📋 FORMAT:", _download_format_selector(q), flush=True)
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            last_pct = -20
            last_time = time.monotonic()
            final_path = None
            read_task = asyncio.create_task(proc.stdout.readline())
            try:
                while True:
                    if cancel_flag:
                        return None
                    done, _ = await asyncio.wait({read_task}, timeout=1)
                    if not done:
                        if time.monotonic() - last_time > timeout_sec:
                            print("❌ yt-dlp: مهلت بی‌خبری از پردازش تمام شد")
                            return None
                        continue
                    line_bytes = read_task.result()
                    if not line_bytes:
                        break
                    read_task = asyncio.create_task(proc.stdout.readline())
                    last_time = time.monotonic()
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    print(f"YTDLP: {line}")
                    if line.startswith("FINAL_FILE: "):
                        final_path = line[len("FINAL_FILE: "):].strip()
                    elif "ERROR" in line:
                        error_lines.append(line)
                    match = re.search(r"\b(\d+(?:\.\d+)?)%", line)
                    if match and "[download]" in line.lower():
                        pct = max(0, min(100, int(float(match.group(1)))))
                        if pct < last_pct:
                            last_pct = -20
                        if pct - last_pct >= 20 or (pct == 100 and last_pct != 100):
                            last_pct = pct
                            filled = pct // 5
                            bar = "█" * filled + "░" * (20 - filled)
                            await safe_edit(status_msg, f"⬇️ دانلود؛ سقف {q}p\n[{bar}] {pct}%")
            finally:
                if not read_task.done():
                    read_task.cancel()
                    await asyncio.gather(read_task, return_exceptions=True)

            await proc.wait()
            print(f"📋 yt-dlp exit: {proc.returncode}")
            if proc.returncode == 0 and final_path and os.path.isfile(final_path):
                if os.path.getsize(final_path) > 100_000:
                    return final_path
            return None
        except Exception as e:
            print(f"❌ yt-dlp subprocess error: {e}")
            return None
        finally:
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            if cookie_path:
                try:
                    os.remove(cookie_path)
                except FileNotFoundError:
                    pass


    # ================== استخراج لینک ویدیو از HTML ==================
    _VID_RE = re.compile(
        r"""(?:https?:)?//[^\s"'<>()\\,]+?\.(?:mp4|m3u8|webm|mkv|m4v|mpd)(?:\?[^\s"'<>()\\,]*)?""",
        re.I,
    )
    _IFRAME_RE = re.compile(r"""<iframe[^>]+src=["']([^"']+)["']""", re.I)
    _ALT_RE = re.compile(r"""altplayer\.php\?i=([^"'&\s]+)""", re.I)
    _JUNK = ("preview", "thumb", "trailer", "/ads", "banner", "promo", "sprite", "poster",
             "sample", "splash", "/tr_", "_trailer", "/teaser", "watermark")


    def _abs(u, base):
        u = _unescape_text(u).strip()
        if u.startswith("//"):
            u = "https:" + u
        return urljoin(base, u)


    def _height_of(u):
        nums = [int(n) for n in re.findall(r"(?<!\d)(2160|1440|1080|720|540|480|360|240|144)(?!\d)", u or "")]
        return max(nums) if nums else 0


    def _http_get(url, referer=None, max_bytes=4_000_000, timeout=(20, 45)):
        """HTML را با سقف حجم می‌گیرد.

        باگ قبلی: برای لینک مستقیمِ ۹۷۰ مگی، همین تابع سعی می‌کرد کل فایل را در حافظه
        بخواند و بعد از ۳۰ ثانیه با ۳۶ مگ دانلود timeout می‌داد. حالا:
        اگر content-type رسانه باشد اصلاً بدنه خوانده نمی‌شود و حداکثر ۴ مگ خوانده می‌شود.
        """
        url = _normalize_url(url)
        headers = {
            "User-Agent": UA_CHROME,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if referer:
            headers["Referer"] = _normalize_url(referer)
        resp = None
        try:
            if _has_curl_cffi():
                from curl_cffi import requests as creq
                resp = creq.get(url, headers=headers, impersonate="chrome", timeout=timeout,
                                stream=True, allow_redirects=True)
            else:
                resp = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
            if resp.status_code >= 400:
                print(f"🔎 GET {url[:110]} → {resp.status_code}")
                return ""
            ct = (resp.headers.get("content-type") or "").lower()
            if ct and not any(x in ct for x in ("html", "text", "json", "javascript", "xml")):
                print(f"⏭️ GET {url[:110]} نوع محتوا {ct.split(';')[0]} است → اسکرپ رد شد")
                return ""
            chunks, got = [], 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                chunks.append(chunk)
                got += len(chunk)
                if got >= max_bytes:
                    break
            return b"".join(chunks).decode("utf-8", errors="replace")
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass


    def _page_video_ids(page_url):
        """شناسهٔ ویدیو از آدرس صفحه (مثل -205966838_456239117) تا لینک‌های ویدیوهای
        دیگر/تیزرهای داخل همان صفحه اشتباهی انتخاب نشوند."""
        if not page_url:
            return []
        try:
            m = re.search(r"(-?\d{5,})[_/](\d{5,})", _normalize_url(page_url))
        except Exception:
            m = None
        if not m:
            return []
        return [m.group(1), m.group(2)]


    def _media_candidates_from_html(html, base, page_url=None):
        """همهٔ کاندیدهای ویدیو در HTML، با اولویت: ویدیوی خودِ صفحه ← امضاشده ← کیفیت بالاتر."""
        if not html:
            return []
        text = _unescape_text(html)
        page_ids = _page_video_ids(page_url or base)
        urls = []
        for raw in _VID_RE.findall(text):
            full = _abs(raw, base)
            low = full.lower()
            if any(j in low for j in _JUNK):
                continue
            if "seg-" in low or low.endswith(".ts"):
                continue
            urls.append(full)
        urls = list(dict.fromkeys(urls))
        candidates = []
        for u in urls:
            candidates.append({
                "url": u,
                "height": _height_of(u),
                "signed": bool(re.search(r"(secure|token|sig|signature|expires|exp)=", u, re.I)),
                "matches_page": bool(page_ids) and all(pid in u for pid in page_ids),
            })
        candidates.sort(key=lambda c: (0 if c["matches_page"] else 1,
                                       0 if c["signed"] else 1,
                                       -(c["height"] or 0)))
        return candidates


    def _pick_best_candidate(candidates, quality):
        """بهترین کاندید در سقف کیفیت: بالاترین کیفیت زیر سقف، وگرنه نزدیک‌ترین بالای سقف."""
        if not candidates:
            return None
        try:
            q = int(quality)
        except Exception:
            q = 720
        matched = [c for c in candidates if c.get("matches_page")]
        if matched:                      # ویدیوی خودِ صفحه، نه تیزر/ویدیوی پیشنهادی
            candidates = matched
        under = [c for c in candidates if c["height"] and 0 < c["height"] <= q]
        if under:
            return max(under, key=lambda c: c["height"])
        over = [c for c in candidates if c["height"] and c["height"] > q]
        if over:
            return min(over, key=lambda c: c["height"])
        unknown = [c for c in candidates if not c["height"]]
        return unknown[0] if unknown else candidates[0]


    def _html_scrape_video(url, quality, max_pages=6):
        """صفحه و iframeهایش را می‌گردد و بهترین mp4/m3u8 زیر سقف کیفیت را برمی‌گرداند: (link, referer)."""
        url = _normalize_url(url)
        if _looks_like_media(url):
            print("⏭️ خودِ لینک فایل است → اسکرپ HTML لازم نیست")
            return None
        pages = [(url, None)]
        if "://m." in url:
            pages.append((url.replace("://m.", "://", 1), None))
        candidates, seen, index = [], set(), 0
        while index < len(pages) and index < max_pages:
            page, ref = pages[index]
            index += 1
            if page in seen:
                continue
            seen.add(page)
            try:
                html = _http_get(page, ref)
            except Exception as e:
                print(f"⚠️ scrape {page[:110]}: {e}")
                continue
            if not html:
                continue
            for cand in _media_candidates_from_html(html, page, page):
                candidates.append((cand, page))
            text = _unescape_text(html)
            for match in _IFRAME_RE.findall(text) + _ALT_RE.findall(text):
                frame = _abs(match, page)
                if (frame.startswith("http") and frame not in seen
                        and not any(j in frame.lower() for j in ("ads", "banner", "chat", "splash", "promo"))):
                    pages.append((frame, page))
        if not candidates:
            return None

        unique = []
        seen_urls = set()
        for cand, page in candidates:
            if cand["url"] in seen_urls:
                continue
            seen_urls.add(cand["url"])
            unique.append((cand, page))
        for cand, _ in unique:
            print(f"🎯 کاندید: {cand['height'] or '?'}p | signed={'yes' if cand['signed'] else 'no'} | {cand['url'][:130]}")
        best = _pick_best_candidate([c for c, _ in unique], quality)
        if not best:
            return None
        page_of_best = next(p for c, p in unique if c["url"] == best["url"])
        print(f"✅ انتخاب شد: {best['height'] or '?'}p | {best['url'][:130]}")
        return best["url"], page_of_best


    # ================== بررسی سلامت و ابعاد فایل ==================
    def _ffprobe_json(path, extra_args=None):
        args = ["ffprobe", "-v", "error"]
        if extra_args:
            args.extend(extra_args)
        args.extend(["-show_entries", "stream=width,height,codec_type", "-of", "json", path])
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=120)
        except Exception as e:
            print("⚠️ ffprobe:", e)
            return None


    def _sniff_container(path):
        """نوع کانتینر را از امضای بایت‌های اول تشخیص می‌دهد (پسوند هیچ ارزشی ندارد)."""
        try:
            with open(path, "rb") as f:
                head = f.read(16)
        except Exception:
            return "unknown"
        if len(head) >= 8 and head[4:8] == b"ftyp":
            return "mp4"
        if head[:4] == b"\x1aE\xdf\xa3":
            return "mkv"
        if head[:3] == b"FLV":
            return "flv"
        if head[:1] == b"\x47":
            return "ts"
        return "unknown"


    def _ensure_mp4(path):
        """اگر فایل واقعاً MP4 نیست (مثلاً HLS به‌صورت TS ذخیره شده) بدون افت کیفیت به mp4 تبدیل می‌کند.

        نکته: بعضی دانلودرها دادهٔ MPEG-TS را با پسوند .mp4 می‌نویسند؛ همان فایل
        برای ffprobe/تلگرام مشکل‌ساز می‌شود.
        """
        if not path or not os.path.isfile(path):
            return path
        kind = _sniff_container(path)
        if kind == "mp4":
            return path
        if kind not in ("ts", "mkv", "flv", "unknown"):
            return path
        print(f"🔧 کانتینر «{kind}» شناسایی شد → remux به mp4 (بدون افت کیفیت)...")
        base = path.rsplit(".", 1)[0]
        for extra in (["-bsf:a", "aac_adtstoasc"], []):
            out = base + "_remux.mp4"
            cmd = ["ffmpeg", "-v", "error", "-y", "-err_detect", "ignore_err", "-i", path,
                   "-c", "copy", *extra, "-movflags", "+faststart", "-f", "mp4", out]
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=7200)
            except Exception as e:
                print("⚠️ remux:", e)
                continue
            if result.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 100_000:
                print(f"✅ remux شد: {os.path.getsize(out) / 1048576:.1f} MB")
                try:
                    os.remove(path)
                except OSError:
                    pass
                return out
            try:
                if os.path.exists(out):
                    os.remove(out)
            except OSError:
                pass
        print("⚠️ remux نشد؛ فایل همان‌طور ادامه می‌دهد")
        return path


    def _probe_dimensions(path):
        """(path, width, height) — اگر فایل moov انتهایی/ناقص باشد اول remux می‌کند.

        نسخهٔ قبلی با check=True مستقیم استثنا می‌داد و کل دانلود سالم را دور می‌ریخت.
        """
        result = _ffprobe_json(path, ["-select_streams", "v:0"])
        if result is None or result.returncode != 0 or not (result.stdout or "").strip():
            print("🔧 ffprobe نخواند → تلاش برای remux/تعمیر فایل...")
            fixed = fix_video_file(path)
            if fixed and fixed != path and os.path.isfile(fixed):
                path = fixed
                result = _ffprobe_json(path, ["-select_streams", "v:0"])
        if result is None or result.returncode != 0 or not (result.stdout or "").strip():
            result = _ffprobe_json(path)
        if result is None or result.returncode != 0:
            raise ValueError("ffprobe نتوانست فایل را بخواند (فایل ناقص یا خراب)")
        try:
            streams = json.loads(result.stdout or "{}").get("streams", []) or []
        except Exception:
            streams = []
        video = [s for s in streams if (s.get("codec_type") == "video")] or streams
        if not video:
            raise ValueError("هیچ استریم ویدیویی در فایل نیست")
        w = int(video[0].get("width") or 0)
        h = int(video[0].get("height") or 0)
        return path, w, h


    # ================== تابع اصلی دانلود ==================
    async def download_link(url, status_msg):
        global cancel_flag, DOWNLOAD_QUALITY
        url = _normalize_url(url)
        base_dir = "/content" if os.path.isdir("/content") else None
        tmpdir = tempfile.mkdtemp(dir=base_dir) if base_dir else tempfile.mkdtemp()
        quality = int(DOWNLOAD_QUALITY)

        async def finalize(result_path, clean_dir=None):
            try:
                result_path = await asyncio.to_thread(_ensure_mp4, result_path)
                result_path, w, h = await asyncio.to_thread(_probe_dimensions, result_path)
                short = min(w, h) if (w > 0 and h > 0) else 0
                if short <= 0:
                    print("⚠️ ابعاد ویدیو معلوم نشد؛ فایل بدون تغییر ارسال می‌شود")
                elif short > quality:
                    await safe_edit(status_msg, f"🔧 فایل {short}p است → تبدیل به {quality}p...")
                    scale = f"scale=-2:{quality}" if h <= w else f"scale={quality}:-2"
                    scaled = os.path.join(tmpdir, "scaled.mp4")
                    run_result = await asyncio.to_thread(
                        subprocess.run,
                        ["ffmpeg", "-y", "-i", result_path, "-vf", scale,
                         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", scaled],
                        capture_output=True, timeout=7200,
                    )
                    if run_result.returncode != 0 or not os.path.isfile(scaled):
                        raise ValueError("تبدیل کیفیت ناموفق بود")
                    result_path = scaled
            except Exception as e:
                print(f"❌ بررسی کیفیت خروجی: {e}")
                await safe_edit(status_msg, f"❌ فایل ارسال نشد: فایل سالم/قابل تأیید نیست ({e})")
                if clean_dir:
                    shutil.rmtree(clean_dir, ignore_errors=True)
                shutil.rmtree(tmpdir, ignore_errors=True)
                return None

            final = tempfile.mktemp(suffix=".mp4", dir=TEMP_PATH)
            try:
                shutil.move(result_path, final)   # جابه‌جایی به‌جای کپی: نصف دیسک و چند برابر سریع‌تر
            except Exception:
                shutil.copy2(result_path, final)
            if clean_dir:
                shutil.rmtree(clean_dir, ignore_errors=True)
            shutil.rmtree(tmpdir, ignore_errors=True)
            print(f"✅ دانلود موفق: {os.path.getsize(final) / 1048576:.1f} MB")
            return final

        try:
            is_direct = _looks_like_media(url)

            # ---------- ۱) لینک فایل/استریم مستقیم ----------
            if is_direct:
                await safe_edit(status_msg, "🔗 لینک فایل مستقیم → تست دسترسی و دانلود...")
                access = await asyncio.to_thread(_probe_media_access, url, None)
                if access and access.get("kind") == "hls":
                    res = await _ytdlp_subprocess(url, tmpdir, status_msg, access.get("headers") or {},
                                                  timeout_sec=900, quality=quality)
                    if res:
                        return await finalize(res)
                elif access:
                    res = await _download_from_access(url, os.path.join(tmpdir, "direct.mp4"),
                                                     status_msg, access)
                    if res:
                        return await finalize(res)
            else:
                # صفحه‌ای که ممکن است خودش فایل تحویل دهد (مثل ?hash=...&download=true)
                access = await asyncio.to_thread(_probe_media_access, url, None)
                if access and access.get("kind") != "hls":
                    res = await _download_from_access(url, os.path.join(tmpdir, "direct.mp4"),
                                                     status_msg, access)
                    if res:
                        return await finalize(res)

            if cancel_flag:
                return None

            is_pornhub = "pornhub.com" in (urlparse(url).hostname or "").lower()

            # ---------- ۲) اسکرپ HTML: سریع‌ترین راه برای سایت‌های بدون extractor ----------
            if not is_pornhub:
                await safe_edit(status_msg, "🔍 استخراج لینک ویدیو از صفحه...")
                scraped = await asyncio.to_thread(_html_scrape_video, url, quality)
                if scraped:
                    vurl, vref = scraped
                    if _looks_like_hls(vurl):
                        hdrs = _get_smart_headers(vurl, referer=vref, for_media=True)
                        res = await _ytdlp_subprocess(vurl, tmpdir, status_msg, hdrs,
                                                      timeout_sec=900, quality=quality)
                        if res:
                            return await finalize(res)
                    else:
                        resign = (lambda old: _resign_media_url_sync(url, old, quality))
                        res = await _download_direct_smart(
                            vurl, os.path.join(tmpdir, "scraped.mp4"), status_msg, quality,
                            page_referer=vref, resign=resign, tmpdir=tmpdir,
                        )
                        if res:
                            return await finalize(res)

            if cancel_flag:
                return None

            # ---------- ۳) yt-dlp (اکسترکتورهای واقعی؛ بدون Referer اشتباه) ----------
            await safe_edit(status_msg, "⬇️ تلاش با yt-dlp...")
            page_headers = _get_smart_headers(url)
            res = await _ytdlp_subprocess(url, tmpdir, status_msg, page_headers,
                                          timeout_sec=600, quality=quality)
            if res:
                return await finalize(res)

            if cancel_flag:
                return None

            # ---------- ۴) yt-dlp با شبیه‌سازی مرورگر (ضد Cloudflare) ----------
            await safe_edit(status_msg, "🛡️ تلاش با شبیه‌سازی مرورگر...")
            res = await _ytdlp_subprocess(url, tmpdir, status_msg, page_headers, timeout_sec=600,
                                          extra_args=["--impersonate", "chrome", "--extractor-retries", "3"],
                                          quality=quality)
            if res:
                return await finalize(res)

            if cancel_flag:
                return None

            # ---------- ۵) yt-dlp generic ----------
            await safe_edit(status_msg, "⬇️ تلاش با yt-dlp generic...")
            res = await _ytdlp_subprocess(url, tmpdir, status_msg, page_headers, timeout_sec=300,
                                          extra_args=["--force-generic-extractor"], quality=quality)
            if res:
                return await finalize(res)

            if cancel_flag:
                return None

            # ---------- ۶) Chromium: پیدا کردن لینک + دانلود با همان نشست ----------
            extracted = await download_with_chromium_enhanced(url, status_msg, quality=quality)
            if extracted:
                await safe_edit(status_msg, "🌐 Chromium لینک را پیدا کرد → دانلود با نشست مرورگر...")
                dl_path = os.path.join(tmpdir, "chromium_direct.mp4")
                res = await _chromium_session_download(extracted, dl_path, status_msg, quality=quality)
                if res:
                    return await finalize(res)

            if cancel_flag:
                return None

            # ---------- ۷) آخرین تلاش: خودِ آدرس ورودی به‌عنوان فایل ----------
            if not is_direct:
                await safe_edit(status_msg, "🔗 آخرین تلاش: دانلود مستقیم HTTP...")
                res = await _download_direct_smart(url, os.path.join(tmpdir, "last_try.mp4"),
                                                   status_msg, quality, page_referer=None,
                                                   tmpdir=tmpdir)
                if res:
                    return await finalize(res)
        except Exception as e:
            print(f"❌ خطای غیرمنتظره در دانلود: {type(e).__name__}: {e}")
            await safe_edit(status_msg, f"❌ خطای غیرمنتظره: {type(e).__name__}")
            return None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        await safe_edit(status_msg, "❌ همه روش‌ها شکست خوردند.")
        return None


    async def _download_direct_smart(url, filepath, status_msg, quality, page_referer=None,
                                     resign=None, tmpdir=None):
        """probe → اگر HLS بود yt-dlp، وگرنه دانلود تکه‌ای چنداتصاله."""
        url = _normalize_url(url)
        access = await asyncio.to_thread(_probe_media_access, url, page_referer)
        if not access:
            return None
        if access.get("kind") == "hls":
            out_dir = tmpdir or os.path.dirname(filepath) or "."
            headers = dict(access.get("headers") or {})
            result = await _ytdlp_subprocess(url, out_dir, status_msg, headers,
                                            timeout_sec=900, quality=quality)
            if result and os.path.normpath(result) != os.path.normpath(filepath):
                try:
                    shutil.move(result, filepath)
                    return filepath
                except Exception as e:
                    print("⚠️ جابه‌جایی فایل HLS:", e)
                    return result
            return result
        return await _download_from_access(url, filepath, status_msg, access, resign=resign)

    #================== صف رندر و آپلود موازی تلگرام ==================
    queue = None  # ساخته‌شدن داخل حلقهٔ اختصاصی uvloop
    processing = False
    upload_tasks = set()
    upload_semaphore = None  # ساخته‌شدن داخل حلقهٔ اختصاصی uvloop
    own_output_fingerprints = {}
    IS_BOT_ACCOUNT = False


    def _cleanup_paths(paths):
        seen = set()
        for path in paths or []:
            if not path or path in seen:
                continue
            seen.add(path)
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception as e:
                print(f"⚠️ پاک‌سازی فایل ناموفق بود ({path}): {e}")


    async def choose_thumbnail_index(event, screenshots, status):
        """بدون ارسال پیش‌نمایش و بدون انتظار؛ فریم تامبنیل فوراً تصادفی انتخاب می‌شود."""
        if not screenshots:
            return None
        selected_index = random.randrange(len(screenshots))
        print(
            f"🎲 انتخاب خودکار تامبنیل: فریم {selected_index + 1} از {len(screenshots)}"
        )
        await safe_edit(
            status,
            f"🎲 تامبنیل به‌صورت تصادفی انتخاب شد (فریم {selected_index + 1}).\n"
            "🎬 آماده‌سازی رندر..."
        )
        return selected_index


    TG_MAX_PART_BYTES = 1_950_000_000
    TG_VIDEO_BRAND = "تلگرام گیلاس خیس 🍒💦"
    TG_VIDEO_CAPTION = "تلگرام گیلاس خیس 🍒💦👇\n\n@INO_BOKHOR1"

    def _split_video_under_limit_sync(file_path, max_bytes=TG_MAX_PART_BYTES):
        """Split at keyframes, filling every non-final part as close as possible to max_bytes."""
        size = os.path.getsize(file_path)
        if size <= max_bytes:
            return [file_path]
        duration_raw = _get_duration_sync(file_path)
        duration = float(duration_raw or 0)
        if duration <= 0:
            raise RuntimeError("مدت ویدیو برای پارت‌بندی قابل تشخیص نیست")
        if max_bytes <= 0:
            raise ValueError("حداکثر حجم پارت نامعتبر است")

        work_dir = tempfile.mkdtemp(prefix="tg_parts_")
        # Start very close to the theoretical maximum; keyframe placement and VBR are corrected below.
        segment_time = max(1.0, duration * (max_bytes / size) * 0.998)
        best_parts = None
        best_dir = None
        best_full_size = 0
        last_error = None

        for attempt in range(14):
            for old in os.listdir(work_dir):
                old_path = os.path.join(work_dir, old)
                try:
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                    elif os.path.isdir(old_path):
                        shutil.rmtree(old_path, ignore_errors=True)
                except Exception:
                    pass

            pattern = os.path.join(work_dir, "part_%03d.mp4")
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", file_path,
                "-map", "0", "-c", "copy", "-f", "segment",
                "-segment_time", f"{segment_time:.3f}", "-reset_timestamps", "1",
                "-segment_format", "mp4", "-segment_format_options", "movflags=+faststart",
                pattern
            ]
            result = subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
            )
            if result.returncode != 0:
                last_error = result.stderr[-1200:]
                segment_time *= 0.80
                continue

            parts = sorted(
                os.path.join(work_dir, name) for name in os.listdir(work_dir)
                if name.lower().endswith(".mp4")
                and os.path.getsize(os.path.join(work_dir, name)) > 0
            )
            if len(parts) < 2:
                last_error = "FFmpeg حداقل دو پارت نساخت"
                segment_time *= 0.70
                continue

            sizes = [os.path.getsize(part) for part in parts]
            largest = max(sizes, default=0)
            oversized = [part_size for part_size in sizes if part_size > max_bytes]

            if not oversized:
                # The last segment is normally the remainder; target the largest full segment.
                full_sizes = sizes[:-1] if len(sizes) > 1 else sizes
                largest_full = max(full_sizes, default=0)
                fill_ratio = largest_full / max_bytes if max_bytes else 0
                if fill_ratio >= 0.992:
                    if best_dir:
                        shutil.rmtree(best_dir, ignore_errors=True)
                    print(
                        f"✅ پارت‌بندی بهینه: {len(parts)} پارت | "
                        f"بزرگ‌ترین پارت کامل: {largest_full / 1_000_000_000:.3f} GB "
                        f"از سقف {max_bytes / 1_000_000_000:.2f} GB"
                    )
                    return parts

                if largest_full > best_full_size:
                    # Preserve the fullest valid attempt while the next estimate is tested.
                    if best_dir:
                        shutil.rmtree(best_dir, ignore_errors=True)
                    best_dir = tempfile.mkdtemp(prefix="tg_parts_best_")
                    best_parts = []
                    for part in parts:
                        saved_part = os.path.join(best_dir, os.path.basename(part))
                        os.replace(part, saved_part)  # same filesystem rename, no duplicate disk usage
                        best_parts.append(saved_part)
                    best_full_size = largest_full

                # Grow the time slice when a complete part is unnecessarily small.
                growth = (max_bytes / max(1, largest_full)) * 0.998
                segment_time *= min(1.35, max(1.02, growth))
            else:
                # If any segment crosses the cap, scale down in proportion to its actual byte size.
                ratio = max_bytes / max(1, largest)
                segment_time *= min(0.98, max(0.45, ratio * 0.998))

        # If keyframe spacing prevents an exact fill, use the fullest valid attempt rather than failing.
        if best_parts and all(os.path.exists(part) and os.path.getsize(part) <= max_bytes for part in best_parts):
            shutil.rmtree(work_dir, ignore_errors=True)
            print(
                f"⚠️ پارت‌بندی امن انجام شد؛ فاصلهٔ کی‌فریم‌ها اجازهٔ پرشدن دقیق نداد. "
                f"بزرگ‌ترین پارت کامل: {best_full_size / 1_000_000_000:.3f} GB"
            )
            return best_parts

        shutil.rmtree(work_dir, ignore_errors=True)
        if best_dir:
            shutil.rmtree(best_dir, ignore_errors=True)
        raise RuntimeError(
            "پارت‌بندی زیر سقف ۱.۹۵ گیگابایت ناموفق بود: "
            + str(last_error or "اندازهٔ پارت‌ها")
        )


    async def upload_to_telegram(event, file_path, thumb_path, status, cleanup_after=()):
        """ارسال ویدیو با موتور انتقال WZGram؛ پارت‌بندی و مشخصات ویدیو حفظ می‌شود."""
        global cancel_flag
        generated_parts = []
        try:
            async with upload_semaphore:
                if cancel_flag:
                    await safe_edit(status, "⏹️ آپلود لغو شد.")
                    return
                if not os.path.exists(file_path):
                    await safe_edit(status, "❌ فایل خروجی برای آپلود پیدا نشد.")
                    return

                original_size = os.path.getsize(file_path)
                if original_size > TG_MAX_PART_BYTES:
                    await safe_edit(status, "✂️ حجم خروجی بیشتر از ۱٫۹۵ گیگابایت است؛ در حال پارت‌بندی بدون افت کیفیت...")
                    generated_parts = await asyncio.to_thread(_split_video_under_limit_sync, file_path)
                else:
                    generated_parts = [file_path]

                total_parts = len(generated_parts)
                random_id = random.randint(100000, 999999)
                for part_index, part_path in enumerate(generated_parts, start=1):
                    if cancel_flag:
                        await safe_edit(status, "⏹️ آپلود پارت‌ها لغو شد.")
                        return

                    part_size = os.path.getsize(part_path)
                    file_size_mb = part_size / (1024 * 1024)
                    if total_parts == 1:
                        file_name = f"{TG_VIDEO_BRAND}_{random_id}.mp4"
                        caption = TG_VIDEO_CAPTION
                    else:
                        file_name = f"{TG_VIDEO_BRAND}_{random_id}_پارت {part_index}.mp4"
                        caption = f"پارت {part_index} تلگرام گیلاس خیس 🍒💦👇\n\n@INO_BOKHOR1"

                    try:
                        duration_raw = await asyncio.to_thread(_get_duration_sync, part_path)
                        duration = max(1, int(round(float(duration_raw or 1))))
                    except Exception:
                        duration = 1
                    try:
                        width, height = await asyncio.to_thread(_get_video_dimensions_sync, part_path)
                    except Exception:
                        width, height = 1280, 720

                    last_bucket = [-10]
                    upload_started = time.monotonic()
                    loop = asyncio.get_running_loop()

                    async def on_upload_progress(sent, total):
                        if not total:
                            return
                        pct = max(0, min(100, int(sent * 100 / total)))
                        bucket = 100 if pct >= 100 else (pct // 10) * 10
                        if bucket <= last_bucket[0]:
                            return
                        last_bucket[0] = bucket
                        elapsed = max(0.1, time.monotonic() - upload_started)
                        speed = max(0.0, sent) / elapsed / (1024 * 1024)
                        remain = max(0, total - sent) / (1024 * 1024)
                        eta_seconds = int(remain / speed) if speed > 0.01 else 0
                        eta = f"{eta_seconds // 60}:{eta_seconds % 60:02d}" if speed > 0.01 else "..."
                        bar = "█" * (bucket // 5) + "░" * (20 - bucket // 5)
                        status_text = (
                            f"⬆️ آپلود تلگرام | پارت {part_index}/{total_parts}\n"
                            f"[{bar}] {bucket}%\n📦 {file_size_mb:.1f} MB\n"
                            f"⚡ سرعت: {speed:.1f} MB/s | ⏱️ باقی‌مانده: {eta}"
                        )
                        loop.call_soon_threadsafe(
                            lambda text=status_text: asyncio.create_task(safe_edit(status, text))
                        )

                    thumb = thumb_path if thumb_path and os.path.exists(thumb_path) else None
                    own_output_fingerprints[(file_name, part_size)] = time.time() + 900
                    await safe_edit(
                        status,
                        f"🚀 شروع آپلود با موتور WZGram | پارت {part_index}/{total_parts}\n"
                        f"📂 {file_name}\n📦 {file_size_mb:.1f} MB\n"
                        f"🔧 انتقال موازی داخلی WZGram"
                    )

                    send_args = {
                        "caption": caption,
                        "duration": duration,
                        "width": int(width),
                        "height": int(height),
                        "thumb": thumb,
                        "file_name": file_name,
                        "supports_streaming": True,
                        "reply_to_message_id": event.id,
                        "progress": on_upload_progress,
                    }
                    try:
                        sent_message = await client.send_video(event.chat_id, part_path, **send_args)
                    except Exception as send_error:
                        msg = str(send_error).lower()
                        thumb_related = any(
                            token in msg for token in (
                                "thumb", "photo_invalid", "photo_content", "photo_size",
                                "dimensions", "photo_crop", "thumbnail"
                            )
                        )
                        if not thumb or not thumb_related:
                            raise
                        send_args["thumb"] = None
                        await safe_edit(
                            status,
                            "⚠️ تامبنیل سفارشی پذیرفته نشد؛ ارسال با تامبنیل خودکار WZGram..."
                        )
                        upload_started = time.monotonic()
                        last_bucket[0] = -10
                        sent_message = await client.send_video(event.chat_id, part_path, **send_args)

                    if sent_message is None:
                        raise RuntimeError("WZGram ارسال را متوقف کرد و پیامی برنگرداند")
                    await safe_edit(status, f"✅ پارت {part_index}/{total_parts} با WZGram در تلگرام ارسال شد.")

                await safe_edit(
                    status,
                    "✅ همهٔ ویدیوها با موفقیت در تلگرام ارسال شدند.\n"
                    f"🎞️ تعداد پارت: {total_parts}\n"
                    f"🏷️ نام: {TG_VIDEO_BRAND}_{random_id}.mp4"
                )
        except asyncio.CancelledError:
            try:
                await safe_edit(status, "⏹️ آپلود تلگرام لغو شد.")
            except Exception:
                pass
            raise
        except Exception as e:
            print("WZGRAM VIDEO UPLOAD ERROR:", repr(e))
            await safe_edit(status, f"❌ خطا در آپلود تلگرام با WZGram:\n`{str(e)[:700]}`")
        finally:
            if generated_parts and generated_parts != [file_path]:
                parent_dirs = {os.path.dirname(x) for x in generated_parts}
                _cleanup_paths(generated_parts)
                for directory in parent_dirs:
                    shutil.rmtree(directory, ignore_errors=True)
            _cleanup_paths(cleanup_after)


    async def worker():
        global processing, cancel_flag
        if processing:
            return
        processing = True
        try:
            while not queue.empty():
                if cancel_flag:
                    break
                event, original_path = await queue.get()
                try:
                    await process_message(event, original_path)
                except Exception as e:
                    print("PROCESS WORKER ERROR:", repr(e))
                    try:
                        await event.reply(f"❌ خطا در پردازش: {e}")
                    except Exception:
                        pass
                finally:
                    queue.task_done()
                await asyncio.sleep(0.2)
        finally:
            processing = False
            if not queue.empty() and not cancel_flag:
                asyncio.create_task(worker())


    # ================= تابع پردازش پیام ==================
    async def process_message(event, original_path):
        global cancel_flag
        status = await event.reply("🖼️ در حال آماده‌سازی اسکرین‌شات‌ها...")
        album_pics = []
        main_thumb = None
        selected_thumb = None
        telegram_thumb = None
        custom_thumb_path = None
        final_path = original_path
        keep_for_upload = False

        try:
            album_pics = await asyncio.to_thread(
                _get_multiple_screenshots_sync, original_path, SCREENSHOT_COUNT
            )

            if cancel_flag:
                await safe_edit(status, "⏹️ عملیات لغو شد.")
                return

            if album_pics:
                selection = await choose_thumbnail_index(event, album_pics, status)
                if selection is None or cancel_flag:
                    await safe_edit(status, "⏹️ عملیات لغو شد.")
                    return
                if isinstance(selection, dict) and selection.get("custom_message"):
                    custom_thumb_path = tempfile.mktemp(
                        suffix="_chosen_thumb.jpg", dir=TEMP_PATH
                    )
                    downloaded_image = await client.download_media(
                        selection["custom_message"], file=custom_thumb_path
                    )
                    if not downloaded_image or not os.path.exists(downloaded_image) or os.path.getsize(downloaded_image) <= 0:
                        _cleanup_paths([custom_thumb_path])
                        custom_thumb_path = None
                        await safe_edit(status, "❌ دریافت تامبنیل انتخابی ناموفق بود.")
                        return
                    custom_thumb_path = downloaded_image
                    selected_thumb = custom_thumb_path
                    selection_label = "عکس ارسالی شما"
                elif isinstance(selection, dict) and selection.get("custom_path"):
                    custom_thumb_path = selection["custom_path"]
                    selected_thumb = custom_thumb_path
                    selection_label = "عکس ارسالی شما"
                else:
                    selected_index = max(0, min(int(selection), len(album_pics) - 1))
                    selected_thumb = album_pics[selected_index]
                    selection_label = f"فریم شمارهٔ {selected_index + 1}"
                telegram_thumb = await asyncio.to_thread(
                    _make_telegram_thumbnail_sync, selected_thumb
                )
                await safe_edit(
                    status,
                    f"✅ تامبنیل انتخاب شد: {selection_label}.\n"
                    f"🎬 حالا رندر شروع می‌شود..."
                )
            else:
                print("⚠️ اسکرین‌شاتی برای انتخاب تولید نشد؛ فریم میانی ویدیو استفاده می‌شود.")
                main_thumb = await asyncio.to_thread(_get_thumbnail_sync, original_path)
                selected_thumb = main_thumb
                telegram_thumb = await asyncio.to_thread(
                    _make_telegram_thumbnail_sync, selected_thumb
                )
                await safe_edit(status, "⚠️ اسکرین‌شات آماده نشد؛ تامبنیل پیش‌فرض انتخاب شد. شروع رندر...")

            # تصاویر پیش‌نمایش دیگر لازم نیستند؛ فایل JPEG نهایی جداگانه نگه داشته می‌شود.
            _cleanup_paths(album_pics)
            album_pics = []
            if main_thumb and main_thumb != selected_thumb:
                _cleanup_paths([main_thumb])
                main_thumb = None

            if cancel_flag:
                await safe_edit(status, "⏹️ عملیات لغو شد.")
                return

            active_overlay = bool(OVERLAY_ENABLED and get_overlay_path() and os.path.exists(get_overlay_path()))
            effects_active = bool(WATERMARK_ENABLED or active_overlay)
            if effects_active:
                action_text = []
                if WATERMARK_ENABLED:
                    action_text.append("واترمارک")
                if active_overlay:
                    action_text.append("اورلی تمام‌مدت")
                await safe_edit(status, f"🎬 اعمال {' + '.join(action_text)}...")
                loop = asyncio.get_running_loop()

                def on_progress(pct, eta):
                    filled = int(pct / 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    progress_text = (
                        f"🎬 اعمال {' + '.join(action_text)}...\n"
                        f"[{bar}] {pct}%\n"
                        f"⏱ زمان باقیمانده: {eta}"
                    )
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(safe_edit(status, progress_text))
                    )

                processed = await asyncio.to_thread(
                    _apply_watermark_sync, original_path, None, on_progress
                )
                if not processed or not os.path.exists(processed) or not is_valid_video(processed):
                    await safe_edit(status, "❌ رندر واترمارک/اورلی ناموفق شد؛ برای جلوگیری از ارسال نسخهٔ بدون افکت، آپلود متوقف شد.")
                    return
                final_path = processed
                await safe_edit(
                    status,
                    f"🎬 اعمال {' + '.join(action_text)}...\n"
                    f"[██████████] 100%\n"
                    f"✅ رندر کیفیت بالا کامل شد"
                )

            if cancel_flag:
                await safe_edit(status, "⏹️ عملیات لغو شد.")
                return

            if not final_path or not os.path.exists(final_path) or not is_valid_video(final_path):
                await safe_edit(status, "❌ فایل خروجی سالم نیست؛ آپلود انجام نشد.")
                return

            file_size_mb = os.path.getsize(final_path) / (1024 * 1024)
            await safe_edit(
                status,
                f"✅ رندر آماده شد ({file_size_mb:.1f} MB).\n"
                f"🚀 آپلود تلگرام همین حالا در پس‌زمینه شروع می‌شود؛ رندر بعدی منتظر آپلود نمی‌ماند."
            )

            cleanup_after = [original_path, final_path, telegram_thumb, main_thumb, custom_thumb_path]
            upload_task = asyncio.create_task(
                upload_to_telegram(
                    event,
                    final_path,
                    telegram_thumb,
                    status,
                    cleanup_after=cleanup_after
                )
            )
            upload_tasks.add(upload_task)
            upload_task.add_done_callback(upload_tasks.discard)
            keep_for_upload = True

        finally:
            # اگر task آپلود ساخته نشده، تمام فایل‌های همین آیتم را همین‌جا پاک کن.
            if not keep_for_upload:
                _cleanup_paths([original_path, final_path, telegram_thumb, main_thumb, custom_thumb_path] + album_pics)

    #================== هندلر اصلی ==================
    def is_video_message(msg):
        if getattr(msg, "video", None) or getattr(msg, "video_note", None):
            return True
        document = getattr(msg, "document", None)
        if document:
            mime = (getattr(document, "mime_type", None) or "").lower()
            name = (getattr(document, "file_name", None) or "").lower()
            return mime.startswith("video/") or name.endswith((".mp4", ".mkv", ".mov", ".webm", ".m4v", ".avi"))
        return False

    async def handler(event):
        global processing, WATERMARK_ENABLED, OVERLAY_ENABLED, cancel_flag, DOWNLOAD_QUALITY, WATERMARK_TEXT, FONT_PATH, SCREENSHOT_TEXT

        raw_text = (event.message.message or "").strip()
        caption = raw_text.lower()

        # ویدیویی که همین کلاینت آپلود کرده نباید دوباره وارد صف پردازش شود.
        msg_file = getattr(event.message, "file", None)
        msg_name = getattr(msg_file, "name", None) if msg_file else None
        msg_size = int(getattr(msg_file, "size", 0) or 0) if msg_file else 0
        now = time.time()
        for fingerprint, expires in list(own_output_fingerprints.items()):
            if expires <= now:
                own_output_fingerprints.pop(fingerprint, None)
        if msg_name and msg_size and (msg_name, msg_size) in own_output_fingerprints:
            own_output_fingerprints.pop((msg_name, msg_size), None)
            return

        is_link = raw_text.startswith("http://") or raw_text.startswith("https://")
        is_overlay_intent = caption in ["اورلی", "overlay", "save overlay", "ذخیره اورلی", "اورلی ذخیره"]

        if getattr(event.message, "forward", None):
            print(f"🔍 FORWARD: video={bool(event.message.video)}, doc={bool(event.message.document)}")

        # ========== استارت ==========
        if caption == "استارت":
            wm_s = "✅ روشن" if WATERMARK_ENABLED else "❌ خاموش"
            ol_s = "✅ روشن" if OVERLAY_ENABLED else "❌ خاموش"
            help_text = (
                "📖 **راهنمای کامل دستورات ربات**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "🏠 **دستورات اصلی:**\n\n"
                "🔹 `استارت`\n"
                "     نمایش این راهنما\n\n"
                "🔹 ارسال لینک ویدیو\n"
                "     ربات لینک رو دانلود و پردازش میکنه\n\n"
                "🔹 ارسال ویدیو یا فایل\n"
                "     تامبنیل به‌صورت خودکار و تصادفی از فریم‌های ویدیو انتخاب میشه؛ نیازی به ارسال عکس یا انتخاب دستی نیست. سپس رندر و آپلود تلگرام شروع میشه\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n"
                "💧 **تنظیمات واترمارک:**\n\n"
                "🔹 `واترمارک روشن`\n"
                "     فعال کردن واترمارک روی ویدیو\n\n"
                "🔹 `واترمارک خاموش`\n"
                "     غیرفعال کردن واترمارک\n\n"
                "🔹 `متن واترمارک @channel`\n"
                "     تغییر متن واترمارک به انگلیسی\n\n"
                "🔹 `متن واترمارک کانال من`\n"
                "     تغییر متن واترمارک به فارسی\n"
                "     (فونت فارسی خودکار دانلود میشه)\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n"
                "🖼️ **اسکرین‌شات‌ها:**\n\n"
                "🔹 `متن اسکرین‌شات ...`\n"
                "     تغییر کلمه‌ای که روی ۱۲ اسکرین‌شات\n"
                "     نوشته میشه — خودکار در خالی‌ترین\n"
                "     ناحیه، دور از چهره و بدن افراد (حتی\n"
                "     بدون صورت)، با کاور مشکی و متن سفید\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n"
                "🎞️ **تنظیمات اورلی:**\n\n"
                "🔹 `اورلی روشن`\n"
                "     فعال کردن اورلی روی ویدیو\n\n"
                "🔹 `اورلی خاموش`\n"
                "     غیرفعال کردن اورلی\n\n"
                "🔹 `اورلی` + ارسال عکس یا ویدیو\n"
                "     کپشن عکس/ویدیو رو «اورلی» بنویس\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n"
                "🎬 **کیفیت دانلود (سقف کیفیت، اولویت HLS):**\n\n"
                "     ابتدا بهترین HLS تا سقف انتخابی؛ در نبود آن فرمت دیگر.\n"
                "     اگر HLS پایین‌تر موجود باشد، به فایل مستقیمِ بالاتر ترجیح داده می‌شود.\n"
                "     کیفیت بالاتر از سقف ارسال نمی‌شود؛ تبدیل کیفیت انجام نمی‌شود.\n"
                "     اعداد فارسی هم پذیرفته می‌شوند: `کیفیت ۷۲۰`\n\n"
                "🔹 `کیفیت 1080`\n"
                "     حداکثر Full HD\n\n"
                "🔹 `کیفیت 720`\n"
                "     حداکثر HD — پیشفرض\n\n"
                "🔹 `کیفیت 480`\n"
                "     حداکثر 480p\n\n"
                "🔹 `کیفیت 360`\n"
                "     حداکثر 360p\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n"
                "🛑 **لغو عملیات:**\n\n"
                "🔹 `لغو`\n"
                "     لغو فوری همه عملیات‌های در حال اجرا\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 **وضعیت فعلی:**\n"
                f"   💧 واترمارک: {wm_s}\n"
                f"   📝 متن واترمارک: `{WATERMARK_TEXT}`\n"
                f"   🖼️ متن اسکرین‌شات: `{SCREENSHOT_TEXT}`\n"
                f"   🎞️ اورلی: {ol_s}\n"
                f"   🎬 کیفیت دانلود: `{DOWNLOAD_QUALITY}p`"
            )
            await event.reply(help_text)
            return

        # ========== واترمارک روشن/خاموش ==========
        if caption == "واترمارک روشن":
            WATERMARK_ENABLED = True
            await event.reply("✅ واترمارک **روشن** شد.")
            return

        if caption == "واترمارک خاموش":
            WATERMARK_ENABLED = False
            await event.reply("❌ واترمارک **خاموش** شد.")
            return

        # ========== تغییر متن واترمارک ==========
        if raw_text.startswith("متن واترمارک "):
            new_text = raw_text[len("متن واترمارک "):].strip()
            if not new_text:
                await event.reply(
                    "⚠️ متن واترمارک نمیتونه خالی باشه!\n\n"
                    "مثال انگلیسی:\n`متن واترمارک @MyChannel`\n\n"
                    "مثال فارسی:\n`متن واترمارک کانال من`"
                )
                return
            forbidden = ["'", '"', "\\", "\n"]
            if any(c in new_text for c in forbidden):
                await event.reply(
                    "⚠️ متن نمیتونه شامل این کاراکترها باشه:\n"
                    "` ' \" \\ `"
                )
                return
            WATERMARK_TEXT = new_text
            has_persian = any('\u0600' <= c <= '\u06FF' for c in new_text)
            if has_persian:
                await event.reply("⏳ متن فارسی شناسایی شد، در حال دانلود فونت...")
                font = await asyncio.to_thread(_setup_persian_font)
                # ⚠️ FONT_PATH را دست نمی‌زنیم — بازمحافظهٔ آن باعث می‌شد متن اسکرین‌شات حذف بشود
                font_status = "✅ فونت Vazir" if (font and "Vazir" in font) else "⚠️ فونت پیشفرض"
                await event.reply(
                    f"✅ متن واترمارک تغییر کرد:\n`{WATERMARK_TEXT}`\n\n"
                    f"🔤 فونت: {font_status}"
                )
            else:
                await event.reply(
                    f"✅ متن واترمارک تغییر کرد:\n`{WATERMARK_TEXT}`"
                )
            return

        # ========== تغییر متن اسکرین‌شات ==========
        if raw_text.startswith("متن اسکرین‌شات "):
            new_text = raw_text[len("متن اسکرین‌شات "):].strip()
            if not new_text:
                await event.reply("⚠️ متن اسکرین‌شات نمی‌تونه خالی باشه!")
                return
            forbidden = ["'", '"', "\\", "\n"]
            if any(c in new_text for c in forbidden):
                await event.reply("⚠️ متن نمی‌تونه شامل این کاراکترها باشه: ` ' \" \\ `")
                return
            SCREENSHOT_TEXT = new_text
            has_persian = any('\u0600' <= c <= '\u06FF' for c in new_text)
            if has_persian:
                await asyncio.to_thread(_setup_persian_font)
            await event.reply(
                f"✅ متن اسکرین‌شات تغییر کرد:\n`{SCREENSHOT_TEXT}`\n"
                f"(روی اسکرین‌شات‌های ویدیوهای بعدی اعمال میشه)"
            )
            return

        # ========== اورلی روشن/خاموش ==========
        if caption == "اورلی روشن":
            OVERLAY_ENABLED = True
            await event.reply("✅ اورلی **روشن** شد.")
            return

        if caption == "اورلی خاموش":
            OVERLAY_ENABLED = False
            await event.reply("❌ اورلی **خاموش** شد.")
            return

        # ========== کیفیت دانلود: اعداد انگلیسی، فارسی و عربی ==========
        quality_text = caption.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        quality_match = re.fullmatch(r"کیفیت\s+(\d{1,4})\s*p?", quality_text)
        if quality_match:
            requested = int(quality_match.group(1))
            if not 1 <= requested <= 8640:
                await event.reply("⚠️ کیفیت باید عددی مثبت تا 8640 باشد؛ مثلاً: کیفیت 720")
                return
            DOWNLOAD_QUALITY = requested
            await event.reply(
                f"✅ سقف کیفیت دانلود روی **{DOWNLOAD_QUALITY}p** تنظیم شد.\n"
                "⚡ اولویت با HLS است؛ اگر موجود نباشد، فرمت دیگر در همین سقف انتخاب می‌شود.\n"
                "این تنظیم برای دانلودهای بعدی اعمال می‌شود."
            )
            return
        if caption.startswith("کیفیت"):
            await event.reply(
                f"🎬 سقف کیفیت فعلی: **{DOWNLOAD_QUALITY}p**\n"
                "برای تغییر: `کیفیت 480` یا `کیفیت 720` یا `کیفیت 1080`"
            )
            return

        # ========== لغو ==========
        if caption == "لغو":
            cancel_flag = True
            # آپلودهای پس‌زمینه هم جزو عملیات جاری‌اند و با «لغو» متوقف می‌شوند.
            for task in list(upload_tasks):
                if not task.done():
                    task.cancel()
            while not queue.empty():
                try:
                    _, q_path = queue.get_nowait()
                    queue.task_done()
                    if q_path and os.path.exists(q_path):
                        try: os.remove(q_path)
                        except: pass
                except: break
            subprocess.run(["pkill", "-f", "ffmpeg"], capture_output=True)
            subprocess.run(["pkill", "-f", "yt-dlp"], capture_output=True)
            subprocess.run(["pkill", "-f", "curl"], capture_output=True)
            subprocess.run(["pkill", "-f", "chromium"], capture_output=True)
            processing = False
            await event.reply("✅ تمام عملیات‌ها لغو شدند.")
            await asyncio.sleep(3)
            cancel_flag = False
            return

        # ========== ذخیره اورلی ==========
        if is_overlay_intent:
            if event.message.photo or event.message.video or (
                event.message.document and (
                    "video" in getattr(event.message.document, "mime_type", "") or
                    "image" in getattr(event.message.document, "mime_type", "")
                )
            ):
                await save_overlay_image(event)
            else:
                await event.reply("⚠️ لطفاً عکس یا ویدیو را همراه با کلمه «اورلی» ارسال کنید.")
            return

        # ========== دانلود لینک ==========
        if is_link:
            status = await event.reply("📥 لینک دریافت شد، شروع دانلود آنی...")
            url = raw_text.split()[0]
            downloaded_path = await download_link(url, status)
            if cancel_flag:
                await safe_edit(status, "⏹️ عملیات لغو شد.")
                return
            if downloaded_path:
                await queue.put((event, downloaded_path))
                wm_status = "با واترمارک" if WATERMARK_ENABLED else "بدون واترمارک"
                ol_status = "با اورلی" if OVERLAY_ENABLED else "بدون اورلی"
                await safe_edit(
                    status,
                    f"✅ دانلود کامل شد.\n"
                    f"({wm_status} | {ol_status} | {DOWNLOAD_QUALITY}p)\n"
                    f"صف: {queue.qsize()}"
                )
                if not processing: asyncio.create_task(worker())
                return
            else:
                await safe_edit(status, "❌ دانلود لینک انجام نشد.")
                return

        # ========== ویدیو ارسال شده ==========
        is_video_file = is_video_message(event.message) and not is_overlay_intent
        if is_video_file:
            status = await event.reply("⬇️ در حال دانلود ویدیو...")
            dest_path = tempfile.mktemp(
                suffix=".mp4",
                dir=TEMP_PATH
            )
            try:
                path = await fast_tg_download(event.message, dest_path, status)
            except Exception as e:
                await safe_edit(status, f"❌ خطا در دانلود ویدیو: {e}")
                return
            if not path or not os.path.exists(path):
                await safe_edit(status, "❌ فایل دریافت نشد.")
                return
            file_size = os.path.getsize(path)
            if file_size < 500_000:
                await safe_edit(status, "⚠️ فایل ناقص است. دوباره به صورت فایل بفرستید.")
                try: os.remove(path)
                except: pass
                return
            await queue.put((event, path))
            wm_status = "با واترمارک" if WATERMARK_ENABLED else "بدون واترمارک"
            ol_status = "با اورلی" if OVERLAY_ENABLED else "بدون اورلی"
            await safe_edit(status, f"📋 در صف پردازش: {queue.qsize()} ({wm_status} | {ol_status})")
            if not processing: asyncio.create_task(worker())
            return

    #================== اجرا ==================
    async def main():
        global IS_BOT_ACCOUNT, client
        print("🔌 در حال اتصال به تلگرام با WZGram...")
        # Client must be constructed inside its own running loop. Marimo's loop stays untouched.
        client = _WZGramCompatClient()
        client.register_owner_handler(handler)
        print(
            f"⚡ WZGram آمادهٔ انتقال موازی است | حداکثر انتقال هم‌زمان: {client.max_transfers}"
        )
        # 🧹 پاک‌سازی فایل‌های ناقص/موقت باقی‌مانده از اجرای قبلی
        #    (خروج ناگهانی، دکمه Stop و...) — تا ربات همیشه تمیز روشن بشه
        cleanup_incomplete_files("شروع")
        # اگه FORCE_RELOGIN = True باشه، فقط نشست اختصاصی WZGram پاک می‌شود.
        if FORCE_RELOGIN:
            session_paths = [
                os.path.join(WZGRAM_SESSION_DIR, SESSION_NAME + ".session"),
            ]
            for sf in session_paths:
                if os.path.exists(sf):
                    try:
                        os.remove(sf)
                        print(f"⚠️ session قدیمی حذف شد: {sf}")
                    except Exception as e:
                        print(f"❌ خطا در حذف session: {e}")
        # چک سلامت OpenCV — اگه numpy/opencv خراب باشه فقط هشدار میده، ربات قطع نمیشه
        try:
            import cv2
            print("✅ OpenCV:", cv2.__version__)
        except Exception as e:
            print("⚠️ OpenCV در دسترس نیست:", e)
            print("   (تشخیص چهره موقتا غیرفعاله؛ بقیهٔ ربات کار می‌کنه)")
            print("   برای رفع: ری‌استارت رانتایم + اجرای دوبارهٔ سلول نصب — بعدش دیگه نیازی نیست)")
        try:
            # WZGram credentials are passed to its constructor; start() takes no credential arguments.
            await client.start()
            me = await client.get_me()
            IS_BOT_ACCOUNT = bool(me and (getattr(me, "is_bot", False) or getattr(me, "bot", False)))
            print("✅ نوع نشست تلگرام:", "Bot (inline فعال)" if IS_BOT_ACCOUNT else "User (انتخاب شماره‌ای تامبنیل)")
            _is_premium = bool(getattr(me, "is_premium", False) or getattr(me, "premium", False))
            _acct = "bot" if IS_BOT_ACCOUNT else ("premium" if _is_premium else "user")
            _rate_key = {"bot": "WZGRAM_UPLOAD_RATE_BOT", "premium": "WZGRAM_UPLOAD_RATE_PREMIUM", "user": "WZGRAM_UPLOAD_RATE_USER"}[_acct]
            _pool_key = {"bot": "WZGRAM_UPLOAD_POOL_BOT", "premium": "WZGRAM_UPLOAD_POOL_PREMIUM", "user": "WZGRAM_UPLOAD_POOL_USER"}[_acct]
            if _acct == "premium":
                print("🚀 حساب پریمیوم: آپلود بدون پِیسِر (unpaced) + سقف ۴ گیگ")
            else:
                print(
                    f"🚀 پروفایل آپلود ({_acct}): سقف پِیسِر {os.environ.get(_rate_key, '?')} پارت/ثانیه"
                    f" (~{int(os.environ.get(_rate_key, '0')) * 0.5:.0f} MB/s مجاز) |"
                    f" پول رسانه‌ای {os.environ.get(_pool_key, '?')} نشست |"
                    f" حساب {'پریمیوم نیست؛ اگر آپلود هنوز ~۲-۳ MB/s بماند، سقف سمت تلگرام/آپ‌لینک است'}"
                )
            print("   💡 برای دیدن دلیل دقیق افت سرعت: WZGRAM_DEBUG=1 را در محیط ست کن (FloodWaitها چاپ می‌شوند)")
        except Exception as e:
            m = str(e).upper()
            print("❌ خطا در اتصال تلگرام:", e)
            if "FLOOD" in m:
                print("⏳ تلگرام دسترسی را موقتاً محدود کرده — ۱۰ دقیقه صبر کن و دوباره اجرا کن")
            elif any(k in m for k in ("BLOCKED", "BANNED", "DEACTIVATED", "TERMINATED")):
                print("🚫 اکانت تلگرام محدود یا غیرفعال شده است (از اپ تلگرام چک کن)")
            elif any(k in m for k in ("SESSION", "AUTH", "PHONE")):
                print("🛠️ session قبلی نامعتبر است (معمولاً از ری‌استارت وسط لاگین).")
                print("   فایل session پاک شد — در اجرای بعد فقط یک‌بار کد تلگرام را وارد کن")
                for sf in (os.path.join(WZGRAM_SESSION_DIR, SESSION_NAME + ".session"),):
                    if os.path.exists(sf):
                        try:
                            os.remove(sf)
                            print(f"   🗑️ {sf} پاک شد")
                        except Exception:
                            pass
            raise
        await asyncio.sleep(3)  # شروع آرام‌تر تا درخواست‌های اولیه پشت سر هم نروند
        print(f"✅ ربات آماده — OWNER_ID: {OWNER_ID}")

        # WZGram مدیریت اتصال مجدد و انتقال‌های رسانه‌ای را درون خود انجام می‌دهد.
        # idle فقط اجرای برنامه را تا سیگنال توقف زنده نگه می‌دارد.
        try:
            await client.run_until_disconnected()
        except asyncio.CancelledError:
            raise

    # ---------------- اجرای ایزولهٔ ربات روی uvloop ----------------
    # Marimo حلقهٔ خودش را دارد؛ WZGram از ابتدا تا انتها روی یک حلقهٔ اختصاصی اجرا می‌شود.
    BOT_LOOP = None
    BOT_MAIN_TASK = None
    BOT_THREAD = None
    BOT_THREAD_ERROR = None
    BOT_STOP_EVENT = threading.Event()

    def _request_bot_stop():
        """درخواست توقف امن ربات از حلقهٔ Marimo یا هنگام لغو سلول."""
        BOT_STOP_EVENT.set()
        loop_ref = BOT_LOOP
        task_ref = BOT_MAIN_TASK
        if loop_ref is not None and task_ref is not None and not task_ref.done():
            try:
                loop_ref.call_soon_threadsafe(task_ref.cancel)
            except Exception as stop_error:
                print("⚠️ ارسال درخواست توقف ربات ناموفق بود:", stop_error)

    async def _bot_loop_lifecycle():
        global BOT_MAIN_TASK
        BOT_MAIN_TASK = asyncio.current_task()
        try:
            # حتی اگر Stop پیش از آماده‌شدن loop برسد، درخواست از دست نمی‌رود.
            if BOT_STOP_EVENT.is_set():
                raise asyncio.CancelledError()
            await main()
        finally:
            # اول وظایف ارسال را متوقف و جمع می‌کنیم، بعد اتصال WZGram را می‌بندیم.
            pending_uploads = [t for t in list(upload_tasks) if not t.done()]
            for task in pending_uploads:
                task.cancel()
            if pending_uploads:
                await asyncio.gather(*pending_uploads, return_exceptions=True)
            try:
                if client is not None:
                    await client.disconnect()
            except Exception:
                pass
            cleanup_incomplete_files("پایان")
            print("🧹 پاکسازی کامل شد.")

    def _bot_uvloop_thread_main():
        global BOT_LOOP, BOT_THREAD_ERROR
        loop_ref = None
        try:
            if _UVLOOP_AVAILABLE:
                loop_ref = uvloop.new_event_loop()
                loop_label = f"uvloop {getattr(uvloop, '__version__', '')}".strip()
            else:
                loop_ref = asyncio.new_event_loop()
                loop_label = "asyncio استاندارد (fallback)"
            asyncio.set_event_loop(loop_ref)
            BOT_LOOP = loop_ref

            # تمام primitiveهای async متعلق به ربات روی همین loop ساخته می‌شوند.
            global _safe_edit_lock, _safe_edit_last_at, queue, upload_semaphore
            _safe_edit_lock = asyncio.Lock()
            _safe_edit_last_at = 0.0
            queue = asyncio.Queue()
            upload_semaphore = asyncio.Semaphore(TG_UPLOAD_CONCURRENCY)

            print(f"🚀 حلقهٔ اجرای ربات: {loop_label}")
            print("✅ WZGram، صف پردازش، قفل وضعیت و semaphore روی یک حلقهٔ مستقل اجرا می‌شوند.")
            loop_ref.run_until_complete(_bot_loop_lifecycle())
        except asyncio.CancelledError:
            print("⏹️ اجرای ربات لغو شد.")
        except KeyboardInterrupt:
            print("⏹️ توقف دریافت شد.")
        except BaseException as loop_error:
            BOT_THREAD_ERROR = loop_error
            print("❌ خطای حلقهٔ ربات:", repr(loop_error))
            traceback.print_exc()
        finally:
            if loop_ref is not None and not loop_ref.is_closed():
                try:
                    pending = [t for t in asyncio.all_tasks(loop_ref) if not t.done()]
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop_ref.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception as shutdown_error:
                    print("⚠️ پاک‌سازی taskهای uvloop:", shutdown_error)
                try:
                    loop_ref.run_until_complete(loop_ref.shutdown_asyncgens())
                except Exception:
                    pass
                try:
                    loop_ref.run_until_complete(loop_ref.shutdown_default_executor())
                except Exception:
                    pass
                try:
                    loop_ref.close()
                except Exception:
                    pass
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass
            BOT_LOOP = None

    # signal handler فقط در ترد اصلی مجاز است؛ اینجا قبل از ساخت ترد ثبت می‌شود.
    _install_exit_handlers()
    BOT_THREAD = threading.Thread(
        target=_bot_uvloop_thread_main,
        name="telegram-uvloop-runtime",
        daemon=True,
    )
    BOT_THREAD.start()
    _BOT_ACTIVE_THREAD = BOT_THREAD
    print("✅ ربات روی حلقهٔ مستقل شروع شد؛ Marimo loop دست‌نخورده باقی می‌ماند.")




    '''
    import textwrap as _textwrap
    _embedded_source = _textwrap.dedent(_embedded_source).lstrip("\n")
    exec(compile(_embedded_source, "telegram_gilas_khis_marimo_wzgram.py", "exec"), globals(), globals())
    _bot_thread_ref = globals().get("BOT_THREAD")
    if _bot_thread_ref is not None:
        try:
            await _marimo_asyncio.to_thread(_bot_thread_ref.join)
        except _marimo_asyncio.CancelledError:
            _stop_fn = globals().get("_request_bot_stop")
            if callable(_stop_fn):
                _stop_fn()
            await _marimo_asyncio.to_thread(_bot_thread_ref.join)
            raise
        _thread_error = globals().get("BOT_THREAD_ERROR")
        if _thread_error is not None:
            raise RuntimeError("اجرای ربات روی حلقهٔ اختصاصی متوقف شد") from _thread_error
    return


if __name__ == "__main__":
    app.run()
