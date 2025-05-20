import os
import io
import logging
import time
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from collections import defaultdict
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd
from contextlib import asynccontextmanager
from app.database import SessionLocal, create_tables
from app.models import HL7MessageWish, HL7MessageOrline
from app.schemas import HL7MessageWishSchema, HL7MessageOrlineSchema
from app.crud import create_wish_message, create_orline_message


create_tables()
logging.basicConfig(level=logging.INFO)


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

WATCHED_FOLDERS = {
    r"C:\Users\sbenayed\Desktop\PFE\hl7_archive\WISH ADT 7 avril 2025": "WISH",
    r"C:\Users\sbenayed\Desktop\PFE\hl7_archive\ORL SIU 7 avril 2025": "ORLine",
    r"C:\Users\sbenayed\Desktop\PFE\hl7_archive\ORL ADT 7 avril 2025": "ORLine",
}

SUPPORTED_EXTENSIONS = [".hl7", ".txt", ".dat", ".xml"]


class HourlyCount(BaseModel):
    hour: str  # au lieu de int
    total_patients: int
    by_unit: Dict[str, int]

class DailyCount(BaseModel):
    date: date
    hourly_counts: List[HourlyCount]
class PatientCountsResponse(BaseModel):
    start_date: date
    end_date: date
    daily_counts: List[DailyCount]



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

class HL7Handler(FileSystemEventHandler):
    def __init__(self, source: str):
        super().__init__()
        self.source = source

    def on_created(self, event):
        if not event.is_directory:
            self._process(event.src_path)

    def on_moved(self, event):
        # Fichiers copiés depuis l’explorateur arrivent souvent via un move
        if not event.is_directory:
            self._process(event.dest_path)

    def on_modified(self, event):
        # Couvrir d’éventuelles modifications in-place
        if not event.is_directory:
            self._process(event.src_path)

    def _process(self, path: str):
        # Laisser Windows finir la copie
        time.sleep(0.1)

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return

        logging.info(f"→ Processing HL7 file {path} as {ext}")
        db = SessionLocal()
        try:
            # Lecture en UTF-8 ou ISO-8859-1
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(path, "r", encoding="iso-8859-1") as f:
                    content = f.read()

            # Insertion en base
            if self.source == "WISH":
                create_wish_message(db, content)
            else:
                create_orline_message(db, content)

            # Suppression
            os.remove(path)
            logging.info(f"✓ Handled and removed {path}")
        except Exception as e:
            logging.error(f"Error processing {path}: {e}")
        finally:
            db.close()
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("▶️ Lifespan startup begin") 
    app.state.observers = []

    # 1) Backlog : traiter les fichiers déjà présents
    for path, source in WATCHED_FOLDERS.items():
        os.makedirs(path, exist_ok=True)
        handler = HL7Handler(source)
        # Timeout plus court pour quasi-temps réel
        obs = Observer(timeout=0.5)
        obs.schedule(handler, path, recursive=False)
        obs.start()
        logging.info(f"Watcher (real-time) started on {path}")
        app.state.observers.append(obs)
        for fname in os.listdir(path):
            full = os.path.join(path, fname)
            ext = os.path.splitext(full)[1].lower()
            if os.path.isfile(full) and ext in SUPPORTED_EXTENSIONS:
                logging.info(f"Backlog processing existing file {full}")
                db = SessionLocal()
                try:
                    # Lecture robuste du contenu
                    try:
                        with open(full, "r", encoding="utf-8") as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        with open(full, "r", encoding="iso-8859-1") as f:
                            content = f.read()

                    # Insertion en base
                    if source == "WISH":
                        create_wish_message(db, content)
                    else:
                        create_orline_message(db, content)

                    # Suppression du fichier
                    os.remove(full)
                    logging.info(f"Backlog removed {full}")
                finally:
                    db.close()

    # 2) Démarrage des observers pour les nouveaux fichiers
    for path, source in WATCHED_FOLDERS.items():
        handler = HL7Handler(source)
        obs = Observer()
        obs.schedule(handler, path, recursive=False)
        obs.start()
        logging.info(f"Watcher started on {path} (source={source})")
        app.state.observers.append(obs)
    logging.info("▶️ Lifespan startup end") 
    yield  # l’app démarre ici
    logging.info("⏹ Lifespan shutdown")
    # 3) Arrêt propre
    for obs in app.state.observers:
        obs.stop()
        obs.join()
        logging.info("Watcher stopped cleanly")

