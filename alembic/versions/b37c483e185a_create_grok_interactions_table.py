"""create_grok_interactions_table

Revision ID: b37c483e185a
Revises: 9ebc95ca31d0
Create Date: 2025-09-28 22:21:11.856450

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b37c483e185a"
down_revision: Union[str, Sequence[str], None] = "9ebc95ca31d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Removed the unused Books table
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Removed the Books table creation logic
    pass
