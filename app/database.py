# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Configuración de la base de datos SQLite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'inventario.db')}"

# Crear motor de base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Solo para SQLite
    echo=True  # Muestra SQL en consola (útil para desarrollo)
)

# Crear fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()

# Dependencia para obtener sesión de BD
def get_db():
    """
    Proporciona una sesión de base de datos para cada request.
    Se cierra automáticamente al final.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Crear todas las tablas en la base de datos"""
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada")
def init_db():
    Base.metadata.create_all(bind=engine)
    
    # 🆕 Migración para agregar columna si no existe
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    
    if 'movimientos' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('movimientos')]
        
        if 'cliente_destino' not in columns:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE movimientos ADD COLUMN cliente_destino VARCHAR'))
                conn.commit()
                print("Columna cliente_destino agregada a movimientos")