# --- Instanciation de l’app ---
app = FastAPI(lifespan=lifespan)
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
    wish_messages = db.query(HL7MessageWish).yield_per(500)
    extracted_data = []
    for msg in wish_messages:
        nsej = msg.nsej
        if msg.clrs_cd == "A05":
         try:
                if msg.hl7_raw:
                    for line in msg.hl7_raw.splitlines():
                        if line.startswith("PV1|"):
                            parts = line.strip().split("|")
                            if len(parts) > 6:
                                raw_nsej = parts[6].strip()
                                nsej = raw_nsej[1:] if raw_nsej.startswith("1") else raw_nsej
                            break
            except Exception:
                pass
        else:
         try:
                if msg.hl7_raw:
                    for line in msg.hl7_raw.splitlines():
                        if line.startswith("PV1|"):
                            parts = line.strip().split("|")
                            if len(parts) > 19:
                                raw_nsej = parts[19].strip()
                                nsej = raw_nsej[1:] if raw_nsej.startswith("1") else raw_nsej
                            break
            except Exception:
                pass
           
        msg_dict = msg.__dict__.copy()
        msg_dict["nsej"] = msg.nsej
        extracted_data.append(msg_dict)
    wish_df = pd.DataFrame(extracted_data)
    for col in ["_sa_instance_state", "id"]:
        if col in wish_df.columns:
            wish_df = wish_df.drop(columns=[col])
    if "clrs_cd" in wish_df.columns:
        wish_df = wish_df[wish_df["clrs_cd"].isin(["A01", "A02", "A03"])]
        wish_df["clrs_cd"] = wish_df["clrs_cd"].map({
            "A01": "A",
            "A02": "T",
            "A03": "D"
        })
    if "clfrom" in wish_df.columns:
        wish_df["clfrom"] = pd.to_datetime(wish_df["clfrom"], errors="coerce")
        wish_df = wish_df.sort_values(by=["cbmrn", "clfrom"])
    if "clnsid" in wish_df.columns:
        wish_df["nsdscr"] = wish_df["clnsid"].map(unit_names).fillna("")
        wish_df = wish_df[wish_df["clnsid"].isin(unit_names.keys())]
    wish_df["clfrom"] = pd.to_datetime(wish_df["clfrom"], errors="coerce")
    wish_df = wish_df.sort_values(["cbmrn", "nsej", "clnsid", "clfrom"])
    wish_df["prev_clfrom"] = wish_df.groupby(
        ["cbmrn", "nsej", "clnsid"]
    )["clfrom"].shift(1)
    wish_df["delta_min"] = (
        (wish_df["clfrom"] - wish_df["prev_clfrom"])
        .dt.total_seconds() / 60.0
    )
    to_drop = []
    for (pat, sej, unit), grp in wish_df.groupby(["cbmrn", "nsej", "clnsid"]):
        short = grp[grp["delta_min"] < 5.0]
        if short.empty:
            continue
        for idx in short.index:
            prev = grp.loc[idx, "prev_clfrom"]
            cur = grp.loc[idx, "clfrom"]
            two = grp[(grp["clfrom"] == prev) | (grp["clfrom"] == cur)]
            if "8BLO" in two["clsvtc"].values:
                drop_idx = two[two["clsvtc"] != "8BLO"].index
            else:
                drop_idx = [two.index.min()]
            to_drop.extend(drop_idx)
    wish_df = wish_df.drop(index=set(to_drop))
    wish_df = wish_df.drop(columns=["prev_clfrom", "delta_min"])
    wish_order = [
        "clrs_cd", "nsej", "cbmrn", "cbtype", "cbadty", "tsv", "clfrom",
        "clnsid", "nsdscr", "clroom", "clbed", "clsvtc", "tectxtfr",
        "cldept", "svnomf", "nrpr", "nomm", "cltima"
    ]
    wish_df = wish_df[[c for c in wish_order if c in wish_df.columns]]

    # 2) Charger Orline et construire le DataFrame
    orline_data = [msg.__dict__ for msg in db.query(HL7MessageOrline).yield_per(500)]
    orline_df = pd.DataFrame(orline_data)
    for col in ["_sa_instance_state", "id"]:
        if col in orline_df.columns:
            orline_df = orline_df.drop(columns=[col])
    if "date_message" in orline_df.columns:
        orline_df["date_message"] = pd.to_datetime(orline_df["date_message"], errors="coerce")
        orline_df = orline_df.sort_values(by=["id_pat", "date_message"])
    orline_order = [
        "date_message", "message_type", "message_id", "id_pat", "id_sejour",
        "id_ope", "heu_deb_ope_prev", "heu_fin_ope_prev", "tps_ope_prev",
        "type_ope", "date_ope", "id_sal_ope", "arr_sal_ope", "anesth",
        "discip", "chir", "planning", "naissance", "sexe"
    ]
    orline_df = orline_df[[c for c in orline_order if c in orline_df.columns]]

    preadmissions = []
    for msg in db.query(HL7MessageWish).filter(HL7MessageWish.clrs_cd == "A05"):
        # Récupérer le message HL7 depuis le fichier original correspondant à message_id
        filepath = None
        for folder_path in WATCHED_FOLDERS:
            for fname in os.listdir(folder_path):
                if msg.message_id and msg.message_id in fname:
                    filepath = os.path.join(folder_path, fname)
                    break
            if filepath:
                break

        nsej_value = msg.nsej
        if not nsej_value and filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(filepath, "r", encoding="iso-8859-1") as f:
                    content = f.read()

            for line in content.splitlines():
                if line.startswith("PV1|"):
                    fields = line.split("|")
                    if len(fields) > 6 and fields[6]:
                        nsej_raw = fields[6].strip()
                        nsej_value = nsej_raw[1:] if nsej_raw.startswith("1") else nsej_raw
                        break
        adm_ent = "UAPO" if msg.sour == "O" else "HOSP"
        if msg.cbadty == "A":
            adm_sor = "HOSP"
        elif msg.cbadty == "Z":
            adm_sor = "HDJ" if msg.clnsid != "225" else "HDJ"
        else:
            adm_sor = ""
        preadmissions.append([
            msg.cbmrn,
            msg.clfrom,
            msg.clnsid,
            nsej_value,
            msg.cldept,
            msg.nomm,
            msg.cbadty,
            msg.sour,
            adm_ent,
            adm_sor
        ])

    preadmission_df = pd.DataFrame(
        preadmissions,
        columns=["MRN", "Date admission", "Unité Ch. Lit", "N° admission", "Service", "Méd.", "T. adm.", "Sour.", "Adm_Ent", "Adm_Sor"]
    )

    # 4) Écriture dans un fichier Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wish_df.to_excel(writer, index=False, sheet_name="Wish Messages")
        orline_df.to_excel(writer, index=False, sheet_name="Orline Messages")
        if not preadmission_df.empty:
            preadmission_df.to_excel(writer, index=False, sheet_name="Pré-admissions")
    output.seek(0)

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
    wish_msgs = db.query(HL7MessageWish).filter(HL7MessageWish.cbmrn == id_pat).all()
    orline_msgs = db.query(HL7MessageOrline).filter(HL7MessageOrline.id_pat == id_pat).all()
    all_msgs = [*wish_msgs, *orline_msgs]

    raw: List[Dict] = []
    for msg in all_msgs:
        d = msg.__dict__
        code = (d.get("clrs_cd") or "").upper()
        if code not in {"A01", "A02", "A03"}:
            continue
        dt = format_dt(d.get("cltima"))
        if dt is None:
            continue
        raw.append({
            "nsej": d.get("nsej"),
            "cbmrn": d.get("cbmrn"),
            "clnsid": d.get("clnsid") or "",
            "clsvtc": d.get("clsvtc") or "",
            "dt": dt,
            "code": code
        })

    raw.sort(key=lambda e: e["dt"])
    if not raw:
        raise HTTPException(404, "Aucun événement A01/A02/A03 trouvé.")

    a01_indices = [i for i, e in enumerate(raw) if e["code"] == "A01"]
    if not a01_indices:
        raise HTTPException(404, "Aucun événement d’admission trouvé.")
    last_a01_index = max(a01_indices, key=lambda i: raw[i]["dt"])
    last_admission = raw[last_a01_index]
    raw = [e for i, e in enumerate(raw) if e["code"] != "A01" or i == last_a01_index]

    filtered = []
    i = 0
    while i < len(raw):
        curr = raw[i]
        if i + 1 < len(raw):
            nxt = raw[i + 1]
            delta = nxt["dt"] - curr["dt"]
            same_sej = curr["nsej"] == nxt["nsej"]
            same_unit = curr["clnsid"] == nxt["clnsid"]

            if curr["code"] == "A02" and nxt["code"] == "A02" and same_sej and same_unit and delta < timedelta(minutes=5):
                # Si l’un des deux contient clsvtc prioritaire, garder celui-là
                if nxt["clsvtc"] in {"8BLO", "8REV"}:
                    filtered.append(nxt)
                elif curr["clsvtc"] in {"8BLO", "8REV"}:
                    filtered.append(curr)
                else:
                    filtered.append(nxt)  # garder le plus récent
                i += 2
                continue

            if curr["code"] == "A02" and delta < timedelta(minutes=5) and curr["clsvtc"] not in {"8BLO", "8REV"}:
                i += 1
                continue

        filtered.append(curr)
        i += 1

    admission_dt = last_admission["dt"]
    filtered.insert(0, last_admission)

    result: List[Dict] = []
    for idx, ev in enumerate(filtered):
        is_last = (idx == len(filtered) - 1)
        dt_evt = fmt_str(ev["dt"])
        unit = unit_names.get(ev["clnsid"], ev["clnsid"])
        service = service_technique_names.get(ev["clsvtc"], ev["clsvtc"])
        code_lbl = {"A01": "ADMISSION", "A02": "TRANSFER", "A03": "DISCHARGE"}[ev["code"]]
        next_dt = filtered[idx + 1]["dt"] if idx + 1 < len(filtered) else None

        if ev["code"] == "A01":
            result.append({
                "NSEJ": ev["nsej"],
                "CBMRN": ev["cbmrn"],
                "Resource": f"{ev['code']} - {code_lbl}",
                "Unité de soins": unit,
                "Service technique": service,
                "Date/heure d'événement": dt_evt,
                "Temps passé": diff_str(ev["dt"], next_dt)
            })
            continue

        if ev["code"] == "A02":
            result.append({
                "NSEJ": ev["nsej"],
                "CBMRN": ev["cbmrn"],
                "Resource": f"{ev['code']} - {code_lbl}",
                "Unité de soins": unit,
                "Service technique": service,
                "Date/heure d'événement": dt_evt,
                "Temps passé" if not is_last else "Temps passé en cours": diff_str(ev["dt"], next_dt if not is_last else None)
            })
            continue

        if ev["code"] == "A03":
            total = diff_str(admission_dt, ev["dt"])
            result.append({
                "NSEJ": ev["nsej"],
                "CBMRN": ev["cbmrn"],
                "Resource": f"{ev['code']} - {code_lbl}",
                "Unité de soins": unit,
                "Service technique": service,
                "Date/heure de sortie": dt_evt,
                "Durée totale de séjour": total
            })
            break

    return result





