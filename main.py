
from keep_alive import keep_alive
keep_alive()

import telebot
import os
import random
from gtts import gTTS
import tempfile
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

API_KEY = os.getenv("B_API")
bot = telebot.TeleBot(API_KEY)

@bot.message_handler(commands=['start'])
def greet(message):
    bot.reply_to(message, "Chào bạn! Tôi đang hoạt động.")

# Load vocab
with open('vocabulary.txt', encoding='utf-8') as f:
    lines = [line.strip() for line in f if '|' in line]
vocab = [tuple(line.split('|')) for line in lines]

# Lưu thông tin từng người dùng
user_data = {}

# Gửi một câu hỏi
def create_question(user_id, vocab_slice):
    correct = random.choice(vocab_slice)
    distractors = random.sample([v for v in vocab_slice if v != correct], 3)
    all_options = [correct] + distractors
    random.shuffle(all_options)

    meanings = [item[1] for item in all_options]
    correct_index = all_options.index(correct)

    keyboard = InlineKeyboardMarkup()
    for idx, meaning in enumerate(meanings):
        keyboard.add(InlineKeyboardButton(meaning, callback_data=str(idx)))

    user_data[user_id]['current_question'] = {
        'word': correct[0],
        'meanings': meanings,
        'correct_index': correct_index
    }

    return correct[0], keyboard

# Gửi câu tiếp theo
def send_next_question(chat_id):
    data = user_data[chat_id]
    vocab_slice = data['vocab_slice']
    word, keyboard = create_question(chat_id, vocab_slice)

    bot.send_message(chat_id,
                     f"🔤 *Từ tiếng Anh:* `{word}`\n\nChọn nghĩa đúng:",
                     reply_markup=keyboard,
                     parse_mode='Markdown')

@bot.message_handler(commands=['go'])
def handle_go(message):
    chat_id = message.chat.id
    args = message.text.strip().split()
    vocab_slice = vocab

    if len(args) == 2 and '-' in args[1]:
        try:
            start, end = map(int, args[1].split('-'))
            if start < 1 or end > len(vocab) or start >= end:
                raise ValueError("Khoảng không hợp lệ")
            vocab_slice = vocab[start-1:end]
        except:
            bot.reply_to(message,
                         f"❗ Khoảng dòng không hợp lệ. Hãy nhập lại lệnh như: `/go 20-30`\nChọn trong khoảng 1–{len(vocab)}.",
                         parse_mode="Markdown")
            return

    if len(vocab_slice) < 4:
        bot.reply_to(message, "❗ Cần ít nhất 4 từ để tạo câu hỏi.")
        return

    user_data[chat_id] = {
        'correct': 0,
        'wrong': 0,
        'vocab_slice': vocab_slice,
        'current_question': None
    }

    send_next_question(chat_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)

    if not data or not data.get('current_question'):
        bot.answer_callback_query(call.id, "❓ Không tìm thấy câu hỏi.")
        return

    selected_index = int(call.data)
    q = data['current_question']
    word_full = q['word']
    word_en = word_full.split('/')[0].strip()
    meanings = q['meanings']
    correct_index = q['correct_index']
    correct_meaning = meanings[correct_index]

    if selected_index == correct_index:
        data['correct'] += 1
        result = f"✅ *Chính xác!*\nTừ: `{word_full}`\nNghĩa đúng: `{correct_meaning}`"
    else:
        data['wrong'] += 1
        selected_meaning = meanings[selected_index]
        result = f"❌ *Sai rồi!*\nTừ: `{word_full}`\nBạn chọn: `{selected_meaning}`\nĐúng là: `{correct_meaning}`"

    total = data['correct'] + data['wrong']
    percent = round(data['correct'] / total * 100, 2) if total else 0.0
    score_text = f"\n📊 Kết quả: {data['correct']} đúng / {data['wrong']} sai ({percent}%)"

    bot.edit_message_text(chat_id=chat_id,
                          message_id=call.message.message_id,
                          text=result + score_text,
                          parse_mode='Markdown',
                          disable_web_page_preview=True)

    # Gửi giọng đọc từ
    try:
        tts = gTTS(text=word_en, lang='en')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tts.save(tmp.name)
            bot.send_chat_action(chat_id, 'upload_audio')
            bot.send_voice(chat_id, voice=open(tmp.name, 'rb'))
        os.unlink(tmp.name)
    except Exception as e:
        bot.send_message(chat_id, f"Không thể phát âm từ `{word_en}`. Lỗi: {e}", parse_mode='Markdown')

    send_next_question(chat_id)

bot.infinity_polling()
