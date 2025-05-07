import os
import io
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

import pandas as pd

from app.database import SessionLocal, create_tables
from app.models import HL7MessageWish, HL7MessageOrline
from app.schemas import HL7MessageWishSchema, HL7MessageOrlineSchema
from app.crud import create_wish_message, create_orline_message

create_tables()
app = FastAPI()

fake_users_db = {}
unit_names = {
        "210": "210-ONCOLOGIE/ENDOCRINOLOGIE",
        "220": "220-REVALIDATION",
        "225": "225-NEUROCHIR/ORTHO (CD5)",
        "230": "230-CARDIOLOGIE/CHIR. VASCULAIRE",
        "235": "235-GASTROENTEROLOGIE",
        "240": "240-MEDECINE INTERNE GENERALE",
        "245": "245-GERIATRIE",
        "255": "255-PNEUMOLOGIE/NEPHROLOGIE",
        "310": "310-SOINS INTENSIFS",
        "311": "311-SOINS INTENSIFS",
        "316": "316-SOINS INTENSIFS",
        "317": "317-STROKE",
        "318": "318-SOINS INTENSIFS",
        "413": "413-SALLE DE REVEIL (COVID 19)",
        "420": "420-NEUROCHIR/ORTHO (CD7)",
        "425": "425-NEUROLOGIE",
        "426": "426-POLYSOMNOGRAPHIE ADULTES",
        "430": "430-CHIRURGIE ABDOMINALE",
        "435": "435-GYNECOLOGIE/UROLOGIE",
        "440": "440-GERIATRIE",
        "445": "445-GERIATRIE",
        "450": "450-PSYCHIATRIE COURT SEJOUR",
        "640": "640-PEDIATRIE",
        "809": "809-SOINS INTENSIFS PEDIATRIQUES",
        "810": "810-BLOC OBSTETRIQUE",
        "812": "812-ACCUEIL ACCOUCHEMENT",
        "815": "815-MIC",
        "820": "820-NIC",
        "820K": "820K-KANGOUROU",
        "820M": "820M-MATERNITE/KANGOUROU",
        "825": "825-ETUDE DU SOMMEIL PEDIATRIQUE",
        "830": "830-MATERNITE",
        "835": "835-MATERNITE",
        "840": "840-PEDIATRIE",
        "845": "845-PEDIATRIE",
        "910": "910-PSYCHIATRIE",
        "707": "707-URGENCES ADULTES",
        "410": "410-HOPITAL DE JOUR CHIR/UAPO",
        "410A": "410-HOPITAL DE JOUR CHIR/UAPO-HJ",
        "415": "415-HOPITAL DE JOUR CHIRURGICAL"
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_hl7_datetime(dt_str: str) -> str:
    if not dt_str:
        return None
    try:
        if len(dt_str) == 12:
            dt = datetime.strptime(dt_str, "%Y%m%d%H%M")
        elif len(dt_str) == 14:
            dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
        else:
            return dt_str
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str

@app.get("/wish/", response_model=List[HL7MessageWishSchema])
def get_all_wish_messages(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return db.query(HL7MessageWish).offset(skip).limit(limit).all()

@app.get("/orline/", response_model=List[HL7MessageOrlineSchema])
def get_all_orline_messages(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return db.query(HL7MessageOrline).offset(skip).limit(limit).all()

class PatientsResponse(BaseModel):
    patients: List[str]
    total: int

@app.get("/patients", response_model=PatientsResponse)
def get_all_patients(source: str = Query("both", enum=["wish", "orline", "both", "intersection"]), db: Session = Depends(get_db)):
    wish_ids = set([row[0] for row in db.query(HL7MessageWish.cbmrn).filter(HL7MessageWish.cbmrn.isnot(None)).distinct()])
    orline_ids = set([row[0] for row in db.query(HL7MessageOrline.id_pat).filter(HL7MessageOrline.id_pat.isnot(None)).distinct()])

    if source == "wish":
        ids = wish_ids
    elif source == "orline":
        ids = orline_ids
    elif source == "intersection":
        ids = wish_ids & orline_ids
    else:
        ids = wish_ids | orline_ids

    return PatientsResponse(
        total=len(ids),
        patients=sorted(ids)
    )
@app.get("/patient/{id_pat}/sejours", response_model=List[str])
def get_sejours_by_patient(id_pat: str, db: Session = Depends(get_db)):
    wish_sejours = db.query(HL7MessageWish.nsej).filter(HL7MessageWish.cbmrn == id_pat, HL7MessageWish.nsej.isnot(None)).distinct().all()
    orline_sejours = db.query(HL7MessageOrline.id_sejour).filter(HL7MessageOrline.id_pat == id_pat, HL7MessageOrline.id_sejour.isnot(None)).distinct().all()

    sejours = set()
    sejours.update([s[0] for s in wish_sejours if s[0]])
    sejours.update([s[0] for s in orline_sejours if s[0]])

    if not sejours:
        raise HTTPException(status_code=404, detail="Aucun séjour trouvé pour ce patient.")

    return sorted(sejours)
WATCHED_FOLDERS = {
    r"C:\Users\sbenayed\Desktop\WISH_ADT - Copie\WISH_ADT - Copie": "WISH",
    r"C:\Users\sbenayed\Desktop\ORLine\SIU": "ORLine",
    r"C:\Users\sbenayed\Desktop\ORLine\ADT": "ORLine",
}

SUPPORTED_EXTENSIONS = [".hl7", ".txt", ".dat", ".xml"]

def process_file(filepath: str, source: str, db: Session):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='iso-8859-1') as file:
            content = file.read()

    if source == "WISH":
        create_wish_message(db=db, hl7_raw_message=content)
    elif source == "ORLine":
        create_orline_message(db=db, hl7_raw_message=content)

def process_all_folders():
    db = SessionLocal()
    try:
        for folder_path, source in WATCHED_FOLDERS.items():
            if not os.path.isdir(folder_path):
                continue
            for filename in os.listdir(folder_path):
                full_path = os.path.join(folder_path, filename)
                if os.path.isfile(full_path) and os.path.splitext(filename)[1].lower() in SUPPORTED_EXTENSIONS:
                    process_file(full_path, source, db)
    finally:
        db.close()

@app.post("/process-all/")
def run_full_importation(db: Session = Depends(get_db)):
    process_all_folders()
    return {"message": "Importation terminée."}

@app.delete("/clear-all/")
def clear_all_tables(db: Session = Depends(get_db)):
    try:
        db.execute(text("TRUNCATE TABLE hl7_message_wish RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE TABLE hl7_message_orline RESTART IDENTITY CASCADE"))
        db.commit()
        return {"message": "Toutes les tables ont été vidées avec succès."}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}

@app.get("/messages-by-patient/{patient_id}")
def get_messages_by_patient(patient_id: str, source: str = Query("both", enum=["wish", "orline", "both"]), db: Session = Depends(get_db)):
    result = {}
    if source in ["wish", "both"]:
        wish_messages = db.query(HL7MessageWish).filter(HL7MessageWish.cbmrn == patient_id).all()
        result["wish_messages"] = [message.__dict__ for message in wish_messages]
    if source in ["orline", "both"]:
        orline_messages = db.query(HL7MessageOrline).filter(HL7MessageOrline.id_pat == patient_id).all()
        result["orline_messages"] = [message.__dict__ for message in orline_messages]
    if not result.get("wish_messages") and not result.get("orline_messages"):
        raise HTTPException(status_code=404, detail="Aucun message trouvé pour cet ID patient.")
    return result

@app.get("/messages-by-patient-sejour")
def get_messages_by_patient_sejour(id_pat: str, id_sejour: str, db: Session = Depends(get_db)):
    wish_msgs = db.query(HL7MessageWish).filter(
        HL7MessageWish.cbmrn == id_pat,
        HL7MessageWish.nsej == id_sejour
    ).all()

    orline_msgs = db.query(HL7MessageOrline).filter(
        HL7MessageOrline.id_pat == id_pat,
        HL7MessageOrline.id_sejour == id_sejour
    ).all()

    results = [msg.__dict__ for msg in wish_msgs + orline_msgs]

    if not results:
        raise HTTPException(status_code=404, detail="Aucun message trouvé pour ce patient et ce séjour.")

    return results

@app.get("/journey/full/{id_pat}/{id_sejour}")
def get_patient_journey_one_sejour(id_pat: str, id_sejour: str, db: Session = Depends(get_db)):
    wish_msgs = db.query(HL7MessageWish).filter(
        HL7MessageWish.cbmrn == id_pat,
        HL7MessageWish.nsej == id_sejour
    ).all()

    orline_msgs = db.query(HL7MessageOrline).filter(
        HL7MessageOrline.id_pat == id_pat,
        HL7MessageOrline.id_sejour == id_sejour
    ).all()

   

    def parse_event(msg: dict, source: str):
        from datetime import datetime

        def to_dt(s):
            try:
                if s is None:
                    return None
                return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            except:
                return None

        date_debut_str = parse_hl7_datetime(msg.get("clfrom") or msg.get("date_message") or msg.get("date_evt") or "")
        date_fin_str = parse_hl7_datetime(msg.get("clto") or msg.get("date_fin") or msg.get("cltime") or "")

        date_debut = to_dt(date_debut_str)
        date_fin = to_dt(date_fin_str)

        raw_unite = msg.get("cleent") or msg.get("Service_Name") or ""
        unite = unit_names.get(raw_unite, raw_unite)
        service = raw_unite
        medecin = msg.get("nomm") or msg.get("medecin") or ""

        desc = (msg.get("typ_evt") or msg.get("Event_Description") or "").lower()
        if "admission" in desc or "entrée" in desc:
            type_evt = "ADMISSION"
        elif "sortie" in desc:
            type_evt = "DISCHARGE"
        elif "transfert" in desc:
            type_evt = "TRANSFER"
        else:
            return None

        duration = ""
        if date_debut and date_fin:
            delta = date_fin - date_debut
            duration = str(delta)

        return {
            "debut": date_debut_str,
            "fin": date_fin_str,
            "unite": unite,
            "service": service,
            "type_evenement": type_evt,
            "medecin": medecin,
            "duration": duration
        }

    parcours = [
        *[parse_event(msg.__dict__, "WISH") for msg in wish_msgs],
        *[parse_event(msg.__dict__, "ORLINE") for msg in orline_msgs]
    ]

    parcours = [p for p in parcours if p and p["debut"]]
    parcours.sort(key=lambda x: x["debut"])

    if not parcours:
        raise HTTPException(status_code=404, detail="Aucun message trouvé pour ce patient et ce séjour.")

    return {
        "timeline": [
            {
                "Unité de soins": p["unite"],
                "Start": p["debut"].replace("-", "").replace(":", "").replace(" ", ""),
                "Finish": p["fin"].replace("-", "").replace(":", "").replace(" ", ""),
                "Resource": p["service"]
            } for p in parcours
        ],
        "events": parcours
    }


@app.get("/hl7/export-all")
def export_all_messages_to_excel(db: Session = Depends(get_db)):
    # 1) Charger Wish et construire le DataFrame
    wish_messages = db.query(HL7MessageWish).all()
    wish_data = [msg.__dict__ for msg in wish_messages]
    wish_df = pd.DataFrame(wish_data)
    # Supprimer les colonnes inutiles
    for col in ["_sa_instance_state", "id"]:
        if col in wish_df.columns:
            wish_df = wish_df.drop(columns=[col])
    if "clrs_cd" in wish_df.columns:
        wish_df = wish_df[wish_df["clrs_cd"].isin(["A01", "A02", "A03"])]

    if "clfrom" in wish_df.columns:
       wish_df["clfrom"] = pd.to_datetime(wish_df["clfrom"], errors="coerce")
       wish_df = wish_df.sort_values(by=["cbmrn", "clfrom"])

    # 2) Réordonner les colonnes selon votre liste
    wish_order = [
        "clrs_cd", "nsej", "cbmrn", "cbtype", "cbadty", "tsv", "clfrom",
        "clnsid", "nsdscr", "clroom", "clbed", "clsvtc", "tectxtfr",
        "cldept", "svnomf", "nrpr", "nomm", "cltima"
    ]
    # Garde seulement les colonnes existantes, dans l’ordre
    wish_df = wish_df[[c for c in wish_order if c in wish_df.columns]]

    # 3) Charger Orline et construire le DataFrame
    orline_messages = db.query(HL7MessageOrline).all()
    orline_data = [msg.__dict__ for msg in orline_messages]
    orline_df = pd.DataFrame(orline_data)
    for col in ["_sa_instance_state", "id"]:
        if col in orline_df.columns:
            orline_df = orline_df.drop(columns=[col])
    if "date_message" in orline_df.columns:
        orline_df["date_message"] = pd.to_datetime(orline_df["date_message"], errors="coerce")
        orline_df = orline_df.sort_values(by=["id_pat", "date_message"])

    # 4) Réordonner les colonnes selon votre liste
    orline_order = [
        "date_message", "message_type", "message_id", "id_pat", "id_sejour",
        "id_ope", "heu_deb_ope_prev", "heu_fin_ope_prev", "tps_ope_prev",
        "type_ope", "date_ope", "id_sal_ope", "arr_sal_ope", "anesth",
        "discip", "chir", "planning", "naissance", "sexe"
    ]
    orline_df = orline_df[[c for c in orline_order if c in orline_df.columns]]

    # 5) Écrire dans un fichier Excel en mémoire, deux feuilles
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wish_df.to_excel(writer, index=False, sheet_name="Wish Messages")
        orline_df.to_excel(writer, index=False, sheet_name="Orline Messages")
    output.seek(0)

    # 6) Retour en StreamingResponse pour téléchargement
    headers = {
        "Content-Disposition": 'attachment; filename="hl7_messages_export.xlsx"'
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
class UserCreate(BaseModel):
    username: str
    password: str
    function: str
    role: str

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/register")
def register_user(user: UserCreate):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà pris.")
    fake_users_db[user.username] = {
        "password": user.password,
        "function": user.function,
        "role": user.role
    }
    return {"message": "Utilisateur créé avec succès."}

@app.post("/login")
def login_user(user: UserLogin):
    db_user = fake_users_db.get(user.username)
    if not db_user or db_user["password"] != user.password:
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    return {"message": "Connexion réussie."}
service_technique_names = {
    "8BLO": "BLOC OPERATOIRE-MLE",
    "8REV": "SALLE REVEIL-MLE",
    # ajouter d'autres mappings si besoin
}

def format_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def fmt_str(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y à %H:%M")

def diff_str(start: datetime, end: Optional[datetime]) -> str:
    if not end:
        return "en cours"
    delta = end - start
    h, rem = divmod(delta.total_seconds(), 3600)
    m = rem // 60
    return f"{int(h)} h {int(m)} min"

@app.get("/patient-journey-gantt/{id_pat}")
def get_patient_journey_detailed(
    id_pat: str,
    db: Session = Depends(get_db)
) -> List[Dict]:
    # 1) Récupération des messages WISH + ORLINE
    wish_msgs   = db.query(HL7MessageWish).filter(HL7MessageWish.cbmrn == id_pat).all()
    orline_msgs = db.query(HL7MessageOrline).filter(HL7MessageOrline.id_pat == id_pat).all()
    all_msgs    = [*wish_msgs, *orline_msgs]

    # 2) Construction de la liste brute d'événements
    raw: List[Dict] = []
    for msg in all_msgs:
        d    = msg.__dict__
        code = (d.get("clrs_cd") or "").upper()
        if code not in {"A01", "A02", "A03"}:
            continue
        dt = format_dt(d.get("cltima"))
        if dt is None:
            continue

        raw.append({
            "nsej":   d.get("nsej"),
            "cbmrn":  d.get("cbmrn"),
            "clnsid": d.get("clnsid") or "",
            "clsvtc": d.get("clsvtc") or "",
            "dt":     dt,
            "code":   code
        })

    # 3) Tri chronologique
    raw.sort(key=lambda e: e["dt"])
    if not raw:
        raise HTTPException(404, "Aucun événement A01/A02/A03 trouvé.")

    # 4) Date d’admission initiale pour calcul de durée totale
    admission_dt = next((e["dt"] for e in raw if e["code"] == "A01"), raw[0]["dt"])

    # 5) Construction du résultat formaté
    result: List[Dict] = []
    for idx, ev in enumerate(raw):
        is_last  = (idx == len(raw) - 1)
        dt_evt   = fmt_str(ev["dt"])
        unité    = unit_names.get(ev["clnsid"], ev["clnsid"])
        service  = service_technique_names.get(ev["clsvtc"], ev["clsvtc"])
        code_lbl = {"A01": "ADMISSION", "A02": "TRANSFER", "A03": "DISCHARGE"}[ev["code"]]
        next_dt  = raw[idx + 1]["dt"] if idx + 1 < len(raw) else None

        # 1) Admission
        if ev["code"] == "A01":
            result.append({
                "NSEJ":                   ev["nsej"],
                "CBMRN":                  ev["cbmrn"],
                "Resource":               f"{ev['code']} - {code_lbl}",
                "Unité de soins":         unité,
                "Service technique":      service,
                "Date/heure d'événement": dt_evt,
                "Temps passé":            diff_str(ev["dt"], next_dt)
            })
            continue

        # 2) Transfert intermédiaire
        if ev["code"] == "A02" and not is_last:
            result.append({
                "NSEJ":                   ev["nsej"],
                "CBMRN":                  ev["cbmrn"],
                "Resource":               f"{ev['code']} - {code_lbl}",
                "Unité de soins":         unité,
                "Service technique":      service,
                "Date/heure d'événement": dt_evt,
                "Temps passé":            diff_str(ev["dt"], next_dt)
            })
            continue

        # 3) Dernier transfert non terminé
        if ev["code"] == "A02" and is_last:
            result.append({
                "NSEJ":                   ev["nsej"],
                "CBMRN":                  ev["cbmrn"],
                "Resource":               f"{ev['code']} - {code_lbl}",
                "Unité de soins":         unité,
                "Service technique":      service,
                "Date/heure d'événement": dt_evt,
                "Temps passé en cours":   diff_str(ev["dt"], None)
            })
            break

        # 4) Discharge final
        if ev["code"] == "A03" and is_last:
            total = diff_str(admission_dt, ev["dt"])
            result.append({
                "NSEJ":                   ev["nsej"],
                "CBMRN":                  ev["cbmrn"],
                "Resource":               f"{ev['code']} - {code_lbl}",
                "Unité de soins":         unité,
                "Service technique":      service,
                "Date/heure de sortie":   dt_evt,
                "Durée totale de séjour": total
            })
            break

    return result