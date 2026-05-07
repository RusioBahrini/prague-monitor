import asyncio
import hashlib
import requests
import os
from playwright.async_api import async_playwright
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID   = os.environ.get("CHAT_ID", "")
URL       = "https://prague.pasport.org.ua/solutions/e-queue"
CHECK_INTERVAL = 1860
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def send_telegram(text: str):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        if r.status_code != 200:
            log(f"Помилка Telegram: {r.text}")
    except Exception as e:
        log(f"Не вдалось надіслати: {e}")

async def get_page_text() -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=40000)
        await asyncio.sleep(7)
        text = await page.inner_text("body")
        await browser.close()
        return text

def make_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def has_free_slots(text: str) -> bool:
    markers = [
        "вільн", "available", "оберіть",
        "обрати час", "обрати дату",
        "вибрати дату", "записатись", "slot",
    ]
    t = text.lower()
    return any(m in t for m in markers)

async def main():
    log("Бот запущено")
    send_telegram(
        "✅ <b>Моніторинг запущено!</b>\n"
        f"🔗 {URL}\n"
        f"⏱ Перевірка кожні {CHECK_INTERVAL} сек.\n\n"
        "Як тільки з'являться вільні місця — одразу напишу! 🔔"
    )

    prev_hash = None

    while True:
        try:
            log("Перевіряю сторінку...")
            text = await get_page_text()
            cur_hash = make_hash(text)

            if prev_hash is None:
                prev_hash = cur_hash
                log("Початковий стан збережено")
            elif cur_hash != prev_hash:
                log("Сторінка змінилась!")
                if has_free_slots(text):
                    send_telegram(
                        "🟢 <b>З'ЯВИЛИСЬ ВІЛЬНІ МІСЦЯ!</b>\n\n"
                        f"👉 Переходь ЗАРАЗ:\n{URL}\n\n"
                        "⚡ Дій швидко — місця можуть зникнути!"
                    )
                else:
                    send_telegram(
                        f"🔄 Сторінка змінилась.\n"
                        f"Перевір сам: {URL}"
                    )
                prev_hash = cur_hash
            else:
                log("Змін немає")

        except Exception as e:
            log(f"Помилка: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
