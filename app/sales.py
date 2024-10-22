from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Product, Sale, CartItem, Category
from app import socketio, limiter
from flask_socketio import emit
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

sales_bp = Blueprint('sales', __name__)

# Helper function to check low stock
def check_low_stock(product):
    return product.stock < 5

# Route for cashier to view sales screen
@sales_bp.route('/sales')
@limiter.limit("200 per day")
@login_required
def sales_screen():
    categories = Category.query.all()
    return render_template('sales.html', categories=categories)

# API to fetch products by category
@sales_bp.route('/api/products/<int:category_id>', methods=['GET'])
@limiter.limit("200 per day")
@login_required
def get_products_by_category(category_id):
    products = Product.query.filter_by(category_id=category_id).all()
    product_list = [{'id': product.id, 'name': product.name, 'price': product.price, 'stock': product.stock} for product in products]
    return jsonify({'products': product_list})

# API to add item to cart (with quantity increment on repeated clicks)
@sales_bp.route('/add_to_cart', methods=['POST'])
@limiter.limit("500 per day")
@login_required
def add_to_cart():
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    if product.stock < quantity:
        return jsonify({'success': False, 'message': 'Insufficient stock'}), 400

    return jsonify({
        'success': True,
        'product_id': product.id,
        'product_name': product.name,
        'quantity': quantity,
        'price': product.price,
        'total_price': product.price * quantity
    })

# API to handle checkout
@sales_bp.route('/checkout', methods=['POST'])
@limiter.limit("100 per hour")
@login_required
def checkout():
    data = request.json
    cart = data.get('cart', [])
    payment_method = data.get('payment_method', 'cash')
    customer_name = data.get('customer_name')

    if not cart:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400

    total_amount = 0
    for item in cart:
        product = Product.query.get(item['id'])  # Changed from 'product_id' to 'id'
        if product is None:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        total_amount += product.price * item['quantity']

    sale = Sale(date=datetime.utcnow(), total=total_amount, payment_method=payment_method,
                customer_name=customer_name if payment_method == 'credit' else None)
    db.session.add(sale)

    try:
        for item in cart:
            product = Product.query.get(item['id'])
            if product.stock < item['quantity']:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Insufficient stock for {product.name}'}), 400

            product.stock -= item['quantity']
            # No commit here yet, we will do it after the loop

            cart_item = CartItem(product_id=product.id, quantity=item['quantity'], sale_id=sale.id)
            db.session.add(cart_item)

        db.session.commit()  # Commit all changes at once

        # Emit real-time updates after successful commit
        for item in cart:
            product = Product.query.get(item['id'])
            socketio.emit('stock_updated', {'id': product.id, 'name': product.name, 'stock': product.stock}, broadcast=True)
            if check_low_stock(product):
                socketio.emit('low_stock_alert', {'product_name': product.name, 'stock': product.stock}, broadcast=True)

        return jsonify({'success': True, 'message': 'Sale completed successfully'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Integrity error during transaction'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@sales_bp.route('/reports/daily', methods=['GET'])
@limiter.limit("50 per day")
@login_required
def daily_sales_report():
    today = datetime.today().date()  # Get today's date
    sales = Sale.query.filter(db.func.date(Sale.date) == today).all()

    if not sales:
        flash("No sales data available for today", "info")

    return render_template('daily_sales_report.html', sales=sales, today=today)


# Weekly sales report
@sales_bp.route('/reports/weekly', methods=['GET'])
@limiter.limit("50 per week")
@login_required
def weekly_sales_report():
    one_week_ago = datetime.utcnow().date() - timedelta(days=7)
    sales = Sale.query.filter(Sale.date >= one_week_ago).all()
    return render_template('weekly_sales_report.html', sales=sales)


@sales_bp.route('/reports/filter', methods=['POST'])
@login_required
def filter_sales_report():
    start_date_str = request.json.get('start_date')
    end_date_str = request.json.get('end_date')

    # Parse the dates from the request
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Use join to optimize querying sales with items
    sales = Sale.query.filter(Sale.date.between(start_date, end_date)).all()

    # Initialize report data and totals
    report_data = {}
    total_revenue = 0
    total_items_sold = 0
    total_profit = 0

    # Process sales data to gather required information
    for sale in sales:
        sale_items = sale.cart_items  # Get all items in the sale
        total_sale_value = sale.total  # Total revenue for this sale

        for item in sale_items:
            product_name = item.product.name  # Get the product name
            quantity = item.quantity
            unit_price = item.product.price  # Cost price of the product
            cost_price = unit_price * quantity
            profit = total_sale_value - cost_price

            # Group by product name instead of category
            if product_name not in report_data:
                report_data[product_name] = {
                    'total_sold': 0,
                    'total_revenue': 0,
                    'cost_price': 0,
                    'profit': 0,
                }

            # Accumulate the values for each product
            report_data[product_name]['total_sold'] += quantity
            report_data[product_name]['total_revenue'] += total_sale_value
            report_data[product_name]['cost_price'] += cost_price
            report_data[product_name]['profit'] += profit

            # Aggregate totals
            total_revenue += total_sale_value
            total_items_sold += quantity
            total_profit += profit

    # Convert the report data into a list for the JSON response
    report_data_list = [
        {
            'product_name': product,
            'total_sold': data['total_sold'],
            'total_revenue': data['total_revenue'],
            'cost_price': data['cost_price'],
            'profit': data['profit'],
        }
        for product, data in report_data.items()
    ]

    # Return the sales data and aggregated totals in JSON format
    return jsonify({
        'sales': report_data_list,
        'total_revenue': total_revenue,
        'total_items_sold': total_items_sold,
        'total_profit': total_profit
    })
