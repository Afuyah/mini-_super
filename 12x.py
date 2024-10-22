import os
from app import create_app, db
from app.models import User, Role
from werkzeug.security import generate_password_hash

app = create_app()
app.app_context().push()

def create_admin():
    # Remove any existing user with the username 'admin' in lowercase
    existing_user = User.query.filter_by(username='admin').first()
    
    if existing_user:
        db.session.delete(existing_user)
        db.session.commit()
        print("Existing admin user removed.")

    # Create the new admin user
    admin_user = User.query.filter_by(username='admin').first()
    
    if not admin_user:
        admin_user = User(
            username='admin',
            
            role=Role.ADMIN  # Use the Role enum directly
        )
        admin_user.set_password('12x')  # Hash the password using the method defined in User model
        db.session.add(admin_user)
        db.session.commit()
        print("New admin user created successfully!")
    else:
        print("Admin user already exists.")

if __name__ == '__main__':
    # Create the database tables
    db.create_all()
    create_admin()
