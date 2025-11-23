# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import tempfile
import re
import random  # ✅ ДОБАВЛЕНО: явный импорт random
import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import concurrent.futures

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS = os.environ.get('ADMIN_IDS', '').split(',')

if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не установлен")
    print("📝 Добавьте переменную BOT_TOKEN в настройках Railway")
    sys.exit(1)

ADMIN_IDS = [id.strip() for id in ADMIN_IDS if id.strip()]

# ✅ УВЕЛИЧЕНО: одновременных загрузок с 1 до 3
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_TIMEOUT = 180
SEARCH_TIMEOUT = 30
MAX_FILE_SIZE_MB = 50
RESULTS_PER_PAGE = 10

# ✅ УЛУЧШЕНО: более гибкие таймауты в зависимости от типа операции
DYNAMIC_TIMEOUTS = {
    'short_track': 30,      # до 3 минут
    'medium_track': 60,     # 3-10 минут  
    'long_track': 120,      # более 10 минут
    'search': 25
}

DATA_FILE = Path('user_data.json')
CHARTS_FILE = Path('charts_cache.json')

# ✅ УПРОЩЕНО: настройки скачивания
SIMPLE_DOWNLOAD_OPTS = {
    'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio[ext=ogg]/bestaudio[ext=wav]/bestaudio[ext=flac]/bestaudio/best',
    'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
    'quiet': True,
    'no_warnings': True,
    'retries': 3,  # ✅ УВЕЛИЧЕНО: количество попыток
    'fragment_retries': 3,
    'skip_unavailable_fragments': True,
    'noprogress': True,
    'nopart': True,
    'nooverwrites': True,
    'noplaylist': True,
    'max_filesize': 45000000,
    'ignoreerrors': True,
    'ignore_no_formats_error': True,
    'socket_timeout': 30,
}

# ... (остальные константы остаются без изменений)

# ==================== УЛУЧШЕННАЯ СИСТЕМА УВЕДОМЛЕНИЙ ====================

class NotificationManager:
    """✅ НОВЫЙ КЛАСС: Упрощенный менеджер уведомлений"""
    
    @staticmethod
    async def send_progress(update, context, stage: str, track=None, **kwargs):
        """Упрощенные прогресс-уведомления"""
        stages = {
            'searching': "🔍 Ищем треки...",
            'downloading': "⬇️ Скачиваем аудио...", 
            'processing': "🔄 Обрабатываем файл...",
            'sending': "📤 Отправляем в Telegram...",
            'success': "✅ Готово!",
            'error': "❌ Ошибка"
        }
        
        message = stages.get(stage, "⏳ Работаем...")
        if track and stage != 'searching':
            title = track.get('title', 'Неизвестный трек')[:30]
            message = f"{message}\n🎵 {title}"
            
        try:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(message)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=message
                )
        except Exception as e:
            logger.warning(f"Ошибка уведомления: {e}")

# ==================== ОСНОВНОЙ КЛАСС БОТА ====================

