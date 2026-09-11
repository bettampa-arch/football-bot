import os
import threading
import time
import requests
from datetime import datetime
from flask import Flask
import telebot
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
FOOTBALL_DATA_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
app = Flask(__name__)

@app.route('/')
def home():
    return "Football AI Bot is Running!"

def keep_alive():
    while True:
        time.sleep(600)
        if RENDER_URL:
            try:
                requests.get(RENDER_URL)
            except Exception as e:
                print(f"Keep-alive error: {e}")

def get_football_data(match_query):
    if not FOOTBALL_DATA_TOKEN:
        return "API Token не налаштовано."
    headers = {'X-Auth-Token': FOOTBALL_DATA_TOKEN}
    try:
        url = 'https://api.football-data.org/v4/matches'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            matches = response.json().get('matches', [])
            relevant = []
            for m in matches:
                home = m.get('homeTeam', {}).get('name', '')
                away = m.get('awayTeam', {}).get('name', '')
                date = m.get('utcDate', '')
                relevant.append(f"{date}: {home} vs {away}")
            return "\n".join(relevant[:10])
    except Exception as e:
        return f"Помилка API: {e}"
    return "Не вдалося отримати свіжі дані з API."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привіт! Я твій AI-аналітик футбольних матчів. ⚽🤖\n\nНадсилай запит у форматі:\n*Команда1 - Команда2 / ДД.ММ.ГГ*\n(наприклад: `Венеція - Фіорентина / 11.09.26`)", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def analyze_match(message):
    user_input = message.text
    bot.send_message(message.chat.id, f"🔍 Глибокий аналіз (метрики Sofascore): *{user_input}*...", parse_mode="Markdown")
    
    live_stats = get_football_data(user_input)
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    prompt = (
        f"Запит від користувача: {user_input}\n"
        f"Сьогоднішня дата за замовчуванням: {current_date}\n"
        f"Дані API: {live_stats}\n\n"
        "РОЛЬ ТА МЕТОДОЛОГІЯ:\n"
        "Ти спортивний аналітик рівня Sofascore/Opta. Під час визначення ймовірностей обов'язково опирайся на:\n"
        "- Показники xG (створені моменти) та xGA (допущені моменти біля власних воріт)\n"
        "- Тренди останніх 10 матчів (середні кутові, жовті картки, володіння м'ячем)\n"
        "- Результативність у домашніх/виїзних поєдинках та стиль гри суперників\n\n"
        "ІНСТРУКЦІЯ ТА ФОРМАТ ВІДПОВІДІ:\n"
        "1. Якщо користувач вказав дату через слеш '/' (наприклад: Венеція - Фіорентина / 11.09.26), використай САМЕ ЦЮ ДАТУ.\n"
        "2. Перший рядок відповіді БЕЗ ВИНЯТКІВ має відповідати формату:\n"
        "[Назва Команди 1] - [Назва Команди 2] / [Вказана Дата]\n\n"
        "3. Виведи СТРOГО 1 або максимум 2 найвірогідніші ставки. Жодних таблиць, HTML-тегів чи довгих текстів.\n\n"
        "ПРИКЛАД ВІДПОВІДІ:\n\n"
        "Венеція - Фіорентина / 11.09.2026\n\n"
        "🔥 **НАЙБІЛЬШ ВІРОГІДНА СТАВКА:**\n\n"
        "📌 **Кутові**\n"
        "• **Ставка:** Фіорентина 5-6\n"
        "• **Ймовірність:** 65%\n"
        "• **Обґрунтування:** Згідно зі статистикою xG та флангової активності Sofascore, Фіорентина подає в середньому 5.6 кутових проти низького блоку.\n\n"
        "📌 **Тотал голів**\n"
        "• **Ставка:** Менше 2.5\n"
        "• **Ймовірність:** 60%\n"
        "• **Обґрунтування:** Сумарний xG двох команд у 5 останніх матчах становить лише 1.8 за гру."
    )
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ти професійний спортивний аналітик. Використовуй статистику xG та метрики Sofascore, але суворо дотримуйся заданого лаконічного формату."},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-20b",
            temperature=0.2,
        )
        response_text = chat_completion.choices[0].message.content
        bot.reply_to(message, response_text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Помилка аналізу: {e}")

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    run_bot()
                
