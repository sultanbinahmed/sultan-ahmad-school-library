from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import os

# إنشاء تطبيق Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إنشاء قاعدة البيانات
db = SQLAlchemy(app)

# إعداد مدير تسجيل الدخول
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'info'

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# التحقق من صلاحيات المسؤول
def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'librarian']:
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# التحقق من صلاحيات المعلم
def teacher_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'teacher']:
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# إنشاء قاعدة البيانات وإضافة مستخدم المسؤول
def create_tables():
    with app.app_context():
        db.create_all()
        
        # التحقق من وجود مستخدم المسؤول
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin421'),
                name='مسؤول النظام',
                role='admin'
            )
            db.session.add(admin)
            
            # إضافة بعض التصنيفات الافتراضية
            categories = [
                Category(name='علوم', description='كتب في مجال العلوم المختلفة'),
                Category(name='رياضيات', description='كتب في مجال الرياضيات'),
                Category(name='لغة عربية', description='كتب في مجال اللغة العربية وآدابها'),
                Category(name='لغة إنجليزية', description='كتب في مجال اللغة الإنجليزية'),
                Category(name='تاريخ', description='كتب في مجال التاريخ'),
                Category(name='جغرافيا', description='كتب في مجال الجغرافيا'),
                Category(name='تربية إسلامية', description='كتب في مجال التربية الإسلامية'),
                Category(name='تقنية معلومات', description='كتب في مجال تقنية المعلومات والحاسوب')
            ]
            
            for category in categories:
                db.session.add(category)
            
            # إضافة بعض الموارد الافتراضية
            resources = [
                Resource(name='مختبر العلوم', type='lab', description='مختبر للتجارب العلمية', capacity=30),
                Resource(name='مختبر الحاسوب', type='lab', description='مختبر لدروس الحاسوب', capacity=25),
                Resource(name='غرفة المصادر 1', type='resource_room', description='غرفة مصادر للأنشطة التعليمية', capacity=20),
                Resource(name='غرفة المصادر 2', type='resource_room', description='غرفة مصادر للأنشطة التعليمية', capacity=15)
            ]
            
            for resource in resources:
                db.session.add(resource)
            
            # إضافة قواعد الاستعارة الافتراضية
            borrowing_rules = BorrowingRules(
                max_days=7,
                max_books=3,
                rules_text="""
                1. يجب المحافظة على الكتب وإعادتها بحالة جيدة.
                2. يمنع الكتابة على الكتب أو تمزيقها.
                3. في حالة فقدان الكتاب أو تلفه، يجب تعويضه أو دفع قيمته.
                4. يجب إعادة الكتب في الموعد المحدد.
                5. يمكن تمديد فترة الاستعارة مرة واحدة فقط إذا لم يكن هناك حجز على الكتاب.
                """
            )
            db.session.add(borrowing_rules)
            
            db.session.commit()

# استدعاء دالة إنشاء قاعدة البيانات
create_tables()

# نماذج الاستمارات
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField, IntegerField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, Email, Optional, NumberRange

# نموذج تسجيل الدخول
class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(message='يرجى إدخال اسم المستخدم')])
    password = PasswordField('كلمة المرور', validators=[DataRequired(message='يرجى إدخال كلمة المرور')])
    remember = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

# نموذج التسجيل
class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(message='يرجى إدخال اسم المستخدم'), Length(min=4, max=25, message='يجب أن يكون اسم المستخدم بين 4 و 25 حرف')])
    name = StringField('الاسم الكامل', validators=[DataRequired(message='يرجى إدخال الاسم الكامل'), Length(min=2, max=100, message='يجب أن يكون الاسم بين 2 و 100 حرف')])
    password = PasswordField('كلمة المرور', validators=[DataRequired(message='يرجى إدخال كلمة المرور'), Length(min=6, message='يجب أن تكون كلمة المرور 6 أحرف على الأقل')])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(message='يرجى تأكيد كلمة المرور'), EqualTo('password', message='كلمة المرور غير متطابقة')])
    grade = SelectField('الصف/الدور', choices=[
        ('10', 'الصف العاشر'),
        ('11', 'الصف الحادي عشر'),
        ('12', 'الصف الثاني عشر'),
        ('teacher', 'معلم'),
        ('other', 'أخرى')
    ], validators=[DataRequired(message='يرجى اختيار الصف أو الدور')])
    submit = SubmitField('تسجيل')

