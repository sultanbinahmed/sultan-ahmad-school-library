from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# إنشاء قاعدة البيانات
db = SQLAlchemy()

# جدول المستخدمين
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, teacher, admin, librarian
    grade = db.Column(db.String(20), nullable=True)  # الصف للطلاب
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    book_reservations = db.relationship('BookReservation', backref='user', lazy=True)
    resource_reservations = db.relationship('ResourceReservation', backref='user', lazy=True)

# جدول تصنيفات الكتب
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # العلاقات
    books = db.relationship('Book', backref='category', lazy=True)

# جدول الكتب
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=True)
    isbn = db.Column(db.String(20), nullable=True)
    publication_year = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    available = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    reservations = db.relationship('BookReservation', backref='book', lazy=True)
    added_by_user = db.relationship('User', foreign_keys=[added_by])

# جدول حجوزات الكتب
class BookReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    reservation_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, returned, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# جدول المختبرات وغرف المصادر
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # lab, resource_room
    description = db.Column(db.Text, nullable=True)
    capacity = db.Column(db.Integer, nullable=True)
    
    # العلاقات
    reservations = db.relationship('ResourceReservation', backref='resource', lazy=True)

# جدول حجوزات المختبرات وغرف المصادر
class ResourceReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    reservation_date = db.Column(db.Date, nullable=False)
    period = db.Column(db.Integer, nullable=False)  # رقم الحصة (1-8)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # قيد فريد لضمان عدم تكرار الحجز لنفس المورد في نفس اليوم والحصة
    __table_args__ = (
        db.UniqueConstraint('resource_id', 'reservation_date', 'period', name='unique_resource_reservation'),
    )

# جدول شروط الاستعارة
class BorrowingRules(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    max_days = db.Column(db.Integer, default=7)  # الحد الأقصى لأيام الاستعارة
    max_books = db.Column(db.Integer, default=3)  # الحد الأقصى لعدد الكتب المستعارة للشخص الواحد
    rules_text = db.Column(db.Text, nullable=True)  # نص الشروط
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
