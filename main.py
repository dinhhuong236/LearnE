from keep_alive import keep_alive
keep_alive()

import telebot
import os
import random
import tempfile
from gtts import gTTS
from collections import defaultdict, deque
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

API_KEY = os.getenv("B_API")
bot = telebot.TeleBot(API_KEY)

# Load vocab
with open('vocabulary.txt', encoding='utf-8') as f:
    lines = [line.strip() for line in f if '|' in line]
vocab = [tuple(line.split('|')) for line in lines]

# Dữ liệu người dùng
user_data = {}

@bot.message_handler(commands=['start'])
def greet(message):
    bot.reply_to(message, "Chào bạn! Tôi đang hoạt động.")

@bot.message_handler(commands=['go'])
def handle_go(message):
    chat_id = message.chat.id
    args = message.text.strip().split()
    vocab_slice = vocab

    if len(args) == 2 and '-' in args[1]:
        try:
            start, end = map(int, args[1].split('-'))
            if start < 1 or end > len(vocab) or start >= end:
                raise ValueError()
            vocab_slice = vocab[start - 1:end]
        except:
            bot.reply_to(message,
                         f"❗ Khoảng dòng không hợp lệ. Nhập lại: `/go 20-30` (1–{len(vocab)})",
                         parse_mode="Markdown")
            return

    if len(vocab_slice) < 4:
        bot.reply_to(message, "❗ Cần ít nhất 4 từ.")
        return

    user_data[chat_id] = {
        'correct': 0,
        'wrong': 0,
        'vocab_slice': vocab_slice,
        'current_question': None,
        'mute': False,
        'user_messages': [],
        'show_count': defaultdict(int),
        'target_count': defaultdict(lambda: 1),
        'recent_words': deque([], maxlen=5),
        'priority_weight': 2,
        'sentence_count': 3,
        'sentence_level': 0
    }

    send_next_question(chat_id)

