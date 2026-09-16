# ESIC Medellín - Asistente IA: 7 Escenarios de Automatización

## Escenario 1: Chatbot Inteligente para Egresados

### Contexto Escenario 1

ESIC Medellín recibe diariamente consultas de egresados interesados en programas de especialización, opciones de financiamiento y oportunidades laborales. El objetivo es atender estas consultas con IA generativa, recuperando información de múltiples fuentes y escalando a un asesor humano cuando sea necesario.

### Reto Escenario 1

Diseñar e implementar un chatbot inteligente que:

- Responda consultas complejas usando IA generativa (LLM).
- Acceda a información de programas, financiamiento y oportunidades laborales.
- Derive a un agente humano si es necesario, con el contexto completo.
- Registre la interacción para análisis posterior.
- Utilice una base de datos vectorial para recuperación de información.

## Escenario 2: Automatización de Validación de Documentos

### Contexto Escenario 2

El área de admisiones recibe solicitudes con documentos que requieren validación (transcripts, cédula, certificados). Actualmente un empleado revisa manualmente ~2 horas por 20 solicitudes.

### Reto Escenario 2

- Procesar documentos automáticamente (OCR + análisis con IA).
- Validar integridad y completitud.
- Extraer información clave.
- Generar reportes y alertas de inconsistencias.
- Integrar con el sistema académico.

## Solución propuesta: `ESIC Asistente IA`

### Componentes principales

1. **Chatbot con IA Generativa (RAG + LLM)**
   - Recuperación aumentada (RAG) sobre datos de programas, financiamiento y empleos.
   - Generación de respuestas naturales con LLM real (OpenAI) o plantilla local de respaldo.
   - Derivación automática a asesor humano cuando la confianza es baja.

2. **Bases de datos vectoriales**
   - **Chroma**: persistente y eficiente.
   - **FAISS**: búsqueda rápida por similitud.
   - **SQLite**: implementación propia con embeddings.

3. **Datos**
   - **15 programas reales de ESIC** (Colombia y España) obtenidos de `esic.co` y `esic.edu`.
   - Financiamiento, oportunidades laborales, egresados y solicitudes de admisión son datos ilustrativos generados localmente, listos para reemplazar por conectores reales.

4. **Validación de documentos (Escenario 2)**
   - Extracción automática de texto (PDF, DOCX, TXT e imágenes con OCR).
   - Validación de completitud e integridad.
   - Reportes descargables en CSV con alertas.

5. **Registro de interacciones**
   - SQLite con logs de conversación, escalamientos y validaciones.
   - Análisis posterior de consultas y métricas.

### Arquitectura

```text
Egresado
  │
  ▼
Streamlit UI
  │
  ▼
Chatbot
  │
  ├── RAG ──► Vector Store (Chroma / FAISS / SQLite)
  │           └── Embeddings (sentence-transformers)
  │
  ├── LLM ──► OpenAI (si hay API key)
  │           └── Respuesta local con contexto
  │
  ├── Derivación ──► Registro en SQLite
  │
  └── Logs ──► SQLite (interactions.db)
```

## Estructura del prototipo

```text
ESIC JULIAN TORRES/
├── README.md
├── requirements.txt
├── streamlit_app.py          # Aplicación principal con tabs
├── real_programs.py          # Programas reales de ESIC
├── data_generator.py         # Generador de datos
├── vector_store.py           # Implementaciones Chroma, FAISS y SQLite
├── document_validator.py     # Validación de documentos de admisión
├── recommender.py            # Sistema de recomendación de programas
├── education_analytics.py    # Analítica y pronósticos educativos
├── architecture_view.py      # Vistas de arquitectura empresarial en Mermaid
├── observability.py          # Trazas, FinOps, rate limits y feedback
├── cache.py                  # Caché de respuestas (Redis/SQLite)
├── auth.py                   # Autenticación básica
├── ui.py                     # Estilos y mejoras UX/UI
├── precargar_bases.py        # Precarga de datos y bases vectoriales
├── llm_service.py            # Servicio de IA generativa (OpenAI, Mistral, Groq, local)
├── .streamlit/
│   └── secrets.toml          # API keys (no subir a git)
├── data/
│   └── dummy_data.json       # Datos generados (programas reales + datos ilustrativos)
└── data/chroma_db/           # Persistencia Chroma (generado)
```

## Instalación

```bash
pip install -r requirements.txt
```

> **Nota:** Para usar un LLM real (OpenAI, Mistral o Groq), edita `.streamlit/secrets.toml` con tus claves. También puedes ingresarlas manualmente en la barra lateral. Si no hay clave, el sistema usa respuestas generadas localmente con el contexto recuperado.

## Ejecución

Generar y precargar datos y bases vectoriales (recomendado para evitar esperas al iniciar Streamlit):

```bash
python precargar_bases.py
```

Ejecutar la app:

```bash
streamlit run streamlit_app.py
```

Abre la URL que muestra la terminal (por defecto `http://localhost:8501`).

## Funciones principales

- **Chat inteligente (Escenario 1)**: responde sobre programas, financiamiento y empleos.
- **Selector de vector store**: alterna entre Chroma, FAISS y SQLite desde la barra lateral.
- **Proveedores de LLM**: OpenAI, Mistral, Groq o respuesta local.
- **Gestión segura de claves**: `secrets.toml` para OpenAI, Mistral y Groq.
- **Validación de documentos (Escenario 2)**: extrae, valida y reporta solicitudes de admisión.
- **OCR y extracción**: PDF, DOCX, TXT e imágenes.
- **Reportes de inconsistencias**: descargable en CSV.
- **Recomendación de programas (Escenario 3)**: analiza perfil del estudiante y sugiere programas con explicación.
- **Education Analytics (Escenario 4)**: empleabilidad, pronóstico de demanda, éxito estudiantil y top áreas.
- **Arquitectura Empresarial (Escenario 5)**: vistas de arquitectura en Mermaid (empresarial, negocios, datos, soluciones, ciberseguridad, integraciones).
- **FinOps & Observabilidad (Escenario 6)**: trazas, costos por proveedor, tokens, latencia y métricas de uso.
- **Evaluación de usuario (Escenario 7)**: feedback util / no util sobre las respuestas del chatbot.
- **Fallback automático entre LLM**: si un proveedor falla, intenta con el siguiente.
- **Caché de respuestas**: Redis o SQLite para reducir costos y latencia.
- **Rate limit avanzado**: ventanas deslizantes por sesión e IP, con límite por minuto y por hora.
- **Autenticación básica**: contraseña configurable en `secrets.toml` y expiración de sesión por inactividad.
- **Seguridad del chat**: validación de PII, prompt injection, lenguaje inapropiado y temas permitidos.
- **Sanitización RAG**: eliminación de datos sensibles del contexto y de las respuestas.
- **Moderación externa**: integración con OpenAI Moderation cuando se usa proveedor OpenAI.
- **Derivación a humano**: registra el caso con el contexto completo.
- **Registro de interacciones**: guarda mensajes y escalamientos para análisis.

## Branding

La interfaz utiliza el logo institucional `Logo.png` y los colores de ESIC:

- **Fondo**: blanco (`#ffffff`).
- **Color principal**: azul ESIC (`#0044DD`).
- **Títulos, botones y pestañas**: azul institucional.

## Métricas esperadas

- Reducción del 70% en consultas manuales repetitivas de egresados.
- Tiempo de respuesta < 2 segundos para el 90% de las consultas.
- Disponibilidad 24/7 para consultas de primer nivel.
