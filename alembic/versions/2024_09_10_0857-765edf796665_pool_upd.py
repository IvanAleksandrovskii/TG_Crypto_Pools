"""empty message

Revision ID: 765edf796665
Revises: 23b84313a680
Create Date: 2024-09-10 08:57:04.005196

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '765edf796665'
down_revision: Union[str, None] = '23b84313a680'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('pools', 'website_url',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('pools', 'website_url',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
