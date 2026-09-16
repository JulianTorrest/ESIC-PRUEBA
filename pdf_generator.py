import base64
import io
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from fpdf import FPDF


def _descargar_diagrama_mermaid(code: str) -> bytes:
    """Descarga la imagen de un diagrama Mermaid desde mermaid.ink."""
    encoded = base64.b64encode(json.dumps({"code": code, "mermaid": {"theme": "default"}}).encode()).decode()
    url = f"https://mermaid.ink/img/{encoded}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()
    except Exception:
        return b""


class _PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.set_text_color(0, 68, 221)
        self.cell(0, 10, "ESIC Medellin - Propuesta de Asistente IA", ln=True, align="C")
        self.ln(2)
        self.set_draw_color(0, 68, 221)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 68, 221)
        self.cell(0, 10, title, ln=True)
        self.ln(2)

    def chapter_subtitle(self, subtitle):
        self.set_font("Arial", "B", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, subtitle, ln=True)
        self.ln(1)

    def body_text(self, text):
        self.set_font("Arial", "", 10)
        self.set_text_color(0, 0, 0)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5, text, ln=1)
        self.ln(2)

    def bullet_list(self, items):
        self.set_font("Arial", "", 10)
        self.set_text_color(0, 0, 0)
        for item in items:
            self.set_x(self.l_margin)
            self.multi_cell(0, 5, f"- {item}", ln=1)
        self.ln(2)


def _add_fonts(pdf):
    """Registra Arial del sistema para soportar tildes."""
    if not hasattr(pdf, "fonts_added"):
        try:
            pdf.add_font("Arial", "", r"C:\Windows\Fonts\arial.ttf", uni=True)
            pdf.add_font("Arial", "B", r"C:\Windows\Fonts\arialbd.ttf", uni=True)
        except Exception:
            pass
        pdf.fonts_added = True


