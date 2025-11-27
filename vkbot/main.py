import os
from typing import Optional

from vkbottle.bot import Bot, Message, MessageEvent
from vkbottle.tools.formatting import Formatter
from vkbottle import CtxStorage, GroupEventType, GroupTypes, Callback
from vkbottle.tools.uploader import PhotoMessageUploader
from vkbottle import Keyboard, Callback, KeyboardButtonColor
from states import States
from db import get_next_category_by_id, get_prev_category_by_id, get_next_prod_by_id, get_prev_prod_by_id


bot = Bot(os.getenv('VK_GROUP_TOKEN'))

photo_uploader = PhotoMessageUploader(bot.api)

last_mess_id = CtxStorage()


KEYBOARD = (
    Keyboard(one_time=False, inline=True)
    .add(Callback("<-", payload={"command": "btn_prev"}))
    .add(Callback("Выбрать", payload={"command": "btn_choice"}), color=KeyboardButtonColor.POSITIVE)
    .add(Callback("->", payload={"command": "btn_next"}))
    .row()
    .add(Callback("Вернуться", payload={"command": "btn_back"}))
    .get_json()
)


async def send_edit_message(peer_id, photo_url, text):
    # Загружаем фото
    photo = await photo_uploader.upload(
        file_source="img/" + photo_url,
        peer_id=peer_id,
    )

    # отправляем методом редактирования последнего сообщения
    await bot.api.messages.edit(
        message_id=last_mess_id.get(peer_id).message_id,
        peer_id=peer_id,
        message=text,
        keyboard=KEYBOARD,
        attachment=photo,
    )


async def call_btn_next_prev(event: MessageEvent):
    # исходим из того что клиент уже известен. кнопку нажал, значит известен.
    state = await bot.state_dispenser.get(event.object.peer_id)
    
    # и тут два варианта. либо крутим категории, либо продукты.
    if state.state == States.CHOICE_CATEGORY_STATE:
        if event.object.payload["command"] == "btn_next":
            category = get_next_category_by_id(state.payload["category"])
        else:
            category = get_prev_category_by_id(state.payload["category"])

        photo_url = category.img_url
        text = Formatter("Категория: {:bold}").format(category.name)

        await send_edit_message(
            event.object.peer_id, photo_url, text
        )

        await bot.state_dispenser.set(
            event.object.peer_id, States.CHOICE_CATEGORY_STATE, category=category.id, prod=0
        )
    
    elif state.state == States.CHOICE_PROD_STATE:
        if event.object.payload["command"] == "btn_next":
            prod = get_next_prod_by_id(state.payload["category"], state.payload["prod"])
        else:
            prod = get_prev_prod_by_id(state.payload["category"], state.payload["prod"])

        photo_url = prod.img_url
        text = Formatter("Категория: {:bold}\nНаименование: {:bold}\nОписание: {:bold}\nЦена: {:bold}") \
            .format(prod.category_rel.name, prod.name, prod.description, prod.price)

        await send_edit_message(
            event.object.peer_id, photo_url, text
        )

        await bot.state_dispenser.set(
            event.object.peer_id, States.CHOICE_PROD_STATE, category=prod.category_id, prod=prod.id
        )


async def call_btn_choice(event: MessageEvent):
    state = await bot.state_dispenser.get(event.object.peer_id)

    if state.state == States.CHOICE_CATEGORY_STATE:
        prod = get_next_prod_by_id(state.payload["category"], state.payload["prod"])

        photo_url = prod.img_url
        text = Formatter("Категория: {:bold}\nНаименование: {:bold}\nЦена: {:bold}") \
            .format(prod.category_rel.name, prod.name, prod.price)

        await send_edit_message(
            event.object.peer_id, photo_url, text
        )

        await bot.state_dispenser.set(
            event.object.peer_id, States.CHOICE_PROD_STATE, category=prod.category_id, prod=prod.id
        )

    elif state.state == States.CHOICE_PROD_STATE:
        # Здесь должна бы быть логика добавления товара в корзину.
        await bot.api.messages.send_message_event_answer(
            event_id=event.object.event_id,
            user_id=event.object.user_id,
            peer_id=event.object.peer_id,
            event_data='{"type":"show_snackbar", "text":"Вы выбрали товар."}',
        )


async def call_btn_back(event: MessageEvent):
    # Выходим на список категорий, фиксируем стейт
    state = await bot.state_dispenser.get(event.object.peer_id)

    category = get_next_category_by_id(state.payload["category"])

    photo_url = category.img_url
    text = Formatter("Категория: {:bold}").format(category.name)

    await send_edit_message(
        event.object.peer_id, photo_url, text
    )

    await bot.state_dispenser.set(
        event.object.peer_id, States.CHOICE_CATEGORY_STATE, category=category.id, prod=0
    )



@bot.on.message(text=["/start", "/Start", "/начать", "/Начать"])
async def start_handler(message: Message, item: Optional[str] = None):
    """ Точка входа """
    # Если клиент совсем новый, создаем под него машину состояний
    if message.peer_id not in bot.state_dispenser.dictionary:
        await bot.state_dispenser.set(
            message.peer_id, States.CHOICE_CATEGORY_STATE,
            category=0, prod=0,
        )

    # Получим стэйт для клиента
    state = await bot.state_dispenser.get(message.peer_id)

    if state.state == States.CHOICE_CATEGORY_STATE:
        category = get_next_category_by_id(state.payload["category"])

        # Загружаем фото
        photo = await photo_uploader.upload(
            file_source="img/" + category.img_url,
            peer_id=message.peer_id,
        )

        mess_id = await message.answer(
            message=Formatter("Категория: {:bold}").format(category.name), 
            keyboard=KEYBOARD,
            attachment=photo
        )
        
        # фиксируем id мессаги, будем ее редактировать в дальнейшем. дабы не плодить мусора в ленте.
        # наверно надо бы фикировать это дело в машину состояний. но это потом.
        last_mess_id.set(message.peer_id, mess_id)
        await bot.state_dispenser.set(message.peer_id, States.CHOICE_CATEGORY_STATE, category=category.id, prod=0)


@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=GroupTypes.MessageEvent)
async def btn_prev_handler(event: MessageEvent):
    """ Обработка нажатий кнопок с клавиатуры управления """
    command = event.object.payload["command"]
    
    if command == "btn_choice":
        await call_btn_choice(event)
    elif command == "btn_back":
        await call_btn_back(event)
    else:
        await call_btn_next_prev(event)

    


# @bot.on.message()
# async def std_mess_handler(message: Message, item: Optional[str] = None):
#     print("!!!!!!!!!!!!!!!!!!!!!!!!!")
#     print(message, "\n", item)
#     print("!!!!!!!!!!!!!!!!!!!!!!!!!")
#     await message.answer("Я такого не понимаю.\nИспользуйте команду /start")



bot.run_forever()