# نموذج حجز الكتب
class BookReservationForm(FlaskForm):
    reservation_date = DateField('تاريخ الحجز', validators=[DataRequired(message='يرجى اختيار تاريخ الحجز')])
    submit = SubmitField('حجز الكتاب')

# نموذج حجز المختبرات وغرف المصادر
class ResourceReservationForm(FlaskForm):
    resource_id = SelectField('المورد', coerce=int, validators=[DataRequired(message='يرجى اختيار المورد')])
    reservation_date = DateField('تاريخ الحجز', validators=[DataRequired(message='يرجى اختيار تاريخ الحجز')])
    period = SelectField('الحصة', choices=[
        (1, 'الحصة الأولى'),
        (2, 'الحصة الثانية'),
        (3, 'الحصة الثالثة'),
        (4, 'الحصة الرابعة'),
        (5, 'الحصة الخامسة'),
        (6, 'الحصة السادسة'),
        (7, 'الحصة السابعة'),
        (8, 'الحصة الثامنة')
    ], coerce=int, validators=[DataRequired(message='يرجى اختيار الحصة')])
    submit = SubmitField('حجز المورد')

# نموذج إضافة/تعديل الكتب
class BookForm(FlaskForm):
    title = StringField('عنوان الكتاب', validators=[DataRequired(message='يرجى إدخال عنوان الكتاب'), Length(min=2, max=200, message='يجب أن يكون العنوان بين 2 و 200 حرف')])
    author = StringField('المؤلف', validators=[Length(max=100, message='يجب أن لا يتجاوز اسم المؤلف 100 حرف')])
    isbn = StringField('الرقم المعياري الدولي', validators=[Length(max=20, message='يجب أن لا يتجاوز الرقم المعياري 20 حرف')])
    publication_year = IntegerField('سنة النشر', validators=[Optional(), NumberRange(min=1800, max=2100, message='يرجى إدخال سنة نشر صحيحة')])
    description = TextAreaField('وصف الكتاب', validators=[Optional()])
    category_id = SelectField('التصنيف', coerce=int, validators=[DataRequired(message='يرجى اختيار تصنيف')])
    available = BooleanField('متاح للاستعارة', default=True)
    submit = SubmitField('حفظ')

# نموذج إضافة/تعديل التصنيفات
class CategoryForm(FlaskForm):
    name = StringField('اسم التصنيف', validators=[DataRequired(message='يرجى إدخال اسم التصنيف'), Length(min=2, max=100, message='يجب أن يكون اسم التصنيف بين 2 و 100 حرف')])
    description = TextAreaField('وصف التصنيف', validators=[Optional()])
    submit = SubmitField('حفظ')

# نموذج تعديل المستخدمين
class UserForm(FlaskForm):
    name = StringField('الاسم الكامل', validators=[DataRequired(message='يرجى إدخال الاسم الكامل'), Length(min=2, max=100, message='يجب أن يكون الاسم بين 2 و 100 حرف')])
    role = SelectField('الدور', choices=[
        ('student', 'طالب'),
        ('teacher', 'معلم'),
        ('librarian', 'أمين مكتبة'),
        ('admin', 'مسؤول')
    ], validators=[DataRequired(message='يرجى اختيار الدور')])
    grade = SelectField('الصف', choices=[
        ('none', 'غير محدد'),
        ('10', 'الصف العاشر'),
        ('11', 'الصف الحادي عشر'),
        ('12', 'الصف الثاني عشر')
    ])
    password = PasswordField('كلمة المرور الجديدة (اترك فارغاً للإبقاء على كلمة المرور الحالية)')
    submit = SubmitField('حفظ')

