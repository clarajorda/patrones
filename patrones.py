# all the imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, jsonify
from flask_bootstrap import Bootstrap


# configuration
DATABASE = 'datos.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
Bootstrap(app)

# -- define the conection
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

# -- define a common function to execute command
def extract_pattern(cur_):
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3] ) for row in cur_.fetchall() ]
    return patrones

# -- connect to the database
@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

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
    cur = g.db.execute('insert into patrones (titulo, descripcion, url) values (?, ?, ?)', [request.form.get('titulo'), request.form.get('descripcion'), request.form.get('url')])
    current_id =  (cur.lastrowid)
    values = request.form.get('labels').split(',')
    tupla_values = [(current_id,x,) for x in values if x]
    # print tupla_values
    g.db.executemany('insert into labels (patron_id, etiqueta) values (?,?)', tupla_values )
    g.db.commit()
    flash('New entry was successfully posted', 'success') #success, info, warning o danger
    return redirect(url_for('show_patrones'))

# -- show the list of patterns
@app.route('/list') 
def show_patrones():
    # cur = g.db.execute('select id, titulo, descripcion, url from patrones order by id desc')
    # patrones = extract_pattern(cur)

    cur = g.db.execute(''' select patrones.id, patrones.titulo, patrones.descripcion, patrones.url, group_concat(labels.etiqueta,",") from patrones left join labels on patrones.id = labels.patron_id 
    group by patrones.id ''')
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3], labels=row[4] ) for row in cur.fetchall() ]    
    return render_template('lista.html', patrones=patrones)

# -- show the editable list
@app.route('/list-editable')
def show_and_edit_patrones():
    cur = g.db.execute('select id, titulo, descripcion, url from patrones order by id desc')
    patrones = extract_pattern(cur)
    return render_template('lista-editable.html', patrones=patrones)

# -- show the description for a single patter
@app.route('/show-pattern-<id_pattern>')
def show_single_pattern(id_pattern):

    #cur = g.db.execute('select id, titulo, descripcion, url from patrones where id = ?', (id_pattern,) )
    #patron = extract_pattern(cur)

    cur = g.db.execute(''' select patrones.id, patrones.titulo, patrones.descripcion, patrones.url, group_concat(labels.etiqueta,",") from patrones left join labels on patrones.id = labels.patron_id 
    group by patrones.id having patrones.id = ?''', (id_pattern,))

    patron = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3], labels=row[4] ) for row in cur.fetchall() ]    

    return render_template('single-pattern.html', patron=patron[0])

# -- edit a pattern
@app.route('/new-edition-<id_pattern>')
def edit_entry(id_pattern):
    cur = g.db.execute('select id, titulo, descripcion, url from patrones where id = ?', (id_pattern,) )
    patron = extract_pattern(cur)
    cur2 = g.db.execute('select etiqueta from labels where patron_id = ?', (id_pattern,))
    labels = [ row[0] for row in cur2.fetchall() ]

    return render_template('editar.html', patron=patron[0], labels=','.join(labels))

# -- update the database with the edit information
@app.route('/edit-pattern-<id_pattern>', methods=['POST'])
def edit_pattern(id_pattern):
    cur = g.db.execute('update patrones set titulo = ?, descripcion = ?, url = ? where id = ?', (request.form.get('titulo'), request.form.get('descripcion'), request.form.get('url'), id_pattern,) )

    values = request.form.get('labels').split(',')
    tupla_values = [ ( int(id_pattern),x ) for x in values if x]

    g.db.execute('delete from labels where patron_id = ?', id_pattern, )
    g.db.executemany('insert into labels (patron_id, etiqueta) values (?,?)', tupla_values )
    g.db.commit()

    flash('Edition was successfully posted')
    return redirect(url_for('show_single_pattern',id_pattern=id_pattern))

# -- remove an entry from the database
@app.route('/remove-entry-<id_pattern>')
def remove_entry(id_pattern):
    g.db.execute('delete from patrones where id = ?', (id_pattern,))
    g.db.execute('delete from labels where patron_id = ?', (id_pattern,))
    g.db.commit()
    return redirect(url_for('show_patrones'))

# -- list all labels for the autocompletion
@app.route('/labels/list')
def list_labels():
    cur = g.db.execute("select distinct etiqueta from labels order by etiqueta")
    labels = [ row[0] for row in cur.fetchall() ]
    return jsonify(results=labels)

# -- make a search in the database
@app.route('/search', methods=['POST'])
def search():
    cur = g.db.execute(''' select id, titulo, descripcion,url from patrones where titulo like ? or descripcion like ? ''',  ( '%'+request.form.get('busqueda')+'%','%'+request.form.get('busqueda')+'%' ) )
    patrones = extract_pattern(cur)
    return render_template('lista.html', patrones=patrones)

# -- main function
if __name__ == '__main__':
    app.run()

