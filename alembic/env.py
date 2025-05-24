from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
from sqlalchemy import create_engine
from empPortal.models import Base  # Import your SQLAlchemy models
import os
import django

# Ensure Django is initialized
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xtraTrustInsurance.settings")
django.setup()

from empPortal.models import Base  # Import your SQLAlchemy models


# Load Alembic Config
config = context.config

# Load logging configuration
fileConfig(config.config_file_name)

# Define the target metadata (IMPORTANT)
target_metadata = Base.metadata  # Ensure your models have a Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(config.get_section(config.config_ini_section),
                                     prefix="sqlalchemy.",
                                     poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
