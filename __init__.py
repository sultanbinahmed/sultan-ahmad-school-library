from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# إنشاء قاعدة البيانات
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # تهيئة قاعدة البيانات مع التطبيق
    db.init_app(app)
    
    # إعداد مدير تسجيل الدخول
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة'
    login_manager.login_message_category = 'info'
    
    # استيراد وتسجيل المسارات
    from routes.auth_routes import auth_bp
    from routes.book_routes import book_bp
    from routes.reservation_routes import reservation_bp
    from routes.admin_routes import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(admin_bp)
    
    # تسجيل معالجات الأخطاء
    register_error_handlers(app)
    
    # إنشاء قاعدة البيانات وإضافة البيانات الافتراضية
    with app.app_context():
        from models import User, Category, Book, Resource, BorrowingRules
        from werkzeug.security import generate_password_hash
        
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
    
    return app

def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html', current_year=datetime.now().year), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html', current_year=datetime.now().year), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html', current_year=datetime.now().year), 500

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