# نموذج شروط الاستعارة
class BorrowingRulesForm(FlaskForm):
    max_days = IntegerField('الحد الأقصى لأيام الاستعارة', validators=[DataRequired(message='يرجى إدخال الحد الأقصى لأيام الاستعارة'), NumberRange(min=1, max=30, message='يجب أن يكون الحد الأقصى بين 1 و 30 يوم')])
    max_books = IntegerField('الحد الأقصى لعدد الكتب المستعارة للشخص الواحد', validators=[DataRequired(message='يرجى إدخال الحد الأقصى لعدد الكتب'), NumberRange(min=1, max=10, message='يجب أن يكون الحد الأقصى بين 1 و 10 كتب')])
    rules_text = TextAreaField('نص شروط الاستعارة', validators=[DataRequired(message='يرجى إدخال نص شروط الاستعارة')])
    submit = SubmitField('حفظ')

# الصفحة الرئيسية
@app.route('/')
def index():
    latest_books = Book.query.order_by(Book.created_at.desc()).limit(6).all()
    categories = Category.query.limit(6).all()
    borrowing_rules = BorrowingRules.query.first()
    
    if not borrowing_rules:
        borrowing_rules = BorrowingRules(max_days=7, max_books=3, rules_text="شروط استعارة الكتب")
        db.session.add(borrowing_rules)
        db.session.commit()
    
    return render_template('index.html', latest_books=latest_books, categories=categories, borrowing_rules=borrowing_rules, current_year=datetime.now().year)

# تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('فشل تسجيل الدخول. يرجى التحقق من اسم المستخدم وكلمة المرور', 'danger')
    
    return render_template('login.html', form=form, current_year=datetime.now().year)

# تسجيل خروج
@app.route('/logout')
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

# تسجيل مستخدم جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # التحقق من عدم وجود اسم المستخدم مسبقاً
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('اسم المستخدم موجود بالفعل. يرجى اختيار اسم مستخدم آخر', 'danger')
            return render_template('register.html', form=form, current_year=datetime.now().year)
        
        # تحديد دور المستخدم
        role = 'student'
        if form.grade.data == 'teacher':
            role = 'teacher'
        
        # إنشاء المستخدم الجديد
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            password=hashed_password,
            name=form.name.data,
            role=role,
            grade=form.grade.data if form.grade.data not in ['teacher', 'other'] else None
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('تم إنشاء حسابك بنجاح! يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form, current_year=datetime.now().year)

# عرض الكتب
@app.route('/books')
def books():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '')
    category_id = request.args.get('category', '')
    sort = request.args.get('sort', 'title')
    
    # بناء الاستعلام
    books_query = Book.query
    
    # تطبيق البحث إذا وجد
    if query:
        books_query = books_query.filter(Book.title.contains(query) | Book.author.contains(query))
    
    # تطبيق فلتر التصنيف إذا وجد
    if category_id and category_id.isdigit():
        books_query = books_query.filter_by(category_id=int(category_id))
    
    # تطبيق الترتيب
    if sort == 'title':
        books_query = books_query.order_by(Book.title)
    elif sort == 'author':
        books_query = books_query.order_by(Book.author)
    elif sort == 'newest':
        books_query = books_query.order_by(Book.created_at.desc())
    
    # تنفيذ الاستعلام مع الصفحات
    books = books_query.paginate(page=page, per_page=12)
    categories = Category.query.all()
    
    return render_template('books.html', 
                          books=books,
                          categories=categories,
                          pagination=books,
                          current_year=datetime.now().year)

