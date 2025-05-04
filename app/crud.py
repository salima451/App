# app/crud.py

from sqlalchemy.orm import Session
from app.models import HL7MessageWish, HL7MessageOrline
from app.parsing_details_orline import parse_details_hl7_orline_specific
from app.parsing_details_wish import parse_details_hl7_wish_specific
from sqlalchemy import inspect

def create_wish_message(db: Session, hl7_raw_message: str):
    parsed_data_list = parse_details_hl7_wish_specific(hl7_raw_message)

    for parsed_data in parsed_data_list:
        db_message = HL7MessageWish(
            **parsed_data  
        )
        db.add(db_message)

    db.commit()
    db.refresh(db_message)
    return db_message

def create_orline_message(db: Session, hl7_raw_message: str):
    parsed = parse_details_hl7_orline_specific(hl7_raw_message)

    mapper = inspect(HL7MessageOrline)
    cols = {c.key for c in mapper.columns}
    filtered = {k: v for k, v in parsed.items() if k in cols}

    db_message = HL7MessageOrline(**filtered)
    db.add(db_message)
    db.flush()           # ← important
    db.refresh(db_message)
    db.commit()
    return db_message
