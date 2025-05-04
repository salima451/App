# app/schemas.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# ✅ Schéma pour créer un message HL7
class HL7MessageCreate(BaseModel):
    message_content: str = Field(..., description="Le contenu XML complet du message HL7")
    source: str = Field(..., description="Source du message (ex: WISH ou ORLINE)")

# ✅ Schéma pour afficher les messages WISH
class HL7MessageWishSchema(BaseModel):
    id: int
    message_id: Optional[str] = None
    date_message: Optional[str] = None
    clrs_cd: Optional[str] = None
    nsej: Optional[str] = None
    cbmrn: Optional[str] = None
    cbtype: Optional[str] = None
    cbadty: Optional[str] = None
    tsv: Optional[str] = None
    clfrom: Optional[str] = None
    clnsid: Optional[str] = None
    nsdscr: Optional[str] = None
    clroom: Optional[str] = None
    clbed: Optional[str] = None
    clsvtc: Optional[str] = None
    tectxtfr: Optional[str] = None
    cldept: Optional[str] = None
    nrpr: Optional[str] = None
    nomm: Optional[str] = None
    cltima: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ✅ Schéma pour afficher les messages ORLINE
class HL7MessageOrlineSchema(BaseModel):
    id: int
    message_id: Optional[str]
    date_message: Optional[str]
    message_type: Optional[str]
    id_pat: Optional[str]
    id_sejour: Optional[str]
    id_ope: Optional[str]
    date_ope: Optional[str]
    date_ope_prev: Optional[str]
    planning: Optional[str]
    heu_deb_ope_prev: Optional[str]
    id_sal_ope: Optional[str]
    arr_sal_ope: Optional[str]
    tps_ope_prev: Optional[str]
    heu_fin_ope_prev: Optional[str]
    anesth: Optional[str]
    discip: Optional[str]
    type_ope: Optional[str]
    chir: Optional[str]
    naissance: Optional[str]
    sexe: Optional[str]

    model_config = ConfigDict(from_attributes=True)
