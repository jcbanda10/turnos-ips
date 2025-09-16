import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import holidays

# -------------------
# Configuración de Google Sheets
# -------------------
SHEET_ID = "1pTSu9qr79Y544VFOL3_hjXBqvLVV8xR3Loi9fFs3WrY"
SERVICIOS = [
    "URGENCIA","UCI","HOSPITALIZACIÓN","CIRUGÍA","LABORATORIO",
    "FARMACIA","AUXILIARES MÉDICOS","SERVICIOS GENERALES","MANTENIMIENTO",
    "SEGURIDAD","ADMISIONES","ADMINISTRATIVOS"
]

# Conectar con Google Sheets
try:
    creds_dict = st.secrets["google_service_account"]
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

# -------------------
# Funciones
# -------------------
def crear_hoja_si_no_existe(servicio):
    try:
        hoja = spreadsheet.worksheet(servicio)
    except gspread.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title=servicio, rows="1000", cols="10")
        hoja.append_row(["Nombre","Fecha","Tipo_Turno","Observación"])
    return hoja

def guardar_turno(nombre, servicio, fecha, tipo_turno, observacion):
    hoja = crear_hoja_si_no_existe(servicio)
    registros = hoja.get_all_records()
    df_existente = pd.DataFrame(registros)

    # Normalizar nombre a minúscula para evitar duplicados
    nombre_lower = nombre.strip().lower()

    if not df_existente.empty:
        df_existente["Nombre_normalizado"] = df_existente["Nombre"].str.strip().str.lower()
        if ((df_existente["Nombre_normalizado"] == nombre_lower) & (df_existente["Fecha"] == str(fecha))).any():
            st.warning(f"Turno ya registrado para {nombre} el {fecha}")
            return

    hoja.append_row([nombre, str(fecha), tipo_turno, observacion])
    st.success(f"Turno registrado: {nombre} - {tipo_turno} - {fecha}")

def eliminar_persona(nombre, servicio):
    hoja = crear_hoja_si_no_existe(servicio)
    registros = hoja.get_all_records()
    if not registros:
        st.warning("No hay registros para este servicio")
        return
    df = pd.DataFrame(registros)
    nombre_lower = nombre.strip().lower()
    df["Nombre_normalizado"] = df["Nombre"].str.strip().str.lower()

    if nombre_lower not in df["Nombre_normalizado"].values:
        st.warning(f"{nombre} no se encuentra en el servicio {servicio}")
        return

    # Filtrar las filas que no sean el nombre a eliminar
    df_filtrado = df[df["Nombre_normalizado"] != nombre_lower].drop(columns=["Nombre_normalizado"])
    hoja.clear()
    hoja.append_row(["Nombre","Fecha","Tipo_Turno","Observación"])
    for _, row in df_filtrado.iterrows():
        hoja.append_row([row["Nombre"], row["Fecha"], row["Tipo_Turno"], row["Observación"]])
    st.success(f"{nombre} eliminado del servicio {servicio}")

def leer_todos_turnos():
    todos = []
    for servicio in SERVICIOS:
        hoja = crear_hoja_si_no_existe(servicio)
        registros = hoja.get_all_records()
        if registros:
            df = pd.DataFrame(registros)
            df["Servicio"] = servicio
            todos.append(df)
    if todos:
        return pd.concat(todos, ignore_index=True)
    return pd.DataFrame(columns=["Nombre","Fecha","Tipo_Turno","Observación","Servicio"])

# -------------------
# Streamlit UI
# -------------------
st.title("Registro de Turnos IPS")

# Formulario para agregar turno
with st.form("registro_turnos"):
    nombre = st.text_input("Nombre completo")
    servicio = st.selectbox("Servicio", SERVICIOS)
    fecha = st.date_input("Fecha del turno", datetime.date.today())
    tipo_turno = st.selectbox("Tipo de turno", ["Nocturno","Dominical","Festivo"])
    observacion = st.text_input("Observación (opcional)")
    submit = st.form_submit_button("Registrar turno")
    
    if submit:
        if nombre:
            guardar_turno(nombre, servicio, fecha, tipo_turno, observacion)
        else:
            st.error("Debe ingresar el nombre del trabajador")

# Formulario para eliminar persona
with st.form("eliminar_persona_form"):
    nombre_eliminar = st.text_input("Nombre completo a eliminar")
    servicio_eliminar = st.selectbox("Servicio de la persona a eliminar", SERVICIOS, key="eliminar_servicio")
    eliminar_submit = st.form_submit_button("Eliminar persona")
    
    if eliminar_submit:
        if nombre_eliminar:
            eliminar_persona(nombre_eliminar, servicio_eliminar)
        else:
            st.error("Debe ingresar el nombre de la persona a eliminar")

# Mostrar consolidado
df_turnos = leer_todos_turnos()
if not df_turnos.empty:
    colombia_holidays = holidays.CO()
    df_turnos["Horas_Nocturnas"] = df_turnos.apply(lambda x: 8 if x["Tipo_Turno"]=="Nocturno" else 0, axis=1)
    df_turnos["Horas_Dominicales"] = df_turnos.apply(lambda x: 8 if x["Tipo_Turno"]=="Dominical" else 0, axis=1)
    df_turnos["Horas_Festivas"] = df_turnos.apply(lambda x: 8 if x["Tipo_Turno"]=="Festivo" or pd.to_datetime(x["Fecha"]).date() in colombia_holidays else 0, axis=1)
    
    st.subheader("Consolidado de Turnos")
    st.dataframe(df_turnos)

    # Descargar Excel con pestañas por servicio y consolidado
    with pd.ExcelWriter("reporte_turnos.xlsx", engine="openpyxl") as writer:
        for servicio in SERVICIOS:
            df_serv = df_turnos[df_turnos["Servicio"]==servicio]
            if not df_serv.empty:
                df_serv.to_excel(writer, sheet_name=servicio, index=False)
        df_turnos.to_excel(writer, sheet_name="Consolidado", index=False)

    with open("reporte_turnos.xlsx", "rb") as f:
        st.download_button("⬇️ Descargar Excel", f, file_name="reporte_turnos.xlsx")
