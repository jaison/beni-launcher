"""Atualizador automático (beni/sistema/beni-atualizar) e mudanças de catálogo."""
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load_module(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


atualizar = load_module("beni_atualizar", ROOT / "beni/sistema/beni-atualizar")
migrar = load_module("migrar_config", ROOT / "beni/ferramentas/migrar-config.py")


class UpdaterTest(unittest.TestCase):
    def test_semver_and_force_mark(self):
        self.assertEqual(atualizar.semver("v1.2.3"), (1, 2, 3))
        self.assertIsNone(atualizar.semver("1.2"))
        self.assertTrue(atualizar.FORCE_MARK.search("Correção urgente [forcar]"))
        self.assertTrue(atualizar.FORCE_MARK.search("[ Forçar ]"))
        self.assertFalse(atualizar.FORCE_MARK.search("forçar sem colchetes"))

    def _package(self, tmp, version, files=("instalar.sh", "src/server.py", "beni/sistema/instalar-sistema.sh")):
        archive = Path(tmp) / "p.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for name in list(files) + ["VERSION"]:
                data = (version + "\n").encode() if name == "VERSION" else b"x"
                info = tarfile.TarInfo(f"beni-launcher-{version}/{name}")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return archive

    def test_extract_and_check_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = atualizar.safe_extract(self._package(tmp, "1.1.0"), os.path.join(tmp, "x"))
            atualizar.check_package(root, "v1.1.0")
            with self.assertRaises(RuntimeError):
                atualizar.check_package(root, "1.2.0")  # VERSION não bate com a tag

    def test_incomplete_package_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = atualizar.safe_extract(self._package(tmp, "1.1.0", files=("instalar.sh",)), os.path.join(tmp, "x"))
            with self.assertRaises(RuntimeError):
                atualizar.check_package(root, "1.1.0")

    def test_night_window(self):
        conf = {"JANELA_INICIO": "2", "JANELA_FIM": "5"}
        with mock.patch.object(atualizar, "datetime") as dt:
            dt.datetime.now.return_value.hour = 3
            self.assertTrue(atualizar.in_night_window(conf))
            dt.datetime.now.return_value.hour = 14
            self.assertFalse(atualizar.in_night_window(conf))

    def test_live_apply_waits_for_open_app(self):
        with mock.patch.object(atualizar, "launcher_busy", return_value=True), \
                mock.patch.object(atualizar, "cmd_aplicar") as aplicar, \
                mock.patch.object(atualizar, "log"):
            atualizar.maybe_apply_live({}, None, forced=True)
        aplicar.assert_not_called()

    def test_not_forced_outside_window_does_nothing(self):
        with mock.patch.object(atualizar, "in_night_window", return_value=False), \
                mock.patch.object(atualizar, "cmd_aplicar") as aplicar:
            atualizar.maybe_apply_live({}, None, forced=False)
        aplicar.assert_not_called()

    def test_shell_scripts_parse(self):
        for script in ("instalar.sh", "beni/sistema/instalar-sistema.sh"):
            subprocess.run(["bash", "-n", str(ROOT / script)], check=True)

    def test_version_file_is_semver(self):
        self.assertIsNotNone(atualizar.semver((ROOT / "VERSION").read_text().strip()))


class AutoUpdateStatusTest(unittest.TestCase):
    def test_reads_updater_state(self):
        import server as server_module
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "estado.json"
            timer = Path(tmp) / "timer"
            timer.write_text("x")
            state.write_text(json.dumps({"baixada": "1.1.0", "forcada": True, "erro": None,
                                         "ultimaVerificacao": "2026-10-19T15:00:00-03:00"}))
            with mock.patch.object(server_module, "get_version", return_value="1.0.0"):
                status = server_module.auto_update_status(str(state), str(timer))
                self.assertEqual(status["staged"], "1.1.0")
                self.assertTrue(status["forced"])
                self.assertTrue(status["autoUpdate"])
                self.assertFalse(status["updateAvailable"])
                missing = server_module.auto_update_status(str(Path(tmp) / "nada"), str(Path(tmp) / "nada"))
                self.assertFalse(missing["autoUpdate"])
                self.assertEqual(missing["installedVersion"], "1.0.0")


class CatalogMigrationTest(unittest.TestCase):
    def cfg(self):
        return {"profiles": [
            {"id": "default", "tiles": [{"id": "a"}, {"id": "b"}], "categoryLimits": {"categories": {}}},
            {"id": "bea", "tiles": [{"id": "a"}]},
        ]}

    def test_add_after_and_skip_existing(self):
        cfg = self.cfg()
        op = {"op": "adicionar_tile", "depois_de": "a", "tile": {"id": "novo"}}
        self.assertEqual(migrar.apply_op(cfg, op), 2)
        self.assertEqual([t["id"] for t in cfg["profiles"][0]["tiles"]], ["a", "novo", "b"])
        self.assertEqual(migrar.apply_op(cfg, op), 0)

    def test_profiles_remove_update_and_set(self):
        cfg = self.cfg()
        migrar.apply_op(cfg, {"op": "remover_tile", "id": "a", "perfis": ["bea"]})
        self.assertEqual(cfg["profiles"][1]["tiles"], [])
        migrar.apply_op(cfg, {"op": "atualizar_tile", "id": "b", "campos": {"visible": False}})
        self.assertFalse(cfg["profiles"][0]["tiles"][1]["visible"])
        op = {"op": "definir", "caminho": "categoryLimits.categories.x", "valor": {"minutes": 5},
              "so_se_ausente": True, "perfis": ["default"]}
        migrar.apply_op(cfg, op)
        cfg["profiles"][0]["categoryLimits"]["categories"]["x"]["minutes"] = 9
        migrar.apply_op(cfg, op)  # não sobrescreve o que os pais mudaram
        self.assertEqual(cfg["profiles"][0]["categoryLimits"]["categories"]["x"]["minutes"], 9)

    def test_unknown_op_fails(self):
        with self.assertRaises(ValueError):
            migrar.apply_op(self.cfg(), {"op": "apagar_tudo"})

    def test_repository_migrations_file_is_valid(self):
        data = json.loads((ROOT / "beni/config/migracoes.json").read_text())
        ids = [m["id"] for m in data["migracoes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for migration in data["migracoes"]:
            for op in migration.get("operacoes", []):
                migrar.apply_op(self.cfg(), op)


if __name__ == "__main__":
    unittest.main()