@bot.message_handler(commands=['setsentence'])
def set_sentence_param(message):
    chat_id = message.chat.id
    args = message.text.strip().split()
    if len(args) != 3 or not args[1].isdigit() or not args[2] in ['0', '1']:
        bot.reply_to(message, "❗ Dùng: /setsentence a b
Trong đó a: số câu, b: 0 (dễ) hoặc 1 (khó)")
        return
    a = int(args[1])
    b = int(args[2])
    user_data.setdefault(chat_id, {})['sentence_count'] = a
    user_data.setdefault(chat_id, {})['sentence_level'] = b
    bot.reply_to(message, f"📘 Đã đặt số câu ví dụ: {a}, độ khó: {b}")

@bot.message_handler(commands=['mute'])
def handle_mute(message):
    chat_id = message.chat.id
    user_data.setdefault(chat_id, {})['mute'] = True
    bot.reply_to(message, "🔇 Đã tắt độc phát âm.")

@bot.message_handler(commands=['unmute'])
def handle_unmute(message):
    chat_id = message.chat.id
    user_data.setdefault(chat_id, {})['mute'] = False
    bot.reply_to(message, "🔊 Đã bật độc phát âm.")

@bot.message_handler(commands=['priority'])
def handle_priority(message):
    chat_id = message.chat.id
    args = message.text.strip().split()
    val = 2
    if len(args) == 2 and args[1].isdigit():
        val = int(args[1])
    user_data.setdefault(chat_id, {})['priority_weight'] = val
    bot.reply_to(message, f"📌 Đã bật ưu tiên sai. Trọng số = {val}.")

@bot.message_handler(commands=['nopriority'])
def handle_nopriority(message):
    chat_id = message.chat.id
    user_data.setdefault(chat_id, {})['priority_weight'] = 0
    bot.reply_to(message, "❌ Đã tắt ưu tiên sai.")

def extract_sentences(word, folder='dataset', count=5, level=0):
    import heapq
    results = []
    files = sorted([
        f for f in os.listdir(folder)
        if f.startswith("sentences_data_") and f.endswith(".tsv")
    ], key=lambda x: int(x.replace("sentences_data_", "").replace(".tsv", "")), reverse=(level == 1))

    for file in files:
        with open(os.path.join(folder, file), encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 3 and word.lower() in parts[2].lower():
                    heapq.heappush(results, (len(parts[2].split()), parts[2]))
                    if len(results) > count:
                        heapq.heappop(results)
    return [s for _, s in sorted(results)]

def create_question(user_id, vocab_slice):
    data = user_data[user_id]
    show_count = data['show_count']
    target_count = data['target_count']
    recent_words = set(data['recent_words'])

    candidates = [(item, target_count[item[0]] - show_count[item[0]])
                  for item in vocab_slice if item[0] not in recent_words]
    if not candidates:
        candidates = [(item, target_count[item[0]] - show_count[item[0]])
                      for item in vocab_slice]

    candidates.sort(key=lambda x: (-x[1], random.random()))
    correct = candidates[0][0]

    show_count[correct[0]] += 1
    data['recent_words'].append(correct[0])

    distractors = random.sample([v for v in vocab_slice if v != correct], 3)
    all_options = [correct] + distractors
    random.shuffle(all_options)

    meanings = [item[1] for item in all_options]
    correct_index = all_options.index(correct)

    keyboard = InlineKeyboardMarkup()
    for idx, meaning in enumerate(meanings):
        keyboard.add(InlineKeyboardButton(meaning, callback_data=str(idx)))
    keyboard.add(InlineKeyboardButton("📘 Show usages", callback_data='show_usages'))

    data['current_question'] = {
        'word': correct[0],
        'meanings': meanings,
        'correct_index': correct_index
    }

    return correct[0], keyboard

def send_next_question(chat_id):
    data = user_data[chat_id]
    word, keyboard = create_question(chat_id, data['vocab_slice'])
    bot.send_message(chat_id,
                     f"🄤 *Từ tiếng Anh:* `{word}`\n\nChọn nghĩa đúng:",
                     reply_markup=keyboard,
                     parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)

    if not data or not data.get('current_question'):
        bot.answer_callback_query(call.id, "❓ Không tìm thấy câu hỏi.")
        return

    if call.data == 'show_usages':
        word_full = data['current_question']['word']
        word_en = word_full.split('/')[0].strip()
        samples = extract_sentences(word_en, count=data.get('sentence_count', 3), level=data.get('sentence_level', 0))
        reply = f"📘 *Câu ví dụ chứa từ* `{word_en}`:\n\n"
        reply += '\n'.join(f"- {s}" for s in samples) if samples else "(Không tìm thấy)"
        bot.send_message(chat_id, reply, parse_mode='Markdown')
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
        result = f"✅ *Chính xác!\nTừ:* `{word_full}`\nNghĩa: `{correct_meaning}`"
    else:
        data['wrong'] += 1
        selected_meaning = meanings[selected_index]
        result = f"❌ *Sai!*\nTừ: `{word_full}`\nChọn: `{selected_meaning}`\nĐúng: `{correct_meaning}`"
        data['target_count'][word_full] += data.get('priority_weight', 2)

    total = data['correct'] + data['wrong']
    percent = round(data['correct'] / total * 100, 2) if total else 0.0
    score = f"\n📊 Kết quả: {data['correct']} đúng / {data['wrong']} sai ({percent}%)"

    bot.edit_message_text(chat_id=chat_id,
                          message_id=call.message.message_id,
                          text=result + score,
                          parse_mode='Markdown')

    # Voice
    if not data.get('mute', False):
        try:
            tts = gTTS(text=word_en, lang='en')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                tts.save(tmp.name)
                msg = bot.send_voice(chat_id, voice=open(tmp.name, 'rb'))
            os.unlink(tmp.name)
            data['user_messages'].append(msg.message_id)
            if len(data['user_messages']) > 10:
                old = data['user_messages'].pop(0)
                try:
                    bot.delete_message(chat_id, old)
                except:
                    pass
        except Exception as e:
            bot.send_message(chat_id, f"Lỗi phát âm: {e}")

    send_next_question(chat_id)

bot.infinity_polling()
