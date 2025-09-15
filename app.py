import streamlit as st
import pandas as pd
import datetime
import holidays

# ---------------- CONFIGURACIÓN ----------------
colombia_holidays = holidays.CO()

# Estado global
if "turnos" not in st.session_state:
    st.session_state.turnos = []

# ---------------- ENCABEZADO ----------------
col_logo, col_title = st.columns([1,4])
with col_logo:
    st.image("logo.png", width=120)  # 👈 coloca tu logo en la misma carpeta que app.py
with col_title:
    st.title("🏥 Registro de Turnos IPS")
    st.write("Sistema de control de turnos **Nocturnos, Dominicales y Festivos**")

# ---------------- FORMULARIO ----------------
st.subheader("📋 Registro manual de turnos")

with st.form("registro_turnos"):
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("👤 Nombre del trabajador")
    with col2:
        servicio = st.text_input("🏥 Servicio / Área")

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
    if submitted:
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

uploaded_file = st.file_uploader("Sube un archivo Excel o CSV con el cronograma", type=["xlsx","csv"])
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df_upload = pd.read_excel(uploaded_file)
        else:
            df_upload = pd.read_csv(uploaded_file)

        # Normalizamos nombres de columnas mínimas
        # Se espera que el archivo tenga: Nombre, Servicio, Fecha, Tipo_Turno, Observacion
        columnas_necesarias = ["Nombre","Servicio","Fecha","Tipo_Turno"]
        for col in columnas_necesarias:
            if col not in df_upload.columns:
                st.error(f"⚠️ Falta la columna obligatoria: {col}")
                df_upload = None
                break

        if df_upload is not None:
            # Convertir Fecha a datetime si viene como texto
            df_upload["Fecha"] = pd.to_datetime(df_upload["Fecha"]).dt.date

            # Unir con los registros manuales
            for _, row in df_upload.iterrows():
                st.session_state.turnos.append({
                    "Nombre": row["Nombre"],
                    "Servicio": row["Servicio"],
                    "Fecha": row["Fecha"],
                    "Tipo_Turno": row["Tipo_Turno"],
                    "Observacion": row.get("Observacion","")
                })
            st.success("📥 Cronograma cargado y anexado al consolidado")
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

    # ---------------- GRÁFICO ----------------
    st.bar_chart(
        reporte.set_index("Nombre")[["Horas_Nocturnas","Horas_Dominicales","Horas_Festivas"]],
        use_container_width=True
    )

    # ---------------- DESCARGAS ----------------
    st.subheader("📥 Exportar reportes")
    with pd.ExcelWriter("reporte_turnos.xlsx") as writer:
        reporte.to_excel(writer, sheet_name="Consolidado", index=False)
        df.to_excel(writer, sheet_name="Detalle", index=False)

    with open("reporte_turnos.xlsx","rb") as f:
        st.download_button("⬇️ Descargar Excel", f, file_name="reporte_turnos.xlsx")

    st.download_button("⬇️ Descargar CSV (detalle)", df.to_csv(index=False), file_name="detalle_turnos.csv", mime="text/csv")