from flask import Flask, render_template, url_for, flash, redirect, request, session
from flask_bootstrap import Bootstrap
from sqlalchemy import create_engine, MetaData, Table, and_, join
from sqlalchemy.sql import select
from pymongo import MongoClient
import datetime
import stripe

lib = Flask(__name__)

engine = create_engine("mysql+mysqlconnector://root:+jna^4CV@localhost:3306/library")
tablemeta = MetaData(engine)
conn = engine.connect()

###########SQL TABLES##########################################
users = Table("user", tablemeta, autoload = True)
adminUsers = Table("adminuser", tablemeta, autoload = True)
books = Table("book", tablemeta, autoload = True)
borrowings = Table("borrowing", tablemeta, autoload = True)
reservations = Table("reservation", tablemeta, autoload = True)
fines = Table("fine", tablemeta, autoload = True)
payments = Table("payment", tablemeta, autoload = True)
###############################################################

client = MongoClient('localhost', 27017)
db = client.library
collection = db.books
collection.create_index([('title', 'text')])

currentDate = datetime.date.today()
currentTime = datetime.datetime.today()

Bootstrap(lib)

lib.secret_key = "bt2102_11"
lib.config['STRIPE_PUBLIC_KEY'] = 'pk_test_51IYB8bHNTuBLOsCvey41moB9QnhAKpjCxVixnSnHi38BFGNfeWOuqvNUjnqkd7t28yxbyRbXvHAytZoi7TwuoFrY00kwKp157U'
lib.config['STRIPE_SECRET_KEY'] = 'sk_test_51IYB8bHNTuBLOsCv63Ospa0OXe4JxoE25Z1006u3Tjwt66X2Q52hkERGywlX6OGBvDwPhUztxRyadGnDtauYTI0Y00PFLkHwSR'
stripe.api_key = lib.config['STRIPE_SECRET_KEY']


########################################### FUNCTIONS FOR BORROWING ##########################################################################
def is_borrowed(bookid):
    s = select([borrowings]).where(borrowings.c.bookID == bookid)
    result = conn.execute(s).first()
    if result == None:
        return False
    else: 
    	return True

def get_no_of_books(userid):
	s = borrowings.select().where(borrowings.c.userID == userid)
	result = conn.execute(s).fetchall()
	return len(result)

def borrow_book(userid, bookid):
    if get_no_of_books(userid) >= 4:
        flash("USER HAS REACHED MAX BORROWING LIMIT", category = "danger")
        return
    if is_borrowed(bookid):
        flash("BOOK ALREADY BORROWED", category = "danger")
        return    
    try:
	    due = currentDate + datetime.timedelta(weeks = 4) # four weeks after current date
	    ins = borrowings.insert().values(borrowDate = currentDate, dueDate = due, userID = userid, bookID = bookid) 
	    conn.execute(ins)
	    flash("BOOK SUCCESSFULLY BORROWED", category = "success")
    except:
        flash("BORROWING UNSUCCESSFUL", category = "danger")

########################################### FUNCTIONS FOR RESERVING ##########################################################################

def is_reserved(bookid):
    s = reservations.select().where(reservations.c.bookID == bookid)
    result = conn.execute(s).first()
    if result == None:
        return False
    else: return True

def reserve_book(userid, bookid):
    #need to check if book has already been reserved
    if is_reserved(bookid):
        flash("BOOK ALREADY RESERVED", category = "danger")
        return
    if borrowed_by_user(userid, bookid):
        flash("YOU HAVE ALREADY BORROWED THIS BOOK", category = "danger")
        return 
    try:
        ins = reservations.insert().values(reserveDate = currentDate, userID = userid, bookID = bookid) 
        conn.execute(ins)
        flash("BOOK SUCCESSFULLY RESERVED", category = "success")
    except:
        flash("RESERVING UNSUCCESSFUL")

########################################### FUNCTIONS FOR FINES ##########################################################################

def add_to_fine(userid, fineAmount):
    s = fines.select()
    result = conn.execute(s).first()
    totalfine = fineAmount + result[0]
    update = fines.update().where(fines.c.userID == userid).values(fineAmount = totalfine)
    conn.execute(update)

def cancel_all_reservation(userid):
	delete = reservations.delete().where(reservations.c.userID == userid)
	conn.execute(delete)

