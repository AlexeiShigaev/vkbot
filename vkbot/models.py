from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL
from sqlalchemy.orm import declarative_base, relationship



Base = declarative_base()

class Category(Base):
    """ Модель категории. """
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    img_url = Column(String)


class Product(Base):
    """ Модель товара. """
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    img_url = Column(String)
    price = Column(DECIMAL(8, 2))
    category_id = Column(Integer, ForeignKey('categories.id'))
    category_rel = relationship("Category")


class User(Base):
    """ Модель для хранения состояний. """
    __tablename__ = 'userstates'

    id = Column(Integer, primary_key=True)
    peer_id = Column(Integer)
    type_state = Column(String, nullable=False)
    last_mess_id = Column(Integer)
    category_id = Column(Integer)
    product_id = Column(Integer)
    
    def toJSON(self):

        return {
            'peer_id': self.peer_id,
            'type_state': self.__class__.__name__,
            'last_mess_id': self.last_mess_id,
            'category_id': self.category_id,
            'product_id': self.product_id
        }
