import os
import time
import requests

# ضع توكن بوت Telegram هنا
TOKEN = "اكتب_توكن_بوتك_هنا"

# مفتاح Google YouTube API (اختياري للبحث الفعلي)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

API = f"https://api.telegram.org/bot{TOKEN}"
MAX_SIZE = 45 * 1024 * 1024
session = requests.Session()


def send(chat_id, text):
    session.post(
        f"{API}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=30
    )


def search_videos(keyword):
    if not YOUTUBE_API_KEY:
        return (
            "للبحث الفعلي، أضف YOUTUBE_API_KEY إلى GitHub Secrets.\n\n"
            "رابط البحث:\n"
            f"https://www.youtube.com/results?search_query={requests.utils.quote(keyword)}"
        )

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": YOUTUBE_API_KEY,
        "q": keyword,
        "part": "snippet",
        "type": "video",
        "maxResults": 5
    }

    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    items = response.json().get("items", [])

    if not items:
        return "لم أجد نتائج لهذه الكلمة."

    result = f"نتائج البحث عن: {keyword}\n\n"

    for i, item in enumerate(items, 1):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        link = f"https://www.youtube.com/watch?v={video_id}"
        result += f"{i}. {title}\n{link}\n\n"

    return result


def download_direct(url, chat_id):
    # يقبل روابط ملفات فيديو مباشرة فقط، ولا يستخرج الفيديو من صفحات المواقع.
    if not url.startswith("https://"):
        send(chat_id, "يجب أن يكون الرابط HTTPS.")
        return

    allowed_extensions = (".mp4", ".mov", ".webm", ".m4v")
    if not url.lower().split("?")[0].endswith(allowed_extensions):
        send(chat_id, "هذا ليس رابط ملف فيديو مباشر مدعوم.")
        return

    send(chat_id, "بدأ تنزيل الفيديو...")

    path = "/tmp/video_download.mp4"

    try:
        with session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()

            size = int(r.headers.get("Content-Length", 0))
            if size > MAX_SIZE:
                send(chat_id, "حجم الفيديو أكبر من 45 ميجابايت.")
                return

            downloaded = 0

            with open(path, "wb") as f:
                for chunk in r.iter_content(1024 * 256):
                    if not chunk:
                        continue

                    downloaded += len(chunk)

                    if downloaded > MAX_SIZE:
                        send(chat_id, "الفيديو تجاوز حد الحجم.")
                        return

                    f.write(chunk)

        send(chat_id, "اكتمل التنزيل، جاري إرساله...")

        with open(path, "rb") as video:
            response = session.post(
                f"{API}/sendVideo",
                data={"chat_id": chat_id},
                files={"video": ("video.mp4", video, "video/mp4")},
                timeout=180
            )

        response.raise_for_status()
        send(chat_id, "تم إرسال الفيديو.")

    except Exception as e:
        send(chat_id, f"حدث خطأ: {e}")

    finally:
        if os.path.exists(path):
            os.remove(path)


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    if text == "/start":
        send(
            chat_id,
            "أهلاً بك في بوت الفيديو.\n\n"
            "أرسل كلمة إنجليزية للبحث.\n"
            "أو أرسل رابط ملف فيديو مباشر HTTPS لتنزيله.\n\n"
            "مثال:\n"
            "/search nature"
        )
        return

    if text.startswith("/search "):
        keyword = text.replace("/search ", "", 1).strip()

        if not keyword:
            send(chat_id, "اكتب كلمة البحث بعد الأمر.")
            return

        send(chat_id, "جاري البحث...")
        try:
            send(chat_id, search_videos(keyword))
        except Exception as e:
            send(chat_id, f"تعذر البحث: {e}")
        return

    if text.startswith("https://"):
        download_direct(text, chat_id)
        return

    send(
        chat_id,
        "للبحث اكتب:\n/search nature\n\n"
        "ولتنزيل ملف فيديو أرسل رابط HTTPS مباشر للملف."
    )


def main():
    if TOKEN == "9063389269:AAHvZP5Uc_bBwJjXv8_5yAWfJ9icDlRy81o":
        print("ضع توكن البوت في متغير TOKEN داخل الملف.")
        return

    offset = None
    print("Bot started")

    while True:
        try:
            params = {"timeout": 50}

            if offset is not None:
                params["offset"] = offset

            response = session.get(
                f"{API}/getUpdates",
                params=params,
                timeout=60
            )
            response.raise_for_status()

            updates = response.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1

                if "message" in update:
                    handle_message(update["message"])

        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
