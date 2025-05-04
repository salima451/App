# app/models.py

from sqlalchemy import Column, Integer, String
from app.database import Base

# ✅ Classe pour la table hl7_message_wish
class HL7MessageWish(Base):
    __tablename__ = "hl7_message_wish"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, nullable=True)
    date_message = Column(String, nullable=True)
    clrs_cd = Column(String, nullable=True)
    nsej = Column(String, nullable=True)
    cbmrn = Column(String, nullable=True)
    cbtype = Column(String, nullable=True)
    cbadty = Column(String, nullable=True)
    tsv = Column(String, nullable=True)
    clfrom = Column(String, nullable=True)
    clnsid = Column(String, nullable=True)
    nsdscr=  Column(String, nullable=True)
    clroom = Column(String, nullable=True)
    clbed = Column(String, nullable=True)
    clsvtc = Column(String, nullable=True)
    tectxtfr = Column(String, nullable=True)
    cldept = Column(String, nullable=True)
    nrpr = Column(String, nullable=True)
    nomm = Column(String, nullable=True)
    cltima = Column(String, nullable=True)

# ✅ Classe pour la table hl7_message_orline
class HL7MessageOrline(Base):
    __tablename__ = "hl7_message_orline"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, nullable=True)
    date_message = Column(String, nullable=True)
    message_type = Column(String, nullable=True)
    id_pat = Column(String, nullable=True)
    id_sejour = Column(String, nullable=True)
    id_ope = Column(String, nullable=True)
    date_ope = Column(String, nullable=True)
    date_ope_prev = Column(String, nullable=True)
    planning = Column(String, nullable=True)
    heu_deb_ope_prev = Column(String, nullable=True)
    id_sal_ope = Column(String, nullable=True)
    tps_ope_prev = Column(String, nullable=True)
    heu_fin_ope_prev = Column(String, nullable=True)  
    anesth = Column(String, nullable=True)
    discip = Column(String, nullable=True)
    type_ope = Column(String, nullable=True)
    chir = Column(String, nullable=True)
    naissance = Column(String, nullable=True)
    sexe = Column(String, nullable=True)
    arr_sal_ope = Column(String, nullable=True)
