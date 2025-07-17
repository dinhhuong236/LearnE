from keep_alive import keep_alive
keep_alive()

import telebot
import os
import random
import tempfile
from gtts import gTTS
from collections import defaultdict, deque
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

API_KEY = "7214717305:AAEgdgUC6qBuRwQsCPRN7kTjtypWR_tgbIE"#os.getenv("B_API")
bot = telebot.TeleBot(API_KEY)

# # Load vocab
# with open('vocabulary.txt', encoding='utf-8') as f:
#     lines = [line.strip() for line in f if '|' in line]
# vocab = [tuple(line.split('|')) for line in lines]

# Dữ liệu người dùng
user_data = {}

# --- Global variables ---
dict_folder = "dict"
default_dict_file = "vocabulary.txt"
current_dict = []
dict_name = ""
user_dicts = defaultdict(list)  # Temporary user dict storage
selected_user_dict = {}         # Track which user selected their own dict

# --- Load vocabulary from file ---
def load_dict(file_path):
    vocab = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) == 2:
                vocab.append((parts[0].strip(), parts[1].strip()))
    return vocab

# --- Dictionary file management ---
@bot.message_handler(commands=['listdict'])
def list_dicts(message):
    files = [f for f in os.listdir(dict_folder) if f.endswith(".txt")]
    if not files:
        bot.reply_to(message, "Không tìm thấy từ điển nào trong thư mục.")
        return
    reply = "Danh sách từ điển có sẵn:\n"
    for i, f in enumerate(files):
        reply += f"{i+1}. {f}\n"
    bot.reply_to(message, reply)

@bot.message_handler(commands=['selectdict'])
def select_dict(message):
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(message, "Dùng đúng định dạng: /selectdict <số thứ tự từ điển>")
        return
    index = int(parts[1]) - 1
    files = [f for f in os.listdir(dict_folder) if f.endswith(".txt")]
    if 0 <= index < len(files):
        global current_dict, dict_name
        dict_name = files[index]
        current_dict = load_dict(os.path.join(dict_folder, dict_name))
        bot.reply_to(message, f"Đã chọn từ điển: {dict_name} với {len(current_dict)} từ.")
    else:
        bot.reply_to(message, "Chỉ số không hợp lệ.")

# --- User dictionary management ---
@bot.message_handler(commands=['newdict'])
def new_dict(message):
    user_id = message.from_user.id
    user_dicts[user_id] = []
    bot.reply_to(message, "Đã tạo từ điển tạm thời cho bạn. Dùng /add word|mean để thêm từ.")

@bot.message_handler(commands=['add'])
def add_word(message):
    user_id = message.from_user.id
    if user_id not in user_dicts:
        bot.reply_to(message, "Bạn chưa tạo từ điển. Dùng /newdict để tạo.")
        return
    try:
        _, content = message.text.split(' ', 1)
        word, mean = content.split('|')
        if len('|'.join([word, mean]).encode('utf-8')) > 100:
            bot.reply_to(message, "Từ quá dài.")
            return
        user_dicts[user_id].append((word.strip(), mean.strip()))
        bot.reply_to(message, f"Đã thêm: {word.strip()} | {mean.strip()}")
    except:
        bot.reply_to(message, "Định dạng sai. Dùng /add từ|nghĩa")

@bot.message_handler(commands=['selectuserdict'])
def use_user_dict(message):
    user_id = message.from_user.id
    if user_id not in user_dicts or not user_dicts[user_id]:
        bot.reply_to(message, "Từ điển của bạn chưa có dữ liệu.")
        return
    global current_dict, dict_name
    selected_user_dict[user_id] = True
    current_dict = user_dicts[user_id]
    dict_name = f"user_{user_id}.txt"
    bot.reply_to(message, "Đã chuyển sang dùng từ điển riêng của bạn.")

@bot.message_handler(commands=['download'])
def download_dict(message):
    user_id = message.from_user.id
    data = current_dict if selected_user_dict.get(user_id) else load_dict(os.path.join(dict_folder, dict_name))
    if not data:
        bot.reply_to(message, "Không có dữ liệu để tải.")
        return
    file_path = f"temp_dict_{user_id}.txt"
    with open(file_path, 'w', encoding='utf-8') as f:
        for word, mean in data:
            f.write(f"{word}|{mean}\n")
    with open(file_path, 'rb') as f:
        bot.send_document(message.chat.id, f)
    os.remove(file_path)

# --- Default dictionary on start ---
if not os.path.exists(dict_folder):
    os.makedirs(dict_folder)

default_path = os.path.join(dict_folder, default_dict_file)
if os.path.exists(default_path):
    current_dict = load_dict(default_path)
    dict_name = default_dict_file