@app.get(
    "/tableaudebord/patient-counts-advanced-v2",
    response_model=PatientCountsResponse
)
def patient_counts_advanced_v2(
    start_date: date = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date:   date = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
) -> PatientCountsResponse:
    """
    Pour chaque jour de [start_date…end_date], renvoie :
      - total_patients : nombre de patients dans l'hôpital
      - by_unit : { unité: patients dans cette unité }
    """
    # 1) Période par défaut = 30 derniers jours
    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = end_date - timedelta(days=29)

    # 2) Collecte des événements A01/A02/A03 (identique à la version précédente)
    events: List[Tuple[datetime, str, Tuple[str,str], str]] = []
    def collect(msg, code_field, time_field, pat_field, seq_field, unit_field):
        d = msg.__dict__
        code = (d.get(code_field) or "").upper()
        if code not in {"A01","A02","A03"}:
            return
        ts = d.get(time_field)
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except:
            return
        key = (d.get(pat_field), d.get(seq_field))
        unit = d.get(unit_field) or "Inconnu"
        events.append((dt, code, key, unit))

    wish = db.query(HL7MessageWish).filter(HL7MessageWish.clrs_cd.in_(["A01","A02","A03"])).all()
    orline = db.query(HL7MessageOrline).filter(HL7MessageOrline.message_type.in_(["A01","A02","A03"])).all()
    for m in wish:
        collect(m, "clrs_cd",      "cltima",      "cbmrn",  "nsej",      "clnsid")
    for m in orline:
        collect(m, "message_type", "date_message","id_pat", "id_sejour", "Service_Name")

    # 3) Trier tous les événements
    events.sort(key=lambda x: x[0])

    # 4) Initialisation avant start_date
    total = 0
    by_unit = defaultdict(int)
    current_stay_unit: Dict[Tuple[str,str], str] = {}
    for dt, code, key, unit in events:
        if dt.date() >= start_date:
            break
        if code == "A01":
            total += 1
            by_unit[unit] += 1
            current_stay_unit[key] = unit
        elif code == "A02" and key in current_stay_unit:
            old = current_stay_unit[key]
            by_unit[old] -= 1
            by_unit[unit] += 1
            current_stay_unit[key] = unit
        elif code == "A03" and key in current_stay_unit:
            total -= 1
            old = current_stay_unit.pop(key)
            by_unit[old] -= 1

    # 5) Parcours jour par jour
    daily: List[DailyCount] = []
    idx = 0
    num_days = (end_date - start_date).days + 1
    for i in range(num_days):
        d = start_date + timedelta(days=i)
        hourly_counts: List[HourlyCount] = []

        for h in range(24):
            current_hour = datetime.combine(d, datetime.min.time()) + timedelta(hours=h)
            next_hour = current_hour + timedelta(hours=1)

            # Appliquer les événements de cette heure
            while idx < len(events) and current_hour <= events[idx][0] < next_hour:
                _, code, key, unit = events[idx]
                if code == "A01":
                    total += 1
                    by_unit[unit] += 1
                    current_stay_unit[key] = unit
                elif code == "A02" and key in current_stay_unit:
                    old = current_stay_unit[key]
                    by_unit[old] -= 1
                    by_unit[unit] += 1
                    current_stay_unit[key] = unit
                elif code == "A03" and key in current_stay_unit:
                    total -= 1
                    old = current_stay_unit.pop(key)
                    by_unit[old] -= 1
                idx += 1

            snapshot = {u: cnt for u, cnt in by_unit.items() if cnt > 0}
            hourly_counts.append(HourlyCount(
                hour=f"{h:02d}:00",
                total_patients=total,
                by_unit=snapshot.copy()
            ))

        daily.append(DailyCount(
            date=d,
            hourly_counts=hourly_counts
        ))

    return PatientCountsResponse(
        start_date=start_date,
        end_date=end_date,
        daily_counts=daily
    )









