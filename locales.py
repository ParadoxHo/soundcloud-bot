# -*- coding: utf-8 -*-
LANGUAGES = {
    'uk': '🇺🇦 Українська',
    'ro': '🇲🇩 Română',
    'en': '🇬🇧 English', 
    'de': '🇩🇪 Deutsch',
    'fr': '🇫🇷 Français',
    'es': '🇪🇸 Español',
    'it': '🇮🇹 Italiano',
    'pl': '🇵🇱 Polski',
    'ru': '🇷🇺 Русский'
}

TEXTS = {
    'uk': {
        # Главное меню
        'main_menu': '🏠 Головне меню',
        'welcome': 'Привіт, {name}!',
        'choose_action': '🎵 Оберіть дію:',
        'random_track': '🎲 Випадковий трек',
        'search_music': '🔍 Пошук музики',
        'top_charts': '📊 Топ чарти',
        'mood': '🎭 Настрій',
        'recommendations': '🎯 Рекомендації',
        'settings': '⚙️ Налаштування',
        
        # Настройки
        'settings_title': '⚙️ Налаштування',
        'current_language': 'Мова: {language}',
        'notifications': 'Сповіщення: {status}',
        'duration_filter': 'Фільтр за тривалістю: {filter}',
        'music_only': 'Тільки музика: {status}',
        'interface_theme': 'Тема: {theme}',
        'change_language': '🌐 Змінити мову',
        'duration_menu': '⏱️ Фільтр за тривалістю',
        'toggle_music': '🎵 Тільки музика',
        'back_to_settings': '🔙 Назад до налаштувань',
        'back_to_main': '🔙 В головне меню',
        
        # Фильтры длительности
        'duration_title': '⏱️ Фільтр за тривалістю',
        'choose_duration': 'Оберіть фільтр за тривалістю:',
        'no_filter': 'Без фільтру',
        'up_to_5min': 'До 5 хвилин',
        'up_to_10min': 'До 10 хвилин',
        'up_to_20min': 'До 20 хвилин',
        
        # Поиск
        'search_title': '🔍 Пошук музики',
        'enter_query': 'Введіть назву пісні або виконавця:',
        'search_results': '🔍 Результати за запитом:',
        'page': 'Сторінка {current} з {total}',
        'found': 'Знайдено: {count} результатів',
        'new_search': '🔍 Новий пошук',
        
        # Статусы
        'on': '✅ Вкл',
        'off': '❌ Викл',
        'dark_theme': '🌙 Темна',
        'light_theme': '☀️ Світла',
        
        # Уведомления
        'language_changed': '✅ Мову змінено!',
        'searching': '🔍 Шукаємо треки...',
        'downloading': '⬇️ Завантажуємо аудіо...',
        'processing': '🔄 Обробляємо файл...',
        'sending': '📤 Надсилаємо в Telegram...',
        'success': '✅ Готово!',
        'error': '❌ Помилка',
        
        # Чарты и рекомендации
        'charts_title': '📊 Топ чарти',
        'recommendations_title': '🎯 Ваші рекомендації',
        'mood_title': '🎭 Музика за настроєм',
        'loading_charts': '📊 Завантажую популярні треки...',
        'loading_recommendations': '🎯 Завантажую ваші рекомендації...',
        
        # Кнопки навигации
        'back': '⬅️ Назад',
        'next': 'Вперед ➡️',
        'refresh': '🔄 Оновити',
        'current_page': '{current}/{total}',
    },
    
    'ru': {
        # Главное меню
        'main_menu': '🏠 Главное меню',
        'welcome': 'Привет, {name}!',
        'choose_action': '🎵 Выберите действие:',
        'random_track': '🎲 Случайный трек',
        'search_music': '🔍 Поиск музыки',
        'top_charts': '📊 Топ чарты',
        'mood': '🎭 Настроение',
        'recommendations': '🎯 Рекомендации',
        'settings': '⚙️ Настройки',
        
        # Настройки
        'settings_title': '⚙️ Настройки',
        'current_language': 'Язык: {language}',
        'notifications': 'Уведомления: {status}',
        'duration_filter': 'Фильтр по длительности: {filter}',
        'music_only': 'Только музыка: {status}',
        'interface_theme': 'Тема: {theme}',
        'change_language': '🌐 Сменить язык',
        'duration_menu': '⏱️ Фильтр по длительности',
        'toggle_music': '🎵 Только музыка',
        'back_to_settings': '🔙 Назад к настройкам',
        'back_to_main': '🔙 В главное меню',
        
        # Фильтры длительности
        'duration_title': '⏱️ Фильтр по длительности',
        'choose_duration': 'Выберите фильтр по длительности:',
        'no_filter': 'Без фильтра',
        'up_to_5min': 'До 5 минут',
        'up_to_10min': 'До 10 минут',
        'up_to_20min': 'До 20 минут',
        
        # Поиск
        'search_title': '🔍 Поиск музыки',
        'enter_query': 'Введите название песни или исполнителя:',
        'search_results': '🔍 Результаты по запросу:',
        'page': 'Страница {current} из {total}',
        'found': 'Найдено: {count} результатов',
        'new_search': '🔍 Новый поиск',
        
        # Статусы
        'on': '✅ ВКЛ',
        'off': '❌ ВЫКЛ',
        'dark_theme': '🌙 Темная',
        'light_theme': '☀️ Светлая',
        
        # Уведомления
        'language_changed': '✅ Язык изменен!',
        'searching': '🔍 Ищем треки...',
        'downloading': '⬇️ Скачиваем аудио...',
        'processing': '🔄 Обрабатываем файл...',
        'sending': '📤 Отправляем в Telegram...',
        'success': '✅ Готово!',
        'error': '❌ Ошибка',
        
        # Чарты и рекомендации
        'charts_title': '📊 Топ чарты',
        'recommendations_title': '🎯 Ваши рекомендации',
        'mood_title': '🎭 Музыка по настроению',
        'loading_charts': '📊 Загружаю популярные треки...',
        'loading_recommendations': '🎯 Загружаю ваши рекомендации...',
        
        # Кнопки навигации
        'back': '⬅️ Назад',
        'next': 'Вперед ➡️',
        'refresh': '🔄 Обновить',
        'current_page': '{current}/{total}',
    },
    
    'en': {
        # Главное меню
        'main_menu': '🏠 Main Menu',
        'welcome': 'Hello, {name}!',
        'choose_action': '🎵 Choose action:',
        'random_track': '🎲 Random Track',
        'search_music': '🔍 Search Music',
        'top_charts': '📊 Top Charts',
        'mood': '🎭 Mood',
        'recommendations': '🎯 Recommendations',
        'settings': '⚙️ Settings',
        
        # Настройки
        'settings_title': '⚙️ Settings',
        'current_language': 'Language: {language}',
        'notifications': 'Notifications: {status}',
        'duration_filter': 'Duration filter: {filter}',
        'music_only': 'Music only: {status}',
        'interface_theme': 'Theme: {theme}',
        'change_language': '🌐 Change language',
        'duration_menu': '⏱️ Duration filter',
        'toggle_music': '🎵 Music only',
        'back_to_settings': '🔙 Back to settings',
        'back_to_main': '🔙 Back to main menu',
        
        # Фильтры длительности
        'duration_title': '⏱️ Duration Filter',
        'choose_duration': 'Choose duration filter:',
        'no_filter': 'No filter',
        'up_to_5min': 'Up to 5 minutes',
        'up_to_10min': 'Up to 10 minutes',
        'up_to_20min': 'Up to 20 minutes',
        
        # Поиск
        'search_title': '🔍 Search Music',
        'enter_query': 'Enter song name or artist:',
        'search_results': '🔍 Results for query:',
        'page': 'Page {current} of {total}',
        'found': 'Found: {count} results',
        'new_search': '🔍 New search',
        
        # Статусы
        'on': '✅ ON',
        'off': '❌ OFF',
        'dark_theme': '🌙 Dark',
        'light_theme': '☀️ Light',
        
        # Уведомления
        'language_changed': '✅ Language changed!',
        'searching': '🔍 Searching tracks...',
        'downloading': '⬇️ Downloading audio...',
        'processing': '🔄 Processing file...',
        'sending': '📤 Sending to Telegram...',
        'success': '✅ Ready!',
        'error': '❌ Error',
        
        # Чарты и рекомендации
        'charts_title': '📊 Top Charts',
        'recommendations_title': '🎯 Your Recommendations',
        'mood_title': '🎭 Music by Mood',
        'loading_charts': '📊 Loading popular tracks...',
        'loading_recommendations': '🎯 Loading your recommendations...',
        
        # Кнопки навигации
        'back': '⬅️ Back',
        'next': 'Next ➡️',
        'refresh': '🔄 Refresh',
        'current_page': '{current}/{total}',
    }
}

# Для остальных языков можно добавить позже, пока используем эти три
for lang in ['ro', 'de', 'fr', 'es', 'it', 'pl']:
    TEXTS[lang] = TEXTS['en']  # Временно используем английский как базовый
