# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import tempfile
import re
import random
import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не установлен")
    sys.exit(1)

print("🔧 Универсальный Music Bot запускается...")

# Конфигурация через переменные окружения
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', 50))
DOWNLOAD_TIMEOUT = int(os.environ.get('DOWNLOAD_TIMEOUT', 180))
SEARCH_TIMEOUT = int(os.environ.get('SEARCH_TIMEOUT', 30))
REQUESTS_PER_MINUTE = int(os.environ.get('REQUESTS_PER_MINUTE', 10))

# Оптимизированные настройки для SoundCloud
SOUNDCLOUD_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
    'quiet': True,
    'no_warnings': True,
    'retries': 3,
    'fragment_retries': 3,
    'skip_unavailable_fragments': True,
    'noprogress': True,
    'nopart': True,
    'noplaylist': True,
    'max_filesize': MAX_FILE_SIZE_MB * 1024 * 1024,
    'ignoreerrors': True,
    'socket_timeout': 30,
    'extractaudio': True,
    'audioformat': 'mp3',
}

# Список для случайных треков
RANDOM_SEARCHES = [
    'lo fi beats', 'chillhop', 'deep house', 'synthwave', 'indie rock',
    'electronic music', 'jazz lounge', 'ambient', 'study music',
    'focus music', 'relaxing music', 'instrumental', 'acoustic',
    'piano covers', 'guitar music', 'vocal trance', 'dubstep',
    'tropical house', 'future bass', 'retro wave', 'city pop',
    'latin music', 'reggaeton', 'k-pop', 'j-pop', 'classical piano',
    'orchestral', 'film scores', 'video game music'
]

# ==================== IMPORT TELEGRAM & YT-DLP ====================
try:
    from telegram import Update
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
        filters, ContextTypes
    )
    import yt_dlp
    print("✅ Все зависимости загружены")
except ImportError as exc:
    print(f"❌ Ошибка импорта: {exc}")
    os.system("pip install python-telegram-bot yt-dlp")
    try:
        from telegram import Update
        from telegram.ext import (
            Application, CommandHandler, MessageHandler, CallbackQueryHandler,
            filters, ContextTypes
        )
        import yt_dlp
        print("✅ Зависимости успешно установлены")
    except ImportError as exc2:
        print(f"❌ Ошибка импорта после установки: {exc2}")
        sys.exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== RATE LIMITER ====================
class RateLimiter:
    def __init__(self):
        self.user_requests = defaultdict(list)
    
    def is_limited(self, user_id: int, limit: int = REQUESTS_PER_MINUTE, period: int = 60):
        now = datetime.now()
        user_requests = self.user_requests[user_id]
        user_requests = [req for req in user_requests if now - req < timedelta(seconds=period)]
        self.user_requests[user_id] = user_requests
        
        if len(user_requests) >= limit:
            return True
            
        user_requests.append(now)
        return False

