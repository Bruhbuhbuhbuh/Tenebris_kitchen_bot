import os
import re

import telebot
from telebot import types
from groq import Groq


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; if not installed, environment variables should be provided by the host
    pass

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def _valid_telegram_token(t: str) -> bool:
    if not t or ":" not in t:
        return False
    bot_id = t.split(":", 1)[0]
    return bot_id.isdigit()

if not TOKEN or not GROQ_API_KEY:
    raise RuntimeError(
        "Добавь переменные окружения: TELEGRAM_BOT_TOKEN и GROQ_API_KEY (см. .env.example)."
    )

if not _valid_telegram_token(TOKEN):
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN имеет неверный формат. Ожидается '<bot_id>:<token>' (пример: 123456789:ABC...). Проверьте .env."
    )

try:
    bot = telebot.TeleBot(TOKEN)
except ValueError as e:
    raise RuntimeError(
        "Ошибка инициализации Telegram-бота: проверьте переменную TELEGRAM_BOT_TOKEN."
    ) from e

groq_client = Groq(api_key=GROQ_API_KEY)


SYSTEM_PROMPT = """
Ты — AI-ассистент Telegram-бота, который помогает пользователю понять, что можно приготовить из того, что уже есть дома.

Главная идея: «Покажи, что у тебя есть — мы придумаем, что из этого приготовить».

Твоя задача:
- Анализировать список продуктов пользователя.
- Учитывать ограничения: тип питания, время, бюджет, количество людей, аллергии, запреты.
- Не придумывать продукты, которых нет у пользователя.
- Предлагать 3 реальных и практичных варианта блюд.
- Использовать как можно больше имеющихся продуктов.
- Указывать, что уже есть, что нужно купить и что можно заменить.
- Формат ответа должен быть удобен для Telegram: короткие блоки, эмодзи, списки, шаги.
- Если чего-то не хватает, предложить минимальную покупку.
- Если важных данных не хватает, задавать один короткий уточняющий вопрос.
- Не советовать испорченные продукты.

Формат ответа:
🍽️ Название блюда
⏱️ Время: ...
📊 Сложность: ...
👨‍🍳 Порции: ...

✅ Что есть дома:
- ...

🛒 Нужно купить:
- ...

🔄 Можно заменить:
- ...

Ингредиенты:
- ...

Приготовление:
1. ...
2. ...
3. ...

💡 Совет:
- ...

Всегда сохраняй практичность и понятность.
"""


PRODUCTS = [
    "яйца",
    "молоко",
    "картошка",
    "лук",
    "помидоры",
    "огурцы",
    "сыр",
    "колбаса",
    "рис",
    "гречка",
    "макароны",
    "курица",
    "рыба",
    "творог",
    "сметана",
    "хлеб",
    "мука",
    "масло",
    "соль",
    "перец",
    "зелень",
    "морковь",
    "капуста",
    "болгарский перец",
    "чеснок",
    "грибы",
    "баклажаны",
    "кабачки",
    "петрушка",
    "укроп",
    "шампиньоны",
    "соевый соус",
    "кетчуп",
    "майонез",
    "свёкла",
    "яблоки",
    "бананы",
]

STATE = {}


def get_user_state(chat_id):
    if chat_id not in STATE:
        STATE[chat_id] = {
            "products": [],
            "diet": "любая",
            "time": "любое",
            "budget": "любой",
            "people": 2,
        }
    return STATE[chat_id]


def normalize_products(raw_text):
    if not raw_text:
        return []

    cleaned = raw_text.lower()
    cleaned = cleaned.replace("/recipe", "")
    cleaned = cleaned.replace("/start", "")
    cleaned = cleaned.replace("\n", ",")
    cleaned = re.sub(r"[^а-яёa-z0-9,\-\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    parts = [p.strip() for p in cleaned.split(",")]
    result = []
    seen = set()

    for part in parts:
        part = part.strip(" -")
        if not part:
            continue
        normalized = " ".join(part.split())
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)

    return result


def make_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(
        types.KeyboardButton("🍳 Что приготовить?"),
        types.KeyboardButton("🧺 Добавить продукты"),
    )
    markup.row(
        types.KeyboardButton("🥗 Здоровая еда"),
        types.KeyboardButton("🍔 Фастфуд"),
    )
    markup.row(
        types.KeyboardButton("⚡ До 15 минут"),
        types.KeyboardButton("💰 Бюджетно"),
    )
    markup.row(
        types.KeyboardButton("🗑️ Очистить"),
        types.KeyboardButton("⚙️ Настройки"),
    )
    return markup


