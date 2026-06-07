# Asistente de Selección y Entrevistas — UADE IA Aplicada

## Estructura del proyecto

```
hr-assistant/
├── index.html          ← Frontend completo
├── api/
│   └── analyze.py      ← Backend serverless (corre en Vercel)
├── requirements.txt    ← Dependencias Python
├── vercel.json         ← Configuración de Vercel
└── README.md
```

---

## Paso 1 — Obtener la API key de Anthropic

1. Ir a https://console.anthropic.com
2. Crear cuenta (gratis)
3. Ir a "API Keys" → "Create Key"
4. Copiar la key (empieza con `sk-ant-...`)

---

## Paso 2 — Subir a Vercel

### Opción A — Desde GitHub (recomendado)

1. Crear un repositorio en https://github.com
2. Subir todos estos archivos
3. Ir a https://vercel.com → "Add New Project"
4. Importar el repositorio de GitHub
5. En "Environment Variables" agregar:
   - **Key:** `ANTHROPIC_API_KEY`
   - **Value:** tu key de Anthropic
6. Click en "Deploy"

### Opción B — Desde la CLI de Vercel

```bash
# Instalar Vercel CLI
npm install -g vercel

# Desde la carpeta del proyecto
vercel

# Cuando pregunte, completar:
# Project name: hr-assistant-uade
# Framework: Other

# Agregar la API key
vercel env add ANTHROPIC_API_KEY
# Pegar la key y confirmar

# Deploy final
vercel --prod
```

---

## Paso 3 — Usar la app

Una vez deployada, Vercel te da una URL del tipo:
`https://hr-assistant-uade.vercel.app`

Abrís esa URL en cualquier navegador y la app funciona.

---

## Costo estimado

| Uso | Costo aproximado |
|-----|-----------------|
| 1 análisis completo | ~$0.003 |
| Demo en clase (10 pruebas) | ~$0.03 |
| Anthropic crédito gratis al registrarse | ~$5 |

El crédito gratuito alcanza para ~1.600 análisis completos.

---

## Modelo de IA usado

`claude-sonnet-4-6` — elegido por su menor tasa de alucinación,
alineado con la Política de Cero Alucinación del sistema.