########################################################################################################################################################







import os
import io
import logging
import time

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from collections import defaultdict
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd
from contextlib import asynccontextmanager
from app.database import SessionLocal, create_tables
from app.models import HL7MessageWish, HL7MessageOrline
from app.schemas import HL7MessageWishSchema, HL7MessageOrlineSchema
from app.crud import create_wish_message, create_orline_message


create_tables()
logging.basicConfig(level=logging.INFO)


fake_users_db = {}
import os
import io
import pandas as pd
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
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
WATCHED_FOLDERS = {
    r"C:\Users\sbenayed\Desktop\WISH_ADT - Copie 14_05\WISH_ADT - Copie": "WISH",
    r"C:\Users\sbenayed\Desktop\ORL_SIU - Copie": "ORLine",
    r"C:\Users\sbenayed\Desktop\ORL_ADT - Copie": "ORLine",
}

SUPPORTED_EXTENSIONS = [".hl7", ".txt", ".dat", ".xml"]


class HourlyCount(BaseModel):
    hour: str  # au lieu de int
    total_patients: int
    by_unit: Dict[str, int]

class DailyCount(BaseModel):
    date: date
    hourly_counts: List[HourlyCount]
class PatientCountsResponse(BaseModel):
    start_date: date
    end_date: date
    daily_counts: List[DailyCount]



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

