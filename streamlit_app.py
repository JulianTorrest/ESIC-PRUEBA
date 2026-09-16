# uncompyle6 version 3.9.3

# Python bytecode version base 3.8.0 (3413)

# Decompiled from: Python 3.8.10 (tags/v3.8.10:3d8993a, May  3 2021, 11:48:03) [MSC v.1928 64 bit (AMD64)]

# Embedded file name: streamlit_app.py

# Compiled at: 2026-09-15 21:34:10

# Size of source mod 2**32: 24250 bytes

import re
import sqlite3, uuid

from datetime import datetime

from pathlib import Path

import pandas as pd, streamlit as st

from architecture_view import get_architecture_view, list_views, mermaid_image_url

from auth import check_credentials, get_default_credentials

from cache import ResponseCache

from data_generator import main as generate_data

from document_validator import DocumentValidator

from education_analytics import EducationAnalytics

from llm_service import direct_search, generate_response

from observability import feedback_stats, finops_summary, get_traces, rate_limit_check, save_feedback

from recommender import ProgramRecommender

from pdf_generator import generar_imagenes_pdf, generar_imagenes_presentacion_ejecutiva, preview_pdf_text

from ui import apply_custom_styles

from vector_store import DATA_FILE, get_vector_store

BASE_DIR = Path(__file__).resolve().parent

LOGO_PATH = BASE_DIR / "Logo.png"

LOG_DB = BASE_DIR / "data" / "interactions.db"



def _get_cache():

    try:

        redis_url = st.secrets["cache"]["REDIS_URL"]

    except (FileNotFoundError, KeyError, TypeError):

        redis_url = None

    else:

        return ResponseCache(redis_url=redis_url)





cache = _get_cache()

st.set_page_config(page_title="ESIC Asistente IA - Escenarios",

  page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,

  layout="wide",

  initial_sidebar_state="collapsed")



PII_PATTERNS = [
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    re.compile(r'\b\d{10,11}\b'),
    re.compile(r'\b\d{6,10}\b'),
]

PROMPT_INJECTION_KEYWORDS = [
    'ignora', 'olvidar', 'system', 'sistema', 'prompt', 'instrucciones', 'role', 'rol',
    'bypass', 'hackear', 'jailbreak', 'override', 'modo desarrollador', 'ignore previous',
    'ignore todas', 'olvidate', 'desactivar', 'burlar'
]

GROSERIAS = [
    'puta', 'puto', 'mierda', 'marica', 'maricon', 'idiota', 'estupido', 'estupida',
    'imbecil', 'pendejo', 'pendeja', 'culero', 'huevon', 'cago', 'carajo', 'verga',
    'chinga', 'chingar', 'coño', 'joder', 'jodete', 'hijueputa', 'malparido'
]

TEMAS_PERMITIDOS = [
    'programa', 'especializacion', 'maestria', 'doctorado', 'pregrado', 'posgrado',
    'financiamiento', 'beca', 'credito', 'pago', 'matricula',
    'empleo', 'trabajo', 'oportunidad', 'laboral', 'empresa', 'cargo',
    'admision', 'documento', 'validacion', 'requisito',
    'recomendacion', 'carrera', 'habilidad', 'area', 'asesor', 'contacto',
    'hola', 'buenos dias', 'gracias', 'adios'
]


def _validar_seguridad(texto: str):
    """Valida PII, prompt injection, insultos y temas permitidos."""
    for patron in PII_PATTERNS:
        if patron.search(texto):
            return False, "No compartas datos personales (correos, telefonos, documentos)."
    q = texto.lower()
    for kw in PROMPT_INJECTION_KEYWORDS:
        if kw in q:
            return False, "Detectado intento de manipulacion del sistema."
    for g in GROSERIAS:
        if re.search(rf'\b{re.escape(g)}', q, re.IGNORECASE):
            return False, "Detectado lenguaje inapropiado."
    if not any(tema in q for tema in TEMAS_PERMITIDOS):
        return False, "Solo puedo responder sobre programas, admisiones, financiamiento, empleabilidad y recomendaciones."
    return True, ""


