from app.db.base import Base
from app.db.session import engine

# Import all models so they register with Base
from app.models import user
from app.models import invoice
from app.models import tax
from app.models import audit
from app.models import accounting
from app.models import report

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully 🚀")
