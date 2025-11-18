# api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import re
from typing import List, Optional

# PATH para a planilha — **use o arquivo que você enviou**
EXCEL_PATH = "E:/python/BOTCFOP/REGRA_SAIDA.xlsx"

# Inicialização
app = FastAPI(title="CFOP Bot API")
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Montar a pasta de arquivos estáticos
app.mount("/static", StaticFiles(directory="E:/python/BOTCFOP/static"), name="static")

# Rota para servir o index.html diretamente na raiz
@app.get("/")
def serve_index():
    return FileResponse(os.path.join("E:/python/BOTCFOP/static", "index.html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

# carregar planilha uma vez na inicialização
try:
    df = pd.read_excel(EXCEL_PATH, dtype=str).fillna("")
    df["CFOP"] = df["CODNAT"].astype(str).str.strip()
except Exception as e:
    # fallback: dataframe vazio, endpoint retornará erro apropriado
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

# precompute UF sets
if not df.empty and "DESCR_NAT" in df.columns:
    df["_UF_SET"] = df["DESCR_NAT"].apply(extrair_ufs)
else:
    df["_UF_SET"] = []

# util: match procedencia in cell list like "0, 4, 5, 6, 7, 90"
def procedencia_casou(celula: str, selecionado: str) -> bool:
    if selecionado in ("", None): return True
    if celula is None: return False
    parts = [p.strip() for p in re.split(r"[;,/]", str(celula)) if p.strip() != ""]
    return selecionado in parts

# Input model
class FilterRequest(BaseModel):
    uf: str
    procedencia: Optional[str] = ""
    descricao: Optional[str] = ""

# Output model
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

    # 1) filtrar por UF (usando set pré-calculado)
    filtrado = df[df["_UF_SET"].apply(lambda s: uf in s)]

    # 2) filtrar por procedencia (se informada) — procura no CSV-like
    if procedencia != "":
        filtrado = filtrado[filtrado["PROCEDENCIA"].apply(lambda c: procedencia_casou(c, procedencia))]

    # 3) filtrar por descricao (substring, opcional)
    if descricao:
        filtrado = filtrado[filtrado["DESCR_NAT"].str.upper().str.contains(descricao, na=False)]

    if filtrado.empty:
        return []

    # dedupe by CFOP (first occurrence)
    filtrado = filtrado.drop_duplicates(subset=["CFOP"], keep="first")

    # build response
    out = []
    for _, r in filtrado.iterrows():
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