def _sanitizar_respuesta(texto: str) -> str:
    for g in GROSERIAS:
        texto = re.sub(rf'\b{re.escape(g)}', '[***]', texto, flags=re.IGNORECASE)
    return texto


def ensure_data():

    if not DATA_FILE.exists():

        with st.spinner("Generando datos dummies..."):

            generate_data()





def init_logs_db():

    LOG_DB.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(LOG_DB)

    cursor = conn.cursor()

    cursor.executescript("\n        CREATE TABLE IF NOT EXISTS interactions (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            session_id TEXT,\n            role TEXT,\n            message TEXT,\n            vector_store TEXT,\n            sources TEXT,\n            escalated INTEGER,\n            created_at TEXT\n        );\n        CREATE TABLE IF NOT EXISTS escalations (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            session_id TEXT,\n            user_name TEXT,\n            user_email TEXT,\n            reason TEXT,\n            context TEXT,\n            created_at TEXT\n        );\n        ")

    conn.commit()

    conn.close()





def log_interaction(session_id, role, message, vector_store, sources, escalated):

    conn = sqlite3.connect(LOG_DB)

    cursor = conn.cursor()

    cursor.execute("INSERT INTO interactions (session_id, role, message, vector_store, sources, escalated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (

     session_id, role, message, vector_store, sources, escalated, datetime.now().isoformat()))

    conn.commit()

    conn.close()





def log_escalation(session_id, name, email, reason, context):

    conn = sqlite3.connect(LOG_DB)

    cursor = conn.cursor()

    cursor.execute("INSERT INTO escalations (session_id, user_name, user_email, reason, context, created_at) VALUES (?, ?, ?, ?, ?, ?)", (

     session_id, name, email, reason, context, datetime.now().isoformat()))

    conn.commit()

    conn.close()





def get_default_config():

    """Lee la configuracin por defecto desde secrets.toml sin mostrar sidebar."""

    try:

        store_name = st.secrets["llm"].get("DEFAULT_VECTOR_STORE", "SQLite")

    except (FileNotFoundError, KeyError, TypeError):

        store_name = "SQLite"

    else:

        try:

            provider = st.secrets["llm"].get("DEFAULT_PROVIDER", "local")

        except (FileNotFoundError, KeyError, TypeError):

            provider = "local"

        else:

            try:

                model = st.secrets["models"].get(f"{provider.upper()}_MODEL", "")

            except (FileNotFoundError, KeyError, TypeError):

                model = ""

            else:

                try:

                    api_key = st.secrets["api_keys"].get(f"{provider.upper()}_API_KEY", "")

                except (FileNotFoundError, KeyError, TypeError):

                    api_key = ""

                else:

                    return (

                     store_name, provider, model, api_key)





