"""O projeto Scratch "Pista Turbo" é gerado e é coerente."""
import importlib.machinery
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
gerar = importlib.machinery.SourceFileLoader(
    "gerar_pista", str(ROOT / "beni/ferramentas/gerar-pista-turbo.py")).load_module()


class PistaTurboTest(unittest.TestCase):
    def test_generated_project_is_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p.sb3"
            gerar.main(["x", str(out)])
            with zipfile.ZipFile(out) as z:
                project = json.loads(z.read("project.json"))
                names = set(z.namelist())
        stage, carro = project["targets"]
        for target in (stage, carro):
            for costume in target["costumes"]:
                self.assertIn(costume["md5ext"], names)
        blocks = carro["blocks"]
        for bid, block in blocks.items():
            if block["next"]:
                self.assertEqual(blocks[block["next"]]["parent"], bid)
            for value in block["inputs"].values():
                for item in value[1:]:
                    if isinstance(item, str):
                        self.assertEqual(blocks[item]["parent"], bid)
        variables = {v[0] for v in stage["variables"].values()}
        self.assertTrue({"velocidade", "voltas", "velocidade máxima", "voltas para vencer"} <= variables)

    def test_committed_copy_matches_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p.sb3"
            gerar.main(["x", str(out)])
            with zipfile.ZipFile(out) as a, zipfile.ZipFile(ROOT / "src/scratch/Pista Turbo.sb3") as b:
                self.assertEqual(json.loads(a.read("project.json")), json.loads(b.read("project.json")))


if __name__ == "__main__":
    unittest.main()