# تفاصيل الكتاب
@app.route('/books/<int:book_id>')
def book_details(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookReservationForm()
    
    # تعيين التاريخ الافتراضي للحجز (اليوم التالي)
    tomorrow = datetime.now().date() + timedelta(days=1)
    form.reservation_date.data = tomorrow
    
    return render_template('book_details.html', 
                          book=book,
                          form=form,
                          current_year=datetime.now().year)

# عرض كتب التصنيف
@app.route('/categories/<int:category_id>')
def category_books(category_id):
    category = Category.query.get_or_404(category_id)
    page = request.args.get('page', 1, type=int)
    
    books = Book.query.filter_by(category_id=category_id).paginate(page=page, per_page=12)
    
    return render_template('category_books.html', 
                          category=category,
                          books=books,
                          pagination=books,
                          current_year=datetime.now().year)

# عرض التصنيفات
@app.route('/categories')
def categories():
    categories = Category.query.all()
    
    return render_template('categories.html', 
                          categories=categories,
                          current_year=datetime.now().year)

# عرض شروط الاستعارة
@app.route('/borrowing_rules')
def borrowing_rules():
    rules = BorrowingRules.query.first()
    
    if not rules:
        rules = BorrowingRules(max_days=7, max_books=3, rules_text="شروط استعارة الكتب")
        db.session.add(rules)
        db.session.commit()
    
    return render_template('borrowing_rules.html', 
                          rules=rules,
                          current_year=datetime.now().year)

# حجز كتاب
@app.route('/reserve_book/<int:book_id>', methods=['POST'])
@login_required
def reserve_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # التحقق من توفر الكتاب
    if not book.available:
        flash('هذا الكتاب غير متاح للحجز حالياً', 'danger')
        return redirect(url_for('book_details', book_id=book_id))
    
    form = BookReservationForm()
    
    if form.validate_on_submit():
        # التحقق من عدد الكتب المستعارة للمستخدم
        borrowing_rules = BorrowingRules.query.first()
        active_reservations = BookReservation.query.filter_by(user_id=current_user.id, status='approved').count()
        
        if active_reservations >= borrowing_rules.max_books:
            flash(f'لا يمكنك استعارة أكثر من {borrowing_rules.max_books} كتب في نفس الوقت', 'danger')
            return redirect(url_for('book_details', book_id=book_id))
        
        # التحقق من أن التاريخ ليس في الماضي وليس يوم الجمعة أو السبت
        reservation_date = form.reservation_date.data
        day_of_week = reservation_date.weekday()
        
        if day_of_week == 4 or day_of_week == 5:  # 4 = الجمعة، 5 = السبت
            flash('لا يمكن حجز الكتب في أيام الجمعة والسبت', 'danger')
            return redirect(url_for('book_details', book_id=book_id))
        
        # إنشاء الحجز
        reservation = BookReservation(
            user_id=current_user.id,
            book_id=book_id,
            reservation_date=reservation_date,
            status='pending'
        )
        
        # تحديث حالة الكتاب
        book.available = False
        
        db.session.add(reservation)
        db.session.commit()
        
        flash('تم حجز الكتاب بنجاح. سيتم مراجعة طلبك من قبل المسؤول', 'success')
        return redirect(url_for('my_reservations'))
    
    # في حالة وجود أخطاء في النموذج
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{error}', 'danger')
    
    return redirect(url_for('book_details', book_id=book_id))

# حجوزاتي
@app.route('/my_reservations')
@login_required
def my_reservations():
    book_reservations = BookReservation.query.filter_by(user_id=current_user.id).order_by(BookReservation.created_at.desc()).all()
    
    # للمعلمين فقط: عرض حجوزات المختبرات وغرف المصادر
    resource_reservations = []
    if current_user.role in ['teacher', 'admin']:
        resource_reservations = ResourceReservation.query.filter_by(user_id=current_user.id).order_by(ResourceReservation.reservation_date.desc()).all()
    
    return render_template('my_reservations.html', 
                          book_reservations=book_reservations,
                          resource_reservations=resource_reservations,
                          current_year=datetime.now().year)

# إلغاء حجز كتاب
@app.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    reservation = BookReservation.query.get_or_404(reservation_id)
    
    # التحقق من أن الحجز للمستخدم الحالي
    if reservation.user_id != current_user.id and current_user.role not in ['admin', 'librarian']:
        abort(403)
    
    # إعادة الكتاب إلى حالة متاح
    book = Book.query.get(reservation.book_id)
    book.available = True
    
    # حذف الحجز
    db.session.delete(reservation)
    db.session.commit()
    
    flash('تم إلغاء الحجز بنجاح', 'success')
    return redirect(url_for('my_reservations'))

# عرض المختبرات وغرف المصادر
@app.route('/resources')
@login_required
@teacher_required
def resources():
    resources = Resource.query.all()
    today = date.today().strftime('%Y-%m-%d')
    selected_date = request.args.get('date', today)
    
    # تحويل التاريخ إلى كائن date
    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        selected_date_obj = date.today()
    
    # الحصول على جميع الحجوزات للتاريخ المحدد
    day_reservations = ResourceReservation.query.filter_by(reservation_date=selected_date_obj).all()
    
    # تنظيم الحجوزات حسب المورد والحصة
    reservations = {}
    for reservation in day_reservations:
        if reservation.resource_id not in reservations:
            reservations[reservation.resource_id] = []
        reservations[reservation.resource_id].append(reservation.period)
    
    # الحصول على حجوزات المستخدم الحالي
    my_reservations = ResourceReservation.query.filter_by(user_id=current_user.id).order_by(ResourceReservation.reservation_date).all()
    
    return render_template('resources.html', 
                          resources=resources,
                          reservations=reservations,
                          my_reservations=my_reservations,
                          selected_date=selected_date,
                          today=today,
                          current_year=datetime.now().year)

# حجز مختبر أو غرفة مصادر
@app.route('/reserve_resource', methods=['POST'])
@login_required
@teacher_required
def reserve_resource():
    resource_id = request.form.get('resource_id')
    date_str = request.form.get('date')
    period = request.form.get('period')
    
    if not resource_id or not date_str or not period:
        flash('بيانات غير كاملة', 'danger')
        return redirect(url_for('resources'))
    
    # تحويل التاريخ إلى كائن date
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('تاريخ غير صالح', 'danger')
        return redirect(url_for('resources'))
    
    # التحقق من أن التاريخ ليس في الماضي
    if reservation_date < date.today():
        flash('لا يمكن الحجز في تاريخ سابق', 'danger')
        return redirect(url_for('resources'))
    
    # التحقق من أن التاريخ ليس يوم الجمعة أو السبت
    day_of_week = reservation_date.weekday()
    if day_of_week == 4 or day_of_week == 5:  # 4 = الجمعة، 5 = السبت
        flash('لا يمكن حجز المختبرات في أيام الجمعة والسبت', 'danger')
        return redirect(url_for('resources'))
    
    # التحقق من عدم وجود حجز سابق لنفس المورد في نفس التاريخ والحصة
    existing_reservation = ResourceReservation.query.filter_by(
        resource_id=resource_id,
        reservation_date=reservation_date,
        period=period
    ).first()
    
    if existing_reservation:
        flash('هذا المورد محجوز بالفعل في هذا التاريخ والحصة', 'danger')
        return redirect(url_for('resources'))
    
    # إنشاء الحجز
    reservation = ResourceReservation(
        user_id=current_user.id,
        resource_id=resource_id,
        reservation_date=reservation_date,
        period=int(period)
    )
    
    db.session.add(reservation)
    db.session.commit()
    
    flash('تم حجز المورد بنجاح', 'success')
    return redirect(url_for('resources'))

# إلغاء حجز مختبر أو غرفة مصادر
@app.route('/cancel_resource_reservation/<int:reservation_id>', methods=['POST'])
@login_required
@teacher_required
def cancel_resource_reservation(reservation_id):
    reservation = ResourceReservation.query.get_or_404(reservation_id)
    
    # التحقق من أن الحجز للمستخدم الحالي
    if reservation.user_id != current_user.id and current_user.role != 'admin':
        abort(403)
    
    # حذف الحجز
    db.session.delete(reservation)
    db.session.commit()
    
    flash('تم إلغاء الحجز بنجاح', 'success')
    return redirect(url_for('resources'))

# لوحة تحكم المسؤول
@app.route('/admin')
@admin_required
def admin_dashboard():
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

# إدارة المستخدمين
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', 
                          active_tab='users',
                          users=users,
                          current_year=datetime.now().year)