def render_chatbot(store_name, provider, model, api_key):

    st.title("ESIC Medellín - Chatbot Inteligente para Egresados")

    st.markdown("### Escenario 1: Consultas sobre programas, financiamiento y oportunidades laborales")

    if st.session_state.vector_store is None or st.session_state.get("store_name") != store_name:

        with st.spinner(f"Cargando base vectorial {store_name}..."):

            st.session_state.vector_store = get_vector_store(store_name)

            st.session_state.store_name = store_name

    store = st.session_state.vector_store

    if st.session_state.get("pending_answer"):

        st.session_state.messages.append({'role':"assistant",  'content':(st.session_state).pending_answer,  'trace_id':(st.session_state.get)("pending_trace_id")})

        del st.session_state.pending_answer

        del st.session_state.pending_trace_id

    for msg in st.session_state.messages:

        with st.chat_message(msg["role"]):

            st.markdown(msg["content"])

            if msg["role"] == "assistant":

                if msg.get("trace_id"):

                    c1, c2 = st.columns([1, 1])

                    with c1:

                        if st.button("i Util", key=f'up_{msg["trace_id"]}'):

                            save_feedback(msg["trace_id"], st.session_state.session_id, 1)

                            st.success("iGracias por tu feedback!")

                    with c2:

                        if st.button("A No til", key=f'down_{msg["trace_id"]}'):

                            save_feedback(msg["trace_id"], st.session_state.session_id, 0)

                            st.success("Gracias, lo usaremos para mejorar.")

    else:

        user_query = st.chat_input("Escribe tu consulta, por ejemplo: 'qu programas de especializacin ofrecen para egresados de marketing?'")

        if user_query:

            if not rate_limit_check((st.session_state.session_id), max_calls=100, window_minutes=60):

                st.warning("Has alcanzado el lmite de 100 consultas por hora. Intenta más tarde.")

            else:

                seguro, motivo = _validar_seguridad(user_query)

                if not seguro:

                    st.warning(f"Consulta bloqueada: {motivo}")

                    st.session_state.messages.append({'role':"user",  'content':user_query})

                    st.session_state.messages.append({'role':"assistant",  'content':"Tu consulta fue bloqueada por seguridad. Evita compartir datos personales o usar lenguaje inapropiado."})

                    st.rerun()

                st.session_state.messages.append({'role':"user",  'content':user_query})

                q = user_query.lower()

                if "programa" in q or "especializacin" in q:

                    results = direct_search(user_query, "programas")

                else:

                    results = store.search(user_query, k=5)

                sources = ", ".join(sorted(set((r["category"] for r in results)))) if results else "ninguna"

                confidence = max([r["score"] for r in results]) if results else 0.0

                escalated = confidence < 0.45

                trace_id = None

                if escalated:

                    answer = "No encontr informacin con la confianza suficiente para responder. He registrado tu consulta para que un asesor humano de ESIC te contacte. Puedes dejar tus datos en el panel lateral de 'Derivar a asesor'."

                else:

                    answer, trace_id = generate_response(user_query,

                      results,

                      session_id=(st.session_state.session_id),

                      provider=provider,

                      api_key=(api_key or None),

                      model=(model or None),

                      cache=cache)

                answer = _sanitizar_respuesta(answer)

                st.session_state.pending_answer = answer

                st.session_state.pending_trace_id = trace_id

                log_interaction(st.session_state.session_id, "user", user_query, store_name, sources, int(escalated))

                log_interaction(st.session_state.session_id, "assistant", answer, store_name, sources, int(escalated))

                st.rerun()

        with st.sidebar:

            st.markdown("---")

            st.header("n Derivar a asesor")

            name = st.text_input("Nombre")

            email = st.text_input("Correo")

            reason = st.text_area("Motivo de escalamiento")

            if st.button("Derivar ahora"):

                context = "\n".join([f'{m["role"]}: {m["content"]}' for m in st.session_state.messages[-6:]])

                log_escalation(st.session_state.session_id, name, email, reason, context)

                st.success("Caso de escalamiento registrado. Un asesor te contactari.")





def render_document_validator():

    st.title("ESIC Medellín - Validación de Documentos de Admisión")

    st.markdown("### Escenario 2: Procesamiento, validación y reporte de documentos")

    validator = DocumentValidator()

    solicitudes = validator.get_solicitudes()

    col1, col2 = st.columns([1, 2])

    with col1:

        st.subheader("Validar solicitud")

        ids = [s["id"] for s in solicitudes]

        selected_id = st.selectbox("Selecciona una solicitud", ids)

        uploaded = st.file_uploader("Subir documento (PDF, DOCX, TXT o imagen)",

          type=[

         'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'])

        if st.button("UC Procesar y validar"):

            file_bytes = uploaded.getvalue() if uploaded else None

            filename = uploaded.name if uploaded else None

            resultado = validator.validar_solicitud(selected_id, file_bytes, filename)

            if "error" in resultado:

                st.error(resultado["error"])

            else:

                st.success(f'Solicitud {selected_id}: **{resultado["estado_final"].upper()}**')

                st.json(resultado)

    with col2:

        st.subheader("Reporte de validaciones")

        reporte = validator.generar_reporte()

        st.dataframe(reporte, use_container_width=True)

        aprobadas = (reporte["Estado"] == "Aprobada").sum()

        rechazadas = (reporte["Estado"] != "Aprobada").sum()

        col_a, col_r = st.columns(2)

        col_a.metric("Aprobadas", aprobadas)

        col_r.metric("Pendientes/Rechazadas", rechazadas)

        st.download_button("Descargar reporte CSV",

          data=(reporte.to_csv(index=False).encode("utf-8")),

          file_name="reporte_validacion_documentos.csv",

          mime="text/csv")





