import mysql.connector
import streamlit as st

def get_db_connection():
    """Establece y retorna una conexión activa a la base de datos MySQL."""
    try:
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            port=st.secrets["mysql"]["port"],
        )
        cur = conn.cursor()
        cur.execute("SET time_zone = '-05:00';")
        cur.close()
        return conn
    except mysql.connector.Error as e:
        st.error(f"❌ Error crítico al conectar con la base de datos: {e}")
        st.stop()

def query_db(sql, params=(), one=False):
    """Ejecuta consultas de lectura (SELECT) usando la conexión centralizada."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        res = cur.fetchone() if one else cur.fetchall()
        cur.close()
        conn.close()
        return res
    except mysql.connector.Error as e:
        st.error(f"❌ Error SQL en consulta: {e}")
        st.stop()

def execute_db(sql, params=()):
    """Ejecuta operaciones de escritura (INSERT, UPDATE, DELETE)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        rowid, rowcount = cur.lastrowid, cur.rowcount
        cur.close()
        conn.close()
        return rowid, rowcount
    except mysql.connector.Error as e:
        st.error(f"❌ Error SQL al ejecutar: {e}")
        st.stop()