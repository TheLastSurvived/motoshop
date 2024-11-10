from flask import Flask, render_template, request, flash, redirect, session, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
from hashlib import md5
from  sqlalchemy.sql.expression import func
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqlamodel import ModelView
from flask_admin import Admin


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['UPLOAD_FOLDER'] = 'static/img/upload'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
db = SQLAlchemy(app)
ckeditor = CKEditor(app)


class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), unique=True)
    root = db.Column(db.Integer, default=0)
    
    orders = db.relationship('Orders', backref='user', lazy=True)
   
    def __repr__(self):
        return 'User %r' % self.id 
    
    
class Articles(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(100))
    text = db.Column(db.Text)
    image_name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    price = db.Column(db.Integer)
    
    orders = db.relationship('Orders', backref='article', lazy=True)

    def __repr__(self):
        return 'Articles %r' % self.id 
    
    
class Orders(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id'))
    id_article = db.Column(db.Integer, db.ForeignKey('articles.id'))
    address = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return 'Orders %r' % self.id 
    
    
class AdminIndex(AdminIndexView):
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if 'name' in session:
            user = Users.query.filter_by(email=session['name']).first()
            if user.root!=1:
                abort(403)
            else:
                return self.render('admin/dashboard_index.html')
        else:
            abort(401)


admin = Admin(app, name='MotoShop',index_view=AdminIndex())

class OrdersView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id_user','id_article', 'address', 'date']

admin.add_view(ModelView(Users, db.session))
admin.add_view(ModelView(Articles, db.session))
admin.add_view(OrdersView(Orders, db.session))

    
@app.route('/', methods=['GET', 'POST'])
def index():
    random_articles = Articles.query.order_by(func.random()).limit(3).all()
    return render_template("index.html",random_articles=random_articles)


@app.route('/catalog', methods=['GET', 'POST'])
def catalog(): 
    articles = Articles.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        price = request.form.get('price')
        image = request.files['image']
        filename = secure_filename(image.filename)
        pic_name = str(uuid.uuid4()) + "_" + filename
        image.save("static/img/upload/" + pic_name)
        text = request.form.get('ckeditor')
        article = Articles(title=title,category=category,price=price,image_name=pic_name,text=text)
        db.session.add(article)
        db.session.commit()
        flash("Запись добавлена!", category="ok")
        return redirect(url_for("catalog"))
    
    if request.method == 'GET':
        category = request.args.get('category')
        if category:
            category= category.capitalize()
            category = "%{}%".format(category)
            articles = Articles.query.filter(Articles.category.like(category)).all()
            return render_template("catalog.html",articles=articles)
        else:
             return render_template("catalog.html",articles=articles)
    
    return render_template("catalog.html",articles=articles)


@app.route('/article/<int:id>', methods=['GET', 'POST'])
def article(id):
    article = Articles.query.get(id)
    if request.method == 'POST':
        article.title = request.form.get('title')
        article.category = request.form.get('category')
        article.price = request.form.get('price')
        article.text = request.form.get('ckeditor')
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            pic_name = str(uuid.uuid4()) + "_" + filename
            image.save("static/img/upload/" + pic_name)
            article.image_name = pic_name
        db.session.commit()
        flash("Запись обновлена!", category="ok")
        return redirect(url_for("article", id=article.id))
    return render_template("article.html",article=article)


@app.route('/delete-article/<int:id>')
def delete_article(id):
    obj = Articles.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    flash("Запись удалена!", category="bad")
    return redirect('/catalog')


@app.route('/delete-order/<int:id>')
def delete_order(id):
    obj = Orders.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    flash("Заказ отменен!", category="bad")
    return redirect('/profile')


@app.route('/add-order/<int:id_user>/<int:id_article>', methods=[ 'POST'])
def add_order(id_user,id_article):
    if request.method == 'POST':
        address = request.form.get('address')
        order = Orders(address=address,id_user=id_user,id_article=id_article)
        db.session.add(order)
        db.session.commit()
    flash("Заказ оформлен!", category="ok")
    return redirect(url_for("article", id=id_article))


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/profile')
def profile():
    if not 'name' in session:
        abort(401)
    total_user = Users.query.filter_by(email=session['name']).first()
    orders = Orders.query.filter_by(id_user=total_user.id).join(Articles).all()
    return render_template("profile.html",orders=orders)


@app.route('/login', methods=['GET', 'POST'])
def login():
    session.pop('name', None)
    if request.method == 'POST':
        email = request.form.get('email')
        password = md5(request.form.get('password').encode()).hexdigest()
        user = Users.query.filter_by(email=email,password=password).first()
        if user:
            session['name'] = Users.query.filter_by(email=email).first().email
            return redirect(url_for("index"))
        else:
            flash("Неправильная почта или пароль!", category="bad")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route('/reg', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            surname = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            user = Users(name=name,surname=surname,email=email,password=md5(password.encode()).hexdigest())
            db.session.add(user)
            db.session.commit()
            flash("Регистрация прошла успешно!", category="ok")
            return redirect(url_for("reg"))
        except:
            flash("Произошла ошибка! Проверьте введенные данные!", category="bad")
            db.session.rollback()
            return redirect(url_for("reg"))
    return render_template("reg.html")


@app.context_processor
def inject_user():
    def get_user_name():
        if 'name' in session:
            return Users.query.filter_by(email=session['name']).first()
    return dict(active_user=get_user_name())


@app.context_processor
def inject_user():
    return dict(
    articles_category=db.session.query(Articles.category).distinct().all(),
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidded(e):
    return render_template('403.html'), 403


@app.errorhandler(401)
def forbidded(e):
    return render_template('401.html'), 401


@app.route('/logout')
def logout():
    session.pop('name', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)