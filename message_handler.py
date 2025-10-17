#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики сообщений пользователей - процесс покупки товаров
"""

import os
import sqlite3
import base64
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')


def decrypt_data(encrypted_data: str) -> str:
    """Расшифровка данных"""
    return base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')


def register_user_handlers(bot, user_states, user_data):
    """Регистрация всех обработчиков для пользователей"""
    
    # ========== КАТАЛОГ ТОВАРОВ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "catalog")
    def catalog_callback(call):
        """Отображение каталога товаров"""
        bot.answer_callback_query(call.id, "🛍 Каталог товаров")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем товары, у которых есть доступные единицы на складе
        cursor.execute("""
            SELECT DISTINCT p.id, p.name, COUNT(i.id) as count
            FROM products p
            LEFT JOIN inventory i ON p.id = i.product_id AND i.status = 'available'
            GROUP BY p.id, p.name
            HAVING count > 0
            ORDER BY p.name
        """)
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="start"))
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🛍 <b>Каталог товаров</b>\n\n"
                     "К сожалению, сейчас нет товаров в наличии.\n"
                     "Попробуйте зайти позже.",
                parse_mode='HTML',
                reply_markup=markup
            )
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for product_id, product_name, count in products:
            markup.add(
                types.InlineKeyboardButton(
                    f"{product_name} ({count} шт.)",
                    callback_data=f"buy_product_{product_id}"
                )
            )
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🛍 <b>Каталог товаров</b>\n\n"
                 "Выберите товар:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    # ========== ПРОЦЕСС ПОКУПКИ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_product_"))
    def buy_product_callback(call):
        """Шаг 1: Выбор товара - показать города"""
        product_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем название товара
        cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            bot.answer_callback_query(call.id, "❌ Товар не найден", show_alert=True)
            conn.close()
            return
        
        product_name = product[0]
        
        # Получаем города, где доступен этот товар
        cursor.execute("""
            SELECT DISTINCT c.id, c.name, COUNT(i.id) as count
            FROM cities c
            JOIN inventory i ON c.id = i.city_id
            WHERE i.product_id = ? AND i.status = 'available'
            GROUP BY c.id, c.name
            ORDER BY c.name
        """, (product_id,))
        cities = cursor.fetchall()
        conn.close()
        
        if not cities:
            bot.answer_callback_query(call.id, "❌ Этот товар сейчас недоступен", show_alert=True)
            return
        
        # Сохраняем данные пользователя
        user_data[call.from_user.id] = {
            "buy_product_id": product_id,
            "buy_product_name": product_name
        }
        
        bot.answer_callback_query(call.id, f"Товар: {product_name}")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for city_id, city_name, count in cities:
            markup.add(
                types.InlineKeyboardButton(
                    f"{city_name} ({count} шт.)",
                    callback_data=f"buy_city_{city_id}"
                )
            )
        markup.add(
            types.InlineKeyboardButton("◀️ К каталогу", callback_data="catalog")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🛍 <b>Покупка товара</b>\n\n"
                 f"📦 Товар: {product_name}\n\n"
                 f"Шаг 1/3: Выберите город:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_city_"))
    def buy_city_callback(call):
        """Шаг 2: Выбор города - показать районы"""
        city_id = int(call.data.split("_")[-1])
        
        data = user_data.get(call.from_user.id, {})
        product_id = data.get("buy_product_id")
        product_name = data.get("buy_product_name")
        
        if not product_id:
            bot.answer_callback_query(call.id, "❌ Ошибка: товар не выбран", show_alert=True)
            return
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем название города
        cursor.execute("SELECT name FROM cities WHERE id = ?", (city_id,))
        city = cursor.fetchone()
        
        if not city:
            bot.answer_callback_query(call.id, "❌ Город не найден", show_alert=True)
            conn.close()
            return
        
        city_name = city[0]
        
        # Получаем районы, где доступен товар
        cursor.execute("""
            SELECT DISTINCT d.id, d.name, COUNT(i.id) as count
            FROM districts d
            JOIN inventory i ON d.id = i.district_id
            WHERE i.product_id = ? AND i.city_id = ? AND i.status = 'available'
            GROUP BY d.id, d.name
            ORDER BY d.name
        """, (product_id, city_id))
        districts = cursor.fetchall()
        conn.close()
        
        if not districts:
            bot.answer_callback_query(call.id, "❌ В этом городе товар недоступен", show_alert=True)
            return
        
        # Сохраняем выбор
        data["buy_city_id"] = city_id
        data["buy_city_name"] = city_name
        user_data[call.from_user.id] = data
        
        bot.answer_callback_query(call.id, f"Город: {city_name}")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for district_id, district_name, count in districts:
            markup.add(
                types.InlineKeyboardButton(
                    f"{district_name} ({count} шт.)",
                    callback_data=f"buy_district_{district_id}"
                )
            )
        markup.add(
            types.InlineKeyboardButton("◀️ К выбору города", callback_data=f"buy_product_{product_id}")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🛍 <b>Покупка товара</b>\n\n"
                 f"📦 Товар: {product_name}\n"
                 f"🌆 Город: {city_name}\n\n"
                 f"Шаг 2/3: Выберите район:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_district_"))
    def buy_district_callback(call):
        """Шаг 3: Выбор района - показать доступные товары с группировкой"""
        district_id = int(call.data.split("_")[-1])
        
        data = user_data.get(call.from_user.id, {})
        product_id = data.get("buy_product_id")
        product_name = data.get("buy_product_name")
        city_id = data.get("buy_city_id")
        city_name = data.get("buy_city_name")
        
        if not product_id or not city_id:
            bot.answer_callback_query(call.id, "❌ Ошибка: данные не найдены", show_alert=True)
            return
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем название района
        cursor.execute("SELECT name FROM districts WHERE id = ?", (district_id,))
        district = cursor.fetchone()
        
        if not district:
            bot.answer_callback_query(call.id, "❌ Район не найден", show_alert=True)
            conn.close()
            return
        
        district_name = district[0]
        
        # Получаем доступные товары в этом районе С ГРУППИРОВКОЙ
        cursor.execute("""
            SELECT weight_grams, price_rub, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM inventory
            WHERE product_id = ? AND city_id = ? AND district_id = ? AND status = 'available'
            GROUP BY weight_grams, price_rub
            ORDER BY price_rub ASC
        """, (product_id, city_id, district_id))
        items = cursor.fetchall()
        conn.close()
        
        if not items:
            bot.answer_callback_query(call.id, "❌ В этом районе товар недоступен", show_alert=True)
            return
        
        # Сохраняем выбор
        data["buy_district_id"] = district_id
        data["buy_district_name"] = district_name
        user_data[call.from_user.id] = data
        
        bot.answer_callback_query(call.id, f"Район: {district_name}")
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for weight, price, ids, count in items:
            # Берем первый ID из группы для покупки
            first_id = int(ids.split(',')[0])
            
            # Формируем текст кнопки с остатками
            button_text = f"⚖️ {weight}г - 💰 {price}₽"
            if count > 1:
                button_text += f" (в наличии: {count} шт.)"
            
            markup.add(
                types.InlineKeyboardButton(
                    button_text,
                    callback_data=f"buy_item_{first_id}"
                )
            )
        markup.add(
            types.InlineKeyboardButton("◀️ К выбору района", callback_data=f"buy_city_{city_id}")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🛍 <b>Покупка товара</b>\n\n"
                 f"📦 Товар: {product_name}\n"
                 f"🌆 Город: {city_name}\n"
                 f"🏘 Район: {district_name}\n\n"
                 f"Шаг 3/3: Выберите вес и цену:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_item_"))
    def buy_item_callback(call):
        """Финальный шаг: Подтверждение покупки"""
        item_id = int(call.data.split("_")[-1])
        
        data = user_data.get(call.from_user.id, {})
        product_name = data.get("buy_product_name")
        city_name = data.get("buy_city_name")
        district_name = data.get("buy_district_name")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем данные о товаре
        cursor.execute("""
            SELECT weight_grams, price_rub, status
            FROM inventory
            WHERE id = ?
        """, (item_id,))
        item = cursor.fetchone()
        
        if not item:
            bot.answer_callback_query(call.id, "❌ Товар не найден", show_alert=True)
            conn.close()
            return
        
        weight, price, status = item
        
        if status != 'available':
            bot.answer_callback_query(call.id, "❌ Товар уже продан", show_alert=True)
            conn.close()
            return
        
        conn.close()
        
        # Сохраняем ID товара для подтверждения
        data["buy_item_id"] = item_id
        data["buy_weight"] = weight
        data["buy_price"] = price
        user_data[call.from_user.id] = data
        
        bot.answer_callback_query(call.id, "✅ Проверьте данные")
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить покупку", callback_data=f"confirm_buy_{item_id}"),
            types.InlineKeyboardButton("◀️ Назад к выбору", callback_data=f"buy_district_{data.get('buy_district_id')}")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🛍 <b>Подтверждение покупки</b>\n\n"
                 f"📦 Товар: {product_name}\n"
                 f"🌆 Город: {city_name}\n"
                 f"🏘 Район: {district_name}\n"
                 f"⚖️ Вес: {weight} грамм\n"
                 f"💰 Цена: {price} рублей\n\n"
                 f"Подтвердите покупку:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_buy_"))
    def confirm_buy_callback(call):
        """Обработка подтверждения покупки - показываем инструкции по оплате"""
        item_id = int(call.data.split("_")[-1])
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name
        
        data = user_data.get(user_id, {})
        product_name = data.get("buy_product_name")
        city_name = data.get("buy_city_name")
        district_name = data.get("buy_district_name")
        weight = data.get("buy_weight")
        price = data.get("buy_price")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Проверяем, что товар еще доступен
        cursor.execute("SELECT status FROM inventory WHERE id = ?", (item_id,))
        result = cursor.fetchone()
        
        if not result:
            bot.answer_callback_query(call.id, "❌ Товар не найден", show_alert=True)
            conn.close()
            return
        
        status = result[0]
        
        if status != 'available':
            bot.answer_callback_query(call.id, "❌ Товар уже продан", show_alert=True)
            conn.close()
            return
        
        # Получаем инструкции по оплате
        cursor.execute("SELECT payment_instructions FROM bot_settings WHERE id = 1")
        settings = cursor.fetchone()
        payment_instructions = settings[0] if settings else "Реквизиты будут предоставлены администратором."
        
        conn.close()
        
        bot.answer_callback_query(call.id, "💳 Инструкции по оплате")
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("💰 Я оплатил", callback_data=f"payment_done_{item_id}"),
            types.InlineKeyboardButton("❌ Отменить покупку", callback_data=f"cancel_buy_{item_id}")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"💳 <b>Инструкции по оплате</b>\n\n"
                 f"📦 Товар: {product_name}\n"
                 f"🌆 Город: {city_name}\n"
                 f"🏘 Район: {district_name}\n"
                 f"⚖️ Вес: {weight} грамм\n"
                 f"💰 Цена: <b>{price} рублей</b>\n\n"
                 f"📋 <b>Реквизиты для оплаты:</b>\n"
                 f"{payment_instructions}\n\n"
                 f"⚠️ После оплаты нажмите кнопку 'Я оплатил' и отправьте скриншот квитанции.\n"
                 f"Ваш заказ будет проверен администратором.",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("payment_done_"))
    def payment_done_callback(call):
        """Пользователь нажал 'Я оплатил' - ожидаем скриншот"""
        item_id = int(call.data.split("_")[-1])
        user_id = call.from_user.id
        
        # Сохраняем состояние
        user_states[user_id] = f"awaiting_payment_proof_{item_id}"
        
        bot.answer_callback_query(call.id, "📷 Отправьте скриншот квитанции")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_buy_{item_id}"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📷 <b>Подтверждение оплаты</b>\n\n"
                 "Пожалуйста, отправьте скриншот квитанции об оплате.\n"
                 "Это может быть фото или скриншот из банковского приложения.\n\n"
                 "После отправки ваш заказ будет проверен администратором.",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.message_handler(content_types=['photo'], 
                        func=lambda m: user_states.get(m.from_user.id, "").startswith("awaiting_payment_proof_"))
    def process_payment_proof(message):
        """Обработка скриншота квитанции"""
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        first_name = message.from_user.first_name or "Пользователь"
        
        # Получаем item_id из состояния
        state = user_states.get(user_id, "")
        item_id = int(state.split("_")[-1])
        
        # Получаем file_id фото
        photo_file_id = message.photo[-1].file_id
        
        data = user_data.get(user_id, {})
        product_name = data.get("buy_product_name")
        city_name = data.get("buy_city_name")
        district_name = data.get("buy_district_name")
        weight = data.get("buy_weight")
        price = data.get("buy_price")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Проверяем, что товар еще доступен
        cursor.execute("SELECT status FROM inventory WHERE id = ?", (item_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != 'available':
            bot.send_message(
                message.chat.id,
                "❌ К сожалению, товар уже продан или недоступен."
            )
            user_states.pop(user_id, None)
            user_data.pop(user_id, None)
            conn.close()
            return
        
        # Резервируем товар
        cursor.execute("""
            UPDATE inventory
            SET status = 'reserved', buyer_id = ?
            WHERE id = ?
        """, (user_id, item_id))
        
        # Создаем заказ со статусом pending
        cursor.execute("""
            INSERT INTO orders (user_id, inventory_id, status, payment_proof)
            VALUES (?, ?, 'pending', ?)
        """, (user_id, item_id, photo_file_id))
        
        order_id = cursor.lastrowid
        
        # Регистрируем или обновляем пользователя
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_activity, registration_date)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                last_activity = CURRENT_TIMESTAMP
        """, (user_id, username, first_name))
        
        conn.commit()
        
        # Получаем данные товара для админа
        cursor.execute("""
            SELECT p.name, c.name, d.name, i.weight_grams, i.price_rub
            FROM inventory i
            JOIN products p ON i.product_id = p.id
            JOIN cities c ON i.city_id = c.id
            JOIN districts d ON i.district_id = d.id
            WHERE i.id = ?
        """, (item_id,))
        
        product_info = cursor.fetchone()
        conn.close()
        
        # Очищаем состояние
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        
        # Отправляем подтверждение пользователю с кнопкой отзыва
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⭐️ Оставить отзыв", callback_data=f"write_review_{order_id}"),
            types.InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
            types.InlineKeyboardButton("🏠 В главное меню", callback_data="start")
        )
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>Заказ #{order_id} создан!</b>\n\n"
            f"Ваш заказ отправлен на проверку администратору.\n"
            f"Вы получите уведомление после подтверждения оплаты.\n\n"
            f"📦 Товар: {product_name}\n"
            f"💰 Сумма: {price} руб.\n\n"
            f"⏳ Обычно проверка занимает 5-15 минут.",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        # Отправляем уведомление админу
        from bot import ADMIN_ID, bot as main_bot
        
        if product_info:
            prod_name, city, district, w, p = product_info
            
            admin_markup = types.InlineKeyboardMarkup(row_width=2)
            admin_markup.add(
                types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_order_{order_id}"),
                types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_order_{order_id}")
            )
            admin_markup.add(
                types.InlineKeyboardButton("👤 Профиль пользователя", callback_data=f"admin_user_profile_{user_id}")
            )
            
            try:
                main_bot.send_photo(
                    ADMIN_ID,
                    photo_file_id,
                    caption=f"🔔 <b>Новый заказ #{order_id}</b>\n\n"
                            f"👤 Пользователь: @{username if username else 'без username'} (ID: {user_id})\n"
                            f"📦 Товар: {prod_name}\n"
                            f"⚖️ Вес: {w}г\n"
                            f"💰 Цена: {p}₽\n"
                            f"🌆 Город: {city}\n"
                            f"🏘 Район: {district}\n\n"
                            f"📷 Скриншот квитанции выше ⬆️\n\n"
                            f"Проверьте оплату и подтвердите заказ:",
                    parse_mode='HTML',
                    reply_markup=admin_markup
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления админу: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_buy_"))
    def cancel_buy_callback(call):
        """Отмена покупки"""
        user_id = call.from_user.id
        
        # Очищаем состояние
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        
        bot.answer_callback_query(call.id, "❌ Покупка отменена")
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🛍 К каталогу", callback_data="catalog"),
            types.InlineKeyboardButton("🏠 В главное меню", callback_data="start")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ <b>Покупка отменена</b>\n\n"
                 "Вы можете вернуться к каталогу и выбрать другой товар.",
            parse_mode='HTML',
            reply_markup=markup
        )
