# all the imports
import os, urlparse
import psycopg2
import psycopg2.extensions
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
import sys, logging
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, jsonify
from flask_bootstrap import Bootstrap



# configuration
urlparse.uses_netloc.append("postgres")
DATABASE = os.environ.get("DATABASE_URL", "postgres://wwcyfcrnrnofdq:D2INVOx3bj7qKt6DACMvolcgSf@ec2-54-163-228-58.compute-1.amazonaws.com:5432/dasob1b9e96mtf")
url = urlparse.urlparse(DATABASE)
SECRET_KEY = 'development key'
DEBUG = True

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

# -- define a common function to execute command
def extract_pattern(cur_):
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3] ) for row in cur_.fetchall() ]
    return patrones

# -- define a common function to execute command
def extract_pattern(cur_):
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3] ) for row in cur_.fetchall() ]
    return patrones

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
    g.db.execute('insert into patrones (titulo, descripcion, url) values (%s, %s, %s) returning id', (request.form.get('titulo'), request.form.get('descripcion'), request.form.get('url')) )
    current_id = g.db.fetchone()[0] 
    values = request.form.get('labels').split(',')
    values_norm = [(x.title()) for x in values if x]
    tupla_values = [(current_id,x.title()) for x in list(set(values_norm)) if x]
    g.db.executemany('insert into labels (patron_id, etiqueta) values (%s, %s)', tupla_values )
    g.conn.commit()
    flash('Se incluyo el patron correctamente', 'success') #success, info, warning o danger
    return redirect(url_for('show_and_edit_patrones'))

# -- show the list of patterns
@app.route('/list') 
def show_patrones():
    g.db.execute('''select patrones.id, patrones.titulo, patrones.descripcion, patrones.url, string_agg(labels.etiqueta, ',') from patrones left join labels 
                    on patrones.id = labels.patron_id group by patrones.id, patrones.titulo, patrones.descripcion, patrones.url''')
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3], labels=row[4] ) for row in g.db.fetchall() ]    
    return render_template('lista.html', patrones=patrones)

# -- show the editable list
@app.route('/list-editable')
def show_and_edit_patrones():
    g.db.execute('''select patrones.id, patrones.titulo, patrones.descripcion, patrones.url, string_agg(labels.etiqueta, ',') from patrones left join labels 
                    on patrones.id = labels.patron_id group by patrones.id, patrones.titulo, patrones.descripcion, patrones.url''')
    patrones = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3], labels=sorted(row[4].split(','))) for row in g.db.fetchall() ]  
    return render_template('lista-editable.html', patrones=patrones)


# -- show the description for a single patter
@app.route('/show-pattern-<id_pattern>')
def show_single_pattern(id_pattern):
    g.db.execute('''select patrones.id, patrones.titulo, patrones.descripcion, patrones.url, string_agg(labels.etiqueta, ',') from patrones left join labels 
                    on patrones.id = labels.patron_id group by patrones.id, patrones.titulo, patrones.descripcion, patrones.url having patrones.id = %s''', (id_pattern,) )
    patron = [ dict( id=row[0], titulo=row[1], descripcion=row[2], url=row[3], labels=sorted(row[4].split(',')) ) for row in g.db.fetchall() ]
    return render_template('single-pattern.html', patron=patron[0])

# -- edit a pattern
@app.route('/new-edition-<id_pattern>')
def edit_entry(id_pattern):
    g.db.execute('select id, titulo, descripcion, url from patrones where id = %s', (id_pattern,) )
    patron = extract_pattern(g.db)
    g.db.execute('select etiqueta from labels where patron_id = %s', (id_pattern,) )
    labels = [ row[0] for row in g.db.fetchall() ]

    return render_template('editar.html', patron=patron[0], labels=','.join(labels))

# -- update the database with the edit information
@app.route('/edit-pattern-<id_pattern>', methods=['POST'])
def edit_pattern(id_pattern):
    g.db.execute('update patrones set titulo = %s, descripcion = %s, url = %s where id = %s', (request.form.get('titulo'), request.form.get('descripcion'), request.form.get('url'), id_pattern) )

    values = request.form.get('labels').split(',')
    tupla_values = [ ( int(id_pattern),x ) for x in values if x]

    g.db.execute('delete from labels where patron_id = %s', (id_pattern,) )
    g.db.executemany('insert into labels (patron_id, etiqueta) values (%s, %s)', tupla_values )
    g.conn.commit()
    flash('Se edito el patron correctamente','success')
    return redirect(url_for('show_single_pattern',id_pattern=id_pattern))

# -- remove an entry from the database
@app.route('/remove-entry-<id_pattern>')
def remove_entry(id_pattern):
    g.db.execute('delete from patrones where id = %s', (id_pattern,))
    g.db.execute('delete from labels where patron_id = %s', (id_pattern,))
    g.conn.commit()
    flash('El patron fue borrado correctamente','success')
    return redirect(url_for('show_and_edit_patrones'))

# -- list all labels for the autocompletion
@app.route('/labels/list')
def list_labels():
    g.db.execute("select distinct etiqueta from labels order by etiqueta")
    labels = [ row[0] for row in g.db.fetchall() ]
    return jsonify(results=labels)

# -- make a search in the database
@app.route('/search', methods=['POST'])
def search():
    g.db.execute(''' select id, titulo, descripcion,url from patrones where titulo like %s or descripcion like %s ''',  ( '%'+request.form.get('busqueda')+'%','%'+request.form.get('busqueda')+'%' ) )
    patrones = extract_pattern(g.db)
    return render_template('lista.html', patrones=patrones)

# -- main function
if __name__ == '__main__':
    app.run()