def make_products_keyboard(chat_id):
    state = get_user_state(chat_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

    row = []
    for product in PRODUCTS:
        label = f"✅ {product}" if product in state["products"] else product
        row.append(types.KeyboardButton(label))
        if len(row) == 3:
            markup.row(*row)
            row = []

    if row:
        markup.row(*row)

    markup.row(
        types.KeyboardButton("🍳 Что приготовить?"),
        types.KeyboardButton("🗑️ Очистить"),
    )
    return markup


def make_settings_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(
        types.KeyboardButton("🥗 Здоровая еда"),
        types.KeyboardButton("🍔 Фастфуд"),
    )
    markup.row(
        types.KeyboardButton("💪 Высокобелковая"),
        types.KeyboardButton("🥬 Вегетарианская"),
    )
    markup.row(
        types.KeyboardButton("⚡ До 15 минут"),
        types.KeyboardButton("⏱️ До 30 минут"),
    )
    markup.row(
        types.KeyboardButton("💰 Бюджетно"),
        types.KeyboardButton("👨‍🍳 Для 2 человек"),
    )
    markup.row(
        types.KeyboardButton("🔙 Главное меню"),
    )
    return markup


def generate_recipe_text(products, diet, time, budget, people):
    product_list = ", ".join(products) if products else "нет явно указанных продуктов"

    prompt = f"""
    Пользователь имеет продукты: {product_list}.
    Ограничения:
    - тип питания: {diet}
    - время: {time}
    - бюджет: {budget}
    - количество людей: {people}

    Сгенерируй строго 3 разных рецепта.
    Каждый рецепт должен быть реалистичным, удобным для Telegram и основан на реально имеющихся продуктах.
    Не придумывай продукты, которых нет. Если чего-то нехватает, укажи минимальную покупку.
    Не пишите длинный текст, а делайте короткий, понятный и полезный.

    Формат ответа:
    1. Название блюда
    ⏱️ Время:
    📊 Сложность:
    👨‍🍳 Порции:
    ✅ Что есть дома:
    🛒 Нужно купить:
    🔄 Можно заменить:
    Ингредиенты:
    Приготовление:
    💡 Совет:

    После трёх рецептов кратко напиши: "Выбери рецепт, и я быстро помогу адаптировать его под твои продукты или бюджет."
    """

    response = groq_client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=800,
    )
    try:
        return response.choices[0].message.content.strip()
    except Exception:
        return "Извините, AI-сервис временно недоступен. Попробуйте позже."


def handle_recipe_request(chat_id, raw_text=None):
    state = get_user_state(chat_id)
    products = state["products"]

    if raw_text:
        parsed = normalize_products(raw_text)
        if parsed:
            products = parsed
            state["products"] = parsed

    if not products:
        bot.send_message(
            chat_id,
            "Я не увидел продуктов. Напиши список через запятую или выбери продукты кнопками.\n\nПример: яйца, картошка, лук, сыр",
            reply_markup=make_products_keyboard(chat_id),
        )
        return

    result = generate_recipe_text(
        products=products,
        diet=state["diet"],
        time=state["time"],
        budget=state["budget"],
        people=state["people"],
    )

    bot.send_message(chat_id, result, reply_markup=make_main_keyboard())


@bot.message_handler(commands=["start", "help"])
def start_command(message):
    user_id = message.chat.id
    state = get_user_state(user_id)
    state["products"] = []

    bot.send_message(
        message.chat.id,
        "Привет! Я — AI-помощник по холодильнику.\n\n"
        "Напиши список продуктов или выбери их кнопками.\n"
        "После этого я подберу 3 рецепта под твои продукты, время и бюджет.\n\n"
        "Пример: яйца, картошка, лук, сыр",
        reply_markup=make_main_keyboard(),
    )


@bot.message_handler(commands=["clear"])
def clear_command(message):
    get_user_state(message.chat.id)["products"] = []
    bot.send_message(message.chat.id, "Список продуктов очищен. Можно начать заново.", reply_markup=make_main_keyboard())


