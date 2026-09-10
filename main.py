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
    bot.reply_to(message, "Привіт! Я твій AI-аналітик футбольних матчів. ⚽🤖\n\nНапиши мені назву двох команд (наприклад: *Севілья - Валенсія*), і я знайду найближчу дату та згенерую точний прогноз!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def analyze_match(message):
    user_input = message.text
    bot.send_message(message.chat.id, f"🔍 Шукаю найближчий матч та аналізую лінію: *{user_input}*...", parse_mode="Markdown")
    
    live_stats = get_football_data(user_input)
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    prompt = f"""
    Сьогоднішня поточна дата: {current_date}
    Запит користувача: {user_input}
    Дані з розкладу API:
    {live_stats}

    ІНСТРУКЦІЯ ТА ФОРМАТ ВІДПОВІДІ:
    1. Визнач найближчу дату проведення цього матчу (якщо в API немає точної дати, вкажи найближчу реальну дату цього матчу в сезоні).
    2. Перший рядок відповіді повинен бути СТРOГО у форматі:
    [Назва Команди 1] - [Назва Команди 2] / [ДД.ММ.ГГГГ]

    3. Нижче виведи СТРОГО 1 або максимум 2 найвірогідніші ставки. Не використовуй таблиці, html-теги чи довгі описувальні тексти.

    ПРИКЛАД ВІДПОВІДІ:

    Севілья - Валенсія / 11.09.2026

    🔥 **НАЙБІЛЬШ ВІРОГІДНА СТАВКА:**

    📌 **Кутові**
    • **Ставка:** Севілья 5-6
    • **Ймовірність:** 65%
    • **Обґрунтування:** Севілья в середньому подає 5.8 кутових у домашніх матчах проти команд нижньої частини таблиці.

    📌 **Тотал голів**
    • **Ставка:** Менше 2.5
    • **Ймовірність:** 60%
    • **Обґрунтування:** В останніх 5 очних зустрічах команди не забивали більше двох м'ячів.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ти професійний спортивний аналітик. Дотримуйся заданого формату відповіді без сміття, таблиць та HTML."},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-20b",
            temperature=0.3,
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
                
