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
    
    customer_account: Mapped["CustomerAccount"] = relationship("CustomerAccount", back_populates="customer", uselist=False, cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer", cascade="all, delete-orphan") #Cascade all delete orphan was added to delete the customer account and orders when the when the customer is deleted

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
    products: Mapped[List["Product"]] = db.relationship(
        secondary=order_product, 
        backref="orders",  # Allows bidirectional access if needed
        passive_deletes=True  # Enables passive deletion of related records in the association table
    )

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

@app.route("/customers/<int:customer_id>", methods=["GET"])
def get_customer_by_id(customer_id):
    query = select(Customer).filter(Customer.customer_id == customer_id)
    result = db.session.execute(query).scalar()
    if result is None:
        return jsonify({"error": "Customer not found"}), 404
    return customer_schema.jsonify(result)

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
            session.flush()  # Ensure the ID is generated
            customer_id = new_customer.customer_id
            session.commit()

    return jsonify({
        "message": "New Customer successfully added!",
        "customer_id": customer_id  # Return the ID now that it's safely accessed
    }), 201

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
            # Find the customer
            query = select(Customer).filter(Customer.customer_id == id)
            customer = session.execute(query).scalars().first()

            if customer is None:
                return jsonify({"error": "Customer not found..."}), 404
            
            # Manually delete associated order_product entries for each order
            for order in customer.orders:
                delete_associations = delete(order_product).where(order_product.c.order_id == order.order_id)
                session.execute(delete_associations)
            
            # Now that associations are deleted, delete the customer
            session.delete(customer)
            session.commit()

        return jsonify({"message": "Customer and all associated data removed successfully!"}), 200


@app.route("/customeraccounts", methods=["GET"])
def get_customer_account():
    query = select(CustomerAccount)
    result = db.session.execute(query).scalars()
    accounts = result.all()
    return accounts_schema.jsonify(accounts)

@app.route("/customeraccounts/<int:account_id>", methods=["GET"])
def get_customer_account_by_id(account_id):
    query = select(CustomerAccount).filter(CustomerAccount.account_id == account_id)
    result = db.session.execute(query).scalar()
    if result is None:
        return jsonify({"error": "Customer Account not found"}), 404
    return account_schema.jsonify(result)


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
            session.flush()  # Ensure the account ID is generated
            account_id = new_account.account_id  # Retrieve the account ID
            session.commit()

    return jsonify({
        "message": "New Customer Account successfully added!",
        "account_id": account_id  # Return the account ID
    }), 201

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
    with Session(db.engine) as session:
        with session.begin():
            # First, delete the associations in the order_product table
            delete_associations = delete(order_product).where(order_product.c.order_id == order_id)
            session.execute(delete_associations)
            
            # Now, delete the order itself
            query = select(Order).filter(Order.order_id == order_id)
            result = session.execute(query).scalar()

            if result is None:
                return jsonify({"error": f"Order with ID {order_id} doesn't exist!"}), 404

            session.delete(result)
            session.commit()

        return jsonify({"message": "Order deleted successfully!"}), 200

@app.route("/")
def home():
    return "This is a tasty API"

if __name__ == "__main__":
    app.run(debug=True, port=5000)




