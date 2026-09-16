import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "dummy_data.json"

# Importaciones opcionales para extracción real
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None


def load_data() -> Dict[str, Any]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class DocumentProcessor:
    """Extrae texto de documentos subidos (PDF, DOCX, TXT, imágenes)."""

    def extract_text(self, file_bytes: bytes, filename: str) -> str:
        ext = filename.split(".")[-1].lower()

        if ext == "txt":
            return file_bytes.decode("utf-8", errors="ignore")

        if ext == "pdf" and PyPDF2:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        if ext == "docx" and docx:
            document = docx.Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in document.paragraphs)

        if ext in ("png", "jpg", "jpeg") and Image and pytesseract:
            image = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(image, lang="spa")

        if ext in ("png", "jpg", "jpeg") and (not Image or not pytesseract):
            return (
                "[OCR no disponible: instala pytesseract y Pillow para procesar imágenes. "
                "En Windows también requiere el binario de Tesseract-OCR.]"
            )

        return f"[Formato {ext} no soportado para extracción automática.]"


class DocumentValidator:
    """Valida solicitudes de admisión contra la base académica."""

    def __init__(self):
        self.data = load_data()
        self.processor = DocumentProcessor()

    def get_solicitud(self, solicitud_id: str) -> Dict:
        for s in self.data.get("solicitudes_admision", []):
            if s["id"] == solicitud_id:
                return s
        return None

    def get_solicitudes(self) -> List[Dict]:
        return self.data.get("solicitudes_admision", [])

    def _extraer_campo(self, texto: str, patron: str) -> str:
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def validar_solicitud(self, solicitud_id: str, file_bytes: bytes = None, filename: str = None) -> Dict:
        solicitud = self.get_solicitud(solicitud_id)
        if not solicitud:
            return {"error": f"Solicitud {solicitud_id} no encontrada"}

        texto_extraido = ""
        if file_bytes and filename:
            texto_extraido = self.processor.extract_text(file_bytes, filename)

        docs = solicitud.get("documentos", {})
        observaciones = []
        estado = "aprobada"

        # Verificar transcript
        transcript = docs.get("transcript", {})
        if not transcript.get("completo"):
            observaciones.append(f"Transcript: {transcript.get('observacion', 'incompleto')}")
            estado = "rechazada" if not texto_extraido else "revisión manual"

        # Verificar cédula
        cedula = docs.get("cedula", {})
        if not cedula.get("valida"):
            observaciones.append(f"Cédula: {cedula.get('observacion', 'no válida')}")
            estado = "rechazada" if not texto_extraido else "revisión manual"

        # Verificar certificado
        certificado = docs.get("certificado", {})
        if not certificado.get("valido"):
            observaciones.append(f"Certificado: {certificado.get('observacion', 'no válido')}")
            estado = "rechazada" if not texto_extraido else "revisión manual"

        # Si hay texto extraido, intentar extraer información y comparar
        info_extraida = {}
        if texto_extraido:
            info_extraida = {
                "nombre_detectado": self._extraer_campo(texto_extraido, r"nombre[\s:]+([A-Za-z\s]+)"),
                "cedula_detectada": self._extraer_campo(texto_extraido, r"cedula[\s:]+(\d+)"),
                "programa_detectado": self._extraer_campo(texto_extraido, r"programa[\s:]+([A-Za-z\s]+)"),
            }

            if info_extraida["nombre_detectado"] and info_extraida["nombre_detectado"].lower() not in solicitud["nombre"].lower():
                observaciones.append("El nombre en el documento no coincide con la solicitud.")
                estado = "revisión manual"

        resultado = {
            "solicitud_id": solicitud_id,
            "estudiante": solicitud["nombre"],
            "cedula": solicitud["cedula"],
            "programa": solicitud["programa"],
            "fecha_solicitud": solicitud["fecha_solicitud"],
            "estado_final": estado,
            "observaciones": observaciones,
            "documentos_revisados": docs,
            "texto_extraido_preview": texto_extraido[:500] if texto_extraido else "",
            "info_extraida": info_extraida,
            "validado_en": datetime.now().isoformat(),
        }

        return resultado

    def generar_reporte(self) -> pd.DataFrame:
        filas = []
        for s in self.get_solicitudes():
            docs = s.get("documentos", {})
            transcript_ok = docs.get("transcript", {}).get("completo", False)
            cedula_ok = docs.get("cedula", {}).get("valida", False)
            certificado_ok = docs.get("certificado", {}).get("valido", False)

            observaciones = []
            if not transcript_ok:
                observaciones.append(docs.get("transcript", {}).get("observacion", "transcript incompleto"))
            if not cedula_ok:
                observaciones.append(docs.get("cedula", {}).get("observacion", "cédula no válida"))
            if not certificado_ok:
                observaciones.append(docs.get("certificado", {}).get("observacion", "certificado no válido"))

            filas.append({
                "ID": s["id"],
                "Nombre": s["nombre"],
                "Cédula": s["cedula"],
                "Programa": s["programa"],
                "Transcript_OK": "OK" if transcript_ok else "Falla",
                "Cedula_OK": "OK" if cedula_ok else "Falla",
                "Certificado_OK": "OK" if certificado_ok else "Falla",
                "Observaciones": "; ".join(observaciones) if observaciones else "Ninguna",
                "Estado": "Aprobada" if (transcript_ok and cedula_ok and certificado_ok) else "Revisión/Rechazada",
            })

        return pd.DataFrame(filas)
