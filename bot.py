import os
import uuid
import asyncio
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

BOT_TOKEN = "8994808219:AAFpR3xt2leyIcpbKYrOjZ9ZaYdTD-6OHO0"

DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 1024 * 1024  # 1 MB

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


PHOTO_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

VIDEO_EXT = {
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
    ".m4v"
}


def get_media_type(filename):

    ext = os.path.splitext(
        filename
    )[1].lower()

    if ext in PHOTO_EXT:
        return "photo"

    if ext in VIDEO_EXT:
        return "video"

    return None


bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


def is_discord_attachment(url: str) -> bool:
    hosts = {
        "cdn.discordapp.com",
        "media.discordapp.net"
    }

    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and parsed.netloc.lower() in hosts
            and "/attachments/" in parsed.path
        )
    except:
        return False


async def download_stream(
    url: str,
    filepath: str,
    progress_callback=None
):

    timeout = aiohttp.ClientTimeout(
        total=None
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers
    ) as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception(
                    f"HTTP {resp.status}"
                )

            total_size = int(
                resp.headers.get(
                    "Content-Length",
                    0
                )
            )

            downloaded = 0

            with open(filepath, "wb") as f:

                async for chunk in resp.content.iter_chunked(
                    CHUNK_SIZE
                ):
                    f.write(chunk)

                    downloaded += len(chunk)

                    if (
                        total_size > 0
                        and progress_callback
                    ):
                        percent = int(
                            downloaded
                            * 100
                            / total_size
                        )

                        await progress_callback(
                            percent,
                            downloaded,
                            total_size
                        )


@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "Kirim URL attachment Discord."
    )


@dp.message()
async def handle_download(
    message: Message
):

    url = (
        message.text or ""
    ).strip()

    if not url.startswith("http"):
        return

    if not is_discord_attachment(url):

        return await message.answer(
            "URL Discord tidak valid."
        )

    status = await message.answer(
        "⏳ Memulai download..."
    )

    filename = (
        url.split("/")[-1]
        .split("?")[0]
    )

    if not filename:
        filename = "file.bin"

    filepath = os.path.join(
        DOWNLOAD_DIR,
        f"{uuid.uuid4()}_{filename}"
    )

    last_percent = -1

    async def progress(
        percent,
        downloaded,
        total
    ):
        nonlocal last_percent

        if percent == last_percent:
            return

        if percent % 5 != 0:
            return

        last_percent = percent

        try:
            await status.edit_text(
                f"⬇️ Downloading...\n"
                f"{percent}%"
            )
        except:
            pass

    try:

        await download_stream(
            url,
            filepath,
            progress
        )

        await status.edit_text(
            "📤 Mengirim ke Telegram..."
        )

        file = FSInputFile(filepath)

        media_type = get_media_type(
            filename
        )

        if media_type == "photo":

            await message.answer_photo(
                photo=file,
                caption=filename
            )

        elif media_type == "video":

            await message.answer_video(
                video=file,
                caption=filename,
                supports_streaming=True
            )

        else:

            await message.answer(
                "❌ File bukan foto atau video."
            )

        await status.edit_text(
            "✅ Selesai"
        )

    except Exception as e:

        await status.edit_text(
            f"❌ Error\n<code>{e}</code>"
        )

    finally:

        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass


async def main():

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())