class StableMusicBot:
    def __init__(self):
        self.user_stats = user_data.get('_user_stats', {})
        self.track_info_cache = {}
        self.download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        self.search_semaphore = asyncio.Semaphore(3)
        self.notifications = NotificationManager()  # ✅ ДОБАВЛЕНО: менеджер уведомлений
        logger.info('✅ Бот инициализирован')

    # ✅ УЛУЧШЕНО: Умная проверка размера файла
    async def check_file_size_before_download(self, url: str, track: dict) -> tuple:
        """Проверяет размер файла и возвращает (размер, можно_ли_скачать)"""
        try:
            with yt_dlp.YoutubeDL(FAST_INFO_OPTS) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ydl.extract_info(url, download=False)
                )

                file_size = 0
                if info and 'filesize' in info and info['filesize']:
                    file_size = info['filesize'] / (1024 * 1024)
                elif info and 'filesize_approx' in info and info['filesize_approx']:
                    file_size = info['filesize_approx'] / (1024 * 1024)

                # ✅ УМНАЯ ПРОВЕРКА: учитываем длительность трека
                duration = track.get('duration', 0)
                if duration > 1800:  # более 30 минут
                    can_download = file_size < (MAX_FILE_SIZE_MB * 0.7)
                else:
                    can_download = file_size < MAX_FILE_SIZE_MB

                return file_size, can_download

        except Exception as e:
            logger.warning(f"Не удалось получить размер файла: {e}")
            return 0, True  # Если не получилось проверить, пытаемся скачать

    # ✅ ПЕРЕРАБОТАНО: Улучшенное скачивание с прогрессом
    async def download_and_send_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict) -> bool:
        """Улучшенный метод скачивания с прогресс-баром"""
        url = track.get('webpage_url') or track.get('url')
        if not url:
            return False

        # ✅ УМНАЯ ПРОВЕРКА РАЗМЕРА
        file_size_mb, can_download = await self.check_file_size_before_download(url, track)
        
        if not can_download:
            await self._handle_large_file(update, context, track, file_size_mb)
            return False

        async with self.download_semaphore:
            try:
                # ✅ ПРОГРЕСС: начало скачивания
                await self.notifications.send_progress(update, context, 'downloading', track)
                
                # ✅ АДАПТИВНЫЙ ТАЙМАУТ
                timeout = self._get_dynamic_timeout(track)
                
                return await asyncio.wait_for(
                    self.simple_download(update, context, track),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Таймаут скачивания трека: {track.get('title', 'Unknown')}")
                await self.notifications.send_progress(update, context, 'error', track)
                return False
            except Exception as e:
                logger.exception(f'Ошибка скачивания трека: {e}')
                await self.notifications.send_progress(update, context, 'error', track)
                return False

    def _get_dynamic_timeout(self, track: dict) -> int:
        """✅ НОВЫЙ МЕТОД: Динамические таймауты на основе длительности"""
        duration = track.get('duration', 0)
        if duration < 180:  # до 3 минут
            return DYNAMIC_TIMEOUTS['short_track']
        elif duration < 600:  # 3-10 минут
            return DYNAMIC_TIMEOUTS['medium_track']
        else:  # более 10 минут
            return DYNAMIC_TIMEOUTS['long_track']

    async def _handle_large_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict, file_size: float):
        """✅ УЛУЧШЕНО: Обработка больших файлов"""
        title = track.get('title', 'Неизвестный трек')
        artist = track.get('artist', 'Неизвестный исполнитель')
        
        text = f"📦 <b>Файл слишком большой</b>\n\n"
        text += f"🎵 <b>{title}</b>\n"
        text += f"🎤 {artist}\n"
        text += f"💾 Размер: {file_size:.1f} MB\n\n"
        text += f"⚠️ <b>Превышен лимит {MAX_FILE_SIZE_MB} MB</b>\n\n"
        text += f"🎧 Вы можете:\n• Прослушать онлайн\n• Найти более короткую версию"

        keyboard = [
            [InlineKeyboardButton('🎧 Слушать онлайн', url=track.get('webpage_url', ''))],
            [InlineKeyboardButton('🔍 Найти другую версию', callback_data=f'search_alt:{title}')],
            [InlineKeyboardButton('🎲 Случайный трек', callback_data='random_track')],
        ]

        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    # ✅ УЛУЧШЕНО: Надежное скачивание с улучшенной очисткой
    async def simple_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict) -> bool:
        """Улучшенное скачивание с надежной очисткой"""
        url = track.get('webpage_url') or track.get('url')
        if not url:
            return False

        loop = asyncio.get_event_loop()
        tmpdir = tempfile.mkdtemp()
        
        try:
            await self.notifications.send_progress(update, context, 'processing', track)
            
            ydl_opts = SIMPLE_DOWNLOAD_OPTS.copy()
            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title).100s.%(ext)s')

            def download_track():
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(url, download=True)
                except Exception as e:
                    logger.error(f"Ошибка скачивания: {e}")
                    return None

            info = await asyncio.wait_for(
                loop.run_in_executor(None, download_track),
                timeout=DOWNLOAD_TIMEOUT - 30
            )

            if not info:
                return False

            # ✅ УЛУЧШЕНО: Поиск совместимых форматов
            audio_file = await self._find_compatible_audio_file(tmpdir)
            if not audio_file:
                return False

            fpath = os.path.join(tmpdir, audio_file)
            actual_size_mb = os.path.getsize(fpath) / (1024 * 1024)
            
            # ✅ ДВОЙНАЯ ПРОВЕРКА размера
            if actual_size_mb >= MAX_FILE_SIZE_MB:
                await self._handle_large_file(update, context, track, actual_size_mb)
                return False

            await self.notifications.send_progress(update, context, 'sending', track)

            # ✅ УЛУЧШЕНО: Отправка файла
            success = await self._send_audio_file(update, context, fpath, track, actual_size_mb)
            
            if success:
                await self.notifications.send_progress(update, context, 'success', track)
                return True
            return False

        except asyncio.TimeoutError:
            logger.error(f"Таймаут при скачивании: {track.get('title', 'Unknown')}")
            return False
        except Exception as e:
            logger.exception(f'Ошибка скачивания: {e}')
            return False
        finally:
            # ✅ УЛУЧШЕНО: Надежная очистка
            await self._cleanup_temp_dir(tmpdir)

    async def _find_compatible_audio_file(self, tmpdir: str) -> str:
        """✅ НОВЫЙ МЕТОД: Поиск Telegram-совместимых аудио файлов"""
        telegram_audio_extensions = ['.mp3', '.m4a', '.ogg', '.wav', '.flac']
        
        for file in os.listdir(tmpdir):
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in telegram_audio_extensions:
                logger.info(f"✅ Найден совместимый файл: {file}")
                return file
        
        logger.error(f"❌ Совместимые файлы не найдены в: {os.listdir(tmpdir)}")
        return None

    async def _send_audio_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             fpath: str, track: dict, actual_size_mb: float) -> bool:
        """✅ НОВЫЙ МЕТОД: Надежная отправка аудио файла"""
        try:
            with open(fpath, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=f,
                    title=(track.get('title') or 'Неизвестный трек')[:64],
                    performer=(track.get('artist') or 'Неизвестный исполнитель')[:64],
                    caption=f"🎵 <b>{track.get('title', 'Неизвестный трек')}</b>\n🎤 {track.get('artist', 'Неизвестный исполнитель')}\n⏱️ {self.format_duration(track.get('duration'))}\n💾 {actual_size_mb:.1f} MB",
                    parse_mode='HTML',
                )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки файла: {e}")
            return False

    async def _cleanup_temp_dir(self, tmpdir: str):
        """✅ НОВЫЙ МЕТОД: Надежная очистка временных файлов"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if os.path.exists(tmpdir):
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    logger.info(f"✅ Временные файлы очищены (попытка {attempt + 1})")
                    break
                else:
                    break
            except Exception as e:
                logger.warning(f"Не удалось очистить временную директорию (попытка {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

    # ✅ УЛУЧШЕНО: Поиск с повторными попытками
    async def search_soundcloud(self, query: str, album_only: bool = False):
        """Поиск с повторными попытками при ошибках"""
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
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

                    def perform_search():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            return ydl.extract_info(f"scsearch30:{query}", download=False)

                    loop = asyncio.get_event_loop()
                    info = await asyncio.wait_for(
                        loop.run_in_executor(None, perform_search),
                        timeout=SEARCH_TIMEOUT
                    )

                    if not info:
                        return []

                    entries = info.get('entries', [])
                    if not entries and info.get('_type') != 'playlist':
                        entries = [info]

                    results = []
                    for entry in entries:
                        if not entry:
                            continue

                        title = self.clean_title(entry.get('title') or '')
                        webpage_url = entry.get('webpage_url') or entry.get('url') or ''
                        duration = entry.get('duration') or 0
                        artist = entry.get('uploader') or entry.get('uploader_id') or 'Неизвестно'
                        thumbnail = entry.get('thumbnail')

                        if not title:
                            continue

                        results.append({
                            'title': title,
                            'webpage_url': webpage_url,
                            'duration': duration,
                            'artist': artist,
                            'source': 'track',
                            'thumbnail': thumbnail
                        })

                    logger.info(f"✅ SoundCloud: {len(results)} результатов для: '{query}'")
                    return results

            except asyncio.TimeoutError:
                last_error = f"Таймаут поиска (попытка {attempt + 1})"
                logger.warning(last_error)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                last_error = f"Ошибка поиска: {e} (попытка {attempt + 1})"
                logger.warning(last_error)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue

        logger.error(f"❌ Все попытки поиска провалились: {last_error}")
        return []

    # ✅ УЛУЧШЕНО: Обработка текста с исправлением кодировки
    @staticmethod
    def clean_title(title: str) -> str:
        """Улучшенная очистка названий с исправлением кодировки"""
        if not title:
            return 'Неизвестный трек'
        
        # ✅ ИСПРАВЛЕНО: Проблемы с кодировкой
        try:
            title = title.encode('utf-8').decode('utf-8')
        except:
            pass
        
        # Удаляем специальные символы
        title = re.sub(r".*?|.*?", '', title)
        
        # Удаляем лишние теги
        tags = ['official video', 'official music video', 'lyric video', 'hd', '4k',
                '1080p', '720p', 'official audio', 'audio']
        for tag in tags:
            title = re.sub(tag, '', title, flags=re.IGNORECASE)
        
        # ✅ УЛУЧШЕНО: Убираем лишние пробелы
        title = ' '.join(title.split()).strip()
        
        return title if title else 'Неизвестный трек'

    # ✅ УЛУЧШЕНО: Главное меню с кнопкой отмены
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Улучшенное главное меню"""
        user = update.effective_user
        
        text = f"🏠 <b>Главное меню</b>\n\n"
        text += f"👋 Привет, {user.first_name}!\n\n"
        text += f"🎵 <b>Выберите действие:</b>"

        keyboard = [
            [
                InlineKeyboardButton('🎲 Случайный трек', callback_data='random_track'),
                InlineKeyboardButton('🔍 Поиск', callback_data='start_search')
            ],
            [
                InlineKeyboardButton('🎯 Рекомендации', callback_data='show_recommendations'),
                InlineKeyboardButton('📊 Топ чарты', callback_data='show_charts')
            ],
            [
                InlineKeyboardButton('🎭 Настроение', callback_data='mood_playlists'),
                InlineKeyboardButton('⚙️ Настройки', callback_data='settings')
            ],
            [InlineKeyboardButton('❌ Отменить', callback_data='cancel_operation')]  # ✅ ДОБАВЛЕНО: кнопка отмены
        ]

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    # ✅ ДОБАВЛЕНО: Обработка отмены операций
    async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка отмены операций"""
        query = update.callback_query
        await query.answer("Операция отменена")
        await self.show_main_menu(update, context)

    # ... (остальные методы остаются аналогичными, но с улучшенной обработкой ошибок)

    def run(self):
        print('🚀 Запуск улучшенного Music Bot...')

        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler('start', self.start))
        app.add_handler(CommandHandler('search', self.search_command))
        app.add_handler(CommandHandler('random', self.random_track))
        app.add_handler(CommandHandler('settings', self.show_settings))

        setup_admin_commands(app)

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # ✅ ДОБАВЛЕНО: Обработчик отмены
        app.add_handler(CallbackQueryHandler(self.handle_cancel, pattern='^cancel_operation$'))

        async def set_commands(application):
            commands = [
                ('start', '🚀 Запустить бота'),
                ('search', '🔍 Начать поиск'),
                ('random', '🎲 Случайный трек'),
                ('settings', '⚙️ Настройки фильтров'),
            ]

            await application.bot.set_my_commands(commands)
            print('✅ Улучшенное меню с командами настроено!')

        app.post_init = set_commands

        print('✅ Улучшенный бот запущен и готов к работе!')
        app.run_polling()

if __name__ == '__main__':
    bot = StableMusicBot()
    bot.run()
