from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import Book, BookReservation, Resource, ResourceReservation, BorrowingRules
from forms import BookReservationForm, ResourceReservationForm
from datetime import datetime, date
from __init__ import db
from functools import wraps

reservation_bp = Blueprint('reservation', __name__)

# التحقق من صلاحيات المعلم
def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'teacher']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@reservation_bp.route('/reserve_book/<int:book_id>', methods=['POST'])
@login_required
def reserve_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # التحقق من توفر الكتاب
    if not book.available:
        flash('هذا الكتاب غير متاح للحجز حالياً', 'danger')
        return redirect(url_for('book.book_details', book_id=book_id))
    
    form = BookReservationForm()
    
    if form.validate_on_submit():
        # التحقق من عدد الكتب المستعارة للمستخدم
        borrowing_rules = BorrowingRules.query.first()
        active_reservations = BookReservation.query.filter_by(user_id=current_user.id, status='approved').count()
        
        if active_reservations >= borrowing_rules.max_books:
            flash(f'لا يمكنك استعارة أكثر من {borrowing_rules.max_books} كتب في نفس الوقت', 'danger')
            return redirect(url_for('book.book_details', book_id=book_id))
        
        # التحقق من أن التاريخ ليس في الماضي وليس يوم الجمعة أو السبت
        reservation_date = form.reservation_date.data
        day_of_week = reservation_date.weekday()
        
        if day_of_week == 4 or day_of_week == 5:  # 4 = الجمعة، 5 = السبت
            flash('لا يمكن حجز الكتب في أيام الجمعة والسبت', 'danger')
            return redirect(url_for('book.book_details', book_id=book_id))
        
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
        return redirect(url_for('reservation.my_reservations'))
    
    # في حالة وجود أخطاء في النموذج
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{error}', 'danger')
    
    return redirect(url_for('book.book_details', book_id=book_id))

@reservation_bp.route('/my_reservations')
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

@reservation_bp.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
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
    return redirect(url_for('reservation.my_reservations'))

@reservation_bp.route('/resources')
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
                          today=today,
                          current_year=datetime.now().year)

@reservation_bp.route('/reserve_resource', methods=['POST'])
@login_required
@teacher_required
def reserve_resource():
    resource_id = request.form.get('resource_id')
    date_str = request.form.get('date')
    period = request.form.get('period')
    
    if not resource_id or not date_str or not period:
        flash('بيانات غير كاملة', 'danger')
        return redirect(url_for('reservation.resources'))
    
    # تحويل التاريخ إلى كائن date
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('تاريخ غير صالح', 'danger')
        return redirect(url_for('reservation.resources'))
    
    # التحقق من أن التاريخ ليس في الماضي
    if reservation_date < date.today():
        flash('لا يمكن الحجز في تاريخ سابق', 'danger')
        return redirect(url_for('reservation.resources'))
    
    # التحقق من أن التاريخ ليس يوم الجمعة أو السبت
    day_of_week = reservation_date.weekday()
    if day_of_week == 4 or day_of_week == 5:  # 4 = الجمعة، 5 = السبت
        flash('لا يمكن حجز المختبرات في أيام الجمعة والسبت', 'danger')
        return redirect(url_for('reservation.resources'))
    
    # التحقق من عدم وجود حجز سابق لنفس المورد في نفس التاريخ والحصة
    existing_reservation = ResourceReservation.query.filter_by(
        resource_id=resource_id,
        reservation_date=reservation_date,
        period=period
    ).first()
    
    if existing_reservation:
        flash('هذا المورد محجوز بالفعل في هذا التاريخ والحصة', 'danger')
        return redirect(url_for('reservation.resources'))
    
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
    return redirect(url_for('reservation.resources'))

@reservation_bp.route('/cancel_resource_reservation/<int:reservation_id>', methods=['POST'])
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
    return redirect(url_for('reservation.resources'))
