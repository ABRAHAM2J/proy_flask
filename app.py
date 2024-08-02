import json
import os
import pickle
from datetime import datetime, timedelta

import mysql.connector
import numpy as np
import pandas as pd
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   send_file, session, url_for)
from jinja2 import TemplateNotFound
from keras.models import load_model # type: ignore
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__, template_folder='views')
app.secret_key = 'supersecretkey'

# Configuración de la base de datos
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'bd_ventas'
}

# Función para obtener datos de la base de datos
def get_data_from_db(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# Función para ejecutar comandos de modificación en la base de datos
def execute_db_command(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    conn.commit()
    cursor.close()
    conn.close()

# Funcion para el listado de productos en venta
@app.route('/registro')
def registro_venta():
    query1 = "SELECT * FROM tipos"
    tipos = get_data_from_db(query1)

    query2 = "SELECT * FROM colores"
    colores = get_data_from_db(query2)

    query3 = "SELECT * FROM materiales"
    materiales = get_data_from_db(query3)

    query4 = "SELECT * FROM agregados"
    agregados_data = get_data_from_db(query4)

    agregados_por_tipo = {}
    for agregado in agregados_data:
        tipo_id = agregado['tipo']
        agregado_id = agregado['id']
        nombre = agregado['nombre']
        if tipo_id not in agregados_por_tipo:
            agregados_por_tipo[tipo_id] = []
        agregados_por_tipo[tipo_id].append({'id': agregado_id, 'nombre': nombre})

    query5 = "SELECT * FROM ventas"
    ventas = get_data_from_db(query5)

    return render_template('registro.html', tipos=tipos, colores=colores, materiales=materiales, agregados_por_tipo=agregados_por_tipo, ventas=ventas)

@app.route('/get_price', methods=['POST'])
def get_price():
    data = request.json
    tipo_id = data.get('tipo_id')
    color_id = data.get('color_id')
    material_id = data.get('material_id')
    agregado_id = data.get('agregado_id')

    query = "SELECT precioU FROM producto_combinaciones WHERE tipo_id = %s AND color_id = %s AND material_id = %s AND agregado_id = %s"
    params = (tipo_id, color_id, material_id, agregado_id)
    result = get_data_from_db(query, params)

    if result:
        return jsonify(precioU=result[0]['precioU'])
    else:
        return jsonify(precioU=None), 404




# Función para conectar a la base de datos
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# Función para obtener el siguiente nombre de archivo disponible
def get_next_filename():
    i = 1
    while os.path.exists(f'csv_files/v{i}.csv'):
        i += 1
    return f'csv_files/v{i}.csv'

# Rutas de la aplicación

@app.route('/')
def index():
    # Serializar el diccionario agregados_por_tipo a JSON
    # agregados_json = json.dumps(agregados_por_tipo)
    # Pasar la cadena JSON a la plantilla
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'id' in session:
        return render_template('inicio.html')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM usuario WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            query1 = "SELECT * FROM persona WHERE id = %s"
            persona = get_data_from_db(query1, (user['id_persona'],))
            if persona:
                persona = persona[0]  # Accede al primer elemento de la lista

                session['id'] = user['id']
                session['username'] = user['username']
                session['rol'] = user['rol']
                session['id_persona'] = user['id_persona']
                session['nombre'] = persona['nombre']
                session['apellido'] = persona['apellido']
                flash('Inicio de sesión exitoso.', 'success')
                if user['rol'] == 'administrador':
                    return render_template('inicio.html')
                elif user['rol'] == 'encargado' or user['rol'] == 'empleado':
                    return redirect(url_for('registro'))
            else:
                flash('Datos personales no encontrados.', 'danger')
                return render_template('login.html')
        else:
            flash('Nombre de usuario o contraseña incorrectos.', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('id', None)
    session.pop('username', None)
    session.pop('rol', None)
    session.pop('id_persona', None)
    flash('Cierre de sesión exitoso.', 'success')
    return render_template('login.html')

# @app.route('/<page_name>')
# def render_page(page_name):
#     try:
#         return render_template(f'{page_name}')
#     except TemplateNotFound:
#         return redirect(url_for('page_not_found'))


@app.route('/registro', methods=['POST'])
def registro():
    ventas = []
    num_ventas = int(request.form.get('num_ventas', 0))

    for i in range(num_ventas):
        tipo = request.form.get(f'tipo_{i}')
        color = request.form.get(f'color_{i}')
        material = request.form.get(f'material_{i}')
        agregado_id = request.form.get(f'agregado_{i}')
        cantidad = request.form.get(f'cantidad_{i}')
        precioU = request.form.get(f'precio_{i}')
        fecha = request.form.get(f'fecha_{i}')

        tipo = tipo.split("'")[5]
        color = color.split("'")[5]
        material = material.split("'")[5]

        if not (tipo and color and material and agregado_id and cantidad and precioU and fecha):
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('registro'))

        # Obtener el nombre del agregado a partir de su id
        agregado_nombre = get_agregado_nombre(agregado_id)
        
        cantidad = int(cantidad)
        precioU = float(precioU)
        precioT = cantidad * precioU

        ventas.append((tipo, color, material, agregado_nombre, cantidad, precioU, precioT, fecha))

    # Guardar en la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO ventas (tipo, color, material, agregado, cantidad, precioU, precioT, fecha)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, ventas)
    conn.commit()
    cursor.close()
    conn.close()

    # Generar IDs para el archivo CSV
    ids = list(range(1, len(ventas) + 1))
    ventas_con_id = [(ids[i], *ventas[i]) for i in range(len(ventas))]

    # Guardar en un archivo CSV
    ventas_df = pd.DataFrame(ventas_con_id, columns=['ID', 'Tipo', 'Color', 'Material', 'Agregado', 'Cantidad', 'Precio Unitario', 'Precio Total', 'Fecha'])
    filename = get_next_filename()
    ventas_df.to_csv(filename, index=False)

    flash('Se han registrado las ventas.', 'success')
    return redirect(url_for('registro'))

def get_agregado_nombre(agregado_id):
    query = "SELECT nombre FROM agregados WHERE id = %s"
    result = get_data_from_db(query, (agregado_id,))
    return result[0]['nombre'] if result else None


@app.route('/datos')
def datos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ventas')
    ventas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('registro.html', ventas=ventas)


@app.route('/editar_venta/<int:venta_id>', methods=['GET', 'POST'])
def editar_venta(venta_id):
    if request.method == 'POST':
        tipo_json = request.form.get('tipo_1')
        color_json = request.form.get('color_1')
        material_json = request.form.get('material_1')
        agregado_id = request.form['agregado_1']
        cantidad = int(request.form['cantidad_1'])
        precioU = float(request.form['precioU_1'])
        precioT = cantidad * precioU
        fecha = request.form['fecha_1']

        tipo = json.loads(tipo_json)
        color = json.loads(color_json)
        material = json.loads(material_json)

        tipo_nombre = tipo['nombre']
        color_nombre = color['nombre']
        material_nombre = material['nombre']

        query = """
            UPDATE ventas 
            SET tipo = %s, color = %s, material = %s, agregado = %s, cantidad = %s, precioU = %s, precioT = %s, fecha = %s
            WHERE id = %s
        """
        params = (tipo_nombre, color_nombre, material_nombre, agregado_id, cantidad, precioU, precioT, fecha, venta_id)
        execute_db_command(query, params)

        flash('Venta actualizada correctamente.', 'success')
        return redirect(url_for('registro'))
    return redirect(url_for('registro'))


@app.route('/eliminar_venta/<int:venta_id>', methods=['POST'])
def eliminar_venta(venta_id):
    query = 'DELETE FROM ventas WHERE id = %s'
    execute_db_command(query, (venta_id,))
    flash('Venta eliminada correctamente.', 'success')
    return redirect(url_for('registro'))


@app.route('/profile')
def profile():
    if 'id' not in session:
        return redirect(url_for('login'))  # Redirigir al login si no hay una sesión activa

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM usuario WHERE id = %s', (session['id'],))
    user = cursor.fetchone()

    if user:
        cursor.execute('SELECT * FROM persona WHERE id = %s', (session['id_persona'],))
        persona = cursor.fetchone()
        
        cursor.close()
        conn.close()

        if persona:
            return render_template('profile.html', user=user, persona=persona)
    else:
        cursor.close()
        conn.close()
        flash('Usuario no encontrado.', 'danger')
        return render_template('login.html')

    return render_template('login.html')


@app.route('/update_datos', methods=['POST'])
def update_datos():
    if 'id' not in session:
        flash('Debe iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['id']
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    ci = request.form['ci']
    genero = request.form['genero']
    email = request.form['email']
    telefono = request.form['telefono']
    direccion = request.form['direccion']
    fecha_nac = request.form['fecha_nac']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Actualizar la tabla persona
    cursor.execute("""
        UPDATE persona
        SET nombre = %s, apellido = %s, ci = %s, genero = %s, email = %s, telefono = %s, direccion = %s, fecha_nac = %s
        WHERE id = %s
    """, (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac, session['id_persona']))

    conn.commit()
    cursor.close()
    conn.close()

    # Actualizar los datos de la sesión
    session['nombre'] = nombre
    session['apellido'] = apellido

    flash('Perfil actualizado con éxito.', 'success')
    return redirect(url_for('profile'))

@app.route('/update_user', methods=['POST'])
def update_user():
    if 'id' not in session:
        flash('Debe iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['id']
    username = request.form['username']
    password = request.form['password']
    rol = request.form['rol']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Actualizar la tabla usuario
    cursor.execute("""
        UPDATE usuario
        SET username = %s, password = %s, rol = %s
        WHERE id = %s
    """, (username, password, rol, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Perfil actualizado con éxito.', 'success')
    return redirect(url_for('profile'))


@app.route('/register')
def register():
    query1 = "SELECT * FROM usuario u, persona p WHERE u.id_persona = p.id AND u.rol != 'administrador'"
    usuarios = get_data_from_db(query1)

    return render_template('register.html', usuarios=usuarios)

@app.route('/create_user', methods=['POST'])
def create_user():
    if 'id' not in session:
        flash('Debe iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))
    
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    ci = request.form['ci']
    genero = request.form['genero']
    email = request.form['email']
    telefono = request.form['telefono']
    direccion = request.form['direccion']
    fecha_nac = request.form['fecha_nac']
    rol = request.form['rol']

    # Generar username y password
    nombre_split = nombre.strip().split()
    apellido_split = apellido.strip().split()
    
    if len(nombre_split) > 0 and len(apellido_split) > 0:
        username = nombre_split[0][0].lower() + apellido_split[0].lower()
        if len(apellido_split) > 1:
            username += apellido_split[1][0].lower()
        password = username  # Esto es solo un ejemplo; usualmente, las contraseñas deben ser más seguras
    else:
        flash('Nombre o apellido no proporcionados correctamente.', 'danger')
        return redirect(url_for('register'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insertar en la tabla persona
    cursor.execute("""
        INSERT INTO persona (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac))
    
    # Obtener el id de la persona recién creada
    persona_id = cursor.lastrowid

    # Insertar en la tabla usuario
    cursor.execute("""
        INSERT INTO usuario (username, password, rol, id_persona)
        VALUES (%s, %s, %s, %s)
    """, (username, password, rol, persona_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Usuario creado con éxito.', 'success')
    return redirect(url_for('register'))


@app.route('/editar_datos_personales/<int:user_id>', methods=['POST'])
def editar_datos_personales(user_id):
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    ci = request.form['ci']
    genero = request.form['genero']
    email = request.form['email']
    telefono = request.form['telefono']
    direccion = request.form['direccion']
    fecha_nac = request.form['fecha_nac']

    query = '''
        UPDATE persona
        SET nombre = %s, apellido = %s, ci = %s, genero = %s, email = %s, telefono = %s, direccion = %s, fecha_nac = %s
        WHERE id = %s
    '''
    params = (nombre, apellido, ci, genero, email, telefono, direccion, fecha_nac, user_id)
    execute_db_command(query, params)
    flash('Datos personales actualizados correctamente.', 'success')
    return redirect(url_for('register'))

@app.route('/editar_ajustes_usuario/<int:user_id>', methods=['POST'])
def editar_ajustes_usuario(user_id):
    username = request.form['username']
    password = request.form['password']
    rol = request.form['rol']

    query = '''
        UPDATE usuario
        SET username = %s, password = %s, rol = %s
        WHERE id_persona = %s
    '''
    params = (username, password, rol, user_id)
    execute_db_command(query, params)
    flash('Ajustes de usuario actualizados correctamente.', 'success')
    return redirect(url_for('register'))

@app.route('/eliminar_user/<int:user_id>', methods=['POST'])
def eliminar_user(user_id):
    query_get_persona_id = 'SELECT id_persona FROM usuario WHERE id = %s'
    result = get_data_from_db(query_get_persona_id, (user_id,))
    if result:
        persona_id = result[0]['id_persona']
        
        # Elimina el usuario
        query_delete_user = 'DELETE FROM usuario WHERE id = %s'
        execute_db_command(query_delete_user, (user_id,))
        
        # Elimina la persona asociada
        query_delete_persona = 'DELETE FROM persona WHERE id = %s'
        execute_db_command(query_delete_persona, (persona_id,))
        
        flash('Usuario y persona asociados eliminados correctamente.', 'success')
    else:
        flash('No se encontró el usuario.', 'danger')
    
    return redirect(url_for('registro'))


@app.route('/inventario')
def inventario():
    query1 = "SELECT * FROM tipos"
    tipos = get_data_from_db(query1)

    query2 = "SELECT * FROM colores"
    colores = get_data_from_db(query2)

    query3 = "SELECT * FROM materiales"
    materiales = get_data_from_db(query3)

    query4 = "SELECT * FROM agregados"
    agregados_data = get_data_from_db(query4)

    agregados_por_tipo = {}
    for agregado in agregados_data:
        tipo_id = agregado['tipo']
        agregado_id = agregado['id']
        nombre = agregado['nombre']
        if tipo_id not in agregados_por_tipo:
            agregados_por_tipo[tipo_id] = []
        agregados_por_tipo[tipo_id].append({'id': agregado_id, 'nombre': nombre})

    query5 = "SELECT * FROM ventas"
    ventas = get_data_from_db(query5)

    query6 = "SELECT pc.id, pc.tipo_id, t.nombre as 'n_tipo', pc.color_id, c.nombre as 'n_color', pc.material_id, m.nombre as 'n_material', pc.agregado_id, a.nombre as 'n_agregado', pc.stock, pc.precioU FROM producto_combinaciones pc, tipos t, colores c, materiales m, agregados a WHERE pc.tipo_id = t.id AND pc.color_id = c.id AND pc.material_id = m.id AND pc.agregado_id = a.id"
    inventarios = get_data_from_db(query6)
    return render_template('table.html', inventarios=inventarios, tipos=tipos, colores=colores, materiales=materiales, agregados_por_tipo=agregados_por_tipo, ventas=ventas)









@app.route('/prediccion', methods=['GET'])
def prediccion():
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    # Extraer ventas del día actual desde la base de datos
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ventas WHERE fecha = %s', (fecha_hoy,))
    ventas_hoy = cursor.fetchall()
    cursor.close()
    conn.close()

    if not ventas_hoy:
        flash('No se registraron ventas del día de hoy.', 'warning')
        return redirect(url_for('registro_venta'))

    # Convertir las ventas del día actual en un DataFrame con las columnas adecuadas
    ventas_hoy_df = pd.DataFrame(ventas_hoy)
    ventas_hoy_df.columns = ['ID', 'Tipo', 'Color', 'Material', 'Agregado', 'Cantidad', 'Precio Unitario', 'Precio Total', 'Fecha']

    # Guardar ventas del día actual en un archivo CSV
    filename = get_next_filename()
    ventas_hoy_df.to_csv(filename, index=False)

    # Leer el archivo 'lista.csv'
    ventas_lista = pd.read_csv('lista.csv')

    # Combinar las ventas del día actual con el archivo 'lista.csv'
    ventas_combined = pd.concat([ventas_hoy_df, ventas_lista], ignore_index=True)

    # Realizar la predicción para el día siguiente
    predicciones = predecir_dia_siguiente(ventas_combined)

    # Renderizar el template con las predicciones
    return render_template('predicciones.html', predicciones=predicciones.to_dict(orient='records'))

def predecir_dia_siguiente(ventas_dia):
    # Cargar el modelo entrenado
    model = load_model('modelo.h5')

    # Cargar los codificadores y el scaler
    with open('encoders.pkl', 'rb') as f:
        encoders = pickle.load(f)
    with open('scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)

    ventas_dia = ventas_dia.copy()  # Hacemos una copia para evitar modificaciones sobre la vista
    ventas_dia['Fecha'] = pd.to_datetime(ventas_dia['Fecha'])
    fecha_siguiente = ventas_dia['Fecha'].max() + pd.Timedelta(days=1)
    ventas_dia['Fecha'] = fecha_siguiente
    for feature in encoders.keys():
        ventas_dia[feature] = encoders[feature].transform(ventas_dia[feature])
    ventas_dia['Cantidad'] = scaler.transform(ventas_dia[['Cantidad']])
    X = ventas_dia.drop(columns=['Cantidad', 'Precio Unitario', 'Precio Total', 'Fecha'])
    X = np.expand_dims(X.values, axis=1)
    predicciones = model.predict(X)
    ventas_dia['Cantidad'] = scaler.inverse_transform(predicciones).round().astype(int)  # Redondear y convertir a entero
    for feature in encoders.keys():
        ventas_dia[feature] = encoders[feature].inverse_transform(ventas_dia[feature])
    predicciones_df = ventas_dia[['Tipo', 'Color', 'Material', 'Agregado', 'Cantidad']].head(10)
    predicciones_df.reset_index(inplace=True, drop=True)
    predicciones_df.index += 1
    predicciones_df.reset_index(inplace=True)
    predicciones_df.rename(columns={'index': 'ID'}, inplace=True)
    return predicciones_df

@app.route('/guardar_predicciones', methods=['POST'])
def guardar_predicciones():
    predicciones = request.json['predicciones']
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    hora_hoy = datetime.now().strftime('%H-%M-%S')  
    fecha_manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    filename = f'predicciones_{fecha_hoy}_{hora_hoy}.pdf'
    filepath = os.path.join('pdf_files', filename)

    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont('Helvetica-Bold', 10)

    c.drawString(30, 750, f"Predicciones para el día siguiente: {fecha_manana}")
    c.drawString(30, 735, f"Generado el: {fecha_hoy} a las {hora_hoy}")

    # Encabezados de la tabla
    c.drawString(30, 700, "ID")
    c.drawString(70, 700, "Tipo")
    c.drawString(280, 700, "Color")
    c.drawString(320, 700, "Material")
    c.drawString(390, 700, "Agregado")
    c.drawString(490, 700, "Cant.")

    # Contenido de la tabla
    y = 680
    for prediccion in predicciones:
        c.drawString(30, y, str(prediccion['ID']))
        c.drawString(70, y, prediccion['Tipo'])
        c.drawString(280, y, prediccion['Color'])
        c.drawString(320, y, prediccion['Material'])
        c.drawString(390, y, prediccion['Agregado'])
        c.drawString(490, y, str(prediccion['Cantidad']))
        y -= 20
        if y < 40:  # Para evitar que el texto se salga de la página
            c.showPage()
            c.setFont('Courier', 11)
            y = 750
            c.drawString(30, 700, "ID")
            c.drawString(70, 700, "Tipo")
            c.drawString(280, 700, "Color")
            c.drawString(320, 700, "Material")
            c.drawString(390, 700, "Agregado")
            c.drawString(490, 700, "Cant.")

    c.save()

    return send_file(filepath, as_attachment=True)

@app.route('/guardar_predicciones_futuro', methods=['POST'])
def guardar_predicciones_futuro():
    predicciones = request.json['predicciones']
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    hora_hoy = datetime.now().strftime('%H-%M-%S')
    fecha_futura = predicciones[0]['Fecha']

    filename = f'predicciones_futuro_{fecha_hoy}_{hora_hoy}.pdf'
    filepath = os.path.join('pdf_files', filename)

    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont('Helvetica-Bold', 10)

    c.drawString(30, 750, f"Predicciones para la fecha futura: {fecha_futura}")
    c.drawString(30, 735, f"Generado el: {fecha_hoy} a las {hora_hoy}")

    # Encabezados de la tabla
    c.drawString(30, 700, "ID")
    c.drawString(70, 700, "Tipo")
    c.drawString(280, 700, "Color")
    c.drawString(320, 700, "Material")
    c.drawString(390, 700, "Agregado")
    c.drawString(490, 700, "Cant.")

    # Contenido de la tabla
    y = 680
    for prediccion in predicciones:
        c.drawString(30, y, str(prediccion['ID']))
        c.drawString(70, y, prediccion['Tipo'])
        c.drawString(280, y, prediccion['Color'])
        c.drawString(320, y, prediccion['Material'])
        c.drawString(390, y, prediccion['Agregado'])
        c.drawString(490, y, str(prediccion['Cantidad']))
        y -= 20
        if y < 40:  # Para evitar que el texto se salga de la página
            c.showPage()
            c.setFont('Helvetica-Bold', 10)
            y = 750
            c.drawString(30, y, "ID")
            c.drawString(70, y, "Tipo")
            c.drawString(280, y, "Color")
            c.drawString(320, y, "Material")
            c.drawString(390, y, "Agregado")
            c.drawString(490, y, "Cant.")

    c.save()

    return send_file(filepath, as_attachment=True)

@app.route('/prediccion_futuro', methods=['GET'])
def prediccion_futuro():
    fecha_futura = request.args.get('fecha')
    if not fecha_futura:
        flash('Fecha futura no proporcionada.', 'danger')
        return redirect(url_for('registro_venta'))

    # Obtener las predicciones para la fecha futura
    predicciones = predecir_fecha_futura(fecha_futura)

    # Renderizar el template con las predicciones
    return render_template('datosFuturo.html', predicciones=predicciones.to_dict(orient='records'))

def predecir_fecha_futura(fecha_futura):
    # Cargar el modelo entrenado y los objetos de preprocesamiento
    model = load_model('lstm_model.h5')

    with open('label_encoders.pkl', 'rb') as f:
        label_encoders = pickle.load(f)
    with open('scaler1.pkl', 'rb') as f:
        scaler = pickle.load(f)

    # Cargar los datos históricos
    file_path = 'lista.csv'
    df = pd.read_csv(file_path)

    # Preprocesar los datos históricos
    categorical_columns = ['Tipo', 'Color', 'Material', 'Agregado']
    for col in categorical_columns:
        df[col] = label_encoders[col].transform(df[col])

    df['Cantidad'] = scaler.transform(df[['Cantidad']])
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df = df.sort_values(by='Fecha')

    future_date = datetime.strptime(fecha_futura, "%Y-%m-%d")
    future_day_of_week = future_date.weekday()

    # Crear una secuencia de entrada a partir de los datos históricos más recientes
    sequence_length = 30 
    features = ['Tipo', 'Color', 'Material', 'Agregado', 'Cantidad']
    last_sequence = df[features].values[-sequence_length:]

    # Realizar predicciones iterativas hasta la fecha futura
    current_date = df['Fecha'].iloc[-1]
    predicted_products = []

    # Asegurémonos de solo predecir 6 productos para la fecha futura
    while current_date < future_date:
        daily_predictions = []
        for _ in range(6):  # Generar 6 predicciones para la fecha futura
            last_sequence = last_sequence.reshape((1, sequence_length, len(features)))
            try:
                predicted_values = model.predict(last_sequence, verbose=0)[0]
            except Exception as e:
                print(f"Error during prediction: {e}")
                continue

            # Asignar el tipo, color, material y agregado a partir del promedio histórico
            predicted_values[0] = np.random.choice(df['Tipo'].unique())
            predicted_values[1] = np.random.choice(df['Color'].unique())
            predicted_values[2] = np.random.choice(df['Material'].unique())
            predicted_values[3] = np.random.choice(df['Agregado'].unique())

            daily_predictions.append(predicted_values)
            last_sequence = np.append(last_sequence[0][1:], [predicted_values], axis=0)

        predicted_products.extend(daily_predictions)
        current_date += timedelta(days=1)
        break  # Solo queremos las predicciones para un día específico

    # Transformar las predicciones inversamente a sus etiquetas originales
    predicted_df = pd.DataFrame(predicted_products, columns=features)
    for col in categorical_columns:
        predicted_df[col] = label_encoders[col].inverse_transform(predicted_df[col].astype(int))

    # Asignar las cantidades promedio de los datos históricos del mismo tipo de producto
    def get_avg_quantity(row):
        filtered_df = df[df['Tipo'] == row['Tipo']]
        if not filtered_df.empty:
            avg_quantity = filtered_df['Cantidad'].mean()
            return abs(avg_quantity)  # Asegurar que la cantidad sea positiva
        else:
            return abs(row['Cantidad'])

    predicted_df['Cantidad'] = predicted_df.apply(get_avg_quantity, axis=1)
    predicted_df['Cantidad'] = scaler.inverse_transform(predicted_df[['Cantidad']])
    predicted_df['Cantidad'] = predicted_df['Cantidad'].abs().round().astype(int)

    predicted_df['Fecha'] = future_date

    # Añadir columna de ID
    predicted_df['ID'] = range(1, len(predicted_df) + 1)

    # Mostrar los resultados de la predicción (solo 6 productos)
    return predicted_df[['ID', 'Tipo', 'Color', 'Material', 'Agregado', 'Cantidad', 'Fecha']].head(6)

if __name__ == '__main__':
    if not os.path.exists('csv_files'):
        os.makedirs('csv_files')
    if not os.path.exists('pdf_files'):
        os.makedirs('pdf_files')
    app.run(debug=True)
