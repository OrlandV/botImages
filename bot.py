"""
Многофункциональный телеграм-бот
"""
import telebot
from PIL import Image, ImageOps
import io
from telebot import types

from config import TOKEN

# Набор символов, из которых составляем изображение.
ASCII_CHARS = '@%#*+=-:. '

# Хранилище информации о действиях пользователя.
user_states = {}

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """
    Обработчик команд /start и /help.
    :param message: Команда (сообщение пользователя).
    """
    bot.reply_to(message, "Пришлите мне изображение, и я предложу Вам варианты!")


def get_options_keyboard():
    """
    Формирование клавиатуры главных режимов.
    :return: Клавиатура.
    """
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Пикселизация", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII-арт", callback_data="ascii")
    invert_btn = types.InlineKeyboardButton('Инверсия цветов', callback_data='invert')
    keyboard.add(pixelate_btn, ascii_btn, invert_btn)
    return keyboard


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """
    Обработчик изображений пользователя.
    :param message: Изображение (сообщение) пользователя.
    """
    bot.reply_to(message, "У меня есть Ваша фотография! Пожалуйста, выберите, что бы Вы хотели с ней сделать.",
                 reply_markup=get_options_keyboard())
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}


def pixelate_image(image, pixel_size: int):
    """
    Огрубление изображения (создание пиксельного эффекта).
    :param image: Изображение.
    :param pixel_size: Размер пикселя.
    :return: Новое изображение.
    """
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


def pixelate_and_send(message):
    """
    Пикселизация изображения и отправка его обратно пользователю.
    :param message: Сообщение пользователя с изображением.
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)
    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def get_charset_keyboard():
    """
    Формирование клавиатуры наборов символов.
    :return: Клавиатура.
    """
    keyboard = types.InlineKeyboardMarkup()
    input_btn = types.InlineKeyboardButton("Ввести свой набор", callback_data="input")
    default_btn = types.InlineKeyboardButton("Использовать набор по умолчанию", callback_data="default")
    keyboard.add(input_btn, default_btn)
    return keyboard


def invert_colors(message):
    """
    Инверсия цветов изображения и отправка его обратно пользователю.
    :param message: Сообщение пользователя с изображением.
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    invert_image = ImageOps.invert(image)
    output_stream = io.BytesIO()
    invert_image.save(output_stream, format='JPEG')
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def pixels_to_ascii(image, chars: str = ASCII_CHARS):
    """
    Конвертор пикселей изображения в градациях серого в строку ASCII-символов, используя предопределенную строку.
    :param image: Изображение в градациях серого.
    :param chars: Набор ASCII-символов.
    :return: Строка ASCII-символов.
    """
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += chars[pixel * len(chars) // 256]
    return characters


def image_to_ascii(image_stream, new_width: int = 40, chars: str = ASCII_CHARS):
    """
    Преобразование изображения в ASCII-арт.
    :param image_stream: Файл изображения (байт-строка).
    :param new_width: Новая ширина в символах.
    :param chars: Набор ASCII-символов.
    :return: ASCII-арт.
    """
    # Конвертирование в оттенки серого.
    image = Image.open(image_stream).convert('L')
    # Изменение размера, сохраняя отношение сторон.
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(aspect_ratio * new_width * 0.55)  # 0,55 так как высота букв больше, чем ширина.
    img_resized = image.resize((new_width, new_height))
    img_str = pixels_to_ascii(img_resized, chars)
    img_width = img_resized.width
    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)
    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"
    return ascii_art


def ascii_and_send(message, chars: str = ASCII_CHARS):
    """
    Преобразование изображения в ASCII-арт и отправка результата в виде текстового сообщения.
    :param message: Сообщение пользователя.
    :param chars: Набор ASCII-символов.
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_stream = io.BytesIO(downloaded_file)
    ascii_art = image_to_ascii(image_stream, chars=chars)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")


def user_ascii_and_send(message):
    """
    Оболочка над функцией ascii_and_send, добавляющая пользовательский набор ASCII-символов.
    :param message: Сообщение пользователя.
    """
    ascii_and_send(message, message.text + ' ')


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """
    Обработчик клавиатуры.
    :param call: Кнопка в ответе.
    """
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Пикселизация Вашего изображения…")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.send_message(call.message.chat.id, 'Укажите набор ASCII-символов.',
                         reply_markup=get_charset_keyboard())
    elif call.data == 'invert':
        bot.answer_callback_query(call.id, 'Инверсия Вашего изображения…')
        invert_colors(call.message)
    elif call.data == "default":
        bot.answer_callback_query(call.id, "Преобразование Вашего изображения в ASCII-арт…")
        ascii_and_send(call.message)
    elif call.data == "input":
        msg = bot.reply_to(call.message, 'Укажите Ваш набор ASCII-символов.')
        bot.register_next_step_handler(msg, user_ascii_and_send)


bot.polling(none_stop=True)
