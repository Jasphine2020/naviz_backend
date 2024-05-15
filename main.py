import ast
import os
import time
from datetime import datetime
from typing import List

import psycopg2
from fastapi import FastAPI, status, Form, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

# >>>>>>>>>>>> CREATING A FAST API INSTANCE
app = FastAPI()

# >>>>>>>>>>>>> SETTING UP THE CORS MIDDLEWARE ...
app.add_middleware(CORSMiddleware,
                   allow_origins=['*'],
                   allow_credentials=True,
                   allow_methods=['*'],
                   allow_headers=['*'],
                   )

# >>>>>>>>>>>>> MOUNTING THE ROOT IMAGE FOLDER ...
app.mount('/images', StaticFiles(directory='files/images'), name='images')


# >>>>>>>>>>>> CONNECTING TO THE DATABASE ...

# Connection details
host = 'dpg-copqu6ljm4es73a9ru10-a'
dbname = 'naviz_database'
user = 'root'
password = 'NblwTvV0JCoCiTX9J7ScdERpUp70jtWL'
port = '5432'

# Establishing the database connection
while True:
    try:
        connection = psycopg2.connect(host=host,
                                      port=port,
                                      database=dbname,
                                      user=user,
                                      password=password,
                                      cursor_factory=RealDictCursor)
        cursor = connection.cursor()
        # Removing all items from the "products" table
        cursor.execute("DELETE FROM products;")
        connection.commit()
        break
    except Exception as error:
        connection.rollback()
        print(error)


# >>>>>>>>>>>>>>>> FETCHING ALL PRODUCTS FOR THE HOME PAGE LOADING
@app.get('/', status_code=status.HTTP_200_OK)
async def fetch_products():
    try:
        cursor.execute("""SELECT * FROM products""")
        products = cursor.fetchall()
        data_list = [dict(product) for product in products]
        return {'products': data_list}
    except Exception as e:
        connection.rollback()
        return {'error': str(e)}


#  >>>>>>>>>>>>>>> CREATING NEW PRODUCTS
@app.post('/products', status_code=status.HTTP_201_CREATED)
async def add_product(name: str = Form(...), specs: str = Form(...), category: str = Form(...), price: str = Form(...),
                      image: UploadFile = File(...)):
    try:
        upload_dir = 'files/images'
        if not os.path.exists(upload_dir):
            os.mkdir(upload_dir)

        image_path = os.path.join(upload_dir, image.filename)
        with open(image_path, 'wb') as buffer:
            buffer.write(image.file.read())

        cursor.execute(
            """INSERT INTO products (name, specs, category, price, image) VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (name, specs, category, price, image.filename))
        product = cursor.fetchone()
        connection.commit()

        return {'product': product, 'name': name, 'image': image.filename}
    except Exception as e:
        connection.rollback()
        return {'error': str(e)}


# >>>>>>>>>>>>>>> FETCHING ALL ORDERS
@app.get('/orders', status_code=status.HTTP_200_OK)
async def fetch_orders():
    try:
        cursor.execute("""SELECT * FROM orders ORDER BY id DESC""")
        orders = cursor.fetchall()
        orders_list = []
        for order in orders:
            my_order = dict(order)
            my_order['credentials'] = ast.literal_eval(my_order['credentials'])
            my_order['orders'] = ast.literal_eval(my_order['orders'])
            orders_list.append(my_order)
        return {'orders': orders_list}
    except Exception as e:
        connection.rollback()
        return {'error': str(e)}


# >>>>>>>>>>>>>>>> CREATING NEW ORDERS
class Order(BaseModel):
    credentials: dict
    orders: List[dict]


@app.post('/orders', status_code=status.HTTP_201_CREATED)
async def add_order(order: Order):
    try:
        if order.credentials:
            current = datetime.now()
            timestamp = current.strftime("%d-%m-%Y %H:%M:%S")
            cursor.execute("""
            INSERT INTO orders (credentials, orders, timestamp)
            VALUES (%s, %s, %s) RETURNING *
            """, (str(order.credentials),
                  str(order.orders), timestamp)
                           )

            connection.commit()
            new_order = cursor.fetchone()
            return {'order': new_order}
        return {'order': {}}
    except Exception as e:
        connection.rollback()
        return {'error': str(e)}