def generar_pdf_propuesta(output_path: str = "propuesta_esic_ia.pdf") -> str:
    if FPDF is None:
        raise RuntimeError("fpdf2 no esta instalado. Ejecuta: pip install fpdf2")

    pdf = _PDF()
    _add_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Portada
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(0, 68, 221)
    pdf.cell(0, 40, "Propuesta: Asistente IA para ESIC Medellin", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="C")
    pdf.ln(20)

    # 1. Arquitectura de la Solucion
    pdf.chapter_title("1. Arquitectura de la Solucion")

    pdf.chapter_subtitle("1.1 Componentes principales")
    pdf.body_text(
        "La plataforma ESIC Asistente IA integra los siguientes componentes: "
        "Interfaz Streamlit para experiencia de usuario, multiples bases de datos vectoriales "
        "(Chroma, FAISS, SQLite) para recuperacion de informacion, modelos de lenguaje "
        "(OpenAI, Mistral, Groq, local) para generacion de respuestas, servicio de recomendacion "
        "con SentenceTransformers, validador de documentos, analitica educativa, observabilidad "
        "FinOps y modulo de arquitectura empresarial."
    )

    pdf.chapter_subtitle("1.2 Flujo de datos")
    pdf.bullet_list([
        "El egresado ingresa su consulta en la interfaz Streamlit.",
        "La consulta se valida por seguridad: PII, prompt injection y temas permitidos.",
        "Se recuperan los documentos mas relevantes desde el vector store seleccionado.",
        "El contexto recuperado se sanitiza y se envia al LLM o a plantillas locales.",
        "La respuesta generada se valida, se sanitiza y se presenta al usuario.",
        "Trazas, costos y feedback se registran en SQLite para observabilidad."
    ])

    pdf.chapter_subtitle("1.3 Tecnologias seleccionadas y justificacion")
    pdf.bullet_list([
        "Streamlit: rapido prototipado web sin frontend complejo.",
        "SentenceTransformers: embeddings locales eficientes y economicos.",
        "Chroma / FAISS / SQLite: flexibilidad para pruebas, produccion y entornos sin GPU.",
        "OpenAI / Mistral / Groq: opciones de LLM segun presupuesto y latencia.",
        "SQLite: almacenamiento de logs, trazas, FinOps y escalamientos sin infraestructura adicional."
    ])

    pdf.chapter_subtitle("1.4 Consideraciones de seguridad y escalabilidad")
    pdf.bullet_list([
        "Validacion de PII, prompt injection, lenguaje inapropiado y temas permitidos.",
        "Rate limiting con ventanas deslizantes por sesion e IP.",
        "Expiracion de sesion por inactividad.",
        "Sanitizacion de contexto RAG y respuestas.",
        "Claves en secrets.toml, nunca expuestas en logs.",
        "Arquitectura modular: cada escenario puede escalarse o reemplazarse de forma independiente."
    ])

    pdf.chapter_subtitle("1.5 Vistas de arquitectura empresarial")
    pdf.body_text(
        "Las vistas Mermaid incluidas en la aplicacion cubren: "
        "Vista Empresarial (objetivos de negocio), Vista de Negocio (procesos y actores), "
        "Vista de Datos (fuentes y persistencia), Vista de Solucion (componentes tecnicos), "
        "Vista de Ciberseguridad (controles y flujos seguros) y Vista de Integraciones "
        "(conectores con sistemas externos). Cada vista permite comunicar la solucion a "
        "diferentes stakeholders tecnicos y de negocio."
    )

    from architecture_view import ARQUITECTURAS

    for key, data in ARQUITECTURAS.items():
        pdf.chapter_subtitle(data["titulo"])
        img_bytes = _descargar_diagrama_mermaid(data["mermaid_code"])
        if img_bytes:
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes))
            w_px, h_px = img.size
            max_w = 180
            max_h = 120
            ratio = h_px / w_px
            w_mm = max_w
            h_mm = w_mm * ratio
            if h_mm > max_h:
                h_mm = max_h
                w_mm = h_mm / ratio
            if pdf.get_y() + h_mm + 20 > 270:
                pdf.add_page()
            x = (pdf.w - w_mm) / 2
            pdf.image(img, x=x, w=w_mm)
        else:
            pdf.body_text(f"Diagrama {data['titulo']} no pudo descargarse. Codigo Mermaid: {data['mermaid_code'][:80]}...")

    # 2. Plan de Implementacion
    pdf.add_page()
    pdf.chapter_title("2. Plan de Implementacion")

    pdf.chapter_subtitle("2.1 Fases")
    pdf.bullet_list([
        "Fase 1 - Analisis y diseno: levantamiento de requerimientos, definicion de arquitectura, datos y seguridad.",
        "Fase 2 - MVP: chatbot RAG, validacion de documentos, recomendador y primeros dashboards.",
        "Fase 3 - Piloto: despliegue con usuarios reales, ajustes de prompts y metricas.",
        "Fase 4 - Escalamiento: optimizacion de costos, integracion con sistemas institucionales y gobierno de datos."
    ])

    pdf.chapter_subtitle("2.2 Timeline estimado")
    pdf.bullet_list([
        "Semanas 1-2: analisis, datos y arquitectura base.",
        "Semanas 3-6: desarrollo del MVP funcional.",
        "Semanas 7-8: pruebas internas y piloto con 20 usuarios.",
        "Semanas 9-12: iteraciones, optimizacion y despliegue a produccion."
    ])

    pdf.chapter_subtitle("2.3 Recursos necesarios")
    pdf.bullet_list([
        "1 Data Scientist / ML Engineer.",
        "1 Backend / DevOps para despliegue y observabilidad.",
        "1 UX/UI o Product Owner para ajuste de interfaz.",
        "Infraestructura: servidor Streamlit, base SQLite o Postgres, acceso a APIs de LLM."
    ])

    pdf.chapter_subtitle("2.4 Riesgos y mitigacion")
    pdf.bullet_list([
        "Alucinaciones del LLM: mitigacion con RAG estricto, confianza < 0.45 deriva a humano.",
        "Costos de API: cache de respuestas, rate limits y proveedor local como fallback.",
        "Seguridad y privacidad: sanitizacion de datos, no persistir PII, auditoria completa.",
        "Adopcion de usuarios: piloto gradual, feedback continuo y capacitacion."
    ])

    # 3. Evaluacion de Impacto
    pdf.add_page()
    pdf.chapter_title("3. Evaluacion de Impacto")

    pdf.chapter_subtitle("3.1 Reduccion de tiempo/costos estimada")
    pdf.body_text(
        "Se estima una reduccion del 70% en consultas manuales repetitivas de egresados. "
        "La validacion de documentos puede reducir de 2 horas por 20 solicitudes a unos pocos minutos. "
        "El tiempo promedio de respuesta es menor a 2 segundos para el 90% de las consultas."
    )

    pdf.chapter_subtitle("3.2 Beneficios para usuarios")
    pdf.bullet_list([
        "Atencion 24/7 para consultas de primer nivel.",
        "Recomendaciones personalizadas de programas segun perfil del estudiante.",
        "Tiempos de respuesta consistentes y menor carga para el equipo de admisiones.",
        "Visibilidad de empleabilidad, demanda y costos para toma de decisiones."
    ])

    pdf.chapter_subtitle("3.3 Metricas de exito")
    pdf.bullet_list([
        "Tiempo de respuesta < 2 segundos en el 90% de consultas.",
        "Satisfaccion del usuario > 4/5 basada en feedback util/no util.",
        "Tasa de escalamiento a humano < 15%.",
        "Disponibilidad 24/7 del chatbot y dashboards."
    ])

    pdf.chapter_subtitle("3.4 ROI aproximado")
    pdf.body_text(
        "Con un ahorro estimado de 2-3 horas diarias del equipo de admisiones y egresados, "
        "el retorno de inversion se proyecta en 6-9 meses considerando costos de APIs, infraestructura "
        "y mantenimiento. La disponibilidad 24/7 y la escalabilidad del asistente aumentan el "
        "alcance sin incremento lineal de personal."
    )

    if output_path is None:
        return bytes(pdf.output(dest="S"))

    pdf.output(output_path)
    return os.path.abspath(output_path)


