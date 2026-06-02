import os
import uuid
import aiohttp
import asyncio

from pyrogram import Client, filters


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

    return "document"


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


@app.on_message(filters.text)
async def discord_downloader(client, message):

    urls = [
        line.strip()
        for line in (message.text or "").splitlines()
        if line.strip()
    ]

    urls = [
        url
        for url in urls
        if is_discord_attachment(url)
    ]

    if not urls:
        return

    status = await message.reply(
        f"⏳ Memproses {len(urls)} file..."
    )

    success = 0

    for index, url in enumerate(urls, start=1):

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

            await status.edit(
                f"📤 Upload {index}/{len(urls)}"
            )

            print("FILE EXISTS:", os.path.exists(filepath))
            print("FILE SIZE:", os.path.getsize(filepath))
            print("FILEPATH:", filepath)
            print("MEDIA TYPE:", media_type)

            if media_type == "photo":

                print("START PHOTO UPLOAD")

                await asyncio.wait_for(
                    message.reply_video(
                        video=filepath,
                        caption=filename,
                        supports_streaming=True
                    ),
                    timeout=60
                )

                print("PHOTO SENT")

            elif media_type == "video":

                print("START VIDEO UPLOAD")

                await message.reply_video(
                    video=filepath,
                    caption=filename,
                    supports_streaming=True
                )

                print("VIDEO SENT")

            else:

                await message.reply(
                    f"❌ Format tidak didukung\n{filename}"
                )

                continue

            success += 1

        except Exception as e:

            import traceback

            traceback.print_exc()

            await message.reply(
                f"❌ {filename}\n\n"
                f"{type(e).__name__}: {e}"
            )

        finally:

            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass

    await status.edit(
        f"✅ Selesai\n"
        f"{success}/{len(urls)} berhasil"
    )


app.run()