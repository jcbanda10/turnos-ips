import streamlit as st
import pandas as pd
import datetime
import holidays
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Registro de Turnos IPS", layout="wide")
st.title("🏥 Registro de Turnos IPS con Google Sheets por Servicio")

# ---------------- CONFIGURACIÓN ----------------
colombia_holidays = holidays.CO()
SERVICIOS = ["URGENCIA", "UCI", "HOSPITALIZACIÓN", "CIRUGÍA",
             "LABORATORIO", "FARMACIA", "AUXILIARES MÉDICOS",
             "SERVICIOS GENERALES", "MANTENIMIENTO", "SEGURIDAD",
             "ADMISIONES", "ADMINISTRATIVOS"]

# ---------------- CONEXIÓN CON GOOGLE SHEETS ----------------
try:
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
except KeyError:
    st.error(
        "❌ No se encontró la clave 'google_service_account' en los secretos de Streamlit.\n"
        "Crea el secreto en Streamlit Cloud o en .streamlit/secrets.toml."
    )
    st.stop()

SHEET_ID = "1pTSu9qr79Y544VFOL3_hjXBqvLVV8xR3Loi9fFs3WrY"

# ---------------- FUNCIONES ----------------
def obtener_hoja(sheet_id, nombre_hoja):
    """Obtiene o crea una hoja según el nombre de servicio"""
    spreadsheet = client.open_by_key(sheet_id)
    try:
        hoja = spreadsheet.worksheet(nombre_hoja)
    except gspread.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title=nombre_hoja, rows="100", cols="10")
        hoja.append_row(["Nombre", "Fecha", "Tipo_Turno", "Observacion"])
    return hoja

def guardar_turno(nombre, servicio, fecha, tipo_turno, observacion):
    hoja = obtener_hoja(SHEET_ID, servicio)
    df_existente = pd.DataFrame(hoja.get_all_records())

    # Asegurar columnas
    for col in ["Nombre","Fecha","Tipo_Turno","Observacion"]:
        if col not in df_existente.columns:
            df_existente[col] = ""

    # Verificar duplicado
    if ((df_existente["Nombre"] == nombre) & (df_existente["Fecha"] == str(fecha))).any():
        st.warning(f"⚠️ {nombre} ya tiene turno el {fecha} en {servicio}")
        return

    hoja.append_row([nombre, str(fecha), tipo_turno, observacion])

def leer_todos_turnos():
    """Lee todas las pestañas de servicios y las concatena"""
    spreadsheet = client.open_by_key(SHEET_ID)
    todos_dfs = []

    for servicio in SERVICIOS:
        try:
            hoja = spreadsheet.worksheet(servicio)
        except gspread.WorksheetNotFound:
            # Crear hoja vacía con encabezados
            hoja = spreadsheet.add_worksheet(title=servicio, rows="100", cols="10")
            hoja.append_row(["Nombre", "Fecha", "Tipo_Turno", "Observacion"])
            continue  # No hay datos que leer aún

        df = pd.DataFrame(hoja.get_all_records())
        if not df.empty:
            df["Servicio"] = servicio
            todos_dfs.append(df)

    if todos_dfs:
        return pd.concat(todos_dfs, ignore_index=True)
    else:
        return pd.DataFrame(columns=["Nombre","Fecha","Tipo_Turno","Observacion","Servicio"])

def es_festivo(fecha, tipo_turno):
    try:
        fecha_date = pd.to_datetime(fecha).date()
        if tipo_turno == "Festivo" or fecha_date in colombia_holidays:
            return 8
        return 0
    except:
        return 0

# ---------------- TRABAJADORES ----------------
if "trabajadores" not in st.session_state:
    st.session_state.trabajadores = {servicio: [] for servicio in SERVICIOS}

st.subheader("👥 Gestión de trabajadores")
with st.expander("➕ Agregar trabajador"):
    with st.form("form_add_worker"):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nombre = st.text_input("Nombre completo (Nombre + Primer Apellido + Segundo Apellido)").strip()
        with col2:
            nuevo_servicio = st.selectbox("Servicio", SERVICIOS)
        add_worker = st.form_submit_button("Agregar")
        if add_worker and nuevo_nombre:
            if nuevo_nombre not in st.session_state.trabajadores[nuevo_servicio]:
                st.session_state.trabajadores[nuevo_servicio].append(nuevo_nombre)
                st.success(f"✅ {nuevo_nombre} agregado a {nuevo_servicio}")
            else:
                st.warning("⚠️ Ese trabajador ya existe en este servicio")

