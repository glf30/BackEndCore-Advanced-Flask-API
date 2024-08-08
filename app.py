from flask import Flask, jsonify, request
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship
from sqlalchemy import select, delete, Column, Integer, String, ForeignKey, Date, Float
from flask_cors import CORS
import datetime
from typing import List
from marshmallow import ValidationError, fields, validates, validate
import re

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:Sennenga28!@localhost/project_e_commerce_db"

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

# ==== DB MODELS ============================================================================

class Customer(Base):
    __tablename__ = "Customers"
    customer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str] = mapped_column(String(15))
    
    customer_account: Mapped["CustomerAccount"] = relationship("CustomerAccount", back_populates="customer", uselist=False)
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer")

class CustomerAccount(Base):
    __tablename__ = "Customer_Accounts"
    account_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey('Customers.customer_id'))
    customer: Mapped["Customer"] = relationship("Customer", back_populates="customer_account")

order_product = db.Table(
    "Order_Product",
    Base.metadata,
    db.Column("order_id", db.ForeignKey("Orders.order_id"), primary_key=True),
    db.Column("product_id", db.ForeignKey("Products.product_id"), primary_key=True)
)

class Order(Base):
    __tablename__ = "Orders"
    order_id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customers.customer_id"))

    customer: Mapped["Customer"] = db.relationship(back_populates="orders")
    products: Mapped[List["Product"]] = db.relationship(secondary=order_product)

class Product(Base):
    __tablename__ = "Products"
    product_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

# ==== SCHEMAS ==============================================================================

class CustomerSchema(ma.Schema):
    customer_id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1))
    email = fields.String(required=True, validate=validate.Email())
    phone = fields.String(required=True, validate=validate.Length(min=10, max=15))

    @validates('email')
    def validate_email(self, value):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise ValidationError("Invalid email address.")

    @validates('phone')
    def validate_phone(self, value):
        phone_regex = r'^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$'
        if not re.match(phone_regex, value):
            raise ValidationError("Invalid phone number. Must be in the format +123456789, 123-456-7890, or similar.")

    class Meta:
        fields = ("customer_id", "email", "name", "phone")

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

class AccountSchema(ma.Schema):
    account_id = fields.Integer(dump_only=True)
    username = fields.String(required=True, validate=validate.Length(min=4, max=255))
    password = fields.String(required=True, validate=validate.Length(min=6, max=255))
    customer_id = fields.Integer(required=True)

    @validates('password')
    def validate_password(self, value):
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$', value):
            raise ValidationError("Password must be at least 6 characters long and contain at least one letter and one number.")

    @validates('username')
    def validate_username(self, value):
        if not re.match(r'^\w+$', value):
            raise ValidationError("Username must contain only letters, numbers, and underscores.")

    class Meta:
        fields = ("account_id", "username", "password", "customer_id")

account_schema = AccountSchema()
accounts_schema = AccountSchema(many=True)

class ProductSchema(ma.Schema):
    product_id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1))
    price = fields.Float(required=True, validate=validate.Range(min=0))

    class Meta:
        fields = ("product_id", "name", "price")

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

class OrderSchema(ma.Schema):
    order_id = fields.Integer(dump_only=True)
    customer_id = fields.Integer(required=True)
    date = fields.Date(required=True)
    product_id = fields.List(fields.Integer(), required=False)

    class Meta:
        fields = ("order_id", "customer_id", "date", "product_id")

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

# ==== API ROUTES ===========================================================================

@app.route("/customers", methods=["GET"])
def get_customers():
    query = select(Customer)
    result = db.session.execute(query).scalars()
    customers = result.all()
    return customers_schema.jsonify(customers)

@app.route("/customers", methods=["POST"])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    with Session(db.engine) as session:
        with session.begin():
            new_customer = Customer(**customer_data)
            session.add(new_customer)
            session.commit()
    
    return jsonify({"message": "New Customer successfully added!"}), 201

@app.route("/customers/<int:id>", methods=["PUT"])
def update_customer(id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Customer).filter(Customer.customer_id == id)
            result = session.execute(query).scalars().first()
            if result is None:
                return jsonify({"message": "Customer not found"}), 404

            try:
                customer_data = customer_schema.load(request.json)
            except ValidationError as e:
                return jsonify(e.messages), 400

            for field, value in customer_data.items():
                setattr(result, field, value)

            session.commit()

    return jsonify({"message": "Customer details updated successfully"}), 200

