import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import mysql.connector
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from keras.models import load_model
import pickle
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuración de la base de datos
db_config = {
    'user': 'root',  
    'password': '',  
    'host': 'localhost',
    'database': 'VENTAS_LUZ' 
}

# Listas predefinidas
tipos = sorted([
    'Silla giratoria', 'Silla de espera', 'Silla estática', 'Silla mesedora', 'Silla de peluquería',
    'Silla estática con brazo', 'Catre de internación', 'Camillas para masajes', 'Gradilla de 2 peldaños',
    'Biombo', 'Negtoscopio', 'Camilla tipo escritorio', 'Taburete médico', 'Camilla con Barillas',
    'Lámpara de cuello ganzo', 'Velador clínico', 'Camilla de ginecología', 'Pedestal porta sueros',
    'Camilla de examen', 'Camilla de examen con espaldar movible', 'Mesa de trabajo', 'Mesa de curación',
    'Mesa de instrumentación', 'Horno semi-industrial', 'Cocina industrial de dos quemadores', 'Horno domestico',
    'Broastera simple', 'Horno hogareño', 'Góndolas para supermercados', 'Estanteria tipo vitrin',
    'Casillero de cuatro puertas', 'Estante de puertas corredizas', 'Casillero de dos puertas',
    'Casillero de 6 puertas', 'Casillero de 12 puertas', 'Casillero de 15 puertas', 'Casillero de 2 puertas',
    'Casillero de 20 puertas', 'Casillero de 9 puertas', 'Casillero de 1 cuerpo y 4 puertas',
    'Casillero de 1 cuerpo y tres puertas', 'Casillero de 1 cuerpo y 1 puerta', 'Vitrina doble chapa',
    'Ropero casillero', 'Alacena con pedestal', 'Cajero para supermercado', 'Mostrador para librería',
    'Estante mostrador', 'Credenza', 'Estante Archivador', 'Estante para farmacia de dos cuerpos',
    'Estante para farmacia', 'Vitrina para farmacia', 'Estante para farmacia', 'Escritorio secretarial de cuatro cajas con chapa clave',
    'Escritorio ejecutivo de siete cajas', 'Vitrina de puertas corredizas', 'Gabinete de dos cuerpos',
    'Armario de dos cuerpos', 'Estante para archivos con bandejas', 'Archivero', 'Gabetero con chapa independiente',
    'Archivador de Chapas Individuales', 'Gabetero de 4 cajas', 'Gabetero de 3 cajas', 'Gabetero de 2 cajas con chapa adicional',
    'Gabetero de 2 cajas sin chapa', 'Gabetero de 5 cajas'
])

colores = sorted(['Rojo', 'Azul', 'Negro', 'Blanco', 'Gris'])
materiales = sorted(['Metal', 'Melamina'])

agregados_por_tipo = {
    'Silla': ['Acolchonada', 'No acolchonada', 'Con brazos', 'Sin brazos'],
    'Mesa': ['Cuadrada', 'Redonda', 'Con cajones', 'Sin cajones'],
    'Camilla': ['Con barillas', 'Sin barillas', 'Con espaldar movible', 'Fija'],
    'Casillero': ['Con chapa', 'Sin chapa', 'Con espejo', 'Sin espejo'],
    'Estante': ['Con puertas', 'Sin puertas', 'De pared', 'De pie'],
    'Escritorio': ['Con chapas', 'Sin chapas', 'Con ruedas', 'Fijo'],
    'Horno': ['Con ventilador', 'Sin ventilador', 'A gas', 'Eléctrico'],
    'Gabetero': ['Con cerradura', 'Sin cerradura', 'De oficina', 'De hogar'],
    'Vitrina': ['De vidrio', 'De madera', 'Con iluminación', 'Sin iluminación'],
    'Cama': ['Con cabecera', 'Sin cabecera', 'Plegable', 'Fija'],
    'Armario': ['Con espejo', 'Sin espejo', 'De madera', 'Metálico']
}

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
    agregados_json = json.dumps(agregados_por_tipo)
    # Pasar la cadena JSON a la plantilla
    return render_template('index.html', agregados_json=agregados_json)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM persona WHERE nombre = %s AND apellido = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['nombre']
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')


@app.route('/registro', methods=['POST'])
def registro():
    ventas = []
    num_ventas = int(request.form.get('num_ventas', 0))

    for i in range(num_ventas):
        tipo = request.form.get(f'tipo_{i}')
        color = request.form.get(f'color_{i}')
        material = request.form.get(f'material_{i}')
        agregado = request.form.get(f'agregado_{i}')
        cantidad = request.form.get(f'cantidad_{i}')
        precioU = request.form.get(f'precio_{i}')
        fecha = request.form.get(f'fecha_{i}')

        if not (tipo and color and material and agregado and cantidad and precioU and fecha):
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('index'))

        cantidad = int(cantidad)
        precioU = float(precioU)
        precioT = cantidad * precioU

        ventas.append((tipo, color, material, agregado, cantidad, precioU, precioT, fecha))

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
    return redirect(url_for('registro_venta'))

@app.route('/datos')
def datos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ventas')
    ventas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('datos.html', ventas=ventas)

@app.route('/registro')
def registro_venta():
    return render_template('registro.html', tipos=tipos, colores=colores, materiales=materiales, agregados_por_tipo=agregados_por_tipo)

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
