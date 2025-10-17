#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель: Массовая рассылка
"""

import os
import sqlite3
from datetime import datetime
from telebot import types
import time


DATABASE = os.getenv('DATABASE', 'bot.db')


def register_admin_broadcast_handlers(bot, user_states, user_data):
    """Регистрация обработчиков массовой рассылки"""
    
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    
    def is_admin(user_id):
        """Проверка прав администратора"""
        return user_id == ADMIN_ID
    
    
    # ========== ГЛАВНОЕ МЕНЮ РАССЫЛКИ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast" and is_admin(call.from_user.id))
    def admin_broadcast_callback(call):
        """Главное меню массовой рассылки"""
        bot.answer_callback_query(call.id, "📢 Массовая рассылка")
        show_broadcast_menu(call.message)
    
    
    def show_broadcast_menu(message):
        """Показать меню массовой рассылки"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Статистика пользователей
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0")
        active_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM broadcasts")
        total_broadcasts = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM broadcasts 
            WHERE created_at > datetime('now', '-30 days')
        """)
        recent_broadcasts = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""📢 *Массовая рассылка*

📊 *Статистика:*
• Активных пользователей: {active_users}
• Всего рассылок: {total_broadcasts}
• За последний месяц: {recent_broadcasts}

⚠️ *Внимание:*
Рассылка будет отправлена всем активным пользователям.
Убедитесь в правильности сообщения перед отправкой!

Выберите действие:"""
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✍️ Создать рассылку", callback_data="broadcast_create"),
            types.InlineKeyboardButton("📋 История рассылок", callback_data="broadcast_history_0"),
            types.InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")
        )
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== СОЗДАНИЕ РАССЫЛКИ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "broadcast_create" and is_admin(call.from_user.id))
    def broadcast_create_callback(call):
        """Создание новой рассылки"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "creating_broadcast"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_broadcast"))
        
        bot.edit_message_text(
            "✍️ *Создание рассылки*\n\n"
            "Напишите текст сообщения для рассылки.\n\n"
            "Вы можете использовать Markdown форматирование:\n"
            "• `*жирный*` → *жирный*\n"
            "• `_курсив_` → _курсив_\n"
            "• \\`код\\` → `код`\n\n"
            "Максимум 4000 символов.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda message: is_admin(message.from_user.id) and user_states.get(message.from_user.id) == "creating_broadcast")
    def handle_broadcast_text(message):
        """Обработка текста рассылки"""
        text = message.text
        
        if len(text) < 10:
            bot.send_message(
                message.chat.id,
                "❌ Текст рассылки слишком короткий. Минимум 10 символов."
            )
            return
        
        if len(text) > 4000:
            bot.send_message(
                message.chat.id,
                "❌ Текст рассылки слишком длинный. Максимум 4000 символов."
            )
            return
        
        # Сохраняем текст рассылки
        user_data[message.from_user.id] = {'broadcast_text': text}
        user_states[message.from_user.id] = "confirming_broadcast"
        
        # Показываем превью
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Отправить", callback_data="broadcast_confirm"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="admin_broadcast")
        )
        
        preview_text = f"📢 *Превью рассылки*\n\n"
        preview_text += "─" * 30 + "\n\n"
        preview_text += text
        preview_text += "\n\n" + "─" * 30 + "\n\n"
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0")
        recipients = cursor.fetchone()[0]
        conn.close()
        
        preview_text += f"Получателей: *{recipients}* человек\n\n"
        preview_text += "⚠️ Подтвердите отправку или отмените."
        
        bot.send_message(
            message.chat.id,
            preview_text,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "broadcast_confirm" and is_admin(call.from_user.id))
    def broadcast_confirm_callback(call):
        """Подтверждение и отправка рассылки"""
        bot.answer_callback_query(call.id, "🚀 Запуск рассылки...")
        
        broadcast_text = user_data.get(call.from_user.id, {}).get('broadcast_text')
        
        if not broadcast_text:
            bot.send_message(call.message.chat.id, "❌ Ошибка: текст рассылки не найден")
            return
        
        # Очищаем состояние
        user_states.pop(call.from_user.id, None)
        user_data.pop(call.from_user.id, None)
        
        # Получаем список активных пользователей
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id FROM users WHERE is_blocked = 0
        """)
        users = cursor.fetchall()
        
        # Создаём запись о рассылке
        cursor.execute("""
            INSERT INTO broadcasts (admin_id, message_text, status, total_count, created_at)
            VALUES (?, ?, 'sending', ?, datetime('now'))
        """, (call.from_user.id, broadcast_text, len(users)))
        
        broadcast_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Отправляем рассылку
        bot.edit_message_text(
            f"🚀 *Рассылка запущена!*\n\n"
            f"ID рассылки: {broadcast_id}\n"
            f"Получателей: {len(users)}\n\n"
            f"Отправка может занять несколько минут...",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        
        # Счётчики
        success_count = 0
        failed_count = 0
        
        # Отправляем сообщения
        for (user_id,) in users:
            try:
                bot.send_message(user_id, broadcast_text, parse_mode="Markdown")
                success_count += 1
                time.sleep(0.05)  # Защита от flood
            except Exception as e:
                failed_count += 1
                # Блокируем пользователей, которые заблокировали бота
                if "bot was blocked" in str(e).lower():
                    conn = sqlite3.connect(DATABASE)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
                    conn.commit()
                    conn.close()
        
        # Обновляем статистику рассылки
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE broadcasts
            SET status = 'completed', sent_count = ?, failed_count = ?, completed_at = datetime('now')
            WHERE id = ?
        """, (success_count, failed_count, broadcast_id))
        conn.commit()
        conn.close()
        
        # Итоговый отчёт
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Меню рассылки", callback_data="admin_broadcast"))
        
        report = f"✅ *Рассылка завершена!*\n\n"
        report += f"ID рассылки: {broadcast_id}\n"
        report += f"✅ Успешно: {success_count}\n"
        report += f"❌ Ошибок: {failed_count}\n"
        report += f"📊 Процент доставки: {(success_count / len(users) * 100) if users else 0:.1f}%"
        
        bot.send_message(
            call.message.chat.id,
            report,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ИСТОРИЯ РАССЫЛОК ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("broadcast_history_") and is_admin(call.from_user.id))
    def broadcast_history_callback(call):
        """Показать историю рассылок"""
        bot.answer_callback_query(call.id)
        page = int(call.data.split("_")[-1])
        show_broadcast_history(call.message, page)
    
    
    def show_broadcast_history(message, page=0):
        """Показать историю рассылок с пагинацией"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM broadcasts")
        total = cursor.fetchone()[0]
        
        if total == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_broadcast"))
            
            bot.edit_message_text(
                "📋 *История рассылок*\n\nРассылок пока нет.",
                message.chat.id,
                message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            conn.close()
            return
        
        per_page = 5
        offset = page * per_page
        
        cursor.execute("""
            SELECT id, message_text, status, total_count, sent_count, failed_count, created_at
            FROM broadcasts
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        broadcasts = cursor.fetchall()
        conn.close()
        
        text = f"📋 *История рассылок*\n"
        text += f"Всего: {total} | Страница {page + 1}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        status_emoji = {
            'sending': '⏳ Отправка',
            'completed': '✅ Завершена',
            'failed': '❌ Ошибка'
        }
        
        for broadcast_id, msg, status, total_users, sent_count, failed_count, created_at in broadcasts:
            date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
            status_text = status_emoji.get(status, status)
            
            # Укорачиваем текст для кнопки
            short_msg = msg[:30] + "..." if len(msg) > 30 else msg
            short_msg = short_msg.replace('\n', ' ')
            
            button_text = f"{status_text} | №{broadcast_id} | {date}"
            markup.add(types.InlineKeyboardButton(
                button_text,
                callback_data=f"broadcast_view_{broadcast_id}"
            ))
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("◀️", callback_data=f"broadcast_history_{page-1}"))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton("▶️", callback_data=f"broadcast_history_{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ Меню рассылки", callback_data="admin_broadcast"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("broadcast_view_") and is_admin(call.from_user.id))
    def broadcast_view_callback(call):
        """Просмотр детальной информации о рассылке"""
        bot.answer_callback_query(call.id)
        broadcast_id = int(call.data.split("_")[-1])
        show_broadcast_details(call.message, broadcast_id)
    
    
    def show_broadcast_details(message, broadcast_id):
        """Показать детали рассылки"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, admin_id, message_text, status, total_users, sent_count, 
                   failed_count, created_at, completed_at
            FROM broadcasts
            WHERE id = ?
        """, (broadcast_id,))
        broadcast = cursor.fetchone()
        conn.close()
        
        if not broadcast:
            bot.answer_callback_query(message.chat.id, "❌ Рассылка не найдена")
            return
        
        b_id, admin_id, msg, status, total_users, sent_count, failed_count, created_at, completed_at = broadcast
        
        status_emoji = {
            'sending': '⏳ Отправка',
            'completed': '✅ Завершена',
            'failed': '❌ Ошибка'
        }
        
        text = f"📢 *Рассылка №{b_id}*\n\n"
        text += f"📊 Статус: {status_emoji.get(status, status)}\n"
        text += f"📅 Создана: {datetime.fromisoformat(created_at).strftime('%d.%m.%Y %H:%M')}\n"
        
        if completed_at:
            text += f"✅ Завершена: {datetime.fromisoformat(completed_at).strftime('%d.%m.%Y %H:%M')}\n"
        
        text += f"\n📊 *Статистика:*\n"
        text += f"• Получателей: {total_users}\n"
        text += f"• Отправлено: {sent_count or 0}\n"
        text += f"• Ошибок: {failed_count or 0}\n"
        
        if total_users and sent_count:
            delivery_rate = (sent_count / total_users) * 100
            text += f"• Доставляемость: {delivery_rate:.1f}%\n"
        
        text += f"\n📝 *Текст сообщения:*\n"
        text += "─" * 30 + "\n"
        text += msg[:500] + ("..." if len(msg) > 500 else "")
        text += "\n" + "─" * 30
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ К истории", callback_data="broadcast_history_0"))
        markup.add(types.InlineKeyboardButton("🏠 Меню рассылки", callback_data="admin_broadcast"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
