from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import User, Book, Category, BookReservation, Resource, ResourceReservation, BorrowingRules
from admin_forms import UserForm, BookForm, CategoryForm, BorrowingRulesForm
from datetime import datetime
from __init__ import db
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# التحقق من صلاحيات المسؤول
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'librarian']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
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

@admin_bp.route('/users')
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', 
                          active_tab='users',
                          users=users,
                          current_year=datetime.now().year)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        user.name = form.name.data
        user.role = form.role.data
        user.grade = form.grade.data if form.grade.data != 'none' else None
        
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        
        db.session.commit()
        
        flash('تم تحديث المستخدم بنجاح', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/edit_user.html', 
                          active_tab='users',
                          form=form,
                          user=user,
                          current_year=datetime.now().year)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # لا يمكن حذف المسؤول الرئيسي
    if user.username == 'admin':
        flash('لا يمكن حذف المسؤول الرئيسي', 'danger')
        return redirect(url_for('admin.users'))
    
    # التحقق من عدم وجود حجوزات للمستخدم
    if user.book_reservations or user.resource_reservations:
        flash('لا يمكن حذف المستخدم لأنه مرتبط بحجوزات', 'danger')
        return redirect(url_for('admin.users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/books')
@admin_required
def books():
    page = request.args.get('page', 1, type=int)
    books = Book.query.order_by(Book.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/books.html', 
                          active_tab='books',
                          books=books,
                          current_year=datetime.now().year)

@admin_bp.route('/books/add', methods=['GET', 'POST'])
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

@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
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

@admin_bp.route('/books/delete/<int:book_id>', methods=['POST'])
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

@admin_bp.route('/categories')
@admin_required
def categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', 
                          active_tab='categories',
                          categories=categories,
                          current_year=datetime.now().year)

@admin_bp.route('/categories/add', methods=['GET', 'POST'])
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

@admin_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
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

@admin_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
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

@admin_bp.route('/reservations')
@admin_required
def reservations():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    # بناء الاستعلام
    reservations_query = BookReservation.query
    
    # تطبيق فلتر الحالة إذا وجد
    if status:
        reservations_query = reservations_query.filter_by(status=status)
    
    # تنفيذ الاستعلام مع الصفحات
    reservations = reservations_query.order_by(BookReservation.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('admin/reservations.html', 
                          active_tab='reservations',
                          reservations=reservations,
                          pagination=reservations,
                          current_year=datetime.now().year)

@admin_bp.route('/reservations/approve/<int:reservation_id>', methods=['POST'])
@admin_required
def approve_reservation(reservation_id):
    reservation = BookReservation.query.get_or_404(reservation_id)
    
    # تحديث حالة الحجز
    reservation.status = 'approved'
    
    db.session.commit()
    
    flash('تم الموافقة على الحجز بنجاح', 'success')
    return redirect(url_for('admin.reservations'))

@admin_bp.route('/reservations/reject/<int:reservation_id>', methods=['POST'])
@admin_required
def reject_reservation(reservation_id):
    reservation = BookReservation.query.get_or_404(reservation_id)
    
    # تحديث حالة الحجز
    reservation.status = 'rejected'
    
    # إعادة الكتاب إلى حالة متاح
    book = Book.query.get(reservation.book_id)
    book.available = True
    
    db.session.commit()
    
    flash('تم رفض الحجز بنجاح', 'success')
    return redirect(url_for('admin.reservations'))

@admin_bp.route('/reservations/return/<int:reservation_id>', methods=['POST'])
@admin_required
def return_book(reservation_id):
    reservation = BookReservation.query.get_or_404(reservation_id)
    
    # تحديث حالة الحجز
    reservation.status = 'returned'
    reservation.return_date = datetime.now()
    
    # إعادة الكتاب إلى حالة متاح
    book = Book.query.get(reservation.book_id)
    book.available = True
    
    db.session.commit()
    
    flash('تم تسجيل إعادة الكتاب بنجاح', 'success')
    return redirect(url_for('admin.reservations'))

@admin_bp.route('/resource_reservations')
@admin_required
def resource_reservations():
    page = request.args.get('page', 1, type=int)
    date_str = request.args.get('date', '')
    
    # بناء الاستعلام
    reservations_query = ResourceReservation.query
    
    # تطبيق فلتر التاريخ إذا وجد
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            reservations_query = reservations_query.filter_by(reservation_date=filter_date)
        except ValueError:
            pass
    
    # تنفيذ الاستعلام مع الصفحات
    reservations = reservations_query.order_by(ResourceReservation.reservation_date.desc()).paginate(page=page, per_page=10)
    
    return render_template('admin/resource_reservations.html', 
                          active_tab='resource_reservations',
                          reservations=reservations,
                          pagination=reservations,
                          current_year=datetime.now().year)

@admin_bp.route('/borrowing_rules', methods=['GET', 'POST'])
@admin_required
def borrowing_rules():
    rules = BorrowingRules.query.first()
    
    if not rules:
        rules = BorrowingRules(max_days=7, max_books=3, rules_text="شروط استعارة الكتب")
        db.session.add(rules)
        db.session.commit()
    
    form = BorrowingRulesForm(obj=rules)
    
    if form.validate_on_submit():
        rules.max_days = form.max_days.data
        rules.max_books = form.max_books.data
        rules.rules_text = form.rules_text.data
        
        db.session.commit()
        
        flash('تم تحديث شروط الاستعارة بنجاح', 'success')
        return redirect(url_for('admin.borrowing_rules'))
    
    return render_template('admin/borrowing_rules.html', 
                          active_tab='borrowing_rules',
                          form=form,
                          rules=rules,
                          current_year=datetime.now().year)
