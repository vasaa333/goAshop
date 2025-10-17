#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель: Просмотр логов бота
"""

import os
import sqlite3
from datetime import datetime
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')
LOG_FILE = 'bot.log'


def register_admin_logs_handlers(bot, user_states, user_data):
    """Регистрация обработчиков логов"""
    
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    
    def is_admin(user_id):
        """Проверка прав администратора"""
        return user_id == ADMIN_ID
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_logs" and is_admin(call.from_user.id))
    def admin_logs_callback(call):
        """Главное меню логов"""
        bot.answer_callback_query(call.id, "📋 Логи бота")
        show_logs_menu(call.message)
    
    
    def show_logs_menu(message):
        """Показать меню логов"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📄 Последние 70 строк", callback_data="logs_view_70"),
            types.InlineKeyboardButton("📊 Статистика логов", callback_data="logs_stats"),
            types.InlineKeyboardButton("🗑 Очистить логи", callback_data="logs_clear"),
            types.InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")
        )
        
        bot.edit_message_text(
            "📋 *Логи бота*\n\n"
            "Выберите действие:",
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "logs_view_70" and is_admin(call.from_user.id))
    def logs_view_70_callback(call):
        """Показать последние 70 строк логов"""
        bot.answer_callback_query(call.id, "📄 Загрузка логов...")
        
        try:
            if not os.path.exists(LOG_FILE):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
                
                bot.edit_message_text(
                    "📄 *Логи бота*\n\n❌ Файл логов не найден.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                return
            
            # Читаем последние 70 строк
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_70 = lines[-70:] if len(lines) >= 70 else lines
            
            if not last_70:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
                
                bot.edit_message_text(
                    "📄 *Логи бота*\n\n❌ Логи пусты.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                return
            
            # Форматируем логи методом цитирования
            log_text = ''.join(last_70)
            
            # Telegram имеет лимит на длину сообщения (4096 символов)
            # Разбиваем на части если нужно
            max_len = 3500  # оставляем запас
            
            if len(log_text) > max_len:
                log_text = "..." + log_text[-max_len:]
            
            # Отправляем логи методом цитирования (blockquote в Markdown)
            formatted_log = f"📄 *Последние 70 строк логов:*\n\n```\n{log_text}\n```"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="logs_view_70"))
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
            
            bot.edit_message_text(
                formatted_log,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            
        except Exception as e:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
            
            bot.edit_message_text(
                f"📄 *Логи бота*\n\n❌ Ошибка чтения логов:\n`{str(e)}`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "logs_stats" and is_admin(call.from_user.id))
    def logs_stats_callback(call):
        """Статистика логов"""
        bot.answer_callback_query(call.id)
        
        try:
            if not os.path.exists(LOG_FILE):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
                
                bot.edit_message_text(
                    "📊 *Статистика логов*\n\n❌ Файл логов не найден.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                return
            
            # Читаем файл и собираем статистику
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            errors = sum(1 for line in lines if 'ERROR' in line)
            warnings = sum(1 for line in lines if 'WARNING' in line)
            info = sum(1 for line in lines if 'INFO' in line)
            
            # Размер файла
            file_size = os.path.getsize(LOG_FILE)
            size_mb = file_size / (1024 * 1024)
            
            text = f"📊 *Статистика логов*\n\n"
            text += f"📄 Всего строк: {total_lines}\n"
            text += f"❌ Ошибок (ERROR): {errors}\n"
            text += f"⚠️ Предупреждений (WARNING): {warnings}\n"
            text += f"ℹ️ Информационных (INFO): {info}\n"
            text += f"💾 Размер файла: {size_mb:.2f} MB\n"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
            
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
            
        except Exception as e:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
            
            bot.edit_message_text(
                f"📊 *Статистика логов*\n\n❌ Ошибка: `{str(e)}`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "logs_clear" and is_admin(call.from_user.id))
    def logs_clear_callback(call):
        """Подтверждение очистки логов"""
        bot.answer_callback_query(call.id)
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить", callback_data="logs_clear_confirm"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="admin_logs")
        )
        
        bot.edit_message_text(
            "🗑 *Очистка логов*\n\n"
            "⚠️ Вы уверены, что хотите очистить файл логов?\n"
            "Это действие необратимо!",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "logs_clear_confirm" and is_admin(call.from_user.id))
    def logs_clear_confirm_callback(call):
        """Очистка логов"""
        bot.answer_callback_query(call.id, "🗑 Очистка логов...")
        
        try:
            if os.path.exists(LOG_FILE):
                # Очищаем файл
                with open(LOG_FILE, 'w', encoding='utf-8') as f:
                    f.write(f"{datetime.now().isoformat()} - Логи очищены администратором\n")
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
                
                bot.edit_message_text(
                    "🗑 *Очистка логов*\n\n✅ Логи успешно очищены!",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
                
                bot.edit_message_text(
                    "🗑 *Очистка логов*\n\n❌ Файл логов не найден.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                
        except Exception as e:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_logs"))
            
            bot.edit_message_text(
                f"🗑 *Очистка логов*\n\n❌ Ошибка: `{str(e)}`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