class HL7Handler(FileSystemEventHandler):
    def __init__(self, source: str):
        super().__init__()
        self.source = source

    def on_created(self, event):
        if not event.is_directory:
            self._process(event.src_path)

    def on_moved(self, event):
        # Fichiers copiés depuis l’explorateur arrivent souvent via un move
        if not event.is_directory:
            self._process(event.dest_path)

    def on_modified(self, event):
        # Couvrir d’éventuelles modifications in-place
        if not event.is_directory:
            self._process(event.src_path)

    def _process(self, path: str):
        # Laisser Windows finir la copie
        time.sleep(0.1)

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return

        logging.info(f"→ Processing HL7 file {path} as {ext}")
        db = SessionLocal()
        try:
            # Lecture en UTF-8 ou ISO-8859-1
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(path, "r", encoding="iso-8859-1") as f:
                    content = f.read()

            # Insertion en base
            if self.source == "WISH":
                create_wish_message(db, content)
            else:
                create_orline_message(db, content)

            # Suppression
            os.remove(path)
            logging.info(f"✓ Handled and removed {path}")
        except Exception as e:
            logging.error(f"Error processing {path}: {e}")
        finally:
            db.close()
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("▶️ Lifespan startup begin") 
    app.state.observers = []

    # 1) Backlog : traiter les fichiers déjà présents
    for path, source in WATCHED_FOLDERS.items():
        os.makedirs(path, exist_ok=True)
        handler = HL7Handler(source)
        # Timeout plus court pour quasi-temps réel
        obs = Observer(timeout=0.5)
        obs.schedule(handler, path, recursive=False)
        obs.start()
        logging.info(f"Watcher (real-time) started on {path}")
        app.state.observers.append(obs)
        for fname in os.listdir(path):
            full = os.path.join(path, fname)
            ext = os.path.splitext(full)[1].lower()
            if os.path.isfile(full) and ext in SUPPORTED_EXTENSIONS:
                logging.info(f"Backlog processing existing file {full}")
                db = SessionLocal()
                try:
                    # Lecture robuste du contenu
                    try:
                        with open(full, "r", encoding="utf-8") as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        with open(full, "r", encoding="iso-8859-1") as f:
                            content = f.read()

                    # Insertion en base
                    if source == "WISH":
                        create_wish_message(db, content)
                    else:
                        create_orline_message(db, content)

                    # Suppression du fichier
                    #os.remove(full)
                    #logging.info(f"Backlog removed {full}")
                finally:
                    db.close()

    # 2) Démarrage des observers pour les nouveaux fichiers
    for path, source in WATCHED_FOLDERS.items():
        handler = HL7Handler(source)
        obs = Observer()
        obs.schedule(handler, path, recursive=False)
        obs.start()
        logging.info(f"Watcher started on {path} (source={source})")
        app.state.observers.append(obs)
    logging.info("▶️ Lifespan startup end") 
    yield  # l’app démarre ici
    logging.info("⏹ Lifespan shutdown")
    # 3) Arrêt propre
    for obs in app.state.observers:
        obs.stop()
        obs.join()
        logging.info("Watcher stopped cleanly")

