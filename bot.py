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


def get_keyboard(buttons: list[tuple[str, str]], row_width: int = 3) -> types.InlineKeyboardMarkup:
    """
    Формирование клавиатуры.
    :param buttons: Список кортежей надписи на кнопке и строки ответа кнопки.
        (Пример: [('Кнопка1', 'Ответ1'), ('Кнопка2', 'Ответ2')])
    :param row_width: Количество кнопок в строке.
    :return: Клавиатура.
    """
    keyboard = types.InlineKeyboardMarkup()
    btn = [types.InlineKeyboardButton(b[0], callback_data=b[1]) for b in buttons]
    keyboard.add(*btn, row_width=row_width)
    return keyboard


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """
    Обработчик изображений пользователя.
    :param message: Изображение (сообщение) пользователя.
    """
    btn = [('Пикселизация', 'pixelate'), ('ASCII-арт', 'ascii'),
           ('Инверсия цветов', 'invert'), ('Отражение', 'reflection')]
    bot.reply_to(message, "У меня есть Ваша фотография! Пожалуйста, выберите, что бы Вы хотели с ней сделать.",
                 reply_markup=get_keyboard(btn, 2))
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


def get_image(message):
    """
    Получение изображения.
    :param message: Сообщение пользователя с изображением.
    :return: Изображение.
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_stream = io.BytesIO(downloaded_file)
    return Image.open(image_stream)


def send_image(image, message):
    """
    Отправка изображения.
    :param image: Изображение, готовое к отправке.
    :param message: Сообщение пользователя.
    """
    output_stream = io.BytesIO()
    image.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def pixelate_and_send(message):
    """
    Пикселизация изображения и отправка его обратно пользователю.
    :param message: Сообщение пользователя с изображением.
    """
    image = get_image(message)
    pixelated = pixelate_image(image, 20)
    send_image(pixelated, message)


def invert_colors(message):
    """
    Инверсия цветов изображения и отправка его обратно пользователю.
    :param message: Сообщение пользователя с изображением.
    """
    image = get_image(message)
    invert_image = ImageOps.invert(image)
    send_image(invert_image, message)


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


def image_to_ascii(image, new_width: int = 40, chars: str = ASCII_CHARS):
    """
    Преобразование изображения в ASCII-арт.
    :param image: Изображение.
    :param new_width: Новая ширина в символах.
    :param chars: Набор ASCII-символов.
    :return: ASCII-арт.
    """
    # Конвертирование в оттенки серого.
    image = image.convert('L')
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
    image = get_image(message)
    ascii_art = image_to_ascii(image, chars=chars)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")


def user_ascii_and_send(message):
    """
    Оболочка над функцией ascii_and_send, добавляющая пользовательский набор ASCII-символов.
    :param message: Сообщение пользователя.
    """
    ascii_and_send(message, message.text + ' ')


def reflection(message, direction: str):
    """
    Горизонтальное отражение изображения и отправка его обратно пользователю.
    :param message: Сообщение пользователя с изображением.
    :param direction: Направление отражения ('horizontal', 'vertical').
    """
    image = get_image(message)
    if direction == 'horizontal':
        direct = Image.Transpose.FLIP_LEFT_RIGHT
    elif direction == 'vertical':
        direct = Image.Transpose.FLIP_TOP_BOTTOM
    else:
        raise ValueError('Ошибка в аргументе «direction». Ожидаются значения «horizontal» или «vertical».')
    reflection_image = image.transpose(direct)
    send_image(reflection_image, message)


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
        btn = [('Ввести свой набор', 'input'), ('Использовать набор по умолчанию', 'default')]
        bot.send_message(call.message.chat.id, 'Укажите набор ASCII-символов.',
                         reply_markup=get_keyboard(btn))
    elif call.data == 'invert':
        bot.answer_callback_query(call.id, 'Инверсия Вашего изображения…')
        invert_colors(call.message)
    elif call.data == 'reflection':
        btn = [('Горизонтальное', 'horizontal'), ('Вертикальное', 'vertical')]
        bot.send_message(call.message.chat.id, 'Укажите направление отражения.',
                         reply_markup=get_keyboard(btn))
    elif call.data == "default":
        bot.answer_callback_query(call.id, "Преобразование Вашего изображения в ASCII-арт…")
        ascii_and_send(call.message)
    elif call.data == "input":
        msg = bot.reply_to(call.message, 'Укажите Ваш набор ASCII-символов.')
        bot.register_next_step_handler(msg, user_ascii_and_send)
    elif call.data == 'horizontal':
        bot.answer_callback_query(call.id, 'Горизонтальное отражение…')
        reflection(call.message, 'horizontal')
    elif call.data == 'vertical':
        bot.answer_callback_query(call.id, 'Вертикальное отражение…')
        reflection(call.message, 'vertical')


bot.polling(none_stop=True)
