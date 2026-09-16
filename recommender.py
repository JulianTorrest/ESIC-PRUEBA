import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "dummy_data.json"


class ProgramRecommender:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)
        self.data = self._load_data()
        self.programas = self.data.get("programas", [])
        self.egresados = self.data.get("egresados", [])
        self._precompute_embeddings()

    def _load_data(self) -> Dict[str, Any]:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _precompute_embeddings(self):
        texts = [self._program_text(p) for p in self.programas]
        self.program_embeddings = self.model.encode(texts, convert_to_numpy=True)

    @staticmethod
    def _program_text(program: Dict) -> str:
        return (
            f"Nombre: {program.get('nombre', '')}. "
            f"Área: {program.get('area', '')}. "
            f"Nivel: {program.get('nivel', '')}. "
            f"Modalidad: {program.get('modalidad', '')}. "
            f"Duración: {program.get('duracion', '')}. "
            f"Descripción: {program.get('descripcion', '')}"
        )

    def _empleabilidad_score(self, area: str) -> Dict[str, Any]:
        total = [e for e in self.egresados if e.get("sector_interes") == area or e.get("programa") == area]
        empleados = [e for e in total if e.get("empleado", False)]
        if not total:
            return {"tasa_empleo": 0.0, "muestra": 0, "salario_promedio": 0}
        tasa = len(empleados) / len(total)
        salarios = []
        return {"tasa_empleo": tasa, "muestra": len(total), "salario_promedio": 0}

    @staticmethod
    def _nivel_match(tipo_buscado: str, nivel_programa: str) -> float:
        pregrados = ["pregrado"]
        posgrados = ["maestría", "máster", "master", "especialización", "executive", "ejecutivo", "posgrado", "permanente", "universitario"]
        nb = tipo_buscado.lower()
        np = nivel_programa.lower()

        if any(t in np for t in pregrados):
            return 1.0 if "pregrado" in nb else 0.0
        if any(t in np for t in posgrados):
            return 1.0 if any(t in nb for t in ["posgrado", "maestría", "máster", "master", "especialización"]) else 0.0
        return 0.5

    def recommend(self, perfil: Dict, n: int = 3) -> List[Dict]:
        habilidades = perfil.get("habilidades", "")
        intereses = perfil.get("intereses", "")
        carrera = perfil.get("carrera", "")
        tipo_buscado = perfil.get("tipo_programa_buscado", "")

        partes = [f"Habilidades: {habilidades}", f"Intereses: {intereses}", f"Carrera anterior: {carrera}"]
        if perfil.get("programa_pregrado"):
            partes.append(f"Programa de pregrado: {perfil['programa_pregrado']}")
        if perfil.get("experiencia_anos"):
            partes.append(f"Años de experiencia: {perfil['experiencia_anos']}")
        if perfil.get("sector_economico"):
            partes.append(f"Sector económico: {perfil['sector_economico']}")
        if perfil.get("pais_origen"):
            partes.append(f"País: {perfil['pais_origen']}")

        perfil_text = ". ".join(partes)
        perfil_emb = self.model.encode([perfil_text], convert_to_numpy=True)

        similarities = np.dot(self.program_embeddings, perfil_emb.T).flatten()

        combined = []
        for idx, sim in enumerate(similarities):
            program = self.programas[idx]
            match = self._nivel_match(tipo_buscado, program.get("nivel", ""))
            final_score = float(sim) * (0.6 + 0.4 * match)
            combined.append((idx, final_score, match))

        combined.sort(key=lambda x: x[1], reverse=True)

        resultados = []
        for idx, score, match in combined[:n]:
            program = self.programas[idx]
            empleo = self._empleabilidad_score(program.get("area", ""))
            razonamiento = (
                f"Este programa coincide con tu perfil porque aborda {program.get('area', 'esta área')}, "
                f"relacionado con tus intereses en '{intereses}'. "
                f"La modalidad es {program.get('modalidad', '')} con duración de {program.get('duracion', '')}. "
            )
            if match >= 1.0:
                razonamiento += f"Es una opción de {program.get('nivel', '')}, acorde con tu búsqueda. "
            if empleo["muestra"] > 0:
                razonamiento += f"Además, la tasa de empleabilidad histórica de egresados en este sector es del {empleo['tasa_empleo']*100:.0f}% en la muestra disponible."
            else:
                razonamiento += "No hay datos de egresados suficientes para calcular empleabilidad, pero la formación está alineada con tu perfil."

            resultados.append({
                "programa": program,
                "score_similitud": score,
                "empleabilidad": empleo,
                "razonamiento": razonamiento,
            })

        return resultados