# --- Instanciation de l’app ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://http://localhost:3001"],
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
        wish_df["clrs_cd"] = wish_df["clrs_cd"].map({
            "A01": "A",
            "A02": "T",
            "A03": "D"
        })
    if "clfrom" in wish_df.columns:
       wish_df["clfrom"] = pd.to_datetime(wish_df["clfrom"], errors="coerce")
       wish_df = wish_df.sort_values(by=["cbmrn", "clfrom"])
    if "clnsid" in wish_df.columns:
       wish_df["nsdscr"] = wish_df["clnsid"].map(unit_names).fillna("")
       wish_df = wish_df[wish_df["clnsid"].isin(unit_names.keys())]
    wish_df["clfrom"] = pd.to_datetime(wish_df["clfrom"], errors="coerce")
    wish_df = wish_df.sort_values(["cbmrn", "nsej", "clnsid", "clfrom"])
    wish_df["prev_clfrom"] = wish_df.groupby(
      ["cbmrn", "nsej", "clnsid"]
    )["clfrom"].shift(1)
    wish_df["delta_min"] = (
       (wish_df["clfrom"] - wish_df["prev_clfrom"])
       .dt.total_seconds() / 60.0
    )
    to_drop = []
    for (pat, sej, unit), grp in wish_df.groupby(["cbmrn", "nsej", "clnsid"]):
       # repère les indices où delta < 5
       short = grp[grp["delta_min"] < 5.0]
       if short.empty:
         continue
       # pour chacun de ces cas, on regarde si l’un des deux a clsvtc == "8BLO"
       for idx in short.index:
          # ligne actuelle et précédente
          prev = grp.loc[idx, "prev_clfrom"]
          cur = grp.loc[idx, "clfrom"]
          # sous-groupe de ces deux lignes
          two = grp[(grp["clfrom"] == prev) | (grp["clfrom"] == cur)]
          if "8BLO" in two["clsvtc"].values:
              # on supprime toutes sauf celle avec 8BLO
              drop_idx = two[two["clsvtc"] != "8BLO"].index
          else:
             # on supprime toutes sauf la plus récente
             drop_idx = [two.index.min()]
          to_drop.extend(drop_idx)

    # ❺ On débarrasse wish_df des lignes indésirables
    wish_df = wish_df.drop(index=set(to_drop))

    # ❻ On peut nettoyer les colonnes intermédiaires
    wish_df = wish_df.drop(columns=["prev_clfrom", "delta_min"])
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
    "8BCE": "SALLE CESARIENNE-MLE",
    "8OUT":"EXAMENS HORS-MLE",
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
    wish_msgs = db.query(HL7MessageWish).filter(HL7MessageWish.cbmrn == id_pat).all()
    orline_msgs = db.query(HL7MessageOrline).filter(HL7MessageOrline.id_pat == id_pat).all()
    all_msgs = [*wish_msgs, *orline_msgs]

    raw: List[Dict] = []
    for msg in all_msgs:
        d = msg.__dict__
        code = (d.get("clrs_cd") or "").upper()
        if code not in {"A01", "A02", "A03"}:
            continue
        dt = format_dt(d.get("cltima"))
        if dt is None:
            continue
        raw.append({
            "nsej": d.get("nsej"),
            "cbmrn": d.get("cbmrn"),
            "clnsid": d.get("clnsid") or "",
            "clsvtc": d.get("clsvtc") or "",
            "dt": dt,
            "code": code
        })

    raw.sort(key=lambda e: e["dt"])
    if not raw:
        raise HTTPException(404, "Aucun événement A01/A02/A03 trouvé.")

    a01_indices = [i for i, e in enumerate(raw) if e["code"] == "A01"]
    if not a01_indices:
        raise HTTPException(404, "Aucun événement d’admission trouvé.")
    last_a01_index = max(a01_indices, key=lambda i: raw[i]["dt"])
    last_admission = raw[last_a01_index]
    raw = [e for i, e in enumerate(raw) if e["code"] != "A01" or i == last_a01_index]

    filtered = []
    i = 0
    while i < len(raw):
        curr = raw[i]
        if i + 1 < len(raw):
            nxt = raw[i + 1]
            delta = nxt["dt"] - curr["dt"]
            same_sej = curr["nsej"] == nxt["nsej"]
            same_unit = curr["clnsid"] == nxt["clnsid"]

            if curr["code"] == "A02" and nxt["code"] == "A02" and same_sej and same_unit and delta < timedelta(minutes=5):
                # Si l’un des deux contient clsvtc prioritaire, garder celui-là
                if nxt["clsvtc"] in {"8BLO", "8REV"}:
                    filtered.append(nxt)
                elif curr["clsvtc"] in {"8BLO", "8REV"}:
                    filtered.append(curr)
                else:
                    filtered.append(nxt)  # garder le plus récent
                i += 2
                continue

            if curr["code"] == "A02" and delta < timedelta(minutes=5) and curr["clsvtc"] not in {"8BLO", "8REV"}:
                i += 1
                continue

        filtered.append(curr)
        i += 1

    admission_dt = last_admission["dt"]
    filtered.insert(0, last_admission)

    result: List[Dict] = []
    for idx, ev in enumerate(filtered):
        is_last = (idx == len(filtered) - 1)
        dt_evt = fmt_str(ev["dt"])
        unit = unit_names.get(ev["clnsid"], ev["clnsid"])
        service = service_technique_names.get(ev["clsvtc"], ev["clsvtc"])
        code_lbl = {"A01": "ADMISSION", "A02": "TRANSFER", "A03": "DISCHARGE"}[ev["code"]]
        next_dt = filtered[idx + 1]["dt"] if idx + 1 < len(filtered) else None

        if ev["code"] == "A01":
            result.append({
                "NSEJ": ev["nsej"],
                "CBMRN": ev["cbmrn"],
                "Resource": f"{ev['code']} - {code_lbl}",
                "Unité de soins": unit,
                "Service technique": service,
                "Date/heure d'événement": dt_evt,
                "Temps passé": diff_str(ev["dt"], next_dt)
            })
            continue

        if ev["code"] == "A02":
            result.append({
                "NSEJ": ev["nsej"],
                "CBMRN": ev["cbmrn"],
                "Resource": f"{ev['code']} - {code_lbl}",
                "Unité de soins": unit,
                "Service technique": service,
                "Date/heure d'événement": dt_evt,
                "Temps passé" if not is_last else "Temps passé en cours": diff_str(ev["dt"], next_dt if not is_last else None)
            })
            continue

        if ev["code"] == "A03":
            total = diff_str(admission_dt, ev["dt"])
            result.append({
                "NSEJ": ev["nsej"],
                "CBMRN": ev["cbmrn"],
                "Resource": f"{ev['code']} - {code_lbl}",
                "Unité de soins": unit,
                "Service technique": service,
                "Date/heure de sortie": dt_evt,
                "Durée totale de séjour": total
            })
            break

    return result




