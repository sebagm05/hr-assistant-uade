import json
import os
from http.server import BaseHTTPRequestHandler
import anthropic

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
REGLA: evidencia_en_cv debe ser cita textual. Sin cita posible = no va en match_fuerte."""

    elif step == "t3":
        t2 = ctx.get("t2", {})
        return f"""TAREA: Cálculo de Match Score.
Output T2: {json.dumps(t2, ensure_ascii=False)}
Ponderación: base 100, cada brecha_excluyente Crítica descuenta 20 pts, cada brecha_deseable Moderada descuenta 5 pts, bonus +5 por skills adicionales verificables en el CV. Mínimo 0.
Devuelve SOLO este JSON exacto:
{{"match_score": <número 0-100>, "recomendacion": "Avanzar a entrevista|Revisión manual|Descartar", "justificacion_score": "<máx 3 líneas>", "penalizaciones_aplicadas": [{{"requisito": "<string>", "descuento": <número>}}]}}"""

    elif step == "t4":
        t2 = ctx.get("t2", {})
        t3 = ctx.get("t3", {})
        return f"""TAREA: Diseño de Guía de Entrevista Personalizada.
CV: {cv}
Output T2: {json.dumps(t2, ensure_ascii=False)}
Output T3: {json.dumps(t3, ensure_ascii=False)}
Devuelve SOLO este JSON exacto:
{{"preguntas": [{{"tipo": "Técnica", "pregunta": "<string>", "que_buscar": "<string>"}}, {{"tipo": "Brecha", "pregunta": "<string>", "que_buscar": "<string>"}}, {{"tipo": "Conductual STAR", "pregunta": "<string>", "que_buscar": "<string>"}}, {{"tipo": "Situacional", "pregunta": "<string>", "que_buscar": "<string>"}}]}}
REGLA: Cada pregunta debe nombrar un logro o herramienta específica del CV. No preguntas genéricas."""

    elif step == "val":
        t2 = ctx.get("t2", {})
        t3 = ctx.get("t3", {})
        t4 = ctx.get("t4", None)
        return f"""TAREA: Auditoría de Calidad y Control Anti-Alucinaciones.
CV original: {cv}
Output T2: {json.dumps(t2, ensure_ascii=False)}
Output T3: {json.dumps(t3, ensure_ascii=False)}
Output T4: {json.dumps(t4, ensure_ascii=False) if t4 else "No aplica (candidato descartado)"}
Devuelve SOLO este JSON exacto:
{{"control_1": "PASA|FALLA", "control_2": "PASA|FALLA", "control_3": "PASA|FALLA", "veredicto": "Validación exitosa. Listo para presentar al reclutador.|Requiere corrección.", "observaciones": "<máx 2 líneas>"}}"""

    else:
        raise ValueError(f"Step desconocido: {step}")


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # silencia logs de requests en consola

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

            step = body.get("step")
            cv   = body.get("cv", "")
            jd   = body.get("jd", "")
            ctx  = body.get("ctx", {})

            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                self.send_json(500, {"error": "ANTHROPIC_API_KEY no configurada en las variables de entorno de Vercel."})
                return

            client = anthropic.Anthropic(api_key=api_key)
            prompt = build_prompt(step, cv, jd, ctx)

            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw  = message.content[0].text
            result = json.loads(clean_json(raw))
            self.send_json(200, result)

        except json.JSONDecodeError as e:
            self.send_json(500, {"error": f"La IA no devolvió JSON válido: {str(e)}", "raw": raw if 'raw' in dir() else ""})
        except Exception as e:
            self.send_json(500, {"error": str(e)})
