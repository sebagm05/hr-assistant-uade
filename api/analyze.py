import json
import os
from http.server import BaseHTTPRequestHandler
from groq import Groq

SYSTEM_PROMPT = """ROL: Eres un Asistente Experto en Adquisición de Talento y Evaluación Técnica.
OBJETIVO: Analizar perfiles de manera estrictamente objetiva y libre de sesgos.
RESTRICCIONES ABSOLUTAS:
1. No inferirás habilidades no escritas explícitamente en los documentos.
2. Si una habilidad no aparece en el CV: "No especificado en el documento".
3. No emitas juicios de valor sobre la persona. Solo evalúa el perfil documentado.
4. Responde ÚNICAMENTE en español con JSON válido, sin texto adicional, sin bloques markdown.
5. Temperatura efectiva: 0.
TONO: Profesional, directo y corporativo.
PROPÓSITO: Optimizar la toma de decisiones del reclutador humano, quien siempre tiene la decisión final."""


def clean_json(text):
    return text.replace("```json", "").replace("```", "").strip()


def build_prompt(step, cv, jd, ctx):
    if step == "t1":
        return f"""TAREA: Extracción de Entidades del Perfil Profesional.
CV: {cv}
Devuelve SOLO este JSON exacto:
{{"anos_experiencia_total": "<número o No especificado>", "ultimo_rol": "<string>", "hard_skills": ["..."], "soft_skills": ["..."], "nivel_educativo": "<string>", "certificaciones": ["..."], "confianza_extraccion": "Alta|Media|Baja", "nota_confianza": "<string>"}}
REGLA: Incluye solo lo que esté escrito literalmente en el CV. No inferas."""

    elif step == "t2":
        t1 = ctx.get("t1", {})
        return f"""TAREA: Análisis de Brechas y Match entre CV y Job Description.
Datos CV (output T1): {json.dumps(t1, ensure_ascii=False)}
Job Description: {jd}
Devuelve SOLO este JSON exacto:
{{"match_fuerte": [{{"skill": "<string>", "evidencia_en_cv": "<cita textual del CV>"}}], "brechas_excluyentes": [{{"requisito": "<string>", "severidad": "Crítica", "presente_en_cv": false}}], "brechas_deseables": [{{"requisito": "<string>", "severidad": "Moderada", "presente_en_cv": false}}]}}
MATCHING SEMÁNTICO (obligatorio): Compará por SIGNIFICADO, no solo por texto literal. Si el CV cumple un requisito del JD aunque esté escrito con otras palabras, va en match_fuerte, NO en brechas. Ejemplos de equivalencia válida: "Inglés técnico (lectura)" ≈ "Inglés técnico para leer documentación"; "JS" ≈ "JavaScript"; "BI" ≈ "Business Intelligence"; "consultas SQL con CTEs y joins" ≈ "SQL avanzado". Solo declarás una brecha si el requisito NO está cubierto ni de forma explícita ni equivalente.
REGLA: evidencia_en_cv debe ser cita textual del CV. Sin cita posible = no va en match_fuerte."""

    elif step == "t3":
        t2 = ctx.get("t2", {})
        return f"""TAREA: Cálculo de Match Score.
Output T2: {json.dumps(t2, ensure_ascii=False)}
Ponderación: base 100, cada brecha_excluyente Crítica descuenta 20 pts, cada brecha_deseable Moderada descuenta 5 pts, bonus +5 por skills adicionales verificables en el CV. Mínimo 0.
Umbrales de recomendación (aplicalos exactamente según el match_score calculado): score >= 70 -> "Avanzar a entrevista"; score entre 55 y 69 -> "Revisión manual"; score < 55 -> "Descartar".
Devuelve SOLO este JSON exacto:
{{"match_score": 0, "recomendacion": "Avanzar a entrevista|Revisión manual|Descartar", "umbral_aplicado": 70, "justificacion_score": "<máx 3 líneas>", "penalizaciones_aplicadas": [{{"requisito": "<string>", "descuento": 0}}]}}"""

    elif step == "t4":
        t2 = ctx.get("t2", {})
        t3 = ctx.get("t3", {})
        return f"""TAREA: Diseño de Guía de Entrevista Personalizada.
CV: {cv}
Output T2: {json.dumps(t2, ensure_ascii=False)}
Output T3: {json.dumps(t3, ensure_ascii=False)}
Devuelve SOLO este JSON exacto:
{{"preguntas": [{{"tipo": "Técnica", "pregunta": "<string>", "que_buscar": "<string>"}}, {{"tipo": "Brecha", "pregunta": "<string>", "que_buscar": "<string>"}}, {{"tipo": "Conductual STAR", "pregunta": "<string>", "que_buscar": "<string>"}}, {{"tipo": "Situacional", "pregunta": "<string>", "que_buscar": "<string>"}}]}}
REGLA: Cada pregunta debe nombrar un logro o herramienta específica del CV."""

    elif step == "val":
        t2 = ctx.get("t2", {})
        t3 = ctx.get("t3", {})
        t4 = ctx.get("t4", None)
        return f"""TAREA: Auditoría de Calidad y Control Anti-Alucinaciones.
CV original: {cv}
Output T2: {json.dumps(t2, ensure_ascii=False)}
Output T3: {json.dumps(t3, ensure_ascii=False)}
Output T4: {json.dumps(t4, ensure_ascii=False) if t4 else "No aplica"}
Controles (PASA = sin problema, FALLA = se detectó el problema):
- control_1: ¿Hay alguna skill en match_fuerte que NO esté escrita en el CV? (si la hay, FALLA)
- control_2: ¿El score se basó en alguna suposición externa al texto del CV? (si la hay, FALLA)
- control_3: ¿Todas las preguntas de entrevista referencian el CV? (si alguna es genérica, FALLA)
- control_4: ¿Hay alguna brecha (excluyente o deseable) que en realidad SÍ figura en el CV con redacción distinta o equivalente? (si encontrás una brecha falsa, FALLA)
Si algún control da FALLA, el veredicto debe ser "Requiere corrección." y explicá cuál en observaciones.
Devuelve SOLO este JSON exacto:
{{"control_1": "PASA|FALLA", "control_2": "PASA|FALLA", "control_3": "PASA|FALLA", "control_4": "PASA|FALLA", "veredicto": "Validación exitosa. Listo para presentar al reclutador.|Requiere corrección.", "observaciones": "<máx 2 líneas>"}}"""

    else:
        raise ValueError(f"Step desconocido: {step}")


def process(body):
    """Ejecuta un paso del pipeline. Recibe el body (dict) y devuelve (status, result).
    Separado del handler HTTP para poder testear igual en Vercel y en local."""
    step = body.get("step")
    cv   = body.get("cv", "")
    jd   = body.get("jd", "")
    ctx  = body.get("ctx", {})
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return 500, {"error": "GROQ_API_KEY no configurada en Vercel."}
    raw = ""
    try:
        client = Groq(api_key=api_key)
        prompt = build_prompt(step, cv, jd, ctx)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            temperature=0,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content
        return 200, json.loads(clean_json(raw))
    except json.JSONDecodeError as e:
        return 500, {"error": f"JSON inválido: {str(e)}", "raw": raw}
    except Exception as e:
        return 500, {"error": str(e)}


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            status, result = process(body)
            self.send_json(status, result)
        except Exception as e:
            self.send_json(500, {"error": str(e)})
