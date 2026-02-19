# config.py
"""
Módulo de configuración para centralizar parámetros de la base de datos.
"""
import os

DB_SERVER = os.getenv('DB_SERVER', '148.204.107.22')
DB_NAME = os.getenv('DB_NAME', 'Base_pruebas')
DB_USER = os.getenv('DB_USER', 'sa')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'emmanuel280900')