def check_all():
	s = borrowings.select()
	result = conn.execute(s).fetchall()
	for borrow_date, due_date, userid, bookid in result:
		if currentDate > due_date:
			day_difference = (currentDate - due_date).days
			if user_in_fines(userid):
				add_to_fine(userid, day_difference)
			else:
				create_fine(userid, day_difference)
		else:
			continue

def create_fine(userid, fineAmount):
    # need to remove all reservations associated to userid
    cancel_all_reservation(userid)
    ins = fines.insert().values(userID = userid, fineAmount = fineAmount)
    conn.execute(ins)

def delete_all_fines():
    deleted = fines.delete()
    conn.execute(deleted)

def get_fine_amount(userid):
	s = select([fines.c.fineAmount]).where(fines.c.userID == userid)
	result = conn.execute(s).first()
	if result == None:
		return 0
	else:
		return result[0] 

def has_expired_borrowings(userid):
	s = select([borrowings]).where(and_(borrowings.c.userID == userid, borrowings.c.dueDate < currentDate))
	result = conn.execute(s).fetchall()
	if result:
		return True
	else:
		return False

def make_payment(userid, paymentAmount):
	ins = payments.insert().values(userID = userid, paymentAmount = paymentAmount, paymentDate = currentDate, paymentNo = currentTime.timestamp())
	conn.execute(ins)
    #deleting record from fine
	delete = fines.delete().where(fines.c.userID == userid)
	conn.execute(delete)

########################################### FUNCTIONS FOR MANAGING BOOKS ##########################################################################

def return_book(userid, bookid):
    try:
        delete = borrowings.delete().where(and_(borrowings.c.userID == userid, borrowings.c.bookID == bookid))
        conn.execute(delete)
        flash("BOOK RETURNED", category="success")
    except:
        flash('RESERVATION UNSUCCESSFUL', category = "danger")


def borrowed_by_user(userid, bookid):
    s = select([borrowings]).where(and_(borrowings.c.userID == userid, borrowings.c.bookID == bookid))
    result = conn.execute(s).first()
    if result == None:
        return False
    else: return True


def extend(userid, bookid):
    try:
        s = select([borrowings.c.dueDate]).where(and_(borrowings.c.userID == userid, borrowings.c.bookID == bookid))
        result = conn.execute(s).first()[0]
        if result - currentDate == datetime.timedelta(weeks = 8):
            flash("EXTENSION LIMIT REACHED", category = "danger")
        else:
            newDueDate = result + datetime.timedelta(weeks = 4) # four weeks after current date
            extend = borrowings.update()\
                    .where(and_(borrowings.c.userID == userid, borrowings.c.bookID == bookid))\
                    .values(dueDate = newDueDate)
            conn.execute(extend)
            flash("EXTENSION SUCCESSFUL(4 WEEKS)", category = "success")
    except:
        flash("EXTENSION UNSUCCESSFUL", category = "danger")

def convert_return_to_borrow(userid, bookid):
	if is_borrowed(bookid):
		flash("BOOK STILL BORROWED", category = "danger")
	else:
		cancel_reservation(userid, bookid)
		borrow_book(userid, bookid)
		flash("CONVERSION SUCCESSFUL", category = "success")


def cancel_reservation(userid, bookid):
    try:
        delete = reservations.delete().where(and_(reservations.c.userID == userid, reservations.c.bookID == bookid))
        conn.execute(delete)
        flash("RESERVATION CANCELLED", category = "success")
    except:
        flash("RESERVATION UNSUCCESSFUL", category = "danger")

def display_borrowings(userid):
    j = books.join(borrowings, books.c.bookID == borrowings.c.bookID)
    s = select([books, borrowings.c.borrowDate, borrowings.c.dueDate]).select_from(j).where(borrowings.c.userID == userid)
    result = conn.execute(s)
    lst= result.fetchall()
    return lst

def display_reservations(userid):
    j = books.join(reservations, books.c.bookID == reservations.c.bookID)
    s = select([books, reservations.c.reserveDate]).select_from(j).where(reservations.c.userID == userid)
    result = conn.execute(s)
    lst = result.fetchall()
    return lst

########################################### FUNCTIONS FOR SEARCHING ##########################################################################

def get_dueDate(bookid):
	s = select([borrowings.c.dueDate]).where(borrowings.c.bookID == bookid)
	result = conn.execute(s).first()
	if result != None:
		return result[0]
	else:
		return None

########################################### APP ROUTES ##########################################################################

@lib.route('/')
def index():
	return redirect(url_for("login"))

@lib.route('/home')
def home():
	return render_template('home.html')

