import streamlit as st
import pandas as pd
import datetime
import holidays

# ---------------- CONFIGURACIÓN ----------------
colombia_holidays = holidays.CO()

# Estado global
if "turnos" not in st.session_state:
    st.session_state.turnos = []
if "cronograma" not in st.session_state:
    st.session_state.cronograma = None
if "trabajadores" not in st.session_state:
    st.session_state.trabajadores = {
        "URGENCIA": [],
        "UCI": [],
        "HOSPITALIZACIÓN": [],
        "CIRUGÍA": [],
        "LABORATORIO": [],
        "FARMACIA": [],
        "AUXILIARES MÉDICOS": [],
        "SERVICIOS GENERALES": [],
        "MANTENIMIENTO": [],
        "SEGURIDAD": [],
        "ADMISIONES": [],
        "ADMINISTRATIVOS": []
    }

# ---------------- ENCABEZADO ----------------
st.title("🏥 Registro de Turnos IPS")
st.write("Sistema de control de turnos **Nocturnos, Dominicales y Festivos**")

# ---------------- GESTIÓN DE TRABAJADORES ----------------
st.subheader("👥 Gestión de trabajadores")

with st.expander("➕ Agregar trabajador"):
    with st.form("form_add_worker"):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nombre = st.text_input("Nombre del trabajador")
        with col2:
            nuevo_servicio = st.selectbox("Servicio", list(st.session_state.trabajadores.keys()))
        add_worker = st.form_submit_button("Agregar")
        if add_worker and nuevo_nombre:
            if nuevo_nombre not in st.session_state.trabajadores[nuevo_servicio]:
                st.session_state.trabajadores[nuevo_servicio].append(nuevo_nombre)
                st.success(f"✅ {nuevo_nombre} agregado a {nuevo_servicio}")
            else:
                st.warning("⚠️ Ese trabajador ya existe en este servicio")

with st.expander("🗑️ Eliminar trabajador"):
    servicio_borrar = st.selectbox("Selecciona servicio", list(st.session_state.trabajadores.keys()))
    if st.session_state.trabajadores[servicio_borrar]:
        trabajador_borrar = st.selectbox("Selecciona trabajador", st.session_state.trabajadores[servicio_borrar])
        if st.button("Eliminar trabajador"):
            st.session_state.trabajadores[servicio_borrar].remove(trabajador_borrar)
            st.success(f"🗑️ {trabajador_borrar} eliminado de {servicio_borrar}")
    else:
        st.info("No hay trabajadores en este servicio")

# ---------------- FORMULARIO DE TURNOS ----------------
st.subheader("📋 Registro manual de turnos")

with st.form("registro_turnos"):
    col1, col2 = st.columns(2)
    with col1:
        servicio = st.selectbox("🏥 Servicio", list(st.session_state.trabajadores.keys()))
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

    # Lista de fechas del mes seleccionado
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
            st.session_state.turnos.append({
                "Nombre": nombre,
                "Servicio": servicio,
                "Fecha": f,
                "Tipo_Turno": tipo_turno,
                "Observacion": observacion
            })
        st.success("Turnos registrados correctamente")

# ---------------- SUBIDA DE ARCHIVO ----------------
st.subheader("📂 Cargar cronograma de turnos")

uploaded_file = st.file_uploader("Sube un archivo Excel o CSV (cualquier formato)", type=["xlsx","csv"])
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df_upload = pd.read_excel(uploaded_file)
        else:
            df_upload = pd.read_csv(uploaded_file)

        st.session_state.cronograma = df_upload
        st.success("📥 Cronograma cargado correctamente")
        st.dataframe(df_upload, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")

# ---------------- DETALLE ----------------
if st.session_state.turnos:
    df = pd.DataFrame(st.session_state.turnos)
    st.subheader("📑 Detalle de registros")
    st.dataframe(df, use_container_width=True)

    # ---------------- CONSOLIDADO ----------------
    df["Horas_Nocturnas"] = df.apply(lambda x: 8 if x["Tipo_Turno"]=="Nocturno" else 0, axis=1)
    df["Horas_Dominicales"] = df.apply(lambda x: 8 if x["Tipo_Turno"]=="Dominical" or x["Fecha"].weekday()==6 else 0, axis=1)
    df["Horas_Festivas"] = df.apply(lambda x: 8 if x["Tipo_Turno"]=="Festivo" or x["Fecha"] in colombia_holidays else 0, axis=1)

    reporte = df.groupby(["Servicio","Nombre"])[["Horas_Nocturnas","Horas_Dominicales","Horas_Festivas"]].sum().reset_index()
    reporte["Horas_Totales_Adicionales"] = reporte.sum(axis=1, numeric_only=True)

    st.subheader("📊 Consolidado por trabajador")
    st.dataframe(reporte, use_container_width=True)

    st.bar_chart(
        reporte.set_index("Nombre")[["Horas_Nocturnas","Horas_Dominicales","Horas_Festivas"]],
        use_container_width=True
    )

    # ---------------- EXPORTAR ----------------
    st.subheader("📥 Exportar reportes")

    with pd.ExcelWriter("reporte_turnos.xlsx", engine="openpyxl") as writer:
        reporte.to_excel(writer, sheet_name="Consolidado", index=False)
        df.to_excel(writer, sheet_name="Detalle", index=False)
        resumen_servicio = df.groupby("Servicio")[["Horas_Nocturnas","Horas_Dominicales","Horas_Festivas"]].sum().reset_index()
        resumen_servicio["Horas_Totales"] = resumen_servicio.sum(axis=1, numeric_only=True)
        resumen_servicio.to_excel(writer, sheet_name="Resumen_Servicio", index=False)
        if st.session_state.cronograma is not None:
            st.session_state.cronograma.to_excel(writer, sheet_name="Cronograma", index=False)

    with open("reporte_turnos.xlsx","rb") as f:
        st.download_button("⬇️ Descargar Excel con todas las pestañas", 
                           f, file_name="reporte_turnos.xlsx")