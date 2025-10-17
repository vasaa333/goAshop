#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель: Система логов действий
"""

import os
import sqlite3
from datetime import datetime
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')


def log_action(admin_id, action, details=''):
    """Записать действие в лог"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO action_logs (admin_id, action, details, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (admin_id, action, details))
        conn.commit()
        conn.close()
    except:
        pass  # Не прерываем работу бота при ошибке логирования


def register_admin_logs_handlers(bot, user_states, user_data):
    """Регистрация обработчиков логов"""
    
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    
    def is_admin(user_id):
        """Проверка прав администратора"""
        return user_id == ADMIN_ID
    
    
    # ========== ГЛАВНОЕ МЕНЮ ЛОГОВ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_logs" and is_admin(call.from_user.id))
    def admin_logs_callback(call):
        """Главное меню логов"""
        bot.answer_callback_query(call.id, "📜 Логи действий")
        show_logs_menu(call.message)
    
    
    def show_logs_menu(message):
        """Показать меню логов"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Статистика логов
        cursor.execute("SELECT COUNT(*) FROM action_logs")
        total_logs = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM action_logs 
            WHERE created_at > datetime('now', '-1 day')
        """)
        today_logs = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM action_logs 
            WHERE created_at > datetime('now', '-7 days')
        """)
        week_logs = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""📜 *Логи действий администратора*

📊 *Статистика:*
• Всего записей: {total_logs}
• За сегодня: {today_logs}
• За неделю: {week_logs}

Выберите период для просмотра:"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📅 Сегодня", callback_data="logs_view_today_0"),
            types.InlineKeyboardButton("📆 Неделя", callback_data="logs_view_week_0")
        )
        markup.add(
            types.InlineKeyboardButton("📋 Все логи", callback_data="logs_view_all_0"),
            types.InlineKeyboardButton("🗑 Очистить старые", callback_data="logs_cleanup")
        )
        markup.add(types.InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ПРОСМОТР ЛОГОВ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("logs_view_") and is_admin(call.from_user.id))
    def logs_view_callback(call):
        """Просмотр логов"""
        bot.answer_callback_query(call.id)
        parts = call.data.split("_")
        period = parts[2]  # today, week, all
        page = int(parts[3])
        show_logs(call.message, period, page)
    
    
    def show_logs(message, period="all", page=0):
        """Показать логи с пагинацией"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Определяем фильтр по периоду
        if period == "today":
            title = "📅 Логи за сегодня"
            where_clause = "WHERE created_at > datetime('now', '-1 day')"
        elif period == "week":
            title = "📆 Логи за неделю"
            where_clause = "WHERE created_at > datetime('now', '-7 days')"
        else:
            title = "📋 Все логи"
            where_clause = ""
        
        # Считаем количество
        cursor.execute(f"SELECT COUNT(*) FROM action_logs {where_clause}")
        total = cursor.fetchone()[0]
        
        if total == 0:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
            
            bot.edit_message_text(
                f"{title}\n\nЗаписей не найдено.",
                message.chat.id,
                message.message_id,
                reply_markup=markup
            )
            conn.close()
            return
        
        per_page = 10
        offset = page * per_page
        
        cursor.execute(f"""
            SELECT id, admin_id, action, details, created_at
            FROM action_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        logs = cursor.fetchall()
        conn.close()
        
        text = f"{title}\n"
        text += f"Всего: {total} | Страница {page + 1} из {(total + per_page - 1) // per_page}\n\n"
        
        for log_id, admin_id, action, details, created_at in logs:
            date = datetime.fromisoformat(created_at).strftime("%d.%m %H:%M")
            details_short = details[:30] + "..." if details and len(details) > 30 else details or ""
            
            text += f"🔹 `{date}` | {action}\n"
            if details_short:
                text += f"   _{details_short}_\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("◀️", callback_data=f"logs_view_{period}_{page-1}"))
        if (page + 1) * per_page < total:
            nav_buttons.append(types.InlineKeyboardButton("▶️", callback_data=f"logs_view_{period}_{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("◀️ Меню логов", callback_data="admin_logs"))
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ОЧИСТКА СТАРЫХ ЛОГОВ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "logs_cleanup" and is_admin(call.from_user.id))
    def logs_cleanup_callback(call):
        """Очистить старые логи"""
        bot.answer_callback_query(call.id)
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🗑 Удалить старше 30 дней", callback_data="logs_cleanup_30"),
            types.InlineKeyboardButton("🗑 Удалить старше 90 дней", callback_data="logs_cleanup_90"),
            types.InlineKeyboardButton("🗑 Удалить все логи", callback_data="logs_cleanup_all"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="admin_logs")
        )
        
        bot.edit_message_text(
            "🗑 *Очистка логов*\n\n"
            "⚠️ Удаление логов необратимо!\n\n"
            "Выберите период для удаления:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("logs_cleanup_") and is_admin(call.from_user.id))
    def logs_cleanup_confirm_callback(call):
        """Подтверждение очистки логов"""
        period = call.data.split("_")[-1]
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        if period == "30":
            cursor.execute("DELETE FROM action_logs WHERE created_at < datetime('now', '-30 days')")
            msg = "✅ Логи старше 30 дней удалены"
        elif period == "90":
            cursor.execute("DELETE FROM action_logs WHERE created_at < datetime('now', '-90 days')")
            msg = "✅ Логи старше 90 дней удалены"
        elif period == "all":
            cursor.execute("DELETE FROM action_logs")
            msg = "✅ Все логи удалены"
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        log_action(call.from_user.id, "Очистка логов", f"Удалено записей: {deleted}")
        
        bot.answer_callback_query(call.id, f"{msg} ({deleted} записей)")
        show_logs_menu(call.message)


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ЛОГИРОВАНИЯ ==========

def log_order_confirmation(admin_id, order_id):
    """Лог подтверждения заказа"""
    log_action(admin_id, "Подтверждение заказа", f"Заказ №{order_id}")


def log_order_rejection(admin_id, order_id, reason):
    """Лог отклонения заказа"""
    log_action(admin_id, "Отклонение заказа", f"Заказ №{order_id}: {reason[:50]}")


def log_user_block(admin_id, user_id):
    """Лог блокировки пользователя"""
    log_action(admin_id, "Блокировка пользователя", f"User ID: {user_id}")


def log_user_unblock(admin_id, user_id):
    """Лог разблокировки пользователя"""
    log_action(admin_id, "Разблокировка пользователя", f"User ID: {user_id}")


def log_broadcast(admin_id, broadcast_id, recipients):
    """Лог рассылки"""
    log_action(admin_id, "Массовая рассылка", f"ID: {broadcast_id}, получателей: {recipients}")


def log_product_add(admin_id, product_name):
    """Лог добавления товара"""
    log_action(admin_id, "Добавление товара", product_name)


def log_inventory_add(admin_id, product_name, count):
    """Лог добавления товара на склад"""
    log_action(admin_id, "Пополнение склада", f"{product_name}: {count} шт.")


def log_setting_change(admin_id, setting_key, new_value):
    """Лог изменения настройки"""
    log_action(admin_id, "Изменение настройки", f"{setting_key} = {new_value[:50]}")
