import os
import uuid
import aiohttp
import asyncio

from pyrogram import Client, filters
from pyrogram.types import (
    InputMediaPhoto,
    InputMediaVideo
)


API_ID = 36507359
API_HASH = "9968050f79b08b2bfaa7bf84e2943208"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DOWNLOAD_DIR = os.path.join(
    BASE_DIR,
    "downloads"
)

CHUNK_SIZE = 1024 * 1024

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


app = Client(
    "discord_downloader",
    api_id=API_ID,
    api_hash=API_HASH
)


pending_rename = {}


def is_discord_attachment(url: str) -> bool:
    return (
        "cdn.discordapp.com/attachments/" in url
        or "media.discordapp.net/attachments/" in url
    )


def get_media_type(filename: str):
    ext = os.path.splitext(filename)[1].lower()

    if ext in PHOTO_EXT:
        return "photo"

    if ext in VIDEO_EXT:
        return "video"

    return None


async def download_file(url, filepath):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    timeout = aiohttp.ClientTimeout(
        total=None
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers
    ) as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                raise Exception(
                    f"HTTP {resp.status}"
                )

            with open(filepath, "wb") as f:

                async for chunk in resp.content.iter_chunked(
                    CHUNK_SIZE
                ):
                    f.write(chunk)


async def process_downloads(
    message,
    urls,
    base_name
):

    status = await message.reply(
        f"⏳ Memproses {len(urls)} file..."
    )

    success = 0

    uploaded_media = []
    all_files = []

    for index, url in enumerate(urls, start=1):

        original_name = (
            url.split("/")[-1]
            .split("?")[0]
        )

        ext = os.path.splitext(
            original_name
        )[1]

        if len(urls) == 1:

            filename = (
                f"{base_name}{ext}"
            )

        else:

            filename = (
                f"{base_name}_{index:02d}{ext}"
            )

        filepath = os.path.join(
            DOWNLOAD_DIR,
            f"{uuid.uuid4()}_{filename}"
        )

        all_files.append(filepath)

        try:

            await status.edit(
                f"⬇️ Download {index}/{len(urls)}"
            )

            await download_file(
                url,
                filepath
            )

            media_type = get_media_type(
                filename
            )

            if media_type is None:

                await message.reply(
                    f"❌ Format tidak didukung\n{filename}"
                )

                continue

            await status.edit(
                f"📦 Menyiapkan {index}/{len(urls)}"
            )

            print(
                "FILE EXISTS:",
                os.path.exists(filepath)
            )

            print(
                "FILE SIZE:",
                os.path.getsize(filepath)
            )

            print(
                "FILEPATH:",
                filepath
            )

            print(
                "MEDIA TYPE:",
                media_type
            )

            if media_type == "photo":

                uploaded_media.append(
                    InputMediaPhoto(
                        media=filepath,
                        caption=filename
                    )
                )

            elif media_type == "video":

                uploaded_media.append(
                    InputMediaVideo(
                        media=filepath,
                        caption=filename
                    )
                )

            success += 1

        except Exception as e:

            import traceback

            traceback.print_exc()

            await message.reply(
                f"❌ {filename}\n\n"
                f"{type(e).__name__}: {e}"
            )

    if uploaded_media:

        await status.edit(
            "📤 Mengirim album..."
        )

        for i in range(
            0,
            len(uploaded_media),
            10
        ):

            chunk = uploaded_media[
                i:i + 10
            ]

            await message.reply_media_group(
                chunk
            )

    for file in all_files:

        try:

            if os.path.exists(file):
                os.remove(file)

        except:
            pass

    await status.edit(
        f"✅ Selesai\n"
        f"{success}/{len(urls)} berhasil"
    )


@app.on_message(filters.text)
async def discord_downloader(client, message):

    user_id = message.from_user.id

    # Sedang menunggu nama file
    if user_id in pending_rename:

        urls = pending_rename.pop(user_id)

        base_name = message.text.strip()

        await process_downloads(
            message,
            urls,
            base_name
        )

        return

    # Pesan berisi URL
    urls = [
        line.strip()
        for line in (message.text or "").splitlines()
        if line.strip()
    ]

    valid_urls = [
        url
        for url in urls
        if is_discord_attachment(url)
    ]

    if not valid_urls:
        return

    pending_rename[user_id] = valid_urls

    await message.reply(
        f"📦 Ditemukan {len(valid_urls)} file.\n\n"
        f"Kirim satu nama dasar."
    )


app.run()