@app.route("/customers/<int:id>", methods=["DELETE"])
def delete_customer(id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Customer).filter(Customer.customer_id == id)
            result = session.execute(query).scalars().first()

            if result is None:
                return jsonify({"error": "Customer not found..."}), 404
            
            session.delete(result)
            session.commit()

        return jsonify({"message": "Customer removed successfully!"}), 200

@app.route("/customeraccounts", methods=["GET"])
def get_customer_account():
    query = select(CustomerAccount)
    result = db.session.execute(query).scalars()
    accounts = result.all()
    return accounts_schema.jsonify(accounts)

@app.route("/customeraccounts", methods=["POST"])
def add_customer_account():
    try:
        customer_account_data = account_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    with Session(db.engine) as session:
        with session.begin():
            new_account = CustomerAccount(**customer_account_data)
            session.add(new_account)
            session.commit()

    return jsonify({"message": "New Customer Account successfully added!"}), 201

@app.route("/customeraccounts/<int:account_id>", methods=["PUT"])
def update_customer_account(account_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(CustomerAccount).filter_by(account_id=account_id)
            result = session.execute(query).scalars().first()
            
            if result is None:
                return jsonify({"message": "Customer Account not found"}), 404
            
            try:
                customer_account_data = account_schema.load(request.json)
            except ValidationError as e:
                return jsonify(e.messages), 400
            
            for field, value in customer_account_data.items():
                setattr(result, field, value)

            session.commit()

    return jsonify({"message": "Customer Account details updated successfully"}), 200

@app.route("/customeraccounts/<int:account_id>", methods=["DELETE"])
def delete_customer_account(account_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(CustomerAccount).filter(CustomerAccount.account_id == account_id)
            result = session.execute(query).scalars().first()
            
            if result is None:
                return jsonify({"message": "Customer Account not found"}), 404
            
            session.delete(result)
            session.commit()

    return jsonify({"message": "Customer Account successfully deleted"}), 200

@app.route("/products", methods=["GET"])
def get_products():
    query = select(Product)
    result = db.session.execute(query).scalars()
    products = result.all()
    return products_schema.jsonify(products)

@app.route("/products/<int:product_id>", methods=["GET"])
def get_product_by_id(product_id):
    query = select(Product).filter(Product.product_id == product_id)
    result = db.session.execute(query).scalar()
    if result is None:
        return jsonify({"error": "Product not found"}), 404
    return product_schema.jsonify(result)

@app.route("/products", methods=["POST"])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    with Session(db.engine) as session:
        with session.begin():
            new_product = Product(**product_data)
            session.add(new_product)
            session.commit()

    return jsonify({"message": "New product added successfully!"}), 201

@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    with Session(db.engine) as session:
        with session.begin():
            query = select(Product).filter(Product.product_id == product_id)
            result = session.execute(query).scalar()

            if result is None:
                return jsonify({"error": "Product not found"}), 404
            
            try:
                product_data = product_schema.load(request.json)
            except ValidationError as err:
                return jsonify(err.messages), 400

            for field, value in product_data.items():
                setattr(result, field, value)

            session.commit()
            return jsonify({"message": f"Product with ID {product_id} updated successfully"}), 200

@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    delete_statement = delete(Product).where(Product.product_id == product_id)
    with db.session.begin():
        result = db.session.execute(delete_statement)
        if result.rowcount == 0:
            return jsonify({"error": f"Product with ID {product_id} doesn't exist!"}), 404

        return jsonify({"message": "Product deleted successfully!"}), 200

@app.route("/orders", methods=["GET"])
def get_orders():
    query = select(Order)
    result = db.session.execute(query).scalars().all()
    orders_with_products = []

    for order in result:
        order_dict = {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "date": order.date,
            "products": [product.product_id for product in order.products]
        }
        orders_with_products.append(order_dict)

    return jsonify(orders_with_products)

@app.route("/orders", methods=["POST"])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    product_ids = order_data.get('product_id', [])

    new_order = Order(
        customer_id=order_data['customer_id'],
        date=order_data['date']
    )

    with Session(db.engine) as session:
        with session.begin():
            for product_id in product_ids:
                product = session.query(Product).get(product_id)
                if product:
                    new_order.products.append(product)

            session.add(new_order)
            session.commit()

    return jsonify({"message": "Order added successfully!"}), 201

@app.route('/orders/<int:order_id>', methods=["PUT"])
def update_order(order_id):
    try:
        json_order = request.json
        products = json_order.pop('products', None)
        
        order_data = order_schema.load(json_order, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    with Session(db.engine) as session:
        with session.begin():
            query = select(Order).filter(Order.order_id == order_id)
            result = session.execute(query).scalar()
            if result is None:
                return jsonify({"message": "Order Not Found"}), 404
            
            order = result
            
            for field, value in order_data.items():
                setattr(order, field, value)
            
            if products is not None:
                order.products.clear()
                for id in products:
                    product = session.execute(select(Product).filter(Product.product_id == id)).scalar()
                    if product:
                        order.products.append(product)
                    else:
                        return jsonify({"error": f"Product with ID {id} not found"}), 404

            session.commit()
            
    return jsonify({"message": "Order was successfully updated!"}), 200

@app.route("/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    delete_statement = delete(Order).where(Order.order_id == order_id)
    with db.session.begin():
        result = db.session.execute(delete_statement)
        if result.rowcount == 0:
            return jsonify({"error": f"Order with ID {order_id} doesn't exist!"}), 404
        return jsonify({"message": "Order deleted successfully!"}), 200

@app.route("/")
def home():
    return "This is a tasty API"

if __name__ == "__main__":
    app.run(debug=True, port=5000)




















####--------------------------------OLD CODE --------------------------------------------------------------------------------------------------------------------

# # First i need to open up a virtual envirnonment so that i can add all the dependecies that i will need for the project.


# # Opening a virtual Environment:
# # python -m venv my_venv

# # Next we will need to activate it.
# # my_venv\Scripts\activate

# # Next we need to install Flask into the virtual environment.
# # pip install flask

# # Now we need to install Flask Marshmalllow
# # pip install flask-marshmallow

# #Now we need to go install the sql connector
# #pip install mysql-connector-python


# #Now we can Start Setting up our imports

# from flask import Flask 
# from flask_marshmallow import Marshmallow 
# from marshmallow import fields 
# from flask import Flask, jsonify, request  
# from flask_sqlalchemy import SQLAlchemy 
# from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship, declarative_base 
# from sqlalchemy import select, delete, Column, Integer, String, ForeignKey, Table, Date, Float 
# from flask_marshmallow import Marshmallow 
# from flask_cors import CORS 
# import datetime 
# from typing import List 
# from marshmallow import ValidationError, fields, validates, validate 
# import re 

# app = Flask(__name__) # instantiate our app 
# CORS(app) # enable cross origin resource sharing
# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:Sennenga28!@localhost/project_e_commerce_db" # set our database URI

# class Base(DeclarativeBase): # create a base class for our models
#     pass

# # instantiate our db
# db = SQLAlchemy(app, model_class=Base) # instantiate our db
# ma = Marshmallow(app) # instantiate our marshmallow object



# # ==== DB MODELS =============================================================================================================================================
# # The DB models are the classes that represent the tables in our database. We will create the following tables:
# # Customer
# # CustomerAccount
# # Order
# # Product

# # Customer table with a one to one relationship with the CustomerAccount table and a one to many relationship with the Order table
# class Customer(Base): # Customer table
#     __tablename__ = "Customers"  # table name
#     customer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True) # customer_id column
#     name: Mapped[str] = mapped_column(db.String(255), nullable=False) # name column
#     email: Mapped[str] = mapped_column(db.String(320), nullable=False) # email column
#     phone: Mapped[str] = mapped_column(db.String(15)) # phone column
    
#     customer_account: Mapped["CustomerAccount"] = relationship("CustomerAccount", back_populates="customer", uselist=False) # one to one relationship with the CustomerAccount table
#     orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer") # one to many relationship with the Order table

# # Customer Account with a one to one relationship with the Customer table
# class CustomerAccount(Base): 
#     __tablename__ = "Customer_Accounts" # table name

#     account_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
#     username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
#     password: Mapped[str] = mapped_column(String(255), nullable=False)

#     customer_id: Mapped[int] = mapped_column(Integer, ForeignKey('Customers.customer_id'))  # foreign key to the Customer table
#     customer: Mapped["Customer"] = relationship("Customer", back_populates="customer_account")  # one to one relationship with the Customer table


# # associate table between orders and products to manage the many to many relationship
# order_product = db.Table( 
#     "Order_Product", # table name
#     Base.metadata, # metadata from the base class
#     db.Column("order_id", db.ForeignKey("Orders.order_id"), primary_key=True), # foreign key to the Orders table
#     db.Column("product_id", db.ForeignKey("Products.product_id"), primary_key=True) # foreign key to the Products table      
# )

# # creating Orders and a one to many relationship bewtween Customer and Order
# class Order(Base):
#     __tablename__ = "Orders"

#     order_id: Mapped[int] = mapped_column(primary_key=True)
#     date: Mapped[datetime.date] = mapped_column(db.Date, nullable = False)
#     customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customers.customer_id"))

#     customer: Mapped["Customer"] = db.relationship(back_populates="orders") # one to many relationship with the Customer table
#     products: Mapped[List["Product"]] = db.relationship(secondary=order_product) # many to many relationship with the Products table

# class Product(Base):
#     __tablename__ = "Products"
#     product_id: Mapped[int] = mapped_column(primary_key=True)
#     name: Mapped[str] = mapped_column(db.String(255), nullable=False)
#     price: Mapped[float] = mapped_column(db.Float, nullable=False)


# with app.app_context(): # create all tables
#     db.create_all() #

# # ==== Customer SCHEMA ===========================================================================================

# # We will need a schema for each of the tables in our database. We will create the following schemas:
# # CustomerSchema
# # AccountSchema
# # ProductSchema
# # OrderSchema

# # The CustomerSchema class is used to validate the data that is sent to the API and to serialize the data that is returned from the API.
# class CustomerSchema(ma.Schema):
#     customer_id = fields.Integer() 
#     name = fields.String(required=True, validate=fields.Length(min=1))
#     email = fields.String(required=True)
#     phone = fields.String(required=True)

# # The Meta class is used to specify the fields that are returned from the schema.
#     class Meta:
#         fields = ("customer_id", "email", "name", "phone")
# # The validate_email method is used to validate the email field using a regular
#     @validates('email') # validate email
#     def validate_email(self, value): 
#         email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$' # regex for email
#         if not re.match(email_regex, value): # if email does not match regex
#             raise ValidationError("Invalid email address.") # raise an error
# # The validate_phone method is used to validate the phone field using a regular expression.  
#     @validates('phone')
#     def validate_phone(self, value):
#         phone_regex = r'^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$'
#         if not re.match(phone_regex, value):
#             raise ValidationError("Invalid phone number. Must be in the format +123456789, 123-456-7890, or similar.")
        
# customer_schema = CustomerSchema() # create an instance of the CustomerSchema
# customers_schema = CustomerSchema(many=True) # create an instance of the CustomerSchema for multiple customers


# # ==== CUSTOMERS API ROUTES =========================================================================================
# # The API routes are used to interact with the database through the API. We will create the following routes:
# # GET /customers - get all customers
# # POST /customers - add a customer
# # PUT /customers/<id> - update a customer by id
# # DELETE /customers/<id> - delete a customer by id

# # get all customers
# @app.route("/customers", methods = ["GET"])
# def get_customers():
#     query = select(Customer) 
#     # SELECT * FROM Customers
#     result = db.session.execute(query).scalars() # execute the query
#     customers = result.all() # get all the customers

#     return customers_schema.jsonify(customers) # return the customers in json format

# # add a customer
# @app.route("/customers", methods = ["POST"])
# def add_customer():
#     try:
#         customer_data = customer_schema.load(request.json) # load the request data into the schema
#     except ValidationError as err: # if there is a validation error
#         return jsonify(err.messages), 400 # return the error messages and a Bad Request status code
 
#     with Session(db.engine) as session: # create a session  
#         with session.begin(): # begin a transaction
#             name = customer_data['name'] # get the name from the request
#             email = customer_data['email'] # get the email from the request
#             phone = customer_data['phone'] # get the phone from the request

#             new_customer = Customer(name=name, email=email, phone=phone) # create a new customer object
#             session.add(new_customer) # add the new customer to the session
#             session.commit()
    
#     # return jsonify(new_customer), 201 # new resource was created
#     return jsonify({"message": "New Customer successfully added!"}), 201 # return a success message and a Created status code

# # UPDATE a Customer
# @app.route("/customers/<int:id>", methods=["PUT"])
# def update_customer(id):
#     with Session(db.engine) as session:
#         with session.begin():

#             query = select(Customer).filter(Customer.customer_id == id) # select the customer by id
#             result = session.execute(query).scalars().first() # execute the query and get the first result
#             if result is None:  # if the result is None
#                 return jsonify({"message": "Customer not found"}), 404  # return a not found status code
        
#             customer = result # get the customer
#             try: 
#                 customer_data = customer_schema.load(request.json) # load the request data into the schema
#             except ValidationError as e: # if there is a validation error
#                 return jsonify(e.messages), 400 #Bad Request

#             for field, value in customer_data.items(): # loop through the fields and values
#                 setattr(customer, field, value) # set the attribute of the customer to the value

#             session.commit() 

#     return jsonify({"message": "Customer details updated successfully"}), 200 # return a success message and an OK status code

# @app.route("/customers/<int:id>", methods=["DELETE"])
# def delete_customer(id):

#     with Session(db.engine) as session:
#         with session.begin():
#             query = select(Customer).filter(Customer.customer_id == id)
#             result = session.execute(query).scalars().first()
            
#             if result is None:
#                 return jsonify({"error": "Customer not found..."}), 404 #not found
            
#             session.delete(result)
        
#         return jsonify({"message": "Customer removed successfully!"})

# # ====================================== SCHEMA =======================================================
# # The AccountSchema class is used to validate the data that is sent to the API and to serialize the data that is returned from the API.

# class AccountSchema(ma.Schema):
#     account_id = fields.Integer(dump_only=True)
#     username = fields.String(required=True, validate=fields.Length(min=4, max=255))
#     password = fields.String(required=True, validate=fields.Length(min=6, max=255))
#     customer_id = fields.Integer(required=True)

#     class Meta:
#         fields = ("account_id", "username", "password", "customer_id")

#     @validates('password')
#     def validate_password(self, value):
#         if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$', value):
#             raise ValidationError("Password must be at least 6 characters long and contain at least one letter and one number.")

#     @validates('username')
#     def validate_username(self, value):
#         if not re.match(r'^\w+$', value):  # Alphanumeric characters and underscores
#             raise ValidationError("Username must contain only letters, numbers, and underscores.")

# account_schema = AccountSchema()
# accounts_schema = AccountSchema(many=True)

# # ==== CustomerAccount API ROUTE ========================================================================
# # The API routes are used to interact with the database through the API. We will create the following routes:
# # GET /customeraccounts - get all customer accounts
# # POST /customeraccounts - add a customer account
# # PUT /customeraccounts/<id> - update a customer account by id
# # DELETE /customeraccounts/<id> - delete a customer account by id

 
# # # Get all customer accounts
# @app.route("/customeraccounts", methods=["GET"])
# def get_customer_account():
    
#     query = select(CustomerAccount)

#     result = db.session.execute(query).scalars() 
#     customers = result.all() 

#     return accounts_schema.jsonify(customers)


# @app.route("/customeraccount", methods=["POST"])

# def add_customer_account():
#     try:
#         customer_account_data = account_schema.load(request.json)
#     except ValidationError as e:
#         return jsonify(e.messages), 400
    
#     with Session(db.engine) as session:
#         with session.begin():
#             username = customer_account_data['username']
#             password = customer_account_data['password']
#             customer_id = customer_account_data['customer_id']
#             new_account = CustomerAccount(username=username, password=password, customer_id=customer_id)
#             session.add(new_account)
#             session.commit()

#         return jsonify({"message": "New Customer successfully added!"}), 201 
    

# @app.route("/customeraccount/<int:account_id>", methods=["PUT"])
# def update_customer_account(account_id):
    
#     with Session(db.engine) as session:
#         with session.begin():
#             query = select(CustomerAccount).filter_by(account_id=account_id)
#             result = session.execute(query).scalars().first()
            
#             if result is None:
#                 return jsonify({"message": "Customer not found"}), 404 # resource not found
            
#             customer = result

#             try: 
#                 customer_account_data = account_schema.load(request.json)
#             except ValidationError as e:
#                 return jsonify(e.messages), 400 #Bad Request
            
#             for field, value in customer_account_data.items():
#                 setattr(customer, field, value)

#             session.commit() 

#     return jsonify({"message": "Customer details updated successfully"}), 200 #OK         


# @app.route("/customeraccount/<int:account_id>", methods=["DELETE"])
# def delete_customer_account(account_id):
#     with Session(db.engine) as session:
#         with session.begin():
#             query = select(CustomerAccount).filter(CustomerAccount.account_id == account_id)
#             result = session.execute(query).scalars().first()
            
#             if result is None:
#                 return jsonify({"message": "Customer not found"}), 404 # resource not found
            
#             session.delete(result)
            

#             return jsonify({"message": "Customer successfully deleted"}), 200 #OK

# # ==== Products Schema ========================================================================
# # The ProductSchema class is used to validate the data that is sent to the API and to serialize the data that is returned from the API.
# class ProductSchema(ma.Schema):
#     product_id = fields.Integer(required=False)
#     name = fields.String(required=True, validate=validate.Length(min=1)) #name must be at least 1 character long
#     price = fields.Float(required=True, validate=validate.Range(min=0)) #price must be a positive number

#     class Meta:
#         fields = ("product_id", "name", "price") #fields to be returned

# #instance of schema 
# product_schema = ProductSchema()
# products_schema = ProductSchema(many=True)

# # ==== Products API ROUTEs ========================================================================
# # The API routes are used to interact with the database through the API. We will create the following routes:
# # GET /products - get all products
# # POST /products - add a product
# # PUT /products/<id> - update a product by id
# # DELETE /products/<id> - delete a product by id

# #get products
# @app.route("/products", methods=["GET"])
# def get_products():
#     query = select(Product) #SELECT * FROM product
#     result = db.session.execute(query).scalars()
#     products = result.all()

#     return products_schema.jsonify(products) #print it this way 

# #get products by id
# @app.route("/products/<int:product_id>", methods=["GET"])
# def get_product_by_id(product_id):
#     query = select(Product).filter(Product.product_id == product_id)
#     result = db.session.execute(query).scalar()
#     print(result)
#     if result is None:
#         return jsonify({"error": "Product not found"}), 404 # not found
#     product = result
#     try:
        
#         return product_schema.jsonify(product)
#     except ValidationError as err:
#         return jsonify(err.messages), 400 # Bad request
    
# # get product by name
# # @app.route("/products/by-name", methods=["GET"])
# # def get_product_by_name():
# #     name = request.args.get("name")
# #     search = f"%{name}%" #% is a wildcard
# #     # use % with LIKE to find partial matches
# #     query = select(Product).where(Product.name.like(search)).order_by(Product.price.asc())

# #     products = db.session.execute(query).scalars().all()
# #     print(products)

# #     return products_schema.jsonify(products)


# #create products
# @app.route("/products", methods=["POST"])
# def add_product():
#     try:
        
#         product_data = product_schema.load(request.json)
#     except ValidationError as err:
        
#         return jsonify(err.messages) , 400 # BAD REQUEST - not enough or mismatched data

#     with Session(db.engine) as session:
#         with session.begin():

#             new_product = Product(name=product_data['name'],price= product_data['price'])
#             session.add(new_product)
#             session.commit()

#     return jsonify({"Message": "new product added successfully"}) , 201 #new resource created

# #update products by ID
# @app.route("/products/<int:product_id>", methods =["PUT"])
# def update_product(product_id):
#     with Session(db.engine) as session:
#         with session.begin():

#             query = select(Product).filter(Product.product_id == product_id)
#             result = session.execute(query).scalar() 
#             print(result)
#             if result is None:

#                 return jsonify({"error": "Product not found"}), 404 # not found
#             product = result
#             try:
#                 product_data = product_schema.load(request.json)
#             except ValidationError as err:

#                 return jsonify(err.messages), 400 # Bad request
            

#             for field, value in product_data.items():
#                 setattr(product,field, value)

#             session.commit()
#             return jsonify({"Message":f"Product with id of {product_id} updated successfully"}), 200 # update successful

# #delete products
# @app.delete("/products/<int:product_id>")
# def delete_product(product_id):

#     delete_statment = delete(Product).where(Product.product_id == product_id)
#     with db.session.begin():
#         result = db.session.execute(delete_statment)
#         if result.rowcount == 0:

#             return jsonify({"error":f"Product with id of {product_id} doesn't exist!"}), 404

#         return jsonify({"message":"Product is gone, probably"}), 200


# # ==== Order Schema ========================================================================
# # The OrderSchema class is used to validate the data that is sent to the API and to serialize the data that is returned from the API.

# #orders 
# class OrderSchema(ma.Schema):
#     order_id = fields.Integer(required= False)
#     customer_id = fields.Integer(required = True)
#     date = fields.Date(required=True) #"2024-07-05"
#     product_id = fields.List(fields.Integer(), required= False)

#     class Meta:
#         fields = ("order_id","customer_id","date","product_id")
# #Instance of schemas
# order_schema = OrderSchema()
# orders_schema = OrderSchema(many=True)


# # ==== Orders API ROUTE ========================================================================
# # The API routes are used to interact with the database through the API. We will create the following routes:
# # GET /orders - get all orders
# # POST /orders - add an order
# # PUT /orders/<id> - update an order by id
# # DELETE /orders/<id> - delete an order by id
# # For this one we use @app.method instead of @app.route showing we can use different methods

# #get orders
# @app.get("/orders") # get all orders
# def get_orders():
#     query = select(Order) 
#     result = db.session.execute(query).scalars().all()
#     orders_with_products = []
#     orders = result
#     for order in orders:
#         order_dict = {
#             "order_id": order.order_id,
#             "customer_id": order.customer_id,
#             "date": order.date,
#             "products": [product.product_id for product in order.products]
#         }
#         orders_with_products.append(order_dict)

#     return jsonify(orders_with_products)


# #create orders
# @app.post("/orders")
# def add_order():

#     try:

#         order_data = order_schema.load(request.json)
#     except ValidationError as err:    

#         return jsonify(err.messages), 400
#     product_ids = order_data.get('product_id', [])


#     new_order = Order(
#         customer_id=order_data['customer_id'],
#         date=order_data['date']
#     )

#     with Session(db.engine) as session:
#         with session.begin():

#             for product_id in product_ids:
#                 product = session.query(Product).get(product_id)
#                 if product:
#                     new_order.products.append(product)


#             session.add(new_order)
#             session.commit()

#     return jsonify({"message": "Order added successfully"}), 201

# # update an order by its ID
# @app.route('/orders/<int:order_id>', methods=["PUT"])
# def update_order(order_id):
#     try:
#         json_order = request.json
#         products = json_order.pop('products', None)
        
#         # Validate the order data excluding products
#         order_data = order_schema.load(json_order, partial=True)
#     except ValidationError as err:
#         return jsonify(err.messages), 400
    
#     with Session(db.engine) as session:
#         with session.begin():
#             query = select(Order).filter(Order.order_id == order_id)
#             result = session.execute(query).scalar()
#             if result is None:
#                 return jsonify({"message": "Order Not Found"}), 404
            
#             order = result
            
#             for field, value in order_data.items():
#                 setattr(order, field, value)
            
#             # If products are provided, update the products associated with the order
#             if products is not None:
#                 order.products.clear()
#                 for id in products:
#                     product = session.execute(select(Product).filter(Product.product_id == id)).scalar()
#                     if product:
#                         order.products.append(product)
#                     else:
#                         return jsonify({"Error": f"Product with ID {id} not found"}), 404

#             session.commit()
            
#     return jsonify({"message": "Order was successfully updated!"}), 200
    
# #del orders 
# @app.delete("/orders/<int:order_id>")
# def delete_order(order_id):
#     delete_statement = delete(Order).where(Order.order_id == order_id)
#     with db.session.begin():
#         result = db.session.execute(delete_statement)
#         if result.rowcount == 0:
#             return jsonify({"Error":f"Order with id {order_id} doesnt exist"})
#         return jsonify({"message":"Its outta here! "})



# @app.route("/") # home route
# def home(): # home function
#     return "This is a tasty API " # return a message




# if __name__ == "__main__":  # if the script is run
#     app.run(debug=True, port=5000) # run the app on port 5000 in debug mode


