# app/crud.py

from sqlalchemy.orm import Session
from app.models import HL7MessageWish, HL7MessageOrline
from app.parsing_details_orline import parse_details_hl7_orline_specific
from app.parsing_details_wish import parse_details_hl7_wish_specific
from sqlalchemy import inspect
from sqlalchemy.exc import InvalidRequestError


def create_wish_message(db: Session, hl7_raw_message: str) -> HL7MessageWish:
    parsed_data_list = parse_details_hl7_wish_specific(hl7_raw_message)
    last_msg = None
    for parsed_data in parsed_data_list:
        db_message = HL7MessageWish(
            **parsed_data  
        )
        db.add(db_message)
        db.flush()
        try:
            db.refresh(db_message)
        except InvalidRequestError:
            db_message = db.query(HL7MessageWish).get(db_message.id)
        last_msg = db_message
    db.commit()
    return last_msg

def create_orline_message(db: Session, hl7_raw_message: str)-> HL7MessageOrline:
    parsed = parse_details_hl7_orline_specific(hl7_raw_message)

    mapper = inspect(HL7MessageOrline)
    valid_cols = {col.key for col in mapper.columns}

    # Keep only those keys that map to actual DB columns
    filtered_data = {k: v for k, v in parsed.items() if k in valid_cols}

    db_message = HL7MessageOrline(**filtered_data)
    db.add(db_message)

    # Flush to assign PK
    db.flush()

    # Refresh or re-query if detached
    try:
        db.refresh(db_message)
    except InvalidRequestError:
        db_message = db.query(HL7MessageOrline).get(db_message.id)

    # Commit the transaction
    db.commit()
    return db_message