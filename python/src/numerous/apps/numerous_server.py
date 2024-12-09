import argparse
import uvicorn
import importlib
from pathlib import Path
from .backend import Backend

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run a Numerous application server')
    parser.add_argument('app', help='Application import path (e.g. "myapp.main:app")')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to (default: 8000)')
    parser.add_argument('--log-level', default='INFO', 
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      help='Set the logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Parse the app import path
    module_path, app_name = args.app.split(':')
    
    abs_module_path = Path(module_path).resolve()
    is_file = abs_module_path.is_file()

    backend = Backend(abs_module_path, app_name, is_file, log_level=args.log_level)
    backend.run()
    
if __name__ == '__main__':
    main()
