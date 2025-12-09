import os, dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Category, Product, User

dotenv.load_dotenv()
engine = create_engine(os.getenv('DB_URL'), echo=False)
Session = sessionmaker(bind=engine)

# Base.metadata.create_all(engine)


def get_next_category_by_id(id: int):
    session = Session()

    next_pos = session.query(Category) \
        .filter(Category.id > id) \
        .order_by(Category.id) \
        .limit(1) \
        .first()
    
    if next_pos:
        return next_pos

    return session.query(Category).first()
    

def get_prev_category_by_id(id: int):
    session = Session()

    prev_pos = session.query(Category) \
        .filter(Category.id < id) \
        .order_by(Category.id.desc()) \
        .limit(1) \
        .first()
    
    if prev_pos:
        return prev_pos
    
    return session.query(Category).order_by(Category.id.desc()).first()
    

def get_next_prod_by_id(cat_id: int, prod_id: int):
    session = Session()
    
    next_prod = session.query(Product) \
        .filter_by(category_id=cat_id) \
        .filter(Product.id > prod_id) \
        .order_by(Product.id) \
        .limit(1) \
        .first()
    
    if next_prod:
        return next_prod
    
    return session.query(Product).filter_by(category_id=cat_id).first()


def get_prev_prod_by_id(cat_id: int, prod_id: int):
    session = Session()

    prev_prod = session.query(Product) \
        .filter_by(category_id=cat_id) \
        .filter(Product.id < prod_id) \
        .order_by(Product.id.desc()) \
        .limit(1) \
        .first()

    if prev_prod:
        return prev_prod
    
    return session.query(Product).filter_by(category_id=cat_id).order_by(Product.id.desc()).first()



def get_state_from_db(peer_id_to_find: int):
    session = Session()
    
    return session.query(User) \
        .filter_by(peer_id=peer_id_to_find) \
        .first()
        

def insert_new_peer(state_json):
    session = Session()
    
    session.add(User(**state_json))
    session.commit()
    
    
def update_user_state(user):
    session = Session()
    
    user_to_update = session.query(User).filter_by(peer_id=user["peer_id"]).first()
    if user_to_update:
        user_to_update.last_mess_id = user["last_mess_id"]
        user_to_update.category_id = user["category_id"]
        user_to_update.product_id = user["product_id"]
        user_to_update.type_state = user["type_state"]
        session.commit()
        
        
