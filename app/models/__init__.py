# Prateek: Import all models here so Base.metadata.create_all() in main.py sees every table.
from app.models.user import User  # noqa: F401
from app.models.llm_usage import LLMUsage  # noqa: F401
