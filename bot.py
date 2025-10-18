import os
import telebot
import time
import logging
import sqlite3
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
logger.info("✅ Бот инициализирован")

# ========== БАЗА ДАННЫХ ==========

def init_database():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect('events_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                step TEXT DEFAULT 'start',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

def get_user_step(user_id):
    """Получить шаг пользователя"""
    try:
        conn = sqlite3.connect('events_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT step FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 'start'
    except Exception as e:
        logger.error(f"❌ Ошибка получения шага: {e}")
        return 'start'

def create_or_update_user(user_id, username, first_name, step='start'):
    """Создать или обновить пользователя"""
    try:
        conn = sqlite3.connect('events_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        
        # Проверяем существование пользователя
        cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Обновляем существующего
            cursor.execute(
                'UPDATE users SET username=?, first_name=?, step=? WHERE user_id=?',
                (username, first_name, step, user_id)
            )
            logger.info(f"🔄 Пользователь {user_id} обновлен")
        else:
            # Создаем нового
            cursor.execute(
                'INSERT INTO users (user_id, username, first_name, step) VALUES (?, ?, ?, ?)',
                (user_id, username, first_name, step)
            )
            logger.info(f"👤 Создан пользователь {user_id}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка создания пользователя: {e}")
        return False

def save_application(user_id, event_info):
    """Сохранить заявку"""
    try:
        conn = sqlite3.connect('events_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO applications (user_id, event_info) VALUES (?, ?)',
            (user_id, event_info)
        )
        conn.commit()
        conn.close()
        logger.info(f"✅ Заявка сохранена для {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения заявки: {e}")
        return False

def update_user_step(user_id, step):
    """Обновить шаг пользователя"""
    try:
        conn = sqlite3.connect('events_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET step = ? WHERE user_id = ?',
            (step, user_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"🔄 Шаг пользователя {user_id} изменен на: {step}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления шага: {e}")
        return False

# Инициализируем БД
init_database()

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    logger.info(f"👤 Команда /start от {user_id}")
    
    if create_or_update_user(user_id, username, first_name, 'awaiting_info'):
        welcome_text = (
            f"🎉 Здравствуйте, {first_name}!\n\n"
            "Спасибо, что обратились в Event Agency 'CONCEPT'. Чтобы наши менеджеры смогли дать наиболее точный ответ, поделитесь, пожалуйста, следующей информацией:\n\n"
            "• Тип события (день рождения, свадьба и т.д.)\n"
            "• Дата проведения мероприятия\n"
            "• Место проведения\n"
            "• Примерное количество гостей\n"
            "• Контактный номер телефона\n\n"
            "Ждем ваших ответов! 🎊\n"
            "Свяжемся с Вами в ближайшее время!"
        )
        
        bot.send_message(message.chat.id, welcome_text)
        logger.info(f"✅ Приветствие отправлено {user_id}")
    else:
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка. Попробуйте еще раз."
        )

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "📋 Доступные команды:\n"
        "/start - начать общение\n"
        "/help - помощь\n\n"
        "Отправьте информацию о мероприятии после /start"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['status'])
def handle_status(message):
    user_id = message.from_user.id
    step = get_user_step(user_id)
    
    if step == 'info_received':
        status_text = "✅ Вы предоставили информацию. Менеджер свяжется с вами!"
    elif step == 'awaiting_info':
        status_text = "⏳ Ждем информацию о вашем мероприятии."
    else:
        status_text = "💡 Используйте /start для начала."
    
    bot.send_message(message.chat.id, status_text)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    user_text = message.text
    
    # Пропускаем команды
    if user_text and user_text.startswith('/'):
        return
    
    logger.info(f"📩 Сообщение от {user_id}: {user_text[:50] if user_text else 'None'}...")
    
    current_step = get_user_step(user_id)
    
    if current_step == 'awaiting_info':
        # Сохраняем заявку
        if save_application(user_id, user_text or "No text provided"):
            # Обновляем шаг
            if update_user_step(user_id, 'info_received'):
                gratitude_text = (
                    "✅ Спасибо за предоставленную информацию!\n\n"
                    "В ближайшее время к работе с Вами подключится наш менеджер. "
                    "Мы ценим сотрудничество с Вами и готовы ответить на любые вопросы."
                )
                bot.send_message(message.chat.id, gratitude_text)
                logger.info(f"✅ Благодарность отправлена {user_id}")
            else:
                bot.send_message(message.chat.id, "⚠️ Ошибка обновления статуса.")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка сохранения информации.")
    else:
        response_text = (
            f"🔊 Вы написали: {user_text}\n\n"
            "💡 Используйте /start для оформления заявки"
        )
        bot.send_message(message.chat.id, response_text)

def run_bot():
    """Запуск бота с обработкой ошибок и удалением вебхука"""
    logger.info("🚀 Запуск бота...")
    
    # Удаляем вебхук перед запуском поллинга
    try:
        logger.info("🗑️ Удаляем активный вебхук...")
        bot.remove_webhook()
        time.sleep(1)  # Даем время на удаление вебхука
        logger.info("✅ Вебхук удален")
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении вебхука: {e}")
    
    while True:
        try:
            logger.info("🔄 Запускаем polling...")
            bot.polling(
                none_stop=True,
                timeout=60,
                long_polling_timeout=60,
                interval=0
            )
        except Exception as e:
            logger.error(f"❌ Ошибка polling: {e}")
            logger.info("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == '__main__':
    run_bot()