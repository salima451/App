# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Ton URL PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:HOSPITWIN@localhost:5432/test_db"

# Création de l'engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"options": "-c client_encoding=UTF8"},
    pool_pre_ping=True
)

# Session locale
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour tous tes modèles
Base = declarative_base()

# Fonction pour obtenir la session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✨ Fonction pour créer toutes les tables
def create_tables():
    from app import models  # Assure-toi que app/models.py existe
    Base.metadata.create_all(bind=engine)