def render_recommender():

    st.title("ESIC Medellín - Recomendación de Programas")

    st.markdown("### Escenario 3: Sistema inteligente de recomendación personalizada")

    rec = ProgramRecommender()

    with st.form("perfil_estudiante"):

        st.subheader("Perfil del estudiante")

        col1, col2 = st.columns(2)

        with col1:

            tipo_programa_buscado = st.selectbox("Qu tipo de programa buscas?", [

             'No importa', 'Pregrado', 'Posgrado / Especialización', 

             'Maestra / Mister', 'Doctorado'])

            edad = st.number_input("Edad", min_value=16, max_value=80, value=28)

            experiencia_anos = st.number_input("Aos de experiencia profesional", min_value=0, max_value=40, value=3)

            sector_economico = st.text_input("Sector econmico de inters", "tecnologa")

        with col2:

            pais_origen = st.text_input("Pas de origen", "Colombia")

            universidad_pregrado = st.text_input("Universidad de pregrado (si aplica)", "")

            programa_pregrado = st.text_input("Programa de pregrado (si aplica)", "")

            habilidades = st.text_input("Habilidades (separadas por coma)", "anilisis de datos, comunicacin, marketing")

        st.markdown("---")

        intereses = st.text_input("Intereses profesionales", "digital, negocios, innovacin")

        carrera = st.text_input("Carrera anterior / área de formacin", "Administración de empresas")

        submitted = st.form_submit_button("Recomendar programas")

    if submitted:

        perfil = {'habilidades': habilidades, 

         'intereses': intereses, 

         'carrera': carrera, 

         'tipo_programa_buscado': tipo_programa_buscado, 

         'edad': edad, 

         'experiencia_anos': experiencia_anos, 

         'sector_economico': sector_economico, 

         'pais_origen': pais_origen, 

         'universidad_pregrado': universidad_pregrado, 

         'programa_pregrado': programa_pregrado}

        recomendaciones = rec.recommend(perfil, n=3)

        n = len(recomendaciones)

        st.markdown("---")

        st.subheader("Indicadores de recomendacion")

        kpi1, kpi2, kpi3 = st.columns(3)

        kpi1.metric("Programas recomendados", n)

        kpi2.metric("Afinidad promedio", (f'{sum((r["score_similitud"] for r in recomendaciones)) / n:.2f}') if n > 0 else "-")

        if n > 0 and any((r["programa"].get("empleabilidad") for r in recomendaciones)):

            emp_avg = sum((r["programa"].get("empleabilidad", 0) for r in recomendaciones)) / n

            kpi3.metric("Empleabilidad promedio", f"{emp_avg:.1f}%")

        else:

            kpi3.metric("Empleabilidad promedio", "-")

        kpi4, kpi5, kpi6 = st.columns(3)

        if n > 0 and any((r["programa"].get("salario_promedio_egresado_cop") for r in recomendaciones)):

            sal_avg = sum((r["programa"].get("salario_promedio_egresado_cop", 0) for r in recomendaciones)) / n

            kpi4.metric("Salario promedio egresado", f"${sal_avg:,.0f}")

        else:

            kpi4.metric("Salario promedio egresado", "-")

        if n > 0:

            rois = []

            for r in recomendaciones:

                p = r["programa"]

                sal = p.get("salario_promedio_egresado_cop")

                pre = p.get("precio_cop")

                if sal and pre:

                    rois.append((sal * 12 / pre - 1) * 100)

            if rois:

                kpi5.metric("ROI promedio", f"{sum(rois) / len(rois):.0f}%")

            else:

                kpi5.metric("ROI promedio", "-")

        else:

            kpi5.metric("ROI promedio", "-")

        if n > 0 and any((r["programa"].get("tiempo_colocacion_meses") for r in recomendaciones)):

            t_avg = sum((r["programa"].get("tiempo_colocacion_meses", 0) for r in recomendaciones)) / n

            kpi6.metric("Tiempo promedio de colocacion", f"{t_avg:.1f} meses")

        else:

            kpi6.metric("Tiempo promedio de colocacion", "-")

        df = pd.DataFrame([{'Programa':r["programa"]["nombre"], 

         'Afinidad':r["score_similitud"],  'Empleabilidad (%)':r["programa"].get("empleabilidad", 0)} for r in recomendaciones])

        c1, c2 = st.columns(2)

        with c1:

            st.bar_chart(df.set_index("Programa")["Afinidad"])

        with c2:

            st.bar_chart(df.set_index("Programa")["Empleabilidad (%)"])

        st.markdown("---")

        for i, r in enumerate(recomendaciones, 1):

            p = r["programa"]

            with st.container():

                st.markdown(f'**{i}. {p["nombre"]}** — *{p["nivel"]}* ({p["modalidad"]}, {p["duracion"]})')

                st.markdown(f'_{r["razonamiento"]}_')

                st.progress(min(1.0, max(0.0, r["score_similitud"])))

                st.caption(f'Score de afinidad: {r["score_similitud"]:.3f}')

                with st.expander("Detalles del programa"):

                    c1, c2 = st.columns(2)

                    with c1:

                        st.markdown(f'**urea:** {p["area"]}')

                        st.markdown(f'**Nivel:** {p["nivel"]}')

                        st.markdown(f'**Modalidad:** {p["modalidad"]}')

                        st.markdown(f'**Duracin:** {p["duracion"]}')

                        if p.get("vigencia"):

                            st.markdown(f'**Vigencia:** {p["vigencia"]}')

                    with c2:

                        if p.get("precio_cop"):

                            st.markdown(f'**Precio (COP):** ${p["precio_cop"]:,}')

                            if p.get("salario_promedio_egresado_cop"):

                                roi = (p["salario_promedio_egresado_cop"] * 12 / p["precio_cop"] - 1) * 100

                                st.markdown(f"**ROI:** {roi:.0f}%")

                        if p.get("empleabilidad"):

                            st.markdown(f'**Empleabilidad:** {p["empleabilidad"]}%')

                        if p.get("salario_promedio_egresado_cop"):

                            st.markdown(f'**Salario egresado:** ${p["salario_promedio_egresado_cop"]:,}')

                        if p.get("tiempo_colocacion_meses"):

                            st.markdown(f'**Tiempo para conseguir trabajo:** {p["tiempo_colocacion_meses"]} meses')

                    st.markdown("---")

                    st.markdown(f'**Descripción**  \n{p.get("descripcion", "—")}')

                    st.markdown(f'**Requisitos**  \n{p.get("requisitos", "—")}')





