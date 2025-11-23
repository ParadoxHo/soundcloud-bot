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
import concurrent.futures

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS = os.environ.get('ADMIN_IDS', '').split(',')

if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not set")
    print("📝 Add BOT_TOKEN variable in Railway settings")
    sys.exit(1)

ADMIN_IDS = [id.strip() for id in ADMIN_IDS if id.strip()]

if not ADMIN_IDS:
    print("⚠️  Warning: ADMIN_IDS not set. Admin commands disabled.")
else:
    print(f"✅ Admins configured: {ADMIN_IDS}")

RESULTS_PER_PAGE = 10
DATA_FILE = Path('user_data.json')
CHARTS_FILE = Path('charts_cache.json')
MAX_FILE_SIZE_MB = 50

MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_TIMEOUT = 180
SEARCH_TIMEOUT = 30

DYNAMIC_TIMEOUTS = {
    'short_track': 30,
    'medium_track': 60, 
    'long_track': 120,
    'search': 25
}

SIMPLE_DOWNLOAD_OPTS = {
    'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio[ext=ogg]/bestaudio[ext=wav]/bestaudio[ext=flac]/bestaudio/best',
    'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
    'quiet': True,
    'no_warnings': True,
    'retries': 3,
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

FAST_INFO_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'simulate': True,
    'format': 'bestaudio/best',
    'skip_download': True,
    'noplaylist': True,
    'extract_flat': True,
    'socket_timeout': 15,
    'ignoreerrors': True,
}

DURATION_FILTERS = {
    'no_filter': 'no_filter',
    'up_to_5min': 'up_to_5min', 
    'up_to_10min': 'up_to_10min',
    'up_to_20min': 'up_to_20min',
}

# Playlists structure
SMART_PLAYLISTS = {
    'morning': {
        'name': 'morning',
        'queries': ['morning music', 'wake up music', 'positive morning', 'upbeat acoustic', 'fresh start'],
        'description': 'morning_description'
    },
    'romance': {
        'name': 'romance',
        'queries': ['romantic music', 'love songs', 'slow dance', 'intimate music', 'couple music'],
        'description': 'romance_description'
    },
    'nostalgia': {
        'name': 'nostalgia',
        'queries': ['80s hits', '90s music', 'retro classics', 'oldies but goldies', 'vintage hits'],
        'description': 'nostalgia_description'
    },
    'work_focus': {
        'name': 'work_focus',
        'queries': ['lo fi study', 'focus music', 'ambient study', 'coding music', 'deep work'],
        'description': 'work_focus_description'
    },
    'workout': {
        'name': 'workout',
        'queries': ['workout music', 'gym motivation', 'edm workout', 'hip hop workout', 'energy music'],
        'description': 'workout_description'
    },
    'relax': {
        'name': 'relax',
        'queries': ['chillhop', 'ambient relax', 'piano relax', 'meditation music', 'calm music'],
        'description': 'relax_description'
    },
    'party': {
        'name': 'party', 
        'queries': ['party hits', 'dance music', 'club mix', 'top hits', 'festival music'],
        'description': 'party_description'
    },
    'road_trip': {
        'name': 'road_trip',
        'queries': ['road trip', 'driving music', 'travel mix', 'adventure music', 'scenic drive'],
        'description': 'road_trip_description'
    },
    'sleep': {
        'name': 'sleep',
        'queries': ['sleep music', 'deep sleep', 'calming sleep', 'piano sleep', 'ambient sleep'],
        'description': 'sleep_description'
    },
    'rainy_day': {
        'name': 'rainy_day',
        'queries': ['rainy day music', 'cozy jazz', 'rain sounds lofi', 'indie rainy day', 'chill rainy'],
        'description': 'rainy_day_description'
    },
    'electronic': {
        'name': 'electronic',
        'queries': ['electronic music', 'edm', 'techno', 'house music', 'trance', 'dubstep', 'drum and bass', 'synthwave'],
        'description': 'electronic_description'
    }
}

RANDOM_SEARCHES = [
    'lo fi beats', 'chillhop', 'deep house', 'synthwave', 'indie rock',
    'electronic music', 'jazz lounge', 'ambient', 'study music',
    'focus music', 'relaxing music', 'instrumental', 'acoustic',
    'piano covers', 'guitar music', 'vocal trance', 'dubstep',
    'tropical house', 'future bass', 'retro wave', 'city pop',
    'latin music', 'reggeaton', 'k-pop', 'j-pop', 'classical piano',
    'orchestral', 'film scores', 'video game music', 'retro gaming',
    'chill beats', 'lounge music', 'smooth jazz', 'progressive house',
    'techno music', 'trance music', 'hip hop instrumental', 'rap beats'
]

POPULAR_SEARCHES = [
    'the weeknd', 'taylor swift', 'bad bunny', 'ariana grande', 'drake',
    'billie eilish', 'ed sheeran', 'dualipa', 'post malone', 'kanye west', 
    'coldplay', 'maroon 5', 'bruno mars', 'adele', 'justin bieber',
    'kendrick lamar', 'travis scott', 'doja cat', 'olivia rodrigo', 'harry styles'
]

# ==================== IMPORT TELEGRAM & YT-DLP ====================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, 
        ContextTypes
    )
    import yt_dlp
    print("✅ All dependencies loaded")
except ImportError as exc:
    print(f"❌ Import error: {exc}")
    print("📦 Installing dependencies...")
    os.system("pip install python-telegram-bot yt-dlp")
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, 
            ContextTypes
        )
        import yt_dlp
        print("✅ Dependencies successfully installed")
    except ImportError as exc2:
        print(f"❌ Import error after installation: {exc2}")
        sys.exit(1)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ==================== LANGUAGES SYSTEM ====================

LANGUAGES = {
    'en': '🇬🇧 English',
    'uk': '🇺🇦 Українська', 
    'ru': '🇷🇺 Русский'
}

