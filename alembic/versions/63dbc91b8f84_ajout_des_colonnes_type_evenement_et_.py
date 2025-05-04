"""Ajout des colonnes type_evenement et date_event dans hl7_message_wish

Revision ID: abcdef123456
Revises: <id de la révision précédente>
Create Date: 2025-04-01 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# Révision identifiers, utilisés par Alembic.
revision = 'abcdef123456'
down_revision = None  # Remplacez par l'ID correspondant
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('hl7_message_wish', sa.Column('type_evenement', sa.String(), nullable=True))
    op.add_column('hl7_message_wish', sa.Column('date_event', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('hl7_message_wish', 'date_event')
    op.drop_column('hl7_message_wish', 'type_evenement')
