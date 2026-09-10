import os
import threading
import time
import requests
from flask import Flask
import telebot
from groq import Groq

# 1. Отримання ключів з налаштувань сервера
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
FOOTBALL_DATA_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
app = Flask(__name__)

@app.route('/')
def home():
    return "Football AI Bot is Running!", 200

def keep_alive():
    while True:
        time.sleep(600)
        if RENDER_URL:
            try:
                requests.get(RENDER_URL)
            except Exception as e:
                print(f"Self-ping error: {e}")

# Функція для автоматичного пошуку даних про матч
def get_football_data(query):
    if not FOOTBALL_DATA_TOKEN:
        return "Дані з API недоступні."
    
    headers = {'X-Auth-Token': FOOTBALL_DATA_TOKEN}
    try:
        url = "https://api.football-data.org/v4/matches"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            matches_info = []
            for match in data.get('matches', [])[:15]:
                home = match['homeTeam']['name']
                away = match['awayTeam']['name']
                competition = match['competition']['name']
                matches_info.append(f"{competition}: {home} vs {away}")
            return "\n".join(matches_info)
    except Exception as e:
        print(f"API Error: {e}")
    return "Не вдалося отримати точні live-дані з API, використовую базові знання."

# Системний промпт для ШІ-аналітика
SYSTEM_PROMPT = """
Ти — професійний спортивний аналітик та каппер із 10-річним досвідом.
Твоє завдання: глибоко аналізувати футбольний матч за запитом користувача.

Твій аналіз повинен включати розрахунки за наступними лініями:
1. 📊 Результат матчу (П1 / X / П2) — ймовірність у %
2. ⚽ Тотал матчу (Більше/Менше 2.5) — ймовірність у %
3. 🛡️ Фора команд (Ф1 / Ф2) — ймовірність у %
4. 🚩 Кутові та Картки — прогнозований діапазон та ймовірність в %
5. 🚑 Травми, дискваліфікації та xG показники (на основі відомої статистики)

⚠️ ОБОВ'ЯЗКОВИЙ ПУНКТ НАПРЕКІНЦІ:
Вибери ОДИН НАЙБІЛЬШ ВІРОГІДНИЙ варіант ставки серед усіх ліній (найкращий Value Bet).
Виведи його чітко у форматі:
"🔥 НАЙБІЛЬШ ВІРОГІДНА СТАВКА: [Назва лінії та вибір] (Вірогідність: X%) — [Коротке обґрунтування]"
"""

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Привіт! Я твій особистий AI-аналітик футбольних матчів. ⚽🤖\n\n"
        "Напиши мені назву двох команд (наприклад: *Арсенал - Челсі* або *Реал Мадрид - Барселона*), "
        "і я підтягну статистику та згенерую повний аналіз із найвірогіднішим прогнозом!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def analyze_match(message):
    user_input = message.text
    bot.send_message(message.chat.id, f"🔍 Збираю статистику, xG та аналізую матч: *{user_input}*...", parse_mode="Markdown")

    live_stats = get_football_data(user_input)

    prompt = f"""
    Проаналізуй футбольний матч: {user_input}
    
    Додатковий контекст з API (найближчі матчі/ліги):
    {live_stats}
    
    Зроби детальний розрахунок відсотків для кожної лінії та вибери ЄДИНИЙ найкращий варіант ставки.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",

            
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
    threading.Thread(target=run_bot, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
