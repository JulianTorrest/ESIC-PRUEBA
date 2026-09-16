import json
import random
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "dummy_data.json"

random.seed(42)


class EducationAnalytics:
    def __init__(self):
        self.data = self._load_data()
        self.programas = self.data.get("programas", [])
        self.egresados = self.data.get("egresados", [])
        self.oportunidades = self.data.get("oportunidades", [])

    def _load_data(self) -> Dict[str, Any]:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def program_stats(self, solo_con_egresados: bool = True) -> pd.DataFrame:
        areas_programas = {}
        for p in self.programas:
            area = p.get("area", "Otro")
            areas_programas.setdefault(area, 0)
            areas_programas[area] += 1

        areas_egresados = {}
        for e in self.egresados:
            area = e.get("sector_interes", "Otro")
            areas_egresados.setdefault(area, {"egresados": 0, "empleados": 0})
            areas_egresados[area]["egresados"] += 1
            if e.get("empleado", False):
                areas_egresados[area]["empleados"] += 1

        areas_ofertas = {}
        for o in self.oportunidades:
            area = o.get("sector", "Otro")
            areas_ofertas[area] = areas_ofertas.get(area, 0) + 1

        todas = set(areas_programas) | set(areas_egresados)
        filas = []
        for area in sorted(todas):
            v = areas_egresados.get(area, {"egresados": 0, "empleados": 0})
            if solo_con_egresados and v["egresados"] == 0:
                continue
            tasa = (v["empleados"] / v["egresados"]) * 100 if v["egresados"] > 0 else None
            filas.append({
                "Area": area,
                "Programas": areas_programas.get(area, 0),
                "Egresados": v["egresados"],
                "Empleados": v["empleados"],
                "Tasa empleabilidad (%)": round(tasa, 1) if tasa is not None else None,
                "Ofertas laborales": areas_ofertas.get(area, 0),
            })

        return pd.DataFrame(filas)

    def forecast_demand(self, periodos: int = 4) -> pd.DataFrame:
        filas = []
        for p in self.programas:
            base = random.randint(5, 40)
            tendencia = random.choice([-2, -1, 0, 1, 2, 3])
            pronostico = []
            for t in range(1, periodos + 1):
                valor = max(0, base + tendencia * t + random.randint(-3, 3))
                pronostico.append(valor)

            row = {
                "Programa": p["nombre"],
                "Area": p.get("area", ""),
                "Demanda base": base,
            }
            for i, val in enumerate(pronostico, 1):
                row[f"Año +{i}"] = val

            filas.append(row)

        return pd.DataFrame(filas)

    def predict_student_success(self, carrera: str, habilidades: str) -> Dict[str, Any]:
        habilidades_list = [h.strip().lower() for h in habilidades.split(",") if h.strip()]
        areas_alineadas = [p.get("area", "") for p in self.programas]
        match = any(h in " ".join(areas_alineadas).lower() for h in habilidades_list)

        base_score = random.randint(60, 90)
        if match:
            base_score = min(99, base_score + 10)

        return {
            "carrera": carrera,
            "habilidades_clave": habilidades_list,
            "indice_riesgo_abandono": round(100 - base_score, 1),
            "indice_exito_estimado": round(base_score, 1),
            "recomendacion_intervencion": "Seguimiento académico" if base_score < 75 else "Sin intervención adicional",
        }

    def top_skills_demand(self, n: int = 5) -> pd.DataFrame:
        sectores = [o.get("sector", "Otro") for o in self.oportunidades]
        conteo = {}
        for s in sectores:
            conteo[s] = conteo.get(s, 0) + 1
        top = sorted(conteo.items(), key=lambda x: x[1], reverse=True)[:n]
        return pd.DataFrame(top, columns=["Area", "Ofertas laborales"])
