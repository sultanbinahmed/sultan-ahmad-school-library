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

@app.route('/books/<int:book_id>')
def book_details(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookReservationForm()
    
    return render_template('book_details.html', 
                          book=book,
                          form=form,
                          current_year=datetime.now().year)

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

@app.route('/categories')
def categories():
    categories = Category.query.all()
    
    return render_template('categories.html', 
                          categories=categories,
                          current_year=datetime.now().year)

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
