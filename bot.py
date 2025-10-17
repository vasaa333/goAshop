#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Shop Bot - Главный модуль
Бот для продажи цифровых товаров с админ-панелью
"""

import os
import sqlite3
import base64
import logging
from dotenv import load_dotenv
import telebot
from telebot import types

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
DATABASE = os.getenv('DATABASE', 'bot.db')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище временных данных пользователей
user_states = {}
user_data = {}


def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Таблица товаров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица городов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица районов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS districts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (city_id) REFERENCES cities(id),
            UNIQUE(city_id, name)
        )
    ''')
    
    # Таблица товарных единиц (клады)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            city_id INTEGER NOT NULL,
            district_id INTEGER NOT NULL,
            weight_grams INTEGER NOT NULL,
            price_rub INTEGER NOT NULL,
            data_encrypted TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sold_at TIMESTAMP,
            buyer_id INTEGER,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (city_id) REFERENCES cities(id),
            FOREIGN KEY (district_id) REFERENCES districts(id)
        )
    ''')
    
    # Таблица заказов (базовая версия, будет расширена миграцией)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            inventory_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inventory_id) REFERENCES inventory(id)
        )
    ''')
    
    # Индексы для быстрого поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_city ON inventory(city_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_district ON inventory(district_id)')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")
    
    # Запускаем миграции
    try:
        from db_migration import migrate_database
        migrate_database()
    except Exception as e:
        logger.warning(f"Миграция БД не выполнена (возможно уже применена): {e}")


def encrypt_data(data: str) -> str:
    """Простое шифрование данных (base64)"""
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def decrypt_data(encrypted_data: str) -> str:
    """Расшифровка данных"""
    return base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id == ADMIN_ID


# Импорт обработчиков
from admin_panel import register_admin_handlers
from admin_orders import register_orders_handlers
from message_handler import register_user_handlers
from user_menu import register_user_menu_handlers
from admin_users import register_admin_users_handlers
from admin_broadcast import register_admin_broadcast_handlers
from admin_settings import register_admin_settings_handlers
from admin_logs import register_admin_logs_handlers
import db_migration

# Регистрация обработчиков
register_admin_handlers(bot, user_states, user_data)
register_orders_handlers(bot, user_states, user_data)
register_user_handlers(bot, user_states, user_data)
register_user_menu_handlers(bot, user_states, user_data)
register_admin_users_handlers(bot, user_states, user_data)
register_admin_broadcast_handlers(bot, user_states, user_data)
register_admin_settings_handlers(bot, user_states, user_data)
register_admin_logs_handlers(bot, user_states, user_data)


@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    first_name = message.from_user.first_name or "Пользователь"
    
    logger.info(f"Пользователь {username} (ID: {user_id}) запустил бота")
    
    # Регистрируем пользователя в БД (если еще нет)
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registration_date)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (user_id, username, first_name, message.from_user.last_name or ""))
        conn.commit()
        conn.close()
    except:
        pass  # Таблица users может не существовать в старых БД
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if is_admin(user_id):
        markup.add(
            types.InlineKeyboardButton("🛍 Каталог", callback_data="catalog"),
            types.InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")
        )
        bot.send_message(
            message.chat.id,
            f"👋 Добро пожаловать, <b>Администратор</b>!\n\n"
            f"Выберите действие:",
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        markup.add(
            types.InlineKeyboardButton("🛍 Каталог", callback_data="catalog"),
            types.InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")
        )
        markup.add(
            types.InlineKeyboardButton("⭐️ Отзывы", callback_data="reviews")
        )
        markup.add(
            types.InlineKeyboardButton("ℹ️ Информация", callback_data="info")
        )
        bot.send_message(
            message.chat.id,
            f"👋 Добро пожаловать, <b>{first_name}</b>!\n\n"
            f"Я бот для покупки товаров.\n"
            f"Выберите действие:",
            parse_mode='HTML',
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data == "about")
def about_callback(call):
    """Информация о боте"""
    bot.answer_callback_query(call.id, "📖 Информация о боте")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="ℹ️ <b>О боте</b>\n\n"
             "Этот бот предназначен для покупки цифровых товаров.\n\n"
             "📋 <b>Как пользоваться:</b>\n"
             "1. Выберите товар из каталога\n"
             "2. Выберите город\n"
             "3. Выберите район\n"
             "4. Получите данные о товаре\n\n"
             "💰 Оплата производится согласно указанной цене.",
        parse_mode='HTML',
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("◀️ Назад", callback_data="start")
        )
    )


@bot.callback_query_handler(func=lambda call: call.data == "start")
def start_callback(call):
    """Возврат в главное меню"""
    bot.answer_callback_query(call.id, "🏠 Главное меню")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    user_id = call.from_user.id
    first_name = call.from_user.first_name or "Пользователь"
    
    if is_admin(user_id):
        markup.add(
            types.InlineKeyboardButton("🛍 Каталог", callback_data="catalog"),
            types.InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")
        )
        text = f"👋 <b>Администратор</b>\n\nВыберите действие:"
    else:
        markup.add(
            types.InlineKeyboardButton("🛍 Каталог", callback_data="catalog"),
            types.InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")
        )
        markup.add(
            types.InlineKeyboardButton("⭐️ Отзывы", callback_data="reviews")
        )
        markup.add(
            types.InlineKeyboardButton("ℹ️ Информация", callback_data="info")
        )
        text = f"👋 <b>{first_name}</b>\n\nВыберите действие:"
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=markup
    )


def main():
    """Главная функция запуска бота"""
    logger.info("Запуск бота...")
    
    # Инициализация базы данных
    init_database()
    
    # Запуск бота
    logger.info("Бот успешно запущен!")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == '__main__':
    main()
