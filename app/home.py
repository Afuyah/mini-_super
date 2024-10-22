
# app/home.py
from flask import Blueprint, render_template

# Define the Blueprint
home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def index():
    return render_template('home.html')