def render_analytics():

    st.title("ESIC Medellín - Education Analytics")

    st.markdown("### Escenario 4: Analítica y pronósticos educativos")

    analytics = EducationAnalytics()

    tab_a, tab_b, tab_c, tab_d = st.tabs(["Empleabilidad", "Pronstico de demanda", "Pronstico del estudiante", "Top áreas en demanda"])

    with tab_a:

        st.subheader("Estadísticas de empleabilidad por área")

        st.caption("Se muestran solo las áreas con egresados en la base de datos para evitar filas con datos vacos.")

        stats = analytics.program_stats(solo_con_egresados=True)

        st.dataframe(stats, use_container_width=True)

        st.bar_chart(stats.set_index("Area")["Tasa empleabilidad (%)"])

    with tab_b:

        st.subheader("Pronstico de demanda por programa")

        st.caption("Cada columna representa un año proyectado a partir del año actual (Ao +1, Ao +2, etc.).")

        n_periods = st.slider("Aos a pronosticar", 2, 8, 4)

        forecast = analytics.forecast_demand(periodos=n_periods)

        st.dataframe(forecast, use_container_width=True)

        st.line_chart(forecast.set_index("Programa").drop(columns=["Area", "Demanda base"]))

    with tab_c:

        st.subheader("Pronstico de éxito del estudiante")

        carrera = st.text_input("Carrera del estudiante", "Ingeniera industrial", key="carrera_eéxito")

        habilidades = st.text_input("Habilidades clave", "matemiticas, liderazgo, anilisis", key="habilidades_eéxito")

        if st.button("Predecir éxito"):

            pred = analytics.predict_student_success(carrera, habilidades)

            col1, col2 = st.columns(2)

            col1.metric("índice de éxito estimado", f'{pred["indice_eéxito_estimado"]}%')

            col2.metric("Riesgo de abandono", f'{pred["indice_riesgo_abandono"]}%')

            st.info(f'Recomendación: {pred["recomendacion_intervencion"]}')

    with tab_d:

        st.subheader("Top áreas con más ofertas laborales")

        n = st.slider("Nmero de áreas", 3, 10, 5)

        top = analytics.top_skills_demand(n)

        st.dataframe(top, use_container_width=True)

        st.bar_chart(top.set_index("Area"))





