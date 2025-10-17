#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Админ-панель: Настройки бота (ПОЛНАЯ ВЕРСИЯ)
"""

import os
import sqlite3
import json
from datetime import datetime
from telebot import types


DATABASE = os.getenv('DATABASE', 'bot.db')


def register_admin_settings_handlers(bot, user_states, user_data):
    """Регистрация обработчиков настроек бота"""
    
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
    
    def is_admin(user_id):
        """Проверка прав администратора"""
        return user_id == ADMIN_ID
    
    
    def get_setting(key, default=''):
        """Получить значение настройки"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT {key} FROM bot_settings WHERE id = 1")
            result = cursor.fetchone()
            conn.close()
            return str(result[0]) if result and result[0] is not None else default
        except Exception as e:
            conn.close()
            return default
    
    
    def set_setting(key, value):
        """Установить значение настройки"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                UPDATE bot_settings 
                SET {key} = ?, updated_at = datetime('now')
                WHERE id = 1
            """, (value,))
            conn.commit()
        except Exception as e:
            pass
        finally:
            conn.close()
    
    
    # ========== ГЛАВНОЕ МЕНЮ НАСТРОЕК ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_settings" and is_admin(call.from_user.id))
    def admin_settings_callback(call):
        """Главное меню настроек"""
        bot.answer_callback_query(call.id, "⚙️ Настройки бота")
        show_settings_menu(call.message)
    
    
    def show_settings_menu(message):
        """Показать меню настроек"""
        maintenance = get_setting('maintenance_mode', '0')
        captcha = get_setting('captcha_enabled', '0')
        support_username = get_setting('support_username', 'не установлен')
        
        maint_status = "🟢 Вкл" if maintenance == '1' else "🔴 Выкл"
        captcha_status = "🟢 Вкл" if captcha == '1' else "🔴 Выкл"
        
        text = f"""⚙️ *Настройки бота*

🔧 *Текущие настройки:*

🛠 Тех.работы: {maint_status}
🤖 Капча: {captcha_status}
🪬 Контакт саппорта: @{support_username}

Выберите действие:"""
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"🛠 Тех.работы: {maint_status}", callback_data="toggle_maintenance"),
            types.InlineKeyboardButton(f"🤖 Капча: {captcha_status}", callback_data="toggle_captcha"),
            types.InlineKeyboardButton("👋 Приветствие бота", callback_data="settings_welcome"),
            types.InlineKeyboardButton("💳 Реквизиты для оплаты", callback_data="settings_payment"),
            types.InlineKeyboardButton("🪬 Контакт саппорта", callback_data="settings_support"),
            types.InlineKeyboardButton("📊 Просмотр всех настроек", callback_data="settings_view_all"),
            types.InlineKeyboardButton("💾 Сохранить настройки в файл", callback_data="settings_export"),
            types.InlineKeyboardButton("📲 Импорт настроек из файла", callback_data="settings_import"),
            types.InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")
        )
        
        bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ПЕРЕКЛЮЧАТЕЛИ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "toggle_maintenance" and is_admin(call.from_user.id))
    def toggle_maintenance_callback(call):
        """Переключить режим тех.работ"""
        current = get_setting('maintenance_mode', '0')
        new_value = '0' if current == '1' else '1'
        set_setting('maintenance_mode', new_value)
        
        status = "включён" if new_value == '1' else "выключен"
        bot.answer_callback_query(call.id, f"🛠 Режим тех.работ {status}")
        show_settings_menu(call.message)
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "toggle_captcha" and is_admin(call.from_user.id))
    def toggle_captcha_callback(call):
        """Переключить капчу"""
        current = get_setting('captcha_enabled', '0')
        new_value = '0' if current == '1' else '1'
        set_setting('captcha_enabled', new_value)
        
        status = "включена" if new_value == '1' else "выключена"
        bot.answer_callback_query(call.id, f"🤖 Капча {status}")
        show_settings_menu(call.message)
    
    
    # ========== ПРИВЕТСТВИЕ БОТА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "settings_welcome" and is_admin(call.from_user.id))
    def settings_welcome_callback(call):
        """Меню приветствия"""
        bot.answer_callback_query(call.id)
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✍️ Изменить текст", callback_data="welcome_change_text"),
            types.InlineKeyboardButton("🖼 Изменить медиа", callback_data="welcome_change_media"),
            types.InlineKeyboardButton("◀️ Назад", callback_data="admin_settings")
        )
        
        current_text = get_setting('welcome_text', 'Добро пожаловать!')
        
        bot.edit_message_text(
            f"👋 *Приветствие бота*\n\n"
            f"Текущий текст:\n{current_text[:200]}...\n\n"
            f"Выберите действие:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "welcome_change_text" and is_admin(call.from_user.id))
    def welcome_change_text_callback(call):
        """Изменить текст приветствия"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "awaiting_welcome_text"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="settings_welcome"))
        
        bot.edit_message_text(
            "✍️ *Изменить приветственный текст*\n\n"
            "Отправьте новый текст приветствия (до 1000 символов):",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and user_states.get(msg.from_user.id) == "awaiting_welcome_text")
    def handle_welcome_text(message):
        """Обработка нового текста приветствия"""
        text = message.text
        
        if len(text) > 1000:
            bot.send_message(message.chat.id, "❌ Текст слишком длинный. Максимум 1000 символов.")
            return
        
        set_setting('welcome_text', text)
        user_states.pop(message.from_user.id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Настройки", callback_data="admin_settings"))
        
        bot.send_message(
            message.chat.id,
            "✅ Приветственный текст обновлён!",
            reply_markup=markup
        )
    
    
    @bot.callback_query_handler(func=lambda call: call.data == "welcome_change_media" and is_admin(call.from_user.id))
    def welcome_change_media_callback(call):
        """Изменить медиа приветствия"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "awaiting_welcome_media"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="settings_welcome"))
        
        bot.edit_message_text(
            "🖼 *Изменить приветственное медиа*\n\n"
            "Отправьте фото или видео для приветственного сообщения:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(content_types=['photo', 'video'], func=lambda msg: is_admin(msg.from_user.id) and user_states.get(msg.from_user.id) == "awaiting_welcome_media")
    def handle_welcome_media(message):
        """Обработка медиа для приветствия"""
        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = 'photo'
        elif message.video:
            file_id = message.video.file_id
            media_type = 'video'
        else:
            return
        
        set_setting('welcome_media_type', media_type)
        set_setting('welcome_media_id', file_id)
        user_states.pop(message.from_user.id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Настройки", callback_data="admin_settings"))
        
        bot.send_message(
            message.chat.id,
            f"✅ Приветственное {media_type} обновлено!",
            reply_markup=markup
        )
    
    
    # ========== РЕКВИЗИТЫ ОПЛАТЫ ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "settings_payment" and is_admin(call.from_user.id))
    def settings_payment_callback(call):
        """Изменить реквизиты оплаты"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "awaiting_payment_info"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_settings"))
        
        current = get_setting('payment_info', 'Не установлены')
        
        bot.edit_message_text(
            f"💳 *Реквизиты для оплаты*\n\n"
            f"Текущие реквизиты:\n```\n{current}\n```\n\n"
            f"Отправьте новые реквизиты для оплаты:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and user_states.get(msg.from_user.id) == "awaiting_payment_info")
    def handle_payment_info(message):
        """Обработка реквизитов оплаты"""
        text = message.text
        
        if len(text) > 500:
            bot.send_message(message.chat.id, "❌ Текст слишком длинный. Максимум 500 символов.")
            return
        
        set_setting('payment_info', text)
        user_states.pop(message.from_user.id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Настройки", callback_data="admin_settings"))
        
        bot.send_message(
            message.chat.id,
            "✅ Реквизиты оплаты обновлены!",
            reply_markup=markup
        )
    
    
    # ========== КОНТАКТ САППОРТА ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "settings_support" and is_admin(call.from_user.id))
    def settings_support_callback(call):
        """Установить контакт саппорта"""
        bot.answer_callback_query(call.id)
        user_states[call.from_user.id] = "awaiting_support_username"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_settings"))
        
        current = get_setting('support_username', 'не установлен')
        
        bot.edit_message_text(
            f"🪬 *Контакт саппорта*\n\n"
            f"Текущий: @{current}\n\n"
            f"Отправьте username саппорта (без @):",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and user_states.get(msg.from_user.id) == "awaiting_support_username")
    def handle_support_username(message):
        """Обработка username саппорта"""
        username = message.text.strip().replace('@', '')
        
        if len(username) < 5 or len(username) > 32:
            bot.send_message(message.chat.id, "❌ Некорректный username. Длина должна быть 5-32 символа.")
            return
        
        set_setting('support_username', username)
        user_states.pop(message.from_user.id, None)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Настройки", callback_data="admin_settings"))
        
        bot.send_message(
            message.chat.id,
            f"✅ Контакт саппорта установлен: @{username}",
            reply_markup=markup
        )
    
    
    # ========== ПРОСМОТР ВСЕХ НАСТРОЕК ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "settings_view_all" and is_admin(call.from_user.id))
    def settings_view_all_callback(call):
        """Просмотр всех настроек"""
        bot.answer_callback_query(call.id)
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bot_settings WHERE id = 1")
        settings = cursor.fetchone()
        conn.close()
        
        if settings:
            text = "📊 *Все настройки бота:*\n\n"
            text += f"🛠 Режим обслуживания: {get_setting('maintenance_mode', '0')}\n"
            text += f"🤖 Капча: {get_setting('captcha_enabled', '0')}\n"
            text += f"👋 Приветствие: {get_setting('welcome_text', 'не установлено')[:50]}...\n"
            text += f"💳 Реквизиты: {get_setting('payment_info', 'не установлены')[:50]}...\n"
            text += f"🪬 Саппорт: @{get_setting('support_username', 'не установлен')}\n"
        else:
            text = "❌ Настройки не найдены"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_settings"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    # ========== ЭКСПОРТ НАСТРОЕК ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "settings_export" and is_admin(call.from_user.id))
    def settings_export_callback(call):
        """Экспорт всех настроек в файл"""
        bot.answer_callback_query(call.id, "💾 Генерация файла...")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Экспортируем все данные
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "bot_settings": {},
            "cities": [],
            "districts": [],
            "products": [],
            "inventory": [],
            "orders": [],
            "users": []
        }
        
        # Настройки
        cursor.execute("SELECT * FROM bot_settings WHERE id = 1")
        settings = cursor.fetchone()
        if settings:
            export_data["bot_settings"] = {
                "maintenance_mode": get_setting('maintenance_mode', '0'),
                "captcha_enabled": get_setting('captcha_enabled', '0'),
                "welcome_text": get_setting('welcome_text', ''),
                "payment_info": get_setting('payment_info', ''),
                "support_username": get_setting('support_username', '')
            }
        
        # Города
        cursor.execute("SELECT id, name FROM cities")
        export_data["cities"] = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        
        # Районы
        cursor.execute("SELECT id, city_id, name FROM districts")
        export_data["districts"] = [{"id": r[0], "city_id": r[1], "name": r[2]} for r in cursor.fetchall()]
        
        # Товары
        cursor.execute("SELECT id, name, description FROM products")
        export_data["products"] = [{"id": r[0], "name": r[1], "description": r[2]} for r in cursor.fetchall()]
        
        # Наличие
        cursor.execute("SELECT inventory_id, product_id, city_id, district_id, weight_grams, price_rub, is_active FROM inventory")
        export_data["inventory"] = [{"id": r[0], "product_id": r[1], "city_id": r[2], "district_id": r[3], "weight": r[4], "price": r[5], "active": r[6]} for r in cursor.fetchall()]
        
        # Заказы
        cursor.execute("SELECT id, user_id, inventory_id, status, created_at FROM orders")
        export_data["orders"] = [{"id": r[0], "user_id": r[1], "inventory_id": r[2], "status": r[3], "created_at": r[4]} for r in cursor.fetchall()]
        
        # Пользователи
        cursor.execute("SELECT user_id, username, first_name, is_blocked FROM users")
        export_data["users"] = [{"id": r[0], "username": r[1], "name": r[2], "blocked": r[3]} for r in cursor.fetchall()]
        
        conn.close()
        
        # Создаём JSON файл
        json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
        filename = f"bot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(f"/tmp/{filename}", "w", encoding="utf-8") as f:
            f.write(json_data)
        
        # Отправляем файл
        with open(f"/tmp/{filename}", "rb") as f:
            bot.send_document(
                call.message.chat.id,
                f,
                caption="💾 Экспорт настроек и данных\n\n✅ Файл создан успешно!",
                visible_file_name=filename
            )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Настройки", callback_data="admin_settings"))
        
        bot.send_message(
            call.message.chat.id,
            "✅ Экспорт завершён!\n\nФайл содержит:\n• Настройки бота\n• Города и районы\n• Товары\n• Витрину\n• Заказы\n• Пользователей",
            reply_markup=markup
        )
    
    
    # ========== ИМПОРТ НАСТРОЕК ==========
    
    @bot.callback_query_handler(func=lambda call: call.data == "settings_import" and is_admin(call.from_user.id))
    def settings_import_callback(call):
        """Импорт настроек из файла"""
        bot.answer_callback_query(call.id)
        
        # Проверяем режим тех.работ
        maintenance = get_setting('maintenance_mode', '0')
        
        if maintenance != '1':
            bot.answer_callback_query(call.id, "⚠️ Включите режим тех.работ перед импортом!", show_alert=True)
            return
        
        user_states[call.from_user.id] = "awaiting_import_file"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="admin_settings"))
        
        bot.edit_message_text(
            "📲 *Импорт настроек*\n\n"
            "⚠️ ВНИМАНИЕ!\n"
            "Импорт перезапишет текущие данные!\n\n"
            "Отправьте JSON файл с настройками:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    
    @bot.message_handler(content_types=['document'], func=lambda msg: is_admin(msg.from_user.id) and user_states.get(msg.from_user.id) == "awaiting_import_file")
    def handle_import_file(message):
        """Обработка файла импорта"""
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Парсим JSON
            import_data = json.loads(downloaded_file.decode('utf-8'))
            
            # Импортируем настройки
            if "bot_settings" in import_data:
                for key, value in import_data["bot_settings"].items():
                    set_setting(key, value)
            
            user_states.pop(message.from_user.id, None)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("◀️ Настройки", callback_data="admin_settings"))
            
            bot.send_message(
                message.chat.id,
                "✅ Импорт завершён успешно!\n\nПрименены новые настройки.",
                reply_markup=markup
            )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Ошибка импорта: {str(e)}\n\nПроверьте формат файла."
            )
