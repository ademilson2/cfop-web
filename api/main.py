from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional
import pandas as pd
import re
import os
# Ajuste forçado para redeploy no Vercel
# Caminhos relativos para produção
BASE_DIR = os.path.dirname(__file__)
EXCEL_PATH = os.path.join(BASE_DIR, "REGRA_SAIDA.xlsx")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Inicialização
app = FastAPI(title="CFOP Bot API")

# Montar a pasta de arquivos estáticos
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Rota para servir o index.html diretamente na raiz
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Carregar planilha
try:
    df = pd.read_excel(EXCEL_PATH, dtype=str).fillna("")
    df["CFOP"] = df["CODNAT"].astype(str).str.strip()
except Exception as e:
    df = pd.DataFrame()
    print("Erro ao carregar planilha:", e)

LISTA_UF = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
    "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
]
uf_pattern = re.compile(r"\b(" + "|".join(LISTA_UF) + r")\b", flags=re.IGNORECASE)

def extrair_ufs(texto: str):
    if not isinstance(texto, str): return set()
    found = uf_pattern.findall(texto)
    return set([f.upper() for f in found])

if not df.empty and "DESCR_NAT" in df.columns:
    df["_UF_SET"] = df["DESCR_NAT"].apply(extrair_ufs)
else:
    df["_UF_SET"] = []

def procedencia_casou(celula: str, selecionado: str) -> bool:
    if selecionado in ("", None): return True
    if celula is None: return False
    parts = [p.strip() for p in re.split(r"[;,/]", str(celula)) if p.strip()]
    return selecionado in parts

class FilterRequest(BaseModel):
    uf: str
    procedencia: Optional[str] = ""
    descricao: Optional[str] = ""

class CFOPItem(BaseModel):
    cfop: str
    descricao: str
    procedencia: str
    ufs: List[str]
    codtmv: Optional[str] = None
    icms_op: Optional[str] = None
    icms_st: Optional[str] = None

@app.get("/api/health")
def health():
    return {"ok": True, "rows": len(df)}

@app.post("/api/filter", response_model=List[CFOPItem])
def api_filter(req: FilterRequest):
    if df.empty:
        raise HTTPException(status_code=500, detail="Planilha não carregada no servidor.")

    uf = (req.uf or "").strip().upper()
    procedencia = (req.procedencia or "").strip()
    descricao = (req.descricao or "").strip().upper()

    if not uf:
        raise HTTPException(status_code=400, detail="UF é obrigatória.")

    filtrado = df[df["_UF_SET"].apply(lambda s: uf in s)]

    if procedencia:
        filtrado = filtrado[filtrado["PROCEDENCIA"].apply(lambda c: procedencia_casou(c, procedencia))]

    if descricao:
        filtrado = filtrado[filtrado["DESCR_NAT"].str.upper().str.contains(descricao, na=False)]

    if filtrado.empty:
        return []

    filtrado = filtrado.drop_duplicates(subset=["CFOP"], keep="first")

    return [
        CFOPItem(
            cfop=r.get("CFOP", ""),
            descricao=r.get("DESCR_NAT", ""),
            procedencia=r.get("PROCEDENCIA", ""),
            ufs=sorted(list(r.get("_UF_SET", []))),
            codtmv=r.get("CODTMV", ""),
            icms_op=r.get("ICMS_OP", ""),
            icms_st=r.get("ICMS_ST", "")
        )
        for _, r in filtrado.iterrows()
    ]
        item = CFOPItem(
            cfop = r.get("CFOP",""),
            descricao = r.get("DESCR_NAT",""),
            procedencia = r.get("PROCEDENCIA",""),
            ufs = sorted(list(r.get("_UF_SET", []))),
            codtmv = r.get("CODTMV",""),
            icms_op = r.get("ICMS_OP",""),
            icms_st = r.get("ICMS_ST","")
        )
        out.append(item)
    return out