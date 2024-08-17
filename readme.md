## Recent Changes and Improvements

This is an improvement from my original API. You can view the original project on GitHub: [BackendCore_E_Commerce_API](https://github.com/Skylar-Ennenga/BackendCore_E_Commerce_API.git).

### Checklist of Changes:

- [x] **Cascade Delete for Customers:** Added `cascade="all, delete-orphan"` to relationships in the `Customer` model for `customer_account` and `orders`.
- [x] **Manual Deletion of `order_product` Associations:** Implemented manual deletion of associated records in the `order_product` table before deleting an `Order` or `Customer`.
- [x] **Enhanced `delete_customer` Route:** Updated to remove related `order_product` entries for each order before deleting the customer.
- [x] **Enhanced `delete_order` Route:** Updated to remove associated records from the `order_product` table before deleting the order itself.
- [x] **Error Handling Improvements:** Added additional error handling for safer deletion operations and to prevent `IntegrityError`.

# E-Commerce API with Flask and SQLAlchemy

This repository contains a RESTful API built with Flask and SQLAlchemy for managing customers, accounts, products, and orders in an e-commerce application.

## Features

- **Customers**: CRUD operations for managing customer data including name, email, and phone.
- **Accounts**: Manage customer accounts with username and password, associated with customer profiles.
- **Products**: CRUD operations for managing product data including name and price.
- **Orders**: Manage customer orders with date and associated products.

## Technologies Used

- **Python**: Programming language used for backend development.
- **Flask**: Micro web framework for Python.
- **SQLAlchemy**: SQL toolkit and Object-Relational Mapping (ORM) for Python.
- **MySQL**: Database management system used for persistent data storage.
- **Marshmallow**: Library for object serialization/deserialization.

## Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/project_e_commerce.git
   cd project_e_commerce
   ```

2. **Setup Virtual Environment:**

   ```bash
   python -m venv my_venv
   my_venv\Scripts\activate  # On Windows
   source my_venv/bin/activate  # On macOS/Linux
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Database:**

   - Ensure MySQL server is running.
   - Set your database URI in `app.config["SQLALCHEMY_DATABASE_URI"]` in `app.py`.

5. **Initialize Database:**

   ```bash
   python app.py
   ```

6. **Run the Application:**

   ```bash
   flask run
   ```

7. **Access API Endpoints:**

   - Customers: `GET /customers`, `POST /customers`, `PUT /customers/<id>`, `DELETE /customers/<id>`
   - Accounts: `GET /customeraccounts`, `POST /customeraccounts`, `PUT /customeraccounts/<id>`, `DELETE /customeraccounts/<id>`
   - Products: `GET /products`, `POST /products`, `PUT /products/<id>`, `DELETE /products/<id>`
   - Orders: `GET /orders`, `POST /orders`, `PUT /orders/<id>`, `DELETE /orders/<id>`

## API Documentation

- Detailed API documentation can be found in the `app.py` file with descriptions of each endpoint, request formats, and response formats.