@lib.route('/login', methods =['GET', 'POST'])
def login():
	if request.method == 'POST':
		#isAdmin = False
		userid = request.form.get('userid')
		password = request.form.get('password')

		adminselect = adminUsers.select().where(and_(adminUsers.c.userID == userid, adminUsers.c.password == password))
		adminResult = conn.execute(adminselect).first()

		if adminResult == None:
			userselect = users.select().where(and_(users.c.userID == userid, users.c.password == password))
			userResult = conn.execute(userselect).first()
			if userResult == None:
				flash("USER NOT FOUND", category = "error")
				return redirect(url_for("login"))
			else:
				session['userid'] = userid
				session['admin'] = False
				delete_all_fines()
				check_all()
				return redirect(url_for('home'))
		else:
			#isAdmin = True
			session['userid'] = userid
			session['admin'] = True
			delete_all_fines()
			check_all()
			return redirect(url_for('admin_home'))
        
	return render_template("login.html")

@lib.route('/manage_books', methods=["GET", "POST"])
def manage_books():
	if "userid" in session:
		userid = session['userid']
	borrowed = display_borrowings(userid)
	reserved = display_reservations(userid)	

	if request.method == "POST":
		
		if "return_button" in request.form:
			bookID = request.form["return_button"]
			return_book(userid, bookID)
			return redirect(url_for("manage_books"))
			
		if "extend_button" in request.form:
			bookID = request.form["extend_button"]
			extend(userid, bookID)
			return redirect(url_for("manage_books"))

		if 'change_button' in request.form:
			bookID = request.form["change_button"]
			convert_return_to_borrow(userid, bookID)
			return redirect(url_for("manage_books"))

		if 'cancel_button' in request.form:
			bookID = request.form["cancel_button"]
			cancel_reservation(userid, bookID)
			return redirect(url_for("manage_books"))

	return render_template("manage_books.html", borrowed = borrowed, reserved=reserved, currentDate = currentDate)

@lib.route('/logout')
def logout():
	if "userid" in session:
		session.pop('userid', None)
	return redirect(url_for('/'))



@lib.route('/signup', methods=["GET","POST"])
def signup():
	if request.method == 'POST':
		userid = request.form.get('userid')
		password = request.form.get('password')
		try:
			ins = users.insert().values(userID = userid, password = password) 
			conn.execute(ins)
			flash("USER SUCCESSFULLY CREATED", category= 'success')
		except:
			flash("USERNAME TAKEN", category='error') 
	return render_template("signup.html")

@lib.route('/search', methods = ["GET", "POST"])
def search():
	final_result = []
	if "userid" in session:
		userid = session["userid"]
	if request.method == "POST":
		title = ""
		if "search" in request.form:
			title = request.form["search"]
		results = collection.find(
				{"$text":{"$search":title}},
				{"title":1}
				)
		for result in results:
			book = []
			book.append(result["_id"])
			book.append(result["title"])
			book.append(is_borrowed(result["_id"]))
			book.append(get_dueDate(result["_id"]))
			final_result.append(book)

		if "search_borrow" in request.form:
			bookid = request.form["search_borrow"]
			borrow_book(userid, bookid)
			return redirect(url_for("manage_books"))

		if "search_reserve" in request.form:
			bookid = request.form["search_reserve"]
			reserve_book(userid, bookid)
			return redirect(url_for("manage_books"))

	return render_template("search.html", final_result = final_result, currentDate = currentDate)

@lib.route('/advanced-search', methods = ["GET","POST"]) 
def advanced_search(): 
	f = {} 
	final_result = [] 
	if "userid" in session:
		userid = session['userid']
	if request.method == "POST": 
		category = request.form.get("category") 	
		author = request.form.get("author") 
		yop = request.form.get("yop") 
		try:
			if author:
				f['authors'] = {'$regex': author, '$options': 'i'}
			if category:
				f['categories'] = {'$regex': category, '$options': 'i'}
			if yop:
				f['$expr'] = {'$eq' : [{"$year": "$publishedDate"}, int(yop)]} 

			results = collection.find(
						f, 
						{"title" : 1})

			for result in results: 
				book = [] 
				book.append(result["_id"]) 	
				book.append(result["title"]) 
				book.append(is_borrowed(result["_id"])) 
				book.append(get_dueDate(result["_id"]))
				final_result.append(book) 

			if "search_borrow" in request.form:
				bookid = request.form["search_borrow"]
				borrow_book(userid, bookid)
				return redirect(url_for("manage_books"))

			if "search_reserve" in request.form:
				bookid = request.form["search_reserve"]
				reserve_book(userid, bookid)
				return redirect(url_for("manage_books"))
		except:
			flash('INVALID INPUT', category = "danger")
	
	return render_template("advanced-search.html", final_result = final_result)

