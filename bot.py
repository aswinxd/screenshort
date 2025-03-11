from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
import fitz
import cv2
import os
import mimetypes

api_id = "12799559"
api_hash = "077254e69d93d08357f25bb5f4504580"
bot_token = "7128064825:AAEw4sbn1nrZeRXDhMURe0t65bCV-pM0Crs"

app = Client("screenshot_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def screenshot_document(file_path, max_pages=10):
    screenshots = []
    try:
        doc = fitz.open(file_path)
        for page_number in range(min(doc.page_count, max_pages)):
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            output_path = f"{file_path}_page_{page_number}.png"
            pix.save(output_path)
            screenshots.append(output_path)
        return screenshots
    except Exception as e:
        print(f"Failed to process document: {e}")
        return []

def screenshot_video(file_path, max_frames=10):
    screenshots = []
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(1, total_frames // max_frames)
        
        for frame_number in range(0, total_frames, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            success, frame = cap.read()
            if success:
                output_path = f"{file_path}_frame_{frame_number}.png"
                cv2.imwrite(output_path, frame)
                screenshots.append(output_path)
            if len(screenshots) >= max_frames:
                break
        
        cap.release()
        return screenshots
    except Exception as e:
        print(f"Failed to process video: {e}")
        return []


global user_preferences
user_preferences = {}


@app.on_message(filters.document | filters.video | filters.photo | filters.audio | filters.animation)
async def file_handler(client, message):
    file = message.document or message.video or message.photo or message.audio or message.animation
    reply_message = await message.reply_text("Downloading file...")
    file_path = await app.download_media(file)
    
    if not file_path:
        await message.reply_text("Failed to download the file.")
        return
    
    mime_type, _ = mimetypes.guess_type(file_path)
    print(f"File MIME type: {mime_type}")

    await reply_message.edit_text("How do you want the screenshots sent?")
    
    buttons = [
        [InlineKeyboardButton("📂 One by one", callback_data=f"one_by_one:{file_path}"),
         InlineKeyboardButton("📁 As album", callback_data=f"album:{file_path}")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text("Choose your preference:", reply_markup=reply_markup)

@app.on_callback_query(filters.regex(r"^(one_by_one|album):(.+)$"))
async def process_screenshots(client, callback_query):
    choice, file_path = callback_query.data.split(":", 1)
    await callback_query.message.edit_text("Processing file...")
    
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if mime_type and mime_type.startswith("application/"):
        screenshots = screenshot_document(file_path)
    elif mime_type and mime_type.startswith("video/"):
        screenshots = screenshot_video(file_path)
    else:
        await callback_query.message.edit_text(f"Unsupported file type: {mime_type}")
        os.remove(file_path)
        return

    os.remove(file_path)

    if not screenshots:
        await callback_query.message.edit_text("Failed to process the file.")
        return

    if choice == "one_by_one":
        await callback_query.message.edit_text("Uploading screenshots one by one...")
        for screenshot_path in screenshots:
            await app.send_photo(chat_id=callback_query.message.chat.id, photo=screenshot_path)
            os.remove(screenshot_path)
    else:
        await callback_query.message.edit_text("Uploading screenshots as an album...")
        media_group = [InputMediaPhoto(screenshot) for screenshot in screenshots]
        await app.send_media_group(chat_id=callback_query.message.chat.id, media=media_group)
        for screenshot_path in screenshots:
            os.remove(screenshot_path)

    await callback_query.message.delete()


if __name__ == "__main__":
    app.run()