# تعديل مستخدم
@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('admin_users'))
    
    return render_template('admin/edit_user.html', 
                          active_tab='users',
                          form=form,
                          user=user,
                          current_year=datetime.now().year)

# حذف مستخدم
@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # لا يمكن حذف المسؤول الرئيسي
    if user.username == 'admin':
        flash('لا يمكن حذف المسؤول الرئيسي', 'danger')
        return redirect(url_for('admin_users'))
    
    # التحقق من عدم وجود حجوزات للمستخدم
    if user.book_reservations or user.resource_reservations:
        flash('لا يمكن حذف المستخدم لأنه مرتبط بحجوزات', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('admin_users'))

# إدارة الكتب
@app.route('/admin/books')
@admin_required
def admin_books():
    page = request.args.get('page', 1, type=int)
    books = Book.query.order_by(Book.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/books.html', 
                          active_tab='books',
                          books=books,
                          current_year=datetime.now().year)

# إضافة كتاب
@app.route('/admin/books/add', methods=['GET', 'POST'])
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
            available=form.available.data,
            added_by=current_user.id
        )
        
        db.session.add(book)
        db.session.commit()
        
        flash('تمت إضافة الكتاب بنجاح', 'success')
        return redirect(url_for('admin_books'))
    
    return render_template('admin/add_book.html', 
                          active_tab='books',
                          form=form,
                          current_year=datetime.now().year)

