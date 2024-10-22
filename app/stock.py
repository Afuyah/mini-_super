from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Product, Category
from app import socketio, limiter
from flask_socketio import emit

stock_bp = Blueprint('stock', __name__)

# Constants for flash messages
FLASH_ACCESS_DENIED = 'Access denied.'
FLASH_CATEGORY_EXISTS = 'Category already exists.'
FLASH_PRODUCT_EXISTS = 'Product already exists.'
FLASH_CATEGORY_CREATED = 'Category "{}" created successfully.'
FLASH_CATEGORY_UPDATED = 'Category "{}" updated successfully.'
FLASH_CATEGORY_DELETED = 'Category "{}" deleted successfully.'
FLASH_PRODUCT_ADDED = 'Product "{}" added successfully.'
FLASH_PRODUCT_UPDATED = 'Product "{}" updated successfully.'
FLASH_PRODUCT_DELETED = 'Product "{}" deleted successfully.'
FLASH_INSUFFICIENT_STOCK = 'Insufficient stock for {}.'

# Rate limit for stock operations
@stock_bp.route('/categories')
@limiter.limit("100 per hour")
@login_required
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@stock_bp.route('/categories/new', methods=['GET', 'POST'])
@limiter.limit("50 per hour")
@login_required
def new_category():
    if not current_user.is_admin():
        flash(FLASH_ACCESS_DENIED)
        return redirect(url_for('stock.categories'))

    if request.method == 'POST':
        name = request.form['name']
        if Category.query.filter_by(name=name).first():
            flash(FLASH_CATEGORY_EXISTS)
            return redirect(url_for('stock.new_category'))

        new_category = Category(name=name)
        db.session.add(new_category)
        db.session.commit()
        flash(FLASH_CATEGORY_CREATED.format(name))
        return redirect(url_for('stock.categories'))

    return render_template('new_category.html')

@stock_bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@limiter.limit("50 per hour")
@login_required
def edit_category(id: int):
    category = Category.query.get_or_404(id)

    if request.method == 'POST':
        category.name = request.form['name']
        db.session.commit()
        flash(FLASH_CATEGORY_UPDATED.format(category.name))
        return redirect(url_for('stock.categories'))

    return render_template('edit_category.html', category=category)

@stock_bp.route('/categories/<int:id>/delete', methods=['POST'])
@limiter.limit("20 per hour")
@login_required
def delete_category(id: int):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash(FLASH_CATEGORY_DELETED.format(category.name))
    return redirect(url_for('stock.categories'))

@stock_bp.route('/products')
@limiter.limit("100 per hour")
@login_required
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@stock_bp.route('/products/new', methods=['GET', 'POST'])
@limiter.limit("50 per hour")
@login_required
def new_product():
    if not current_user.is_admin():
        flash(FLASH_ACCESS_DENIED)
        return redirect(url_for('stock.products'))

    categories = Category.query.all()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        stock = request.form['stock']
        category_id = request.form['category']

        if Product.query.filter_by(name=name).first():
            flash(FLASH_PRODUCT_EXISTS)
            return redirect(url_for('stock.new_product'))

        new_product = Product(
            name=name,
            price=float(price),
            stock=int(stock),
            category_id=category_id
        )
        db.session.add(new_product)
        db.session.commit()
        flash(FLASH_PRODUCT_ADDED.format(name))

        # Emit real-time stock update
        socketio.emit('stock_updated', {
            'id': new_product.id,
            'name': new_product.name,
            'stock': new_product.stock
        }, broadcast=True)

        return redirect(url_for('stock.products'))

    return render_template('new_product.html', categories=categories)

@stock_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@limiter.limit("50 per hour")
@login_required
def edit_product(id: int):
    if not current_user.is_admin():
        flash(FLASH_ACCESS_DENIED)
        return redirect(url_for('stock.products'))

    product = Product.query.get_or_404(id)
    categories = Category.query.all()

    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.category_id = request.form['category']

        db.session.commit()
        flash(FLASH_PRODUCT_UPDATED.format(product.name))

        # Emit real-time stock update
        socketio.emit('stock_updated', {
            'id': product.id,
            'name': product.name,
            'stock': product.stock
        }, broadcast=True)

        return redirect(url_for('stock.products'))

    return render_template('edit_product.html', product=product, categories=categories)

@stock_bp.route('/products/<int:id>/delete', methods=['POST'])
@limiter.limit("20 per hour")
@login_required
def delete_product(id: int):
    if not current_user.is_admin():
        flash(FLASH_ACCESS_DENIED)
        return redirect(url_for('stock.products'))

    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash(FLASH_PRODUCT_DELETED.format(product.name))

    # Emit real-time stock update (stock set to 0)
    socketio.emit('stock_updated', {
        'id': product.id,
        'name': product.name,
        'stock': 0
    }, broadcast=True)

    return redirect(url_for('stock.products'))

# Route to handle real-time stock updates after sales
@stock_bp.route('/update_stock/<int:product_id>/<int:quantity>', methods=['POST'])
@login_required
@limiter.limit("100 per hour")
def update_stock(product_id: int, quantity: int):
    if not current_user.is_admin() and not current_user.is_cashier():
        flash(FLASH_ACCESS_DENIED)
        return redirect(url_for('stock.products'))

    product = Product.query.get_or_404(product_id)
    
    if product.stock < quantity:
        flash(FLASH_INSUFFICIENT_STOCK.format(product.name))
        return jsonify(success=False), 400

    product.stock -= quantity
    db.session.commit()

    # Emit real-time stock update
    socketio.emit('stock_updated', {
        'id': product.id,
        'name': product.name,
        'stock': product.stock
    }, broadcast=True)

    # Check for low stock and emit alert
    if product.stock < 5:
        socketio.emit('low_stock_alert', {
            'product_name': product.name,
            'stock': product.stock
        }, broadcast=True)

    return jsonify(success=True, stock=product.stock)
