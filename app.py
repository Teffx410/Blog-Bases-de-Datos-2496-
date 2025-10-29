import os
from flask import Flask, render_template, request, redirect, url_for, flash

from neo4j import GraphDatabase
from querys_main import generate_user_id, generate_post_id, generate_comment_id
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'dev-secret-change-me'
# ========================
# CONEXIÓN A NEO4J (local)
# ========================
uri = "neo4j+s://189d458e.databases.neo4j.io" #os.getenv("NEO4J_URI")
user = "neo4j" #os.getenv("NEO4J_USERNAME")
password = "UeFXV5g_Zc8guNdabzDGNe_IlmpI7TAR3C2ZzBGptJM" #os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, password))

# ========================
# PÁGINA PRINCIPAL
# ========================
@app.route('/')
def index():
    return render_template('index.html')

# ========================
# USUARIOS
# ========================
@app.route('/usuarios')
def usuarios():
    with driver.session() as session:
        result = session.run("MATCH (u:User) RETURN u ORDER BY u.id")
        usuarios = [dict(record['u']) for record in result]
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/agregar', methods=['POST'])
def agregar_usuario():
    name = request.form['name']
    with driver.session() as session:
        user_id = generate_user_id(session)
        session.run("CREATE (u:User {id:$id, name:$name})", id=user_id, name=name)
    return redirect(url_for('usuarios'))

@app.route('/usuarios/eliminar/<id>')
def eliminar_usuario(id):
    with driver.session() as session:
        session.run("MATCH (u:User {id:$id}) DETACH DELETE u", id=id)
    return redirect(url_for('usuarios'))

@app.route('/usuarios/editar/<id>', methods=['POST'])
def editar_usuario(id):
    new_name = request.form['name']
    with driver.session() as session:
        session.run("MATCH (u:User {id:$id}) SET u.name=$name", id=id, name=new_name)
    return redirect(url_for('usuarios'))

# ========================
# POSTS
# ========================
@app.route('/posts')
def posts():
    with driver.session() as session:
        query = """
        MATCH (u:User)-[:HAS_POST]->(p:Post)
        RETURN p.idp AS idp, p.idu AS idu, p.content AS content, u.name AS author
        ORDER BY p.idp
        """
        posts = [dict(record) for record in session.run(query)]
    return render_template('posts.html', posts=posts)

@app.route('/posts/agregar', methods=['POST'])
def agregar_post():
    user_id = request.form['user_id']
    content = request.form['content']
    with driver.session() as session:
        post_id = generate_post_id(session)
        session.run("""
        MATCH (u:User {id:$user_id})
        CREATE (p:Post {idp:$idp, idu:$user_id, content:$content})
        CREATE (u)-[:HAS_POST]->(p)
        """, idp=post_id, user_id=user_id, content=content)
    return redirect(url_for('posts'))

@app.route('/posts/eliminar/<idp>')
def eliminar_post(idp):
    with driver.session() as session:
        session.run("MATCH (p:Post {idp:$idp}) DETACH DELETE p", idp=idp)
    return redirect(url_for('posts'))

@app.route('/posts/editar/<idp>', methods=['POST'])
def editar_post(idp):
    new_content = request.form['content']
    with driver.session() as session:
        session.run("MATCH (p:Post {idp:$idp}) SET p.content=$content", idp=idp, content=new_content)
    return redirect(url_for('posts'))

# ========================
# COMENTARIOS
# ========================
@app.route('/comentarios')
def comentarios():
    with driver.session() as session:
        rows = session.run("""
            MATCH (c:Comment)<-[:MAKES]-(u:User)
            OPTIONAL MATCH (a:User)-[:AUTHORIZES]->(c)
            RETURN
              c.idc                                   AS idc,
              coalesce(u.name, u.id)                  AS author,
              coalesce(c.content, c.contenido)        AS content,
              coalesce(c.created_at, c.creation)      AS created_at,
              coalesce(c.authorized, c.autorizado, false) AS authorized,
              a.name                                  AS authorized_by,
              coalesce(c.like, false)                 AS like
            ORDER BY created_at DESC
        """).data()

    # rows es una lista de dicts lista para el template
    return render_template('comentarios.html', comentarios=rows)