@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "📚 *Hướng dẫn sử dụng bot học từ vựng tiếng Anh*\n\n"
        "🟢 **Bắt đầu luyện tập:**\n"
        "`/go 1-100` – Luyện từ vựng từ dòng 1 đến 100 trong danh sách.\n"
        "Bạn cần chọn đúng nghĩa của từ được hỏi. Sau mỗi câu có thể xem ví dụ sử dụng.\n\n"

        "🔄 **Tùy chỉnh hiển thị câu ví dụ:**\n"
        "`/setsentence 5 0` – Hiển thị 5 câu ví dụ, độ khó 0 (dễ).\n"
        "`/setsentence 10 1` – Hiển thị 10 câu, độ khó 1 (khó).\n\n"

        "🔊 **Âm thanh:**\n"
        "`/mute` – Tắt phát âm từ.\n"
        "`/unmute` – Bật phát âm từ.\n\n"

        "📌 **Ưu tiên các từ sai nhiều:**\n"
        "`/priority 3` – Ưu tiên hiển thị lại các từ sai, trọng số = 3.\n"
        "`/nopriority` – Tắt ưu tiên.\n\n"

        "🔍 **Tìm câu ví dụ cho một từ hoặc cụm từ:**\n"
        "`/find từ` – Tìm 5 câu dễ mặc định.\n"
        "`/find từ số_câu` – Ví dụ: `/find look up 10`\n"
        "`/find từ số_câu độ_khó` – Ví dụ: `/find look up 10 1`\n"
        "- `độ_khó = 0`: dễ, `1`: khó\n"
        "- Hỗ trợ tìm cả các từ có `-` hoặc có khoảng trắng như `check-in`, `check in`\n\n"

        "📊 **Sau mỗi câu hỏi:**\n"
        "- Bạn sẽ biết mình đúng/sai, kèm theo điểm số.\n"
        "- Có thể xem thêm câu ví dụ bằng nút 📘 *Show usages*.\n\n"

        "Chúc bạn học từ vựng hiệu quả! 💪"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def greet(message):
    bot.reply_to(message, "Chào bạn! Tôi đang hoạt động.")

@bot.message_handler(commands=['go'])
def handle_go(message):
    chat_id = message.chat.id
    args = message.text.strip().split()
    vocab_slice = current_dict

    if len(args) == 2 and '-' in args[1]:
        try:
            start, end = map(int, args[1].split('-'))
            if start < 1 or end > len(current_dict) or start >= end:
                raise ValueError()
            vocab_slice = current_dict[start - 1:end]
        except:
            bot.reply_to(message,
                         f"❗ Khoảng dòng không hợp lệ. Nhập lại: `/go 20-30` (1–{len(current_dict)})",
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
        'sentence_count': 5,
        'sentence_level': 0
    }

    send_next_question(chat_id)

@bot.message_handler(commands=['setsentence'])
def set_sentence_param(message):
    chat_id = message.chat.id
    args = message.text.strip().split()
    if len(args) != 3 or not args[1].isdigit() or not args[2] in ['0', '1']:
        bot.reply_to(message, "❗ Dùng: /setsentence a b Trong đó a: số câu, b: 0 (dễ) hoặc 1 (khó)")
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
@bot.message_handler(commands=['find'])
def handle_find(message):
    chat_id = message.chat.id
    args = message.text.strip().split()

    if len(args) < 2:
        bot.reply_to(message, "❗ Dùng: `/find từ [số_câu] [độ_khó]`\nVí dụ: `/find look up 10 1`", parse_mode="Markdown")
        return

    try:
        # Kiểm tra nếu có độ khó ở cuối
        level = int(args[-1]) if args[-1] in ['0', '1'] else 0
        count = int(args[-2]) if args[-2].isdigit() else 5
        word_parts = args[1:-2] if args[-2].isdigit() and args[-1] in ['0', '1'] else \
                     args[1:-1] if args[-1].isdigit() else \
                     args[1:]

        word = ' '.join(word_parts).strip()
    except Exception as e:
        bot.reply_to(message, f"❗ Cú pháp sai. Dùng: `/find từ [số_câu] [độ_khó]`", parse_mode="Markdown")
        return

    samples = extract_sentences(word, count=count, level=level)
    reply = f"📘 *Câu ví dụ chứa từ* `{word}`:\n\n"
    reply += '\n'.join(f"- {s}" for s in samples) if samples else "(Không tìm thấy)"
    bot.send_message(chat_id, reply, parse_mode='Markdown')



import requests

# def extract_sentences(word, count=5, level=0):
#     """
#     Lấy câu ví dụ từ API của Tatoeba cho từ tiếng Anh `word`.
#     `count`: số câu muốn lấy.
#     """
#     try:
#         url = f"https://tatoeba.org/eng/api_v0/search?query={word}&from=eng&orphans=no&unapproved=no&native=no&has_audio=no&sort=relevance"
#         response = requests.get(url, timeout=5)
#         data = response.json()
#         results = [item["text"] for item in data.get("results", []) if word.lower() in item["text"].lower()]
#         return results[:count]
#     except Exception as e:
#         return [f"(Lỗi khi truy cập Tatoeba: {e})"]

def extract_sentences(word, folder='dataset', count=5, level=0):
    results = []
    filenames = sorted(
        [f for f in os.listdir(folder) if f.startswith("sentences_data_") and f.endswith(".tsv")],
        key=lambda x: int(x.replace("sentences_data_", "").replace(".tsv", "")),
        reverse=(level == 1)
    )

    # Tạo các biến thể của từ để kiểm tra
    word_clean = word.strip().lower()
    variants = set()
    variants.add(word_clean)
    if '-' in word_clean:
        variants.add(word_clean.replace('-', ' '))
    if ' ' in word_clean:
        variants.add(word_clean.replace(' ', '-'))

    for filename in filenames:
        path = os.path.join(folder, filename)
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        sentence = parts[2].lower()
                        if any(v in sentence for v in variants):
                            results.append(parts[2])
                            if len(results) >= count:
                                return results
        except Exception as e:
            print(f"Lỗi đọc {filename}: {e}")

    return results


#     return results  # nếu tìm được ít hơn count, vẫn trả về

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
        samples = extract_sentences(word_en, count=data.get('sentence_count', 5), level=data.get('sentence_level', 0))
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