import base64
import json

# Vistas de arquitectura empresarial del proyecto ESIC en formato Mermaid

ARQUITECTURAS = {
    "empresarial": {
        "titulo": "Arquitectura Empresarial",
        "descripcion": "Vista de alto nivel con los actores, objetivos y procesos principales de ESIC Medellín.",
        "mermaid_code": """
graph TD
    A[Estudiante] -->|Consulta programas| B(Chatbot IA)
    A -->|Solicita admisión| C(Validación documental)
    A -->|Explora opciones| D(Recomendador)
    E[Egresado] -->|Busca empleo| B
    F[Empresa aliada] -->|Publica ofertas| B
    G[Administrativo] -->|Revisa reportes| H[Education Analytics]
    C -->|Alertas| I[Área de admisiones]
    D -->|Sugerencias| A
    H -->|Pronósticos| J[Dirección académica]
        """.strip(),
    },
    "negocios": {
        "titulo": "Arquitectura de Negocios",
        "descripcion": "Procesos de negocio atendidos por la solución: admisiones, atención a egresados y empresas.",
        "mermaid_code": """
graph LR
    subgraph Admisiones
        A1[Recepción documentos] --> A2[OCR + IA]
        A2 --> A3[Validación]
        A3 --> A4{¿Aprobado?}
        A4 -->|Sí| A5[Inscripción]
        A4 -->|No| A6[Revisión manual]
    end
    subgraph Atención
        B1[Consulta] --> B2[RAG + LLM]
        B2 --> B3[Respuesta]
        B3 --> B4{¿Confianza baja?}
        B4 -->|Sí| B5[Derivar asesor]
    end
    subgraph Empleabilidad
        C1[Egresado] --> C2[Recomendación]
        C2 --> C3[Programa + ofertas]
    end
        """.strip(),
    },
    "datos": {
        "titulo": "Arquitectura de Datos",
        "descripcion": "Fuentes de datos, vectorización, almacenamiento y recuperación.",
        "mermaid_code": """
graph TD
    A[Datos ESIC] --> B[Programas reales]
    A --> C[Financiamiento]
    A --> D[Ofertas laborales]
    A --> E[Egresados]
    A --> F[Solicitudes admisión]
    B --> G[Embeddings]
    C --> G
    D --> G
    E --> G
    F --> H[SQLite documental]
    G --> I[Vector Store]
    I --> J[Chroma]
    I --> K[FAISS]
    I --> L[SQLite]
    J --> M[Chatbot RAG]
    K --> M
    L --> M
    M --> N[Respuestas IA]
        """.strip(),
    },
    "soluciones": {
        "titulo": "Arquitectura de Soluciones",
        "descripcion": "Componentes técnicos de la aplicación Streamlit y sus módulos.",
        "mermaid_code": """
graph TD
    A[Streamlit App] --> B[Escenario 1: Chatbot]
    A --> C[Escenario 2: Validación documentos]
    A --> D[Escenario 3: Recomendación]
    A --> E[Escenario 4: Education Analytics]
    A --> F[Escenario 5: Arquitectura]
    B --> G[LLM: OpenAI/Mistral/Groq]
    B --> H[Vector Store]
    C --> I[OCR: PyPDF2/python-docx]
    C --> J[SQLite reportes]
    D --> K[Embeddings + similitud]
    E --> L[pandas + gráficos]
        """.strip(),
    },
    "ciberseguridad": {
        "titulo": "Arquitectura de Ciberseguridad",
        "descripcion": "Gestión de credenciales, control de acceso y buenas prácticas.",
        "mermaid_code": """
graph LR
    A[Usuario] -->|Ingresa clave| B[.streamlit/secrets.toml]
    B --> C[Streamlit Cloud / Local]
    C --> D[OpenAI API]
    C --> E[Mistral API]
    C --> F[Groq API]
    G[Claves] -->|Nunca hardcodeadas| H[Código fuente]
    I[Datos sensibles] --> J[SQLite local]
    J --> K[No versionar secrets]
        """.strip(),
    },
    "integraciones": {
        "titulo": "Arquitectura de Integraciones",
        "descripcion": "Conexiones con CRM, base académica y sistemas Microsoft simulados.",
        "mermaid_code": """
graph TD
    A[ESIC Asistente IA] --> B[CRM]
    A --> C[Base académica]
    A --> D[Microsoft 365]
    B --> E[Leads y contactos]
    C --> F[Programas y notas]
    D --> G[Calendarios]
    D --> H[Documentos SharePoint]
    D --> I[Correos Outlook]
    A --> J[Fuentes reales esic.co / esic.edu]
        """.strip(),
    },
}


def get_architecture_view(nombre: str):
    return ARQUITECTURAS.get(nombre, ARQUITECTURAS["empresarial"])


def list_views():
    return list(ARQUITECTURAS.keys())


def mermaid_image_url(code: str) -> str:
    """Genera una URL de mermaid.ink para renderizar el diagrama como SVG."""
    encoded = base64.b64encode(json.dumps({"code": code, "mermaid": {"theme": "default"}}).encode()).decode()
    return f"https://mermaid.ink/svg/{encoded}"