@app.get("/hl7/export-patient/{patient_id}")
def export_patient_messages_to_excel(patient_id: str):
    def extract_from_folder(folder_path: str, patient_id: str) -> list:
        rows = []
        for fname in os.listdir(folder_path):
            if not any(fname.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                continue
            fpath = os.path.join(folder_path, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(fpath, "r", encoding="iso-8859-1") as f:
                    content = f.read()

            # Vérifie la présence de l'ID patient dans les PID
            found = False
            for line in content.splitlines():
                if line.startswith("PID|"):
                    fields = line.split("|")
                    if len(fields) > 3:
                        if patient_id in fields[3].split("^"):
                            found = True
                            break
            if not found:
                continue

            for line in content.splitlines():
                row = [fname] + line.strip().split("|")
                rows.append(row)
        return rows

    # Récupération depuis les dossiers
    wish_data, orline_data = [], []
    for folder_path, label in WATCHED_FOLDERS.items():
        if label == "WISH":
            wish_data.extend(extract_from_folder(folder_path, patient_id))
        elif label == "ORLine":
            orline_data.extend(extract_from_folder(folder_path, patient_id))

    if not wish_data and not orline_data:
        raise HTTPException(404, detail="Aucun message brut trouvé pour ce patient.")

    # Calcul du nombre de colonnes max pour nommer correctement
    wish_cols = max((len(r) for r in wish_data), default=0)
    orline_cols = max((len(r) for r in orline_data), default=0)

    wish_headers = ["Fichier", "Segment"] + [f"Field_{i}" for i in range(1, wish_cols - 1)] if wish_data else []
    orline_headers = ["Fichier", "Segment"] + [f"Field_{i}" for i in range(1, orline_cols - 1)] if orline_data else []

    df_wish = pd.DataFrame(wish_data, columns=wish_headers)
    df_orline = pd.DataFrame(orline_data, columns=orline_headers)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if not df_wish.empty:
            df_wish.to_excel(writer, sheet_name="WISH Messages", index=False)
        if not df_orline.empty:
            df_orline.to_excel(writer, sheet_name="ORLine Messages", index=False)
    output.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="hl7_brut_{patient_id}.xlsx"'
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

@app.get(
    "/tableaudebord/patient-counts-advanced-v2",
    response_model=PatientCountsResponse
)
def patient_counts_advanced_v2(
    start_date: date = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date:   date = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
) -> PatientCountsResponse:
    """
    Pour chaque jour de [start_date…end_date], renvoie :
      - total_patients : nombre de patients dans l'hôpital
      - by_unit : { unité: patients dans cette unité }
    """
    # 1) Période par défaut = 30 derniers jours
    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = end_date - timedelta(days=29)

    # 2) Collecte des événements A01/A02/A03 (identique à la version précédente)
    events: List[Tuple[datetime, str, Tuple[str,str], str]] = []
    def collect(msg, code_field, time_field, pat_field, seq_field, unit_field):
        d = msg.__dict__
        code = (d.get(code_field) or "").upper()
        if code not in {"A01","A02","A03"}:
            return
        ts = d.get(time_field)
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except:
            return
        key = (d.get(pat_field), d.get(seq_field))
        unit = d.get(unit_field) or "Inconnu"
        events.append((dt, code, key, unit))

    wish = db.query(HL7MessageWish).filter(HL7MessageWish.clrs_cd.in_(["A01","A02","A03"])).all()
    orline = db.query(HL7MessageOrline).filter(HL7MessageOrline.message_type.in_(["A01","A02","A03"])).all()
    for m in wish:
        collect(m, "clrs_cd",      "cltima",      "cbmrn",  "nsej",      "clnsid")
    for m in orline:
        collect(m, "message_type", "date_message","id_pat", "id_sejour", "Service_Name")

    # 3) Trier tous les événements
    events.sort(key=lambda x: x[0])

    # 4) Initialisation avant start_date
    total = 0
    by_unit = defaultdict(int)
    current_stay_unit: Dict[Tuple[str,str], str] = {}
    for dt, code, key, unit in events:
        if dt.date() >= start_date:
            break
        if code == "A01":
            total += 1
            by_unit[unit] += 1
            current_stay_unit[key] = unit
        elif code == "A02" and key in current_stay_unit:
            old = current_stay_unit[key]
            by_unit[old] -= 1
            by_unit[unit] += 1
            current_stay_unit[key] = unit
        elif code == "A03" and key in current_stay_unit:
            total -= 1
            old = current_stay_unit.pop(key)
            by_unit[old] -= 1

    # 5) Parcours jour par jour
    daily: List[DailyCount] = []
    idx = 0
    num_days = (end_date - start_date).days + 1
    for i in range(num_days):
        d = start_date + timedelta(days=i)
        hourly_counts: List[HourlyCount] = []

        for h in range(24):
            current_hour = datetime.combine(d, datetime.min.time()) + timedelta(hours=h)
            next_hour = current_hour + timedelta(hours=1)

            # Appliquer les événements de cette heure
            while idx < len(events) and current_hour <= events[idx][0] < next_hour:
                _, code, key, unit = events[idx]
                if code == "A01":
                    total += 1
                    by_unit[unit] += 1
                    current_stay_unit[key] = unit
                elif code == "A02" and key in current_stay_unit:
                    old = current_stay_unit[key]
                    by_unit[old] -= 1
                    by_unit[unit] += 1
                    current_stay_unit[key] = unit
                elif code == "A03" and key in current_stay_unit:
                    total -= 1
                    old = current_stay_unit.pop(key)
                    by_unit[old] -= 1
                idx += 1

            snapshot = {u: cnt for u, cnt in by_unit.items() if cnt > 0}
            hourly_counts.append(HourlyCount(
                hour=f"{h:02d}:00",
                total_patients=total,
                by_unit=snapshot.copy()
            ))

        daily.append(DailyCount(
            date=d,
            hourly_counts=hourly_counts
        ))

    return PatientCountsResponse(
        start_date=start_date,
        end_date=end_date,
        daily_counts=daily
    )
