# -*- coding: utf-8 -*-
"""
Base de conocimiento del asistente (RAG-lite).
20 documentos de referencia (Sección 6 del informe), organizados por categoría y área.
La recuperación es LÉXICA (solapamiento de términos normalizados), sin embeddings ni
ChromaDB, para correr gratis en el entorno serverless. Devuelve documentos citables.
"""
import re
import unicodedata

KB = [
    {"id": "JD_Referencia_Analista_Datos_v2", "categoria": "JD_Referencia", "area": "IT",
     "texto": "Job Description de referencia para Analista de Datos Senior de Business Intelligence. "
              "Requisitos excluyentes: SQL avanzado con joins, CTEs y subqueries; Python para análisis "
              "con pandas y numpy; Power BI o Tableau. Deseables: scikit-learn, experiencia en fintech, inglés intermedio."},
    {"id": "JD_Referencia_Desarrollador_Backend_v1", "categoria": "JD_Referencia", "area": "IT",
     "texto": "Job Description de referencia para Desarrollador Backend. Requisitos: Node.js, PostgreSQL, "
              "Docker, APIs REST y metodologías ágiles (Scrum). Deseables: AWS, TypeScript, testing automatizado."},
    {"id": "JD_Referencia_RRHH_Generalista_v1", "categoria": "JD_Referencia", "area": "RRHH",
     "texto": "Job Description de referencia para Generalista de Recursos Humanos. Requisitos: liquidación "
              "de sueldos, normativa AFIP y SICOSS, administración de personal, altas y bajas."},
    {"id": "JD_Referencia_Analista_Finanzas_v1", "categoria": "JD_Referencia", "area": "Finanzas",
     "texto": "Job Description de referencia para Analista Financiero. Requisitos: SAP FI, presupuestación, "
              "análisis de estados contables, reporting financiero y control de gestión. Deseable Excel avanzado."},
    {"id": "CV_Ejemplo_Data_Senior_Anon", "categoria": "CV_Ejemplo", "area": "IT",
     "texto": "CV de ejemplo anonimizado: Analista de Datos Senior con 7 años de experiencia en SQL, Python, "
              "pandas, Power BI y Tableau, sector financiero."},
    {"id": "CV_Ejemplo_Data_Junior_Anon", "categoria": "CV_Ejemplo", "area": "IT",
     "texto": "CV de ejemplo anonimizado: Analista de Datos Junior con 1,5 años, SQL básico, Excel y Tableau, sin Python."},
    {"id": "CV_Ejemplo_Dev_Backend_Senior_Anon", "categoria": "CV_Ejemplo", "area": "IT",
     "texto": "CV de ejemplo anonimizado: Desarrollador Backend Senior con 5 años en Node.js, PostgreSQL, Docker y AWS."},
    {"id": "CV_Ejemplo_RRHH_Generalista_Anon", "categoria": "CV_Ejemplo", "area": "RRHH",
     "texto": "CV de ejemplo anonimizado: Generalista de RRHH con 4 años en liquidación de sueldos, altas y bajas y clima laboral."},
    {"id": "Glosario_Skills_IT_v1", "categoria": "Glosario_Tecnico", "area": "IT",
     "texto": "Glosario de 80 habilidades de IT con definición y nivel esperado: SQL, Python, JavaScript, React, "
              "Docker, Kubernetes, cloud AWS/Azure, ETL, testing, Git, APIs REST."},
    {"id": "Glosario_Skills_RRHH_v1", "categoria": "Glosario_Tecnico", "area": "RRHH",
     "texto": "Glosario de habilidades de Recursos Humanos: nómina y liquidación, reclutamiento y selección, "
              "onboarding, clima laboral, evaluación de desempeño, normativa laboral."},
    {"id": "Politica_Requisitos_Excluyentes_v2", "categoria": "Politica_RRHH", "area": "Politica",
     "texto": "Política corporativa que define requisito excluyente (imprescindible, sin él no se avanza) versus "
              "requisito deseable (suma pero no bloquea). Si la vacante no marca excluyentes, no se aplican penalizaciones críticas."},
    {"id": "Politica_Umbral_Corte_v1", "categoria": "Politica_RRHH", "area": "Politica",
     "texto": "Política de umbrales de corte por seniority del match score: Junior 50 por ciento, Semi Senior 60, "
              "Senior 70. Zona gris de revisión manual entre 55 y 69 por ciento."},
    {"id": "Politica_Anti_Alucinacion_v1", "categoria": "Politica_RRHH", "area": "Politica",
     "texto": "Política de cero alucinación e inferencia restringida: no inventar habilidades ausentes, pero sí "
              "reconocer habilidades presentes con otra redacción o sinónimo. Distingue Cero Invención de Cero Omisión Injustificada."},
    {"id": "Banco_Preguntas_SQL_v1", "categoria": "Banco_Preguntas", "area": "IT",
     "texto": "Banco de 15 preguntas técnicas de SQL para entrevistas: joins, CTEs, subqueries, índices, "
              "optimización de consultas y modelado de datos."},
    {"id": "Banco_Preguntas_Python_Data_v1", "categoria": "Banco_Preguntas", "area": "IT",
     "texto": "Banco de 12 preguntas de Python para análisis de datos: pandas, numpy, limpieza de datos, "
              "rendimiento y vectorización."},
    {"id": "Banco_Preguntas_Conductuales_STAR_v1", "categoria": "Banco_Preguntas", "area": "General",
     "texto": "Banco de 20 preguntas conductuales con método STAR (Situación, Tarea, Acción, Resultado) para "
              "cualquier rol: liderazgo, trabajo en equipo, resolución de conflictos, manejo de presión."},
    {"id": "JD_Referencia_Marketing_Digital_v1", "categoria": "JD_Referencia", "area": "Marketing",
     "texto": "Job Description de referencia para Especialista en Marketing Digital. Requisitos: Google Analytics, "
              "Meta Ads, Google Ads, SEO, estrategias de marketing y campañas de performance."},
    {"id": "CV_Ejemplo_Marketing_Senior_Anon", "categoria": "CV_Ejemplo", "area": "Marketing",
     "texto": "CV de ejemplo anonimizado: especialista de Marketing Senior con 6 años en Google Ads, Meta Ads, "
              "Salesforce y marketing digital."},
    {"id": "Registro_Errores_Alucinacion_v1", "categoria": "Politica_RRHH", "area": "Politica",
     "texto": "Registro histórico de 10 casos de alucinaciones detectadas en beta con su causa raíz: falsos "
              "positivos por invención y falsos negativos por matching literal (no reconocer sinónimos)."},
    {"id": "Guia_Onboarding_Reclutador_v1", "categoria": "Politica_RRHH", "area": "Politica",
     "texto": "Manual del reclutador: cómo cargar la Job Description y los CVs, interpretar el match score, "
              "configurar el umbral de corte y leer las banderas verdes y rojas."},
]

_STOP = set(
    "de la el los las un una y o u en con para por a al del que se su sus es son como mas menos "
    "sin sobre entre este esta esto ser dos tres anos ano nivel referencia ejemplo".split()
)


def _norm_tokens(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return {t for t in re.findall(r"[a-z0-9]+", text) if len(t) > 2 and t not in _STOP}


def retrieve(query, k=3, area=None):
    """Recuperación léxica: devuelve los k documentos con mayor solapamiento de términos
    con la consulta. Cada resultado incluye un score de relevancia para poder citarlo."""
    q = _norm_tokens(query)
    if not q:
        return []
    scored = []
    for doc in KB:
        if area and doc["area"] != area:
            continue
        d = _norm_tokens(doc["texto"] + " " + doc["id"])
        overlap = len(q & d)
        if overlap:
            score = overlap / (len(q) ** 0.5 + 1.0)
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"id": doc["id"], "categoria": doc["categoria"], "area": doc["area"],
             "texto": doc["texto"], "score": round(score, 3)} for score, doc in scored[:k]]