@bot.message_handler(content_types=["text"])
def handle_text(message):
    text = message.text.strip()
    chat_id = message.chat.id
    state = get_user_state(chat_id)

    if text == "🔙 Главное меню":
        bot.send_message(chat_id, "Главное меню", reply_markup=make_main_keyboard())
        return

    if text == "🧺 Добавить продукты":
        bot.send_message(chat_id, "Выбери продукты из списка:", reply_markup=make_products_keyboard(chat_id))
        return

    if text == "🍳 Что приготовить?":
        handle_recipe_request(chat_id)
        return

    if text == "🗑️ Очистить":
        state["products"] = []
        bot.send_message(chat_id, "Список продуктов очищен.", reply_markup=make_products_keyboard(chat_id))
        return

    if text == "⚙️ Настройки":
        bot.send_message(chat_id, "Настройки поиска:", reply_markup=make_settings_keyboard())
        return

    if text == "🥗 Здоровая еда":
        state["diet"] = "здоровое питание"
        bot.send_message(chat_id, "Поставил фильтр: здоровая еда.", reply_markup=make_settings_keyboard())
        return

    if text == "🍔 Фастфуд":
        state["diet"] = "фастфуд"
        bot.send_message(chat_id, "Поставил фильтр: фастфуд.", reply_markup=make_settings_keyboard())
        return

    if text == "💪 Высокобелковая":
        state["diet"] = "высокобелковая еда"
        bot.send_message(chat_id, "Поставил фильтр: высокобелковая еда.", reply_markup=make_settings_keyboard())
        return

    if text == "🥬 Вегетарианская":
        state["diet"] = "вегетарианская"
        bot.send_message(chat_id, "Поставил фильтр: вегетарианская.", reply_markup=make_settings_keyboard())
        return

    if text == "⚡ До 15 минут":
        state["time"] = "до 15 минут"
        bot.send_message(chat_id, "Поставил фильтр: до 15 минут.", reply_markup=make_settings_keyboard())
        return

    if text == "⏱️ До 30 минут":
        state["time"] = "до 30 минут"
        bot.send_message(chat_id, "Поставил фильтр: до 30 минут.", reply_markup=make_settings_keyboard())
        return

    if text == "💰 Бюджетно":
        state["budget"] = "минимальный бюджет"
        bot.send_message(chat_id, "Поставил фильтр: бюджетно.", reply_markup=make_settings_keyboard())
        return

    if text == "👨‍🍳 Для 2 человек":
        state["people"] = 2
        bot.send_message(chat_id, "Поставил количество порций: 2 человека.", reply_markup=make_settings_keyboard())
        return

    if text in PRODUCTS:
        if text in state["products"]:
            state["products"].remove(text)
        else:
            state["products"].append(text)
        bot.send_message(chat_id, "Список продуктов обновлён.", reply_markup=make_products_keyboard(chat_id))
        return

    if text.startswith("✅ "):
        product = text.replace("✅ ", "", 1).strip()
        if product in PRODUCTS:
            if product in state["products"]:
                state["products"].remove(product)
            else:
                state["products"].append(product)
            bot.send_message(chat_id, "Список продуктов обновлён.", reply_markup=make_products_keyboard(chat_id))
            return

    if "," in text or " " in text:
        normalized = normalize_products(text)
        if normalized:
            state["products"] = normalized
            handle_recipe_request(chat_id, text)
            return

    bot.send_message(
        chat_id,
        "Напиши список продуктов или выбери их кнопками.\n\nНапример: яйца, картошка, сыр, лук",
        reply_markup=make_main_keyboard(),
    )


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📸 Получил фото, обрабатываю...")

    # Получаем самый большой по размеру файл (последний в списке)
    try:
        photo = message.photo[-1]
    except Exception:
        bot.send_message(chat_id, "Не удалось получить фото. Попробуйте ещё раз.")
        return

    file_id = photo.file_id
    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
    except Exception:
        bot.send_message(chat_id, "Ошибка при загрузке фото. Попробуйте ещё раз.")
        return

    # Сохраняем файл локально
    import os
    images_dir = os.path.join(os.getcwd(), "images")
    os.makedirs(images_dir, exist_ok=True)
    local_path = os.path.join(images_dir, f"{file_id}.jpg")
    try:
        with open(local_path, "wb") as f:
            f.write(downloaded)
    except Exception:
        bot.send_message(chat_id, "Не удалось сохранить фото на сервере.")
        return

    # Отправляем фото в Groq Vision для анализа продуктов
    if analyze_photo_with_groq(local_path, chat_id):
        return
    
    # Fallback: если Vision не смог распознать, просим описать
    bot.send_message(
        chat_id,
        "Фото сохранено, но я не смог распознать продукты. "
        "Напишите, что на нём видно (список через запятую), например: яйца, помидоры, сыр.",
        reply_markup=make_main_keyboard(),
    )


GENERIC_REQUEST_WORDS = {
    "что", "что можно", "что приготовить", "быстро", "ужин", "обед", "завтрак",
    "десерт", "сделай", "подскажи", "рецепт", "приготовить", "на ужин",
    "на обед", "на завтрак", "как", "можно", "есть", "хочу"
}


def looks_like_product_list(text: str) -> bool:
    if not text:
        return False

    normalized = normalize_products(text)
    if not normalized:
        return False

    for item in normalized:
        if item in PRODUCTS:
            return True

    if len(normalized) >= 2:
        return True

    first_word = normalized[0].lower()
    if first_word in GENERIC_REQUEST_WORDS:
        return False

    if any(word in first_word for word in ["приготовить", "ужин", "обед", "завтрак", "рецепт", "быстро"]):
        return False

    return False


