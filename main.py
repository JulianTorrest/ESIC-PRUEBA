import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sentence_transformers import SentenceTransformer, util

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "esic_automation.db"

# Cargar bases de datos simuladas
with open(DATA_DIR / "knowledge_base.json", encoding="utf-8") as f:
    KB = json.load(f)["entries"]

with open(DATA_DIR / "crm_mock.json", encoding="utf-8") as f:
    CRM = json.load(f)

with open(DATA_DIR / "academic_db.json", encoding="utf-8") as f:
    ACADEMIC = json.load(f)

with open(DATA_DIR / "microsoft_data.json", encoding="utf-8") as f:
    MS_DATA = json.load(f)

# Modelo de embeddings para el chatbot RAG
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

kb_questions = [entry["question"] for entry in KB]
kb_embeddings = MODEL.encode(kb_questions, convert_to_tensor=True)

# Inicializar SQLite para logs y seguimientos
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            message TEXT,
            category TEXT,
            confidence REAL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS follow_ups (
            id TEXT PRIMARY KEY,
            user_type TEXT,
            name TEXT,
            detail TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT,
            status TEXT,
            details TEXT,
            validated_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="ESIC Asistente IA + Automatización")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "static")


def find_best_answer(query: str, top_k: int = 1):
    """Recuperación aumentada (RAG) sobre la base de conocimiento."""
    query_embedding = MODEL.encode(query, convert_to_tensor=True)
    similarities = util.cos_sim(query_embedding, kb_embeddings)[0]
    top_indices = np.argsort(similarities.cpu().numpy())[-top_k:][::-1]
    best_idx = top_indices[0]
    best_score = float(similarities[best_idx])
    return KB[best_idx], best_score


def log_message(session_id: str, role: str, message: str, category: str = None, confidence: float = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_logs (session_id, role, message, category, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, role, message, category, confidence, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat")
async def chat(message: str = Form(...), session_id: str = Form(...), user_type: str = Form("general")):
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    best_match, score = find_best_answer(message)

    # Si la confianza es baja, derivar a humano
    if score < 0.45:
        answer = (
            "No tengo una respuesta automática precisa para tu consulta. "
            "Te estoy derivando con un asesor de ESIC que te contactará en menos de 24 horas."
        )
        category = "derivación"
    else:
        answer = best_match["answer"]
        category = best_match["category"]

    log_message(session_id, "user", message, user_type)
    log_message(session_id, "assistant", answer, category, score)

    return JSONResponse({
        "answer": answer,
        "category": category,
        "confidence": round(score, 3),
        "escalated": score < 0.45,
    })


@app.post("/validate-document")
async def validate_document(document_id: str = Form(...), filename: str = Form(...), checksum: str = Form("")):
    """Simula la validación de un documento contra registros institucionales."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Simulación: aceptar documentos cuyo ID comienza con DOC- o CERT-
    if document_id.upper().startswith(("DOC-", "CERT-")) and len(document_id) > 4:
        status = "validado"
        details = f"Documento {document_id} autenticado correctamente. Registro encontrado en base institucional."
    else:
        status = "rechazado"
        details = f"Documento {document_id} no pudo ser verificado. Verifique el código o contacte a registro."

    cursor.execute(
        "INSERT OR REPLACE INTO documents (id, filename, status, details, validated_at) VALUES (?, ?, ?, ?, ?)",
        (document_id, filename, status, details, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return JSONResponse({"document_id": document_id, "status": status, "details": details})


@app.post("/generate-report")
async def generate_report(report_type: str = Form(...), start_date: str = Form(...), end_date: str = Form(...)):
    """Consolida datos de CRM, académico y Microsoft en un reporte simulado."""
    if report_type not in ("admisiones", "egresados", "empresas", "general"):
        raise HTTPException(status_code=400, detail="Tipo de reporte no soportado")

    # Filtrar leads del CRM por rango de fechas (simulado)
    leads = CRM.get("leads", [])
    filtered = [l for l in leads if start_date <= l["fecha_contacto"] <= end_date]

    # Agregar datos académicos y de Microsoft según el tipo
    academic_summary = {
        "programas_activos": len(ACADEMIC["programas"]),
        "cursos_activos": len(ACADEMIC["cursos_activos"]),
    }
    ms_summary = {
        "eventos_proximos": [e for e in MS_DATA["calendario"] if e["fecha"] >= start_date],
        "documentos_disponibles": len(MS_DATA["documentos"]),
    }

    report = {
        "report_id": str(uuid.uuid4())[:8],
        "type": report_type,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now().isoformat(),
        "leads_count": len(filtered),
        "leads": filtered,
        "academic_summary": academic_summary,
        "microsoft_summary": ms_summary,
    }

    return JSONResponse(report)


@app.post("/follow-up")
async def follow_up(action: str = Form(...), user_type: str = Form(...), name: str = Form(...), detail: str = Form(...)):
    """Crea o consulta seguimientos de casos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if action == "create":
        case_id = f"CAS-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO follow_ups (id, user_type, name, detail, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (case_id, user_type, name, detail, "nuevo", now, now),
        )
        conn.commit()
        conn.close()
        return JSONResponse({"case_id": case_id, "status": "nuevo", "message": "Seguimiento creado exitosamente"})

    if action == "list":
        cursor.execute("SELECT id, user_type, name, detail, status, updated_at FROM follow_ups WHERE name = ? ORDER BY updated_at DESC", (name,))
        rows = cursor.fetchall()
        conn.close()
        return JSONResponse({
            "cases": [
                {"id": r[0], "user_type": r[1], "name": r[2], "detail": r[3], "status": r[4], "updated_at": r[5]}
                for r in rows
            ]
        })

    conn.close()
    raise HTTPException(status_code=400, detail="Acción no soportada. Use 'create' o 'list'.")


@app.post("/data-sync")
async def data_sync():
    """Sincroniza datos de CRM, base académica y sistemas Microsoft."""
    unified = {
        "timestamp": datetime.now().isoformat(),
        "sources": ["crm", "academic_db", "microsoft"],
        "crm_leads": len(CRM.get("leads", [])),
        "academic_programs": len(ACADEMIC.get("programas", [])),
        "microsoft_events": len(MS_DATA.get("calendario", [])),
        "status": "sincronizado",
    }
    return JSONResponse(unified)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "model_loaded": MODEL is not None})
