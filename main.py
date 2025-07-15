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

# Load vocab từ file
with open('vocabulary.txt', encoding='utf-8') as f:
    lines = [line.strip() for line in f if '|' in line]
vocab = [tuple(line.split('|')) for line in lines]

# Lưu thông tin người dùng
user_data = {}

# Gửi 1 câu hỏi
def create_question(user_id):
    data = user_data[user_id]
    usage = data['usage']
    vocab_slice = data['vocab_slice']
    priority_weight = data.get('priority_weight', 2)

    # Tạo danh sách câu hỏi có thể chọn (ưu tiên chưa hiện nhiều hoặc trả lời sai)
    weighted_vocab = []
    for idx, word in enumerate(vocab_slice):
        count = usage.get(idx, 0)
        weight = max(0, 2 - count)  # Chỉ xuất hiện tối đa 2 lần mỗi chu kỳ
        if weight > 0:
            weighted_vocab += [idx] * weight

        # Nếu có ưu tiên sai
        if data.get("priority") and idx in data.get("wrong_counts", {}):
            wrongs = data["wrong_counts"][idx]
            weighted_vocab += [idx] * (priority_weight * wrongs)

    if len(weighted_vocab) < 4:
        # Reset chu kỳ
        data['usage'] = {}
        for idx in range(len(vocab_slice)):
            data['usage'][idx] = 0
        return create_question(user_id)

    # Chọn từ đúng
    correct_idx = random.choice(weighted_vocab)
    correct = vocab_slice[correct_idx]
    data['usage'][correct_idx] = data['usage'].get(correct_idx, 0) + 1

    # Chọn 3 đáp án sai
    distractors = random.sample([v for i, v in enumerate(vocab_slice) if i != correct_idx], 3)
    all_options = [correct] + distractors
    random.shuffle(all_options)

    meanings = [item[1] for item in all_options]
    correct_index = all_options.index(correct)

    keyboard = InlineKeyboardMarkup()
    for idx, meaning in enumerate(meanings):
        keyboard.add(InlineKeyboardButton(meaning, callback_data=str(idx)))

    data['current_question'] = {
        'correct_idx': correct_idx,
        'word': correct[0],
        'meanings': meanings,
        'correct_index': correct_index
    }

    return correct[0], keyboard

# Gửi câu tiếp theo
def send_next_question(chat_id):
    word, keyboard = create_question(chat_id)
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
                         f"❗ Khoảng dòng không hợp lệ. Hãy nhập: `/go 20-30` (1–{len(vocab)})",
                         parse_mode="Markdown")
            return

    if len(vocab_slice) < 4:
        bot.reply_to(message, "❗ Cần ít nhất 4 từ để tạo câu hỏi.")
        return

    user_data[chat_id] = {
        'correct': 0,
        'wrong': 0,
        'vocab_slice': vocab_slice,
        'usage': {},  # Số lần hiển thị mỗi từ
        'wrong_counts': {},  # Số lần trả lời sai
        'current_question': None,
        'mute': False,
        'priority': False,
        'priority_weight': 2,
        'user_messages': []
    }

    send_next_question(chat_id)

@bot.message_handler(commands=['priority'])
def enable_priority(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return bot.reply_to(message, "Bạn cần dùng lệnh /go trước.")
    args = message.text.strip().split()
    weight = 2
    if len(args) == 2 and args[1].isdigit():
        weight = int(args[1])
    user_data[chat_id]['priority'] = True
    user_data[chat_id]['priority_weight'] = weight
    bot.reply_to(message, f"📌 Ưu tiên từ sai đã được bật (mức độ: {weight})")

@bot.message_handler(commands=['nopriority'])
def disable_priority(message):
    chat_id = message.chat.id
    if chat_id in user_data:
        user_data[chat_id]['priority'] = False
    bot.reply_to(message, "🚫 Đã tắt ưu tiên từ sai.")

@bot.message_handler(commands=['mute'])
def handle_mute(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['mute'] = True
    bot.reply_to(message, "🔇 Đã tắt phát âm.")

@bot.message_handler(commands=['unmute'])
def handle_unmute(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['mute'] = False
    bot.reply_to(message, "🔊 Đã bật phát âm.")

@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)

    if not data or not data.get('current_question'):
        bot.answer_callback_query(call.id, "❓ Không tìm thấy câu hỏi.")
        return

    selected_index = int(call.data)
    q = data['current_question']
    correct_idx = q['correct_idx']
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
        data['wrong_counts'][correct_idx] = data['wrong_counts'].get(correct_idx, 0) + 1

    total = data['correct'] + data['wrong']
    percent = round(data['correct'] / total * 100, 2) if total else 0.0
    score_text = f"\n📊 Kết quả: {data['correct']} đúng / {data['wrong']} sai ({percent}%)"

    bot.edit_message_text(chat_id=chat_id,
                          message_id=call.message.message_id,
                          text=result + score_text,
                          parse_mode='Markdown',
                          disable_web_page_preview=True)

    # Gửi voice nếu không mute
    if not data.get('mute', False):
        try:
            tts = gTTS(text=word_en, lang='en')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                tts.save(tmp.name)
                msg = bot.send_voice(chat_id, voice=open(tmp.name, 'rb'))
            os.unlink(tmp.name)
            data['user_messages'].append(msg.message_id)
            if len(data['user_messages']) > 10:
                old_msg_id = data['user_messages'].pop(0)
                try:
                    bot.delete_message(chat_id, old_msg_id)
                except:
                    pass
        except Exception as e:
            bot.send_message(chat_id, f"Không thể phát âm từ `{word_en}`.\nLỗi: {e}", parse_mode="Markdown")

    send_next_question(chat_id)

bot.infinity_polling()
