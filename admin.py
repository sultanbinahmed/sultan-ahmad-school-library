from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Book, Category, User
from forms import BookForm, CategoryForm
from app import db, admin_required
from datetime import datetime
import os

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@admin_required
def dashboard():
    # إحصائيات عامة
    stats = {
        'users_count': User.query.count(),
        'books_count': Book.query.count(),
        'categories_count': Category.query.count(),
        'reservations_count': BookReservation.query.count()
    }
    
    # آخر النشاطات
    recent_reservations = BookReservation.query.order_by(BookReservation.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                          active_tab='dashboard',
                          stats=stats,
                          recent_reservations=recent_reservations,
                          recent_users=recent_users,
                          current_year=datetime.now().year)

@admin.route('/books')
@admin_required
def books():
    page = request.args.get('page', 1, type=int)
    books = Book.query.order_by(Book.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/books.html', 
                          active_tab='books',
                          books=books,
                          current_year=datetime.now().year)

@admin.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add_book():
    form = BookForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            isbn=form.isbn.data,
            publication_year=form.publication_year.data,
            description=form.description.data,
            category_id=form.category_id.data,
            added_by=current_user.id
        )
        
        db.session.add(book)
        db.session.commit()
        
        flash('تمت إضافة الكتاب بنجاح', 'success')
        return redirect(url_for('admin.books'))
    
    return render_template('admin/add_book.html', 
                          active_tab='books',
                          form=form,
                          current_year=datetime.now().year)

@admin.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data
        book.isbn = form.isbn.data
        book.publication_year = form.publication_year.data
        book.description = form.description.data
        book.category_id = form.category_id.data
        
        db.session.commit()
        
        flash('تم تحديث الكتاب بنجاح', 'success')
        return redirect(url_for('admin.books'))
    
    return render_template('admin/edit_book.html', 
                          active_tab='books',
                          form=form,
                          book=book,
                          current_year=datetime.now().year)

@admin.route('/books/delete/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # التحقق من عدم وجود حجوزات للكتاب
    if book.reservations:
        flash('لا يمكن حذف الكتاب لأنه مرتبط بحجوزات', 'danger')
        return redirect(url_for('admin.books'))
    
    db.session.delete(book)
    db.session.commit()
    
    flash('تم حذف الكتاب بنجاح', 'success')
    return redirect(url_for('admin.books'))

@admin.route('/categories')
@admin_required
def categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', 
                          active_tab='categories',
                          categories=categories,
                          current_year=datetime.now().year)

@admin.route('/categories/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('تمت إضافة التصنيف بنجاح', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/add_category.html', 
                          active_tab='categories',
                          form=form,
                          current_year=datetime.now().year)

@admin.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        
        db.session.commit()
        
        flash('تم تحديث التصنيف بنجاح', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/edit_category.html', 
                          active_tab='categories',
                          form=form,
                          category=category,
                          current_year=datetime.now().year)

@admin.route('/categories/delete/<int:category_id>', methods=['POST'])
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    # التحقق من عدم وجود كتب مرتبطة بالتصنيف
    if category.books:
        flash('لا يمكن حذف التصنيف لأنه مرتبط بكتب', 'danger')
        return redirect(url_for('admin.categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('تم حذف التصنيف بنجاح', 'success')
    return redirect(url_for('admin.categories'))