with st.expander("🗑️ Eliminar trabajador"):
    servicio_borrar = st.selectbox("Selecciona servicio", SERVICIOS)
    if st.session_state.trabajadores[servicio_borrar]:
        trabajador_borrar = st.selectbox("Selecciona trabajador", st.session_state.trabajadores[servicio_borrar])
        if st.button("Eliminar trabajador"):
            st.session_state.trabajadores[servicio_borrar].remove(trabajador_borrar)
            st.success(f"🗑️ {trabajador_borrar} eliminado de {servicio_borrar}")
    else:
        st.info("No hay trabajadores en este servicio")

# ---------------- FORMULARIO DE TURNOS ----------------
st.subheader("📋 Registro de turnos")
df_turnos = leer_todos_turnos()

with st.form("registro_turnos"):
    col1, col2 = st.columns(2)
    with col1:
        servicio = st.selectbox("🏥 Servicio", SERVICIOS)
    with col2:
        if st.session_state.trabajadores[servicio]:
            nombre = st.selectbox("👤 Nombre del trabajador", st.session_state.trabajadores[servicio])
        else:
            nombre = None
            st.warning("⚠️ No hay trabajadores en este servicio, agréguelos primero")

    col3, col4 = st.columns(2)
    with col3:
        mes = st.selectbox("📅 Mes", list(range(1,13)), index=datetime.date.today().month-1)
    with col4:
        anio = st.number_input("🗓️ Año", value=datetime.date.today().year, step=1)

    primer_dia = datetime.date(anio, mes, 1)
    fechas = []
    d = primer_dia
    while d.month == mes:
        fechas.append(d)
        d += datetime.timedelta(days=1)

    fechas_sel = st.multiselect("📌 Selecciona fechas", fechas)
    tipo_turno = st.selectbox("⏰ Tipo de turno", ["Nocturno","Dominical","Festivo"])
    observacion = st.text_area("📝 Observaciones (opcional)")

    submitted = st.form_submit_button("✅ Registrar turnos")
    if submitted and nombre and servicio and fechas_sel:
        for f in fechas_sel:
            guardar_turno(nombre, servicio, f, tipo_turno, observacion)
        st.success("Turnos registrados y guardados en Google Sheets ✅")
        df_turnos = leer_todos_turnos()

# ---------------- MOSTRAR DATOS ----------------
if not df_turnos.empty:
    st.subheader("📑 Turnos registrados")

    for col in ["Nombre","Servicio","Fecha","Tipo_Turno","Observacion"]:
        if col not in df_turnos.columns:
            df_turnos[col] = ""

    st.dataframe(df_turnos, use_container_width=True)

    # Consolidado
    df_turnos["Horas_Nocturnas"] = df_turnos.apply(lambda x: 8 if x.get("Tipo_Turno","")=="Nocturno" else 0, axis=1)
    df_turnos["Horas_Dominicales"] = df_turnos.apply(
        lambda x: 8 if x.get("Tipo_Turno","")=="Dominical" or pd.to_datetime(x.get("Fecha","1970-01-01")).weekday()==6 else 0,
        axis=1
    )
    df_turnos["Horas_Festivas"] = df_turnos.apply(lambda x: es_festivo(x.get("Fecha","1970-01-01"), x.get("Tipo_Turno","")), axis=1)

    reporte = df_turnos.groupby(["Servicio","Nombre"])[["Horas_Nocturnas","Horas_Dominicales","Horas_Festivas"]].sum().reset_index()
    reporte["Horas_Totales_Adicionales"] = reporte.sum(axis=1, numeric_only=True)

    st.subheader("📊 Consolidado por trabajador")
    st.dataframe(reporte, use_container_width=True)

    st.subheader("📥 Exportar reportes")
    with pd.ExcelWriter("reporte_turnos.xlsx", engine="openpyxl") as writer:
        # Guardar cada servicio en una pestaña
        for servicio in SERVICIOS:
            df_servicio = df_turnos[df_turnos["Servicio"]==servicio]
            if not df_servicio.empty:
                df_servicio.to_excel(writer, sheet_name=servicio, index=False)
        reporte.to_excel(writer, sheet_name="Consolidado", index=False)
    with open("reporte_turnos.xlsx","rb") as f:
        st.download_button("⬇️ Descargar Excel", f, file_name="reporte_turnos.xlsx")
