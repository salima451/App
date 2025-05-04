from datetime import datetime

def extract_pv1_room_info(pv1_3: str):
    clnsid = clroom = clbed = clsvtc = ""

    if pv1_3:
        parts = pv1_3.split('^')
        clnsid = parts[0] if len(parts) > 0 else ""
        clroom = parts[1] if len(parts) > 1 else ""
        clbed = parts[2] if len(parts) > 2 else ""

        if len(parts) > 6:
            last_part = parts[6]
            if '-' in last_part:
                clsvtc = last_part.split('-')[-1]
            else:
                clsvtc = ""

    return clnsid, clroom, clbed, clsvtc
def convert_hl7_datetime(dt_str):
    try:
        return datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def parse_details_hl7_wish_specific(hl7_message):
    lignes = hl7_message.strip().splitlines()

    msh = evn = pid = pv1 = None

    for ligne in lignes:
        champs = ligne.strip().split("|")
        if not champs:
            continue
        segment = champs[0].strip().upper()
        if segment == "MSH":
            msh = champs
        elif segment == "EVN":
            evn = champs
        elif segment == "PID":
            pid = champs
        elif segment == "PV1":
            pv1 = champs
    
    # 👉 EXTRACTION message_id
    message_id = msh[9] if msh and len(msh) > 9 else None

    clrs_cd = evn[1] if evn and len(evn) > 1 else None
    
    clfrom_raw = evn[2] if evn and len(evn) > 2 else None
    clfrom = convert_hl7_datetime(clfrom_raw)
    cbmrn = pid[3] if pid and len(pid) > 3 else None
    cbtype = pv1[2] if pv1 and len(pv1) > 2 else None
    cbadty = pv1[4].split("^")[0] if pv1 and len(pv1) > 4 else None

    nsej = None
    if pv1 and len(pv1) > 19 and pv1[19]:
        nsej = pv1[19]
        if nsej.startswith("1"):
            nsej = nsej[1:]

    # ✅ Utilisation réelle de extract_pv1_room_info sur pv1[3]
    clnsid = clroom = clbed = clsvtc = ""
    if pv1 and len(pv1) > 3:
        clnsid, clroom, clbed, clsvtc = extract_pv1_room_info(pv1[3])

    # ✅ tectxtfr dépend de clsvtc
    if clsvtc == "8BLO":
        tectxtfr = "BLOC OPERTAOIRE-MLE"
    elif clsvtc == "8REV":
        tectxtfr = "SALLE REVEIL-MLE"
    else:
        tectxtfr = ""

    cldept = pv1[10] if pv1 and len(pv1) > 10 else None
    nrpr = pv1[7].split("^")[0] if pv1 and len(pv1) > 7 else None

    nomm = None
    try:
        nomm_parts = pv1[7].split("^")
        nomm = f"{nomm_parts[1]}, {nomm_parts[2]}" if len(nomm_parts) >= 3 else None
    except Exception:
        nomm = None

    cltima_raw = msh[6] if msh and len(msh) > 6 else None
    cltima = convert_hl7_datetime(cltima_raw)

    # ✅ date_message formatée
    date_message = None
    if msh and len(msh) > 3 and msh[3]:
        try:
            msh_3_parts = msh[3].split('^')
            if len(msh_3_parts) > 1:
                raw_datetime = msh_3_parts[1][:14]  # Prend exactement "20250407010834"
                date_obj = datetime.strptime(raw_datetime, "%Y%m%d%H%M%S")
                date_message = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_message = None

    clnsid_to_nsdscr = {
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
        "415": "415-HOPITAL DE JOUR CHIRURGICAL",
    }

    nsdscr = clnsid_to_nsdscr.get(clnsid, "")

    return [{
        "message_id": message_id,
        "date_message": date_message,
        "clrs_cd": clrs_cd,
        "nsej": nsej,
        "cbmrn": cbmrn,
        "cbtype": cbtype,
        "cbadty": cbadty,
        "tsv": "U/I",
        "clfrom": clfrom,
        "clnsid": clnsid,
        "nsdscr": nsdscr,
        "clroom": clroom,
        "clbed": clbed,
        "clsvtc": clsvtc,
        "tectxtfr": tectxtfr,
        "cldept": cldept,
        "nrpr": nrpr,
        "nomm": nomm,
        "cltima": cltima
        
    }]
