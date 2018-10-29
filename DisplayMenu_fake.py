#! /usr/bin/env python2

# SQLAlchemy uses to communicate with various types of DBAPIs and databases.

import os
import sys


from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, relationship

from database_setup import Base, Restaurant, MenuItem, User

engine = create_engine('postgresql://catalog:password@localhost/catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Added fake database in menu items for our website before login.


restaurant1 = Restaurant(id=1, name='Virgin Courtyard', image='https://media-cdn.tripadvisor.com/media/photo-s/05/55/01/a5/virgin-courtyard.jpg',  # noqa
                         description='Awesome place')
session.add(restaurant1)
session.commit()


restaurant2 = Restaurant(id=2, name='Barcode IXC', image='https://content3.jdmagicbox.com/comp/chandigarh/w3/0172px172.x172.171204214247.q5w3/catalogue/barcode-ixc-industrial-area-phase-i-chandigarh-lounge-bars-2m1xq.jpg',  # noqa
                         description='Awesome place')
session.add(restaurant2)
session.commit()


restaurant3 = Restaurant(id=3, name='Pyramid', image='https://b.zmtcdn.com/data/pictures/2/124082/bde023a9a63951a79ffc92fff29f6d92_featured_v2.jpg',    # noqa
                         description='Awesome place')
session.add(restaurant3)
session.commit()


restaurant4 = Restaurant(id=4, name='FLYP@MTV', image='https://b.zmtcdn.com/data/pictures/5/18486025/b1fa09a3ca488fe1a2e61c99747cb5f7_featured_v2.jpg',   # noqa
                         description='Awesome place')
session.add(restaurant4)
session.commit()

# adding items


item1 = MenuItem(name='Salsa with Breads', description='Best dish tasted ever', price='200', image='https://media-cdn.tripadvisor.com/media/photo-s/09/ee/17/40/photo2jpg.jpg',  # noqa
                 categories='Snacks', restaurant=restaurant1)
session.add(item1)
session.commit()

item2 = MenuItem(name='Burger', description='Best Burgerr tasted ever', price='350', image='https://naazarora.files.wordpress.com/2016/12/img_2164.jpg',  # noqa
                 categories='burger', restaurant=restaurant2)
session.add(item2)
session.commit()

item3 = MenuItem(name='Pasta', description='yummy', price='150', image='https://b.zmtcdn.com/data/pictures/2/121552/1a29f5874ff66e972b0c66a6cfd7d8ed_featured_v2.jpg',  # noqa
                 categories='Pasta', restaurant=restaurant3)
session.add(item3)
session.commit()

item4 = MenuItem(name='Chicken Balls', description='yummiest foood ever tried', price='350', image='https://content3.jdmagicbox.com/comp/chandigarh/k6/0172px172.x172.170413100531.g9k6/catalogue/flyp-at-mtv-chandigarh-sector-26-chandigarh-restaurants-a7bi24.jpg',  # noqa
                 categories='Food', restaurant=restaurant4)
session.add(item4)
session.commit()

print ("items added successfully!")


print ("Restaurants added successfully!")
