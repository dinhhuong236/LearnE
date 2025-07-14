from keep_alive import keep_alive
keep_alive()
import telebot
import os

# Nhập token từ bàn phím
API_KEY = os.getenv("B_API")
#input("Nhập API Token của bot Telegram: ").strip()

import telebot
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


bot = telebot.TeleBot(API_KEY)

@bot.message_handler(commands=['start'])
def greet(message):
    bot.reply_to(message, "Chào bạn! Tôi đang hoạt động.")




# Load vocab
with open('vocabulary.txt', encoding='utf-8') as f:
    lines = [line.strip() for line in f if '|' in line]
vocab = [tuple(line.split('|')) for line in lines]



# Lưu thông tin từng người dùng: câu đúng/sai, đáp án
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

    # Lưu trạng thái câu hỏi
    user_data[user_id]['current_question'] = {
        'word': correct[0],
        'meanings': meanings,
        'correct_index': correct_index
    }

    return correct[0], keyboard

# Hàm gửi tin nhắn kết quả + câu hỏi tiếp theo
def send_next_question(chat_id):
    data = user_data[chat_id]
    vocab_slice = data['vocab_slice']
    word, keyboard = create_question(chat_id, vocab_slice)

    bot.send_message(chat_id,
                     f"🔤 *Từ tiếng Anh:* `{word}`\n\nChọn nghĩa đúng:",
                     reply_markup=keyboard,
                     parse_mode='Markdown')

# Bắt đầu kiểm tra: /go hoặc /go 20-30
@bot.message_handler(commands=['go'])
def handle_go(message):
    chat_id = message.chat.id
    args = message.text.strip().split()

    # Mặc định: dùng toàn bộ vocab
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

    # Khởi tạo dữ liệu người dùng
    user_data[chat_id] = {
        'correct': 0,
        'wrong': 0,
        'vocab_slice': vocab_slice,
        'current_question': None
    }

    send_next_question(chat_id)

# Xử lý chọn đáp án
@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)

    if not data or not data.get('current_question'):
        bot.answer_callback_query(call.id, "❓ Không tìm thấy câu hỏi.")
        return

    selected_index = int(call.data)
    q = data['current_question']
    word = q['word']
    meanings = q['meanings']
    correct_index = q['correct_index']
    correct_meaning = meanings[correct_index]

    if selected_index == correct_index:
        data['correct'] += 1
        result = f"✅ *Chính xác!*\nTừ: `{word}`\nNghĩa đúng: `{correct_meaning}`"
    else:
        data['wrong'] += 1
        selected_meaning = meanings[selected_index]
        result = f"❌ *Sai rồi!*\nTừ: `{word}`\nBạn chọn: `{selected_meaning}`\nĐúng là: `{correct_meaning}`"

    total = data['correct'] + data['wrong']
    percent = round(data['correct'] / total * 100, 2) if total else 0.0
    score_text = f"\n📊 Kết quả: {data['correct']} đúng / {data['wrong']} sai ({percent}%)"

    # Gửi kết quả và câu tiếp theo
    bot.edit_message_text(chat_id=chat_id,
                          message_id=call.message.message_id,
                          text=result + score_text,
                          parse_mode='Markdown')
    send_next_question(chat_id)

bot.infinity_polling()