# ==================== UNIVERSAL MUSIC BOT ====================
class UniversalMusicBot:
    def __init__(self):
        self.download_semaphore = asyncio.Semaphore(1)
        self.search_semaphore = asyncio.Semaphore(3)
        self.rate_limiter = RateLimiter()
        logger.info('✅ Универсальный бот инициализирован')

    @staticmethod
    def clean_title(title: str) -> str:
        if not title:
            return 'Неизвестный трек'
        title = re.sub(r".*?|.*?", '', title)
        tags = ['official video', 'official music video', 'lyric video', 'hd', '4k',
                '1080p', '720p', 'official audio', 'audio']
        for tag in tags:
            title = re.sub(tag, '', title, flags=re.IGNORECASE)
        return ' '.join(title.split()).strip()

    @staticmethod
    def format_duration(seconds) -> str:
        try:
            sec = int(float(seconds))
            minutes = sec // 60
            sec = sec % 60
            return f"{minutes:02d}:{sec:02d}"
        except Exception:
            return '00:00'

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Проверяет валидность URL"""
        if not url:
            return False
        return bool(re.match(r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', url))

    # ==================== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ ====================

    async def handle_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает ВСЕ сообщения из любых чатов"""
        try:
            if not update.message or not update.message.text:
                return
                
            message_text = update.message.text.strip().lower()
            chat_id = update.effective_chat.id
            user = update.effective_user
            
            # Rate limiting
            if self.rate_limiter.is_limited(user.id):
                await update.message.reply_text(
                    f"⏳ {user.first_name}, слишком много запросов!\n"
                    f"Подожди 1 минуту перед следующим запросом."
                )
                return

            # Реагируем ТОЛЬКО на команды "найди" и "рандом"
            if message_text.startswith('найди'):
                await self.handle_find_command(update, context, message_text)
            
            elif message_text.startswith('рандом'):
                await self.handle_random_command(update, context)
            
            # Игнорируем все остальные сообщения
            else:
                return
                
        except Exception as e:
            logger.exception(f'Ошибка обработки сообщения: {e}')

    async def handle_find_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Обрабатывает поиск трека по запросу"""
        status_msg = None
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Извлекаем запрос после "найди"
            query = self.extract_search_query(message_text)
            
            if not query:
                await update.message.reply_text(
                    f"❌ {user.first_name}, не указано что искать\n"
                    f"💡 Напиши: найди [название трека или исполнителя]"
                )
                return

            # Отправляем статус (единственное сообщение)
            status_msg = await update.message.reply_text(
                f"🔍 <b>{user.first_name} ищет:</b> <code>{query}</code>\n"
                f"⏳ Ищу лучший трек...",
                parse_mode='HTML'
            )

            # Ищем трек
            track = await self.find_track(query)
            
            if not track:
                await status_msg.edit_text(
                    f"❌ <b>Не найдено по запросу:</b> <code>{query}</code>\n"
                    f"💡 Попробуй другой запрос, {user.first_name}",
                    parse_mode='HTML'
                )
                return

            # Скачиваем трек
            file_path = await self.download_track(track.get('webpage_url'))
            if not file_path:
                await status_msg.edit_text(
                    f"❌ <b>Не удалось скачать трек</b>\n"
                    f"🎵 {track.get('title', 'Неизвестный трек')}",
                    parse_mode='HTML'
                )
                return

            # Отправляем аудио и редактируем статус
            with open(file_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=(track.get('title') or 'Неизвестный трек')[:64],
                    performer=(track.get('artist') or 'Неизвестный исполнитель')[:64],
                    caption=f"🎵 <b>{track.get('title', 'Неизвестный трек')}</b>\n"
                           f"🎤 {track.get('artist', 'Неизвестный исполнитель')}\n"
                           f"⏱️ {self.format_duration(track.get('duration'))}\n"
                           f"👤 Запросил: {user.first_name}\n"
                           f"🔍 По запросу: <code>{query}</code>",
                    parse_mode='HTML',
                )

            # Удаляем временный файл
            try:
                os.remove(file_path)
            except:
                pass

            # Удаляем статус-сообщение (оставляем только аудио)
            try:
                await status_msg.delete()
            except:
                # Если нельзя удалить (нет прав), просто оставляем как есть
                await status_msg.edit_text(
                    f"✅ <b>{user.first_name} нашел:</b>\n"
                    f"🎵 {track.get('title', 'Неизвестный трек')}\n"
                    f"🔍 По запросу: <code>{query}</code>",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.exception(f'Ошибка при поиске: {e}')
            if status_msg:
                await status_msg.edit_text(
                    f"❌ <b>Ошибка при поиске</b>\n"
                    f"💡 Попробуй еще раз, {user.first_name}",
                    parse_mode='HTML'
                )

    async def handle_random_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает запрос на случайный трек"""
        status_msg = None
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Отправляем статус (единственное сообщение)
            status_msg = await update.message.reply_text(
                f"🎲 <b>{user.first_name} ищет случайный трек...</b>\n"
                "⏳ Ищу интересную музыку...",
                parse_mode='HTML'
            )

            # Случайный запрос
            random_query = random.choice(RANDOM_SEARCHES)
            
            # Ищем трек
            track = await self.find_track(random_query)
            
            if not track:
                await status_msg.edit_text(
                    f"❌ <b>Не удалось найти случайный трек</b>\n"
                    f"💡 Попробуй еще раз, {user.first_name}",
                    parse_mode='HTML'
                )
                return

            # Скачиваем трек
            file_path = await self.download_track(track.get('webpage_url'))
            if not file_path:
                await status_msg.edit_text(
                    f"❌ <b>Не удалось скачать случайный трек</b>\n"
                    f"🎵 {track.get('title', 'Неизвестный трек')}",
                    parse_mode='HTML'
                )
                return

            # Отправляем аудио и редактируем статус
            with open(file_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=(track.get('title') or 'Неизвестный трек')[:64],
                    performer=(track.get('artist') or 'Неизвестный исполнитель')[:64],
                    caption=f"🎵 <b>{track.get('title', 'Неизвестный трек')}</b>\n"
                           f"🎤 {track.get('artist', 'Неизвестный исполнитель')}\n"
                           f"⏱️ {self.format_duration(track.get('duration'))}\n"
                           f"👤 Случайный трек для: {user.first_name}",
                    parse_mode='HTML',
                )

            # Удаляем временный файл
            try:
                os.remove(file_path)
            except:
                pass

            # Удаляем статус-сообщение (оставляем только аудио)
            try:
                await status_msg.delete()
            except:
                # Если нельзя удалить (нет прав), просто оставляем как есть
                await status_msg.edit_text(
                    f"✅ <b>Случайный трек для {user.first_name}:</b>\n"
                    f"🎵 {track.get('title', 'Неизвестный трек')}",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.exception(f'Ошибка при поиске случайного трека: {e}')
            if status_msg:
                await status_msg.edit_text(
                    f"❌ <b>Ошибка при поиске</b>\n"
                    f"💡 Попробуй еще раз, {user.first_name}",
                    parse_mode='HTML'
                )

    def extract_search_query(self, message_text: str) -> str:
        """Извлекает поисковый запрос из сообщения"""
        query = message_text.replace('найди', '').strip()
        stop_words = ['пожалуйста', 'мне', 'трек', 'песню', 'музыку', 'плз', 'plz']
        for word in stop_words:
            query = query.replace(word, '')
        return query.strip()

    # ==================== ПОИСК ТРЕКОВ ====================

    async def find_track(self, query: str):
        """Находит трек по запросу с улучшенной релевантностью"""
        async with self.search_semaphore:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'ignoreerrors': True,
                'noplaylist': True,
                'socket_timeout': 15,
            }

            try:
                print(f"🔍 Улучшенный поиск: {query}")
                
                def perform_search():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(f"scsearch15:{query}", download=False)

                loop = asyncio.get_event_loop()
                info = await asyncio.wait_for(
                    loop.run_in_executor(None, perform_search),
                    timeout=SEARCH_TIMEOUT
                )

                if not info:
                    return None

                entries = info.get('entries', [])
                if not entries and info.get('_type') != 'playlist':
                    entries = [info]

                print(f"✅ Найдено {len(entries)} результатов")

                # Фильтрация и сортировка для лучшей релевантности
                filtered_entries = []
                for entry in entries:
                    if not entry:
                        continue

                    # Фильтруем по длительности (минимум 60 секунд)
                    duration = entry.get('duration') or 0
                    if duration < 60:
                        continue

                    title = self.clean_title(entry.get('title') or '')
                    if not title:
                        continue

                    # Приоритет для "official" треков
                    priority = 0
                    if 'official' in title.lower():
                        priority = 2
                    elif 'original' in title.lower():
                        priority = 1

                    filtered_entries.append({
                        'entry': entry,
                        'priority': priority,
                        'duration': duration,
                        'title': title
                    })

                # Сортируем по приоритету и длительности
                filtered_entries.sort(key=lambda x: (-x['priority'], -x['duration']))

                # Берем лучший результат
                if filtered_entries:
                    best_entry = filtered_entries[0]['entry']
                    title = self.clean_title(best_entry.get('title') or '')
                    webpage_url = best_entry.get('webpage_url') or best_entry.get('url') or ''
                    duration = best_entry.get('duration') or 0
                    artist = best_entry.get('uploader') or best_entry.get('uploader_id') or 'Неизвестно'

                    print(f"🎵 Выбран лучший трек: {title} - {artist}")
                    return {
                        'title': title,
                        'webpage_url': webpage_url,
                        'duration': duration,
                        'artist': artist
                    }

                return None

            except asyncio.TimeoutError:
                logger.warning(f"Таймаут поиска: {query}")
                return None
            except Exception as e:
                logger.warning(f'Ошибка поиска: {e}')
                return None

    # ==================== СКАЧИВАНИЕ ====================

    async def download_track(self, url: str) -> str:
        """Скачивает трек и возвращает путь к файлу"""
        if not self.is_valid_url(url):
            return None

        loop = asyncio.get_event_loop()
        tmpdir = tempfile.mkdtemp()
        
        try:
            ydl_opts = SOUNDCLOUD_OPTS.copy()
            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title).100s.%(ext)s')

            def download_track():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)

            info = await asyncio.wait_for(
                loop.run_in_executor(None, download_track),
                timeout=DOWNLOAD_TIMEOUT - 30
            )

            if not info:
                return None

            # Ищем Telegram-совместимые файлы
            telegram_audio_extensions = ['.mp3', '.m4a', '.ogg', '.wav', '.flac']
            
            for file in os.listdir(tmpdir):
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in telegram_audio_extensions:
                    file_path = os.path.join(tmpdir, file)
                    
                    # Проверяем размер файла
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if file_size_mb >= MAX_FILE_SIZE_MB:
                        continue
                    
                    return file_path

            return None

        except Exception as e:
            logger.exception(f'Ошибка скачивания: {e}')
            return None
        finally:
            # Очищаем временную директорию
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass

    # ==================== КОМАНДЫ ====================

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        await update.message.reply_text(
            f"🎵 <b>Универсальный музыкальный бот</b>\n\n"
            f"👋 Привет, {user.first_name}!\n\n"
            f"📢 <b>Доступные команды:</b>\n"
            f"• <code>найди [запрос]</code> - найти трек\n"
            f"• <code>рандом</code> - случайный трек\n\n"
            f"🚀 <b>Начни поиск музыки!</b>",
            parse_mode='HTML'
        )

    # ==================== ЗАПУСК БОТА ====================

    def run(self):
        print('🚀 Запуск улучшенного Music Bot...')
        print('💡 Бот работает ВО ВСЕХ чатах (ЛС и группы)')
        print('🎯 Реагирует на: "найди" и "рандом"')
        print('🛡️  Rate limiting: {} запросов/минуту'.format(REQUESTS_PER_MINUTE))
        print('🔍 Улучшенный поиск: 15 результатов + фильтрация')

        app = Application.builder().token(BOT_TOKEN).build()

        # Обработчик ВСЕХ текстовых сообщений ВО ВСЕХ чатах
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_all_messages
        ))

        # Команды
        app.add_handler(CommandHandler('start', self.start_command))
        app.add_handler(CommandHandler('help', self.start_command))

        print('✅ Бот запущен!')
        print('📝 Тестируй в любом чате:')
        print('   • "найди coldplay"')
        print('   • "рандом"')
        
        app.run_polling()

if __name__ == '__main__':
    bot = UniversalMusicBot()
    bot.run()