@bot.message_handler(commands=["ai", "ask"])
def ai_command(message):
    command_text = message.text.replace("/ai", "", 1).replace("/ask", "", 1).strip()
    chat_id = message.chat.id
    state = get_user_state(chat_id)

    if not command_text:
        bot.send_message(
            message.chat.id,
            "Напиши, что сейчас лежит у тебя в холодильнике и на полках.\n\nПример: яйца, рис, курица, лук, масло, сыр.\n\nПосле этого я подберу 3 реальных рецепта."
        )
        return

    if not looks_like_product_list(command_text) and not state["products"]:
        bot.send_message(
            message.chat.id,
            "Привет! Чтобы я мог предложить 3 реальных рецепта, напиши, пожалуйста, что сейчас лежит у тебя в холодильнике и на полках.\n\nНапример: курица, рис, лук, масло, сыр, яйца.\n\nЖду твой список! 📝"
        )
        return

    if looks_like_product_list(command_text):
        state["products"] = normalize_products(command_text)

    # ask_groq may call the Groq chat completion API; implement fallback here
    prompt = (
        f"Пользователь спрашивает: {command_text}\n\n"
        f"У пользователя сейчас есть такие продукты: {', '.join(state['products']) if state['products'] else 'не указаны'}\n\n"
        "Отвечай как AI-помощник по холодильнику. Если продукты есть, используй их. Если чего-то нет — предложи минимальную замену или покупку. Отвечай кратко, понятно, по-русски и в формате Telegram."
    )

    try:
        answer = ask_groq(prompt, system_prompt="Ты — помощник по холодильнику и кулинарии. Отвечай кратко и по-русски.")
    except Exception:
        # fallback: use generate_recipe_text for a short reply
        try:
            answer = generate_recipe_text(
                products=state.get("products", []),
                diet=state.get("diet", "любая"),
                time=state.get("time", "любое"),
                budget=state.get("budget", "любой"),
                people=state.get("people", 2),
            )
        except Exception:
            answer = "Извините, сейчас временные проблемы с AI-сервисом. Попробуйте позже."

    bot.send_message(message.chat.id, answer)


def ask_groq(user_prompt: str, system_prompt: str = SYSTEM_PROMPT, temperature: float = 0.7, max_tokens: int = 800) -> str:
    """Send a chat completion request to Groq and return the assistant text."""
    response = groq_client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def generate_image_caption(image_path: str) -> str:
    """Generate a caption for an image using BLIP (Hugging Face transformers)."""
    try:
        from PIL import Image
        from transformers import BlipProcessor, BlipForConditionalGeneration
        
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        
        raw_image = Image.open(image_path).convert("RGB")
        inputs = processor(images=raw_image, return_tensors="pt")
        out = model.generate(**inputs, max_length=50)
        caption = processor.decode(out[0], skip_special_tokens=True)
        return caption.strip()
    except Exception as e:
        # Fall back gracefully if model download or inference fails
        return None


def analyze_photo_with_groq(image_path: str, chat_id: int) -> bool:
    """
    Send image to Groq Vision API to recognize products/food and generate recipes.
    Returns True if successful, False if fallback is needed.
    """
    try:
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    except Exception:
        return False

    try:
        # Groq Vision API supports image_url with data URI
        vision_prompt = (
            "Это изображение продуктов на холодильнике, столе или в кухне. "
            "Определи ВСЕ видимые продукты, ингредиенты, еду. "
            "Верни ТОЛЬКО список продуктов через запятую, без объяснений и лишних слов. "
            "Пример ответа: яйца, молоко, помидоры, огурцы, сыр, хлеб, масло"
        )
        
        response = groq_client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": vision_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.5,
            max_tokens=300,
        )
        
        products_text = response.choices[0].message.content.strip()
        if not products_text or len(products_text.split(",")) < 2:
            return False  # Not enough products recognized
        
        state = get_user_state(chat_id)
        normalized = normalize_products(products_text)
        
        if not normalized:
            return False
        
        state["products"] = normalized
        bot.send_message(chat_id, f"✅ Я вижу: {', '.join(normalized)}\n\n🍳 Подбираю рецепты...")
        
        # Generate recipes
        result = generate_recipe_text(
            products=normalized,
            diet=state.get("diet", "любая"),
            time=state.get("time", "любое"),
            budget=state.get("budget", "любой"),
            people=state.get("people", 2),
        )
        bot.send_message(chat_id, result, reply_markup=make_main_keyboard())
        return True
        
    except Exception as e:
        # Groq Vision call failed; return False to trigger fallback
        return False


if __name__ == "__main__":
    print("Bot started")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