def generar_imagenes_pdf(dpi: int = 150):
    """Genera el PDF y devuelve una lista de imagenes PNG (una por pagina)."""
    try:
        import fitz
    except ImportError:
        raise RuntimeError("pymupdf no esta instalado. Ejecuta: pip install pymupdf")

    pdf_bytes = generar_pdf_propuesta(None)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    imagenes = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        imagenes.append(pix.tobytes("png"))
    doc.close()
    return imagenes


def generar_presentacion_ejecutiva(output_path: str = None):
    """Genera un PDF de presentacion ejecutiva de maximo 2 parrafos."""
    pdf = _PDF()
    _add_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Portada
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(0, 68, 221)
    pdf.cell(0, 40, "Presentacion Ejecutiva", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Asistente IA para ESIC Medellin", ln=True, align="C")
    pdf.ln(15)

    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0)
    parrafo1 = (
        "ESIC Medellin se enfrenta a una creciente demanda de atencion por parte de estudiantes, "
        "egresados y empresas aliadas, que consultan diariamente sobre programas de especializacion, "
        "financiamiento, admisiones y oportunidades laborales. La propuesta de Asistente IA centraliza "
        "estas interacciones en una plataforma unica disponible 24/7, reduciendo la carga operativa del "
        "equipo de admisiones y egresados, mejorando la experiencia del usuario y acelerando los tiempos "
        "de respuesta con informacion precisa y personalizada."
    )
    parrafo2 = (
        "El proyecto se sienta sobre una arquitectura modular segura: chatbot con RAG, validacion de "
        "documentos, recomendador de programas, analitica educativa, observabilidad FinOps y multiples "
        "vistas de arquitectura empresarial. Se estima una reduccion del 70% en consultas manuales, un "
        "retorno de inversion entre 6 y 9 meses, y un escalamiento controlado que permite integrar datos "
        "reales de la institucion sin exponer informacion sensible."
    )
    pdf.multi_cell(0, 7, parrafo1)
    pdf.ln(5)
    pdf.multi_cell(0, 7, parrafo2)

    # Segunda pagina - Cifras clave
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 68, 221)
    pdf.cell(0, 15, "Cifras y proyeccion de impacto", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(
        0, 7,
        "La implementacion se divide en cuatro fases de 12 semanas: analisis, MVP, piloto y escalamiento. "
        "Se espera reducir en un 70% las consultas manuales, lograr tiempos de respuesta menores a 2 segundos "
        "en el 90% de los casos y mantener una tasa de escalamiento a asesores humanos inferior al 15%. "
        "El retorno de inversion se proyecta entre 6 y 9 meses."
    )
    pdf.ln(8)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Metricas de exito", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 7, "- Disponibilidad 24/7 del asistente.\n- Satisfaccion del usuario mayor a 4/5.\n- Reduccion de 2-3 horas diarias en atencion manual.\n- Escalamiento controlado sin incremento lineal de personal.")

    if output_path is None:
        return bytes(pdf.output(dest="S"))

    pdf.output(output_path)
    return os.path.abspath(output_path)


def generar_imagenes_presentacion_ejecutiva(dpi: int = 150):
    """Genera la presentacion ejecutiva y devuelve imagenes PNG de sus paginas."""
    try:
        import fitz
    except ImportError:
        raise RuntimeError("pymupdf no esta instalado. Ejecuta: pip install pymupdf")

    pdf_bytes = generar_presentacion_ejecutiva(None)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    imagenes = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        imagenes.append(pix.tobytes("png"))
    doc.close()
    return imagenes


def preview_pdf_text() -> str:
    """Devuelve un texto plano con el contenido del PDF para previsualizar."""
    return """Propuesta: Asistente IA para ESIC Medellin

1. Arquitectura de la Solucion
- Componentes principales: Streamlit, vector stores (Chroma/FAISS/SQLite), LLM providers, recomendador, validador de documentos, analytics, FinOps.
- Flujo de datos: consulta -> validacion de seguridad -> recuperacion RAG -> sanitizacion -> LLM/local -> respuesta validada -> logs.
- Tecnologias: SentenceTransformers, SQLite, OpenAI/Mistral/Groq, pandas.
- Seguridad y escalabilidad: rate limits, expiracion de sesion, sanitizacion, PII filtering, modulo escalable.
- Vistas de arquitectura: Empresarial, Negocio, Datos, Solucion, Ciberseguridad, Integraciones.

2. Plan de Implementacion
- Fases: Analisis, MVP, Piloto, Escalamiento.
- Timeline: 12 semanas.
- Recursos: ML Engineer, Backend, Product Owner, infraestructura.
- Riesgos: alucinaciones, costos, seguridad, adopcion.

3. Evaluacion de Impacto
- Reduccion del 70% en consultas manuales.
- Beneficios: atencion 24/7, recomendaciones personalizadas, menor carga administrativa.
- Metricas: <2s respuesta, >4/5 satisfaccion, <15% escalamiento.
- ROI: 6-9 meses estimados.
"""
