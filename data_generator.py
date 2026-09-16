import json
import random
from pathlib import Path

from real_programs import get_programas

random.seed(42)

AREAS = [
    "Marketing Digital", "Finanzas Corporativas", "Dirección de Proyectos",
    "Inteligencia de Negocios", "Innovación y Emprendimiento", "Gestión Humana",
    "Logística y Cadena de Suministro", "Transformación Digital", "Analítica de Datos",
    "Comercio Internacional", "Derecho Empresarial", "Sostenibilidad"
]

MODALIDADES = ["Presencial", "Virtual", "Híbrida"]

EMPRESAS = [
    "TechMedellín", "Finanzas del Norte", "Global Retail SAS", "Innovasoft",
    "Constructora Andina", "BioSalud", "Energía Verde", "Agroindustrias del Valle",
    "Consultora Estrategia 7", "LogisTrans", "Banco Pacífico", "Seguros La Montaña",
    "Telecomunicaciones Río", "Alimentos del Sur", "Software Axis", "Industrias Metalmec"
]

CARGOS = [
    "Gerente de Marketing", "Analista Financiero", "Director de Proyectos",
    "Especialista en BI", "Coordinador de Innovación", "Jefe de Talento Humano",
    "Analista de Logística", "Consultor Digital", "Científico de Datos Jr",
    "Ejecutivo de Comercio Exterior", "Asesor Legal", "Coordinador de Sostenibilidad"
]

FINANCIAMIENTOS = [
    {"tipo": "Pago de contado", "descripcion": "Descuento del 10% por pago total anticipado."},
    {"tipo": "Financiación directa ESIC", "descripcion": "Hasta 24 cuotas sin intereses con la institución."},
    {"tipo": "Crédito educativo Bancolombia", "descripcion": "Tasa preferencial y plazo hasta 60 meses."},
    {"tipo": "Crédito educativo Davivienda", "descripcion": "Aprobación inmediata para egresados ESIC."},
    {"tipo": "Beca por excelencia académica", "descripcion": "Hasta 40% de descuento según promedio."},
    {"tipo": "Convenio empresarial", "descripcion": "Descuentos especiales para colaboradores de empresas aliadas."},
    {"tipo": "Beca de oportunidades", "descripcion": "Dirigida a egresados desempleados o en búsqueda laboral."},
    {"tipo": "Pago con tarjeta de crédito", "descripcion": "Diferido a 3, 6, 12 o 18 cuotas."},
    {"tipo": "Beca de diversidad", "descripcion": "Apoyo para poblaciones en situación de vulnerabilidad."},
    {"tipo": "Fondo de emprendedores", "descripcion": "Financiación condicionada a presentación de plan de negocio."}
]


def generar_programas(n=50):
    programas = []
    for i in range(1, n + 1):
        area = random.choice(AREAS)
        modalidad = random.choice(MODALIDADES)
        duracion = random.choice(["4 meses", "6 meses", "8 meses", "12 meses", "16 meses"])
        precio = random.randint(8, 45) * 1000000
        programas.append({
            "id": f"PROG-{i:03d}",
            "tipo": "programa",
            "nombre": f"Especialización en {area} {i}",
            "area": area,
            "modalidad": modalidad,
            "duracion": duracion,
            "precio_cop": precio,
            "descripcion": f"Programa especializado en {area} con enfoque práctico, modalidad {modalidad.lower()} y duración de {duracion}.",
            "requisitos": random.choice(["Título profesional", "Técnico o tecnólogo con experiencia", "Egresado de pregrado"])
        })
    return programas


def generar_financiamiento(n=30):
    opciones = []
    for i in range(1, n + 1):
        base = random.choice(FINANCIAMIENTOS)
        opciones.append({
            "id": f"FIN-{i:03d}",
            "tipo": "financiamiento",
            "nombre": f"{base['tipo']} {i}",
            "descripcion": base["descripcion"],
            "beneficio": random.choice(["Sin intereses", "Tasa preferencial", "Aprobación rápida", "Descuento académico"]),
            "requisitos": random.choice(["Ser egresado ESIC", "Carta laboral", "Referido empresarial", "Promedio acumulado >= 4.0"]),
            "vigencia": random.choice(["2026-10", "2026-11", "2026-12", "2027-01"])
        })
    return opciones