@app.route('/comentarios/agregar', methods=['POST'])
def agregar_comentario():
    user_id  = request.form.get('user_id')
    post_id  = request.form.get('post_id')
    content  = request.form.get('content') or request.form.get('contenido')
    like     = (request.form.get('like') or '').lower() in ('on','true','1','sí','si')

    if not user_id or not post_id or not content:
        flash("Faltan campos (user_id, post_id, content).", "error")
        return redirect(url_for('comentarios'))

    from datetime import datetime

    with driver.session() as session:
        # Siguiente id C###
        maxnum = session.run("""
            MATCH (c:Comment)
            WITH c, toInteger(replace(c.idc,'C','')) AS num
            RETURN coalesce(max(num),0) AS maxnum
        """).single()['maxnum'] or 0
        new_idc = f"C{maxnum+1:03d}"

        # CREA el comentario con claves UNIFICADAS
        session.run("""
            MATCH (u:User {id: $user_id})
            MATCH (p:Post {idp: $post_id})
            CREATE (c:Comment {
                idc: $idc,
                content: $content,          // <— usa 'content' (no 'contenido')
                like: $like,
                created_at: $created_at,    // <— usa 'created_at'
                authorized: false           // <— default
            })
            CREATE (u)-[:MAKES]->(c)
            CREATE (p)-[:HAS]->(c)
        """, {
            "user_id": user_id,
            "post_id": post_id,
            "idc": new_idc,
            "content": content,
            "like": like,
            "created_at": datetime.utcnow().isoformat()
        })

    flash("Comentario agregado correctamente.", "success")
    return redirect(url_for('comentarios'))


@app.route('/comentarios/eliminar/<idc>', methods=['POST'])
def eliminar_comentario(idc):
    with driver.session() as session:
        session.run("MATCH (c:Comment {idc: $idc}) DETACH DELETE c", {"idc": idc})
    flash("Comentario eliminado.", "success")
    return redirect(url_for('comentarios'))


@app.route('/comentarios/editar/<idc>', methods=['POST'])
def editar_comentario(idc):
    new_content = request.form['content']
    like = True if 'like' in request.form else False
    with driver.session() as session:
        session.run("MATCH (c:Comment {idc:$idc}) SET c.content=$content, c.like=$like",
                    idc=idc, content=new_content, like=like)
    return redirect(url_for('comentarios'))

from flask import request, redirect, url_for, flash

@app.route('/comentarios/autorizar/<idc>', methods=['POST'])
def autorizar_comentario(idc):
    authorizer_id = request.form.get('authorizer_id', '999')  # MANAGER por defecto

    with driver.session() as session:
        row = session.run("""
            MATCH (c:Comment {idc: $idc})
            OPTIONAL MATCH (u:User {id: $authorizer_id})
            RETURN c IS NOT NULL AS has_comment, u IS NOT NULL AS has_user
        """, {"idc": idc, "authorizer_id": authorizer_id}).single()

        if not row or not row["has_comment"]:
            flash("Comentario no encontrado.", "error")
            return redirect(url_for('comentarios'))
        if not row["has_user"]:
            flash(f"Usuario autorizador {authorizer_id} no existe.", "error")
            return redirect(url_for('comentarios'))

        # ✅ Cypher corregido (elige A o B)
        session.run("""
            MATCH (c:Comment {idc: $idc})
            MATCH (u:User {id: $authorizer_id})
            SET c.authorized = true,
                c.authorized_at = datetime(),      // o: toString(datetime())
                c.authorized_by = $authorizer_id
            MERGE (u)-[:AUTHORIZES]->(c)
        """, {"idc": idc, "authorizer_id": authorizer_id})

    flash("Comentario autorizado.", "success")
    return redirect(url_for('comentarios'))



# ========================
# CONSULTAS
# ========================
@app.route('/consultas', methods=['GET', 'POST'])
def consultas():
    post_id = request.args.get('post_id') or request.form.get('post_id')
    resultados = []

    if post_id:
        with driver.session() as session:
            resultados = session.run("""
                MATCH (p:Post {idp: $post_id})-[:HAS]->(c:Comment)
                OPTIONAL MATCH (u:User)-[:MAKES]->(c)
                OPTIONAL MATCH (a:User)-[:AUTHORIZES]->(c)
                RETURN
                  c.idc                                        AS idc,
                  coalesce(u.name, u.id)                       AS author,
                  coalesce(c.content, c.contenido, '')         AS content,
                  coalesce(toString(c.created_at),
                           toString(c.creation), '-')          AS created_at,
                  coalesce(c.authorized, c.autorizado, false)  AS authorized,
                  CASE
                    WHEN a.name IS NOT NULL THEN a.name
                    WHEN c.authorized_by = '999' THEN 'MANAGER'
                    ELSE coalesce(c.authorized_by, '—')
                  END                                          AS authorized_by,
                  coalesce(c.like, false)                      AS like
                ORDER BY idc
            """, {"post_id": post_id}).data()

    return render_template('consultas.html', resultados=resultados)


