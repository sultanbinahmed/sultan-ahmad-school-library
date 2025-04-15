from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email

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

class BookForm(FlaskForm):
    title = StringField('عنوان الكتاب', validators=[DataRequired(message='يرجى إدخال عنوان الكتاب'), Length(min=2, max=200, message='يجب أن يكون العنوان بين 2 و 200 حرف')])
    author = StringField('المؤلف', validators=[Length(max=100, message='يجب أن لا يتجاوز اسم المؤلف 100 حرف')])
    isbn = StringField('الرقم المعياري الدولي', validators=[Length(max=20, message='يجب أن لا يتجاوز الرقم المعياري 20 حرف')])
    publication_year = IntegerField('سنة النشر', validators=[Optional(), NumberRange(min=1800, max=2100, message='يرجى إدخال سنة نشر صحيحة')])
    description = TextAreaField('وصف الكتاب', validators=[Optional()])
    category_id = SelectField('التصنيف', coerce=int, validators=[DataRequired(message='يرجى اختيار تصنيف')])
    available = BooleanField('متاح للاستعارة', default=True)

class CategoryForm(FlaskForm):
    name = StringField('اسم التصنيف', validators=[DataRequired(message='يرجى إدخال اسم التصنيف'), Length(min=2, max=100, message='يجب أن يكون اسم التصنيف بين 2 و 100 حرف')])
    description = TextAreaField('وصف التصنيف', validators=[Optional()])

class BorrowingRulesForm(FlaskForm):
    max_days = IntegerField('الحد الأقصى لأيام الاستعارة', validators=[DataRequired(message='يرجى إدخال الحد الأقصى لأيام الاستعارة'), NumberRange(min=1, max=30, message='يجب أن يكون الحد الأقصى بين 1 و 30 يوم')])
    max_books = IntegerField('الحد الأقصى لعدد الكتب المستعارة للشخص الواحد', validators=[DataRequired(message='يرجى إدخال الحد الأقصى لعدد الكتب'), NumberRange(min=1, max=10, message='يجب أن يكون الحد الأقصى بين 1 و 10 كتب')])
    rules_text = TextAreaField('نص شروط الاستعارة', validators=[DataRequired(message='يرجى إدخال نص شروط الاستعارة')])
