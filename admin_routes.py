@admin.route('/users')
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', 
                          active_tab='users',
                          users=users,
                          current_year=datetime.now().year)

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
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

@admin.route('/users/delete/<int:user_id>', methods=['POST'])
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

@admin.route('/reservations')
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

@admin.route('/reservations/approve/<int:reservation_id>', methods=['POST'])
@admin_required
def approve_reservation(reservation_id):
    reservation = BookReservation.query.get_or_404(reservation_id)
    
    # تحديث حالة الحجز
    reservation.status = 'approved'
    
    db.session.commit()
    
    flash('تم الموافقة على الحجز بنجاح', 'success')
    return redirect(url_for('admin.reservations'))

@admin.route('/reservations/reject/<int:reservation_id>', methods=['POST'])
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

@admin.route('/reservations/return/<int:reservation_id>', methods=['POST'])
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

@admin.route('/resource_reservations')
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

@admin.route('/borrowing_rules', methods=['GET', 'POST'])
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
