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
host = 'dpg-copqu6ljm4es73a9ru10-a.oregon-postgres.render.com'
dbname = 'naviz_database'
user = 'root'
password = 'NblwTvV0JCoCiTX9J7ScdERpUp70jtWL'
port = '5432'

while True:
    try:
        connection = psycopg2.connect(host=host,
                                      port=port,
                                      database=dbname,
                                      user=user,
                                      password=password,
                                      cursor_factory=RealDictCursor)
        cursor = connection.cursor()
        break
    except Exception as error:
        time.sleep(2)


# >>>>>>>>>>>>>>>> FETCHING ALL PRODUCTS FOR THE HOME PAGE LOADING
@app.get('/', status_code=status.HTTP_200_OK)
async def fetch_products():
    cursor.execute("""SELECT * FROM products""")
    products = cursor.fetchall()
    data_list = []
    for i in range(len(products)):
        data = dict(products[i])
        data_list.append(data)
    return {'products': data_list}


#  >>>>>>>>>>>>>>> CREATING NEW PRODUCTS
@app.post('/products', status_code=status.HTTP_201_CREATED)
async def add_product(name: str = Form(...), specs: str = Form(...), category: str = Form(...), price: str = Form(...),
                      image: UploadFile = File(...)):

    upload_dir = 'files/images'
    if not os.path.exists(upload_dir):
        os.mkdir(upload_dir)

    image_path = os.path.join(upload_dir, image.filename)
    with open(image_path, 'wb', ) as buffer:
        buffer.write(image.file.read())

    cursor.execute(
        """INSERT INTO products (name, specs, category, price, image) VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (name, specs, category, price, image.filename))
    product = cursor.fetchone()
    connection.commit()

    return {'product': product, 'name': name, 'image': image.filename}


# >>>>>>>>>>>>>>> FETCHING ALL ORDERS
@app.get('/orders', status_code=status.HTTP_200_OK)
async def fetch_orders():
    cursor.execute("""SELECT * FROM orders ORDER BY id DESC""")
    orders = cursor.fetchall()
    orders_list = []
    for i in range(len(orders)):
        my_order = dict(orders[i])
        id_ = my_order['id']
        credentials = ast.literal_eval(my_order['credentials'])
        items = ast.literal_eval(my_order['orders'])
        timestamp = my_order['timestamp']
        new_order = {
            'id': id_,
            'credentials': credentials,
            'orders': items,
            'timestamp': timestamp
        }
        orders_list.append(new_order)
    return {
        'orders': orders_list
    }


# >>>>>>>>>>>>>> A MODEL FOR NEW ORDERS
class Order(BaseModel):
    credentials: dict
    orders: List[dict]


# >>>>>>>>>>>>>>>> CREATING NEW ORDERS
@app.post('/orders', status_code=status.HTTP_201_CREATED)
async def add_product(order: Order):
    if not len(order.credentials) == 0:
        current = datetime.now()
        timestamp = current.strftime("%d-%m-%Y %H:%M:%S")
        print(timestamp)
        cursor.execute("""
        INSERT INTO orders (credentials, orders, timestamp)
        VALUES (%s, %s, %s) RETURNING *
        """, (str(order.credentials),
              str(order.orders), timestamp)
                       )

        connection.commit()
        new_order = cursor.fetchone()
        return {'product': new_order}
    return {'product': {}}
