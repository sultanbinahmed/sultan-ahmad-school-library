from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from forms import LoginForm, RegistrationForm
from datetime import datetime
from __init__ import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('book.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('book.index'))
        else:
            flash('فشل تسجيل الدخول. يرجى التحقق من اسم المستخدم وكلمة المرور', 'danger')
    
    return render_template('login.html', form=form, current_year=datetime.now().year)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('book.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('book.index'))
    
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
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form, current_year=datetime.now().year)