@app.route('/consultas/usuario_posts', methods=['POST'])
def consulta_usuario_posts():
    user_id = request.form['user_id']
    with driver.session() as session:
        query = """
        MATCH (u:User {id:$user_id})-[:HAS_POST]->(p:Post)
        WHERE u.name <> 'ANONIMO' AND u.name <> 'MANAGER'
        RETURN u.name AS usuario, p.idp AS idp, p.content AS contenido
        """
        resultados = [dict(record) for record in session.run(query, user_id=user_id)]
    return render_template('consultas.html', resultados=resultados, tipo="usuario_posts")

@app.route('/consultas/comentarios_post', methods=['POST'])
def consulta_comentarios_post():
    post_id = request.form.get('post_id')
    resultados = []
    if post_id:
        with driver.session() as session:
            resultados = session.run("""
                MATCH (p:Post {idp:$post_id})-[:HAS]->(c:Comment)
                OPTIONAL MATCH (a:User)-[:MAKES]->(c)
                OPTIONAL MATCH (auth:User)-[:AUTHORIZES]->(c)

                // Normalizamos fechas y flags
                WITH c, a, auth,
                     CASE
                       WHEN c.created_at IS NOT NULL THEN c.created_at
                       WHEN c.creation   IS NOT NULL THEN c.creation
                       WHEN c.datec      IS NOT NULL THEN c.datec
                       ELSE NULL
                     END AS ca,
                     CASE
                       WHEN c.authorized IS NOT NULL THEN c.authorized
                       WHEN c.autorizado IS NOT NULL THEN c.autorizado
                       WHEN auth IS NOT NULL THEN true
                       ELSE false
                     END AS authflag

                RETURN
                  c.idc                                                AS idc,
                  coalesce(a.name, a.id, '—')                          AS author,
                  coalesce(c.content, c.contenido, '—')                AS content,
                  CASE WHEN ca IS NULL THEN '—' ELSE toString(ca) END  AS created_at,
                  authflag                                             AS authorized,
                  coalesce(
                    auth.name,
                    CASE WHEN c.authorized_by = '999' THEN 'MANAGER' ELSE c.authorized_by END,
                    '—'
                  )                                                    AS authorized_by,
                  coalesce(c.like, c.megusta, false)                   AS like
                ORDER BY ca
            """, {"post_id": post_id}).data()

    return render_template('consultas.html', resultados=resultados, tipo="comentarios_post")


# Consulta 1 — Posts de un usuario (no anónimo ni manager)
@app.route("/consultas/usuario_posts", methods=["POST"])
def consultas_usuario_posts():
    user_id = request.form.get("user_id")
    resultados = []
    if user_id:
        with driver.session() as session:
            resultados = session.run("""
                MATCH (u:User {id:$user_id})-[:HAS_POST]->(p:Post)
                WHERE u.id <> 'ANONIMO' AND u.id <> '999'
                RETURN
                  coalesce(u.name, u.id)                 AS usuario,
                  p.idp                                   AS idp,
                  coalesce(p.content, p.contenido, '—')  AS content
                ORDER BY idp
            """, {"user_id": user_id}).data()
    return render_template("consultas.html", tipo="usuario_posts", resultados=resultados)


# Consulta 2 — Comentarios de un post
@app.route("/consultas/comentarios_post", methods=["POST"])
def consultas_comentarios_post():
    post_id = request.form.get("post_id")
    resultados = []
    if post_id:
        with driver.session() as session:
            resultados = session.run("""
                MATCH (p:Post {idp:$post_id})-[:HAS]->(c:Comment)
                OPTIONAL MATCH (u:User)-[:MAKES]->(c)
                OPTIONAL MATCH (a:User)-[:AUTHORIZES]->(c)
                RETURN
                  c.idc AS idc,
                  coalesce(u.name, u.id, '—')                    AS author,
                  coalesce(c.content, c.contenido, '—')          AS content,
                  coalesce(
                    toString(c.created_at),
                    toString(c.creation),
                    '—'
                  )                                              AS created_at,
                  CASE
                    WHEN coalesce(c.authorized, c.autorizado, false) THEN true
                    WHEN a IS NOT NULL THEN true                 -- relación AUTHORIZES existente
                    ELSE false
                  END                                            AS authorized,
                  coalesce(
                    a.name,
                    CASE WHEN c.authorized_by = '999' THEN 'MANAGER' ELSE c.authorized_by END,
                    '—'
                  )                                              AS authorized_by,
                  coalesce(c.like, c.megusta, false)             AS like
                ORDER BY idc
            """, {"post_id": post_id}).data()
    return render_template("consultas.html", tipo="comentarios_post", resultados=resultados)


# ========================
# RUN SERVER
# ========================
if __name__ == '__main__':
    app.run(debug=True)