def render_architecture():

    st.title("ESIC Medellín - Arquitectura Empresarial")

    st.markdown("### Vistas de arquitectura con Mermaid")

    vista = st.selectbox("Selecciona una vista de arquitectura", list_views())

    data = get_architecture_view(vista)

    st.subheader(data["titulo"])

    st.markdown(data["descripcion"])

    st.image((mermaid_image_url(data["mermaid_code"])), use_column_width=True)

    with st.expander("Ver código Mermaid"):

        st.code((data["mermaid_code"]), language="mermaid")





def render_finops():

    st.title("ESIC Medellín - FinOps & Observabilidad")

    st.markdown("### Costos, trazas y rendimiento de los LLM")

    summary = finops_summary()

    if summary:

        st.subheader("Resumen por proveedor")

        for provider, data in summary.items():

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Proveedor", provider)

            col2.metric("Llamadas", data["calls"])

            col3.metric("Tokens", data["total_tokens"])

            col4.metric("Costo (USD)", f'${data["total_cost_usd"]:.4f}')



    else:

        st.info("An no hay trazas. Realiza una consulta en el chatbot para generar mtricas.")

    st.subheader("Ultimas trazas")

    traces = get_traces(limit=50)

    if traces:

        df = pd.DataFrame(traces)

        st.dataframe(df, use_container_width=True)

    else:

        st.info("No hay trazas registradas an.")






def render_pdf_propuesta():

    st.title("ESIC Medellín - Propuesta PDF")

    st.markdown("### Escenario 7: Arquitectura, Plan e Impacto")

    st.info("Previsualizacion del PDF pagina a pagina. El PDF oficial se genera fuera de Streamlit.")

    try:

        imagenes = generar_imagenes_pdf(dpi=120)

        for img in imagenes:

            st.image(img, use_column_width=True)

    except Exception as e:

        st.error(f"No se pudo renderizar la previsualizacion: {e}")

        with st.expander("Ver contenido de texto"):

            st.text(preview_pdf_text())


