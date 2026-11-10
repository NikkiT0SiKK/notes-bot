import os
import speech_recognition as sr
import imageio_ffmpeg
from pydub import AudioSegment
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.types import Message

from db.queries import add_note
from utils.tags import extract_tags

router = Router()
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

@router.message(StateFilter(None), F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    processing_msg = await message.answer("🎙 Слушаю и распознаю... Это может занять пару секунд.")
    
    ogg_path = f"temp_{message.from_user.id}.ogg"
    wav_path = f"temp_{message.from_user.id}.wav"
    
    try:
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, ogg_path)
        
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            
        clean_text, tags = extract_tags(text)
        
        if not clean_text:
            await processing_msg.edit_text("❌ Не удалось распознать текст (возможно, только теги).")
            return

        note_id = await add_note(message.from_user.id, clean_text, tags)
        tag_str = (" ".join(f"#{t}" for t in tags)) if tags else "—"
        
        await processing_msg.edit_text(
            f"✅ <b>Голосовая заметка #{note_id} сохранена!</b>\n\n"
            f"📝 <i>Распознанный текст:</i> {clean_text}\n"
            f"🏷 Теги: {tag_str}",
            parse_mode="HTML"
        )

    except sr.UnknownValueError:
        await processing_msg.edit_text("❌ Извини, я не разобрал(а) слова. Попробуй говорить четче.")
    except sr.RequestError as e:
        await processing_msg.edit_text(f"❌ Ошибка сервиса распознавания: {e}")
    except Exception as e:
        await processing_msg.edit_text(f"❌ Произошла ошибка: {e}")
    finally:
        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)