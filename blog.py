from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# ------ KULLANICI KAYIT FORMU ------


class registerForm(Form):
    name = StringField("İsim Soyisim", validators=[
                       validators.Length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[
                           validators.Length(min=4, max=25)])
    email = StringField("Email Adresi", validators=[
                        validators.Email(message="Geçersiz Email Adresi")])
    password = PasswordField("Parola", validators=[
        validators.DataRequired(message="Parola belirleyiniz !!"),
        validators.EqualTo(fieldname="confirm",
                           message="Parolalar aynı değil !!")
    ])
    confirm = PasswordField("Parola Doğrulama")

# ----- KULLANICI GİRİŞ FORMU ------


class loginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

# ----- MAKALE FORM -----


class articleForm(Form):
    title = StringField("Başlık", validators=[
                        validators.Length(min=5, max=100)])
    content = TextAreaField("İçerik", validators=[validators.Length(min=20)])

# ----- KULLANICI GİRİŞ KONTROL DECORATOR -----


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "loggedIn" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapın..!", "danger")
            return redirect(url_for("login"))
    return decorated_function


# ----- HOST ve MySQL AYARLARI -----
app = Flask(__name__)
app.secret_key = "jmpli_krea"
app.config["MYSQL_HOST"] = ""
app.config["MYSQL_USER"] = ""
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = ""
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
app.env = "Development"
mysql = MySQL(app)

# ----- ANASAYFA -----


@app.route("/")
def index():
    return render_template("index.html")

# ----- HAKKINDA -----


@app.route("/about")
def about():
    return render_template("about.html")

# ----- MAKALELER -----


@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()

        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html")


# ----- KAYIT OL ------
@app.route("/register", methods=["GET", "POST"])
def register():
    form = registerForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO users(name,email,username,password) VALUES (%s,%s,%s,%s)"
        cursor.execute(sorgu, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarılı şekilde kaydınız oluşturuldu...", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)

# ------ GİRİŞ YAP ------


@app.route("/login", methods=["GET", "POST"])
def login():
    """1den fazla aynı kişi"""
    form = loginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        passwordEntered = form.password.data
        cursor = mysql.connection.cursor()
        sorguUsername = "SELECT * FROM users WHERE username=%s"
        result = cursor.execute(sorguUsername, (username,))
        if result > 0:
            data = cursor.fetchone()
            cursor.close()
            realPassword = data["password"]
            if sha256_crypt.verify(passwordEntered, realPassword):
                flash("Başarıyla giriş yapıldı...", "success")
                session["loggedIn"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz !!", "danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı yok !!", "danger")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)

# ----- ÇIKIŞ YAP ------


@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış Yapıldı...", "success")
    return redirect(url_for("index"))

# ----- KULLANICI PANELİ ------


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author=%s"
    result = cursor.execute(sorgu, (session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("/dashboard.html", articles=articles)
    else:
        return render_template("/dashboard.html")

# ----- MAKALE EKLEME -----


@app.route("/addarticle", methods=["POST", "GET"])
def addarticle():
    form = articleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        author = session["username"]
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title,author,content) values (%s,%s,%s)"
        cursor.execute(sorgu, (title, author, content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Eklendi...", "success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("/addarticle.html", form=form)

# ----- MAKALE DETAY -----


@app.route("/article/<string:id>")
def detail(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id=%s"
    result = cursor.execute(sorgu, (id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article=article)
    else:
        return render_template("article.html")

# ----- MAKALE SİLME ------


@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    kontrolSorgu = "SELECT * FROM articles WHERE author=%s and id=%s"
    result = cursor.execute(kontrolSorgu, (session["username"], id))
    if result > 0:
        sorgu = "DELETE FROM articles WHERE id=%s"
        cursor.execute(sorgu, (id,))
        mysql.connection.commit()
        cursor.close()
        flash("Makale silindi...", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok!", "danger")
        return redirect(url_for("index"))

# ----- MAKALE GÜNCELLEME -----


@app.route("/edit/<string:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        kontrolSorgu = "SELECT * FROM articles WHERE author=%s and id=%s"
        result = cursor.execute(kontrolSorgu, (session["username"], id))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok!", "danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = articleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("edit.html", form=form)
    else:
        cursor = mysql.connection.cursor()
        kontrolSorgu = "SELECT * FROM articles WHERE author=%s and id=%s"
        result = cursor.execute(kontrolSorgu, (session["username"], id))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok!", "danger")
            return redirect(url_for("index"))
        else:
            form = articleForm(request.form)
            newtitle = form.title.data
            newcontent = form.content.data
            sorgu = "UPDATE articles SET title=%s,content=%s WHERE id=%s"
            cursor.execute(sorgu, (newtitle, newcontent, id))
            mysql.connection.commit()
            cursor.close()
            flash("Makale başaryla güncellendi...", "success")
            return redirect(url_for("dashboard"))

# ----- MAKALE ARAMA


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title like '%"+keyword+"%'"
        result = cursor.execute(sorgu)
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı !", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles=articles)


# ----- LOCALHOST BAŞLAT -----
if __name__ == "__main__":
    app.run(debug=True)