def render_presentacion_ejecutiva():

    st.title("ESIC Medellín - Presentación Ejecutiva")

    st.markdown("### Resumen para directivos")

    try:

        output = Path(__file__).resolve().parent / "presentacion_ejecutiva.pdf"

        from pdf_generator import generar_presentacion_ejecutiva

        generar_presentacion_ejecutiva(str(output))

        st.success(f"PDF guardado: {output}")

        imagenes = generar_imagenes_presentacion_ejecutiva(dpi=150)

        for img in imagenes:

            st.image(img, use_column_width=True)

    except Exception as e:

        st.error(f"No se pudo renderizar la presentacion: {e}")


def _session_expired() -> bool:
    """Verifica inactividad de 15 minutos."""
    last = st.session_state.get("last_activity")
    if last is None:
        return False
    return (datetime.now() - last).total_seconds() > 900


def main():

    if "authenticated" not in st.session_state:

        st.session_state.authenticated = False

    if st.session_state.get("authenticated") and _session_expired():

        st.session_state.authenticated = False

        st.session_state.pop("last_activity", None)

        st.warning("Sesion expirada por inactividad. Vuelve a iniciar sesion.")

    if not st.session_state.authenticated:

        apply_custom_styles()

        if LOGO_PATH.exists():

            c1, c2, c3 = st.columns([1, 2, 1])

            with c2:

                st.image(str(LOGO_PATH), use_column_width=True)

        st.markdown("<h1 style='text-align: center; color: #0044DD;'>ESIC Asistente IA</h1>", unsafe_allow_html=True)

        st.markdown("<h3 style='text-align: center; color: #666;'>Plataforma inteligente para estudiantes, egresados y empresas</h3>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:

            st.markdown("<div class='login-box'>", unsafe_allow_html=True)

            st.subheader("Iniciar sesión")

            creds = get_default_credentials()

            st.caption(f'Usuario: **{creds["username"]}** | Contraseña: **{creds["password"]}**')

            username = st.text_input("Usuario", value=(creds["username"]))

            password = st.text_input("Contraseña", type="password", value=(creds["password"]))

            if st.button("Ingresar", use_container_width=True):

                if check_credentials(username, password):

                    st.session_state.authenticated = True

                    st.rerun()

                else:

                    st.error("Usuario o contraseña incorrectos")

            st.markdown("</div>", unsafe_allow_html=True)

        st.stop()

    st.session_state.last_activity = datetime.now()

    apply_custom_styles()

    ensure_data()

    init_logs_db()

    if "session_id" not in st.session_state:

        st.session_state.session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"

    if "messages" not in st.session_state:

        st.session_state.messages = []

    if "vector_store" not in st.session_state:

        st.session_state.vector_store = None

    if LOGO_PATH.exists():

        c1, c2, c3 = st.columns([1, 2, 1])

        with c2:

            st.image(str(LOGO_PATH), use_column_width=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([

     'Escenario 1: Chatbot', 

     'Escenario 2: Validación de documentos', 

     'Escenario 3: Recomendación', 

     'Escenario 4: Education Analytics', 

     'Escenario 5: Arquitectura', 

     'Escenario 6: FinOps',

     'Escenario 7: Propuesta PDF',

     'Escenario 8: Presentación Ejecutiva'])

    store_name, provider, model, api_key = get_default_config()

    with tab1:

        render_chatbot(store_name, provider, model, api_key)

    with tab2:

        render_document_validator()

    with tab3:

        render_recommender()

    with tab4:

        render_analytics()

    with tab5:

        render_architecture()

    with tab6:

        render_finops()

    with tab7:

        render_pdf_propuesta()

    with tab8:

        render_presentacion_ejecutiva()





if __name__ == "__main__":

    import traceback

    from datetime import datetime

    try:

        main()

    except Exception as e:

        try:

            error_msg = f"[{datetime.now().isoformat()}] ERROR EN STREAMLIT APP\n{type(e).__name__}: {e}\n{traceback.format_exc()}"

            with open("streamlit_error_log.txt", "w", encoding="utf-8") as f:

                f.write(error_msg)

            raise

        finally:

            e = None

            del e



# okay decompiling __pycache__\streamlit_app.cpython-38.pyc

