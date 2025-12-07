import os
import dotenv
import logging
from typing import Optional

from vkbottle.bot import Bot, Message, MessageEvent
from vkbottle.tools.formatting import Formatter
from vkbottle import GroupEventType, GroupTypes, Callback
from vkbottle.tools.uploader import PhotoMessageUploader
from vkbottle import Keyboard, Callback, KeyboardButtonColor
from db import get_next_category_by_id, get_prev_category_by_id, get_next_prod_by_id, get_prev_prod_by_id
from db import get_state_from_db, insert_new_peer, update_user_state



dotenv.load_dotenv()
logging.getLogger("vkbottle").setLevel("DEBUG") #INFO/DEBUG

bot = Bot(os.getenv('VK_GROUP_TOKEN'))

photo_uploader = PhotoMessageUploader(bot.api)

KEYBOARD = (
    Keyboard(one_time=False, inline=True)
    .add(Callback("<-", payload={"command": "btn_prev"}))
    .add(Callback("Выбрать", payload={"command": "btn_choice"}), color=KeyboardButtonColor.POSITIVE)
    .add(Callback("->", payload={"command": "btn_next"}))
    .row()
    .add(Callback("Вернуться", payload={"command": "btn_back"}))
    .get_json()
)




"""
Классы для машины состояний в реализации паттерна Состояние
"""
class UserState:
    last_mess_id = 0
    peer_id = 0
    category_id = 0
    product_id = 0
    
    def __init__(self, params: dict):
        self.peer_id = params["peer_id"]
        self.last_mess_id = params["last_mess_id"]
        self.category_id = params["category_id"]
        self.product_id = params["product_id"]
    
    def toJSON(self):

        return {
            'peer_id': self.peer_id,
            'type_state': self.__class__.__name__,
            'last_mess_id': self.last_mess_id,
            'category_id': self.category_id,
            'product_id': self.product_id
        }

    async def send_edit_message(self, photo_url, text):
        # Загружаем фото
        photo = await photo_uploader.upload(
            file_source="img/" + photo_url,
            peer_id=self.peer_id,
        )

        # отправляем методом редактирования последнего сообщения
        await bot.api.messages.edit(
            message_id=self.last_mess_id,
            peer_id=self.peer_id,
            message=text,
            keyboard=KEYBOARD,
            attachment=photo,
        )

    
    def handle(self):
        ...
    
    
class StartMessageState(UserState):
    
    def __init__(self, params: dict):
        super().__init__(params)
        
    
    async def handle(self, mess: Message):
        # Начинаем с показа категорий. по одной. кучу кнопок не вываливаем.
        category = get_next_category_by_id(self.category_id)
        self.category_id = category.id

        # Загружаем фото
        photo = await photo_uploader.upload(
            file_source="img/" + category.img_url,
            peer_id=self.peer_id,
        )
        
        # Создается новое сообщение, запоминаем его ID-шку
        ret = await mess.answer(
            message=Formatter("Категория: {:bold}").format(category.name), 
            keyboard=KEYBOARD,
            attachment=photo
        )
        self.last_mess_id = ret.message_id
        
        # Переключамся на выбор категории.
        controller.set_state(
            SelectCategoryState(self.toJSON())
        )
        
        
class SelectCategoryState(UserState):
    def __init__(self, params: dict):
        super().__init__(params)
        
    
    async def handle(self, event: MessageEvent):
        command = event.object.payload["command"]
        if command == "btn_choice":
            controller.set_state(
                SelectProductState(self.toJSON())
            )
            event.object.payload["command"] = "btn_next"
            await controller.processor(event)
            return
        
        if command == "btn_next":
            category = get_next_category_by_id(self.category_id)
        else:
            category = get_prev_category_by_id(self.category_id)
        
        self.category_id = category.id
        
        text = Formatter("Категория: {:bold}").format(category.name)

        await self.send_edit_message(
            category.img_url, text
        )
    

class SelectProductState(UserState):
    def __init__(self, params: dict):
        super().__init__(params)
        
    async def handle(self, event: MessageEvent):
        command = event.object.payload["command"]
        
        if command == "btn_choice":
            controller.set_state(
                ChoiceProductState(self.toJSON())
            )
            event.object.payload["command"] = "btn_next"
            await controller.processor(event)
            return
        
        if command == "btn_back":
            controller.set_state(
                SelectCategoryState(self.toJSON())
            )
            event.object.payload["command"] = "btn_prev"
            await controller.processor(event)
            return
        
        if event.object.payload["command"] == "btn_next":
            prod = get_next_prod_by_id(self.category_id, self.product_id)
        else:
            prod = get_prev_prod_by_id(self.category_id, self.product_id)
        
        self.product_id = prod.id
        
        text = Formatter("Категория: {:bold}\nНаименование: {:bold}\nОписание: {:bold}\nЦена: {:bold}") \
            .format(prod.category_rel.name, prod.name, prod.description, prod.price)

        await self.send_edit_message(
            prod.img_url, text
        )
        

class ChoiceProductState(UserState):
    def __init__(self, params: dict):
        super().__init__(params)
        
    async def handle(self, event: MessageEvent):
        # Здесь должна бы быть логика добавления товара в корзину.
        await bot.api.messages.send_message_event_answer(
            event_id=event.object.event_id,
            user_id=event.object.user_id,
            peer_id=self.peer_id,
            event_data='{"type":"show_snackbar", "text":"Вы выбрали товар."}',
        )
    
    
class BotController:
    peers = {}
        
    
    async def processor(self, mess):
        # история, когда нет пира ни в пирах, ни в базе.

        if isinstance(mess, Message):
            peer_id = mess.peer_id
        else:
            peer_id = mess.object.peer_id
            

        if peer_id not in self.peers:
            result = get_state_from_db(peer_id)
            
            if not result:
                self.peers[peer_id] = StartMessageState(
                    {   'peer_id': peer_id,
                        'last_mess_id': 0,
                        'category_id': 0,
                        'product_id': 0
                    }
                )
                insert_new_peer(self.peers[peer_id].toJSON())
            else:
                # Создаем экземпляр состояния сохраненного типа
                self.peers[peer_id] = globals()[result.type_state](result.toJSON())
        
        # пир есть, даем ему команду
        await self.peers[peer_id].handle(mess)
        
    
    def set_state(self, new_state: UserState):
        # Сохраняем новый стейт
        self.peers[new_state.peer_id] = new_state
        
        update_user_state(new_state.toJSON())
        
        

controller = BotController()



@bot.on.message(text=["/start", "/Start", "/начать", "/Начать"])
async def start_handler(message: Message, item: Optional[str] = None):
    """ Точка входа """
    print("Start event")
    await controller.processor(message)



@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=GroupTypes.MessageEvent)
async def btn_prev_handler(event: MessageEvent):
    """ Обработка нажатий кнопок с клавиатуры управления """
    await controller.processor(event)

    


# @bot.on.message()
# async def std_mess_handler(message: Message, item: Optional[str] = None):
#     print("!!!!!!!!!!!!!!!!!!!!!!!!!")
#     print(message, "\n", item)
#     print("!!!!!!!!!!!!!!!!!!!!!!!!!")
#     await message.answer("Я такого не понимаю.\nИспользуйте команду /start")



bot.run_forever()
