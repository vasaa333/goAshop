#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель: Управление заказами с пагинацией
"""

import os
import sqlite3
import base64
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
ORDERS_PER_PAGE = 5


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id == ADMIN_ID


def register_orders_handlers(bot, user_states, user_data):
    """Регистрация обработчиков управления заказами"""
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_orders")
    def admin_orders_menu(call):
        """Главное меню управления заказами"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "🛒 Управление заказами")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем статистику
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'confirmed'")
        confirmed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'cancelled'")
        cancelled = cursor.fetchone()[0]
        
        conn.close()
        
        text = (
            "🛒 <b>Управление заказами</b>\n\n"
            f"⏳ Ожидающие: {pending}\n"
            f"✅ Подтверждённые: {confirmed}\n"
            f"❌ Отменённые: {cancelled}\n\n"
            "Выберите категорию:"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"⏳ Ожидающие ({pending})", callback_data="admin_orders_list_pending_1"),
            types.InlineKeyboardButton(f"✅ Подтверждённые ({confirmed})", callback_data="admin_orders_list_confirmed_1"),
            types.InlineKeyboardButton(f"❌ Отменённые ({cancelled})", callback_data="admin_orders_list_cancelled_1"),
            types.InlineKeyboardButton("📋 Все заказы", callback_data="admin_orders_list_all_1"),
            types.InlineKeyboardButton("🔍 Поиск по номеру", callback_data="admin_order_search"),
            types.InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_orders_list_"))
    def admin_orders_list(call):
        """Список заказов с пагинацией"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        # Парсим: admin_orders_list_pending_1
        parts = call.data.split("_")
        status_filter = parts[3]  # pending/confirmed/cancelled/all
        page = int(parts[4]) if len(parts) > 4 else 1
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Строим запрос в зависимости от фильтра
        if status_filter == "all":
            query = """
                SELECT o.id, o.user_id, o.status, o.created_at, 
                       p.name, i.weight_grams, i.price_rub
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN products p ON i.product_id = p.id
                ORDER BY o.id DESC
                LIMIT ? OFFSET ?
            """
            count_query = "SELECT COUNT(*) FROM orders"
            cursor.execute(query, (ORDERS_PER_PAGE, (page - 1) * ORDERS_PER_PAGE))
        else:
            query = """
                SELECT o.id, o.user_id, o.status, o.created_at,
                       p.name, i.weight_grams, i.price_rub
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN products p ON i.product_id = p.id
                WHERE o.status = ?
                ORDER BY o.id DESC
                LIMIT ? OFFSET ?
            """
            count_query = "SELECT COUNT(*) FROM orders WHERE status = ?"
            cursor.execute(query, (status_filter, ORDERS_PER_PAGE, (page - 1) * ORDERS_PER_PAGE))
        
        orders = cursor.fetchall()
        
        # Получаем общее количество
        if status_filter == "all":
            cursor.execute(count_query)
        else:
            cursor.execute(count_query, (status_filter,))
        
        total_orders = cursor.fetchone()[0]
        conn.close()
        
        total_pages = (total_orders + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE
        
        # Заголовок в зависимости от фильтра
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "cancelled": "❌",
            "all": "📋"
        }
        status_names = {
            "pending": "Ожидающие",
            "confirmed": "Подтверждённые",
            "cancelled": "Отменённые",
            "all": "Все заказы"
        }
        
        text = f"{status_emoji.get(status_filter, '📋')} <b>{status_names.get(status_filter, 'Заказы')}</b>\n\n"
        
        if not orders:
            text += "Заказов не найдено.\n"
        else:
            text += f"Страница {page} из {total_pages}\n\n"
        
        bot.answer_callback_query(call.id, f"{status_names.get(status_filter, 'Заказы')}")
        
        # Строим кнопки с заказами
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for order_id, user_id, status, created_at, prod_name, weight, price in orders:
            status_icon = status_emoji.get(status, "📦")
            button_text = f"{status_icon} Заказ #{order_id} | {prod_name[:15]} | {price}₽"
            markup.add(
                types.InlineKeyboardButton(button_text, callback_data=f"admin_order_view_{order_id}")
            )
        
        # Навигация
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                types.InlineKeyboardButton("◀️ Назад", callback_data=f"admin_orders_list_{status_filter}_{page-1}")
            )
        if page < total_pages:
            nav_buttons.append(
                types.InlineKeyboardButton("Вперёд ▶️", callback_data=f"admin_orders_list_{status_filter}_{page+1}")
            )
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ К категориям", callback_data="admin_orders"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_order_view_"))
    def admin_order_view(call):
        """Детальный просмотр заказа"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        order_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем полную информацию о заказе
        cursor.execute("""
            SELECT o.id, o.user_id, o.status, o.created_at, o.updated_at,
                   o.payment_proof, o.confirmed_by, o.confirmed_at, o.rejection_reason,
                   p.name, i.weight_grams, i.price_rub, i.data_encrypted,
                   c.name, d.name,
                   u.username, u.first_name
            FROM orders o
            JOIN inventory i ON o.inventory_id = i.id
            JOIN products p ON i.product_id = p.id
            JOIN cities c ON i.city_id = c.id
            JOIN districts d ON i.district_id = d.id
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            bot.answer_callback_query(call.id, "❌ Заказ не найден", show_alert=True)
            return
        
        (oid, user_id, status, created_at, updated_at, payment_proof, confirmed_by, 
         confirmed_at, rejection_reason, prod_name, weight, price, encrypted_data,
         city, district, username, first_name) = order
        
        # Формируем сообщение
        status_emoji = {"pending": "⏳", "confirmed": "✅", "cancelled": "❌"}
        status_names = {"pending": "Ожидает подтверждения", "confirmed": "Подтверждён", "cancelled": "Отменён"}
        
        text = (
            f"📋 <b>Заказ #{oid}</b>\n\n"
            f"📊 Статус: {status_emoji.get(status, '❓')} {status_names.get(status, status)}\n\n"
            f"<b>Товар:</b>\n"
            f"├ 📦 Название: {prod_name}\n"
            f"├ ⚖️ Вес: {weight}г\n"
            f"├ 💰 Цена: {price}₽\n"
            f"├ 🌆 Город: {city}\n"
            f"└ 🏘 Район: {district}\n\n"
            f"<b>Покупатель:</b>\n"
            f"├ 👤 ID: {user_id}\n"
            f"├ 📛 Имя: {first_name or 'Не указано'}\n"
            f"└ 🔗 Username: @{username if username else 'нет'}\n\n"
            f"<b>Даты:</b>\n"
            f"├ 📅 Создан: {created_at[:19]}\n"
            f"└ 🔄 Обновлён: {updated_at[:19] if updated_at else '-'}\n"
        )
        
        if status == "confirmed" and confirmed_at:
            text += f"\n✅ Подтверждён: {confirmed_at[:19]}"
        
        if status == "cancelled" and rejection_reason:
            text += f"\n\n❌ <b>Причина отмены:</b>\n{rejection_reason}"
        
        # Кнопки действий
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        if status == "pending":
            markup.add(
                types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_order_{oid}"),
                types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_order_{oid}")
            )
        
        # Просмотр скриншота
        if payment_proof:
            markup.add(types.InlineKeyboardButton("📷 Скриншот оплаты", callback_data=f"admin_show_payment_{oid}"))
        
        # Просмотр зашифрованных данных
        markup.add(types.InlineKeyboardButton("🔒 Данные товара", callback_data=f"admin_show_data_{oid}"))
        
        # Профиль пользователя
        markup.add(types.InlineKeyboardButton("👤 Профиль пользователя", callback_data=f"admin_user_profile_{user_id}"))
        
        # Удалить заказ
        markup.add(types.InlineKeyboardButton("🗑 Удалить заказ", callback_data=f"admin_delete_order_{oid}"))
        
        markup.add(types.InlineKeyboardButton("◀️ К списку", callback_data=f"admin_orders_list_{status}_1"))
        
        bot.answer_callback_query(call.id, f"Заказ #{oid}")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_show_payment_"))
    def admin_show_payment(call):
        """Показать скриншот оплаты"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        order_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT payment_proof FROM orders WHERE id = ?", (order_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            bot.answer_callback_query(call.id, "❌ Скриншот не найден", show_alert=True)
            return
        
        payment_proof = result[0]
        
        bot.answer_callback_query(call.id, "📷 Показываю скриншот")
        
        try:
            bot.send_photo(
                call.message.chat.id,
                payment_proof,
                caption=f"📷 Скриншот оплаты для заказа #{order_id}"
            )
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Ошибка загрузки скриншота: {e}")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_show_data_"))
    def admin_show_data(call):
        """Показать зашифрованные данные товара"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        order_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.data_encrypted
            FROM orders o
            JOIN inventory i ON o.inventory_id = i.id
            WHERE o.id = ?
        """, (order_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            bot.answer_callback_query(call.id, "❌ Данные не найдены", show_alert=True)
            return
        
        encrypted_data = result[0]
        decrypted_data = base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
        
        bot.answer_callback_query(call.id, "🔓 Данные расшифрованы")
        
        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Данные товара для заказа #{order_id}:</b>\n\n"
            f"<code>{decrypted_data}</code>",
            parse_mode='HTML'
        )
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_order_search")
    def admin_order_search_start(call):
        """Начало поиска заказа по номеру"""
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Доступ запрещен", show_alert=True)
            return
        
        user_states[call.from_user.id] = "awaiting_order_search_id"
        
        bot.answer_callback_query(call.id, "🔍 Поиск заказа")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_orders"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔍 <b>Поиск заказа по номеру</b>\n\n"
                 "Введите номер заказа (ID):",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_order_search_id")
    def admin_order_search_process(message):
        """Обработка поиска заказа"""
        if not is_admin(message.from_user.id):
            return
        
        try:
            order_id = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введите корректный номер заказа (целое число)")
            return
        
        user_states.pop(message.from_user.id, None)
        
        # Проверяем существование заказа
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
        exists = cursor.fetchone()
        conn.close()
        
        if not exists:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_orders"))
            bot.send_message(
                message.chat.id,
                f"❌ Заказ #{order_id} не найден.",
                reply_markup=markup
            )
            return
        
        # Перенаправляем на просмотр заказа
        # Имитируем callback
        from types import SimpleNamespace
        fake_call = SimpleNamespace(
            from_user=message.from_user,
            message=message,
            id=message.message_id,
            data=f"admin_order_view_{order_id}"
        )
        
        # Отправляем сообщение с деталями заказа
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id, o.user_id, o.status, o.created_at, o.updated_at,
                   o.payment_proof, o.confirmed_by, o.confirmed_at, o.rejection_reason,
                   p.name, i.weight_grams, i.price_rub,
                   c.name, d.name,
                   u.username, u.first_name
            FROM orders o
            JOIN inventory i ON o.inventory_id = i.id
            JOIN products p ON i.product_id = p.id
            JOIN cities c ON i.city_id = c.id
            JOIN districts d ON i.district_id = d.id
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        conn.close()
        
        if order:
            (oid, user_id, status, created_at, updated_at, payment_proof, confirmed_by,
             confirmed_at, rejection_reason, prod_name, weight, price,
             city, district, username, first_name) = order
            
            status_emoji = {"pending": "⏳", "confirmed": "✅", "cancelled": "❌"}
            status_names = {"pending": "Ожидает подтверждения", "confirmed": "Подтверждён", "cancelled": "Отменён"}
            
            text = (
                f"📋 <b>Заказ #{oid}</b>\n\n"
                f"📊 Статус: {status_emoji.get(status, '❓')} {status_names.get(status, status)}\n\n"
                f"<b>Товар:</b>\n"
                f"├ 📦 Название: {prod_name}\n"
                f"├ ⚖️ Вес: {weight}г\n"
                f"├ 💰 Цена: {price}₽\n"
                f"├ 🌆 Город: {city}\n"
                f"└ 🏘 Район: {district}\n\n"
                f"<b>Покупатель:</b>\n"
                f"├ 👤 ID: {user_id}\n"
                f"├ 📛 Имя: {first_name or 'Не указано'}\n"
                f"└ 🔗 Username: @{username if username else 'нет'}\n\n"
                f"<b>Даты:</b>\n"
                f"├ 📅 Создан: {created_at[:19]}\n"
                f"└ 🔄 Обновлён: {updated_at[:19] if updated_at else '-'}\n"
            )
            
            if status == "confirmed" and confirmed_at:
                text += f"\n✅ Подтверждён: {confirmed_at[:19]}"
            
            if status == "cancelled" and rejection_reason:
                text += f"\n\n❌ <b>Причина отмены:</b>\n{rejection_reason}"
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            
            if status == "pending":
                markup.add(
                    types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_order_{oid}"),
                    types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_order_{oid}")
                )
            
            if payment_proof:
                markup.add(types.InlineKeyboardButton("📷 Скриншот оплаты", callback_data=f"admin_show_payment_{oid}"))
            
            markup.add(types.InlineKeyboardButton("🔒 Данные товара", callback_data=f"admin_show_data_{oid}"))
            markup.add(types.InlineKeyboardButton("👤 Профиль пользователя", callback_data=f"admin_user_profile_{user_id}"))
            markup.add(types.InlineKeyboardButton("◀️ К списку", callback_data="admin_orders"))
            
            bot.send_message(
                message.chat.id,
                text,
                parse_mode='HTML',
                reply_markup=markup
            )
