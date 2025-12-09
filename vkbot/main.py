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
logging.getLogger("vkbottle").setLevel("INFO") #INFO/DEBUG

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
Класс события для машины состояний
"""
class BotEvent():
    command: str
    last_mess_id: int
    peer_id: int
    event_id: int
    user_id: int
    
    def __init__(self, 
                 command: str = "btn_next", 
                 last_mess_id: int = 0, 
                 peer_id: int = 0,
                 event_id: int = 0,
                 user_id: int = 0
                 ):
        self.command = command
        self.peer_id = peer_id
        self.last_mess_id = last_mess_id
        self.event_id = event_id
        self.user_id = user_id

    

"""
Эти обработчики обязательны к реализации, как минимум в классе UserState
"""
handlers = {
    "btn_prev": "handler_btn_prev",
    "btn_next": "handler_btn_next",
    "btn_choice": "handler_btn_choice",
    "btn_back": "handler_btn_back",
}
    


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

    
    async def handler_btn_prev(self, event: BotEvent):
        # Заглушка.
        return ""
        
    async def handler_btn_next(self, event: BotEvent):
        # Заглушка.
        return ""
    
    async def handler_btn_choice(self, event: BotEvent):
        # Заглушка.
        return ""


    async def handler_btn_back(self, event: BotEvent):
        # Заглушка.
        return ""

    
    
class StartMessageState(UserState):
    """ Условное состояние по команде /start. Не факт что нужное. или нужно перепродумать его работу."""
    def __init__(self, params: dict):
        super().__init__(params)
        
    
    async def handler_btn_next(self, event: BotEvent):
        # Начинаем с показа категорий. по одной. кучу кнопок не вываливаем.
        category = get_next_category_by_id(self.category_id)
        
        self.category_id = category.id

        self.last_mess_id = event.last_mess_id

        await self.send_edit_message(
            category.img_url,
            Formatter("Категория: {:bold}").format(category.name)
        )
        
        # Переключаемся на выбор категории.
        controller.set_state(
            SelectCategoryState(self.toJSON())
        )
        
        
        
class SelectCategoryState(UserState):
    """ Набор реакций на нажатия разных кнопок при листании категорий """
    def __init__(self, params: dict):
        super().__init__(params)
        
    async def handler_btn_next(self, event: BotEvent):
        category = get_next_category_by_id(self.category_id)
          
        self.category_id = category.id
        
        text = Formatter("Категория: {:bold}").format(category.name)

        await self.send_edit_message(
            category.img_url, text
        )

    async def handler_btn_prev(self, event: BotEvent):
        category = get_prev_category_by_id(self.category_id)
          
        self.category_id = category.id
        
        text = Formatter("Категория: {:bold}").format(category.name)

        await self.send_edit_message(
            category.img_url, text
        )    
    
    async def handler_btn_choice(self, event: BotEvent):
        controller.set_state(
            SelectProductState(self.toJSON())
        )
        event.command = "btn_next"
        await controller.processor(event)
        
    async def handler_btn_back(self, event: BotEvent):
        await bot.api.messages.send_message_event_answer(
            event_id=event.event_id,
            user_id=event.user_id,
            peer_id=event.peer_id,
            event_data='{"type":"show_snackbar", "text":"Вы в корне каталога"}',
        )
    

class SelectProductState(UserState):
    """ Набор реакций на листания или выбор/выход в списке продуктов """
    def __init__(self, params: dict):
        super().__init__(params)
        
        
    async def handler_btn_next(self, event: BotEvent):
        prod = get_next_prod_by_id(self.category_id, self.product_id)
        self.product_id = prod.id
        
        text = Formatter("Категория: {:bold}\nНаименование: {:bold}\nОписание: {:bold}\nЦена: {:bold}") \
            .format(prod.category_rel.name, prod.name, prod.description, prod.price)

        await self.send_edit_message(
            prod.img_url, text
        )
        
    async def handler_btn_prev(self, event: BotEvent):
        prod = get_prev_prod_by_id(self.category_id, self.product_id)
        self.product_id = prod.id
        
        text = Formatter("Категория: {:bold}\nНаименование: {:bold}\nОписание: {:bold}\nЦена: {:bold}") \
            .format(prod.category_rel.name, prod.name, prod.description, prod.price)

        await self.send_edit_message(
            prod.img_url, text
        )
        
    async def handler_btn_choice(self, event: BotEvent):
        controller.set_state(
            ChoiceProductState(self.toJSON())
        )
        event.command = "btn_next"
        await controller.processor(event)
        
    async def handler_btn_back(self, event: BotEvent):
        controller.set_state(
            SelectCategoryState(self.toJSON())
        )
        event.command = "btn_next"
        await controller.processor(event)
        


class ChoiceProductState(UserState):
    """ Состояние - выбор продукта. Кнопки все те же, важно сделать выход на предыдущий уровень. """
    def __init__(self, params: dict):
        super().__init__(params)
        
    async def handler_btn_choice(self, event: BotEvent):
        # Здесь должна бы быть логика добавления товара в корзину.
        await bot.api.messages.send_message_event_answer(
            event_id=event.object.event_id,
            user_id=event.object.user_id,
            peer_id=self.peer_id,
            event_data='{"type":"show_snackbar", "text":"Вы выбрали товар."}',
        )
        
    async def handler_btn_next(self, event: BotEvent):
        # ЗЗаглушка.
        await bot.api.messages.send_message_event_answer(
            event_id=event.event_id,
            user_id=event.user_id,
            peer_id=self.peer_id,
            event_data='{"type":"show_snackbar", "text":"Товар в корзине.\nПо идее, кнопку либо убрать, либо она не активна."}',
        )
        
    async def handler_btn_prev(self, event: BotEvent):
        # Заглушка.
        await bot.api.messages.send_message_event_answer(
            event_id=event.event_id,
            user_id=event.user_id,
            peer_id=self.peer_id,
            event_data='{"type":"show_snackbar", "text":"Товар в корзине.\nПо идее, кнопку либо убрать, либо она не активна."}',
        )
        
    async def handler_btn_back(self, event: BotEvent):
        controller.set_state(
            SelectCategoryState(self.toJSON())
        )
        event.command = "btn_prev"
        await controller.processor(event)
    
    
    
class BotController:
    """ Класс обработчика событий машины состояния. """
    peers = {}
        
    async def processor(self, event: BotEvent):
        # история, когда нет пира ни в пирах, ни в базе.
        if event.peer_id not in self.peers:
            result = get_state_from_db(event.peer_id)
            
            if not result:
                self.peers[event.peer_id] = StartMessageState(
                    {   'peer_id': event.peer_id,
                        'last_mess_id': event.last_mess_id,
                        'category_id': 0,
                        'product_id': 0
                    }
                )
                insert_new_peer(self.peers[event.peer_id].toJSON())
            else:
                # Создаем экземпляр состояния сохраненного типа
                self.peers[event.peer_id] = globals()[result.type_state](result.toJSON())
                
        # пир есть, даем ему команду
        if event.last_mess_id:
            self.peers[event.peer_id].last_mess_id = event.last_mess_id 
        

        state = self.peers[event.peer_id]
        handler = state.__getattribute__(handlers[event.command])
        await handler(event)
        
    
    def set_state(self, new_state: UserState):
        # Сохраняем новый стейт в базу
        self.peers[new_state.peer_id] = new_state
        
        update_user_state(new_state.toJSON())
        
        

controller = BotController()



@bot.on.message(text=["/start", "/Start", "/начать", "/Начать"])
async def start_handler(message: Message, item: Optional[str] = None):
    """ Точка входа """
    msg = await message.answer(message="Привет!")
    
    await controller.processor(
        BotEvent(
            command="btn_next",
            last_mess_id=msg.message_id,
            peer_id=msg.peer_id
        )
    )



@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=GroupTypes.MessageEvent)
async def btn_press_handler(event: MessageEvent):
    """ Обработка нажатий кнопок с клавиатуры управления """
    await controller.processor(
        BotEvent(
            command=event.object.payload["command"],
            peer_id=event.object.peer_id,
            event_id=event.object.event_id,
            user_id=event.object.user_id
        )
    )

    


bot.run_forever()

