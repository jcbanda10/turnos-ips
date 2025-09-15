import streamlit as st
import pandas as pd
import datetime
import holidays
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Registro de Turnos IPS", layout="wide")
st.title("🏥 Registro de Turnos IPS con Google Sheets")

# ---------------- CONFIGURACIÓN ----------------
colombia_holidays = holidays.CO()

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

# ---------------- GOOGLE SHEET ----------------
SHEET_ID = "1pTSu9qr79Y544VFOL3_hjXBqvLVV8xR3Loi9fFs3WrY"

# Función para abrir o crear hoja "Turnos"
def obtener_hoja(sheet_id, nombre_hoja="Turnos"):
    try:
        spreadsheet = client.open_by_key(sheet_id)
        try:
            hoja = spreadsheet.worksheet(nombre_hoja)
        except gspread.WorksheetNotFound:
            hoja = spreadsheet.add_worksheet(title=nombre_hoja, rows="100", cols="10")
        return hoja
    except gspread.SpreadsheetNotFound:
        st.error("❌ No se encontró el Google Sheet. Verifica el ID y que la cuenta de servicio tenga acceso.")
        st.stop()

hoja_turnos = obtener_hoja(SHEET_ID, "Turnos")

# ---------------- FUNCIONES ----------------
def leer_turnos():
    data = hoja_turnos.get_all_records()
    return pd.DataFrame(data)

def guardar_turno(nombre, servicio, fecha, tipo_turno, observacion):
    hoja_turnos.append_row([nombre, servicio, str(fecha), tipo_turno, observacion])

# ---------------- TRABAJADORES ----------------
SERVICIOS = ["URGENCIA", "UCI", "HOSPITALIZACIÓN", "CIRUGÍA",
             "LABORATORIO", "FARMACIA", "AUXILIARES MÉDICOS",
             "SERVICIOS GENERALES", "MANTENIMIENTO", "SEGURIDAD",
             "ADMISIONES", "ADMINISTRATIVOS"]

if "trabajadores" not in st.session_state:
    st.session_state.trabajadores = {servicio: [] for servicio in SERVICIOS}

st.subheader("👥 Gestión de trabajadores")
with st.expander("➕ Agregar trabajador"):
    with st.form("form_add_worker"):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nombre = st.text_input("Nombre del trabajador")
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
df_turnos = leer_turnos()

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

    # Fechas del mes
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
        df_turnos = leer_turnos()

# ---------------- MOSTRAR DATOS ----------------
if not df_turnos.empty:
    st.subheader("📑 Turnos registrados")
    st.dataframe(df_turnos, use_container_width=True)

    # Consolidado
    df_turnos["Horas_Nocturnas"] = df_turnos.apply(lambda x: 8 if x["Tipo_Turno"]=="Nocturno" else 0, axis=1)
    df_turnos["Horas_Dominicales"] = df_turnos.apply(lambda x: 8 if x["Tipo_Turno"]=="Dominical" or pd.to_datetime(x["Fecha"]).weekday()==6 else 0, axis=1)
    df_turnos["Horas_Festivas"] = df_turnos.apply(lambda x: 8 if x["Tipo_Turno"]=="Festivo" or pd.to_datetime(x["Fecha"]) in holidays.CO() else 0, axis=1)

    reporte = df_turnos.groupby(["Servicio","Nombre"])[["Horas_Nocturnas","Horas_Dominicales","Horas_Festivas"]].sum().reset_index()
    reporte["Horas_Totales_Adicionales"] = reporte.sum(axis=1, numeric_only=True)

    st.subheader("📊 Consolidado por trabajador")
    st.dataframe(reporte, use_container_width=True)

    # Exportar Excel
    st.subheader("📥 Exportar reportes")
    with pd.ExcelWriter("reporte_turnos.xlsx", engine="openpyxl") as writer:
        reporte.to_excel(writer, sheet_name="Consolidado", index=False)
        df_turnos.to_excel(writer, sheet_name="Detalle", index=False)
    with open("reporte_turnos.xlsx","rb") as f:
        st.download_button("⬇️ Descargar Excel", f, file_name="reporte_turnos.xlsx")
