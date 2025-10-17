#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель: Управление пользователями
"""

import os
import sqlite3
from datetime import datetime
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')


def register_admin_users_handlers(bot, user_states, user_data):
    """Регистрация обработчиков управления пользователями"""
    
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    
    def is_admin(user_id):
        """Проверка прав администратора"""
        return user_id == ADMIN_ID
    
    
    # ========== ГЛАВНОЕ МЕНЮ ПОЛЬЗОВАТЕЛЕЙ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_users" and is_admin(call.from_user.id))
    def admin_users_callback(call):
        """Главное меню управления пользователями"""
        bot.answer_callback_query(call.id, "👥 Управление пользователями")
        show_users_menu(call.message)
    
    
    def show_users_menu(message):
        """Показать меню управления пользователями"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Статистика пользователей
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0")
        active_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
        blocked_users = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM orders
            WHERE status = 'confirmed'
        """)
        buyers = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""👥 *Управление пользователями*

📊 *Статистика:*
• Всего пользователей: {total_users}
• Активных: {active_users}
• Заблокированных: {blocked_users}
• Совершили покупки: {buyers}

Выберите действие:"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📋 Все пользователи", callback_data="users_list_all_0"),
            types.InlineKeyboardButton("🔒 Заблокированные", callback_data="users_list_blocked_0")
        )
        markup.add(
            types.InlineKeyboardButton("🛍 Покупатели", callback_data="users_list_buyers_0"),
            types.InlineKeyboardButton("🔍 Поиск по ID", callback_data="users_search")
        )
        markup.add(types.InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== СПИСКИ ПОЛЬЗОВАТЕЛЕЙ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("users_list_") and is_admin(call.from_user.id))
    def users_list_callback(call):
        """Показать список пользователей"""
        bot.answer_callback_query(call.id)
        
        parts = call.data.split("_")
        list_type = parts[2]  # all, blocked, buyers
        page = int(parts[3])
        
        show_users_list(call.message, list_type, page)
    
    
    def show_users_list(message, list_type="all", page=0):
        """Показать список пользователей с пагинацией"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Определяем фильтр
        if list_type == "all":
            title = "📋 Все пользователи"
            where_clause = ""
            params = []
        elif list_type == "blocked":
            title = "🔒 Заблокированные пользователи"
            where_clause = "WHERE u.is_blocked = 1"
            params = []
        elif list_type == "buyers":
            title = "🛍 Покупатели"
            where_clause = """
                WHERE u.user_id IN (
                    SELECT DISTINCT user_id FROM orders WHERE status = 'confirmed'
                )
            """
            params = []
        
        # Считаем общее количество
        cursor.execute(f"""
            SELECT COUNT(*) FROM users u {where_clause}
        """, params)
        total = cursor.fetchone()[0]
        
        if total == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_users"))
            
            bot.edit_message_text(
                f"{title}\n\nПользователей не найдено.",
                message.chat.id,
                message.message_id,
                reply_markup=markup
            )
            conn.close()
            return
        
        # Пагинация: 10 пользователей на страницу
        per_page = 10
        offset = page * per_page
        
        cursor.execute(f"""
            SELECT u.user_id, u.username, u.first_name, u.is_blocked, u.registration_date,
                   COUNT(DISTINCT o.id) as orders_count
            FROM users u
            LEFT JOIN orders o ON u.user_id = o.user_id
            {where_clause}
            GROUP BY u.user_id
            ORDER BY u.registration_date DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])
        users = cursor.fetchall()
        conn.close()
        
        text = f"{title}\n"
        text += f"Всего: {total} | Страница {page + 1} из {(total + per_page - 1) // per_page}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for user_id, username, first_name, is_blocked, created_at, orders_count in users:
            status = "🔒" if is_blocked else "✅"
            name = first_name or username or f"User{user_id}"
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y")
            
            button_text = f"{status} {name} | ID: {user_id} | Заказов: {orders_count} | {date}"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"user_view_{user_id}"
            ))
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "◀️ Назад",
                callback_data=f"users_list_{list_type}_{page-1}"
            ))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton(
                "Вперёд ▶️",
                callback_data=f"users_list_{list_type}_{page+1}"
            ))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ Меню пользователей", callback_data="admin_users"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            reply_markup=markup
        )
    
    
    # ========== ПРОСМОТР ПОЛЬЗОВАТЕЛЯ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_view_") and is_admin(call.from_user.id))
    def user_view_callback(call):
        """Просмотр информации о пользователе"""
        bot.answer_callback_query(call.id)
        user_id = int(call.data.split("_")[-1])
        show_user_details(call.message, user_id)
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_user_profile_") and is_admin(call.from_user.id))
    def admin_user_profile_callback(call):
        """Просмотр профиля пользователя (из заказов)"""
        bot.answer_callback_query(call.id, "👤 Профиль пользователя")
        user_id = int(call.data.split("_")[-1])
        show_user_details(call.message, user_id)
    
    
    def show_user_details(message, user_id):
        """Показать детальную информацию о пользователе"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Получаем данные пользователя
        cursor.execute("""
            SELECT user_id, username, first_name, last_name, is_blocked, registration_date
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            bot.answer_callback_query(message.chat.id, "❌ Пользователь не найден")
            conn.close()
            return
        
        user_id, username, first_name, last_name, is_blocked, registration_date = user
        
        # Статистика заказов
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN o.status = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                SUM(CASE WHEN o.status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                SUM(CASE WHEN o.status = 'confirmed' THEN i.price_rub ELSE 0 END) as total_spent
            FROM orders o
            LEFT JOIN inventory i ON o.inventory_id = i.inventory_id
            WHERE o.user_id = ?
        """, (user_id,))
        orders_stats = cursor.fetchone()
        
        # Статистика отзывов
        cursor.execute("""
            SELECT COUNT(*) FROM reviews WHERE user_id = ?
        """, (user_id,))
        reviews_count = cursor.fetchone()[0]
        
        # Последний заказ
        cursor.execute("""
            SELECT created_at FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        last_order = cursor.fetchone()
        
        conn.close()
        
        # Формируем текст
        full_name = f"{first_name or ''} {last_name or ''}".strip() or "Не указано"
        status_text = "🔒 Заблокирован" if is_blocked else "✅ Активен"
        
        text = f"👤 *Информация о пользователе*\n\n"
        text += f"ID: `{user_id}`\n"
        text += f"Имя: {full_name}\n"
        text += f"Username: @{username or 'нет'}\n"
        text += f"Статус: {status_text}\n"
        text += f"Регистрация: {datetime.fromisoformat(registration_date).strftime('%d.%m.%Y %H:%M')}\n"
        
        if last_order:
            text += f"Последний заказ: {datetime.fromisoformat(last_order[0]).strftime('%d.%m.%Y')}\n"
        
        text += f"\n📊 *Статистика:*\n"
        text += f"• Всего заказов: {orders_stats[0]}\n"
        text += f"  ✅ Подтверждено: {orders_stats[1]}\n"
        text += f"  ⏳ В ожидании: {orders_stats[2]}\n"
        text += f"  ❌ Отменено: {orders_stats[3]}\n"
        text += f"• Потрачено: {orders_stats[4] or 0}₽\n"
        text += f"• Отзывов: {reviews_count}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Кнопка блокировки/разблокировки
        if is_blocked:
            markup.add(types.InlineKeyboardButton(
                "✅ Разблокировать",
                callback_data=f"user_unblock_{user_id}"
            ))
        else:
            markup.add(types.InlineKeyboardButton(
                "🔒 Заблокировать",
                callback_data=f"user_block_{user_id}"
            ))
        
        markup.add(
            types.InlineKeyboardButton("📦 Заказы", callback_data=f"user_orders_{user_id}_0"),
            types.InlineKeyboardButton("💬 Обращения", callback_data=f"user_tickets_{user_id}_0")
        )
        markup.add(
            types.InlineKeyboardButton("⭐️ Отзывы", callback_data=f"user_reviews_{user_id}_0"),
            types.InlineKeyboardButton("📝 Написать", callback_data=f"user_message_{user_id}")
        )
        markup.add(types.InlineKeyboardButton("◀️ К списку", callback_data="users_list_all_0"))
        markup.add(types.InlineKeyboardButton("🏠 Меню пользователей", callback_data="admin_users"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== БЛОКИРОВКА/РАЗБЛОКИРОВКА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_block_") and is_admin(call.from_user.id))
    def user_block_callback(call):
        """Заблокировать пользователя"""
        user_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "✅ Пользователь заблокирован")
        show_user_details(call.message, user_id)
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                user_id,
                "🔒 Ваш аккаунт был заблокирован администратором.\n"
                "Для разъяснения причин создайте обращение в поддержку."
            )
        except:
            pass
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_unblock_") and is_admin(call.from_user.id))
    def user_unblock_callback(call):
        """Разблокировать пользователя"""
        user_id = int(call.data.split("_")[-1])
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "✅ Пользователь разблокирован")
        show_user_details(call.message, user_id)
        
        # Уведомляем пользователя
        try:
            bot.send_message(
                user_id,
                "✅ Ваш аккаунт был разблокирован.\n"
                "Теперь вы можете пользоваться ботом."
            )
        except:
            pass
    
    
    # ========== ЗАКАЗЫ ПОЛЬЗОВАТЕЛЯ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_orders_") and is_admin(call.from_user.id))
    def user_orders_callback(call):
        """Показать заказы пользователя"""
        bot.answer_callback_query(call.id)
        parts = call.data.split("_")
        user_id = int(parts[2])
        page = int(parts[3])
        show_user_orders(call.message, user_id, page)
    
    
    def show_user_orders(message, user_id, page=0):
        """Показать заказы конкретного пользователя"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Считаем заказы
        cursor.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        
        if total == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"user_view_{user_id}"))
            
            bot.edit_message_text(
                f"📦 Заказы пользователя {user_id}\n\nЗаказов нет.",
                message.chat.id,
                message.message_id,
                reply_markup=markup
            )
            conn.close()
            return
        
        per_page = 5
        offset = page * per_page
        
        cursor.execute("""
            SELECT o.id, p.name, i.weight_grams, i.price_rub, o.status, o.created_at
            FROM orders o
            JOIN inventory i ON o.inventory_id = i.id
            JOIN products p ON i.product_id = p.id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, per_page, offset))
        orders = cursor.fetchall()
        conn.close()
        
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'cancelled': '❌'
        }
        
        text = f"📦 *Заказы пользователя {user_id}*\n"
        text += f"Всего: {total} | Страница {page + 1}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for order_id, name, weight, price, status, created_at in orders:
            emoji = status_emoji.get(status, '❓')
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y")
            
            button_text = f"{emoji} №{order_id} | {name} {weight}g | {price}₽ | {date}"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"admin_order_view_{order_id}"
            ))
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "◀️",
                callback_data=f"user_orders_{user_id}_{page-1}"
            ))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton(
                "▶️",
                callback_data=f"user_orders_{user_id}_{page+1}"
            ))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ К пользователю", callback_data=f"user_view_{user_id}"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ОБРАЩЕНИЯ ПОЛЬЗОВАТЕЛЯ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_tickets_") and is_admin(call.from_user.id))
    def user_tickets_callback(call):
        """Показать обращения пользователя"""
        bot.answer_callback_query(call.id)
        parts = call.data.split("_")
        user_id = int(parts[2])
        page = int(parts[3])
        show_user_tickets(call.message, user_id, page)
    
    
    def show_user_tickets(message, user_id, page=0):
        """Показать обращения конкретного пользователя"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        
        if total == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"user_view_{user_id}"))
            
            bot.edit_message_text(
                f"💬 Обращения пользователя {user_id}\n\nОбращений нет.",
                message.chat.id,
                message.message_id,
                reply_markup=markup
            )
            conn.close()
            return
        
        per_page = 5
        offset = page * per_page
        
        cursor.execute("""
            SELECT id, subject, status, created_at
            FROM tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, per_page, offset))
        tickets = cursor.fetchall()
        conn.close()
        
        status_emoji = {
            'open': '🟢',
            'answered': '🔵',
            'closed': '⚫️'
        }
        
        text = f"💬 *Обращения пользователя {user_id}*\n"
        text += f"Всего: {total} | Страница {page + 1}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for ticket_id, subject, status, created_at in tickets:
            emoji = status_emoji.get(status, '❓')
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y")
            
            button_text = f"{emoji} №{ticket_id} | {date}"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"admin_ticket_view_{ticket_id}"
            ))
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "◀️",
                callback_data=f"user_tickets_{user_id}_{page-1}"
            ))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton(
                "▶️",
                callback_data=f"user_tickets_{user_id}_{page+1}"
            ))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ К пользователю", callback_data=f"user_view_{user_id}"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ОТЗЫВЫ ПОЛЬЗОВАТЕЛЯ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_reviews_") and is_admin(call.from_user.id))
    def user_reviews_callback(call):
        """Показать отзывы пользователя"""
        bot.answer_callback_query(call.id)
        parts = call.data.split("_")
        user_id = int(parts[2])
        page = int(parts[3])
        show_user_reviews(call.message, user_id, page)
    
    
    def show_user_reviews(message, user_id, page=0):
        """Показать отзывы конкретного пользователя"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM reviews WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        
        if total == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"user_view_{user_id}"))
            
            bot.edit_message_text(
                f"⭐️ Отзывы пользователя {user_id}\n\nОтзывов нет.",
                message.chat.id,
                message.message_id,
                reply_markup=markup
            )
            conn.close()
            return
        
        per_page = 3
        offset = page * per_page
        
        cursor.execute("""
            SELECT id, rating, comment, status, created_at
            FROM reviews
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, per_page, offset))
        reviews = cursor.fetchall()
        conn.close()
        
        text = f"⭐️ *Отзывы пользователя {user_id}*\n"
        text += f"Всего: {total} | Страница {page + 1}\n\n"
        
        for review_id, rating, comment, status, created_at in reviews:
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y")
            status_text = "✅" if status == "approved" else "⏳"
            
            text += f"{status_text} ID:{review_id} | {'⭐️' * rating}\n"
            text += f"_{comment}_\n"
            text += f"📅 {date}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "◀️",
                callback_data=f"user_reviews_{user_id}_{page-1}"
            ))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton(
                "▶️",
                callback_data=f"user_reviews_{user_id}_{page+1}"
            ))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ К пользователю", callback_data=f"user_view_{user_id}"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ОТПРАВКА СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_message_") and is_admin(call.from_user.id))
    def user_message_callback(call):
        """Отправить сообщение пользователю"""
        user_id = int(call.data.split("_")[-1])
        bot.answer_callback_query(call.id)
        
        user_states[call.from_user.id] = f"sending_message_to_{user_id}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data=f"user_view_{user_id}"))
        
        bot.edit_message_text(
            f"📝 *Отправить сообщение пользователю {user_id}*\n\n"
            f"Напишите текст сообщения:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda message: is_admin(message.from_user.id) and user_states.get(message.from_user.id, "").startswith("sending_message_to_"))
    def handle_admin_message_to_user(message):
        """Обработка сообщения администратора пользователю"""
        state = user_states.get(message.from_user.id, "")
        user_id = int(state.split("_")[-1])
        
        text = message.text
        
        if len(text) < 1 or len(text) > 2000:
            bot.send_message(
                message.chat.id,
                "❌ Длина сообщения должна быть от 1 до 2000 символов."
            )
            return
        
        # Отправляем сообщение пользователю
        try:
            bot.send_message(
                user_id,
                f"📩 *Сообщение от администратора:*\n\n{text}",
                parse_mode="Markdown"
            )
            
            user_states.pop(message.from_user.id, None)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ К пользователю", callback_data=f"user_view_{user_id}"))
            
            bot.send_message(
                message.chat.id,
                f"✅ Сообщение отправлено пользователю {user_id}",
                reply_markup=markup
            )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Ошибка отправки сообщения: {str(e)}"
            )
    
    
    # ========== ПОИСК ПОЛЬЗОВАТЕЛЯ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "users_search" and is_admin(call.from_user.id))
    def users_search_callback(call):
        """Поиск пользователя по ID"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "searching_user"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_users"))
        
        bot.edit_message_text(
            "🔍 *Поиск пользователя*\n\n"
            "Введите ID пользователя (число):",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda message: is_admin(message.from_user.id) and user_states.get(message.from_user.id) == "searching_user")
    def handle_user_search(message):
        """Обработка поиска пользователя"""
        try:
            user_id = int(message.text.strip())
            user_states.pop(message.from_user.id, None)
            
            # Проверяем существование пользователя
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()
            conn.close()
            
            if exists:
                # Показываем информацию о пользователе
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("👤 Открыть", callback_data=f"user_view_{user_id}"))
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_users"))
                
                bot.send_message(
                    message.chat.id,
                    f"✅ Пользователь с ID {user_id} найден!",
                    reply_markup=markup
                )
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_users"))
                
                bot.send_message(
                    message.chat.id,
                    f"❌ Пользователь с ID {user_id} не найден в базе данных.",
                    reply_markup=markup
                )
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Введите корректный ID (целое число)."
            )
