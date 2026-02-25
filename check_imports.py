import importlib
import sys
modules=[
    'main','app.handlers','app.handlers.start','app.handlers.flow',
    'app.handlers.menu','app.handlers.subscription','app.handlers.stats',
    'app.handlers.notifications','app.handlers.admin'
]
for m in modules:
    try:
        importlib.import_module(m)
        print(f'{m} imported ok')
    except Exception as e:
        print(f'{m} import error: {e}')
