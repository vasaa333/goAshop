#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель для управления товарами, городами, районами и товарными единицами
"""

import os
import sqlite3
import base64
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id == ADMIN_ID


def encrypt_data(data: str) -> str:
    """Шифрование данных"""
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def register_admin_handlers(bot, user_states, user_data):
    """Регистрация всех обработчиков админ-панели"""
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
    def admin_panel_callback(call):
        """Главное меню админ-панели"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "⚙️ Админ-панель")
        
        # Получаем статистику
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        pending_orders = cursor.fetchone()[0]
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            types.InlineKeyboardButton("🛒 Управление товарами", callback_data="admin_products_menu")
        )
        markup.add(
            types.InlineKeyboardButton("📦 Заказы", callback_data="admin_orders"),
            types.InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
        )
        markup.add(
            types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")
        )
        markup.add(
            types.InlineKeyboardButton("📜 Логи", callback_data="admin_logs"),
            types.InlineKeyboardButton("◀️ Назад", callback_data="start")
        )
        
        text = (
            "⚙️ <b>Админ-панель</b>\n\n"
            f"👥 Пользователей: {users_count}\n"
            f"⏳ Заказов на подтверждении: {pending_orders}\n\n"
            "Выберите раздел:"
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    # ========== ПОДМЕНЮ: УПРАВЛЕНИЕ ТОВАРАМИ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_products_menu")
    def admin_products_menu_callback(call):
        """Подменю управления товарами"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "🛒 Управление товарами")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product"),
            types.InlineKeyboardButton("➕ Добавить город", callback_data="admin_add_city")
        )
        markup.add(
            types.InlineKeyboardButton("➕ Добавить район", callback_data="admin_add_district"),
            types.InlineKeyboardButton("📦 Пополнить склад", callback_data="admin_add_inventory")
        )
        markup.add(
            types.InlineKeyboardButton("📋 Список товаров", callback_data="admin_list_products"),
            types.InlineKeyboardButton("🌆 Список городов", callback_data="admin_list_cities")
        )
        markup.add(
            types.InlineKeyboardButton("🏘 Список районов", callback_data="admin_list_districts"),
            types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🛒 <b>Управление товарами</b>\n\n"
                 "Здесь вы можете:\n"
                 "• Добавлять новые товары\n"
                 "• Управлять городами и районами\n"
                 "• Пополнять склад товарами\n"
                 "• Просматривать списки\n\n"
                 "Выберите действие:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    # ========== ДОБАВЛЕНИЕ ТОВАРА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_product")
    def admin_add_product_callback(call):
        """Начало добавления товара"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "➕ Добавление товара")
        user_states[call.from_user.id] = "awaiting_product_name"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="➕ <b>Добавление нового товара</b>\n\n"
                 "Введите название товара:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_product_name")
    def process_product_name(message):
        """Обработка названия товара"""
        if not is_admin(message.from_user.id):
            return
        
        product_name = message.text.strip()
        
        if not product_name:
            bot.send_message(message.chat.id, "❌ Название товара не может быть пустым. Попробуйте еще раз.")
            return
        
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products (name) VALUES (?)", (product_name,))
            conn.commit()
            conn.close()
            
            user_states.pop(message.from_user.id, None)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("➕ Добавить еще", callback_data="admin_add_product"),
                types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ <b>Товар успешно добавлен!</b>\n\n"
                f"📦 Название: {product_name}",
                parse_mode='HTML',
                reply_markup=markup
            )
        except sqlite3.IntegrityError:
            bot.send_message(
                message.chat.id,
                f"❌ Товар с названием '{product_name}' уже существует!",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
                )
            )
            user_states.pop(message.from_user.id, None)
    
    # ========== ДОБАВЛЕНИЕ ГОРОДА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_city")
    def admin_add_city_callback(call):
        """Начало добавления города"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "➕ Добавление города")
        user_states[call.from_user.id] = "awaiting_city_name"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="➕ <b>Добавление нового города</b>\n\n"
                 "Введите название города:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_city_name")
    def process_city_name(message):
        """Обработка названия города"""
        if not is_admin(message.from_user.id):
            return
        
        city_name = message.text.strip()
        
        if not city_name:
            bot.send_message(message.chat.id, "❌ Название города не может быть пустым. Попробуйте еще раз.")
            return
        
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO cities (name) VALUES (?)", (city_name,))
            conn.commit()
            conn.close()
            
            user_states.pop(message.from_user.id, None)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("➕ Добавить еще", callback_data="admin_add_city"),
                types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ <b>Город успешно добавлен!</b>\n\n"
                f"🌆 Название: {city_name}",
                parse_mode='HTML',
                reply_markup=markup
            )
        except sqlite3.IntegrityError:
            bot.send_message(
                message.chat.id,
                f"❌ Город с названием '{city_name}' уже существует!",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
                )
            )
            user_states.pop(message.from_user.id, None)
    
    # ========== ДОБАВЛЕНИЕ РАЙОНА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_district")
    def admin_add_district_callback(call):
        """Начало добавления района - выбор города"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM cities ORDER BY name")
        cities = cursor.fetchall()
        conn.close()
        
        if not cities:
            bot.answer_callback_query(call.id, "❌ Сначала добавьте города!", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "➕ Добавление района")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for city_id, city_name in cities:
            markup.add(
                types.InlineKeyboardButton(
                    city_name,
                    callback_data=f"admin_district_city_{city_id}"
                )
            )
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="➕ <b>Добавление нового района</b>\n\n"
                 "Шаг 1/2: Выберите город:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_district_city_"))
    def admin_district_city_selected(call):
        """Выбран город для района"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        city_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM cities WHERE id = ?", (city_id,))
        city = cursor.fetchone()
        conn.close()
        
        if not city:
            bot.answer_callback_query(call.id, "❌ Город не найден", show_alert=True)
            return
        
        city_name = city[0]
        user_data[call.from_user.id] = {"district_city_id": city_id, "district_city_name": city_name}
        user_states[call.from_user.id] = "awaiting_district_name"
        
        bot.answer_callback_query(call.id, f"Город: {city_name}")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"➕ <b>Добавление нового района</b>\n\n"
                 f"🌆 Город: {city_name}\n\n"
                 f"Шаг 2/2: Введите название района:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_district_name")
    def process_district_name(message):
        """Обработка названия района"""
        if not is_admin(message.from_user.id):
            return
        
        district_name = message.text.strip()
        
        if not district_name:
            bot.send_message(message.chat.id, "❌ Название района не может быть пустым. Попробуйте еще раз.")
            return
        
        data = user_data.get(message.from_user.id, {})
        city_id = data.get("district_city_id")
        city_name = data.get("district_city_name")
        
        if not city_id:
            bot.send_message(message.chat.id, "❌ Ошибка: город не выбран")
            user_states.pop(message.from_user.id, None)
            user_data.pop(message.from_user.id, None)
            return
        
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO districts (city_id, name) VALUES (?, ?)", (city_id, district_name))
            conn.commit()
            conn.close()
            
            user_states.pop(message.from_user.id, None)
            user_data.pop(message.from_user.id, None)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("➕ Добавить еще", callback_data="admin_add_district"),
                types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ <b>Район успешно добавлен!</b>\n\n"
                f"🌆 Город: {city_name}\n"
                f"🏘 Район: {district_name}",
                parse_mode='HTML',
                reply_markup=markup
            )
        except sqlite3.IntegrityError:
            bot.send_message(
                message.chat.id,
                f"❌ Район '{district_name}' уже существует в городе '{city_name}'!",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
                )
            )
            user_states.pop(message.from_user.id, None)
            user_data.pop(message.from_user.id, None)
    
    # ========== ПОПОЛНЕНИЕ СКЛАДА (ПОШАГОВЫЙ ПРОЦЕСС) ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_inventory")
    def admin_add_inventory_callback(call):
        """Шаг 1: Выбор товара для пополнения"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            bot.answer_callback_query(call.id, "❌ Сначала добавьте товары!", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "📦 Пополнение склада")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for product_id, product_name in products:
            markup.add(
                types.InlineKeyboardButton(
                    product_name,
                    callback_data=f"inv_product_{product_id}"
                )
            )
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📦 <b>Пополнение склада</b>\n\n"
                 "Шаг 1/5: Выберите товар:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_product_"))
    def inventory_product_selected(call):
        """Товар выбран, запрос веса и цены"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        product_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            bot.answer_callback_query(call.id, "❌ Товар не найден", show_alert=True)
            return
        
        product_name = product[0]
        user_data[call.from_user.id] = {"inv_product_id": product_id, "inv_product_name": product_name}
        user_states[call.from_user.id] = "awaiting_inventory_weight_price"
        
        bot.answer_callback_query(call.id, f"Товар: {product_name}")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📦 <b>Пополнение склада</b>\n\n"
                 f"Товар: {product_name}\n\n"
                 f"Шаг 2/5: Введите количество в граммах и цену в рублях через разделитель '|'\n\n"
                 f"Пример: 100|5000\n"
                 f"(100 грамм за 5000 рублей)",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_inventory_weight_price")
    def process_inventory_weight_price(message):
        """Обработка веса и цены"""
        if not is_admin(message.from_user.id):
            return
        
        text = message.text.strip()
        
        if '|' not in text:
            bot.send_message(
                message.chat.id,
                "❌ Неверный формат! Используйте формат: вес_в_граммах|цена_в_рублях\n"
                "Пример: 100|5000"
            )
            return
        
        try:
            weight_str, price_str = text.split('|', 1)
            
            # Поддержка десятичных количеств - заменяем запятую на точку
            weight_str = weight_str.strip().replace(',', '.')
            weight = float(weight_str)
            price_rub = int(price_str.strip())
            
            if weight <= 0 or price_rub <= 0:
                raise ValueError("Значения должны быть положительными")
            
            # Сохраняем вес как есть (может быть 0.25, 0.5, 100 и т.д.)
            data = user_data.get(message.from_user.id, {})
            data['inv_weight'] = weight
            data['inv_price'] = price_rub
            user_data[message.from_user.id] = data
            
            # Переход к выбору города
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM cities ORDER BY name")
            cities = cursor.fetchall()
            conn.close()
            
            if not cities:
                bot.send_message(
                    message.chat.id,
                    "❌ В базе нет городов! Сначала добавьте города.",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
                    )
                )
                user_states.pop(message.from_user.id, None)
                user_data.pop(message.from_user.id, None)
                return
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            for city_id, city_name in cities:
                markup.add(
                    types.InlineKeyboardButton(
                        city_name,
                        callback_data=f"inv_city_{city_id}"
                    )
                )
            markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
            
            bot.send_message(
                message.chat.id,
                f"📦 <b>Пополнение склада</b>\n\n"
                f"Товар: {data.get('inv_product_name')}\n"
                f"Вес: {weight} грамм\n"
                f"Цена: {price_rub} руб.\n\n"
                f"Шаг 3/5: Выберите город:",
                parse_mode='HTML',
                reply_markup=markup
            )
            
            user_states[message.from_user.id] = "inventory_selecting_city"
            
        except (ValueError, IndexError):
            bot.send_message(
                message.chat.id,
                "❌ Неверный формат! Введите целые числа через разделитель '|'\n"
                "Пример: 100|5000"
            )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_city_") and user_states.get(call.from_user.id) == "inventory_selecting_city")
    def inventory_city_selected(call):
        """Город выбран, выбор района"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        city_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM cities WHERE id = ?", (city_id,))
        city = cursor.fetchone()
        
        if not city:
            bot.answer_callback_query(call.id, "❌ Город не найден", show_alert=True)
            conn.close()
            return
        
        city_name = city[0]
        
        cursor.execute("SELECT id, name FROM districts WHERE city_id = ? ORDER BY name", (city_id,))
        districts = cursor.fetchall()
        conn.close()
        
        if not districts:
            bot.answer_callback_query(call.id, "❌ В этом городе нет районов!", show_alert=True)
            return
        
        data = user_data.get(call.from_user.id, {})
        data['inv_city_id'] = city_id
        data['inv_city_name'] = city_name
        user_data[call.from_user.id] = data
        
        bot.answer_callback_query(call.id, f"Город: {city_name}")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for district_id, district_name in districts:
            markup.add(
                types.InlineKeyboardButton(
                    district_name,
                    callback_data=f"inv_district_{district_id}"
                )
            )
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📦 <b>Пополнение склада</b>\n\n"
                 f"Товар: {data.get('inv_product_name')}\n"
                 f"Вес: {data.get('inv_weight')} грамм\n"
                 f"Цена: {data.get('inv_price')} руб.\n"
                 f"Город: {city_name}\n\n"
                 f"Шаг 4/5: Выберите район:",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        user_states[call.from_user.id] = "inventory_selecting_district"
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_district_") and user_states.get(call.from_user.id) == "inventory_selecting_district")
    def inventory_district_selected(call):
        """Район выбран, запрос данных"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        district_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM districts WHERE id = ?", (district_id,))
        district = cursor.fetchone()
        conn.close()
        
        if not district:
            bot.answer_callback_query(call.id, "❌ Район не найден", show_alert=True)
            return
        
        district_name = district[0]
        
        data = user_data.get(call.from_user.id, {})
        data['inv_district_id'] = district_id
        data['inv_district_name'] = district_name
        user_data[call.from_user.id] = data
        
        bot.answer_callback_query(call.id, f"Район: {district_name}")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📦 <b>Пополнение склада</b>\n\n"
                 f"Товар: {data.get('inv_product_name')}\n"
                 f"Вес: {data.get('inv_weight')} грамм\n"
                 f"Цена: {data.get('inv_price')} руб.\n"
                 f"Город: {data.get('inv_city_name')}\n"
                 f"Район: {district_name}\n\n"
                 f"Шаг 5/5: Введите текстовые данные товара\n"
                 f"(координаты, описание местоположения и т.д.):",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        user_states[call.from_user.id] = "awaiting_inventory_data"
    
    @bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "awaiting_inventory_data")
    def process_inventory_data(message):
        """Обработка финальных данных и сохранение в БД"""
        if not is_admin(message.from_user.id):
            return
        
        inventory_data_text = message.text.strip()
        
        if not inventory_data_text:
            bot.send_message(message.chat.id, "❌ Данные не могут быть пустыми. Попробуйте еще раз.")
            return
        
        data = user_data.get(message.from_user.id, {})
        
        product_id = data.get('inv_product_id')
        product_name = data.get('inv_product_name')
        weight = data.get('inv_weight')
        price = data.get('inv_price')
        city_id = data.get('inv_city_id')
        city_name = data.get('inv_city_name')
        district_id = data.get('inv_district_id')
        district_name = data.get('inv_district_name')
        
        # Шифруем данные
        encrypted_data = encrypt_data(inventory_data_text)
        
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO inventory 
                   (product_id, city_id, district_id, weight_grams, price_rub, data_encrypted, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'available')""",
                (product_id, city_id, district_id, weight, price, encrypted_data)
            )
            inventory_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            user_states.pop(message.from_user.id, None)
            user_data.pop(message.from_user.id, None)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("➕ Добавить еще", callback_data="admin_add_inventory"),
                types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ <b>Товар успешно добавлен на склад!</b>\n\n"
                f"ID: #{inventory_id}\n"
                f"📦 Товар: {product_name}\n"
                f"⚖️ Вес: {weight} грамм\n"
                f"💰 Цена: {price} руб.\n"
                f"🌆 Город: {city_name}\n"
                f"🏘 Район: {district_name}\n"
                f"🔒 Данные зашифрованы",
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Ошибка при добавлении: {str(e)}",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel")
                )
            )
            user_states.pop(message.from_user.id, None)
            user_data.pop(message.from_user.id, None)
    
    # ========== СПИСКИ И СТАТИСТИКА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_list_products")
    def admin_list_products_callback(call):
        """Список всех товаров"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "📋 Список товаров")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            text = "📋 <b>Список товаров</b>\n\nТоваров пока нет."
        else:
            text = "📋 <b>Список товаров</b>\n\n"
            for i, (prod_id, name, created) in enumerate(products, 1):
                text += f"{i}. {name} (ID: {prod_id})\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_list_cities")
    def admin_list_cities_callback(call):
        """Список всех городов"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "🌆 Список городов")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM cities ORDER BY name")
        cities = cursor.fetchall()
        conn.close()
        
        if not cities:
            text = "🌆 <b>Список городов</b>\n\nГородов пока нет."
        else:
            text = "🌆 <b>Список городов</b>\n\n"
            for i, (city_id, name) in enumerate(cities, 1):
                text += f"{i}. {name} (ID: {city_id})\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_list_districts")
    def admin_list_districts_callback(call):
        """Список всех районов"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "🏘 Список районов")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id, d.name, c.name 
            FROM districts d
            JOIN cities c ON d.city_id = c.id
            ORDER BY c.name, d.name
        """)
        districts = cursor.fetchall()
        conn.close()
        
        if not districts:
            text = "🏘 <b>Список районов</b>\n\nРайонов пока нет."
        else:
            text = "🏘 <b>Список районов</b>\n\n"
            for i, (dist_id, dist_name, city_name) in enumerate(districts, 1):
                text += f"{i}. {city_name} - {dist_name} (ID: {dist_id})\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
    def admin_stats_callback(call):
        """Статистика"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "📊 Статистика")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM cities")
        cities_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM districts")
        districts_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory WHERE status = 'available'")
        available_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory WHERE status = 'sold'")
        sold_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = cursor.fetchone()[0]
        
        # Новая статистика по заказам
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        pending_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'confirmed'")
        confirmed_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'cancelled'")
        cancelled_orders = cursor.fetchone()[0]
        
        conn.close()
        
        text = (
            "📊 <b>Статистика</b>\n\n"
            f"📦 Товаров: {products_count}\n"
            f"🌆 Городов: {cities_count}\n"
            f"🏘 Районов: {districts_count}\n\n"
            f"✅ Доступно на складе: {available_count}\n"
            f"💰 Продано: {sold_count}\n"
            f"📋 Всего заказов: {orders_count}\n\n"
            f"<b>Заказы:</b>\n"
            f"⏳ Ожидают подтверждения: {pending_orders}\n"
            f"✅ Подтверждены: {confirmed_orders}\n"
            f"❌ Отменены: {cancelled_orders}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_panel"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    # ========== ОБРАБОТКА ПОДТВЕРЖДЕНИЯ/ОТКЛОНЕНИЯ ЗАКАЗОВ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_confirm_order_"))
    def admin_confirm_order_callback(call):
        """Админ подтверждает заказ"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        order_id = int(call.data.split("_")[-1])
        admin_id = call.from_user.id
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем данные заказа
        cursor.execute("""
            SELECT o.user_id, o.inventory_id, o.status, 
                   i.data_encrypted, p.name, i.weight_grams, i.price_rub
            FROM orders o
            JOIN inventory i ON o.inventory_id = i.id
            JOIN products p ON i.product_id = p.id
            WHERE o.id = ?
        """, (order_id,))
        
        order_data = cursor.fetchone()
        
        if not order_data:
            bot.answer_callback_query(call.id, "❌ Заказ не найден", show_alert=True)
            conn.close()
            return
        
        user_id, inv_id, status, encrypted_data, prod_name, weight, price = order_data
        
        if status != 'pending':
            bot.answer_callback_query(call.id, "❌ Заказ уже обработан", show_alert=True)
            conn.close()
            return
        
        # Обновляем статус заказа
        cursor.execute("""
            UPDATE orders
            SET status = 'confirmed', confirmed_by = ?, confirmed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (admin_id, order_id))
        
        # Обновляем статус товара
        cursor.execute("""
            UPDATE inventory
            SET status = 'sold', sold_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (inv_id,))
        
        # Обновляем статистику пользователя
        cursor.execute("""
            UPDATE users
            SET total_orders = total_orders + 1, total_spent = total_spent + ?
            WHERE user_id = ?
        """, (price, user_id))
        
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "✅ Заказ подтвержден!", show_alert=True)
        
        # Обновляем сообщение админа
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"✅ <b>Заказ #{order_id} подтвержден</b>\n\n"
                    f"Пользователь получил данные товара.",
            parse_mode='HTML'
        )
        
        # Расшифровываем данные
        decrypted_data = base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
        
        # Отправляем данные пользователю
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
            types.InlineKeyboardButton("⭐ Оставить отзыв", callback_data=f"leave_review_{order_id}"),
            types.InlineKeyboardButton("🏠 В главное меню", callback_data="start")
        )
        
        try:
            bot.send_message(
                user_id,
                f"✅ <b>Заказ #{order_id} подтвержден!</b>\n\n"
                f"Ваша оплата проверена и подтверждена.\n\n"
                f"📦 Товар: {prod_name}\n"
                f"⚖️ Вес: {weight}г\n"
                f"💰 Цена: {price}₽\n\n"
                f"📍 <b>Данные товара:</b>\n"
                f"<code>{decrypted_data}</code>\n\n"
                f"Спасибо за покупку! 🎉",
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"Ошибка отправки данных пользователю: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reject_order_"))
    def admin_reject_order_callback(call):
        """Админ отклоняет заказ - запрос причины"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        order_id = int(call.data.split("_")[-1])
        
        # Сохраняем состояние
        user_states[call.from_user.id] = f"awaiting_rejection_reason_{order_id}"
        
        bot.answer_callback_query(call.id, "✍️ Укажите причину отклонения")
        
        bot.send_message(
            call.message.chat.id,
            f"📝 <b>Отклонение заказа #{order_id}</b>\n\n"
            f"Пожалуйста, напишите причину отклонения заказа.\n"
            f"Это сообщение будет отправлено пользователю.",
            parse_mode='HTML'
        )
    
    @bot.message_handler(func=lambda m: user_states.get(m.from_user.id, "").startswith("awaiting_rejection_reason_"))
    def process_rejection_reason(message):
        """Обработка причины отклонения"""
        if not is_admin(message.from_user.id):
            return
        
        admin_id = message.from_user.id
        state = user_states.get(admin_id, "")
        order_id = int(state.split("_")[-1])
        reason = message.text.strip()
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем данные заказа
        cursor.execute("""
            SELECT user_id, inventory_id, status
            FROM orders
            WHERE id = ?
        """, (order_id,))
        
        order_data = cursor.fetchone()
        
        if not order_data:
            bot.send_message(message.chat.id, "❌ Заказ не найден")
            user_states.pop(admin_id, None)
            conn.close()
            return
        
        user_id, inv_id, status = order_data
        
        if status != 'pending':
            bot.send_message(message.chat.id, "❌ Заказ уже обработан")
            user_states.pop(admin_id, None)
            conn.close()
            return
        
        # Обновляем статус заказа
        cursor.execute("""
            UPDATE orders
            SET status = 'cancelled', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reason, order_id))
        
        # Возвращаем товар в available
        cursor.execute("""
            UPDATE inventory
            SET status = 'available', buyer_id = NULL
            WHERE id = ?
        """, (inv_id,))
        
        conn.commit()
        conn.close()
        
        user_states.pop(admin_id, None)
        
        bot.send_message(
            message.chat.id,
            f"✅ Заказ #{order_id} отклонен.\n\n"
            f"Пользователь получит уведомление с указанной причиной."
        )
        
        # Уведомляем пользователя
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🛍 К каталогу", callback_data="catalog"),
            types.InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="create_ticket"),
            types.InlineKeyboardButton("🏠 В главное меню", callback_data="start")
        )
        
        try:
            bot.send_message(
                user_id,
                f"❌ <b>Заказ #{order_id} отклонен</b>\n\n"
                f"К сожалению, ваша оплата не была подтверждена.\n\n"
                f"<b>Причина:</b>\n{reason}\n\n"
                f"Если у вас есть вопросы, обратитесь в поддержку.",
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления пользователю: {e}")

    
    # ========== МОДЕРАЦИЯ ОТЗЫВОВ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("approve_review_") and is_admin(call.from_user.id))
    def approve_review_callback(call):
        """Одобрить отзыв"""
        review_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reviews
            SET is_approved = 1
            WHERE id = ?
        """, (review_id,))
        
        conn.commit()
        conn.close()
        
        bot.edit_message_text(
            f"✅ Отзыв #{review_id} одобрен и опубликован!",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id, "✅ Отзыв одобрен")
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("reject_review_") and is_admin(call.from_user.id))
    def reject_review_callback(call):
        """Отклонить отзыв"""
        review_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM reviews
            WHERE id = ?
        """, (review_id,))
        
        conn.commit()
        conn.close()
        
        bot.edit_message_text(
            f"❌ Отзыв #{review_id} отклонён и удалён.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id, "❌ Отзыв отклонён")
