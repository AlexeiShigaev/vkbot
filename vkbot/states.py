from vkbottle import BaseStateGroup


class States(BaseStateGroup):
    START_STATE = 10
    CHOICE_CATEGORY_STATE = 20
    CHOICE_PROD_STATE = 30
    ORDER_STATE = 40
    PAY_STATE = 50
