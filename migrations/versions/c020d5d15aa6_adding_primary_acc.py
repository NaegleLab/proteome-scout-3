"""adding primary acc

Revision ID: c020d5d15aa6
Revises: 
Create Date: 2024-05-28 12:47:45.227223

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'c020d5d15aa6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('protein_acc', sa.Column('primary_acc', sa.Boolean(), nullable=True))

    
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.drop_column('protein_acc', 'primary_acc')
    
    # ### end Alembic commands ###