@lib.route('/fines', methods=["GET", "POST"])
def fine():
	if "userid" in session:
		userid = session['userid']
		data = get_fine_amount(userid)
		has_expired = has_expired_borrowings(userid)
	else:
		data = 0


	session2 = stripe.checkout.Session.create(
		payment_method_types=['card'],
		line_items=[{
			'price': 'price_1IYBATHNTuBLOsCvndhj1WbL',
			'quantity': 1,
		}],
		mode='payment',
		success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
		cancel_url=url_for('fine', _external=True),
	)

	return render_template(
		'fines.html',
		checkout_session_id=session2['id'],
		checkout_public_key=lib.config['STRIPE_PUBLIC_KEY'],
		total = data, #fine
		has_expired_books = has_expired
	)

@lib.route('/fine_pay')
def fine_pay():
	if "userid" in session:
		userid = session['userid']
		data = int(get_fine_amount(userid))
	
	if (session['admin']):
		session2 = stripe.checkout.Session.create(
			payment_method_types=['card'],
			line_items=[{
	            'price': 'price_1IYBATHNTuBLOsCvndhj1WbL',
	            'quantity': data, #fine
	        }],
	        mode='payment',
	        success_url=url_for('admin_thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
	        cancel_url=url_for('fine', _external=True),
    	)
	else: 
		session2 = stripe.checkout.Session.create(
			payment_method_types=['card'],
			line_items=[{
	            'price': 'price_1IYBATHNTuBLOsCvndhj1WbL',
	            'quantity': data, #fine
	        }],
	        mode='payment',
	        success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
	        cancel_url=url_for('fine', _external=True),
	    )
	return {
        'checkout_session_id': session2['id'],
        'checkout_public_key': lib.config['STRIPE_PUBLIC_KEY']
	}

@lib.route('/thanks')
def thanks():
	if "userid" in session:
		userid = session['userid']
		data = get_fine_amount(userid)	
	else:
		data = 0
	make_payment(userid, data)
	return render_template('thanks.html')

@lib.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    print('WEBHOOK CALLED')

    if request.content_length > 1024 * 1024:
        print('REQUEST TOO BIG')
        abort(400)
    payload = request.get_data()
    sig_header = request.environ.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = 'YOUR_ENDPOINT_SECRET'
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print('INVALID PAYLOAD')
        return {}, 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('INVALID SIGNATURE')
        return {}, 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(session)
        line_items = stripe.checkout.Session.list_line_items(session['id'], limit=1)
        print(line_items['data'][0]['description'])

    return {}

########################################### ADMIN APP ROUTES ##########################################################################

@lib.route('/all-book-borrowings') 
def display_all_borrowings(): 
    j = books.join(borrowings, books.c.bookID == borrowings.c.bookID) 
    s = select([books, borrowings.c.borrowDate, borrowings.c.dueDate, borrowings.c.userID]).select_from(j) 
    result = conn.execute(s) 
    list = result.fetchall() 
    return render_template('all-book-borrowings.html', list = list) 
 
@lib.route('/all-book-reservations') 
def display_all_reservations(): 
    j = books.join(reservations, books.c.bookID == reservations.c.bookID) 
    s = select([books, reservations.c.reserveDate, reservations.c.userID]).select_from(j) 
    result = conn.execute(s) 
    list = result.fetchall() 
    return render_template('all-book-reservations.html', list = list) 
 
@lib.route('/all-unpaid-fines') 
def display_all_users_with_fines(): 
    j = users.join(fines, users.c.userID == fines.c.userID) 
    s = select([users.c.userID, fines.c.fineAmount]).select_from(j) 
    result = conn.execute(s) 
    list = result.fetchall() 
    return render_template('all-unpaid-fines.html', list = list)

def user_in_fines(userid):
    s = fines.select().where(fines.c.userID == userid)
    result = conn.execute(s).first()
    if result == None:
        return False
    else: return True

@lib.route('/admin_manage_books', methods=["GET", "POST"])
def admin_manage_books():
	if "userid" in session:
		userid = session['userid']
	borrowed = display_borrowings(userid)
	reserved = display_reservations(userid)	

	if request.method == "POST":
		
		if "return_button" in request.form:
			bookID = request.form["return_button"]
			return_book(userid, bookID)
			return redirect(url_for("admin_manage_books"))
			
		if "extend_button" in request.form:
			bookID = request.form["extend_button"]
			extend(userid, bookID)
			return redirect(url_for("admin_manage_books"))

		if 'change_button' in request.form:
			bookID = request.form["change_button"]
			convert_return_to_borrow(userid, bookID)
			return redirect(url_for("admin_manage_books"))

		if 'cancel_button' in request.form:
			bookID = request.form["cancel_button"]
			cancel_reservation(userid, bookID)
			return redirect(url_for("admin_manage_books"))

	return render_template("admin_manage_books.html", borrowed = borrowed, reserved=reserved, currentDate = currentDate)

@lib.route('/admin_home', methods = ['GET', 'POST'])
def admin_home():
	return render_template("admin_home.html")

@lib.route('/admin_advanced-search', methods = ["GET","POST"]) 
def admin_advanced_search(): 
	f = {} 
	final_result = [] 
	if "userid" in session:
		userid = session['userid']
	if request.method == "POST": 
		category = request.form.get("category") 	
		author = request.form.get("author") 
		yop = request.form.get("yop") 
		try:
			if author:
				f['authors'] = {'$regex': author, '$options': 'i'}
			if category:
				f['categories'] = {'$regex': category, '$options': 'i'}
			if yop:
				f['$expr'] = {'$eq' : [{"$year": "$publishedDate"}, int(yop)]} 

			results = collection.find(
						f, 
						{"title" : 1})

			for result in results: 
				book = [] 
				book.append(result["_id"]) 	
				book.append(result["title"]) 
				book.append(is_borrowed(result["_id"])) 
				book.append(get_dueDate(result["_id"]))
				final_result.append(book) 

			if "search_borrow" in request.form:
				bookid = request.form["search_borrow"]
				borrow_book(userid, bookid)
				return redirect(url_for("admin_manage_books"))

			if "search_reserve" in request.form:
				bookid = request.form["search_reserve"]
				reserve_book(userid, bookid)
				return redirect(url_for("admin_manage_books"))
		except:
			flash("INVALID INPUT", category = "danger")
	
	return render_template("admin_advanced-search.html", final_result = final_result)

@lib.route('/admin_thanks')
def admin_thanks():
	if "userid" in session:
		userid = session['userid']
		data = get_fine_amount(userid)	
	else:
		data = 0
	make_payment(userid, data)
	return render_template('admin_thanks.html')

@lib.route('/admin_fines', methods=["GET", "POST"])
def admin_fines():
	if "userid" in session:
		userid = session['userid']
		data = get_fine_amount(userid)
		has_expired = has_expired_borrowings(userid)
	else:
		data = 0


	session2 = stripe.checkout.Session.create(
		payment_method_types=['card'],
		line_items=[{
			'price': 'price_1IYBATHNTuBLOsCvndhj1WbL',
			'quantity': 1,
		}],
		mode='payment',
		success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
		cancel_url=url_for('admin_fines', _external=True),
	)

	return render_template(
		'admin_fines.html',
		checkout_session_id=session2['id'],
		checkout_public_key=lib.config['STRIPE_PUBLIC_KEY'],
		total = data, #fine
		has_expired_books = has_expired
	)

@lib.route('/admin_search', methods = ["GET", "POST"])
def admin_search():
	final_result = []
	if "userid" in session:
		userid = session["userid"]
	if request.method == "POST":
		title = ""
		if "search" in request.form:
			title = request.form["search"]
		results = collection.find(
				{"$text":{"$search":title}},
				{"title":1}
				)
		for result in results:
			book = []
			book.append(result["_id"])
			book.append(result["title"])
			book.append(is_borrowed(result["_id"]))
			book.append(get_dueDate(result["_id"]))
			final_result.append(book)

		if "admin_search_borrow" in request.form:
			bookid = request.form["admin_search_borrow"]
			borrow_book(userid, bookid)
			return redirect(url_for("admin_manage_books"))

		if "admin_search_reserve" in request.form:
			bookid = request.form["admin_search_reserve"]
			reserve_book(userid, bookid)
			return redirect(url_for("admin_manage_books"))

	return render_template("admin_search.html", final_result = final_result, currentDate = currentDate)

#################################################################################################################################

if __name__ == "__main__":
	lib.run(debug=True)