TEXTS = {
    'en': {
        # Main menu
        'main_menu': '🏠 Main Menu',
        'welcome': 'Hello, {name}!',
        'choose_action': '🎵 Choose action:',
        'random_track': '🎲 Random Track',
        'search_music': '🔍 Search Music',
        'top_charts': '📊 Top Charts',
        'mood': '🎭 Mood',
        'recommendations': '🎯 Recommendations',
        'settings': '⚙️ Settings',
        
        # Settings
        'settings_title': '⚙️ Settings',
        'current_language': 'Language: {language}',
        'notifications': 'Notifications: {status}',
        'duration_filter': 'Duration filter: {filter}',
        'music_only': 'Music only: {status}',
        'change_language': '🌐 Change language',
        'duration_menu': '⏱️ Duration filter',
        'toggle_music': '🎵 Music only',
        'back_to_settings': '🔙 Back to settings',
        'back_to_main': '🔙 Back to main menu',
        
        # Duration filters
        'duration_title': '⏱️ Duration Filter',
        'choose_duration': 'Choose duration filter:',
        'no_filter': 'No filter',
        'up_to_5min': 'Up to 5 minutes',
        'up_to_10min': 'Up to 10 minutes',
        'up_to_20min': 'Up to 20 minutes',
        
        # Search
        'search_title': '🔍 Search Music',
        'enter_query': 'Enter song name or artist:',
        'search_results': '🔍 Results for query:',
        'page': 'Page {current} of {total}',
        'found': 'Found: {count} results',
        'new_search': '🔍 New search',
        
        # Statuses
        'on': '✅ ON',
        'off': '❌ OFF',
        
        # Notifications
        'language_changed': '✅ Language changed!',
        'searching': '🔍 Searching tracks...',
        'downloading': '⬇️ Downloading audio...',
        'processing': '🔄 Processing file...',
        'sending': '📤 Sending to Telegram...',
        'success': '✅ Ready!',
        'error': '❌ Error',
        
        # Charts and recommendations
        'charts_title': '📊 Top Charts',
        'recommendations_title': '🎯 Your Recommendations',
        'mood_title': '🎭 Music by Mood',
        'loading_charts': '📊 Loading popular tracks...',
        'loading_recommendations': '🎯 Loading your recommendations...',
        
        # Navigation buttons
        'back': '⬅️ Back',
        'next': 'Next ➡️',
        'refresh': '🔄 Refresh',
        'current_page': '{current}/{total}',
    },
    
    'uk': {
        # Main menu
        'main_menu': '🏠 Головне меню',
        'welcome': 'Привіт, {name}!',
        'choose_action': '🎵 Оберіть дію:',
        'random_track': '🎲 Випадковий трек',
        'search_music': '🔍 Пошук музики',
        'top_charts': '📊 Топ чарти',
        'mood': '🎭 Настрій',
        'recommendations': '🎯 Рекомендації',
        'settings': '⚙️ Налаштування',
        
        # Settings
        'settings_title': '⚙️ Налаштування',
        'current_language': 'Мова: {language}',
        'notifications': 'Сповіщення: {status}',
        'duration_filter': 'Фільтр за тривалістю: {filter}',
        'music_only': 'Тільки музика: {status}',
        'change_language': '🌐 Змінити мову',
        'duration_menu': '⏱️ Фільтр за тривалістю',
        'toggle_music': '🎵 Тільки музика',
        'back_to_settings': '🔙 Назад до налаштувань',
        'back_to_main': '🔙 В головне меню',
        
        # Duration filters
        'duration_title': '⏱️ Фільтр за тривалістю',
        'choose_duration': 'Оберіть фільтр за тривалістю:',
        'no_filter': 'Без фільтру',
        'up_to_5min': 'До 5 хвилин',
        'up_to_10min': 'До 10 хвилин',
        'up_to_20min': 'До 20 хвилин',
        
        # Search
        'search_title': '🔍 Пошук музики',
        'enter_query': 'Введіть назву пісні або виконавця:',
        'search_results': '🔍 Результати за запитом:',
        'page': 'Сторінка {current} з {total}',
        'found': 'Знайдено: {count} результатів',
        'new_search': '🔍 Новий пошук',
        
        # Statuses
        'on': '✅ Вкл',
        'off': '❌ Викл',
        
        # Notifications
        'language_changed': '✅ Мову змінено!',
        'searching': '🔍 Шукаємо треки...',
        'downloading': '⬇️ Завантажуємо аудіо...',
        'processing': '🔄 Обробляємо файл...',
        'sending': '📤 Надсилаємо в Telegram...',
        'success': '✅ Готово!',
        'error': '❌ Помилка',
        
        # Charts and recommendations
        'charts_title': '📊 Топ чарти',
        'recommendations_title': '🎯 Ваші рекомендації',
        'mood_title': '🎭 Музика за настроєм',
        'loading_charts': '📊 Завантажую популярні треки...',
        'loading_recommendations': '🎯 Завантажую ваші рекомендації...',
        
        # Navigation buttons
        'back': '⬅️ Назад',
        'next': 'Вперед ➡️',
        'refresh': '🔄 Оновити',
        'current_page': '{current}/{total}',
    },
    
    'ru': {
        # Main menu
        'main_menu': '🏠 Главное меню',
        'welcome': 'Привет, {name}!',
        'choose_action': '🎵 Выберите действие:',
        'random_track': '🎲 Случайный трек',
        'search_music': '🔍 Поиск музыки',
        'top_charts': '📊 Топ чарты',
        'mood': '🎭 Настроение',
        'recommendations': '🎯 Рекомендации',
        'settings': '⚙️ Настройки',
        
        # Settings
        'settings_title': '⚙️ Настройки',
        'current_language': 'Язык: {language}',
        'notifications': 'Уведомления: {status}',
        'duration_filter': 'Фильтр по длительности: {filter}',
        'music_only': 'Только музыка: {status}',
        'change_language': '🌐 Сменить язык',
        'duration_menu': '⏱️ Фильтр по длительности',
        'toggle_music': '🎵 Только музыка',
        'back_to_settings': '🔙 Назад к настройкам',
        'back_to_main': '🔙 В главное меню',
        
        # Duration filters
        'duration_title': '⏱️ Фильтр по длительности',
        'choose_duration': 'Выберите фильтр по длительности:',
        'no_filter': 'Без фильтра',
        'up_to_5min': 'До 5 минут',
        'up_to_10min': 'До 10 минут',
        'up_to_20min': 'До 20 минут',
        
        # Search
        'search_title': '🔍 Поиск музыки',
        'enter_query': 'Введите название песни или исполнителя:',
        'search_results': '🔍 Результаты по запросу:',
        'page': 'Страница {current} из {total}',
        'found': 'Найдено: {count} результатов',
        'new_search': '🔍 Новый поиск',
        
        # Statuses
        'on': '✅ ВКЛ',
        'off': '❌ ВЫКЛ',
        
        # Notifications
        'language_changed': '✅ Язык изменен!',
        'searching': '🔍 Ищем треки...',
        'downloading': '⬇️ Скачиваем аудио...',
        'processing': '🔄 Обрабатываем файл...',
        'sending': '📤 Отправляем в Telegram...',
        'success': '✅ Готово!',
        'error': '❌ Ошибка',
        
        # Charts and recommendations
        'charts_title': '📊 Топ чарты',
        'recommendations_title': '🎯 Ваши рекомендации',
        'mood_title': '🎭 Музыка по настроению',
        'loading_charts': '📊 Загружаю популярные треки...',
        'loading_recommendations': '🎯 Загружаю ваши рекомендации...',
        
        # Navigation buttons
        'back': '⬅️ Назад',
        'next': 'Вперед ➡️',
        'refresh': '🔄 Обновить',
        'current_page': '{current}/{total}',
    }
}

def get_text(user_id: str, text_key: str, **kwargs) -> str:
    """Get text in user's language"""
    user_entry = user_data.get(str(user_id), {})
    lang = user_entry.get('preferences', {}).get('language', 'en')  # English by default
    
    text = TEXTS.get(lang, {}).get(text_key, TEXTS.get('en', {}).get(text_key, text_key))
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Text formatting error {text_key}: {e}")
    
    return text

def get_duration_filter_text(user_id: str, filter_key: str) -> str:
    """Get duration filter text"""
    duration_texts = {
        'no_filter': get_text(user_id, 'no_filter'),
        'up_to_5min': get_text(user_id, 'up_to_5min'),
        'up_to_10min': get_text(user_id, 'up_to_10min'),
        'up_to_20min': get_text(user_id, 'up_to_20min')
    }
    return duration_texts.get(filter_key, get_text(user_id, 'no_filter'))

def get_playlist_name(user_id: str, playlist_id: str) -> str:
    """Get playlist name"""
    playlist = SMART_PLAYLISTS.get(playlist_id, {})
    return get_text(user_id, playlist.get('name', playlist_id))

def get_playlist_description(user_id: str, playlist_id: str) -> str:
    """Get playlist description"""
    playlist = SMART_PLAYLISTS.get(playlist_id, {})
    return get_text(user_id, playlist.get('description', ''))

# ==================== USER DATA STORAGE ====================
user_data = {}
charts_cache = {}

