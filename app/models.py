from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from enum import Enum
from datetime import datetime
from sqlalchemy import func, Index
from sqlalchemy.orm import validates  # Import validates for input validation
from app import db


# User Roles Enum
class Role(Enum):
    ADMIN = 'admin'
    CASHIER = 'cashier'

# User Model with Role-based Access
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)  
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False)

    def set_password(self, password):
        """Hashes the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the password is correct."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == Role.ADMIN

    def is_cashier(self):
        return self.role == Role.CASHIER

# Category Model
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    products = db.relationship('Product', backref='category', lazy='joined')  # Join on query to reduce additional queries

# Product Model with Input Validation and Low Stock Alert
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)  # Ensure price defaults to 0.0
    stock = db.Column(db.Integer, nullable=False, default=0)  # Ensure stock defaults to 0
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    sale_items = db.relationship('CartItem', backref='product', lazy='joined')  # Use joined loading for optimization

    # Add indexes for faster querying by category
    __table_args__ = (Index('ix_product_category_id', 'category_id'), )

    @validates('price', 'stock')
    def validate_price_stock(self, key, value):
        """Validate price and stock to avoid negative values."""
        if key == 'price' and value < 0:
            raise ValueError("Price cannot be negative")
        if key == 'stock' and value < 0:
            raise ValueError("Stock cannot be negative")
        return value

    def is_low_stock(self):
        """Returns True if the stock is below a certain threshold."""
        return self.stock < 10  # Threshold for low stock alert, can be adjusted

# Sale Model with Auto Stock Update and Total Price Indexing
class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # Indexed for time-based queries
    total = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # 'cash', 'mpesa', 'credit'
    customer_name = db.Column(db.String(200), nullable=True)  # Optional
    cart_items = db.relationship('CartItem', backref='sale', lazy='joined')  # Use joined loading for optimization

    def serialize(self):
        """Convert the Sale object to a dictionary format for JSON serialization."""
        return {
            'id': self.id,
            'date': self.date.strftime("%Y-%m-%d %H:%M:%S"),
            'total': self.total,
            'payment_method': self.payment_method,
            'customer_name': self.customer_name,
            'items': [item.serialize() for item in self.cart_items]
        }

    def finalize_sale(self):
        """Automatically updates stock after a sale."""
        for item in self.cart_items:
            item.product.stock -= item.quantity
            if item.product.stock < 0:
                raise ValueError(f"Not enough stock for {item.product.name}")
        db.session.commit()

    # Add index for total field to improve performance in queries related to total price
    __table_args__ = (Index('ix_sale_total', 'total'), Index('ix_sale_date', 'date'))

# CartItem Model
class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)

    def __repr__(self):
        return f'<CartItem product_id={self.product_id}, quantity={self.quantity}>'

    def serialize(self):
        """Convert the CartItem object to a dictionary format for JSON serialization."""
        product = self.product
        return {
            'product_name': product.name,
            'quantity': self.quantity,
            'total_price': self.quantity * product.price
        }

# Add necessary indexes for performance improvements
Index('ix_sale_date', Sale.date)
