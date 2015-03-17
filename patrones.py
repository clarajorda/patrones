# all the imports
import os, urlparse
import psycopg2
import sys, logging
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from flask_bootstrap import Bootstrap


# configuration
urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
Bootstrap(app)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

# -- define the conection
def connect_db():
    return psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

# -- connect to the database
@app.before_request
def before_request():
    g.conn = connect_db()
    g.db = g.conn.cursor()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
        g.conn.close()

# -- home
@app.route('/')
def go_home():
    return render_template('home.html')

# -- add new pattern
@app.route('/new-entry')
def insert_entry():
    return render_template('insertar.html')

# -- save the new information into the database
@app.route('/save-entry', methods=['POST'])
def save_entry():
    g.db.execute('insert into patrones (titulo, descripcion, url) values (%s, %s, %s)', (request.form.get('titulo'), request.form.get('descripcion'), request.form.get('url')) )
    g.conn.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_patrones'))

# -- show the list of patterns
@app.route('/list')
def show_patrones():
    g.db.execute('select id, titulo, descripcion, url from patrones order by id desc')
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3] ) for row in g.db.fetchall() ]
    return render_template('lista.html', patrones=patrones)

# -- show the editable list
@app.route('/list-editable')
def show_and_edit_patrones():
    cur = g.db.execute('select id, titulo, descripcion, url from patrones order by id desc')
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3] ) for row in cur.fetchall() ]
    return render_template('lista-editable.html', patrones=patrones)

# -- show the description for a single patter
@app.route('/show-pattern-<id_pattern>')
def show_single_pattern(id_pattern):
    g.db.execute('select id, titulo, descripcion, url from patrones where id = %s', (id_pattern,) )
    patron = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3] ) for row in g.db.fetchall() ]
    return render_template('single-pattern.html', patron=patron[0])

# -- edit a pattern
@app.route('/new-edition-<id_pattern>')
def edit_entry(id_pattern):
    cur = g.db.execute('select id, titulo, descripcion, url from patrones where id = ?', (id_pattern,) )
    patron = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3] ) for row in cur.fetchall() ]
    return render_template('editar.html', patron=patron[0])

# -- update the database with the edit information
@app.route('/edit-pattern-<id_pattern>', methods=['POST'])
def edit_pattern(id_pattern):
    g.db.execute('update patrones set titulo = ?, descripcion = ?, url = ? where id = ?', (request.form.get('titulo'), request.form.get('descripcion'), request.form.get('url'), id_pattern,) )
    g.db.commit()
    flash('Edition was successfully posted')
    return redirect(url_for('show_single_pattern',id_pattern=id_pattern))

# -- main function
if __name__ == '__main__':
    app.run()