# تعديل كتاب
@app.route('/admin/books/edit/<int:book_id>', methods=['GET', 'POST'])
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
        book.available = form.available.data
        
        db.session.commit()
        
        flash('تم تحديث الكتاب بنجاح', 'success')
        return redirect(url_for('admin_books'))
    
    return render_template('admin/edit_book.html', 
                          active_tab='books',
                          form=form,
                          book=book,
                          current_year=datetime.now().year)

# حذف كتاب
@app.route('/admin/books/delete/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # التحقق من عدم وجود حجوزات للكتاب
    if book.reservations:
        flash('لا يمكن حذف الكتاب لأنه مرتبط بحجوزات', 'danger')
        return redirect(url_for('admin_books'))
    
    db.session.delete(book)
    db.session.commit()
    
    flash('تم حذف الكتاب بنجاح', 'success')
    return redirect(url_for('admin_books'))

# إدارة التصنيفات
@app.route('/admin/categories')
@admin_required
def admin_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', 
                          active_tab='categories',
                          categories=categories,
                          current_year=datetime.now().year)

# إضافة تصنيف
@app.route('/admin/categories/add', methods=['GET', 'POST'])
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
        return redirect(url_for('admin_categories'))
    
    return render_template('admin/add_category.html', 
                          active_tab='categories',
                          form=form,
                          current_year=datetime.now().year)

# تعديل تصنيف
@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        
        db.session.commit()
        
        flash('تم تحديث التصنيف بنجاح', 'success')
        return redirect(url_for('admin_categories'))
    
    return render_template('admin/edit_category.html', 
                          active_tab='categories',
                          form=form,
                          category=category,
                          current_year=datetime.now().year)

# حذف تصنيف
@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    # التحقق من عدم وجود كتب مرتبطة بالتصنيف
    if category.books:
        flash('لا يمكن حذف التصنيف لأنه مرتبط بكتب', 'danger')
        return redirect(url_for('admin_categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('تم حذف التصنيف بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# إدارة حجوزات الكتب
@app.route('/admin/reservations')
@admin_required
def admin_reservations():
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

# الموافقة على حجز كتاب
@app.route('/admin/reservations/approve/<int:reservation_id>', methods=['POST'])
@admin_required
def approve_reservation(reservation_id):
    reservation = BookReservation.query.get_or_404(reservation_id)
    
    # تحديث حالة الحجز
    reservation.status = 'approved'
    
    db.session.commit()
    
    flash('تم الموافقة على الحجز بنجاح', 'success')
    return redirect(url_for('admin_reservations'))

# رفض حجز كتاب
@app.route('/admin/reservations/reject/<int:reservation_id>', methods=['POST'])
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
    return redirect(url_for('admin_reservations'))

# تسجيل إعادة كتاب
@app.route('/admin/reservations/return/<int:reservation_id>', methods=['POST'])
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
    return redirect(url_for('admin_reservations'))

# إدارة حجوزات المختبرات وغرف المصادر
@app.route('/admin/resource_reservations')
@admin_required
def admin_resource_reservations():
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

# إدارة شروط الاستعارة
@app.route('/admin/borrowing_rules', methods=['GET', 'POST'])
@admin_required
def admin_borrowing_rules():
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
        return redirect(url_for('admin_borrowing_rules'))
    
    return render_template('admin/borrowing_rules.html', 
                          active_tab='borrowing_rules',
                          form=form,
                          rules=rules,
                          current_year=datetime.now().year)

# صفحة الخطأ 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html', current_year=datetime.now().year), 404

# صفحة الخطأ 403
@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html', current_year=datetime.now().year), 403

# صفحة الخطأ 500
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html', current_year=datetime.now().year), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
