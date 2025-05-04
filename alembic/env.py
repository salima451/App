from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 🛠️ Ajout du chemin pour accéder au module app
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 🔁 Import du Base des modèles SQLAlchemy
from app.database import Base  # veille à ce que app/database.py contient bien Base = declarative_base()

# 📦 Alembic config
config = context.config

# 📋 Logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 📌 C'est ici qu'on active l'autogénération avec SQLAlchemy
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (sans connexion live)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connexion live à la base)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True  # utile pour détecter les changements de types
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
