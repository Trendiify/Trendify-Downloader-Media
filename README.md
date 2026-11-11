<div align="center">

# 📥 Telegram Media Downloader Bot

**Send a link → get the video.**
A Telegram bot with two independent implementations: a free serverless bot on **Cloudflare Workers** and a **yt-dlp** powered Python bot on **Render**.

[English](#english) · [فارسی](#persian)

</div>

---

<a id="english"></a>

# English

## Table of contents

- [Overview](#overview)
- [Which option should I choose?](#which-option-should-i-choose)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Option A: Cloudflare Worker (free, no server)](#option-a-cloudflare-worker-free-no-server)
- [Option B: Python bot on Render (yt-dlp)](#option-b-python-bot-on-render-yt-dlp)
- [Troubleshooting](#troubleshooting)
- [Security checklist](#security-checklist)
- [Limitations](#limitations)
- [Legal notice](#legal-notice)
- [Credits](#credits)

## Overview

| Component | Runs on | Cost | Platforms | How it delivers |
|---|---|---|---|---|
| **Option A** – `worker/` | Cloudflare Workers | Free | TikTok, Twitter/X, Instagram, YouTube (button) | Sends the file directly in Telegram (YouTube: a button to a download site) |
| **Option B** – `render-bot/` | Render (Python) | Free tier available | YouTube and 1000+ sites supported by yt-dlp | Quality picker (1080p / 720p / 480p / MP3), file sent in Telegram |

> ⚠️ A single Telegram bot token can have **only one webhook**. If you deploy both options, create **two different bots** with @BotFather (two tokens).

## Which option should I choose?

| You want… | Choose |
|---|---|
| Zero cost, no server, no cookies | **Option A** |
| TikTok, X and Instagram downloaded directly inside Telegram | **Option A** |
| YouTube downloaded inside Telegram with quality selection | **Option B** (needs cookies and Deno, and can break when YouTube changes) |
| The most stable setup | **Both**, with two bots |

## Project structure

```text
.
├── worker/                  # Option A: Cloudflare Worker
│   ├── worker.js
│   └── wrangler.toml
├── render-bot/              # Option B: Python bot for Render
│   ├── main.py              # rename bot.py to main.py (Render runs "python main.py")
│   ├── requirements.txt
│   └── Dockerfile           # optional, only for the Docker deployment
├── .gitignore
└── README.md
```

## Prerequisites

- A Telegram account and a bot token from [@BotFather](https://t.me/BotFather) (`/newbot`)
- A GitHub account (to host this repository)
- **Option A:** a free [Cloudflare](https://dash.cloudflare.com/sign-up) account and [Node.js](https://nodejs.org/) 18+
- **Option B:** a [Render](https://render.com/) account, and a throwaway Google account for YouTube cookies

---

## Option A: Cloudflare Worker (free, no server)

### How each platform is handled

| Platform | Method |
|---|---|
| TikTok | Public API (`tikwm.com`), no watermark, HD when available, photo slideshows supported |
| Twitter / X | Public API (`api.fxtwitter.com`), videos and photos |
| Instagram | The Worker fetches a fresh token from `save-free.app`, calls its API, downloads the file and uploads it to Telegram (up to 50 MB). If this fails, the bot sends a fallback button (`ddinstagram`) |
| YouTube | Workers cannot run yt-dlp, and YouTube blocks data-center IPs. The bot sends a **button** to a download page. Optional: set `COBALT_API` to get automatic downloads |

### 1. Create the bot

1. Open [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token.

### 2. Deploy the Worker

```bash
cd worker
npx wrangler login

# Secrets are stored encrypted by Cloudflare. They are NOT in the code.
npx wrangler secret put BOT_TOKEN        # paste your bot token
npx wrangler secret put WEBHOOK_SECRET   # any random string: letters, digits, _ and -

npx wrangler deploy
```

Wrangler prints your Worker URL, for example `https://video-downloader-bot.<subdomain>.workers.dev`.

### 3. Connect Telegram to the Worker

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://video-downloader-bot.<subdomain>.workers.dev" \
  -d "secret_token=<WEBHOOK_SECRET>"
```

You should get `{"ok":true,"result":true,"description":"Webhook was set"}`.

### 4. Test

Send the bot a TikTok, X or Instagram link. For a YouTube link you get a button to a download page.

### Configuration

Edit the constants at the top of `worker.js`:

| Setting | Default | Meaning |
|---|---|---|
| `YT_FALLBACK_PAGE` | `https://yt5s.biz/enwr200/` | Page opened by the YouTube button. The user pastes the link there |
| `YT_SWAP_HOST` | `""` (off) | Optional domain-swap mode: the button opens the same YouTube link on another domain. Only use a service you trust |

Optional variables in `wrangler.toml` (YouTube and other sites through [Cobalt](https://github.com/imputnet/cobalt)):

```toml
[vars]
COBALT_API = "https://your-cobalt-host.example.com/"
```

If your Cobalt requires a key: `npx wrangler secret put COBALT_KEY`.

### Debugging

```bash
npx wrangler tail          # live logs, look for lines starting with "IG:"
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

---

## Option B: Python bot on Render (yt-dlp)

### How it works

The bot uses `yt-dlp` to read the video, shows quality buttons, downloads (merging video and audio with ffmpeg), and uploads the file to Telegram (limit: 49 MB).
For YouTube, yt-dlp needs **two extra things**:

1. A **JavaScript runtime (Deno)** to solve YouTube's player challenge.
2. Fresh **cookies** from a logged-in account, because Render's IP is a data-center IP that YouTube treats with suspicion.

### 1. Export YouTube cookies (correctly)

YouTube rotates cookies of sessions that stay open in the browser, which makes exported cookies invalid within minutes. Use this procedure:

1. Open a **new Incognito/Private window** and log in to YouTube (use a **separate, throwaway Google account**, not your main one).
2. In the **same tab**, open `https://www.youtube.com/robots.txt`. This must be the only Incognito tab.
3. Export the `youtube.com` cookies in **Netscape format** with a cookie-export extension (for example "Get cookies.txt LOCALLY").
4. **Close the Incognito window immediately.**
5. Save the file as `youtube_cookies.txt`.

### 2. Put the code on GitHub

Copy the files into `render-bot/`. **Do not commit `youtube_cookies.txt` or any token.**
Make sure the main file is named `main.py`.

`requirements.txt`:

```text
yt-dlp[default]
python-telegram-bot[webhooks]>=21
imageio-ffmpeg
```

> Use `yt-dlp[default]` (not plain `yt-dlp`). It includes the scripts needed for YouTube's challenge.

### 3. Create the Render service (without Docker)

In Render: **New → Web Service**, connect your GitHub repo, and set:

| Field | Value |
|---|---|
| Root Directory | `render-bot` (if you use the structure above) |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt && curl -fsSL https://deno.land/install.sh \| DENO_INSTALL=$PWD/.deno sh` |
| Start Command | `python main.py` |

**Environment variables**

| Name | Required | Value |
|---|---|---|
| `BOT_TOKEN` | Yes | Token of the bot for this service |
| `DENO_BIN` | Recommended | `/opt/render/project/src/.deno/bin/deno` (adjust if you use a Root Directory: `/opt/render/project/src/<root>/.deno/bin/deno`) |
| `WEBHOOK_SECRET` | No | Random string (a random one is generated at every start if empty) |
| `PROXY_URL` | No | Proxy for yt-dlp, e.g. `http://user:pass@host:port` |
| `YTDLP_VERBOSE` | No | `1` (default) shows detailed yt-dlp logs, `0` hides them |

Render provides `PORT` and `RENDER_EXTERNAL_HOSTNAME` automatically.

**Secret file:** in **Environment → Secret Files**, add a file named `youtube_cookies.txt` with the content of your exported cookies. Render mounts it at `/etc/secrets/youtube_cookies.txt`, which is where the code reads it.

> The bot sets its own webhook at startup. **Do not call `setWebhook` manually** for this bot.

### 3b. Alternative: Docker

Use the provided `Dockerfile` (it copies the Deno binary into the image). In Render choose **Docker** as the runtime and keep the same environment variables and secret file.

### 4. Verify the startup log

After deploy, the first lines must look like this:

```text
INFO - yt-dlp version: 2026.x.x
INFO - Deno path: /opt/render/project/src/.deno/bin/deno
INFO - Proxy: none
INFO - Cookies file present: True
```

If you see `Deno path: NOT FOUND`, set `DENO_BIN` as shown above.

### 5. Test

Send a YouTube link, pick a quality, and wait for the file.

---

## Troubleshooting

| Symptom (in logs or in the bot) | Cause | Fix |
|---|---|---|
| `JS runtimes: none`, `n challenge solving failed`, `Only images are available`, `Requested format is not available` | Deno is missing | Install Deno (build command or Docker), set `DENO_BIN`, check `Deno path:` in the startup log |
| `Sign in to confirm you're not a bot` | YouTube blocks the request (invalid cookies and/or data-center IP) | Re-export cookies with the Incognito method, replace the secret file, redeploy. If it keeps coming back, use a residential proxy (`PROXY_URL`) or host at home |
| `The provided YouTube account cookies are no longer valid ... rotated` | Cookies were rotated by YouTube | Export new cookies, and close the Incognito window right after exporting |
| `HTTP Error 429: Too Many Requests` | YouTube rate-limits the IP | Wait, reduce traffic, or use a proxy |
| File is not sent / upload timeout | File is bigger than 49 MB or the upload is slow | Choose a lower quality or MP3 |
| Worker: Instagram says token not found, or captcha | The helper site changed or asks for a captcha | Run `npx wrangler tail`; the bot already offers the fallback button |
| Worker: bot does not reply | Webhook is not set, or the secret does not match (HTTP 403) | Check `getWebhookInfo` and that `secret_token` equals the `WEBHOOK_SECRET` secret |
| Render: first reply is slow | Free services sleep after inactivity | Normal behavior, wait a few seconds |
| Webhook conflicts | One bot token has only one webhook | Use two different bots for Option A and B |

## Security checklist

- **Never commit** bot tokens, `youtube_cookies.txt`, or `.env` files.
- If a token is leaked (logs, screenshots, videos), go to @BotFather → `/revoke`, then update `BOT_TOKEN` everywhere.
- Logs contain the bot token in Telegram API URLs. **Never show raw logs** in public posts, videos or issues.
- Use a **throwaway Google account** for cookies. Automated use may restrict the account.
- Keep cookies in Render **Secret Files**, never in the repository.

Recommended `.gitignore`:

```gitignore
.env
*.txt.bak
youtube_cookies.txt
cookies.txt
.deno/
.venv/
__pycache__/
node_modules/
.wrangler/
```

## Limitations

- YouTube regularly changes its anti-bot protection. Cookies can expire, and the bot may need updates (`pip install -U yt-dlp`).
- Telegram Bot API upload limit is about 50 MB (the bot uses 49 MB).
- Option A depends on third-party services (`tikwm`, `fxtwitter`, `save-free.app`, `ddinstagram`). They can change, rate-limit, or disappear without notice.
- Free hosting tiers have limits and can be slow after inactivity.

## Legal notice

This project is for **personal and educational use**. Downloading content may violate the terms of service of the platforms and copyright law. Only download content you own or have permission to download. You are responsible for how you use this software. It is not affiliated with Telegram, YouTube, Instagram, TikTok or X.

## Credits

[yt-dlp](https://github.com/yt-dlp/yt-dlp) · [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) · [Deno](https://deno.com/) · [Cobalt](https://github.com/imputnet/cobalt) · [InstaFix](https://github.com/Wikidepia/InstaFix) · [Cloudflare Workers](https://workers.cloudflare.com/) · [Render](https://render.com/)

## License

Add the license of your choice (for example MIT) in a `LICENSE` file.

---

<a id="persian"></a>

<div dir="rtl">

# فارسی

## فهرست

- [معرفی](#معرفی)
- [کدام گزینه را انتخاب کنم؟](#کدام-گزینه-را-انتخاب-کنم)
- [ساختار پروژه](#ساختار-پروژه)
- [پیش‌نیازها](#پیش‌نیازها)
- [گزینهٔ الف: Cloudflare Worker (رایگان، بدون سرور)](#گزینهٔ-الف-cloudflare-worker-رایگان-بدون-سرور)
- [گزینهٔ ب: ربات پایتون روی Render](#گزینهٔ-ب-ربات-پایتون-روی-render)
- [رفع اشکال](#رفع-اشکال)
- [نکات امنیتی](#نکات-امنیتی)
- [محدودیت‌ها](#محدودیتها)
- [اطلاعیهٔ حقوقی](#اطلاعیهٔ-حقوقی)

## معرفی

| بخش | اجرا روی | هزینه | پلتفرم‌ها | نحوهٔ ارسال |
|---|---|---|---|---|
| **گزینهٔ الف** – پوشهٔ `worker/` | Cloudflare Workers | رایگان | تیک‌تاک، توییتر/X، اینستاگرام، یوتیوب (با دکمه) | ارسال مستقیم فایل در تلگرام (یوتیوب: دکمه به سایت دانلود) |
| **گزینهٔ ب** – پوشهٔ `render-bot/` | Render (پایتون) | پلن رایگان دارد | یوتیوب و بیش از ۱۰۰۰ سایت پشتیبانی‌شده توسط yt-dlp | انتخاب کیفیت (۱۰۸۰ / ۷۲۰ / ۴۸۰ / MP3) و ارسال فایل در تلگرام |

> ⚠️ هر توکن ربات تلگرام فقط **یک وب‌هوک** می‌تواند داشته باشد. اگر هر دو گزینه را راه می‌اندازی، با @BotFather **دو ربات جدا** (دو توکن) بساز.

## کدام گزینه را انتخاب کنم؟

| می‌خواهی… | انتخاب |
|---|---|
| هزینهٔ صفر، بدون سرور، بدون کوکی | **گزینهٔ الف** |
| دانلود مستقیم تیک‌تاک، X و اینستاگرام داخل تلگرام | **گزینهٔ الف** |
| دانلود یوتیوب داخل تلگرام با انتخاب کیفیت | **گزینهٔ ب** (نیاز به کوکی و Deno دارد و با تغییر یوتیوب ممکن است خراب شود) |
| پایدارترین حالت | **هر دو**، با دو ربات |

## ساختار پروژه

```text
.
├── worker/                  # گزینهٔ الف: Cloudflare Worker
│   ├── worker.js
│   └── wrangler.toml
├── render-bot/              # گزینهٔ ب: ربات پایتون برای Render
│   ├── main.py              # فایل bot.py را به main.py تغییر نام بده
│   ├── requirements.txt
│   └── Dockerfile           # اختیاری، فقط برای دیپلوی با Docker
├── .gitignore
└── README.md
```

## پیش‌نیازها

- حساب تلگرام و توکن ربات از [@BotFather](https://t.me/BotFather) (دستور `/newbot`)
- حساب GitHub برای نگهداری این ریپازیتوری
- **گزینهٔ الف:** حساب رایگان [Cloudflare](https://dash.cloudflare.com/sign-up) و [Node.js](https://nodejs.org/) نسخهٔ ۱۸ به بالا
- **گزینهٔ ب:** حساب [Render](https://render.com/) و یک **حساب گوگل جدا و بی‌اهمیت** برای کوکی یوتیوب

---

## گزینهٔ الف: Cloudflare Worker (رایگان، بدون سرور)

### هر پلتفرم چطور پردازش می‌شود

| پلتفرم | روش |
|---|---|
| تیک‌تاک | API عمومی (`tikwm.com`)، بدون واترمارک، کیفیت HD در صورت وجود، پست‌های اسلایدشو پشتیبانی می‌شود |
| توییتر / X | API عمومی (`api.fxtwitter.com`)، ویدیو و عکس |
| اینستاگرام | Worker یک توکن تازه از `save-free.app` می‌گیرد، API آن را صدا می‌زند، فایل را دانلود می‌کند و در تلگرام آپلود می‌کند (تا ۵۰ مگابایت). اگر شکست بخورد، ربات یک دکمهٔ جایگزین (`ddinstagram`) می‌فرستد |
| یوتیوب | Workers نمی‌تواند yt-dlp را اجرا کند و یوتیوب IP دیتاسنترها را بلاک می‌کند. ربات یک **دکمه** به صفحهٔ دانلود می‌فرستد. اختیاری: با تنظیم `COBALT_API` دانلود خودکار می‌شود |

### ۱. ساخت ربات

۱. در تلگرام به [@BotFather](https://t.me/BotFather) برو، `/newbot` را بزن و توکن را کپی کن.

### ۲. دیپلوی Worker

```bash
cd worker
npx wrangler login

# Secretها در Cloudflare رمزگذاری‌شده نگهداری می‌شوند و داخل کد نیستند.
npx wrangler secret put BOT_TOKEN        # توکن ربات را بچسبان
npx wrangler secret put WEBHOOK_SECRET   # هر رشتهٔ تصادفی: حروف، عدد، _ و -

npx wrangler deploy
```

Wrangler آدرس Worker را چاپ می‌کند، مثلاً `https://video-downloader-bot.<subdomain>.workers.dev`.

### ۳. وصل کردن تلگرام به Worker

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://video-downloader-bot.<subdomain>.workers.dev" \
  -d "secret_token=<WEBHOOK_SECRET>"
```

باید پاسخ `{"ok":true,"result":true,"description":"Webhook was set"}` را ببینی.

### ۴. تست

یک لینک تیک‌تاک، X یا اینستاگرام به ربات بفرست. برای لینک یوتیوب یک دکمه به صفحهٔ دانلود می‌گیری.

### تنظیمات

ثابت‌های بالای فایل `worker.js` را ویرایش کن:

| تنظیم | پیش‌فرض | معنی |
|---|---|---|
| `YT_FALLBACK_PAGE` | `https://yt5s.biz/enwr200/` | صفحه‌ای که دکمهٔ یوتیوب باز می‌کند. کاربر لینک را آنجا می‌چسباند |
| `YT_SWAP_HOST` | `""` (خاموش) | حالت اختیاری تعویض دامنه: دکمه همان لینک یوتیوب را روی دامنهٔ دیگری باز می‌کند. فقط سرویسی را بگذار که به آن اعتماد داری |

متغیر اختیاری در `wrangler.toml` (یوتیوب و سایت‌های دیگر از طریق [Cobalt](https://github.com/imputnet/cobalt)):

```toml
[vars]
COBALT_API = "https://your-cobalt-host.example.com/"
```

اگر Cobalt تو کلید می‌خواهد: `npx wrangler secret put COBALT_KEY`.

### اشکال‌یابی

```bash
npx wrangler tail          # لاگ زنده؛ خط‌هایی که با "IG:" شروع می‌شوند را ببین
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

---

## گزینهٔ ب: ربات پایتون روی Render

### نحوهٔ کار

ربات با `yt-dlp` ویدیو را بررسی می‌کند، دکمه‌های کیفیت نشان می‌دهد، دانلود می‌کند (با ffmpeg صدا و تصویر را ترکیب می‌کند) و فایل را در تلگرام آپلود می‌کند (محدودیت: ۴۹ مگابایت).
برای یوتیوب، yt-dlp به **دو چیز اضافه** نیاز دارد:

۱. یک **JavaScript runtime (یعنی Deno)** برای حل چالش پلیر یوتیوب.
۲. **کوکی تازه** از یک حساب واردشده، چون IP سرور Render از نوع دیتاسنتر است و یوتیوب به آن مشکوک است.

### ۱. گرفتن کوکی یوتیوب (به روش درست)

یوتیوب کوکی‌های نشستی را که در مرورگر باز مانده می‌چرخاند و کوکی‌های صادرشده در چند دقیقه باطل می‌شوند. این روش را دنبال کن:

۱. یک **پنجرهٔ جدید Incognito/Private** باز کن و وارد یوتیوب شو (با یک **حساب گوگل جدا و بی‌اهمیت**، نه حساب اصلی).
۲. در **همان تب**، آدرس `https://www.youtube.com/robots.txt` را باز کن. این باید تنها تب Incognito باشد.
۳. کوکی‌های `youtube.com` را با یک افزونهٔ خروجی کوکی (مثلاً «Get cookies.txt LOCALLY») با **فرمت Netscape** ذخیره کن.
۴. **بلافاصله پنجرهٔ Incognito را ببند.**
۵. فایل را با نام `youtube_cookies.txt` نگه دار.

### ۲. گذاشتن کد روی GitHub

فایل‌ها را داخل `render-bot/` بگذار. **فایل `youtube_cookies.txt` و هیچ توکنی را commit نکن.**
مطمئن شو فایل اصلی `main.py` نام دارد.

فایل `requirements.txt`:

```text
yt-dlp[default]
python-telegram-bot[webhooks]>=21
imageio-ffmpeg
```

> حتماً `yt-dlp[default]` بنویس (نه فقط `yt-dlp`). این نسخه فایل‌های لازم برای چالش یوتیوب را دارد.

### ۳. ساخت سرویس در Render (بدون Docker)

در Render: **New ← Web Service**، ریپوی GitHub را وصل کن و این‌ها را بگذار:

| فیلد | مقدار |
|---|---|
| Root Directory | `render-bot` (اگر از ساختار بالا استفاده می‌کنی) |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt && curl -fsSL https://deno.land/install.sh \| DENO_INSTALL=$PWD/.deno sh` |
| Start Command | `python main.py` |

**متغیرهای محیطی**

| نام | اجباری | مقدار |
|---|---|---|
| `BOT_TOKEN` | بله | توکن رباتِ همین سرویس |
| `DENO_BIN` | پیشنهادی | `/opt/render/project/src/.deno/bin/deno` (اگر Root Directory گذاشتی: `/opt/render/project/src/<root>/.deno/bin/deno`) |
| `WEBHOOK_SECRET` | خیر | رشتهٔ تصادفی (اگر خالی باشد در هر بار اجرا یکی ساخته می‌شود) |
| `PROXY_URL` | خیر | پروکسی برای yt-dlp، مثلاً `http://user:pass@host:port` |
| `YTDLP_VERBOSE` | خیر | `1` (پیش‌فرض) لاگ کامل yt-dlp، `0` لاگ کم |

متغیرهای `PORT` و `RENDER_EXTERNAL_HOSTNAME` را خود Render می‌دهد.

**Secret File:** در **Environment ← Secret Files** یک فایل با نام `youtube_cookies.txt` بساز و محتوای کوکی را داخلش بگذار. Render آن را در `/etc/secrets/youtube_cookies.txt` می‌گذارد، که کد همان‌جا می‌خواند.

> ربات در شروع خودش وب‌هوک را تنظیم می‌کند. برای این ربات **`setWebhook` را دستی نزن.**

### ۳ب. روش جایگزین: Docker

از `Dockerfile` آماده استفاده کن (فایل باینری Deno را داخل ایمیج می‌گذارد). در Render گزینهٔ **Docker** را به‌عنوان Runtime انتخاب کن و همان متغیرها و Secret File را نگه دار.

### ۴. بررسی لاگ شروع

بعد از دیپلوی، چند خط اول لاگ باید شبیه این باشد:

```text
INFO - yt-dlp version: 2026.x.x
INFO - Deno path: /opt/render/project/src/.deno/bin/deno
INFO - Proxy: none
INFO - Cookies file present: True
```

اگر `Deno path: NOT FOUND` دیدی، `DENO_BIN` را همان‌طور که بالا گفته شد تنظیم کن.

### ۵. تست

یک لینک یوتیوب بفرست، کیفیت را انتخاب کن و منتظر فایل بمان.

---

## رفع اشکال

| نشانه (در لاگ یا در ربات) | علت | راه‌حل |
|---|---|---|
| `JS runtimes: none`، `n challenge solving failed`، `Only images are available`، `Requested format is not available` | Deno نصب نیست | Deno را نصب کن (Build Command یا Docker)، `DENO_BIN` را بگذار و خط `Deno path:` را در لاگ شروع ببین |
| `Sign in to confirm you're not a bot` | یوتیوب درخواست را رد می‌کند (کوکی باطل و/یا IP دیتاسنتر) | کوکی را با روش Incognito دوباره بگیر، Secret File را جایگزین کن و دوباره دیپلوی کن. اگر مدام برگشت، از پروکسی residential (`PROXY_URL`) یا هاست خانگی استفاده کن |
| `The provided YouTube account cookies are no longer valid ... rotated` | یوتیوب کوکی‌ها را چرخانده | کوکی جدید بگیر و بلافاصله پنجرهٔ Incognito را ببند |
| `HTTP Error 429: Too Many Requests` | یوتیوب IP را محدود کرده | صبر کن، ترافیک را کم کن یا پروکسی بگذار |
| فایل ارسال نمی‌شود / تایم‌اوت آپلود | حجم فایل از ۴۹ مگابایت بیشتر است یا آپلود کند است | کیفیت پایین‌تر یا MP3 انتخاب کن |
| Worker: اینستاگرام «توکن پیدا نشد» یا کپچا می‌گوید | سایت واسط تغییر کرده یا کپچا خواسته | `npx wrangler tail` را اجرا کن؛ ربات خودش دکمهٔ جایگزین را می‌فرستد |
| Worker: ربات جواب نمی‌دهد | وب‌هوک تنظیم نیست یا secret مطابقت ندارد (خطای 403) | `getWebhookInfo` را چک کن و مطمئن شو `secret_token` برابر `WEBHOOK_SECRET` است |
| Render: اولین پاسخ کند است | سرویس رایگان بعد از بی‌کاری می‌خوابد | رفتار عادی است، چند ثانیه صبر کن |
| تداخل وب‌هوک | هر توکن فقط یک وب‌هوک دارد | برای گزینهٔ الف و ب دو ربات جدا بساز |

## نکات امنیتی

- **هرگز** توکن ربات، `youtube_cookies.txt` یا فایل‌های `.env` را commit نکن.
- اگر توکنی لو رفت (لاگ، اسکرین‌شات، ویدیو)، در @BotFather دستور `/revoke` را بزن و `BOT_TOKEN` را همه‌جا عوض کن.
- لاگ‌ها توکن ربات را در آدرس‌های API تلگرام نشان می‌دهند. **لاگ خام را هرگز** در پست، ویدیو یا issue عمومی نشان نده.
- برای کوکی از یک **حساب گوگل جدا و بی‌اهمیت** استفاده کن. استفادهٔ خودکار ممکن است حساب را محدود کند.
- کوکی را در **Secret Files** رندر نگه دار، نه داخل ریپازیتوری.

فایل `.gitignore` پیشنهادی:

```gitignore
.env
*.txt.bak
youtube_cookies.txt
cookies.txt
.deno/
.venv/
__pycache__/
node_modules/
.wrangler/
```

## محدودیت‌ها

- یوتیوب مرتب محافظت ضدرباتش را عوض می‌کند. کوکی‌ها منقضی می‌شوند و ربات ممکن است نیاز به به‌روزرسانی داشته باشد (`pip install -U yt-dlp`).
- محدودیت آپلود Bot API تلگرام حدود ۵۰ مگابایت است (ربات ۴۹ مگابایت می‌گذارد).
- گزینهٔ الف به سرویس‌های شخص ثالث (`tikwm`، `fxtwitter`، `save-free.app`، `ddinstagram`) وابسته است. آن‌ها ممکن است بدون اطلاع تغییر کنند، محدودیت بگذارند یا از بین بروند.
- هاست رایگان محدودیت دارد و بعد از بی‌کاری ممکن است کند باشد.

## اطلاعیهٔ حقوقی

این پروژه برای **استفادهٔ شخصی و آموزشی** است. دانلود محتوا ممکن است با شرایط استفادهٔ پلتفرم‌ها و قوانین کپی‌رایت در تضاد باشد. فقط محتوایی را دانلود کن که مالک آن هستی یا اجازهٔ دانلودش را داری. مسئولیت نحوهٔ استفاده از این نرم‌افزار با خود توست. این پروژه هیچ ارتباطی با تلگرام، یوتیوب، اینستاگرام، تیک‌تاک یا X ندارد.

## مجوز

مجوز دلخواه خودت (مثلاً MIT) را در فایل `LICENSE` اضافه کن.

</div>