def generar_oportunidades(n=50):
    oportunidades = []
    for i in range(1, n + 1):
        cargo = random.choice(CARGOS)
        area = random.choice(AREAS)
        empresa = random.choice(EMPRESAS)
        salario = random.randint(2, 15) * 1000000
        oportunidades.append({
            "id": f"LAB-{i:03d}",
            "tipo": "oportunidad_laboral",
            "cargo": f"{cargo} {i}",
            "empresa": empresa,
            "sector": area,
            "ubicacion": random.choice(["Medellín", "Bogotá", "Cali", "Remoto", "Híbrido"]),
            "salario_min_cop": salario,
            "salario_max_cop": salario + random.randint(1, 5) * 1000000,
            "experiencia": random.choice(["Junior", "Medio", "Senior"]),
            "requisitos": f"Conocimientos en {area.lower()}, trabajo en equipo y orientación a resultados.",
            "publicado": random.choice(["2026-09-01", "2026-09-05", "2026-09-10", "2026-09-12"])
        })
    return oportunidades


def generar_egresados(n=20):
    egresados = []
    for i in range(1, n + 1):
        egresados.append({
            "id": f"EGR-{i:03d}",
            "tipo": "egresado",
            "nombre": f"Egresado {i}",
            "correo": f"egresado{i}@esic.edu.co",
            "programa": random.choice(AREAS),
            "año_graduacion": random.randint(2015, 2025),
            "empleado": random.choice([True, False]),
            "sector_interes": random.choice(AREAS)
        })
    return egresados


def generar_solicitudes_admision(n=25, programas_nombres=None):
    nombres = [
        "Laura Torres", "Julián Gómez", "Andrea Pérez", "Carlos Ruiz", "María Fernández",
        "Pedro Martínez", "Daniela López", "Santiago Vargas", "Valentina Soto", "Juan García",
        "Camila Herrera", "Sebastián Castro", "Natalia Ortiz", "Mateo Gil", "Isabella Romero",
        "Alejandro Díaz", "Luciana Moreno", "Emmanuel Castaño", "Sofía Arango", "Tomás Velásquez",
        "Paula Cárdenas", "Diego Estrada", "Manuela Salazar", "Felipe Molina", "Catalina Ospina"
    ]
    if programas_nombres is None:
        programas_nombres = AREAS
    solicitudes = []
    for i in range(1, n + 1):
        nombre = random.choice(nombres)
        cedula = f"{random.randint(10, 99)}{random.randint(100, 999)}{random.randint(100, 999)}"
        programa = random.choice(programas_nombres)
        # Simulación de inconsistencias aleatorias
        transcript_completo = random.choices([True, False], weights=[0.8, 0.2])[0]
        cedula_valida = random.choices([True, False], weights=[0.9, 0.1])[0]
        certificado_valido = random.choices([True, False], weights=[0.85, 0.15])[0]
        solicitudes.append({
            "id": f"SOL-{i:03d}",
            "tipo": "solicitud_admision",
            "nombre": nombre,
            "cedula": cedula,
            "correo": f"{nombre.lower().replace(' ', '.')}@email.com",
            "programa": f"Especialización en {programa}",
            "fecha_solicitud": random.choice(["2026-08-20", "2026-08-25", "2026-09-01", "2026-09-05", "2026-09-10"]),
            "documentos": {
                "transcript": {
                    "completo": transcript_completo,
                    "observacion": "Transcript sin sello de la universidad" if not transcript_completo else "",
                    "promedio": round(random.uniform(3.2, 4.8), 2),
                },
                "cedula": {
                    "valida": cedula_valida,
                    "observacion": "Cédula escaneada ilegible" if not cedula_valida else "",
                },
                "certificado": {
                    "valido": certificado_valido,
                    "observacion": "Certificado sin firma del rector" if not certificado_valido else "",
                }
            },
            "estado": "pendiente",
            "observaciones_generales": ""
        })
    return solicitudes


def _enriquecer_programas(programas):
    for p in programas:
        p.setdefault("precio_cop", random.randint(15, 60) * 1000000)
        p.setdefault("empleabilidad", random.randint(65, 95))
        p.setdefault("salario_promedio_egresado_cop", random.randint(4, 18) * 1000000)
        p.setdefault("tiempo_colocacion_meses", random.randint(2, 12))
        p.setdefault("vigencia", random.choice(["2026-10", "2026-11", "2026-12", "2027-01", "2027-02"]))
    return programas


def main():
    programas = _enriquecer_programas(get_programas())
    nombres_programas = [p["nombre"] for p in programas]
    financiamiento = generar_financiamiento(30)
    oportunidades = generar_oportunidades(50)
    egresados = generar_egresados(20)
    solicitudes = generar_solicitudes_admision(25, nombres_programas)

    datos = {
        "programas": programas,
        "financiamiento": financiamiento,
        "oportunidades": oportunidades,
        "egresados": egresados,
        "solicitudes_admision": solicitudes,
        "total_registros": len(programas) + len(financiamiento) + len(oportunidades) + len(egresados) + len(solicitudes)
    }

    output = Path(__file__).resolve().parent / "data" / "dummy_data.json"
    output.parent.mkdir(exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(f"Generados {datos['total_registros']} registros dummies en {output}")


if __name__ == "__main__":
    main()
