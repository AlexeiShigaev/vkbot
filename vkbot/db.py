import os, dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from .models import Base, Category, Product

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