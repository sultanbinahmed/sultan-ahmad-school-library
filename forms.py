from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email
from datetime import datetime, date
import calendar

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(message='يرجى إدخال اسم المستخدم')])
    password = PasswordField('كلمة المرور', validators=[DataRequired(message='يرجى إدخال كلمة المرور')])
    remember = BooleanField('تذكرني')

class RegistrationForm(FlaskForm):
    name = StringField('الاسم الكامل', validators=[DataRequired(message='يرجى إدخال الاسم الكامل'), Length(min=2, max=100, message='يجب أن يكون الاسم بين 2 و 100 حرف')])
    username = StringField('اسم المستخدم', validators=[DataRequired(message='يرجى إدخال اسم المستخدم'), Length(min=3, max=20, message='يجب أن يكون اسم المستخدم بين 3 و 20 حرف')])
    password = PasswordField('كلمة المرور', validators=[DataRequired(message='يرجى إدخال كلمة المرور'), Length(min=6, message='يجب أن تكون كلمة المرور 6 أحرف على الأقل')])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(message='يرجى تأكيد كلمة المرور'), EqualTo('password', message='كلمات المرور غير متطابقة')])
    grade = SelectField('الصف', choices=[
        ('', 'اختر الصف'),
        ('10', 'الصف العاشر'),
        ('11', 'الصف الحادي عشر'),
        ('12', 'الصف الثاني عشر'),
        ('teacher', 'معلم'),
        ('other', 'أخرى')
    ], validators=[DataRequired(message='يرجى اختيار الصف')])

class BookReservationForm(FlaskForm):
    reservation_date = DateField('تاريخ الاستعارة', validators=[DataRequired(message='يرجى اختيار تاريخ الاستعارة')])
    
    def validate_reservation_date(self, field):
        # التحقق من أن التاريخ ليس في الماضي
        if field.data < date.today():
            raise ValidationError('لا يمكن اختيار تاريخ في الماضي')
        
        # التحقق من أن التاريخ ليس يوم الجمعة أو السبت
        day_of_week = field.data.weekday()
        if day_of_week == 4 or day_of_week == 5:  # 4 = الجمعة، 5 = السبت
            raise ValidationError('لا يمكن حجز الكتب في أيام الجمعة والسبت')

class ResourceReservationForm(FlaskForm):
    resource_id = StringField('المورد', validators=[DataRequired(message='يرجى اختيار المورد')])
    date = DateField('التاريخ', validators=[DataRequired(message='يرجى اختيار التاريخ')])
    period = SelectField('الحصة', choices=[(str(i), f'الحصة {i}') for i in range(1, 9)], validators=[DataRequired(message='يرجى اختيار الحصة')])
    
    def validate_date(self, field):
        # التحقق من أن التاريخ ليس في الماضي
        if field.data < date.today():
            raise ValidationError('لا يمكن اختيار تاريخ في الماضي')
        
        # التحقق من أن التاريخ ليس يوم الجمعة أو السبت
        day_of_week = field.data.weekday()
        if day_of_week == 4 or day_of_week == 5:  # 4 = الجمعة، 5 = السبت
            raise ValidationError('لا يمكن حجز المختبرات في أيام الجمعة والسبت')
