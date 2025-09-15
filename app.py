import streamlit as st
import pandas as pd
import datetime
import holidays

# Festivos en Colombia
colombia_holidays = holidays.CO()

# Estado global
if "turnos" not in st.session_state:
    st.session_state.turnos = []

st.title("🗂 Registro de Turnos IPS")

# Formulario
with st.form("registro_turnos"):
    nombre = st.text_input("Nombre del trabajador")
    servicio = st.text_input("Servicio / Área")
    mes = st.selectbox("Mes", list(range(1,13)), index=datetime.date.today().month-1)
    anio = st.number_input("Año", value=datetime.date.today().year, step=1)
    
    # Generar fechas del mes
    primer_dia = datetime.date(anio, mes, 1)
    fechas = []
    d = primer_dia
    while d.month == mes:
        fechas.append(d)
        d += datetime.timedelta(days=1)
    
    fechas_sel = st.multiselect("Selecciona fechas", fechas)
    tipo_turno = st.selectbox("Tipo de turno", ["Nocturno","Dominical","Festivo"])
    observacion = st.text_area("Observaciones (opcional)")
    
    submitted = st.form_submit_button("Registrar")
    if submitted:
        for f in fechas_sel:
            st.session_state.turnos.append({
                "Nombre": nombre,
                "Servicio": servicio,
                "Fecha": f,
                "Tipo_Turno": tipo_turno,
                "Observacion": observacion
            })
        st.success("✅ Turnos registrados correctamente")

# Mostrar detalle
if st.session_state.turnos:
    df = pd.DataFrame(st.session_state.turnos)
    st.subheader("📋 Detalle de registros")
    st.dataframe(df)

    # Consolidado
    df["Horas_Nocturnas"] = df.apply(lambda x: 8 if x["Tipo_Turno"]=="Nocturno" else 0, axis=1)
    df["Horas_Dominicales"] = df.apply(lambda x: 8 if x["Tipo_Turno"]=="Dominical" or x["Fecha"].weekday()==6 else 0, axis=1)
    df["Horas_Festivas"] = df.apply(lambda x: 8 if x["Tipo_Turno"]=="Festivo" or x["Fecha"] in colombia_holidays else 0, axis=1)
    
    reporte = df.groupby(["Servicio","Nombre"])[["Horas_Nocturnas","Horas_Dominicales","Horas_Festivas"]].sum().reset_index()
    reporte["Horas_Totales_Adicionales"] = reporte.sum(axis=1, numeric_only=True)
    
    st.subheader("📊 Consolidado")
    st.dataframe(reporte)

    # Descargar Excel
    with pd.ExcelWriter("reporte_turnos.xlsx") as writer:
        reporte.to_excel(writer, sheet_name="Consolidado", index=False)
        df.to_excel(writer, sheet_name="Detalle", index=False)

    with open("reporte_turnos.xlsx","rb") as f:
        st.download_button("📥 Descargar Excel", f, file_name="reporte_turnos.xlsx")