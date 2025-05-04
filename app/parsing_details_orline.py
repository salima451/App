from datetime import datetime

def format_date_jj_mm_aaaa_hh_mm_ss(date_str):
    try:
        return datetime.strptime(date_str, "%Y%m%d%H%M%S").strftime("%d-%m-%Y %H:%M:%S")
    except Exception:
        return None

def format_date_jj_mm_aaaa(date_str):
    try:
        return datetime.strptime(date_str[:8], "%Y%m%d").strftime("%d-%m-%Y")
    except Exception:
        return None

def format_heure_hh_mm_ss(time_str):
    try:
        return datetime.strptime(time_str, "%H%M%S").strftime("%H:%M:%S")
    except Exception:
        return None

def parse_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def parse_details_hl7_orline_specific(hl7_message):
    lignes = hl7_message.strip().splitlines()

    champs = {
        "message_id": None,
        "date_message": None,
        "message_type": None,
        "id_pat": None,
        "id_sejour": None,
        "id_ope": None,
        "date_ope": None,
        "date_ope_prev": None,
        "planning": None,
        "heu_deb_ope_prev": None,
        "id_sal_ope": None,
        "arr_sal_ope": None,
        "heu_fin_ope_prev": None,
        "anesth": None,
        "discip": None,
        "type_ope": None,
        "chir": None,
        "naissance": None,
        "sexe": None,
        "tps_ope_prev": None
    }

    for ligne in lignes:
        parties = ligne.strip().split("|")
        segment = parties[0]

        if segment == "MSH":
            champs["message_id"] = parties[9] if len(parties) > 9 else None
            champs["date_message"] = format_date_jj_mm_aaaa_hh_mm_ss(parties[6]) if len(parties) > 6 else None
            champs["message_type"] = parties[8].split("^")[0] if len(parties) > 8 and "^" in parties[8] else None
            if len(parties) > 10 and "^ORLine" in parties[10]:
                champs["id_ope"] = parties[10].split("^")[0]

        elif segment == "PID":
            champs["id_pat"] = parties[3] if len(parties) > 3 else None
            champs["naissance"] = format_date_jj_mm_aaaa(parties[7]) if len(parties) > 7 else None
            champs["sexe"] = parties[8] if len(parties) > 8 else None

        elif segment == "PV1":
            if len(parties) > 19:
                id_sejour = parties[19]
                champs["id_sejour"] = id_sejour[1:] if id_sejour.startswith("1") else id_sejour
            if not champs["id_ope"]:
        # on parcourt chaque champ à la recherche de celui qui se termine par ^^^ORLine
              for fld in parties:
                 if fld.endswith("^^^ORLine"):
                # on prend tout ce qui est avant le premier caret
                     champs["id_ope"] = fld.split("^", 1)[0]
                     break
            if not champs["id_sal_ope"] and len(parties) > 3:
                for comp in parties[3].split("^"):
                    if comp.startswith("BLOCMLE."):
                        champs["id_sal_ope"] = comp.split(".")[1]
                        break
        elif segment == "PV2":
             print("PV2 parties:", parties)
             if len(parties) > 8 and parties[8]:
                print("Arrivée salle brute:", parties[8])
                champs["arr_sal_ope"] =  datetime.strptime(parties[8], "%Y%m%d%H%M%S")

        elif segment == "SCH":
            # ID OPE (alternative)
            if not champs["id_ope"] and len(parties) > 1:
                champs["id_ope"] = parties[1].split("^")[0]

            # Extraction des données de timing
            if len(parties) > 11:
                sch_info = parties[11].split("^")
                if len(sch_info) >= 5:
                    date_ope_str = sch_info[3]
                    date_ope_prev = format_date_jj_mm_aaaa(date_ope_str)
                    champs["date_ope_prev"] = date_ope_prev
                    champs["date_ope"] = date_ope_prev  # même valeur sauf info contradictoire
                    champs["heu_deb_ope_prev"] = format_heure_hh_mm_ss(date_ope_str[8:14])
                    champs["heu_fin_ope_prev"] = format_heure_hh_mm_ss(sch_info[4][8:14])
                    champs["tps_ope_prev"] = sch_info[2]

                    # Calcul du planning
                    try:
                        d_prev = datetime.strptime(date_ope_prev, "%d-%m-%Y")
                        d_ope = d_prev  # même date sauf info contradictoire
                        delta = (d_ope - d_prev).days
                        if delta == 0:
                            champs["planning"] = "D0"
                        elif delta < 7:
                            champs["planning"] = ">D1,<D7"
                        else:
                            champs["planning"] = ">D7"
                    except:
                        champs["planning"] = None

            # Type d’opération
            if len(parties) > 7:
                type_ope_info = parties[7].split("^")
                champs["type_ope"] = type_ope_info[1] if len(type_ope_info) > 1 else None

            # Chirurgien
            if len(parties) > 20 and parties[20].strip():
                champs["chir"] = parties[20].strip()

        elif segment == "OBX" and len(parties) > 4 and "ANESTHESIA" in parties[3]:
            champs["anesth"] = parties[5] if len(parties) > 5 else None

        elif segment == "AIP":
            if len(parties) > 4:
                aip_info = parties[4].split("^")
                champs["discip"] = aip_info[-1] if aip_info else None

        elif segment == "AIL":
            if len(parties) > 3 and "." in parties[3]:
                champs["id_sal_ope"] = parties[3].split(".")[1][:2]

    return champs