def load_data():
    global user_data, charts_cache
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load {DATA_FILE}: {e}")
            user_data = {}
    else:
        user_data = {}

    if CHARTS_FILE.exists():
        try:
            with open(CHARTS_FILE, 'r', encoding='utf-8') as f:
                charts_cache = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load {CHARTS_FILE}: {e}")
            charts_cache = {}
    else:
        charts_cache = {}

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def save_charts_cache():
    try:
        with open(CHARTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(charts_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving charts cache: {e}")

load_data()

# ==================== ADMIN FUNCTIONS ====================

def is_admin(user_id: str) -> bool:
    return str(user_id) in ADMIN_IDS

async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("❌ Command not found")
        return False
    return True

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    user_count = len([k for k in user_data.keys() if not k.startswith('_')])
    total_downloads = sum(stats.get('downloads', 0) for stats in user_data.get('_user_stats', {}).values())
    total_searches = sum(stats.get('searches', 0) for stats in user_data.get('_user_stats', {}).values())

    text = f"""📊 <b>Admin Statistics</b>

👥 Users: {user_count}
📥 Total downloads: {total_downloads}
🔍 Total searches: {total_searches}
💾 user_data size: {len(str(user_data))} chars
📈 Charts cache: {len(charts_cache.get('data', {}))} requests
🔧 Admins: {len(ADMIN_IDS)}"""

    await update.message.reply_text(text, parse_mode='HTML')

async def admin_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    cleared_users = 0
    current_time = datetime.now()

    for user_id in list(user_data.keys()):
        if user_id.startswith('_') or user_id in ADMIN_IDS:
            continue

        user_stats = user_data.get('_user_stats', {}).get(user_id, {})
        last_search = user_stats.get('last_search')

        if last_search:
            try:
                last_active = datetime.strptime(last_search, '%d.%m.%Y %H:%M')
                if (current_time - last_active).days > 30:
                    del user_data[user_id]
                    if user_id in user_data.get('_user_stats', {}):
                        del user_data['_user_stats'][user_id]
                    cleared_users += 1
            except ValueError:
                del user_data[user_id]
                cleared_users += 1
        else:
            del user_data[user_id]
            cleared_users += 1

    save_data()

    await update.message.reply_text(
        f"✅ Cleanup completed!\n"
        f"🗑 Inactive users removed: {cleared_users}\n"
        f"👥 Remaining users: {len([k for k in user_data.keys() if not k.startswith('_')])}"
    )

async def admin_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    try:
        user_data_size = os.path.getsize('user_data.json') if os.path.exists('user_data.json') else 0
        charts_cache_size = os.path.getsize('charts_cache.json') if os.path.exists('charts_cache.json') else 0

        text = f"""📁 <b>File Information</b>

user_data.json: {user_data_size / 1024:.1f} KB
charts_cache.json: {charts_cache_size / 1024:.1f} KB
Total users: {len(user_data)}"""

        await update.message.reply_text(text, parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return

    text = """🔧 <b>Admin Commands</b>

/admin_stats - 📊 Bot statistics
/admin_cleanup - 🗑 Clean inactive users  
/admin_files - 📁 File information
/admin_help - ❓ This help"""

    await update.message.reply_text(text, parse_mode='HTML')

def setup_admin_commands(app):
    if ADMIN_IDS:
        app.add_handler(CommandHandler('admin_stats', admin_stats))
        app.add_handler(CommandHandler('admin_cleanup', admin_cleanup))
        app.add_handler(CommandHandler('admin_files', admin_files))
        app.add_handler(CommandHandler('admin_help', admin_help))
        print("✅ Admin commands registered")
    else:
        print("⚠️  Admin commands disabled (ADMIN_IDS not set)")

# ==================== NOTIFICATION SYSTEM ====================

class NotificationManager:
    @staticmethod
    async def send_progress(update, context, stage: str, track=None, **kwargs):
        user_id = update.effective_user.id
        stages = {
            'searching': get_text(user_id, 'searching'),
            'downloading': get_text(user_id, 'downloading'), 
            'processing': get_text(user_id, 'processing'),
            'sending': get_text(user_id, 'sending'),
            'success': get_text(user_id, 'success'),
            'error': get_text(user_id, 'error')
        }
        
        message = stages.get(stage, "⏳ Working...")
        if track and stage != 'searching':
            title = track.get('title', 'Unknown track')[:30]
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
            logger.warning(f"Notification error: {e}")

# ==================== MAIN BOT CLASS ====================

class StableMusicBot:
    def __init__(self):
        self.user_stats = user_data.get('_user_stats', {})
        self.track_info_cache = {}
        self.download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        self.search_semaphore = asyncio.Semaphore(3)
        self.notifications = NotificationManager()
        logger.info('✅ Bot initialized')

    def ensure_user(self, user_id: str):
        if str(user_id) not in user_data:
            user_data[str(user_id)] = {
                'filters': {'duration': 'no_filter', 'music_only': False},
                'search_results': [],
                'search_query': '',
                'current_page': 0,
                'total_pages': 0,
                'favorites': [],
                'search_history': [],
                'download_history': [],
                'download_queue': [],
                'random_track_result': [],
                'achievements': {},
                'preferences': {
                    'language': 'en',  # English by default
                    'favorite_genres': [],
                    'disliked_genres': [],
                    'notifications': True,
                }
            }
        if '_user_stats' not in user_data:
            user_data['_user_stats'] = {}
        if str(user_id) not in user_data['_user_stats']:
            user_data['_user_stats'][str(user_id)] = {
                'searches': 0,
                'downloads': 0,
                'first_seen': datetime.now().strftime('%d.%m.%Y %H:%M'),
                'last_search': None,
            }

    @staticmethod
    def clean_title(title: str) -> str:
        if not title:
            return 'Unknown track'
        try:
            title = title.encode('utf-8').decode('utf-8')
        except:
            pass
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

    async def check_file_size_before_download(self, url: str, track: dict) -> tuple:
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

                duration = track.get('duration', 0)
                if duration > 1800:
                    can_download = file_size < (MAX_FILE_SIZE_MB * 0.7)
                else:
                    can_download = file_size < MAX_FILE_SIZE_MB

                return file_size, can_download

        except Exception as e:
            logger.warning(f"Failed to get file size: {e}")
            return 0, True

    def _get_dynamic_timeout(self, track: dict) -> int:
        duration = track.get('duration', 0)
        if duration < 180:
            return DYNAMIC_TIMEOUTS['short_track']
        elif duration < 600:
            return DYNAMIC_TIMEOUTS['medium_track']
        else:
            return DYNAMIC_TIMEOUTS['long_track']

    async def _handle_large_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict, file_size: float):
        user = update.effective_user
        title = track.get('title', 'Unknown track')
        artist = track.get('artist', 'Unknown artist')
        
        text = f"📦 <b>File too large</b>\n\n"
        text += f"🎵 <b>{title}</b>\n"
        text += f"🎤 {artist}\n"
        text += f"💾 Size: {file_size:.1f} MB\n\n"
        text += f"⚠️ <b>Exceeded limit {MAX_FILE_SIZE_MB} MB</b>\n\n"
        text += f"🎧 You can:\n• Listen online\n• Find shorter version"

        keyboard = [
            [InlineKeyboardButton('🎧 Listen online', url=track.get('webpage_url', ''))],
            [InlineKeyboardButton('🔍 Find other version', callback_data=f'search_alt:{title}')],
            [InlineKeyboardButton(get_text(user.id, 'random_track'), callback_data='random_track')],
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

    async def _find_compatible_audio_file(self, tmpdir: str) -> str:
        telegram_audio_extensions = ['.mp3', '.m4a', '.ogg', '.wav', '.flac']
        
        for file in os.listdir(tmpdir):
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in telegram_audio_extensions:
                logger.info(f"✅ Compatible file found: {file}")
                return file
        
        logger.error(f"❌ Compatible files not found in: {os.listdir(tmpdir)}")
        return None

    async def _send_audio_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             fpath: str, track: dict, actual_size_mb: float) -> bool:
        try:
            with open(fpath, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=f,
                    title=(track.get('title') or 'Unknown track')[:64],
                    performer=(track.get('artist') or 'Unknown artist')[:64],
                    caption=f"🎵 <b>{track.get('title', 'Unknown track')}</b>\n🎤 {track.get('artist', 'Unknown artist')}\n⏱️ {self.format_duration(track.get('duration'))}\n💾 {actual_size_mb:.1f} MB",
                    parse_mode='HTML',
                )
            return True
        except Exception as e:
            logger.error(f"File sending error: {e}")
            return False

    async def _cleanup_temp_dir(self, tmpdir: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if os.path.exists(tmpdir):
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    logger.info(f"✅ Temp files cleaned (attempt {attempt + 1})")
                    break
                else:
                    break
            except Exception as e:
                logger.warning(f"Failed to clean temp directory (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

    async def download_and_send_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict, status_message=None) -> bool:
        url = track.get('webpage_url') or track.get('url')
        if not url:
            return False

        file_size_mb, can_download = await self.check_file_size_before_download(url, track)
        
        if not can_download:
            await self._handle_large_file(update, context, track, file_size_mb)
            return False

        async with self.download_semaphore:
            try:
                if status_message:
                    await status_message.edit_text(f"⬇️ Downloading audio...\n🎵 {track.get('title', 'Unknown track')[:30]}")
                else:
                    await self.notifications.send_progress(update, context, 'downloading', track)
                
                timeout = self._get_dynamic_timeout(track)
                
                return await asyncio.wait_for(
                    self.simple_download(update, context, track, status_message),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Download timeout for track: {track.get('title', 'Unknown')}")
                if status_message:
                    await status_message.edit_text(f"❌ Error: Download timeout\n🎵 {track.get('title', 'Unknown track')[:30]}")
                else:
                    await self.notifications.send_progress(update, context, 'error', track)
                return False
            except Exception as e:
                logger.exception(f'Download error: {e}')
                if status_message:
                    await status_message.edit_text(f"❌ Download error\n🎵 {track.get('title', 'Unknown track')[:30]}")
                else:
                    await self.notifications.send_progress(update, context, 'error', track)
                return False

    async def simple_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict, status_message=None) -> bool:
        url = track.get('webpage_url') or track.get('url')
        if not url:
            return False

        loop = asyncio.get_event_loop()
        tmpdir = tempfile.mkdtemp()
        
        try:
            if status_message:
                await status_message.edit_text(f"🔄 Processing file...\n🎵 {track.get('title', 'Unknown track')[:30]}")
            else:
                await self.notifications.send_progress(update, context, 'processing', track)
            
            ydl_opts = SIMPLE_DOWNLOAD_OPTS.copy()
            ydl_opts['outtmpl'] = os.path.join(tmpdir, '%(title).100s.%(ext)s')

            def download_track():
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(url, download=True)
                except Exception as e:
                    logger.error(f"Download error: {e}")
                    return None

            info = await asyncio.wait_for(
                loop.run_in_executor(None, download_track),
                timeout=DOWNLOAD_TIMEOUT - 30
            )

            if not info:
                return False

            audio_file = await self._find_compatible_audio_file(tmpdir)
            if not audio_file:
                return False

            fpath = os.path.join(tmpdir, audio_file)
            actual_size_mb = os.path.getsize(fpath) / (1024 * 1024)
            
            if actual_size_mb >= MAX_FILE_SIZE_MB:
                await self._handle_large_file(update, context, track, actual_size_mb)
                return False

            if status_message:
                await status_message.edit_text(f"📤 Sending to Telegram...\n🎵 {track.get('title', 'Unknown track')[:30]}")
            else:
                await self.notifications.send_progress(update, context, 'sending', track)

            success = await self._send_audio_file(update, context, fpath, track, actual_size_mb)
            
            if success:
                if status_message:
                    await status_message.edit_text(f"✅ Ready!\n🎵 {track.get('title', 'Unknown track')[:30]}")
                else:
                    await self.notifications.send_progress(update, context, 'success', track)
                return True
            return False

        except asyncio.TimeoutError:
            logger.error(f"Download timeout: {track.get('title', 'Unknown')}")
            return False
        except Exception as e:
            logger.exception(f'Download error: {e}')
            return False
        finally:
            await self._cleanup_temp_dir(tmpdir)

    # ==================== LANGUAGE SYSTEM ====================

    async def show_language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show language selection menu"""
        user = update.effective_user
        self.ensure_user(user.id)
        
        current_lang = user_data[str(user.id)]['preferences'].get('language', 'en')
        current_lang_name = LANGUAGES.get(current_lang, 'English')

        text = f"🌐 <b>{get_text(user.id, 'change_language')}</b>\n\n"
        text += f"{get_text(user.id, 'current_language', language=current_lang_name)}\n\n"
        text += "Choose language:"

        keyboard = []
        # English first, then Ukrainian, then Russian
        for lang_id in ['en', 'uk', 'ru']:
            prefix = "✅ " if lang_id == current_lang else "◯ "
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix}{LANGUAGES[lang_id]}", 
                    callback_data=f'set_language:{lang_id}'
                )
            ])

        keyboard.append([InlineKeyboardButton(get_text(user.id, 'back_to_settings'), callback_data='settings')])

        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    async def set_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lang_id: str):
        """Set user language"""
        user = update.effective_user
        self.ensure_user(user.id)

        if lang_id not in LANGUAGES:
            await update.callback_query.answer("❌ Language not supported")
            return

        user_data[str(user.id)]['preferences']['language'] = lang_id
        save_data()

        lang_name = LANGUAGES[lang_id]
        await update.callback_query.answer(get_text(user.id, 'language_changed'))
        
        # Show language change message
        text = f"✅ {get_text(user.id, 'language_changed')}\n\n"
        text += f"{get_text(user.id, 'current_language', language=lang_name)}"

        keyboard = [[InlineKeyboardButton("OK", callback_data='back_to_main')]]
        
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    # ==================== MAIN MENU ====================

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        user = update.effective_user
        self.ensure_user(user.id)
        
        text = f"{get_text(user.id, 'main_menu')}\n\n"
        text += f"{get_text(user.id, 'welcome', name=user.first_name)}\n\n"
        text += f"{get_text(user.id, 'choose_action')}"

        keyboard = [
            [
                InlineKeyboardButton(get_text(user.id, 'random_track'), callback_data='random_track'),
                InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='start_search')
            ],
            [
                InlineKeyboardButton(get_text(user.id, 'top_charts'), callback_data='show_charts'),
                InlineKeyboardButton(get_text(user.id, 'mood'), callback_data='mood_playlists')
            ],
            [
                InlineKeyboardButton(get_text(user.id, 'recommendations'), callback_data='show_recommendations'),
                InlineKeyboardButton(get_text(user.id, 'settings'), callback_data='settings')
            ]
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

    # ==================== SETTINGS ====================

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings"""
        user = update.effective_user
        self.ensure_user(user.id)

        preferences = user_data[str(user.id)]['preferences']
        filters = user_data[str(user.id)]['filters']
        
        current_lang = LANGUAGES.get(preferences.get('language', 'en'), 'English')
        notifications_status = get_text(user.id, 'on') if preferences.get('notifications', True) else get_text(user.id, 'off')
        current_duration = get_duration_filter_text(user.id, filters.get('duration', 'no_filter'))
        music_only = get_text(user.id, 'on') if filters.get('music_only') else get_text(user.id, 'off')

        text = f"{get_text(user.id, 'settings_title')}\n\n"
        text += f"{get_text(user.id, 'current_language', language=current_lang)}\n"
        text += f"{get_text(user.id, 'notifications', status=notifications_status)}\n"
        text += f"{get_text(user.id, 'duration_filter', filter=current_duration)}\n"
        text += f"{get_text(user.id, 'music_only', status=music_only)}\n\n"
        text += f"{get_text(user.id, 'choose_action')}"

        keyboard = [
            [InlineKeyboardButton(get_text(user.id, 'change_language'), callback_data='language_menu')],
            [InlineKeyboardButton(get_text(user.id, 'duration_menu'), callback_data='duration_menu')],
            [InlineKeyboardButton(f"{get_text(user.id, 'toggle_music')}: {music_only}", callback_data='toggle_music')],
            [InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')],
        ]

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    async def show_duration_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show duration filters menu"""
        user = update.effective_user
        self.ensure_user(user.id)

        current_filter = user_data[str(user.id)]['filters'].get('duration', 'no_filter')

        text = f"{get_text(user.id, 'duration_title')}\n\n"
        text += f"{get_text(user.id, 'choose_duration')}"

        keyboard = []
        for key in DURATION_FILTERS.keys():
            filter_text = get_duration_filter_text(user.id, key)
            prefix = "✅ " if key == current_filter else "◯ "
            keyboard.append([InlineKeyboardButton(f"{prefix}{filter_text}", callback_data=f'set_duration:{key}')])

        keyboard.append([InlineKeyboardButton(get_text(user.id, 'back_to_settings'), callback_data='settings')])

        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    async def set_duration_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
        """Set duration filter"""
        user = update.effective_user
        self.ensure_user(user.id)

        user_data[str(user.id)]['filters']['duration'] = key
        save_data()

        filter_name = get_duration_filter_text(user.id, key)
        await update.callback_query.answer(f"Filter set: {filter_name}")
        await self.show_settings(update, context)

    async def toggle_music_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle 'Music only' filter"""
        user = update.effective_user
        self.ensure_user(user.id)

        current = user_data[str(user.id)]['filters'].get('music_only', False)
        user_data[str(user.id)]['filters']['music_only'] = not current
        save_data()

        status = get_text(user.id, 'on') if not current else get_text(user.id, 'off')
        await update.callback_query.answer(f"{get_text(user.id, 'music_only')} {status}")
        await self.show_settings(update, context)

    # ==================== SEARCH ====================

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /search command"""
        user = update.effective_user
        await update.message.reply_text(get_text(user.id, 'enter_query'))

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Text message handler"""
        text = update.message.text.strip()
        user = update.effective_user
        self.ensure_user(user.id)
        
        if len(text) < 2:
            await update.message.reply_text('❌ Enter at least 2 characters')
            return

        stats = user_data['_user_stats'][str(user.id)]
        stats['searches'] += 1
        stats['last_search'] = datetime.now().strftime('%d.%m.%Y %H:%M')

        user_entry = user_data[str(user.id)]
        history = user_entry.get('search_history', [])
        history = [text] + [h for h in history if h != text][:9]
        user_entry['search_history'] = history

        try:
            await self.notifications.send_progress(update, context, 'searching')
        except:
            return

        try:
            results = await self.search_soundcloud(text)
            if not results:
                await update.message.reply_text('❌ Nothing found for your query.')
                return

            user_entry['search_results'] = results
            user_entry['search_query'] = text
            user_entry['current_page'] = 0
            user_entry['total_pages'] = (len(results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
            save_data()

            await self.show_results_page(update, context, user.id, 0)
        except Exception as e:
            logger.exception('Search error')
            await update.message.reply_text('❌ Search error.')

    async def show_results_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, page: int):
        """Show search results page"""
        user_entry = user_data.get(str(user_id), {})
        results = user_entry.get('search_results', [])
        total_pages = user_entry.get('total_pages', 0)
        query = user_entry.get('search_query', '')

        if page < 0 or page >= max(1, total_pages):
            page = 0

        start = page * RESULTS_PER_PAGE
        end = min(start + RESULTS_PER_PAGE, len(results))

        text = f"{get_text(user_id, 'search_results')} <code>{query}</code>\n"
        text += f"{get_text(user_id, 'page', current=page+1, total=max(1, total_pages))}\n"
        text += f"{get_text(user_id, 'found', count=len(results))}\n\n"

        keyboard = []
        for idx in range(start, end):
            track = results[idx]
            title = track.get('title', 'Unknown track')
            artist = track.get('artist', 'Unknown artist')
            duration = self.format_duration(track.get('duration'))

            short_title = title if len(title) <= 30 else title[:27] + '...'
            short_artist = artist if len(artist) <= 18 else artist[:15] + '...'

            button_text = f"🎵 {idx + 1}. {short_title} • {short_artist} • {duration}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'download:{idx}:{page}')])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(get_text(user_id, 'back'), callback_data=f'page:{page-1}'))
        if total_pages > 1:
            nav_buttons.append(InlineKeyboardButton(get_text(user_id, 'current_page', current=page+1, total=total_pages), callback_data='current_page'))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(get_text(user_id, 'next'), callback_data=f'page:{page+1}'))
        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.extend([
            [InlineKeyboardButton(get_text(user_id, 'new_search'), callback_data='new_search')],
            [InlineKeyboardButton(get_text(user_id, 'random_track'), callback_data='random_track')],
            [InlineKeyboardButton(get_text(user_id, 'settings'), callback_data='settings')],
        ])

        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except Exception as e:
            logger.warning(f'Error displaying results page: {e}')

        user_data[str(user_id)]['current_page'] = page
        save_data()

    # ==================== CALLBACK HANDLERS ====================

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = (query.data or '')
        user = update.effective_user
        self.ensure_user(user.id)

        try:
            await query.answer()
        except Exception as e:
            if "too old" in str(e) or "timeout" in str(e) or "invalid" in str(e):
                logger.warning(f"Ignored old callback: {e}")
                return
            else:
                logger.warning(f"Error in answer callback: {e}")

        try:
            if data == 'start_search' or data == 'new_search':
                await query.edit_message_text(get_text(user.id, 'enter_query'))
                return

            if data == 'random_track':
                await self.random_track(update, context)
                return

            if data == 'show_recommendations' or data == 'refresh_recommendations':
                await self.show_recommendations(update, context)
                return

            if data == 'show_charts' or data == 'refresh_charts':
                await self.show_charts(update, context)
                return

            if data == 'mood_playlists':
                await self.show_mood_playlists(update, context)
                return

            if data == 'settings':
                await self.show_settings(update, context)
                return

            if data == 'language_menu':
                await self.show_language_menu(update, context)
                return

            if data == 'duration_menu':
                await self.show_duration_menu(update, context)
                return

            if data == 'back_to_main':
                await self.show_main_menu(update, context)
                return

            if data == 'toggle_music':
                await self.toggle_music_filter(update, context)
                return

            if data.startswith('set_language:'):
                lang_id = data.split(':', 1)[1]
                await self.set_language(update, context, lang_id)
                return

            if data.startswith('set_duration:'):
                key = data.split(':', 1)[1]
                await self.set_duration_filter(update, context, key)
                return

            if data.startswith('playlist:'):
                playlist_id = data.split(':', 1)[1]
                await self.generate_playlist(update, context, playlist_id)
                return

            if data.startswith('charts_page:'):
                page = int(data.split(':', 1)[1])
                await self.show_charts_page(update, context, page)
                return

            if data.startswith('playlist_page:'):
                page = int(data.split(':', 1)[1])
                await self.show_playlist_page(update, context, page)
                return

            if data.startswith('rec_page:'):
                page = int(data.split(':', 1)[1])
                await self.show_recommendations_page(update, context, page)
                return

            if data.startswith('rec_download:'):
                idx = int(data.split(':', 1)[1])
                await self.download_from_recommendations(update, context, idx)
                return

            if data.startswith('chart_download:'):
                idx = int(data.split(':', 1)[1])
                await self.download_from_charts(update, context, idx)
                return

            if data.startswith('playlist_download:'):
                idx = int(data.split(':', 1)[1])
                await self.download_from_playlist(update, context, idx)
                return

            if data.startswith('page:'):
                page = int(data.split(':', 1)[1])
                await self.show_results_page(update, context, user.id, page)
                return

            if data.startswith('download:'):
                parts = data.split(':')
                if len(parts) >= 3:
                    idx = int(parts[1])
                    return_page = int(parts[2])
                    await self.download_by_index(update, context, idx, return_page)
                return

            await query.edit_message_text('❌ Unknown command')

        except Exception as e:
            logger.exception('Callback processing error')
            try:
                await query.message.reply_text('❌ An error occurred')
            except:
                pass

    # ==================== OTHER METHODS ====================

    async def download_by_index(self, update: Update, context: ContextTypes.DEFAULT_TYPE, index: int, return_page: int = 0):
        """Download track by index with return button"""
        query = update.callback_query
        user = update.effective_user

        user_entry = user_data.get(str(user.id), {})
        results = user_entry.get('search_results', [])
        if index < 0 or index >= len(results):
            await query.edit_message_text('❌ Track not found')
            return

        track = results[index]
        success = await self.download_and_send_track(update, context, track)
        
        if success:
            stats = user_data.get('_user_stats', {}).get(str(user.id), {})
            stats['downloads'] = stats.get('downloads', 0) + 1
            save_data()

            user_entry = user_data[str(user.id)]
            download_history = user_entry.get('download_history', [])
            download_history.append(track)
            user_entry['download_history'] = download_history[-50:]
            save_data()

            # Show return button
            return_text = "✅ Track successfully downloaded!\n\nReturn to search results:"
            
            keyboard = [
                [InlineKeyboardButton('📋 To search results', callback_data=f'page:{return_page}')],
                [InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')]
            ]

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=return_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def random_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search and download random track"""
        user = update.effective_user
        self.ensure_user(user.id)

        random_search = random.choice(RANDOM_SEARCHES)

        if update.callback_query:
            try:
                status_msg = await update.callback_query.message.reply_text(
                    f"🔍 <b>Searching random track</b>\n\n📝 Query: <code>{random_search}</code>\n⏱️ Wait ~10-20 seconds",
                    parse_mode='HTML'
                )
            except:
                return
        else:
            status_msg = await update.message.reply_text(
                f"🔍 <b>Searching random track</b>\n\n📝 Query: <code>{random_search}</code>\n⏱️ Wait ~10-20 seconds",
                parse_mode='HTML'
            )

        try:
            results = await self.search_soundcloud(random_search, album_only=False)
            if not results:
                await status_msg.edit_text(
                    "❌ <b>Failed to find random track</b>\n\n"
                    "Try again or choose another search method",
                    parse_mode='HTML'
                )
                return

            random_track = random.choice(results)
            
            await status_msg.edit_text(
                f"✅ <b>Random track found!</b>\n\n"
                f"🎵 Track: <b>{random_track.get('title', 'Unknown track')}</b>\n"
                f"🎤 Artist: {random_track.get('artist', 'Unknown artist')}\n"
                f"⏱️ Duration: {self.format_duration(random_track.get('duration'))}\n\n"
                f"⏬ <b>Starting download...</b>",
                parse_mode='HTML'
            )

            success = await self.download_and_send_track(update, context, random_track, status_msg)

            if success:
                stats = user_data.get('_user_stats', {}).get(str(user.id), {})
                stats['downloads'] = stats.get('downloads', 0) + 1
                stats['searches'] = stats.get('searches', 0) + 1
                save_data()

                user_entry = user_data[str(user.id)]
                download_history = user_entry.get('download_history', [])
                download_history.append(random_track)
                user_entry['download_history'] = download_history[-50:]
                save_data()

                keyboard = [
                    [InlineKeyboardButton(get_text(user.id, 'random_track'), callback_data='random_track')],
                    [InlineKeyboardButton(get_text(user.id, 'recommendations'), callback_data='show_recommendations')],
                    [InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='start_search')],
                ]

                await status_msg.edit_text(
                    "✅ <b>Random track successfully downloaded!</b>\n\n"
                    "What would you like to do next?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.exception(f'Error searching random track: {e}')
            
            keyboard = [
                [InlineKeyboardButton(get_text(user.id, 'random_track'), callback_data='random_track')],
                [InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='start_search')],
            ]

            await status_msg.edit_text(
                "❌ <b>Error occurred while searching random track</b>\n\n"
                "Try again or choose another search method",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    async def show_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show top charts"""
        user = update.effective_user
        self.ensure_user(user.id)

        try:
            if update.callback_query:
                status_msg = await update.callback_query.message.reply_text(get_text(user.id, 'loading_charts'))
            else:
                status_msg = await update.message.reply_text(get_text(user.id, 'loading_charts'))
        except:
            return

        try:
            await self.update_charts_cache()

            charts_data = charts_cache.get('data', {})

            if not charts_data:
                await status_msg.edit_text("❌ Charts temporarily unavailable. Try again later.")
                return

            all_tracks = []
            for query, tracks in charts_data.items():
                all_tracks.extend(tracks)

            random.shuffle(all_tracks)
            top_tracks = all_tracks[:30]

            user_data[str(user.id)]['current_charts'] = top_tracks
            user_data[str(user.id)]['charts_page'] = 0
            user_data[str(user.id)]['charts_total_pages'] = (len(top_tracks) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
            save_data()

            await self.show_charts_page(update, context, 0, status_msg)

        except Exception as e:
            logger.exception(f'Error showing charts: {e}')
            await status_msg.edit_text('❌ Error loading charts. Try again later.')

    async def show_charts_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int, status_msg=None):
        """Show charts page"""
        user = update.effective_user
        self.ensure_user(user.id)

        charts = user_data[str(user.id)].get('current_charts', [])
        total_pages = user_data[str(user.id)].get('charts_total_pages', 0)

        if page < 0 or page >= max(1, total_pages):
            page = 0

        start = page * RESULTS_PER_PAGE
        end = min(start + RESULTS_PER_PAGE, len(charts))

        text = f"{get_text(user.id, 'charts_title')}\n"
        text += f"{get_text(user.id, 'page', current=page+1, total=max(1, total_pages))}\n"
        text += f"{get_text(user.id, 'found', count=len(charts))}\n\n"

        keyboard = []
        for idx in range(start, end):
            track = charts[idx]

            title = track.get('title', 'Unknown track')
            artist = track.get('artist', 'Unknown artist')
            duration = self.format_duration(track.get('duration'))

            short_title = title if len(title) <= 30 else title[:27] + '...'
            short_artist = artist if len(artist) <= 18 else artist[:15] + '...'

            button_text = f"🎵 {idx + 1}. {short_title} • {short_artist} • {duration}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'chart_download:{idx}')])

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(get_text(user.id, 'back'), callback_data=f'charts_page:{page-1}'))
        if total_pages > 1:
            nav.append(InlineKeyboardButton(get_text(user.id, 'current_page', current=page+1, total=total_pages), callback_data='charts_current_page'))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(get_text(user.id, 'next'), callback_data=f'charts_page:{page+1}'))
        if nav:
            keyboard.append(nav)

        keyboard.extend([
            [InlineKeyboardButton(get_text(user.id, 'refresh'), callback_data='refresh_charts')],
            [InlineKeyboardButton(get_text(user.id, 'recommendations'), callback_data='show_recommendations')],
            [InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='new_search')],
            [InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')],
        ])

        try:
            if status_msg:
                await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            elif update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except Exception as e:
            logger.warning(f'Error displaying charts page: {e}')

        user_data[str(user.id)]['charts_page'] = page
        save_data()

    async def show_recommendations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recommendations"""
        user = update.effective_user
        self.ensure_user(user.id)

        try:
            if update.callback_query:
                status_msg = await update.callback_query.message.reply_text(get_text(user.id, 'loading_recommendations'))
            else:
                status_msg = await update.message.reply_text(get_text(user.id, 'loading_recommendations'))
        except:
            return

        try:
            recommendations = await self.get_recommendations(user.id, 30)

            if not recommendations:
                await status_msg.edit_text(
                    "📝 I can't offer personalized recommendations yet.\n\n"
                    "Download a few tracks so I can learn your preferences!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(get_text(user.id, 'random_track'), callback_data='random_track')],
                        [InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='start_search')],
                        [InlineKeyboardButton(get_text(user.id, 'top_charts'), callback_data='show_charts')],
                    ])
                )
                return

            user_data[str(user.id)]['current_recommendations'] = recommendations
            user_data[str(user.id)]['recommendations_page'] = 0
            user_data[str(user.id)]['recommendations_total_pages'] = (len(recommendations) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
            save_data()

            await self.show_recommendations_page(update, context, 0, status_msg)

        except Exception as e:
            logger.exception(f'Error showing recommendations: {e}')
            await status_msg.edit_text(
                '❌ Error loading recommendations',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(get_text(user.id, 'refresh'), callback_data='show_recommendations')],
                    [InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')],
                ])
            )

    async def show_recommendations_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int, status_msg=None):
        """Show recommendations page"""
        user = update.effective_user
        self.ensure_user(user.id)

        recommendations = user_data[str(user.id)].get('current_recommendations', [])
        total_pages = user_data[str(user.id)].get('recommendations_total_pages', 0)

        if page < 0 or page >= max(1, total_pages):
            page = 0

        start = page * RESULTS_PER_PAGE
        end = min(start + RESULTS_PER_PAGE, len(recommendations))

        text = f"{get_text(user.id, 'recommendations_title')}\n"
        text += f"{get_text(user.id, 'page', current=page+1, total=max(1, total_pages))}\n"
        text += f"{get_text(user.id, 'found', count=len(recommendations))}\n\n"

        history_count = len(user_data[str(user.id)].get('download_history', []))
        if history_count > 0:
            text += f"📊 Based on {history_count} downloaded tracks\n\n"

        keyboard = []
        for idx in range(start, end):
            track = recommendations[idx]

            title = track.get('title', 'Unknown track')
            artist = track.get('artist', 'Unknown artist')
            duration = self.format_duration(track.get('duration'))

            short_title = title if len(title) <= 30 else title[:27] + '...'
            short_artist = artist if len(artist) <= 18 else artist[:15] + '...'

            button_text = f"🎵 {idx + 1}. {short_title} • {short_artist} • {duration}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'rec_download:{idx}')])

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(get_text(user.id, 'back'), callback_data=f'rec_page:{page-1}'))
        if total_pages > 1:
            nav.append(InlineKeyboardButton(get_text(user.id, 'current_page', current=page+1, total=total_pages), callback_data='rec_current_page'))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(get_text(user.id, 'next'), callback_data=f'rec_page:{page+1}'))
        if nav:
            keyboard.append(nav)

        keyboard.extend([
            [InlineKeyboardButton(get_text(user.id, 'refresh'), callback_data='refresh_recommendations')],
            [
                InlineKeyboardButton(get_text(user.id, 'random_track'), callback_data='random_track'),
                InlineKeyboardButton(get_text(user.id, 'top_charts'), callback_data='show_charts')
            ],
            [
                InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='start_search'),
                InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')
            ],
        ])

        try:
            if status_msg:
                await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            elif update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except Exception as e:
            logger.warning(f'Error displaying recommendations page: {e}')

        user_data[str(user.id)]['recommendations_page'] = page
        save_data()

    async def show_mood_playlists(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show mood playlists"""
        user = update.effective_user
        text = f"{get_text(user.id, 'mood_title')}\n\n"
        text += "Ready-made selections for any mood:\n\n"

        keyboard = []
        for playlist_id in SMART_PLAYLISTS.keys():
            playlist_name = get_playlist_name(user.id, playlist_id)
            keyboard.append([InlineKeyboardButton(playlist_name, callback_data=f'playlist:{playlist_id}')])

        keyboard.extend([
            [InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='start_search')],
            [InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')],
        ])

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    # ==================== SERVICE METHODS ====================

    async def search_soundcloud(self, query: str, album_only: bool = False):
        """Search on SoundCloud"""
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

            results = []
            try:
                def perform_search():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(f"scsearch30:{query}", download=False)

                loop = asyncio.get_event_loop()
                info = await asyncio.wait_for(
                    loop.run_in_executor(None, perform_search),
                    timeout=SEARCH_TIMEOUT
                )

                if not info:
                    return results

                entries = info.get('entries', [])
                if not entries and info.get('_type') != 'playlist':
                    entries = [info]

                for entry in entries:
                    if not entry:
                        continue

                    title = self.clean_title(entry.get('title') or '')
                    webpage_url = entry.get('webpage_url') or entry.get('url') or ''
                    duration = entry.get('duration') or 0
                    artist = entry.get('uploader') or entry.get('uploader_id') or 'Unknown'
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

            except asyncio.TimeoutError:
                logger.warning(f"Search timeout for query: {query}")
                return []
            except Exception as e:
                logger.warning(f'SoundCloud search error: {e}')
                return []

            logger.info(f"✅ SoundCloud: {len(results)} results for: '{query}'")
            return results

    async def get_recommendations(self, user_id: str, limit: int = 30) -> list:
        """Get recommendations based on user history"""
        user_entry = user_data.get(str(user_id), {})
        download_history = user_entry.get('download_history', [])
        search_history = user_entry.get('search_history', [])

        if not download_history and not search_history:
            return await self.get_popular_recommendations(limit)

        user_genres = self.analyze_user_preferences_fast(user_id)

        recommendations = []

        for track in download_history[-10:]:
            if track not in recommendations:
                recommendations.append(track)

        popular = await self.get_popular_recommendations(limit // 2)
        recommendations.extend(popular)

        unique_recommendations = []
        seen_titles = set()
        for track in recommendations:
            if track.get('title') and track['title'] not in seen_titles:
                seen_titles.add(track['title'])
                unique_recommendations.append(track)

        random.shuffle(unique_recommendations)
        return unique_recommendations[:limit]

    def analyze_user_preferences_fast(self, user_id: str) -> list:
        """Fast analysis of user preferences"""
        user_entry = user_data.get(str(user_id), {})
        download_history = user_entry.get('download_history', [])

        if not download_history:
            return []

        recent_titles = [track.get('title', '').lower() for track in download_history[-5:]]

        genres = []
        for title in recent_titles:
            if any(word in title for word in ['lofi', 'chill', 'study']):
                genres.append('lofi')
            elif any(word in title for word in ['focus', 'work', 'coding']):
                genres.append('focus')
            elif any(word in title for word in ['rock', 'metal']):
                genres.append('rock')
            elif any(word in title for word in ['jazz', 'blues']):
                genres.append('jazz')

        return list(set(genres))[:3]

    async def get_popular_recommendations(self, limit: int = 15) -> list:
        """Fast popular recommendations"""
        popular_tracks = []

        for query in POPULAR_SEARCHES[:4]:
            try:
                results = await self.search_soundcloud(query, album_only=False)
                if results:
                    popular_tracks.extend(results[:8])
            except Exception as e:
                logger.warning(f"Error searching popular tracks: {e}")

        random.shuffle(popular_tracks)
        return popular_tracks[:limit]

    async def update_charts_cache(self):
        """Update charts cache"""
        now = datetime.now()
        last_update = charts_cache.get('last_update')

        if last_update:
            last_update_date = datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S')
            if now - last_update_date < timedelta(hours=24):
                return

        logger.info("🔄 Updating charts cache...")

        charts_data = {}
        for query in POPULAR_SEARCHES[:5]:
            try:
                results = await self.search_soundcloud(query, album_only=False)
                if results:
                    charts_data[query] = results[:10]
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Error updating chart for {query}: {e}")

        charts_cache['data'] = charts_data
        charts_cache['last_update'] = now.strftime('%Y-%m-%d %H:%M:%S')
        save_charts_cache()
        logger.info("✅ Charts cache updated")

    async def generate_playlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, playlist_id: str):
        """Generate playlist by template"""
        user = update.effective_user
        self.ensure_user(user.id)

        playlist = SMART_PLAYLISTS.get(playlist_id)
        if not playlist:
            if update.callback_query:
                await update.callback_query.message.reply_text("❌ Playlist not found")
            else:
                await update.message.reply_text("❌ Playlist not found")
            return

        try:
            if update.callback_query:
                status_msg = await update.callback_query.message.reply_text(f"🎵 Creating playlist: {get_playlist_name(user.id, playlist_id)}...")
            else:
                status_msg = await update.message.reply_text(f"🎵 Creating playlist: {get_playlist_name(user.id, playlist_id)}...")
        except:
            return

        try:
            all_tracks = []
            for query in playlist['queries'][:3]:
                try:
                    results = await self.search_soundcloud(query, album_only=False)
                    if results:
                        all_tracks.extend(results[:10])
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Search error for playlist {query}: {e}")

            if not all_tracks:
                await status_msg.edit_text("❌ Failed to find tracks for playlist. Try again later.")
                return

            random.shuffle(all_tracks)
            playlist_tracks = all_tracks[:30]

            user_data[str(user.id)]['current_playlist'] = {
                'tracks': playlist_tracks,
                'name': get_playlist_name(user.id, playlist_id),
                'description': get_playlist_description(user.id, playlist_id)
            }
            user_data[str(user.id)]['playlist_page'] = 0
            user_data[str(user.id)]['playlist_total_pages'] = (len(playlist_tracks) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
            save_data()

            await self.show_playlist_page(update, context, 0, status_msg)

        except Exception as e:
            logger.exception(f'Playlist creation error: {e}')
            await status_msg.edit_text('❌ Playlist creation error. Try again later.')

    async def show_playlist_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int, status_msg=None):
        """Show playlist page"""
        user = update.effective_user
        self.ensure_user(user.id)

        playlist_data = user_data[str(user.id)].get('current_playlist', {})
        tracks = playlist_data.get('tracks', [])
        playlist_name = playlist_data.get('name', 'Playlist')
        playlist_description = playlist_data.get('description', '')

        total_pages = user_data[str(user.id)].get('playlist_total_pages', 0)

        if page < 0 or page >= max(1, total_pages):
            page = 0

        start = page * RESULTS_PER_PAGE
        end = min(start + RESULTS_PER_PAGE, len(tracks))

        text = f"🎭 <b>{playlist_name}</b>\n"
        text += f"{get_text(user.id, 'page', current=page+1, total=max(1, total_pages))}\n"
        text += f"{get_text(user.id, 'found', count=len(tracks))}\n"
        text += f"💡 {playlist_description}\n\n"

        keyboard = []
        for idx in range(start, end):
            track = tracks[idx]

            title = track.get('title', 'Unknown track')
            artist = track.get('artist', 'Unknown artist')
            duration = self.format_duration(track.get('duration'))

            short_title = title if len(title) <= 30 else title[:27] + '...'
            short_artist = artist if len(artist) <= 18 else artist[:15] + '...'

            button_text = f"🎵 {idx + 1}. {short_title} • {short_artist} • {duration}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'playlist_download:{idx}')])

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(get_text(user.id, 'back'), callback_data=f'playlist_page:{page-1}'))
        if total_pages > 1:
            nav.append(InlineKeyboardButton(get_text(user.id, 'current_page', current=page+1, total=total_pages), callback_data='playlist_current_page'))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(get_text(user.id, 'next'), callback_data=f'playlist_page:{page+1}'))
        if nav:
            keyboard.append(nav)

        keyboard.extend([
            [InlineKeyboardButton('🔄 Other mood', callback_data='mood_playlists')],
            [InlineKeyboardButton(get_text(user.id, 'search_music'), callback_data='new_search')],
            [InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')],
        ])

        try:
            if status_msg:
                await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            elif update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except Exception as e:
            logger.warning(f'Error displaying playlist page: {e}')

        user_data[str(user.id)]['playlist_page'] = page
        save_data()

    async def download_from_recommendations(self, update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
        """Download from recommendations with return button"""
        user = update.effective_user
        recommendations = user_data[str(user.id)].get('current_recommendations', [])

        if index < 0 or index >= len(recommendations):
            await update.callback_query.edit_message_text('❌ Track not found')
            return

        track = recommendations[index]
        await self.process_track_download_with_return_button(update, context, track, 'recommendations')

    async def download_from_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
        """Download from charts with return button"""
        user = update.effective_user
        charts = user_data[str(user.id)].get('current_charts', [])
        current_page = user_data[str(user.id)].get('charts_page', 0)

        if index < 0 or index >= len(charts):
            await update.callback_query.edit_message_text('❌ Track not found')
            return

        track = charts[index]
        await self.process_track_download_with_return_button(update, context, track, 'charts', current_page)

    async def download_from_playlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
        """Download from playlist with return button"""
        user = update.effective_user
        playlist = user_data[str(user.id)].get('current_playlist', {})
        tracks = playlist.get('tracks', [])
        current_page = user_data[str(user.id)].get('playlist_page', 0)

        if index < 0 or index >= len(tracks):
            await update.callback_query.edit_message_text('❌ Track not found')
            return

        track = tracks[index]
        await self.process_track_download_with_return_button(update, context, track, 'playlist', current_page)

    async def process_track_download_with_return_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict, source: str, return_page: int = 0):
        """Process track download and show return button"""
        query = update.callback_query
        user = update.effective_user

        success = await self.download_and_send_track(update, context, track)

        if success:
            stats = user_data.get('_user_stats', {}).get(str(user.id), {})
            stats['downloads'] = stats.get('downloads', 0) + 1
            save_data()

            user_entry = user_data[str(user.id)]
            download_history = user_entry.get('download_history', [])
            download_history.append(track)
            user_entry['download_history'] = download_history[-50:]
            save_data()

            # Show return button instead of automatic return
            return_text = "✅ Track successfully downloaded!\n\nReturn to list:"
            
            keyboard = []
            if source == 'recommendations':
                keyboard.append([InlineKeyboardButton('📋 To recommendations', callback_data='show_recommendations')])
            elif source == 'charts':
                keyboard.append([InlineKeyboardButton('📋 To charts', callback_data='show_charts')])
            elif source == 'playlist':
                keyboard.append([InlineKeyboardButton('📋 To playlist', callback_data=f'playlist_page:{return_page}')])
            else:  # search results
                keyboard.append([InlineKeyboardButton('📋 To search results', callback_data=f'page:{return_page}')])
            
            keyboard.append([InlineKeyboardButton(get_text(user.id, 'back_to_main'), callback_data='back_to_main')])

            # Send new message with button instead of editing existing one
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=return_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.ensure_user(user.id)
        await self.show_main_menu(update, context)
        save_data()

    async def charts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_charts(update, context)

    async def mood_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_mood_playlists(update, context)

    async def recommendations_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_recommendations(update, context)

    def run(self):
        print('🚀 Starting multilingual Music Bot...')

        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler('start', self.start))
        app.add_handler(CommandHandler('search', self.search_command))
        app.add_handler(CommandHandler('charts', self.charts_command))
        app.add_handler(CommandHandler('random', self.random_track))
        app.add_handler(CommandHandler('mood', self.mood_command))
        app.add_handler(CommandHandler('recommendations', self.recommendations_command))
        app.add_handler(CommandHandler('settings', self.show_settings))

        setup_admin_commands(app)

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        app.add_handler(CallbackQueryHandler(self.handle_callback))

        async def set_commands(application):
            commands = [
                ('start', '🚀 Start bot'),
                ('search', '🔍 Search music'),
                ('charts', '📊 Top charts'),
                ('random', '🎲 Random track'),
                ('mood', '🎭 Mood playlists'),
                ('recommendations', '🎯 Recommendations'),
                ('settings', '⚙️ Settings'),
            ]

            await application.bot.set_my_commands(commands)
            print('✅ Multilingual command menu configured!')

        app.post_init = set_commands

        print('✅ Multilingual bot started and ready!')
        print(f'✅ Supported languages: {", ".join(LANGUAGES.values())}')
        app.run_polling()

if __name__ == '__main__':
    bot = StableMusicBot()
    bot.run()
