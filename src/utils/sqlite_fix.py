"""
SQLite Compatibility Fix for Streamlit Cloud Deployment

This module ensures SQLite compatibility across different deployment environments,
particularly for Streamlit Cloud which may have older SQLite versions.
"""

import sys
import os

def fix_sqlite():
    """
    Fix SQLite compatibility issues for ChromaDB deployment.
    
    This function attempts to use pysqlite3-binary as a replacement
    for the system SQLite3 if the version is too old.
    """
    try:
        # Try to import pysqlite3 and replace sqlite3 module
        import pysqlite3
        sys.modules['sqlite3'] = pysqlite3
        print("✅ SQLite compatibility fix applied successfully")
        return True
    except ImportError:
        # If pysqlite3 is not available, check if system sqlite3 is sufficient
        try:
            import sqlite3
            # Check SQLite version
            version = sqlite3.sqlite_version
            major, minor, patch = map(int, version.split('.'))
            
            if major > 3 or (major == 3 and minor >= 35):
                print(f"✅ System SQLite version {version} is compatible")
                return True
            else:
                print(f"⚠️  System SQLite version {version} may be incompatible")
                print("   Consider installing pysqlite3-binary for better compatibility")
                return False
        except Exception as e:
            print(f"❌ SQLite compatibility check failed: {e}")
            return False

def get_sqlite_info():
    """Get information about the current SQLite installation."""
    try:
        import sqlite3
        return {
            'version': sqlite3.sqlite_version,
            'module_path': sqlite3.__file__ if hasattr(sqlite3, '__file__') else 'Built-in',
            'compatible': True
        }
    except Exception as e:
        return {
            'version': 'Unknown',
            'module_path': 'Unknown',
            'compatible': False,
            'error': str(e)
        }

# Apply the fix when this module is imported
if __name__ != "__main__":
    fix_sqlite()
