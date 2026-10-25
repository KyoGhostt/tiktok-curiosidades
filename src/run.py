import os, runpy
mode = os.environ.get("MODE", "historias")
runpy.run_path(os.path.join(os.path.dirname(__file__), "main_story.py" if mode == "historias" else "main.py"), run_name="__main__")
