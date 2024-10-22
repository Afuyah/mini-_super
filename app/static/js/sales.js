// static/js/sales.js

let cart = [];
let totalPrice = 0;

// Initialize SocketIO client
const socket = io();

// Handle stock updates
socket.on('stock_updated', (data) => {
    // Update product stock in the UI
    updateProductStockUI(data.id, data.stock);
});

socket.on('low_stock_alert', (data) => {
    alert(`Low stock alert for ${data.product_name}: Only ${data.stock} left!`);
});

// Function to filter products by category
function filterCategory(categoryId) {
    fetch(`/stock/categories/${categoryId}/products`)
        .then(response => response.json())
        .then(data => {
            const productList = document.getElementById('product_list');
            productList.innerHTML = '';

            data.products.forEach(product => {
                const listItem = document.createElement('li');
                listItem.id = `product-${product.id}`;
                listItem.innerHTML = `
                    <button onclick="addToCart(${product.id}, '${product.name}', ${product.price})" ${product.stock <= 0 ? 'disabled' : ''}>
                        ${product.name} - Ksh ${product.price} (${product.stock} left)
                    </button>
                `;
                productList.appendChild(listItem);
            });
        });
}

// Function to add product to cart
function addToCart(productId, productName, price) {
    fetch('/sales/add_to_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, quantity: 1 })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const existingItem = cart.find(item => item.product_id === productId);
            if (existingItem) {
                existingItem.quantity += 1;
                existingItem.total_price += price;
            } else {
                cart.push({
                    product_id: productId,
                    product_name: productName,
                    quantity: 1,
                    price: price,
                    total_price: price
                });
            }
            updateCartUI();
        } else {
            alert(data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Function to update the cart UI
function updateCartUI() {
    const cartList = document.getElementById('cart_list');
    cartList.innerHTML = '';
    totalPrice = 0;

    cart.forEach(item => {
        const listItem = document.createElement('li');
        listItem.textContent = `${item.product_name} - Quantity: ${item.quantity} - Price: Ksh ${item.total_price}`;
        cartList.appendChild(listItem);
        totalPrice += item.total_price;
    });

    document.getElementById('total_price').textContent = totalPrice;
}

// Function to toggle customer name input based on payment method
function toggleCustomerName() {
    const paymentMethod = document.getElementById('payment_method').value;
    const customerNameDiv = document.getElementById('customer_name_div');
    if (paymentMethod === 'credit') {
        customerNameDiv.style.display = 'block';
    } else {
        customerNameDiv.style.display = 'none';
    }
}

// Function to complete the sale
function checkout() {
    if (cart.length === 0) {
        alert('Your cart is empty!');
        return;
    }

    const paymentMethod = document.getElementById('payment_method').value;
    const customerName = document.getElementById('customer_name').value || null;

    fetch('/sales/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            cart: cart,
            payment_method: paymentMethod,
            customer_name: customerName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            cart = [];
            updateCartUI();
            // Optionally, reload products to reflect updated stock
            window.location.reload();
        } else {
            alert(data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Function to update product stock in the UI
function updateProductStockUI(productId, newStock) {
    const productItem = document.getElementById(`product-${productId}`);
    if (productItem) {
        const button = productItem.querySelector('button');
        button.innerHTML = button.innerHTML.replace(/\(\d+ left\)/, `(${newStock} left)`);
        button.disabled = newStock <= 0;
    }
}
